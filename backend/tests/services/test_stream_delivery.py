from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from argus.api.contracts import (
    BrowserDeliverySettings,
    StreamDeliveryProfileConfig,
    TenantContext,
)
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import (
    OperatorConfigProfileKind,
    OperatorConfigScope,
    OperatorConfigValidationStatus,
    ProcessingMode,
    RoleEnum,
    TrackerType,
)
from argus.models.tables import Camera, OperatorConfigProfile
from argus.services.app import StreamService


class _DummyMediaMTXClient:
    async def ensure_path(self, path_name: str, *, source: str, source_on_demand: bool) -> None:
        return None

    async def close(self) -> None:
        return None


class _DummyNegotiator:
    async def close(self) -> None:
        return None


class _EmptyScalars:
    def all(self) -> list[object]:
        return []


class _EmptyResult:
    def scalars(self) -> _EmptyScalars:
        return _EmptyScalars()


class _StreamDeliverySession:
    def __init__(self, profile: OperatorConfigProfile) -> None:
        self.profile = profile

    async def execute(self, query: object) -> _EmptyResult:
        del query
        return _EmptyResult()

    async def get(self, model: object, key: object) -> OperatorConfigProfile | None:
        del model
        return self.profile if key == self.profile.id else None


class _StreamDeliverySessionFactory:
    def __init__(self, profile: OperatorConfigProfile) -> None:
        self.profile = profile

    def __call__(self):
        @asynccontextmanager
        async def _session_context():
            yield _StreamDeliverySession(self.profile)

        return _session_context()


def _tenant_context(tenant_id: UUID) -> TenantContext:
    return TenantContext(
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


def _camera(camera_id: UUID, *, delivery_profile_id: UUID) -> Camera:
    return Camera(
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
        browser_delivery=BrowserDeliverySettings(
            default_profile="720p10",
            delivery_profile_id=delivery_profile_id,
        ).model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
    )


def _transport_profile(
    *,
    tenant_id: UUID,
    delivery_mode: str,
    public_base_url: str = "https://streams.example.com",
) -> OperatorConfigProfile:
    return OperatorConfigProfile(
        id=uuid4(),
        tenant_id=tenant_id,
        site_id=None,
        edge_node_id=None,
        camera_id=None,
        kind=OperatorConfigProfileKind.STREAM_DELIVERY,
        scope=OperatorConfigScope.TENANT,
        name=f"{delivery_mode.upper()} delivery",
        slug=f"{delivery_mode}-delivery",
        enabled=True,
        is_default=False,
        config={
            "delivery_mode": delivery_mode,
            "public_base_url": public_base_url,
        },
        validation_status=OperatorConfigValidationStatus.VALID,
        validation_message="Validated by test.",
        validated_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        config_hash="e" * 64,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("delivery_mode", "requested_route", "url_attribute", "blocked_route"),
    [
        ("webrtc", "webrtc", "whep_url", "hls"),
        ("hls", "hls", "hls_url", "webrtc"),
        ("mjpeg", "mjpeg", "mjpeg_url", "webrtc"),
    ],
)
async def test_forced_stream_delivery_mode_allows_matching_route_and_blocks_others(
    monkeypatch: pytest.MonkeyPatch,
    delivery_mode: str,
    requested_route: str,
    url_attribute: str,
    blocked_route: str,
) -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    profile = _transport_profile(
        tenant_id=tenant_id,
        delivery_mode=delivery_mode,
    )
    camera = _camera(camera_id, delivery_profile_id=profile.id)

    async def fake_load_camera(session, requested_tenant_id, requested_camera_id):
        assert requested_tenant_id == tenant_id
        assert requested_camera_id == camera_id
        return camera

    monkeypatch.setattr("argus.services.app._load_camera", fake_load_camera)

    service = StreamService(
        session_factory=_StreamDeliverySessionFactory(profile),
        mediamtx=_DummyMediaMTXClient(),
        negotiator=_DummyNegotiator(),
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    access = await service._resolve_stream_access(
        _tenant_context(tenant_id),
        camera_id,
        requested_route=requested_route,
    )

    assert getattr(access, url_attribute).startswith("https://streams.example.com/")

    with pytest.raises(HTTPException) as exc_info:
        await service._resolve_stream_access(
            _tenant_context(tenant_id),
            camera_id,
            requested_route=blocked_route,
        )

    assert exc_info.value.status_code == 409
    assert f"configured for {delivery_mode}" in str(exc_info.value.detail).lower()


@pytest.mark.parametrize("delivery_mode", ["webrtc", "hls", "mjpeg"])
def test_forced_stream_delivery_modes_require_public_base_url(delivery_mode: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        StreamDeliveryProfileConfig.model_validate({"delivery_mode": delivery_mode})

    assert "public base url" in str(exc_info.value).lower()
