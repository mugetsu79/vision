from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import StreamOfferRequest, StreamOfferResponse, TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, get_current_media_user, get_current_user
from argus.main import create_app
from argus.models.enums import RoleEnum
from argus.api.v1 import streams as streams_module


def _sample_user() -> AuthenticatedUser:
    tenant_id = uuid4()
    return AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(tenant_id),
        claims={},
    )


def _tenant_context(user: AuthenticatedUser) -> TenantContext:
    return TenantContext(
        tenant_id=UUID(str(user.tenant_context)),
        tenant_slug=user.realm,
        user=user,
    )


class FakeTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        return self.context


@dataclass(slots=True)
class FakeProxyStream:
    media_type: str
    headers: dict[str, str]
    chunks: tuple[bytes, ...]

    async def iter_bytes(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk


class FakeStreamService:
    async def create_offer(
        self,
        context: TenantContext,
        *,
        camera_id: UUID,
        offer: StreamOfferRequest,
    ) -> StreamOfferResponse:
        return StreamOfferResponse(
            camera_id=camera_id,
            sdp_answer="v=0\r\no=mediamtx 1 1 IN IP4 127.0.0.1\r\n",
        )

    async def get_hls_playlist_url(
        self,
        context: TenantContext,
        *,
        camera_id: UUID,
    ) -> str:
        return f"http://mediamtx.internal:8888/cameras/{camera_id}/preview/index.m3u8?jwt=test-token"

    async def open_mjpeg_proxy(
        self,
        context: TenantContext,
        *,
        camera_id: UUID,
        user: AuthenticatedUser,
    ) -> FakeProxyStream:
        return FakeProxyStream(
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store"},
            chunks=(
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\nframe-one\r\n",
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\nframe-two\r\n",
            ),
        )


@pytest.mark.asyncio
async def test_hls_route_proxies_playlist_and_rewrites_media_uris(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user()
    context = _tenant_context(user)
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)
    app.state.services = SimpleNamespace(
        tenancy=FakeTenancyService(context),
        streams=FakeStreamService(),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_media_user] = lambda: user
    camera_id = uuid4()

    async def fake_fetch(url: str) -> tuple[bytes, dict[str, str]]:
        assert (
            url
            == "http://mediamtx.internal:8888/cameras/"
            f"{camera_id}/preview/index.m3u8?jwt=test-token&_HLS_msn=42&_HLS_part=2"
        )
        return (
            (
                "#EXTM3U\n"
                "#EXT-X-VERSION:9\n"
                "#EXT-X-MAP:URI=\"init.mp4\"\n"
                "#EXTINF:1.0,\n"
                "segment0.mp4\n"
            ).encode("utf-8"),
            {"content-type": "application/vnd.apple.mpegurl"},
        )

    monkeypatch.setattr(streams_module, "_fetch_hls_upstream", fake_fetch)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.get(
            f"/api/v1/streams/{camera_id}/hls.m3u8",
            params={
                "access_token": "viewer-token",
                "tenant_id": str(context.tenant_id),
                "_HLS_msn": "42",
                "_HLS_part": "2",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.apple.mpegurl")
    assert (
        f"/api/v1/streams/{camera_id}/hls/init.mp4?access_token=viewer-token&tenant_id={context.tenant_id}"
        in response.text
    )
    assert (
        f"/api/v1/streams/{camera_id}/hls/segment0.mp4?access_token=viewer-token&tenant_id={context.tenant_id}"
        in response.text
    )


@pytest.mark.asyncio
async def test_hls_route_accepts_access_token_query_for_browser_media_requests() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)
    app.state.services = SimpleNamespace(
        tenancy=FakeTenancyService(context),
        streams=FakeStreamService(),
    )
    app.state.security = SimpleNamespace(validate_token=AsyncMock(return_value=user))
    camera_id = uuid4()

    async def fake_fetch(url: str) -> tuple[bytes, dict[str, str]]:
        assert url.endswith("index.m3u8?jwt=test-token")
        return (b"#EXTM3U\n", {"content-type": "application/vnd.apple.mpegurl"})

    from argus.api.v1 import streams as streams_module

    app.state.security = SimpleNamespace(validate_token=AsyncMock(return_value=user))
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(streams_module, "_fetch_hls_upstream", fake_fetch)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            response = await client.get(
                f"/api/v1/streams/{camera_id}/hls.m3u8",
                params={"access_token": "viewer-token"},
            )
    finally:
        monkeypatch.undo()

    assert response.status_code == 200
    assert response.text == "#EXTM3U\n"


@pytest.mark.asyncio
async def test_hls_asset_route_proxies_signed_media_resource(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _sample_user()
    context = _tenant_context(user)
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)
    app.state.services = SimpleNamespace(
        tenancy=FakeTenancyService(context),
        streams=FakeStreamService(),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_media_user] = lambda: user
    camera_id = uuid4()

    async def fake_fetch(url: str) -> tuple[bytes, dict[str, str]]:
        assert (
            url
            == f"http://mediamtx.internal:8888/cameras/{camera_id}/preview/segment0.mp4?jwt=test-token"
        )
        return (b"segment-bytes", {"content-type": "video/mp4"})

    monkeypatch.setattr(streams_module, "_fetch_hls_upstream", fake_fetch)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/v1/streams/{camera_id}/hls/segment0.mp4")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")
    assert response.content == b"segment-bytes"


@pytest.mark.asyncio
async def test_video_feed_route_proxies_mjpeg_content() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)
    app.state.services = SimpleNamespace(
        tenancy=FakeTenancyService(context),
        streams=FakeStreamService(),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_media_user] = lambda: user
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/video_feed/{camera_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert response.headers["cache-control"] == "no-store"
    assert b"frame-one" in response.content
    assert b"frame-two" in response.content


@pytest.mark.asyncio
async def test_video_feed_route_accepts_access_token_query_for_browser_media_requests() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)
    app.state.services = SimpleNamespace(
        tenancy=FakeTenancyService(context),
        streams=FakeStreamService(),
    )
    app.state.security = SimpleNamespace(validate_token=AsyncMock(return_value=user))
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            f"/video_feed/{camera_id}",
            params={"access_token": "viewer-token"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert b"frame-one" in response.content


@pytest.mark.asyncio
async def test_webrtc_test_page_is_available() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/webrtc-test.html")

    assert response.status_code == 200
    assert "RTCPeerConnection" in response.text
    assert "/api/v1/streams/" in response.text
