from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    FleetCameraWorkerSummary,
    HardwarePerformanceSample,
    OperationsLifecycleRequestCreate,
    SupervisorRuntimeReportCreate,
    SupervisorRuntimeReportResponse,
    WorkerAssignmentCreate,
    WorkerDesiredState,
    WorkerModelAdmissionRequest,
    WorkerRuntimeStatus,
)
from argus.models.enums import (
    DetectorCapability,
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
    ProcessingMode,
    SupervisorMode,
    WorkerRuntimeState,
)
from argus.services.supervisor_operations import (
    SupervisorOperationsService,
    resolve_worker_operations_controls,
    supervisor_runtime_report_response,
)
from argus.supervisor.reconciler import SupervisorReconciler


@pytest.mark.asyncio
async def test_persists_worker_assignment_and_reassignment_records() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_a = uuid4()
    edge_b = uuid4()
    service = SupervisorOperationsService(_MemorySessionFactory())

    first = await service.create_assignment(
        tenant_id=tenant_id,
        payload=WorkerAssignmentCreate(
            camera_id=camera_id,
            edge_node_id=edge_a,
            desired_state="supervised",
        ),
        actor_subject="operator-1",
    )
    second = await service.create_assignment(
        tenant_id=tenant_id,
        payload=WorkerAssignmentCreate(
            camera_id=camera_id,
            edge_node_id=edge_b,
            desired_state="supervised",
        ),
        actor_subject="operator-2",
    )
    assignments = await service.list_assignments(tenant_id=tenant_id)

    assert first.camera_id == camera_id
    assert first.edge_node_id == edge_a
    assert first.active is False
    assert second.camera_id == camera_id
    assert second.edge_node_id == edge_b
    assert second.active is True
    assert second.supersedes_assignment_id == first.id
    assert [assignment.id for assignment in assignments] == [first.id, second.id]


@pytest.mark.asyncio
async def test_records_worker_runtime_report_with_heartbeat_and_runtime_truth() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    runtime_artifact_id = uuid4()
    scene_contract_hash = "a" * 64
    service = SupervisorOperationsService(_MemorySessionFactory())
    assignment = await service.create_assignment(
        tenant_id=tenant_id,
        payload=WorkerAssignmentCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            desired_state="supervised",
        ),
        actor_subject="operator-1",
    )

    report = await service.record_runtime_report(
        tenant_id=tenant_id,
        payload=SupervisorRuntimeReportCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=assignment.id,
            heartbeat_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            runtime_state=WorkerRuntimeState.RUNNING,
            restart_count=3,
            last_error="recovered from stream timeout",
            runtime_artifact_id=runtime_artifact_id,
            scene_contract_hash=scene_contract_hash,
            selected_provider="TensorrtExecutionProvider",
            media_pipeline_mode="jetson_gstreamer_native",
            media_capture_backend="gstreamer_rawvideo_pipe",
            encoder_mode="hardware",
            worker_origin="edge",
            processing_mode=ProcessingMode.EDGE,
            telemetry_ingest_lag_ms=42.5,
            telemetry_duplicate_frames=2,
            processing_fps_cap=15,
            output_fps=5,
            stream_profile_id="360p5",
            tracking_diagnostics={
                "new_track": 1,
                "active_tracks": 1,
                "coasting_tracks": 0,
            },
        ),
    )
    report.id = uuid4()
    report.created_at = datetime(2026, 5, 13, 9, 0, 1, tzinfo=UTC)
    latest = await service.latest_runtime_reports_by_camera(
        tenant_id=tenant_id,
        camera_ids=[camera_id],
    )
    response = supervisor_runtime_report_response(report)

    assert report.heartbeat_at == datetime(2026, 5, 13, 9, 0, tzinfo=UTC)
    assert report.runtime_state is WorkerRuntimeState.RUNNING
    assert report.restart_count == 3
    assert report.last_error == "recovered from stream timeout"
    assert report.runtime_artifact_id == runtime_artifact_id
    assert report.scene_contract_hash == scene_contract_hash
    assert report.selected_provider == "TensorrtExecutionProvider"
    assert report.media_pipeline_mode == "jetson_gstreamer_native"
    assert report.media_capture_backend == "gstreamer_rawvideo_pipe"
    assert report.encoder_mode == "hardware"
    assert report.worker_origin == "edge"
    assert report.processing_mode == ProcessingMode.EDGE
    assert report.telemetry_ingest_lag_ms == 42.5
    assert report.telemetry_duplicate_frames == 2
    assert report.processing_fps_cap == 15
    assert report.output_fps == 5
    assert report.stream_profile_id == "360p5"
    assert report.tracking_diagnostics == {
        "new_track": 1,
        "active_tracks": 1,
        "coasting_tracks": 0,
    }
    assert latest[camera_id].id == report.id
    assert latest[camera_id].media_capture_backend == "gstreamer_rawvideo_pipe"
    assert latest[camera_id].worker_origin == "edge"
    assert response.worker_origin == "edge"
    assert response.processing_mode == ProcessingMode.EDGE
    assert response.telemetry_ingest_lag_ms == 42.5
    assert response.telemetry_duplicate_frames == 2
    assert response.processing_fps_cap == 15
    assert response.output_fps == 5
    assert response.stream_profile_id == "360p5"
    assert response.tracking_diagnostics == {
        "new_track": 1,
        "active_tracks": 1,
        "coasting_tracks": 0,
    }


def test_supervisor_runtime_report_rejects_negative_ingest_health_values() -> None:
    base_payload = {
        "camera_id": uuid4(),
        "heartbeat_at": datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
    }

    with pytest.raises(ValidationError):
        SupervisorRuntimeReportCreate(
            **base_payload,
            telemetry_ingest_lag_ms=-0.1,
        )

    with pytest.raises(ValidationError):
        SupervisorRuntimeReportCreate(
            **base_payload,
            telemetry_duplicate_frames=-1,
        )

    with pytest.raises(ValidationError):
        SupervisorRuntimeReportCreate(
            **base_payload,
            processing_fps_cap=-1,
        )

    with pytest.raises(ValidationError):
        SupervisorRuntimeReportCreate(
            **base_payload,
            output_fps=-1,
        )


@pytest.mark.asyncio
async def test_creates_lifecycle_requests_without_running_process_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    service = SupervisorOperationsService(_MemorySessionFactory())
    monkeypatch.setattr("subprocess.run", _fail_if_called)

    requests = [
        await service.create_lifecycle_request(
            tenant_id=tenant_id,
            payload=OperationsLifecycleRequestCreate(camera_id=camera_id, action=action),
            actor_subject="operator-1",
        )
        for action in (
            OperationsLifecycleAction.START,
            OperationsLifecycleAction.STOP,
            OperationsLifecycleAction.RESTART,
            OperationsLifecycleAction.DRAIN,
        )
    ]

    assert [request.action for request in requests] == [
        OperationsLifecycleAction.START,
        OperationsLifecycleAction.STOP,
        OperationsLifecycleAction.RESTART,
        OperationsLifecycleAction.DRAIN,
    ]
    assert {request.status for request in requests} == {
        OperationsLifecycleStatus.REQUESTED
    }


@pytest.mark.asyncio
async def test_lifecycle_stop_drain_and_start_update_active_assignment_desired_state() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    service = SupervisorOperationsService(_MemorySessionFactory())
    assignment = await service.create_assignment(
        tenant_id=tenant_id,
        payload=WorkerAssignmentCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            desired_state=WorkerDesiredState.SUPERVISED,
        ),
        actor_subject="operator-1",
    )

    await service.create_lifecycle_request(
        tenant_id=tenant_id,
        payload=OperationsLifecycleRequestCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=assignment.id,
            action=OperationsLifecycleAction.STOP,
        ),
        actor_subject="operator-1",
    )
    stopped = await service.latest_assignments_by_camera(
        tenant_id=tenant_id,
        camera_ids=[camera_id],
    )

    assert stopped[camera_id].desired_state == WorkerDesiredState.NOT_DESIRED.value

    await service.create_lifecycle_request(
        tenant_id=tenant_id,
        payload=OperationsLifecycleRequestCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=assignment.id,
            action=OperationsLifecycleAction.DRAIN,
        ),
        actor_subject="operator-1",
    )
    drained = await service.latest_assignments_by_camera(
        tenant_id=tenant_id,
        camera_ids=[camera_id],
    )

    assert drained[camera_id].desired_state == WorkerDesiredState.NOT_DESIRED.value

    await service.create_lifecycle_request(
        tenant_id=tenant_id,
        payload=OperationsLifecycleRequestCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=assignment.id,
            action=OperationsLifecycleAction.START,
        ),
        actor_subject="operator-1",
    )
    started = await service.latest_assignments_by_camera(
        tenant_id=tenant_id,
        camera_ids=[camera_id],
    )

    assert started[camera_id].desired_state == WorkerDesiredState.SUPERVISED.value


@pytest.mark.asyncio
async def test_polling_mode_creates_request_for_supervisor_pickup_without_push_publish() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    dispatcher = _LifecyclePushDispatchSpy()
    service = SupervisorOperationsService(
        _MemorySessionFactory(),
        push_lifecycle_dispatcher=dispatcher,
    )

    request = await service.create_lifecycle_request(
        tenant_id=tenant_id,
        payload=OperationsLifecycleRequestCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            action=OperationsLifecycleAction.START,
        ),
        actor_subject="operator-1",
        operations_mode={
            "lifecycle_owner": "edge_supervisor",
            "supervisor_mode": "polling",
            "restart_policy": "on_failure",
        },
    )

    assert dispatcher.published_subjects == []
    assert request.status is OperationsLifecycleStatus.REQUESTED
    assert request.request_payload["dispatch_mode"] == "polling"
    assert request.request_payload["dispatch_status"] == "queued_for_polling"


@pytest.mark.asyncio
async def test_push_mode_publishes_lifecycle_request_and_records_ack_state() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    dispatcher = _LifecyclePushDispatchSpy()
    service = SupervisorOperationsService(
        _MemorySessionFactory(),
        push_lifecycle_dispatcher=dispatcher,
    )

    request = await service.create_lifecycle_request(
        tenant_id=tenant_id,
        payload=OperationsLifecycleRequestCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            action=OperationsLifecycleAction.START,
        ),
        actor_subject="operator-1",
        operations_mode={
            "lifecycle_owner": "edge_supervisor",
            "supervisor_mode": "push",
            "restart_policy": "on_failure",
        },
    )

    assert dispatcher.published_subjects == [f"supervisor.{edge_node_id}.lifecycle"]
    assert request.status is OperationsLifecycleStatus.REQUESTED
    assert request.request_payload["dispatch_mode"] == "push"
    assert request.request_payload["dispatch_status"] == "acknowledged"
    assert request.error is None


@pytest.mark.asyncio
async def test_push_mode_records_ack_timeout_state() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    dispatcher = _LifecyclePushDispatchSpy()
    dispatcher.queue_ack(timeout=True)
    service = SupervisorOperationsService(
        _MemorySessionFactory(),
        push_lifecycle_dispatcher=dispatcher,
    )

    request = await service.create_lifecycle_request(
        tenant_id=tenant_id,
        payload=OperationsLifecycleRequestCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            action=OperationsLifecycleAction.RESTART,
        ),
        actor_subject="operator-1",
        operations_mode={
            "lifecycle_owner": "edge_supervisor",
            "supervisor_mode": "push",
            "restart_policy": "always",
        },
    )

    assert dispatcher.published_subjects == [f"supervisor.{edge_node_id}.lifecycle"]
    assert request.status is OperationsLifecycleStatus.REQUESTED
    assert request.request_payload["dispatch_mode"] == "push"
    assert request.request_payload["dispatch_status"] == "ack_timeout"
    assert request.error == "Timed out waiting for supervisor push acknowledgement."


