from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

import argus.supervisor.runner as runner_module
from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    FleetCameraWorkerSummary,
    FleetOverviewResponse,
    FleetSummary,
    HardwarePerformanceSample,
    OperationsLifecycleRequestResponse,
    SupervisorServiceReportCreate,
    WorkerAssignmentResponse,
    WorkerDesiredState,
    WorkerModelAdmissionResponse,
    WorkerRuntimeStatus,
)
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentServiceManager,
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
    ProcessingMode,
)
from argus.supervisor.process_adapter import WorkerProcessResult
from argus.supervisor.runner import SupervisorRunner, parse_args


def test_parse_args_accepts_refreshable_token_credentials_without_static_bearer() -> None:
    config = parse_args(
        [
            "--supervisor-id",
            "central-imac",
            "--role",
            "central",
            "--api-base-url",
            "http://127.0.0.1:8000",
            "--token-url",
            "http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token",
            "--token-username",
            "admin-dev",
            "--token-password",
            "argus-admin-pass",
        ]
    )

    assert config.bearer_token is None
    assert config.token_client_id == "argus-cli"
    assert config.token_username == "admin-dev"


def test_parse_args_product_config_uses_credential_store_without_static_bearer(tmp_path) -> None:
    config_path = tmp_path / "supervisor.json"
    credential_path = tmp_path / "supervisor.credential"
    credential_path.write_text("node-credential-secret", encoding="utf-8")
    config_path.write_text(
        """
{
  "supervisor_id": "central-imac",
  "role": "central",
  "api_base_url": "http://127.0.0.1:8000",
  "credential_store_path": "supervisor.credential"
}
""".strip(),
        encoding="utf-8",
    )

    config = parse_args(["--config", str(config_path), "--once"])

    assert config.bearer_token is None
    assert config.token_password is None
    assert config.credential_store_path == credential_path
    assert config.supervisor_id == "central-imac"


def test_parse_args_product_healthcheck_accepts_config_without_token_file(tmp_path) -> None:
    config_path = tmp_path / "supervisor.json"
    config_path.write_text(
        """
{
  "supervisor_id": "central-imac",
  "role": "central",
  "api_base_url": "http://127.0.0.1:8000",
  "credential_store_path": "supervisor.credential"
}
""".strip(),
        encoding="utf-8",
    )

    config = parse_args(["--healthcheck", "--config", str(config_path)])

    assert config.healthcheck is True
    assert config.credential_store_path == tmp_path / "supervisor.credential"


def test_parse_args_labels_password_grant_as_dev_only() -> None:
    config = parse_args(
        [
            "--supervisor-id",
            "central-imac",
            "--role",
            "central",
            "--api-base-url",
            "http://127.0.0.1:8000",
            "--token-url",
            "http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token",
            "--token-username",
            "admin-dev",
            "--token-password",
            "argus-admin-pass",
        ]
    )

    assert config.product_mode is False
    assert config.auth_mode == "password_grant_dev"


@pytest.mark.asyncio
async def test_runner_posts_service_and_hardware_reports_before_polling() -> None:
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
    assert operations.events == ["service", "hardware", "poll"]
    assert operations.service_reports[0].service_manager is DeploymentServiceManager.DIRECT_CHILD
    assert operations.service_reports[0].install_status is DeploymentInstallStatus.HEALTHY
    assert operations.service_reports[0].credential_status is DeploymentCredentialStatus.ACTIVE
    assert operations.hardware_reports[0].host_profile == "macos-x86_64-intel"
    assert operations.hardware_reports[0].observed_performance == []


@pytest.mark.asyncio
async def test_runner_stays_alive_when_api_credentials_are_not_ready() -> None:
    runner = SupervisorRunner(
        supervisor_id="central-imac",
        edge_node_id=None,
        hardware_probe=_FakeHardwareProbe(),
        metrics_probe=_FakeMetricsProbe([]),
        operations=_UnavailableOperations(),
        process_adapter=_FakeProcessAdapter(),
        tenant_id=uuid4(),
    )

    processed = await runner.run_once()

    assert processed == 0


