from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from argus.api.contracts import TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import ProcessingMode, RoleEnum, TrackerType
from argus.models.tables import Camera
from argus.services.app import StreamService
from argus.streaming.webrtc import StreamMode


class _DummyMediaMTXClient:
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
async def test_stream_service_resolves_central_native_delivery_without_privacy_to_passthrough(
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

    assert access.mode is StreamMode.PASSTHROUGH
    assert access.path_name == f"cameras/{camera_id}/passthrough"


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
