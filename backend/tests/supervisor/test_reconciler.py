from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    FleetCameraWorkerSummary,
    FleetOverviewResponse,
    FleetSummary,
    OperationsLifecycleRequestResponse,
    WorkerAssignmentResponse,
    WorkerDesiredState,
    WorkerModelAdmissionResponse,
    WorkerRuntimeStatus,
)
from argus.models.enums import (
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
    ProcessingMode,
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


@pytest.mark.asyncio
async def test_reconciler_recovers_desired_worker_after_restart() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    admission = _admission_response(
        tenant_id=tenant_id,
        camera_id=uuid4(),
        edge_node_id=edge_node_id,
        assignment_id=uuid4(),
        status=ModelAdmissionStatus.RECOMMENDED,
    )
    worker = _fleet_worker(
        tenant_id=tenant_id,
        edge_node_id=edge_node_id,
        desired_state=WorkerDesiredState.SUPERVISED,
        runtime_status=WorkerRuntimeStatus.OFFLINE,
        admission=admission,
    )
    operations = _FakeSupervisorOperations(
        requests=[],
        admission=admission,
    )
    adapter = _FakeProcessAdapter()
    reconciler = SupervisorReconciler(
        operations=operations,
        process_adapter=adapter,
        tenant_id=tenant_id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=edge_node_id,
    )

    processed = await reconciler.reconcile_once(fleet=_fleet_overview(worker))

    assert processed == 1
    assert adapter.calls == [("start", worker.camera_id)]
    assert operations.admission_evaluations == [worker.camera_id]
    assert operations.runtime_reports[0]["camera_id"] == worker.camera_id


@pytest.mark.asyncio
async def test_reconciler_does_not_recover_worker_with_unknown_model_admission() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    admission = _admission_response(
        tenant_id=tenant_id,
        camera_id=uuid4(),
        edge_node_id=edge_node_id,
        assignment_id=uuid4(),
        status=ModelAdmissionStatus.UNKNOWN,
    )
    worker = _fleet_worker(
        tenant_id=tenant_id,
        edge_node_id=edge_node_id,
        desired_state=WorkerDesiredState.SUPERVISED,
        runtime_status=WorkerRuntimeStatus.RUNNING,
        admission=admission,
    )
    operations = _FakeSupervisorOperations(requests=[], admission=admission)
    adapter = _FakeProcessAdapter()
    reconciler = SupervisorReconciler(
        operations=operations,
        process_adapter=adapter,
        tenant_id=tenant_id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=edge_node_id,
    )

    processed = await reconciler.reconcile_once(fleet=_fleet_overview(worker))

    assert processed == 0
    assert adapter.calls == []
    assert operations.admission_evaluations == [worker.camera_id]
    assert operations.runtime_reports == []


@pytest.mark.asyncio
async def test_reconciler_leaves_not_desired_worker_stopped() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    admission = _admission_response(
        tenant_id=tenant_id,
        camera_id=uuid4(),
        edge_node_id=edge_node_id,
        assignment_id=uuid4(),
        status=ModelAdmissionStatus.RECOMMENDED,
    )
    worker = _fleet_worker(
        tenant_id=tenant_id,
        edge_node_id=edge_node_id,
        desired_state=WorkerDesiredState.NOT_DESIRED,
        runtime_status=WorkerRuntimeStatus.OFFLINE,
        admission=admission,
    )
    operations = _FakeSupervisorOperations(requests=[], admission=admission)
    adapter = _FakeProcessAdapter()
    reconciler = SupervisorReconciler(
        operations=operations,
        process_adapter=adapter,
        tenant_id=tenant_id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=edge_node_id,
    )

    processed = await reconciler.reconcile_once(fleet=_fleet_overview(worker))

    assert processed == 0
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_reconciler_does_not_spawn_duplicate_start_requests() -> None:
    camera_id = uuid4()
    assignment_id = uuid4()
    request_a = _lifecycle_request(
        action=OperationsLifecycleAction.START,
        camera_id=camera_id,
        assignment_id=assignment_id,
    )
    request_b = _lifecycle_request(
        action=OperationsLifecycleAction.START,
        camera_id=camera_id,
        assignment_id=assignment_id,
    )
    admission = _admission_response(
        tenant_id=request_a.tenant_id,
        camera_id=camera_id,
        edge_node_id=request_a.edge_node_id,
        assignment_id=request_a.assignment_id or uuid4(),
        status=ModelAdmissionStatus.RECOMMENDED,
    )
    operations = _FakeSupervisorOperations(
        requests=[request_a, request_b],
        admission=admission,
    )
    adapter = _FakeProcessAdapter()
    reconciler = SupervisorReconciler(
        operations=operations,
        process_adapter=adapter,
        tenant_id=request_a.tenant_id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=request_a.edge_node_id,
    )

    processed = await reconciler.reconcile_once()

    assert processed == 2
    assert adapter.calls == [("start", camera_id)]
    assert [row["runtime_state"] for row in operations.runtime_reports] == [
        "running",
        "running",
    ]


@pytest.mark.asyncio
async def test_reconciler_evaluates_distinct_duplicate_camera_start_requests() -> None:
    camera_id = uuid4()
    assignment_a = uuid4()
    assignment_b = uuid4()
    request_a = _lifecycle_request(
        action=OperationsLifecycleAction.START,
        camera_id=camera_id,
        assignment_id=assignment_a,
    )
    request_b = _lifecycle_request(
        action=OperationsLifecycleAction.START,
        camera_id=camera_id,
        assignment_id=assignment_b,
    )
    admission = _admission_response(
        tenant_id=request_a.tenant_id,
        camera_id=camera_id,
        edge_node_id=request_a.edge_node_id,
        assignment_id=assignment_a,
        status=ModelAdmissionStatus.RECOMMENDED,
    )
    operations = _FakeSupervisorOperations(
        requests=[request_a, request_b],
        admission=admission,
    )
    adapter = _FakeProcessAdapter()
    reconciler = SupervisorReconciler(
        operations=operations,
        process_adapter=adapter,
        tenant_id=request_a.tenant_id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=request_a.edge_node_id,
    )

    processed = await reconciler.reconcile_once()

    assert processed == 2
    assert adapter.calls == [("start", camera_id)]
    assert operations.admission_evaluations == [camera_id, camera_id]
    assert operations.completions[1]["admission_report_id"] == admission.id


def _lifecycle_request(
    *,
    action: OperationsLifecycleAction,
    camera_id: UUID | None = None,
    assignment_id: UUID | None = None,
) -> OperationsLifecycleRequestResponse:
    return OperationsLifecycleRequestResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        camera_id=camera_id or uuid4(),
        edge_node_id=uuid4(),
        assignment_id=assignment_id or uuid4(),
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
        self.admission_evaluations: list[UUID] = []

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
        del tenant_id
        self.admission_evaluations.append(request.camera_id)
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
        self.running: set[UUID] = set()

    async def start(self, camera_id: UUID) -> WorkerProcessResult:
        if camera_id not in self.running:
            self.calls.append(("start", camera_id))
            self.running.add(camera_id)
            return WorkerProcessResult(runtime_state="running")
        return WorkerProcessResult(runtime_state="running")

    def is_running(self, camera_id: UUID) -> bool:
        return camera_id in self.running

    async def stop(self, camera_id: UUID) -> WorkerProcessResult:
        self.calls.append(("stop", camera_id))
        self.running.discard(camera_id)
        return WorkerProcessResult(runtime_state="stopped")

    async def restart(self, camera_id: UUID) -> WorkerProcessResult:
        self.calls.append(("restart", camera_id))
        return WorkerProcessResult(runtime_state="running")

    async def drain(self, camera_id: UUID) -> WorkerProcessResult:
        self.calls.append(("drain", camera_id))
        self.running.discard(camera_id)
        return WorkerProcessResult(runtime_state="draining")


def _fleet_worker(
    *,
    tenant_id: UUID,
    edge_node_id: UUID | None,
    desired_state: WorkerDesiredState,
    runtime_status: WorkerRuntimeStatus,
    admission: WorkerModelAdmissionResponse,
) -> FleetCameraWorkerSummary:
    assignment_id = admission.assignment_id or uuid4()
    return FleetCameraWorkerSummary(
        camera_id=admission.camera_id,
        camera_name="Dock Camera",
        site_id=uuid4(),
        node_id=edge_node_id,
        processing_mode=ProcessingMode.EDGE if edge_node_id is not None else ProcessingMode.CENTRAL,
        desired_state=desired_state,
        runtime_status=runtime_status,
        lifecycle_owner="edge_supervisor" if edge_node_id is not None else "central_supervisor",
        assignment=WorkerAssignmentResponse(
            id=assignment_id,
            tenant_id=tenant_id,
            camera_id=admission.camera_id,
            edge_node_id=edge_node_id,
            desired_state=desired_state,
            active=True,
            supersedes_assignment_id=None,
            assigned_by_subject="operator-1",
            created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        ),
        latest_model_admission=admission,
    )


def _fleet_overview(worker: FleetCameraWorkerSummary) -> FleetOverviewResponse:
    return FleetOverviewResponse(
        mode="supervised",
        generated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        summary=FleetSummary(
            desired_workers=1,
            running_workers=0,
            stale_nodes=0,
            offline_nodes=0,
            native_unavailable_cameras=0,
        ),
        nodes=[],
        camera_workers=[worker],
        delivery_diagnostics=[],
    )


def _admission_response(
    *,
    tenant_id: UUID,
    camera_id: UUID,
    edge_node_id: UUID | None,
    assignment_id: UUID,
    status: ModelAdmissionStatus,
) -> WorkerModelAdmissionResponse:
    return WorkerModelAdmissionResponse(
        id=uuid4(),
        tenant_id=tenant_id,
        camera_id=camera_id,
        edge_node_id=edge_node_id,
        assignment_id=assignment_id,
        hardware_report_id=uuid4(),
        model_id=uuid4(),
        model_name="YOLO26n COCO",
        model_capability="fixed_vocab",
        stream_profile={"width": 1280, "height": 720, "fps": 10},
        status=status,
        selected_backend="CoreMLExecutionProvider",
        rationale=f"{status.value} in test",
        constraints={},
        evaluated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )
