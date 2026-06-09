from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import (
    DeploymentNodeResponse,
    FleetBootstrapRequest,
    TenantContext,
    WorkerDesiredState,
    WorkerModelAdmissionRequest,
)
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DeploymentServiceManager,
    IncidentRuleSeverity,
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    ProcessingMode,
    RoleEnum,
    RuleAction,
    TrackerType,
)
from argus.models.tables import (
    Camera,
    DeploymentNode,
    DetectionRule,
    EdgeNode,
    EdgeNodeHardwareReport,
    RuleEvent,
    Site,
    WorkerAssignment,
    WorkerModelAdmissionReport,
)
from argus.services.app import OperationsService


class _FakeResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows

    def scalars(self) -> _FakeResult:
        return self

    def scalar_one_or_none(self) -> object | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(
        self,
        result_sets: list[list[object]],
        get_map: dict[tuple[type[object], UUID], object],
    ) -> None:
        self._result_sets = result_sets
        self._get_map = get_map

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _FakeResult:  # noqa: ANN001
        return _FakeResult(self._result_sets.pop(0))

    async def get(self, model, ident):  # noqa: ANN001
        return self._get_map.get((model, ident))


class _FakeSessionFactory:
    def __init__(
        self,
        *result_sets: list[object],
        get_map: dict[tuple[type[object], UUID], object] | None = None,
    ) -> None:
        self.result_sets = [list(result_set) for result_set in result_sets]
        self.get_map = get_map or {}

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.result_sets, self.get_map)


class _FakeDeploymentNodes:
    def __init__(self, nodes: list[DeploymentNodeResponse]) -> None:
        self.nodes = nodes

    async def list_nodes(self, *, tenant_id) -> list[DeploymentNodeResponse]:  # noqa: ANN001
        return self.nodes


def _tenant_context(tenant_id) -> TenantContext:  # noqa: ANN001
    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )


def _supervisor_tenant_context(tenant_id: UUID, deployment_node_id: UUID) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject=f"deployment-node:{deployment_node_id}",
            email=None,
            role=RoleEnum.ADMIN,
            issuer="supervisor-node-credential",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={
                "auth_type": "supervisor_node_credential",
                "deployment_node_id": str(deployment_node_id),
            },
        ),
    )


def _site(tenant_id) -> Site:  # noqa: ANN001
    return Site(
        id=uuid4(),
        tenant_id=tenant_id,
        name="HQ",
        description=None,
        tz="UTC",
        geo_point=None,
    )


def _deployment_node(
    tenant_id,
    *,
    node_kind: DeploymentNodeKind,
    supervisor_id: str,
    hostname: str,
    edge_node_id=None,  # noqa: ANN001
    last_service_reported_at: datetime | None,
) -> DeploymentNodeResponse:
    return DeploymentNodeResponse(
        id=uuid4(),
        tenant_id=tenant_id,
        node_kind=node_kind,
        edge_node_id=edge_node_id,
        supervisor_id=supervisor_id,
        hostname=hostname,
        install_status=DeploymentInstallStatus.HEALTHY,
        credential_status=DeploymentCredentialStatus.ACTIVE,
        service_manager=DeploymentServiceManager.SYSTEMD,
        service_status="running",
        version="portable-demo",
        os_name="linux",
        host_profile="linux-aarch64",
        last_service_reported_at=last_service_reported_at,
        diagnostics={},
        created_at=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_fleet_overview_derives_manual_central_worker() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=None,
        name="Lobby",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={
            "default_profile": "720p10",
            "allow_native_on_demand": True,
            "profiles": [{"id": "720p10", "kind": "transcode", "w": 1280, "h": 720, "fps": 10}],
        },
        source_capability={"width": 1280, "height": 720, "fps": 10, "codec": "h264"},
        frame_skip=1,
        fps_cap=25,
    )
    session_factory = _FakeSessionFactory([], [(camera, site)], [], [], [])
    service = OperationsService(session_factory=session_factory, settings=Settings(_env_file=None))
    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    assert response.mode == "manual_dev"
    assert response.summary.desired_workers == 1
    assert response.camera_workers[0].camera_name == "Lobby"
    assert response.camera_workers[0].desired_state == "manual"
    assert response.camera_workers[0].runtime_status == "not_reported"
    dev_run_command = response.camera_workers[0].dev_run_command
    assert dev_run_command is not None
    assert "<token>" not in dev_run_command
    assert "grant_type=password&client_id=argus-cli" in dev_run_command
    assert 'ARGUS_API_BEARER_TOKEN="$TOKEN"' in dev_run_command
    assert "argus.inference.engine --camera-id" in dev_run_command
    assert response.delivery_diagnostics[0].source_capability is not None


@pytest.mark.asyncio
async def test_fleet_overview_reports_incident_rule_runtime_truth() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=None,
        name="Server Room",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={},
        source_capability=None,
        frame_skip=1,
        fps_cap=25,
    )
    rule = DetectionRule(
        id=uuid4(),
        camera_id=camera.id,
        enabled=True,
        name="Restricted person",
        incident_type="restricted_person",
        severity=IncidentRuleSeverity.CRITICAL,
        description=None,
        zone_id=None,
        predicate={"class_names": ["person"], "zone_ids": ["server-room"]},
        action=RuleAction.RECORD_CLIP,
        webhook_url=None,
        cooldown_seconds=45,
        rule_hash="f" * 64,
    )
    rule_event = RuleEvent(
        id=uuid4(),
        ts=datetime(2026, 5, 12, 9, 30, tzinfo=UTC),
        camera_id=camera.id,
        rule_id=rule.id,
        event_payload={"rule_hash": "f" * 64},
        snapshot_url=None,
    )
    session_factory = _FakeSessionFactory(
        [],
        [(camera, site)],
        [],
        [rule],
        [rule_event],
    )
    service = OperationsService(session_factory=session_factory, settings=Settings(_env_file=None))

    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    assert response.camera_workers[0].rule_runtime.configured_rule_count == 1
    assert response.camera_workers[0].rule_runtime.effective_rule_hash == "f" * 64
    assert response.camera_workers[0].rule_runtime.latest_rule_event_at == rule_event.ts
    assert response.camera_workers[0].rule_runtime.load_status == "loaded"


@pytest.mark.asyncio
async def test_fleet_overview_maps_edge_heartbeat_status() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-1",
        public_key="seed",
        version="0.1.0",
        last_seen_at=datetime.now(tz=UTC) - timedelta(minutes=10),
    )
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=edge.id,
        name="Driveway",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["car"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={},
        source_capability=None,
        frame_skip=1,
        fps_cap=25,
    )
    session_factory = _FakeSessionFactory([(edge, site)], [(camera, site)], [], [], [])
    service = OperationsService(session_factory=session_factory, settings=Settings(_env_file=None))
    response = await service.get_fleet_overview(_tenant_context(tenant_id))
    edge_node = next(node for node in response.nodes if node.hostname == "jetson-1")

    assert edge_node.status == "stale"
    assert response.camera_workers[0].lifecycle_owner == "edge_supervisor"
    assert response.camera_workers[0].runtime_status == "stale"


@pytest.mark.asyncio
async def test_fleet_overview_edge_assignment_overrides_central_operations_owner() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-portable-1",
        public_key="seed",
        version="portable-demo",
        last_seen_at=datetime.now(tz=UTC),
    )
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=edge.id,
        name="Room1",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={},
        source_capability=None,
        frame_skip=1,
        fps_cap=25,
    )
    edge_report = EdgeNodeHardwareReport(
        id=uuid4(),
        tenant_id=tenant_id,
        edge_node_id=edge.id,
        supervisor_id="jetson-portable-1",
        reported_at=datetime.now(tz=UTC),
        host_profile="linux-aarch64-nvidia-jetson",
        os_name="linux",
        machine_arch="aarch64",
        cpu_model=None,
        cpu_cores=6,
        memory_total_mb=7607,
        accelerators=["cuda", "tensorrt"],
        provider_capabilities={"TensorrtExecutionProvider": True},
        observed_performance=[],
        thermal_state=None,
        report_hash="c" * 64,
        created_at=datetime.now(tz=UTC),
    )
    session_factory = _FakeSessionFactory([(edge, site)], [(camera, site)], [], [], [])
    service = OperationsService(
        session_factory=session_factory,
        settings=Settings(_env_file=None),
        supervisor_operations=_FakeSupervisorOperations(edge_reports={edge.id: edge_report}),
        runtime_configuration=_FakeRuntimeConfiguration(
            {
                "lifecycle_owner": "central_supervisor",
                "supervisor_mode": "polling",
                "restart_policy": "on_failure",
            }
        ),
    )

    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    worker = response.camera_workers[0]
    assert worker.node_id == edge.id
    assert worker.lifecycle_owner == "edge_supervisor"
    assert OperationsLifecycleAction.START in worker.allowed_lifecycle_actions
    assert worker.detail == (
        "Assigned edge node overrides central supervisor ownership; "
        "edge supervisor owns this worker process."
    )


