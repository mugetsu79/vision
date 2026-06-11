from __future__ import annotations

import json
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from argus.api.contracts import (
    FleetCameraWorkerSummary,
    FleetOverviewResponse,
    OperationsLifecycleRequestResponse,
    WorkerDesiredState,
    WorkerModelAdmissionResponse,
    WorkerRuntimeStatus,
)
from argus.compat import UTC
from argus.models.enums import (
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
    WorkerRuntimeState,
)
from argus.supervisor.process_adapter import WorkerProcessAdapter, WorkerProcessResult

_START_ACTIONS = {OperationsLifecycleAction.START, OperationsLifecycleAction.RESTART}
_ADMITTED_STATUSES = {
    ModelAdmissionStatus.RECOMMENDED,
    ModelAdmissionStatus.SUPPORTED,
    ModelAdmissionStatus.DEGRADED,
}
_DESIRED_RUNNING_STATES = {WorkerDesiredState.DESIRED, WorkerDesiredState.SUPERVISED}
_MAX_ON_FAILURE_RESTARTS = 3


class SupervisorOperationsClient(Protocol):
    async def poll_lifecycle_requests(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
        limit: int,
    ) -> list[OperationsLifecycleRequestResponse]: ...

    async def claim_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
    ) -> OperationsLifecycleRequestResponse: ...

    async def evaluate_model_admission_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
    ) -> WorkerModelAdmissionResponse: ...

    async def complete_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        status: OperationsLifecycleStatus,
        admission_report_id: UUID | None = None,
        error: str | None = None,
    ) -> OperationsLifecycleRequestResponse: ...

    async def record_runtime_report_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
        runtime_state: str,
        last_error: str | None = None,
    ) -> None: ...