@pytest.mark.asyncio
async def test_disabled_supervisor_mode_rejects_lifecycle_request_with_clear_conflict() -> None:
    service = SupervisorOperationsService(_MemorySessionFactory())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_lifecycle_request(
            tenant_id=uuid4(),
            payload=OperationsLifecycleRequestCreate(
                camera_id=uuid4(),
                edge_node_id=uuid4(),
                action=OperationsLifecycleAction.START,
            ),
            actor_subject="operator-1",
            operations_mode={
                "lifecycle_owner": "edge_supervisor",
                "supervisor_mode": "disabled",
                "restart_policy": "never",
            },
        )

    assert exc_info.value.status_code == 409
    assert "supervisor mode is disabled" in str(exc_info.value.detail).lower()


def test_resolved_operations_mode_controls_lifecycle_owner_and_actions() -> None:
    manual = resolve_worker_operations_controls(
        {
            "lifecycle_owner": "manual",
            "supervisor_mode": "disabled",
            "restart_policy": "never",
        },
        assigned_edge_node_id=None,
        supervisor_healthy=False,
    )
    disabled_supervisor = resolve_worker_operations_controls(
        {
            "lifecycle_owner": "edge_supervisor",
            "supervisor_mode": "disabled",
            "restart_policy": "on_failure",
        },
        assigned_edge_node_id=uuid4(),
        supervisor_healthy=True,
    )
    edge_supervisor = resolve_worker_operations_controls(
        {
            "lifecycle_owner": "edge_supervisor",
            "supervisor_mode": "polling",
            "restart_policy": "always",
        },
        assigned_edge_node_id=uuid4(),
        supervisor_healthy=True,
    )
    edge_assigned_central_profile = resolve_worker_operations_controls(
        {
            "lifecycle_owner": "central_supervisor",
            "supervisor_mode": "polling",
            "restart_policy": "always",
        },
        assigned_edge_node_id=uuid4(),
        supervisor_healthy=True,
    )

    assert manual.lifecycle_owner == "manual"
    assert manual.supervisor_mode is SupervisorMode.DISABLED
    assert manual.allowed_actions == []
    assert manual.detail == "Manual mode requires operator-started worker processes."
    assert disabled_supervisor.lifecycle_owner == "edge_supervisor"
    assert disabled_supervisor.allowed_actions == []
    assert disabled_supervisor.detail == "Supervisor mode is disabled."
    assert edge_supervisor.lifecycle_owner == "edge_supervisor"
    assert edge_supervisor.supervisor_mode is SupervisorMode.POLLING
    assert edge_supervisor.restart_policy == "always"
    assert edge_supervisor.allowed_actions == [
        OperationsLifecycleAction.START,
        OperationsLifecycleAction.STOP,
        OperationsLifecycleAction.RESTART,
        OperationsLifecycleAction.DRAIN,
    ]
    assert edge_assigned_central_profile.lifecycle_owner == "edge_supervisor"
    assert edge_assigned_central_profile.detail == (
        "Assigned edge node overrides central supervisor ownership; "
        "edge supervisor owns this worker process."
    )
    assert OperationsLifecycleAction.START in edge_assigned_central_profile.allowed_actions


def test_missing_or_stale_runtime_reports_render_honest_states() -> None:
    service = SupervisorOperationsService(_MemorySessionFactory())
    now = datetime(2026, 5, 13, 10, 0, tzinfo=UTC)

    assert service.runtime_status_for_report(None, now=now) == "not_reported"
    assert (
        service.runtime_status_for_report(
            _ReportLike(heartbeat_at=now - timedelta(minutes=20)),
            now=now,
        )
        == "unknown"
    )