@pytest.mark.asyncio
async def test_fleet_overview_removed_assignment_suppresses_worker_owner() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-portable-1",
        public_key="seed",
        version="portable-demo",
        last_seen_at=datetime.now(tz=UTC),
    )
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=edge.id,
        name="Room1",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={},
        source_capability=None,
        frame_skip=1,
        fps_cap=25,
    )
    assignment = WorkerAssignment(
        id=uuid4(),
        tenant_id=tenant_id,
        camera_id=camera.id,
        edge_node_id=None,
        desired_state=WorkerDesiredState.NOT_DESIRED.value,
        active=True,
        supersedes_assignment_id=None,
        assigned_by_subject="operator-1",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    edge_report = EdgeNodeHardwareReport(
        id=uuid4(),
        tenant_id=tenant_id,
        edge_node_id=edge.id,
        supervisor_id="jetson-portable-1",
        reported_at=datetime.now(tz=UTC),
        host_profile="linux-aarch64-nvidia-jetson",
        os_name="linux",
        machine_arch="aarch64",
        cpu_model=None,
        cpu_cores=6,
        memory_total_mb=7607,
        accelerators=["cuda", "tensorrt"],
        provider_capabilities={"TensorrtExecutionProvider": True},
        observed_performance=[],
        thermal_state=None,
        report_hash="d" * 64,
        created_at=datetime.now(tz=UTC),
    )
    session_factory = _FakeSessionFactory([(edge, site)], [(camera, site)], [], [], [])
    service = OperationsService(
        session_factory=session_factory,
        settings=Settings(_env_file=None),
        supervisor_operations=_FakeSupervisorOperations(
            assignments_by_camera={camera.id: assignment},
            edge_reports={edge.id: edge_report},
        ),
        runtime_configuration=_FakeRuntimeConfiguration(
            {
                "lifecycle_owner": "central_supervisor",
                "supervisor_mode": "polling",
                "restart_policy": "on_failure",
            }
        ),
    )

    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    worker = response.camera_workers[0]
    assert response.summary.desired_workers == 0
    assert worker.desired_state == WorkerDesiredState.NOT_DESIRED
    assert worker.node_id is None
    assert worker.node_hostname is None
    assert worker.lifecycle_owner == "none"
    assert worker.allowed_lifecycle_actions == []
    assert worker.detail == (
        "Worker assignment removed. Assign a worker location to enable processing again."
    )
    assert worker.assignment is not None
    assert worker.assignment.active is True


@pytest.mark.asyncio
async def test_fleet_overview_uses_deployment_heartbeat_status_and_hides_duplicate_edges() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    now = datetime.now(tz=UTC)
    stale_time = now - timedelta(hours=3)
    stale_duplicate_edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-portable-1",
        public_key="old-seed",
        version="portable-demo",
        last_seen_at=stale_time,
    )
    active_edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-portable-1",
        public_key="new-seed",
        version="portable-demo",
        last_seen_at=stale_time,
    )
    deployment_nodes = _FakeDeploymentNodes(
        [
            _deployment_node(
                tenant_id,
                node_kind=DeploymentNodeKind.CENTRAL,
                supervisor_id="100",
                hostname="central-container",
                last_service_reported_at=now,
            ),
            _deployment_node(
                tenant_id,
                node_kind=DeploymentNodeKind.EDGE,
                supervisor_id="jetson-portable-1",
                hostname="edge-container",
                edge_node_id=active_edge.id,
                last_service_reported_at=now,
            ),
        ]
    )
    session_factory = _FakeSessionFactory(
        [(stale_duplicate_edge, site), (active_edge, site)],
        [],
        [],
        [],
        [],
    )
    service = OperationsService(
        session_factory=session_factory,
        settings=Settings(_env_file=None),
        deployment_nodes=deployment_nodes,
    )

    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    assert [(node.hostname, node.status) for node in response.nodes] == [
        ("central", "healthy"),
        ("jetson-portable-1", "healthy"),
    ]
    assert response.summary.offline_nodes == 0
    assert response.summary.stale_nodes == 0