class SupervisorReconciler:
    def __init__(
        self,
        *,
        operations: SupervisorOperationsClient,
        process_adapter: WorkerProcessAdapter,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None = None,
        limit: int = 10,
    ) -> None:
        self.operations = operations
        self.process_adapter = process_adapter
        self.tenant_id = tenant_id
        self.supervisor_id = supervisor_id
        self.edge_node_id = edge_node_id
        self.limit = limit

    async def reconcile_once(self, *, fleet: FleetOverviewResponse | None = None) -> int:
        requests = await self.operations.poll_lifecycle_requests(
            tenant_id=self.tenant_id,
            supervisor_id=self.supervisor_id,
            edge_node_id=self.edge_node_id,
            limit=self.limit,
        )
        processed = 0
        started_requests: set[tuple[UUID, UUID | None, str]] = set()
        for request in requests:
            claimed = await self.operations.claim_lifecycle_request(
                tenant_id=self.tenant_id,
                request_id=request.id,
                supervisor_id=self.supervisor_id,
                edge_node_id=self.edge_node_id,
            )
            await self._process_claimed_request(claimed, started_requests=started_requests)
            processed += 1
        processed += await self._reconcile_desired_workers(fleet)
        return processed

    async def _process_claimed_request(
        self,
        request: OperationsLifecycleRequestResponse,
        *,
        started_requests: set[tuple[UUID, UUID | None, str]],
    ) -> None:
        start_key = _start_key(request)
        if (
            request.action is OperationsLifecycleAction.START
            and start_key in started_requests
        ):
            await self._record_duplicate_start_as_running(request)
            return

        admission_report_id = None
        if request.action in _START_ACTIONS:
            admission = await self.operations.evaluate_model_admission_for_request(
                tenant_id=self.tenant_id,
                request=request,
            )
            admission_report_id = admission.id
            if admission.status not in _ADMITTED_STATUSES:
                await self.operations.complete_lifecycle_request(
                    tenant_id=self.tenant_id,
                    request_id=request.id,
                    supervisor_id=self.supervisor_id,
                    status=OperationsLifecycleStatus.FAILED,
                    admission_report_id=admission_report_id,
                    error=f"model admission {admission.status.value}: {admission.rationale}",
                )
                return

        result = await self._execute(request)
        await self.operations.record_runtime_report_for_request(
            tenant_id=self.tenant_id,
            request=request,
            runtime_state=result.runtime_state,
            last_error=result.last_error,
        )
        await self.operations.complete_lifecycle_request(
            tenant_id=self.tenant_id,
            request_id=request.id,
            supervisor_id=self.supervisor_id,
            status=(
                OperationsLifecycleStatus.FAILED
                if result.last_error
                else OperationsLifecycleStatus.COMPLETED
            ),
            admission_report_id=admission_report_id,
            error=result.last_error,
        )
        if request.action is OperationsLifecycleAction.START and result.last_error is None:
            started_requests.add(start_key)

    async def _record_duplicate_start_as_running(
        self,
        request: OperationsLifecycleRequestResponse,
    ) -> None:
        await self.operations.record_runtime_report_for_request(
            tenant_id=self.tenant_id,
            request=request,
            runtime_state="running",
            last_error=None,
        )
        await self.operations.complete_lifecycle_request(
            tenant_id=self.tenant_id,
            request_id=request.id,
            supervisor_id=self.supervisor_id,
            status=OperationsLifecycleStatus.COMPLETED,
            admission_report_id=None,
            error=None,
        )

    async def _reconcile_desired_workers(
        self,
        fleet: FleetOverviewResponse | None,
    ) -> int:
        if fleet is None:
            return 0
        processed = 0
        for worker in fleet.camera_workers:
            if self._should_record_running_heartbeat(worker):
                request = self._request_from_desired_worker(worker)
                await self.operations.record_runtime_report_for_request(
                    tenant_id=self.tenant_id,
                    request=request,
                    runtime_state="running",
                    last_error=None,
                )
                continue
            if not self._should_start_desired_worker(worker):
                continue
            request = self._request_from_desired_worker(worker)
            admission = await self.operations.evaluate_model_admission_for_request(
                tenant_id=self.tenant_id,
                request=request,
            )
            if admission.status not in _ADMITTED_STATUSES:
                continue
            request.admission_report_id = admission.id
            result = await self.process_adapter.start(worker.camera_id)
            await self.operations.record_runtime_report_for_request(
                tenant_id=self.tenant_id,
                request=request,
                runtime_state=result.runtime_state,
                last_error=result.last_error,
            )
            processed += 1
        return processed

    def _should_record_running_heartbeat(self, worker: FleetCameraWorkerSummary) -> bool:
        if worker.desired_state not in _DESIRED_RUNNING_STATES:
            return False
        if not _worker_owner_matches_supervisor(worker, edge_node_id=self.edge_node_id):
            return False
        is_running = getattr(self.process_adapter, "is_running", None)
        return bool(callable(is_running) and is_running(worker.camera_id))

    def _should_start_desired_worker(self, worker: FleetCameraWorkerSummary) -> bool:
        if getattr(self.process_adapter, "accepting_new_work", True) is False:
            return False
        if worker.desired_state not in _DESIRED_RUNNING_STATES:
            return False
        if not _worker_owner_matches_supervisor(worker, edge_node_id=self.edge_node_id):
            return False
        is_running = getattr(self.process_adapter, "is_running", None)
        if callable(is_running) and is_running(worker.camera_id):
            return False
        if not _restart_policy_allows_recovery(worker):
            return False
        return True

    def _request_from_desired_worker(
        self,
        worker: FleetCameraWorkerSummary,
    ) -> OperationsLifecycleRequestResponse:
        now = datetime.now(tz=UTC)
        return OperationsLifecycleRequestResponse(
            id=uuid4(),
            tenant_id=self.tenant_id,
            camera_id=worker.camera_id,
            edge_node_id=worker.node_id,
            assignment_id=worker.assignment.id if worker.assignment is not None else None,
            action=OperationsLifecycleAction.START,
            status=OperationsLifecycleStatus.ACKNOWLEDGED,
            requested_by_subject="supervisor-desired-state",
            requested_at=now,
            acknowledged_at=now,
            claimed_by_supervisor=self.supervisor_id,
            claimed_at=now,
            completed_at=None,
            admission_report_id=(
                worker.latest_model_admission.id if worker.latest_model_admission else None
            ),
            error=None,
            request_payload=_runtime_report_payload_from_worker(worker),
            created_at=now,
            updated_at=now,
        )

    async def _execute(
        self,
        request: OperationsLifecycleRequestResponse,
    ) -> WorkerProcessResult:
        if request.action is OperationsLifecycleAction.START:
            return await self.process_adapter.start(request.camera_id)
        if request.action is OperationsLifecycleAction.STOP:
            return await self.process_adapter.stop(request.camera_id)
        if request.action is OperationsLifecycleAction.RESTART:
            return await self.process_adapter.restart(request.camera_id)
        if request.action is OperationsLifecycleAction.DRAIN:
            return await self.process_adapter.drain(request.camera_id)
        return WorkerProcessResult(
            runtime_state="error",
            last_error=f"Unsupported lifecycle action {request.action!s}.",
        )