def test_restart_policy_controls_desired_worker_reconciliation() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    reconciler = SupervisorReconciler(
        operations=_NoopSupervisorOperations(),
        process_adapter=_FakeProcessAdapter(),
        tenant_id=tenant_id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=edge_node_id,
    )

    assert not reconciler._should_start_desired_worker(
        _fleet_worker(
            tenant_id=tenant_id,
            edge_node_id=edge_node_id,
            restart_policy="never",
            runtime_state=WorkerRuntimeState.STOPPED,
            restart_count=0,
        )
    )
    assert not reconciler._should_start_desired_worker(
        _fleet_worker(
            tenant_id=tenant_id,
            edge_node_id=edge_node_id,
            restart_policy="on_failure",
            runtime_state=WorkerRuntimeState.STOPPED,
            restart_count=0,
        )
    )
    assert reconciler._should_start_desired_worker(
        _fleet_worker(
            tenant_id=tenant_id,
            edge_node_id=edge_node_id,
            restart_policy="on_failure",
            runtime_state=WorkerRuntimeState.ERROR,
            restart_count=1,
        )
    )
    assert not reconciler._should_start_desired_worker(
        _fleet_worker(
            tenant_id=tenant_id,
            edge_node_id=edge_node_id,
            restart_policy="on_failure",
            runtime_state=WorkerRuntimeState.ERROR,
            restart_count=3,
        )
    )
    assert reconciler._should_start_desired_worker(
        _fleet_worker(
            tenant_id=tenant_id,
            edge_node_id=edge_node_id,
            restart_policy="always",
            runtime_state=WorkerRuntimeState.STOPPED,
            restart_count=0,
        )
    )


@pytest.mark.asyncio
async def test_records_hardware_report_with_capability_and_performance() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    model_id = uuid4()
    service = SupervisorOperationsService(_MemorySessionFactory())

    report = await service.record_hardware_report(
        tenant_id=tenant_id,
        supervisor_id="edge-supervisor-1",
        payload=EdgeNodeHardwareReportCreate(
            edge_node_id=edge_node_id,
            reported_at=datetime(2026, 5, 13, 10, 5, tzinfo=UTC),
            host_profile="macos-x86_64-intel",
            os_name="darwin",
            machine_arch="x86_64",
            cpu_model="Intel Core i7",
            cpu_cores=8,
            memory_total_mb=32768,
            accelerators=["coreml"],
            provider_capabilities={"CoreMLExecutionProvider": True},
            observed_performance=[
                HardwarePerformanceSample(
                    model_id=model_id,
                    model_name="YOLO26n COCO",
                    runtime_backend="CoreMLExecutionProvider",
                    input_width=1280,
                    input_height=720,
                    target_fps=10.0,
                    observed_fps=10.0,
                    stage_p95_ms={"total": 92.0, "detect": 55.0},
                    stage_p99_ms={"total": 118.0, "detect": 71.0},
                )
            ],
            thermal_state="nominal",
        ),
    )
    latest_by_edge = await service.latest_hardware_reports_by_edge_node(
        tenant_id=tenant_id,
        edge_node_ids=[edge_node_id],
    )
    latest_by_supervisor = await service.latest_hardware_report_for_supervisor(
        tenant_id=tenant_id,
        supervisor_id="edge-supervisor-1",
    )
    central_report = await service.record_hardware_report(
        tenant_id=tenant_id,
        supervisor_id="central-supervisor-1",
        payload=EdgeNodeHardwareReportCreate(
            edge_node_id=None,
            reported_at=datetime(2026, 5, 13, 8, 4, tzinfo=UTC),
            host_profile="linux-x86_64-intel",
            os_name="linux",
            machine_arch="x86_64",
            cpu_model="Intel Xeon",
            cpu_cores=16,
            memory_total_mb=65536,
            accelerators=[],
            provider_capabilities={"CPUExecutionProvider": True},
            observed_performance=[],
        ),
    )
    latest_central = await service.latest_hardware_report_for_central(
        tenant_id=tenant_id,
    )

    assert report.edge_node_id == edge_node_id
    assert report.supervisor_id == "edge-supervisor-1"
    assert report.provider_capabilities["CoreMLExecutionProvider"] is True
    assert report.observed_performance[0]["stage_p95_ms"]["total"] == 92.0
    assert len(report.report_hash) == 64
    assert latest_by_edge[edge_node_id].id == report.id
    assert latest_by_supervisor is not None
    assert latest_by_supervisor.id == report.id
    assert central_report.edge_node_id is None
    assert latest_central is not None
    assert latest_central.id == central_report.id


