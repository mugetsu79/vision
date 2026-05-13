from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    EdgeNodeHardwareReportResponse,
    FleetCameraWorkerSummary,
    FleetOverviewResponse,
    OperationsLifecycleRequestResponse,
    SupervisorPollResponse,
    SupervisorRuntimeReportCreate,
    SupervisorRuntimeReportResponse,
    WorkerModelAdmissionRequest,
    WorkerModelAdmissionResponse,
)
from argus.compat import UTC
from argus.models.enums import DetectorCapability, OperationsLifecycleStatus, WorkerRuntimeState


@dataclass(frozen=True, slots=True)
class SupervisorClientError(RuntimeError):
    method: str
    path: str
    status_code: int
    response_body: str

    def __str__(self) -> str:
        return (
            f"{self.method} {self.path} failed with HTTP {self.status_code}: "
            f"{self.response_body}"
        )


class SupervisorOperationsClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        supervisor_id: str,
        bearer_token: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.supervisor_id = supervisor_id
        self.bearer_token = bearer_token
        self.http_client = http_client
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self.http_client is not None and self._owns_client:
            await self.http_client.aclose()

    async def record_hardware_report(
        self,
        report: EdgeNodeHardwareReportCreate,
    ) -> EdgeNodeHardwareReportResponse:
        body = await self._request(
            "POST",
            f"/api/v1/operations/supervisors/{self.supervisor_id}/hardware-reports",
            json=report.model_dump(mode="json"),
        )
        return EdgeNodeHardwareReportResponse.model_validate(body)

    async def fetch_fleet_overview(self) -> FleetOverviewResponse:
        body = await self._request("GET", "/api/v1/operations/fleet")
        return FleetOverviewResponse.model_validate(body)

    async def poll_lifecycle_requests(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
        limit: int,
    ) -> list[OperationsLifecycleRequestResponse]:
        del tenant_id
        body = await self._request(
            "POST",
            f"/api/v1/operations/supervisors/{supervisor_id}/poll",
            json={
                "edge_node_id": str(edge_node_id) if edge_node_id is not None else None,
                "limit": limit,
            },
        )
        return SupervisorPollResponse.model_validate(body).requests

    async def claim_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
    ) -> OperationsLifecycleRequestResponse:
        del tenant_id
        body = await self._request(
            "POST",
            f"/api/v1/operations/lifecycle-requests/{request_id}/claim",
            json={
                "supervisor_id": supervisor_id,
                "edge_node_id": str(edge_node_id) if edge_node_id is not None else None,
            },
        )
        return OperationsLifecycleRequestResponse.model_validate(body)

    async def complete_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        status: OperationsLifecycleStatus,
        admission_report_id: UUID | None = None,
        error: str | None = None,
    ) -> OperationsLifecycleRequestResponse:
        del tenant_id
        body = await self._request(
            "POST",
            f"/api/v1/operations/lifecycle-requests/{request_id}/complete",
            json={
                "supervisor_id": supervisor_id,
                "status": status.value,
                "admission_report_id": (
                    str(admission_report_id) if admission_report_id is not None else None
                ),
                "error": error,
            },
        )
        return OperationsLifecycleRequestResponse.model_validate(body)

    async def record_runtime_report_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
        runtime_state: str,
        last_error: str | None = None,
    ) -> SupervisorRuntimeReportResponse:
        del tenant_id
        payload = SupervisorRuntimeReportCreate(
            camera_id=request.camera_id,
            edge_node_id=request.edge_node_id,
            assignment_id=request.assignment_id,
            heartbeat_at=datetime.now(tz=UTC),
            runtime_state=_runtime_state(runtime_state),
            restart_count=0,
            last_error=last_error,
        )
        body = await self._request(
            "POST",
            "/api/v1/operations/runtime-reports",
            json=payload.model_dump(mode="json"),
        )
        return SupervisorRuntimeReportResponse.model_validate(body)

    async def evaluate_model_admission_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
    ) -> WorkerModelAdmissionResponse:
        del tenant_id
        fleet = await self.fetch_fleet_overview()
        payload = build_admission_request(request, fleet=fleet)
        body = await self._request(
            "POST",
            f"/api/v1/operations/workers/{request.camera_id}/model-admission/evaluate",
            json=payload.model_dump(mode="json"),
        )
        return WorkerModelAdmissionResponse.model_validate(body)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        client = self._client()
        response = await client.request(
            method,
            f"{self.api_base_url}{path}",
            json=json,
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise SupervisorClientError(
                method=method,
                path=path,
                status_code=response.status_code,
                response_body=response.text,
            )
        return response.json()

    def _client(self) -> httpx.AsyncClient:
        if self.http_client is None:
            self.http_client = httpx.AsyncClient()
        return self.http_client


def build_admission_request(
    request: OperationsLifecycleRequestResponse,
    *,
    fleet: FleetOverviewResponse,
) -> WorkerModelAdmissionRequest:
    worker = _worker_for_camera(fleet, request.camera_id)
    request_payload = dict(request.request_payload)
    latest = worker.latest_model_admission if worker is not None else None
    passport = worker.runtime_passport if worker is not None else None
    assignment = worker.assignment if worker is not None else None
    selected_backend = (
        _string(request_payload.get("selected_backend"))
        or (passport.selected_backend if passport is not None else None)
        or (latest.selected_backend if latest is not None else None)
    )
    preferred_backend = (
        _string(request_payload.get("preferred_backend"))
        or selected_backend
        or (latest.recommended_backend if latest is not None else None)
        or "onnxruntime"
    )
    stream_profile = request_payload.get("stream_profile")
    if not isinstance(stream_profile, dict):
        stream_profile = latest.stream_profile if latest is not None else {}
    return WorkerModelAdmissionRequest(
        camera_id=request.camera_id,
        edge_node_id=request.edge_node_id or (worker.node_id if worker is not None else None),
        assignment_id=request.assignment_id or (assignment.id if assignment is not None else None),
        model_id=_uuid(request_payload.get("model_id"))
        or (latest.model_id if latest is not None else None),
        model_name=_string(request_payload.get("model_name"))
        or (latest.model_name if latest is not None else None),
        model_capability=_detector_capability(
            request_payload.get("model_capability"),
            latest.model_capability if latest is not None else None,
        ),
        runtime_artifact_id=_uuid(request_payload.get("runtime_artifact_id"))
        or (passport.runtime_artifact_id if passport is not None else None)
        or (latest.runtime_artifact_id if latest is not None else None),
        runtime_artifact_target_profile=_string(
            request_payload.get("runtime_artifact_target_profile")
        )
        or (passport.target_profile if passport is not None else None),
        runtime_selection_profile_id=_uuid(
            request_payload.get("runtime_selection_profile_id")
        )
        or (passport.runtime_selection_profile_id if passport is not None else None)
        or (latest.runtime_selection_profile_id if latest is not None else None),
        selected_backend=selected_backend,
        preferred_backend=preferred_backend,
        stream_profile=stream_profile,
        fallback_allowed=bool(request_payload.get("fallback_allowed", True)),
    )


def _worker_for_camera(
    fleet: FleetOverviewResponse,
    camera_id: UUID,
) -> FleetCameraWorkerSummary | None:
    return next(
        (worker for worker in fleet.camera_workers if worker.camera_id == camera_id),
        None,
    )


def _runtime_state(value: str) -> WorkerRuntimeState:
    try:
        return WorkerRuntimeState(value)
    except ValueError:
        return WorkerRuntimeState.UNKNOWN


def _uuid(value: object | None) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _detector_capability(
    raw_value: object | None,
    fallback: DetectorCapability | None,
) -> DetectorCapability:
    if isinstance(raw_value, DetectorCapability):
        return raw_value
    if raw_value is not None:
        try:
            return DetectorCapability(str(raw_value))
        except ValueError:
            pass
    return fallback or DetectorCapability.FIXED_VOCAB
