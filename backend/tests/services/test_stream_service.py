from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from jose import jwt

from argus.api.contracts import TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import ProcessingMode, RoleEnum, TrackerType
from argus.models.tables import Camera
from argus.services.app import StreamService
from argus.streaming.webrtc import StreamMode


class _DummyMediaMTXClient:
    def __init__(self) -> None:
        self.ensured_paths: list[tuple[str, str, bool]] = []

    async def ensure_path(self, path_name: str, *, source: str, source_on_demand: bool) -> None:
        self.ensured_paths.append((path_name, source, source_on_demand))

    async def close(self) -> None:
        return None


class _DummyNegotiator:
    async def close(self) -> None:
        return None


class _DummySessionFactory:
    def __call__(self):
        @asynccontextmanager
        async def _session_context():
            yield object()

        return _session_context()


@pytest.mark.asyncio
async def test_stream_service_resolves_edge_native_delivery_to_passthrough_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    tenant_id = uuid4()
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=uuid4(),
        name="CAMERA1",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={"blur_faces": False, "blur_plates": False},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=25,
    )

    async def fake_load_camera(session, requested_tenant_id, requested_camera_id):
        assert requested_tenant_id == tenant_id
        assert requested_camera_id == camera_id
        return camera

    monkeypatch.setattr("argus.services.app._load_camera", fake_load_camera)

    service = StreamService(
        session_factory=_DummySessionFactory(),
        mediamtx=_DummyMediaMTXClient(),
        negotiator=_DummyNegotiator(),
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-dev",
            email="admin-dev@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )

    access = await service._resolve_stream_access(tenant_context, camera_id)

    assert access.mode is StreamMode.PASSTHROUGH
    assert access.path_name == f"cameras/{camera_id}/passthrough"


@pytest.mark.asyncio
async def test_stream_service_relays_edge_passthrough_via_master_mediamtx_when_edge_base_is_configured(  # noqa: E501
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    edge_node_id = uuid4()
    tenant_id = uuid4()
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=edge_node_id,
        name="CAMERA2",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={"blur_faces": False, "blur_plates": False},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=25,
    )

    async def fake_load_camera(session, requested_tenant_id, requested_camera_id):
        assert requested_tenant_id == tenant_id
        assert requested_camera_id == camera_id
        return camera

    monkeypatch.setattr("argus.services.app._load_camera", fake_load_camera)

    mediamtx = _DummyMediaMTXClient()
    service = StreamService(
        session_factory=_DummySessionFactory(),
        mediamtx=mediamtx,
        negotiator=_DummyNegotiator(),
        settings=Settings(
            _env_file=None,
            enable_startup_services=False,
            edge_mediamtx_rtsp_base_urls={
                str(edge_node_id): "rtsp://jetson.local:8554",
            },
            mediamtx_rtsp_base_url="rtsp://imac.local:8554",
            mediamtx_webrtc_base_url="http://imac.local:8889",
            mediamtx_hls_base_url="http://imac.local:8888",
            mediamtx_mjpeg_base_url="http://imac.local:8888",
        ),
    )

    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-dev",
            email="admin-dev@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )

    access = await service._resolve_stream_access(tenant_context, camera_id)

    path_name = f"cameras/{camera_id}/passthrough"
    assert access.mode is StreamMode.PASSTHROUGH
    assert access.path_name == path_name
    assert access.rtsp_url == f"rtsp://imac.local:8554/{path_name}"
    assert access.whep_url == f"http://imac.local:8889/{path_name}/whep"
    assert mediamtx.ensured_paths[0][0] == path_name
    assert mediamtx.ensured_paths[0][2] is True
    source_url = mediamtx.ensured_paths[0][1]
    split_source = urlsplit(source_url)
    assert f"{split_source.scheme}://{split_source.netloc}{split_source.path}" == (
        f"rtsp://jetson.local:8554/{path_name}"
    )
    token = parse_qs(split_source.query)["jwt"][0]
    claims = jwt.get_unverified_claims(token)
    assert claims["mediamtx_permissions"] == [{"action": "read", "path": path_name}]


@pytest.mark.asyncio
async def test_stream_service_reuses_fresh_edge_passthrough_relay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    edge_node_id = uuid4()
    tenant_id = uuid4()
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=edge_node_id,
        name="CAMERA2",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={"blur_faces": False, "blur_plates": False},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=25,
    )

    async def fake_load_camera(session, requested_tenant_id, requested_camera_id):
        assert requested_tenant_id == tenant_id
        assert requested_camera_id == camera_id
        return camera

    monkeypatch.setattr("argus.services.app._load_camera", fake_load_camera)

    mediamtx = _DummyMediaMTXClient()
    service = StreamService(
        session_factory=_DummySessionFactory(),
        mediamtx=mediamtx,
        negotiator=_DummyNegotiator(),
        settings=Settings(
            _env_file=None,
            enable_startup_services=False,
            edge_mediamtx_rtsp_base_urls={"*": "rtsp://jetson.local:8554"},
        ),
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-dev",
            email="admin-dev@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )

    await service._resolve_stream_access(tenant_context, camera_id)
    await service._resolve_stream_access(tenant_context, camera_id)

    assert len(mediamtx.ensured_paths) == 1


@pytest.mark.asyncio
async def test_stream_service_resolves_central_native_delivery_without_privacy_to_clean_processed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    tenant_id = uuid4()
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="CAMERA1",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={"blur_faces": False, "blur_plates": False},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=25,
    )

    async def fake_load_camera(session, requested_tenant_id, requested_camera_id):
        assert requested_tenant_id == tenant_id
        assert requested_camera_id == camera_id
        return camera

    monkeypatch.setattr("argus.services.app._load_camera", fake_load_camera)

    service = StreamService(
        session_factory=_DummySessionFactory(),
        mediamtx=_DummyMediaMTXClient(),
        negotiator=_DummyNegotiator(),
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-dev",
            email="admin-dev@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )

    access = await service._resolve_stream_access(tenant_context, camera_id)

    assert access.mode is StreamMode.ANNOTATED_WHIP
    assert access.path_name == f"cameras/{camera_id}/annotated"


@pytest.mark.asyncio
async def test_stream_service_routes_central_native_delivery_with_privacy_to_processed_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    tenant_id = uuid4()
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="CAMERA1",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={"blur_faces": True, "blur_plates": False},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=25,
    )

    async def fake_load_camera(session, requested_tenant_id, requested_camera_id):
        assert requested_tenant_id == tenant_id
        assert requested_camera_id == camera_id
        return camera

    monkeypatch.setattr("argus.services.app._load_camera", fake_load_camera)

    service = StreamService(
        session_factory=_DummySessionFactory(),
        mediamtx=_DummyMediaMTXClient(),
        negotiator=_DummyNegotiator(),
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-dev",
            email="admin-dev@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )

    access = await service._resolve_stream_access(tenant_context, camera_id)

    assert access.mode is StreamMode.ANNOTATED_WHIP
    assert access.path_name == f"cameras/{camera_id}/annotated"