@pytest.mark.asyncio
async def test_records_model_admission_report_and_latest_by_camera() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    assignment_id = uuid4()
    model_id = uuid4()
    hardware_report_id = uuid4()
    service = SupervisorOperationsService(_MemorySessionFactory())

    admission = await service.record_model_admission(
        tenant_id=tenant_id,
        payload=WorkerModelAdmissionRequest(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=assignment_id,
            model_id=model_id,
            model_name="YOLO26n COCO",
            model_capability=DetectorCapability.FIXED_VOCAB,
            selected_backend="CoreMLExecutionProvider",
            stream_profile={"width": 1280, "height": 720, "fps": 10},
        ),
        hardware_report_id=hardware_report_id,
        status=ModelAdmissionStatus.RECOMMENDED,
        rationale="CoreML p95 total 92.0ms fits the 100.0ms frame budget.",
        constraints={"frame_budget_ms": 100.0},
        recommended_backend="CoreMLExecutionProvider",
    )
    latest = await service.latest_model_admissions_by_camera(
        tenant_id=tenant_id,
        camera_ids=[camera_id],
    )

    assert admission.camera_id == camera_id
    assert admission.edge_node_id == edge_node_id
    assert admission.assignment_id == assignment_id
    assert admission.hardware_report_id == hardware_report_id
    assert admission.status is ModelAdmissionStatus.RECOMMENDED
    assert admission.rationale.startswith("CoreML")
    assert latest[camera_id].id == admission.id


@pytest.mark.asyncio
async def test_supervisor_claims_and_completes_scoped_lifecycle_request() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    admission_report_id = uuid4()
    service = SupervisorOperationsService(_MemorySessionFactory())
    edge_request = await service.create_lifecycle_request(
        tenant_id=tenant_id,
        payload=OperationsLifecycleRequestCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            action=OperationsLifecycleAction.START,
        ),
        actor_subject="operator-1",
    )
    await service.create_lifecycle_request(
        tenant_id=tenant_id,
        payload=OperationsLifecycleRequestCreate(
            camera_id=uuid4(),
            edge_node_id=uuid4(),
            action=OperationsLifecycleAction.START,
        ),
        actor_subject="operator-1",
    )

    pending = await service.poll_lifecycle_requests(
        tenant_id=tenant_id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=edge_node_id,
        limit=10,
    )
    claimed = await service.claim_lifecycle_request(
        tenant_id=tenant_id,
        request_id=edge_request.id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=edge_node_id,
    )
    claimed_status = claimed.status
    claimed_by_supervisor = claimed.claimed_by_supervisor
    claimed_at = claimed.claimed_at
    pending_after_claim = await service.poll_lifecycle_requests(
        tenant_id=tenant_id,
        supervisor_id="edge-supervisor-1",
        edge_node_id=edge_node_id,
        limit=10,
    )
    completed = await service.complete_lifecycle_request(
        tenant_id=tenant_id,
        request_id=edge_request.id,
        supervisor_id="edge-supervisor-1",
        status=OperationsLifecycleStatus.COMPLETED,
        admission_report_id=admission_report_id,
    )

    assert [request.id for request in pending] == [edge_request.id]
    assert claimed_status is OperationsLifecycleStatus.ACKNOWLEDGED
    assert claimed_by_supervisor == "edge-supervisor-1"
    assert claimed_at is not None
    assert pending_after_claim == []
    assert completed.status is OperationsLifecycleStatus.COMPLETED
    assert completed.completed_at is not None
    assert completed.admission_report_id == admission_report_id