@pytest.mark.asyncio
async def test_supervisor_edge_site_scope_allows_credential_for_any_edge_node_on_site() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    stale_duplicate_edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-orin-old",
        public_key="old-seed",
        version="portable-demo",
        last_seen_at=datetime.now(tz=UTC) - timedelta(days=2),
    )
    active_edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-orin-1",
        public_key="new-seed",
        version="portable-demo",
        last_seen_at=datetime.now(tz=UTC),
    )
    deployment_node_id = uuid4()
    deployment_node = DeploymentNode(
        id=deployment_node_id,
        tenant_id=tenant_id,
        edge_node_id=active_edge.id,
        supervisor_id="jetson-orin-1",
        node_kind=DeploymentNodeKind.EDGE,
        hostname="jetson-orin-1",
        install_status=DeploymentInstallStatus.HEALTHY,
        credential_status=DeploymentCredentialStatus.ACTIVE,
        service_manager=DeploymentServiceManager.SYSTEMD,
        service_status="running",
        version="portable-demo",
        os_name="linux",
        host_profile="linux-aarch64-nvidia-jetson",
        diagnostics={},
    )
    session_factory = _FakeSessionFactory(
        [stale_duplicate_edge.id],
        get_map={
            (DeploymentNode, deployment_node_id): deployment_node,
            (EdgeNode, active_edge.id): active_edge,
            (Site, site.id): site,
        },
    )
    service = OperationsService(session_factory=session_factory, settings=Settings(_env_file=None))

    await service.assert_supervisor_edge_site_scope(
        _supervisor_tenant_context(tenant_id, deployment_node_id),
        site.id,
    )


@pytest.mark.asyncio
async def test_supervisor_edge_site_scope_blocks_other_sites() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    other_site = _site(tenant_id)
    edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-orin-1",
        public_key="seed",
        version="portable-demo",
        last_seen_at=datetime.now(tz=UTC),
    )
    deployment_node_id = uuid4()
    deployment_node = DeploymentNode(
        id=deployment_node_id,
        tenant_id=tenant_id,
        edge_node_id=edge.id,
        supervisor_id="jetson-orin-1",
        node_kind=DeploymentNodeKind.EDGE,
        hostname="jetson-orin-1",
        install_status=DeploymentInstallStatus.HEALTHY,
        credential_status=DeploymentCredentialStatus.ACTIVE,
        service_manager=DeploymentServiceManager.SYSTEMD,
        service_status="running",
        version="portable-demo",
        os_name="linux",
        host_profile="linux-aarch64-nvidia-jetson",
        diagnostics={},
    )
    session_factory = _FakeSessionFactory(
        get_map={
            (DeploymentNode, deployment_node_id): deployment_node,
            (EdgeNode, edge.id): edge,
            (Site, site.id): site,
        },
    )
    service = OperationsService(session_factory=session_factory, settings=Settings(_env_file=None))

    with pytest.raises(HTTPException) as exc_info:
        await service.assert_supervisor_edge_site_scope(
            _supervisor_tenant_context(tenant_id, deployment_node_id),
            other_site.id,
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_fleet_overview_does_not_attach_central_hardware_to_unassigned_edge_camera() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=None,
        name="Lab Camera 2",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={},
        source_capability=None,
        frame_skip=1,
        fps_cap=25,
    )
    central_report = EdgeNodeHardwareReport(
        id=uuid4(),
        tenant_id=tenant_id,
        edge_node_id=None,
        supervisor_id="central-imac",
        reported_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        host_profile="macos-x86_64-intel",
        os_name="darwin",
        machine_arch="x86_64",
        cpu_model=None,
        cpu_cores=8,
        memory_total_mb=65536,
        accelerators=["coreml", "cpu"],
        provider_capabilities={"CoreMLExecutionProvider": True},
        observed_performance=[],
        thermal_state=None,
        report_hash="a" * 64,
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )
    session_factory = _FakeSessionFactory([], [(camera, site)], [], [], [])
    service = OperationsService(
        session_factory=session_factory,
        settings=Settings(_env_file=None),
        supervisor_operations=_FakeSupervisorOperations(central_report=central_report),
    )

    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    worker = response.camera_workers[0]
    assert worker.processing_mode is ProcessingMode.EDGE
    assert worker.node_id is None
    assert worker.latest_hardware_report is None


