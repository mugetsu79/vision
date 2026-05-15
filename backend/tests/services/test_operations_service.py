from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    DeploymentNodeResponse,
    FleetBootstrapRequest,
    TenantContext,
)
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DeploymentServiceManager,
    IncidentRuleSeverity,
    OperationsLifecycleAction,
    ProcessingMode,
    RoleEnum,
    RuleAction,
    TrackerType,
)
from argus.models.tables import (
    Camera,
    DetectionRule,
    EdgeNode,
    EdgeNodeHardwareReport,
    RuleEvent,
    Site,
)
from argus.services.app import OperationsService


class _FakeResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows

    def scalars(self) -> _FakeResult:
        return self


class _FakeSession:
    def __init__(self, result_sets: list[list[object]]) -> None:
        self._result_sets = result_sets

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _FakeResult:  # noqa: ANN001
        return _FakeResult(self._result_sets.pop(0))


class _FakeSessionFactory:
    def __init__(self, *result_sets: list[object]) -> None:
        self.result_sets = [list(result_set) for result_set in result_sets]

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.result_sets)


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
    assert worker.lifecycle_owner == "central_supervisor"
    assert worker.dev_run_command is None
    assert OperationsLifecycleAction.START in worker.allowed_lifecycle_actions
    assert worker.detail == "Central Supervisor owns this worker process."


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
        central_report: EdgeNodeHardwareReport | None = None,
        edge_reports: dict[UUID, EdgeNodeHardwareReport] | None = None,
    ) -> None:
        self.central_report = central_report
        self.edge_reports = edge_reports or {}

    async def latest_assignments_by_camera(self, **kwargs):  # noqa: ANN003
        del kwargs
        return {}

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