def _fail_if_called(*args, **kwargs) -> None:  # noqa: ANN002, ANN003
    raise AssertionError("Lifecycle requests must not shell out from the API process.")


class _LifecyclePushDispatchSpy:
    def __init__(self) -> None:
        self.published_subjects: list[str] = []
        self._timeout_next = False

    def queue_ack(self, *, timeout: bool) -> None:
        self._timeout_next = timeout

    async def dispatch(self, request) -> object:  # noqa: ANN001
        self.published_subjects.append(f"supervisor.{request.edge_node_id}.lifecycle")
        if self._timeout_next:
            self._timeout_next = False
            return SimpleNamespace(
                dispatch_status="ack_timeout",
                error="Timed out waiting for supervisor push acknowledgement.",
            )
        return SimpleNamespace(dispatch_status="acknowledged", error=None)


class _ReportLike:
    def __init__(self, heartbeat_at: datetime) -> None:
        self.heartbeat_at = heartbeat_at
        self.runtime_state = WorkerRuntimeState.RUNNING


class _NoopSupervisorOperations:
    pass


class _FakeProcessAdapter:
    accepting_new_work = True

    def is_running(self, camera_id) -> bool:  # noqa: ANN001
        return False


def _fleet_worker(
    *,
    tenant_id,
    edge_node_id,
    restart_policy: str,
    runtime_state: WorkerRuntimeState,
    restart_count: int,
) -> FleetCameraWorkerSummary:
    camera_id = uuid4()
    now = datetime(2026, 5, 13, 10, 0, tzinfo=UTC)
    return FleetCameraWorkerSummary(
        camera_id=camera_id,
        camera_name="Driveway",
        site_id=uuid4(),
        node_id=edge_node_id,
        node_hostname="edge-supervisor-1",
        processing_mode=ProcessingMode.EDGE,
        desired_state=WorkerDesiredState.SUPERVISED,
        runtime_status=WorkerRuntimeStatus.OFFLINE,
        lifecycle_owner="edge_supervisor",
        detail="Edge supervisor owns this worker process.",
        runtime_report=SupervisorRuntimeReportResponse(
            id=uuid4(),
            tenant_id=tenant_id,
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=uuid4(),
            heartbeat_at=now,
            runtime_state=runtime_state,
            restart_count=restart_count,
            last_error="worker exited" if runtime_state is WorkerRuntimeState.ERROR else None,
            runtime_artifact_id=None,
            scene_contract_hash=None,
            created_at=now,
        ),
        supervisor_mode=SupervisorMode.POLLING,
        restart_policy=restart_policy,  # type: ignore[arg-type]
        allowed_lifecycle_actions=[],
    )


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[object]:
        return self.rows


class _MemorySession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    async def __aenter__(self) -> _MemorySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _Result:  # noqa: ANN001
        params = statement.compile().params
        tenant_id = params.get("tenant_id_1")
        camera_id = params.get("camera_id_1")
        rows = self.rows
        if tenant_id is not None:
            rows = [row for row in rows if getattr(row, "tenant_id", None) == tenant_id]
        if camera_id is not None:
            rows = [row for row in rows if getattr(row, "camera_id", None) == camera_id]
        return _Result(rows)

    def add(self, row: object) -> None:
        self.rows.append(row)

    async def commit(self) -> None:
        return None

    async def refresh(self, row: object) -> None:
        return None


class _MemorySessionFactory:
    def __init__(self) -> None:
        self.session = _MemorySession()

    def __call__(self) -> _MemorySession:
        return self.session