def _worker_owner_matches_supervisor(
    worker: FleetCameraWorkerSummary,
    *,
    edge_node_id: UUID | None,
) -> bool:
    if edge_node_id is None:
        return worker.lifecycle_owner == "central_supervisor" and worker.node_id is None
    return worker.lifecycle_owner == "edge_supervisor" and worker.node_id == edge_node_id


def _runtime_report_payload_from_worker(worker: FleetCameraWorkerSummary) -> dict[str, str | None]:
    passport = worker.runtime_passport
    latest = worker.latest_model_admission
    report = worker.runtime_report
    selected_provider = (
        (latest.selected_backend if latest is not None else None)
        or (report.selected_provider if report is not None else None)
        or (passport.selected_backend if passport is not None else None)
    )
    runtime_artifact_id = _fallback_runtime_artifact_id(
        selected_provider,
        passport.runtime_artifact_id if passport is not None else None,
        latest.runtime_artifact_id if latest is not None else None,
        report.runtime_artifact_id if report is not None else None,
    )
    return {
        "source": "desired_state_recovery",
        "runtime_artifact_id": (
            str(runtime_artifact_id) if runtime_artifact_id is not None else None
        ),
        "scene_contract_hash": report.scene_contract_hash if report is not None else None,
        "source_profile_hash": report.source_profile_hash if report is not None else None,
        "selected_provider": selected_provider,
        "media_pipeline_mode": report.media_pipeline_mode if report is not None else None,
        "media_capture_backend": (
            report.media_capture_backend if report is not None else None
        ),
        "encoder_mode": report.encoder_mode if report is not None else None,
    }


def _fallback_runtime_artifact_id(
    selected_provider: str | None,
    *candidates: UUID | None,
) -> UUID | None:
    if not _provider_uses_runtime_artifact(selected_provider):
        return None
    return next((candidate for candidate in candidates if candidate is not None), None)


def _provider_uses_runtime_artifact(selected_provider: str | None) -> bool:
    if not selected_provider:
        return False
    normalized = selected_provider.lower()
    return "tensorrt" in normalized or "trt" in normalized


def _restart_policy_allows_recovery(worker: FleetCameraWorkerSummary) -> bool:
    runtime_report = worker.runtime_report
    if runtime_report is None:
        return True
    if worker.restart_policy == "always":
        return True
    if worker.restart_policy == "never":
        return False
    if worker.restart_policy == "on_failure":
        if worker.runtime_status in {
            WorkerRuntimeStatus.STALE,
            WorkerRuntimeStatus.UNKNOWN,
        }:
            return True
        if (
            worker.runtime_status
            in {WorkerRuntimeStatus.RUNNING, WorkerRuntimeStatus.STARTING}
            and runtime_report.runtime_state is WorkerRuntimeState.RUNNING
        ):
            return True
        return (
            runtime_report.runtime_state is WorkerRuntimeState.ERROR
            and runtime_report.restart_count < _MAX_ON_FAILURE_RESTARTS
        )
    return False


def _start_key(request: OperationsLifecycleRequestResponse) -> tuple[UUID, UUID | None, str]:
    encoded_payload = json.dumps(
        request.request_payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return (request.camera_id, request.assignment_id, encoded_payload)
