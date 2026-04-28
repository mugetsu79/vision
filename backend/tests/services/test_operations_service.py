from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from argus.api.contracts import FleetBootstrapRequest, TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import ProcessingMode, RoleEnum, TrackerType
from argus.models.tables import Camera, EdgeNode, Site
from argus.services.app import OperationsService


class _FakeResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


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
    session_factory = _FakeSessionFactory([], [(camera, site)])
    service = OperationsService(session_factory=session_factory, settings=Settings(_env_file=None))
    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    assert response.mode == "manual_dev"
    assert response.summary.desired_workers == 1
    assert response.camera_workers[0].camera_name == "Lobby"
    assert response.camera_workers[0].desired_state == "manual"
    assert response.camera_workers[0].runtime_status == "not_reported"
    assert "argus.inference.engine --camera-id" in response.camera_workers[0].dev_run_command
    assert response.delivery_diagnostics[0].source_capability is not None


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
    session_factory = _FakeSessionFactory([(edge, site)], [(camera, site)])
    service = OperationsService(session_factory=session_factory, settings=Settings(_env_file=None))
    response = await service.get_fleet_overview(_tenant_context(tenant_id))
    edge_node = next(node for node in response.nodes if node.hostname == "jetson-1")

    assert edge_node.status == "stale"
    assert response.camera_workers[0].lifecycle_owner == "edge_supervisor"
    assert response.camera_workers[0].runtime_status == "stale"


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
    assert (
        "docker compose -f infra/docker-compose.edge.yml up inference-worker"
        in response.dev_compose_command
    )
    assert response.supervisor_environment["ARGUS_EDGE_NODE_ID"] == str(response.edge_node_id)