@pytest.mark.asyncio
async def test_fleet_overview_allows_central_start_when_supervisor_hardware_is_fresh() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=None,
        name="Camera 1",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={},
        source_capability=None,
        frame_skip=1,
        fps_cap=25,
    )
    central_report = EdgeNodeHardwareReport(
        id=uuid4(),
        tenant_id=tenant_id,
        edge_node_id=None,
        supervisor_id="central-imac",
        reported_at=datetime.now(tz=UTC),
        host_profile="macos-x86_64-intel",
        os_name="darwin",
        machine_arch="x86_64",
        cpu_model=None,
        cpu_cores=8,
        memory_total_mb=65536,
        accelerators=["coreml", "cpu"],
        provider_capabilities={"CoreMLExecutionProvider": True},
        observed_performance=[],
        thermal_state=None,
        report_hash="b" * 64,
        created_at=datetime.now(tz=UTC),
    )
    session_factory = _FakeSessionFactory([], [(camera, site)], [], [], [])
    service = OperationsService(
        session_factory=session_factory,
        settings=Settings(_env_file=None),
        supervisor_operations=_FakeSupervisorOperations(central_report=central_report),
        runtime_configuration=_FakeRuntimeConfiguration(
            {
                "lifecycle_owner": "central_supervisor",
                "supervisor_mode": "polling",
                "restart_policy": "on_failure",
            }
        ),
    )

    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    worker = response.camera_workers[0]
    assert response.mode == "supervised"
    assert worker.lifecycle_owner == "central_supervisor"
    assert worker.dev_run_command is None
    assert OperationsLifecycleAction.START in worker.allowed_lifecycle_actions
    assert worker.detail == "Central Supervisor owns this worker process."


@pytest.mark.asyncio
async def test_model_admission_uses_preferred_backend_as_effective_selection() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    central_report = EdgeNodeHardwareReport(
        id=uuid4(),
        tenant_id=tenant_id,
        edge_node_id=None,
        supervisor_id="central-imac",
        reported_at=datetime.now(tz=UTC),
        host_profile="linux-aarch64-nvidia-jetson",
        os_name="linux",
        machine_arch="aarch64",
        cpu_model=None,
        cpu_cores=8,
        memory_total_mb=32768,
        accelerators=["tensorrt"],
        provider_capabilities={"TensorrtExecutionProvider": True},
        observed_performance=[],
        thermal_state=None,
        report_hash="e" * 64,
        created_at=datetime.now(tz=UTC),
    )
    supervisor_operations = _FakeSupervisorOperations(central_report=central_report)
    service = OperationsService(
        session_factory=_FakeSessionFactory(),
        settings=Settings(_env_file=None),
        supervisor_operations=supervisor_operations,
    )

    response = await service.evaluate_worker_model_admission(
        _tenant_context(tenant_id),
        camera_id,
        WorkerModelAdmissionRequest(
            camera_id=uuid4(),
            model_name="YOLO",
            selected_backend=None,
            preferred_backend="tensorrt_engine",
            stream_profile={"width": 1280, "height": 720, "fps": 10},
        ),
    )

    assert response.camera_id == camera_id
    assert response.status is ModelAdmissionStatus.SUPPORTED
    assert response.selected_backend == "tensorrt_engine"
    assert response.recommended_backend == "tensorrt_engine"
    assert supervisor_operations.model_admission_payload is not None
    assert supervisor_operations.model_admission_payload.selected_backend == "tensorrt_engine"


class _FakeEdgeService:
    def __init__(self) -> None:
        self.payload = None

    async def register_edge_node(self, tenant_context, payload):  # noqa: ANN001
        self.payload = payload
        from argus.api.contracts import EdgeRegisterResponse

        return EdgeRegisterResponse(
            edge_node_id=uuid4(),
            api_key="edge_secret_once",
            nats_nkey_seed="nats_secret_once",
            subjects=["evt.tracking.node"],
            mediamtx_url="http://mediamtx:9997",
            overlay_network_hints={"nats_url": "nats://nats:4222"},
        )