@pytest.mark.asyncio
async def test_run_forever_keeps_polling_when_api_credentials_are_not_ready(monkeypatch) -> None:
    class StopLoop(Exception):
        pass

    sleep_calls = 0

    async def stop_after_second_sleep(seconds: float) -> None:
        del seconds
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 2:
            raise StopLoop

    monkeypatch.setattr(runner_module.asyncio, "sleep", stop_after_second_sleep)
    runner = SupervisorRunner(
        supervisor_id="central-imac",
        edge_node_id=None,
        hardware_probe=_FakeHardwareProbe(),
        metrics_probe=_FakeMetricsProbe([]),
        operations=_UnavailableOperations(),
        process_adapter=_FakeProcessAdapter(),
        tenant_id=uuid4(),
    )

    with pytest.raises(StopLoop):
        await runner.run_forever(
            hardware_report_interval_seconds=60.0,
            poll_interval_seconds=5.0,
        )

    assert sleep_calls == 2


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


@pytest.mark.asyncio
async def test_runner_recovers_desired_worker_from_fleet_after_restart() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    worker = _fleet_worker(
        tenant_id=tenant_id,
        edge_node_id=edge_node_id,
        desired_state=WorkerDesiredState.SUPERVISED,
        runtime_status=WorkerRuntimeStatus.OFFLINE,
        admission_status=ModelAdmissionStatus.RECOMMENDED,
    )
    operations = _FakeOperations(
        requests=[],
        fleet=_fleet_overview(worker),
        admission_status=ModelAdmissionStatus.RECOMMENDED,
    )
    adapter = _FakeProcessAdapter()
    runner = SupervisorRunner(
        supervisor_id="edge-supervisor-1",
        edge_node_id=edge_node_id,
        hardware_probe=_FakeHardwareProbe(),
        metrics_probe=_FakeMetricsProbe([]),
        operations=operations,
        process_adapter=adapter,
        tenant_id=tenant_id,
    )

    processed = await runner.run_once()

    assert processed == 1
    assert adapter.calls == [("start", worker.camera_id)]
    assert operations.runtime_reports[0]["camera_id"] == worker.camera_id


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
        fleet: FleetOverviewResponse | None = None,
    ) -> None:
        self.requests = requests
        self.admission_status = admission_status
        self.fleet = fleet
        self.events: list[str] = []
        self.service_reports: list[SupervisorServiceReportCreate] = []
        self.hardware_reports: list[EdgeNodeHardwareReportCreate] = []
        self.completions: list[dict[str, object]] = []
        self.runtime_reports: list[dict[str, object]] = []

    async def record_service_report(self, report: SupervisorServiceReportCreate) -> None:
        self.events.append("service")
        self.service_reports.append(report)

    async def record_hardware_report(self, report: EdgeNodeHardwareReportCreate) -> None:
        self.events.append("hardware")
        self.hardware_reports.append(report)

    async def fetch_fleet_overview(self) -> FleetOverviewResponse | None:
        return self.fleet

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


class _UnavailableOperations:
    async def record_service_report(self, report: SupervisorServiceReportCreate) -> None:
        del report
        raise RuntimeError("Supervisor API bearer token is not configured.")

    async def record_hardware_report(self, report: EdgeNodeHardwareReportCreate) -> None:
        del report
        raise RuntimeError("Supervisor API bearer token is not configured.")

    async def fetch_fleet_overview(self) -> FleetOverviewResponse | None:
        raise RuntimeError("Supervisor API bearer token is not configured.")

    async def poll_lifecycle_requests(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
        limit: int,
    ) -> list[OperationsLifecycleRequestResponse]:
        del tenant_id, supervisor_id, edge_node_id, limit
        raise RuntimeError("Supervisor API bearer token is not configured.")


class _FakeProcessAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, UUID]] = []
        self.running: set[UUID] = set()

    async def start(self, camera_id: UUID) -> WorkerProcessResult:
        self.calls.append(("start", camera_id))
        self.running.add(camera_id)
        return WorkerProcessResult(runtime_state="running")

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
        return WorkerProcessResult(runtime_state="stopped")

    def is_running(self, camera_id: UUID) -> bool:
        return camera_id in self.running


def _fleet_worker(
    *,
    tenant_id: UUID,
    edge_node_id: UUID | None,
    desired_state: WorkerDesiredState,
    runtime_status: WorkerRuntimeStatus,
    admission_status: ModelAdmissionStatus,
) -> FleetCameraWorkerSummary:
    camera_id = uuid4()
    assignment_id = uuid4()
    return FleetCameraWorkerSummary(
        camera_id=camera_id,
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
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            desired_state=desired_state,
            active=True,
            supersedes_assignment_id=None,
            assigned_by_subject="operator-1",
            created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        ),
        latest_model_admission=_admission_response(
            tenant_id=tenant_id,
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=assignment_id,
            status=admission_status,
        ),
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
