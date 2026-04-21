from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient, Request
from httpx import Response as HTTPXResponse

from argus.api.contracts import StreamOfferRequest, StreamOfferResponse, TenantContext
from argus.api.v1 import streams as streams_module
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, get_current_media_user, get_current_user
from argus.main import create_app
from argus.models.enums import RoleEnum


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
async def test_fetch_hls_upstream_retries_playlist_404s_before_succeeding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "http://mediamtx.internal:8888/cameras/test/preview/index.m3u8?jwt=test-token"
    responses = [
        HTTPXResponse(status_code=404, request=Request("GET", url)),
        HTTPXResponse(
            status_code=200,
            request=Request("GET", url),
            content=b"#EXTM3U\n",
            headers={"content-type": "application/vnd.apple.mpegurl"},
        ),
    ]
    requested_urls: list[str] = []
    sleep_delays: list[float] = []

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 10.0

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, requested_url: str) -> HTTPXResponse:
            requested_urls.append(requested_url)
            return responses.pop(0)

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    monkeypatch.setattr(streams_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(streams_module.asyncio, "sleep", fake_sleep)

    payload, headers = await streams_module._fetch_hls_upstream(url)

    assert payload == b"#EXTM3U\n"
    assert headers["content-type"] == "application/vnd.apple.mpegurl"
    assert requested_urls == [url, url]
    assert sleep_delays == [0.25]


@pytest.mark.asyncio
async def test_fetch_hls_upstream_raises_404_for_unready_playlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "http://mediamtx.internal:8888/cameras/test/preview/index.m3u8?jwt=test-token"

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 10.0

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, requested_url: str) -> HTTPXResponse:
            return HTTPXResponse(status_code=404, request=Request("GET", requested_url))

    async def fake_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(streams_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(streams_module.asyncio, "sleep", fake_sleep)

    with pytest.raises(HTTPException) as exc_info:
        await streams_module._fetch_hls_upstream(url)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Stream playlist is not ready yet."


@pytest.mark.asyncio
async def test_hls_route_proxies_playlist_and_rewrites_media_uris(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            b"#EXTM3U\n"
            b"#EXT-X-VERSION:9\n"
            b"#EXT-X-MAP:URI=\"init.mp4\"\n"
            b"#EXTINF:1.0,\n"
            b"segment0.mp4\n",
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
async def test_hls_asset_route_rewrites_nested_playlist_uris(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            f"{camera_id}/preview/video1_stream.m3u8?jwt=test-token&_HLS_msn=7"
        )
        return (
            b"#EXTM3U\n"
            b"#EXT-X-MAP:URI=\"17ecb351ac5d_video1_init.mp4\"\n"
            b"#EXTINF:1.0,\n"
            b"17ecb351ac5d_video1_seg0.mp4\n",
            {"content-type": "application/vnd.apple.mpegurl"},
        )

    monkeypatch.setattr(streams_module, "_fetch_hls_upstream", fake_fetch)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            f"/api/v1/streams/{camera_id}/hls/video1_stream.m3u8",
            params={"access_token": "viewer-token", "_HLS_msn": "7"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.apple.mpegurl")
    assert (
        f"/api/v1/streams/{camera_id}/hls/17ecb351ac5d_video1_init.mp4?access_token=viewer-token"
        in response.text
    )
    assert (
        f"/api/v1/streams/{camera_id}/hls/17ecb351ac5d_video1_seg0.mp4?access_token=viewer-token"
        in response.text
    )


@pytest.mark.asyncio
async def test_hls_asset_route_does_not_forward_frontend_jwt_to_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            f"{camera_id}/preview/video1_stream.m3u8?jwt=test-token&_HLS_msn=7"
        )
        return (
            b"#EXTM3U\n"
            b"#EXT-X-MAP:URI=\"17ecb351ac5d_video1_init.mp4\"\n"
            b"#EXTINF:1.0,\n"
            b"17ecb351ac5d_video1_seg0.mp4\n",
            {"content-type": "application/vnd.apple.mpegurl"},
        )

    monkeypatch.setattr(streams_module, "_fetch_hls_upstream", fake_fetch)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            f"/api/v1/streams/{camera_id}/hls/video1_stream.m3u8",
            params={
                "access_token": "viewer-token",
                "jwt": "frontend-jwt",
                "session_token": "9",
                "_HLS_msn": "7",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.apple.mpegurl")


@pytest.mark.asyncio
async def test_hls_asset_route_proxies_signed_media_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
