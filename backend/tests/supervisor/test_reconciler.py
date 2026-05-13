from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    OperationsLifecycleRequestResponse,
    WorkerModelAdmissionResponse,
)
from argus.models.enums import (
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
)
from argus.supervisor.process_adapter import WorkerProcessResult
from argus.supervisor.reconciler import SupervisorReconciler


@pytest.mark.asyncio
async def test_reconciler_blocks_unsupported_start_before_process_action() -> None:
    request = _lifecycle_request(action=OperationsLifecycleAction.START)
    operations = _FakeSupervisorOperations(
        requests=[request],
        admission=WorkerModelAdmissionResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            camera_id=request.camera_id,
            edge_node_id=request.edge_node_id,
            assignment_id=request.assignment_id,
            hardware_report_id=uuid4(),
            model_id=uuid4(),
            model_name="YOLOE S open vocabulary",
            model_capability="open_vocab",
            runtime_artifact_id=None,
            runtime_selection_profile_id=None,
            stream_profile={"width": 1280, "height": 720, "fps": 10},
            status=ModelAdmissionStatus.UNSUPPORTED,
            selected_backend="onnxruntime",
            recommended_model_id=uuid4(),
            recommended_model_name="YOLO26n COCO",
            recommended_runtime_profile_id=None,
            recommended_backend="onnxruntime",
            rationale="open-world model unsupported on CPU-only hardware",
            constraints={},
            evaluated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
            created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        ),
    )
    adapter = _FakeProcessAdapter()
    reconciler = SupervisorReconciler(
        operations=operations,
        process_adapter=adapter,
        tenant_id=uuid4(),
        supervisor_id="edge-supervisor-1",
        edge_node_id=request.edge_node_id,
    )

    processed = await reconciler.reconcile_once()

    assert processed == 1
    assert adapter.calls == []
    assert operations.completions[0]["status"] is OperationsLifecycleStatus.FAILED
    assert operations.completions[0]["admission_report_id"] == operations.admission.id
    assert "unsupported" in operations.completions[0]["error"]


@pytest.mark.asyncio
async def test_reconciler_starts_worker_when_admission_allows_it() -> None:
    request = _lifecycle_request(action=OperationsLifecycleAction.START)
    operations = _FakeSupervisorOperations(
        requests=[request],
        admission=WorkerModelAdmissionResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            camera_id=request.camera_id,
            edge_node_id=request.edge_node_id,
            assignment_id=request.assignment_id,
            hardware_report_id=uuid4(),
            model_id=uuid4(),
            model_name="YOLO26n COCO",
            model_capability="fixed_vocab",
            runtime_artifact_id=None,
            runtime_selection_profile_id=None,
            stream_profile={"width": 1280, "height": 720, "fps": 10},
            status=ModelAdmissionStatus.RECOMMENDED,
            selected_backend="CoreMLExecutionProvider",
            recommended_model_id=None,
            recommended_model_name=None,
            recommended_runtime_profile_id=None,
            recommended_backend="CoreMLExecutionProvider",
            rationale="CoreML p95 fits frame budget",
            constraints={},
            evaluated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
            created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        ),
    )
    adapter = _FakeProcessAdapter()
    reconciler = SupervisorReconciler(
        operations=operations,
        process_adapter=adapter,
        tenant_id=uuid4(),
        supervisor_id="edge-supervisor-1",
        edge_node_id=request.edge_node_id,
    )

    processed = await reconciler.reconcile_once()

    assert processed == 1
    assert adapter.calls == [("start", request.camera_id)]
    assert operations.completions[0]["status"] is OperationsLifecycleStatus.COMPLETED
    assert operations.runtime_reports[0]["runtime_state"] == "running"


def _lifecycle_request(
    *,
    action: OperationsLifecycleAction,
) -> OperationsLifecycleRequestResponse:
    return OperationsLifecycleRequestResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        camera_id=uuid4(),
        edge_node_id=uuid4(),
        assignment_id=uuid4(),
        action=action,
        status=OperationsLifecycleStatus.REQUESTED,
        requested_by_subject="operator-1",
        requested_at=datetime(2026, 5, 13, 11, 30, tzinfo=UTC),
        acknowledged_at=None,
        claimed_by_supervisor=None,
        claimed_at=None,
        completed_at=None,
        admission_report_id=None,
        error=None,
        request_payload={"source": "test"},
        created_at=datetime(2026, 5, 13, 11, 30, tzinfo=UTC),
        updated_at=datetime(2026, 5, 13, 11, 30, tzinfo=UTC),
    )


class _FakeSupervisorOperations:
    def __init__(
        self,
        *,
        requests: list[OperationsLifecycleRequestResponse],
        admission: WorkerModelAdmissionResponse,
    ) -> None:
        self.requests = requests
        self.admission = admission
        self.completions: list[dict[str, object]] = []
        self.runtime_reports: list[dict[str, object]] = []

    async def poll_lifecycle_requests(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
        limit: int,
    ) -> list[OperationsLifecycleRequestResponse]:
        del tenant_id, supervisor_id, edge_node_id, limit
        return self.requests

    async def claim_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
    ) -> OperationsLifecycleRequestResponse:
        del tenant_id, supervisor_id, edge_node_id
        request = next(row for row in self.requests if row.id == request_id)
        request.status = OperationsLifecycleStatus.ACKNOWLEDGED
        return request

    async def evaluate_model_admission_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
    ) -> WorkerModelAdmissionResponse:
        del tenant_id, request
        return self.admission

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
        del tenant_id, request_id, supervisor_id
        self.completions.append(
            {
                "status": status,
                "admission_report_id": admission_report_id,
                "error": error,
            }
        )
        request = self.requests[0]
        request.status = status
        request.admission_report_id = admission_report_id
        request.error = error
        return request

    async def record_runtime_report_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
        runtime_state: str,
        last_error: str | None = None,
    ) -> None:
        del tenant_id
        self.runtime_reports.append(
            {
                "camera_id": request.camera_id,
                "runtime_state": runtime_state,
                "last_error": last_error,
            }
        )


class _FakeProcessAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, UUID]] = []

    async def start(self, camera_id: UUID) -> WorkerProcessResult:
        self.calls.append(("start", camera_id))
        return WorkerProcessResult(runtime_state="running")

    async def stop(self, camera_id: UUID) -> WorkerProcessResult:
        self.calls.append(("stop", camera_id))
        return WorkerProcessResult(runtime_state="stopped")

    async def restart(self, camera_id: UUID) -> WorkerProcessResult:
        self.calls.append(("restart", camera_id))
        return WorkerProcessResult(runtime_state="running")

    async def drain(self, camera_id: UUID) -> WorkerProcessResult:
        self.calls.append(("drain", camera_id))
        return WorkerProcessResult(runtime_state="draining")
