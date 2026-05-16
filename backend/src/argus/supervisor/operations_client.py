from __future__ import annotations

import inspect
import time
from collections.abc import Awaitable, Callable
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
    SupervisorServiceReportCreate,
    SupervisorServiceReportResponse,
    WorkerConfigResponse,
    WorkerModelAdmissionRequest,
    WorkerModelAdmissionResponse,
)
from argus.compat import UTC
from argus.models.enums import DetectorCapability, OperationsLifecycleStatus, WorkerRuntimeState
from argus.supervisor.credential_store import SupervisorCredentialStore

BearerTokenProvider = Callable[[], str | Awaitable[str]]


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


class PasswordGrantTokenProvider:
    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        username: str,
        password: str,
        client_secret: str | None = None,
        scope: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        refresh_margin_seconds: float = 30.0,
    ) -> None:
        self.token_url = token_url
        self.client_id = client_id
        self.username = username
        self.password = password
        self.client_secret = client_secret
        self.scope = scope
        self.http_client = http_client
        self.refresh_margin_seconds = refresh_margin_seconds
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._owns_client = http_client is None

    async def __call__(self) -> str:
        now = time.monotonic()
        if self._access_token is not None and now < self._expires_at - self.refresh_margin_seconds:
            return self._access_token
        return await self._fetch_token(now)

    def invalidate(self) -> None:
        self._access_token = None
        self._expires_at = 0.0

    async def aclose(self) -> None:
        if self.http_client is not None and self._owns_client:
            await self.http_client.aclose()

    async def _fetch_token(self, now: float) -> str:
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": self.username,
            "password": self.password,
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret
        if self.scope:
            payload["scope"] = self.scope
        response = await self._client().post(self.token_url, data=payload)
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(
                f"Token request failed with HTTP {response.status_code}: {response.text}"
            )
        body = response.json()
        token = body.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("Token response did not include an access_token.")
        expires_in = _positive_float(body.get("expires_in"), 300.0)
        self._access_token = token
        self._expires_at = now + expires_in
        return token

    def _client(self) -> httpx.AsyncClient:
        if self.http_client is None:
            self.http_client = httpx.AsyncClient()
        return self.http_client


class SupervisorOperationsClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        supervisor_id: str,
        bearer_token: str | None = None,
        token_provider: BearerTokenProvider | None = None,
        credential_store: SupervisorCredentialStore | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not bearer_token and token_provider is None and credential_store is None:
            raise ValueError("bearer_token, token_provider, or credential_store is required.")
        self.api_base_url = api_base_url.rstrip("/")
        self.supervisor_id = supervisor_id
        self.bearer_token = bearer_token
        self.token_provider = token_provider
        self.credential_store = credential_store
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

    async def record_service_report(
        self,
        report: SupervisorServiceReportCreate,
    ) -> SupervisorServiceReportResponse:
        body = await self._request(
            "POST",
            f"/api/v1/deployment/supervisors/{self.supervisor_id}/service-reports",
            json=report.model_dump(mode="json"),
        )
        return SupervisorServiceReportResponse.model_validate(body)

    async def fetch_fleet_overview(self) -> FleetOverviewResponse:
        body = await self._request("GET", "/api/v1/operations/fleet")
        return FleetOverviewResponse.model_validate(body)

    async def fetch_worker_config(self, camera_id: UUID) -> WorkerConfigResponse:
        body = await self._request("GET", f"/api/v1/cameras/{camera_id}/worker-config")
        return WorkerConfigResponse.model_validate(body)

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
            headers={"Authorization": f"Bearer {await self._bearer_token()}"},
        )
        if response.status_code == 401 and self.token_provider is not None:
            invalidate = getattr(self.token_provider, "invalidate", None)
            if callable(invalidate):
                invalidate()
            response = await client.request(
                method,
                f"{self.api_base_url}{path}",
                json=json,
                headers={"Authorization": f"Bearer {await self._bearer_token()}"},
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise SupervisorClientError(
                method=method,
                path=path,
                status_code=response.status_code,
                response_body=response.text,
            )
        return response.json()

    async def _bearer_token(self) -> str:
        if self.token_provider is None:
            token = self.credential_store.load() if self.credential_store is not None else None
            token = token or self.bearer_token
        else:
            provided = self.token_provider()
            token = await provided if inspect.isawaitable(provided) else provided
        if not isinstance(token, str) or not token:
            raise RuntimeError("Supervisor API bearer token is not configured.")
        return token

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


def _positive_float(value: object, fallback: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    return number if number > 0 else fallback


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