class _FakeSupervisorOperations:
    def __init__(
        self,
        *,
        assignments_by_camera: dict[UUID, WorkerAssignment] | None = None,
        central_report: EdgeNodeHardwareReport | None = None,
        edge_reports: dict[UUID, EdgeNodeHardwareReport] | None = None,
    ) -> None:
        self.assignments_by_camera = assignments_by_camera or {}
        self.central_report = central_report
        self.edge_reports = edge_reports or {}
        self.model_admission_payload: WorkerModelAdmissionRequest | None = None

    async def latest_assignments_by_camera(self, **kwargs):  # noqa: ANN003
        camera_ids = kwargs.get("camera_ids", [])
        return {
            camera_id: assignment
            for camera_id, assignment in self.assignments_by_camera.items()
            if camera_id in camera_ids
        }

    async def latest_runtime_reports_by_camera(self, **kwargs):  # noqa: ANN003
        del kwargs
        return {}

    async def latest_lifecycle_requests_by_camera(self, **kwargs):  # noqa: ANN003
        del kwargs
        return {}

    async def latest_hardware_reports_by_edge_node(self, **kwargs):  # noqa: ANN003
        edge_node_ids = kwargs.get("edge_node_ids", [])
        return {
            edge_node_id: report
            for edge_node_id, report in self.edge_reports.items()
            if edge_node_id in edge_node_ids
        }

    async def latest_hardware_report_for_central(self, **kwargs):  # noqa: ANN003
        del kwargs
        return self.central_report

    async def latest_model_admissions_by_camera(self, **kwargs):  # noqa: ANN003
        del kwargs
        return {}

    async def record_model_admission_decision(self, **kwargs):  # noqa: ANN003
        payload = kwargs["payload"]
        decision = kwargs["decision"]
        self.model_admission_payload = payload
        now = datetime.now(tz=UTC)
        return WorkerModelAdmissionReport(
            id=uuid4(),
            tenant_id=kwargs["tenant_id"],
            camera_id=payload.camera_id,
            edge_node_id=payload.edge_node_id,
            assignment_id=payload.assignment_id,
            hardware_report_id=kwargs["hardware_report_id"],
            model_id=payload.model_id,
            model_name=payload.model_name,
            model_capability=payload.model_capability,
            runtime_artifact_id=payload.runtime_artifact_id,
            runtime_selection_profile_id=payload.runtime_selection_profile_id,
            stream_profile=dict(payload.stream_profile),
            status=decision.status,
            selected_backend=payload.selected_backend,
            recommended_model_id=decision.recommended_model_id,
            recommended_model_name=decision.recommended_model_name,
            recommended_runtime_profile_id=decision.recommended_runtime_profile_id,
            recommended_backend=decision.recommended_backend,
            rationale=decision.rationale,
            constraints=dict(decision.constraints),
            evaluated_at=now,
            created_at=now,
        )


class _FakeRuntimeConfiguration:
    def __init__(self, config: dict[str, object]) -> None:
        self.config = config

    async def resolve_profile_for_runtime(self, *args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return SimpleNamespace(config=self.config)


@pytest.mark.asyncio
async def test_create_bootstrap_material_wraps_edge_registration() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    session_factory = _FakeSessionFactory()
    edge_service = _FakeEdgeService()
    service = OperationsService(
        session_factory=session_factory,
        settings=Settings(_env_file=None),
        edge_service=edge_service,
    )

    response = await service.create_bootstrap_material(
        _tenant_context(tenant_id),
        FleetBootstrapRequest(site_id=site.id, hostname="edge-kit-01", version="0.1.0"),
    )

    assert edge_service.payload is not None
    assert edge_service.payload.hostname == "edge-kit-01"
    assert response.api_key == "edge_secret_once"
    assert "<token>" not in response.dev_compose_command
    assert "<camera-id>" not in response.dev_compose_command
    assert "grant_type=password&client_id=argus-cli" in response.dev_compose_command
    assert 'ARGUS_API_BEARER_TOKEN="$TOKEN"' in response.dev_compose_command
    assert 'ARGUS_API_BASE_URL="${ARGUS_API_BASE_URL:?' in response.dev_compose_command
    assert 'ARGUS_DB_URL="${ARGUS_DB_URL:?' in response.dev_compose_command
    assert 'ARGUS_MINIO_ENDPOINT="${ARGUS_MINIO_ENDPOINT:?' in response.dev_compose_command
    assert (
        "docker compose -f infra/docker-compose.edge.yml up inference-worker"
        in response.dev_compose_command
    )
    assert response.supervisor_environment["ARGUS_EDGE_NODE_ID"] == str(response.edge_node_id)
