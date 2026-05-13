from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    HardwarePerformanceSample,
    OperationsLifecycleRequestResponse,
    WorkerModelAdmissionResponse,
)
from argus.models.enums import (
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
)
from argus.supervisor.process_adapter import WorkerProcessResult
from argus.supervisor.runner import SupervisorRunner


@pytest.mark.asyncio
async def test_runner_posts_hardware_report_before_polling() -> None:
    operations = _FakeOperations(requests=[])
    runner = SupervisorRunner(
        supervisor_id="central-imac",
        edge_node_id=None,
        hardware_probe=_FakeHardwareProbe(),
        metrics_probe=_FakeMetricsProbe([]),
        operations=operations,
        process_adapter=_FakeProcessAdapter(),
        tenant_id=uuid4(),
    )

    processed = await runner.run_once()

    assert processed == 0
    assert operations.events == ["hardware", "poll"]
    assert operations.hardware_reports[0].host_profile == "macos-x86_64-intel"
    assert operations.hardware_reports[0].observed_performance == []


@pytest.mark.asyncio
async def test_runner_includes_metrics_derived_performance_samples() -> None:
    sample = HardwarePerformanceSample(
        model_name="YOLO26n COCO",
        runtime_backend="CoreMLExecutionProvider",
        input_width=1280,
        input_height=720,
        target_fps=10,
        stage_p95_ms={"total": 92.0},
        stage_p99_ms={"total": 110.0},
    )
    operations = _FakeOperations(requests=[])
    runner = SupervisorRunner(
        supervisor_id="central-imac",
        edge_node_id=None,
        hardware_probe=_FakeHardwareProbe(),
        metrics_probe=_FakeMetricsProbe([sample]),
        operations=operations,
        process_adapter=_FakeProcessAdapter(),
        tenant_id=uuid4(),
    )

    await runner.run_once()

    assert operations.hardware_reports[0].observed_performance == [sample]


@pytest.mark.asyncio
async def test_runner_blocks_unknown_start_without_calling_process_adapter() -> None:
    request = _lifecycle_request(OperationsLifecycleAction.START)
    operations = _FakeOperations(
        requests=[request],
        admission_status=ModelAdmissionStatus.UNKNOWN,
    )
    adapter = _FakeProcessAdapter()
    runner = SupervisorRunner(
        supervisor_id="edge-supervisor-1",
        edge_node_id=request.edge_node_id,
        hardware_probe=_FakeHardwareProbe(),
        metrics_probe=_FakeMetricsProbe([]),
        operations=operations,
        process_adapter=adapter,
        tenant_id=uuid4(),
    )

    processed = await runner.run_once()

    assert processed == 1
    assert adapter.calls == []
    assert operations.completions[0]["status"] is OperationsLifecycleStatus.FAILED
    assert "unknown" in str(operations.completions[0]["error"])


@pytest.mark.asyncio
async def test_runner_allows_supported_start_and_records_runtime_report() -> None:
    request = _lifecycle_request(OperationsLifecycleAction.START)
    operations = _FakeOperations(
        requests=[request],
        admission_status=ModelAdmissionStatus.SUPPORTED,
    )
    adapter = _FakeProcessAdapter()
    runner = SupervisorRunner(
        supervisor_id="edge-supervisor-1",
        edge_node_id=request.edge_node_id,
        hardware_probe=_FakeHardwareProbe(),
        metrics_probe=_FakeMetricsProbe([]),
        operations=operations,
        process_adapter=adapter,
        tenant_id=uuid4(),
    )

    processed = await runner.run_once()

    assert processed == 1
    assert adapter.calls == [("start", request.camera_id)]
    assert operations.runtime_reports[0]["runtime_state"] == "running"
    assert operations.completions[0]["status"] is OperationsLifecycleStatus.COMPLETED


def _lifecycle_request(action: OperationsLifecycleAction) -> OperationsLifecycleRequestResponse:
    return OperationsLifecycleRequestResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        camera_id=uuid4(),
        edge_node_id=uuid4(),
        assignment_id=uuid4(),
        action=action,
        status=OperationsLifecycleStatus.REQUESTED,
        requested_by_subject="operator-1",
        requested_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        request_payload={},
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )


class _FakeHardwareProbe:
    def build_hardware_report(
        self,
        *,
        edge_node_id: UUID | None,
        observed_performance: list[HardwarePerformanceSample],
    ) -> EdgeNodeHardwareReportCreate:
        return EdgeNodeHardwareReportCreate(
            edge_node_id=edge_node_id,
            reported_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
            host_profile="macos-x86_64-intel",
            os_name="darwin",
            machine_arch="x86_64",
            provider_capabilities={"CoreMLExecutionProvider": True},
            accelerators=["coreml"],
            observed_performance=observed_performance,
        )


class _FakeMetricsProbe:
    def __init__(self, samples: list[HardwarePerformanceSample]) -> None:
        self.samples = samples

    async def build_performance_samples(
        self,
        worker_contexts: object,
        previous_snapshot: object | None = None,
    ) -> list[HardwarePerformanceSample]:
        del worker_contexts, previous_snapshot
        return self.samples


class _FakeOperations:
    def __init__(
        self,
        *,
        requests: list[OperationsLifecycleRequestResponse],
        admission_status: ModelAdmissionStatus = ModelAdmissionStatus.RECOMMENDED,
    ) -> None:
        self.requests = requests
        self.admission_status = admission_status
        self.events: list[str] = []
        self.hardware_reports: list[EdgeNodeHardwareReportCreate] = []
        self.completions: list[dict[str, object]] = []
        self.runtime_reports: list[dict[str, object]] = []

    async def record_hardware_report(self, report: EdgeNodeHardwareReportCreate) -> None:
        self.events.append("hardware")
        self.hardware_reports.append(report)

    async def fetch_fleet_overview(self) -> object:
        return object()

    async def poll_lifecycle_requests(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
        limit: int,
    ) -> list[OperationsLifecycleRequestResponse]:
        del tenant_id, supervisor_id, edge_node_id, limit
        self.events.append("poll")
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
        return next(request for request in self.requests if request.id == request_id)

    async def evaluate_model_admission_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
    ) -> WorkerModelAdmissionResponse:
        del tenant_id
        return WorkerModelAdmissionResponse(
            id=uuid4(),
            tenant_id=request.tenant_id,
            camera_id=request.camera_id,
            edge_node_id=request.edge_node_id,
            assignment_id=request.assignment_id,
            hardware_report_id=uuid4(),
            model_id=uuid4(),
            model_name="YOLO26n COCO",
            model_capability="fixed_vocab",
            stream_profile={"width": 1280, "height": 720, "fps": 10},
            status=self.admission_status,
            selected_backend="CoreMLExecutionProvider",
            rationale=f"{self.admission_status.value} in test",
            constraints={},
            evaluated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
            created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        )

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
        del tenant_id, supervisor_id
        self.completions.append(
            {
                "request_id": request_id,
                "status": status,
                "admission_report_id": admission_report_id,
                "error": error,
            }
        )
        return next(request for request in self.requests if request.id == request_id)

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
        return WorkerProcessResult(runtime_state="stopped")
