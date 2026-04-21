from __future__ import annotations

from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import HTTPException
from httpx import AsyncClient, Request, Response
from jose import jwt

import argus.streaming.webrtc as webrtc_module
from argus.models.enums import ProcessingMode
from argus.streaming.mediamtx import StreamMode
from argus.streaming.webrtc import (
    MJPEG_CONTENT_TYPE,
    ConcurrencyLimitExceeded,
    MediaMTXTokenIssuer,
    UserConcurrencyLimiter,
    WebRTCNegotiator,
    _open_rtsp_mjpeg_stream,
    resolve_stream_access,
)


def test_resolve_stream_access_returns_annotated_variant_for_central_processing() -> None:
    camera_id = uuid4()

    access = resolve_stream_access(
        camera_id=camera_id,
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        privacy={"blur_faces": True, "blur_plates": True},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    assert access.mode is StreamMode.ANNOTATED_WHIP
    assert access.path_name == f"cameras/{camera_id}/annotated"
    assert access.rtsp_url == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/annotated"
    assert access.whep_url == f"http://mediamtx.internal:8889/cameras/{camera_id}/annotated/whep"
    assert access.hls_url == f"http://mediamtx.internal:8888/cameras/{camera_id}/annotated/index.m3u8"
    assert access.mjpeg_url == f"http://mediamtx.internal:8890/cameras/{camera_id}/annotated/mjpeg"


def test_resolve_stream_access_disables_passthrough_when_edge_privacy_is_required() -> None:
    camera_id = uuid4()

    access = resolve_stream_access(
        camera_id=camera_id,
        processing_mode=ProcessingMode.EDGE,
        edge_node_id=uuid4(),
        privacy={"blur_faces": True, "blur_plates": False},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    assert access.mode is StreamMode.FILTERED_PREVIEW
    assert access.path_name == f"cameras/{camera_id}/preview"


def test_mediamtx_token_issuer_emits_jwks_and_path_scoped_read_tokens() -> None:
    issuer = MediaMTXTokenIssuer()
    camera_id = uuid4()
    access = resolve_stream_access(
        camera_id=camera_id,
        processing_mode=ProcessingMode.EDGE,
        edge_node_id=uuid4(),
        privacy={"blur_faces": False, "blur_plates": False},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    token = issuer.issue_read_token(
        subject="viewer-1",
        camera_id=camera_id,
        access=access,
    )
    claims = jwt.get_unverified_claims(token)
    jwks = issuer.jwks()

    assert claims["iss"] == issuer.issuer
    assert claims["aud"] == issuer.audience
    assert claims["sub"] == "viewer-1"
    assert claims["mediamtx_permissions"] == [
        {"action": "read", "path": f"cameras/{camera_id}/passthrough"}
    ]
    assert jwks["keys"][0]["kid"] == issuer.key_id


@pytest.mark.asyncio
async def test_webrtc_negotiator_posts_offer_to_whep_with_short_lived_bearer_token() -> None:
    requests: list[tuple[str, str, str, str]] = []
    issuer = MediaMTXTokenIssuer()
    access = resolve_stream_access(
        camera_id=uuid4(),
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        privacy={"blur_faces": True, "blur_plates": True},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    async def handler(request: Request) -> Response:
        requests.append(
            (
                request.method,
                str(request.url),
                request.headers["Authorization"],
                request.content.decode("utf-8"),
            )
        )
        return Response(
            201,
            headers={"Content-Type": "application/sdp"},
            text="v=0\r\no=mediamtx 1 1 IN IP4 127.0.0.1\r\n",
        )

    negotiator = WebRTCNegotiator(
        token_issuer=issuer,
        http_client=AsyncClient(transport=_transport(handler)),
    )

    sdp_answer = await negotiator.negotiate_offer(
        access=access,
        camera_id=UUID(str(access.camera_id)),
        subject="viewer-1",
        sdp_offer="v=0\r\no=browser 1 1 IN IP4 127.0.0.1\r\n",
    )

    assert sdp_answer.startswith("v=0")
    assert requests[0][0] == "POST"
    assert requests[0][1] == access.whep_url
    assert requests[0][3].startswith("v=0")
    token = requests[0][2].removeprefix("Bearer ")
    claims = jwt.get_unverified_claims(token)
    assert claims["mediamtx_permissions"] == [
        {"action": "read", "path": access.path_name}
    ]

    await negotiator.close()


@pytest.mark.asyncio
async def test_webrtc_negotiator_translates_missing_whep_path_to_http_404() -> None:
    issuer = MediaMTXTokenIssuer()
    access = resolve_stream_access(
        camera_id=uuid4(),
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        privacy={"blur_faces": True, "blur_plates": True},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    async def handler(request: Request) -> Response:
        return Response(404, request=request, text="not found")

    negotiator = WebRTCNegotiator(
        token_issuer=issuer,
        http_client=AsyncClient(transport=_transport(handler)),
    )

    with pytest.raises(HTTPException) as exc_info:
        await negotiator.negotiate_offer(
            access=access,
            camera_id=UUID(str(access.camera_id)),
            subject="viewer-1",
            sdp_offer="v=0\r\no=browser 1 1 IN IP4 127.0.0.1\r\n",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "WebRTC stream is not ready yet."

    await negotiator.close()


@pytest.mark.asyncio
async def test_webrtc_negotiator_translates_upstream_request_errors_to_http_502() -> None:
    issuer = MediaMTXTokenIssuer()
    access = resolve_stream_access(
        camera_id=uuid4(),
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        privacy={"blur_faces": True, "blur_plates": True},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    async def transport_handler(request: Request) -> Response:
        raise httpx.ConnectError("connection failed", request=request)

    negotiator = WebRTCNegotiator(
        token_issuer=issuer,
        http_client=AsyncClient(transport=_transport(transport_handler)),
    )

    with pytest.raises(HTTPException) as exc_info:
        await negotiator.negotiate_offer(
            access=access,
            camera_id=UUID(str(access.camera_id)),
            subject="viewer-1",
            sdp_offer="v=0\r\no=browser 1 1 IN IP4 127.0.0.1\r\n",
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Unable to negotiate upstream WebRTC stream."

    await negotiator.close()


@pytest.mark.asyncio
async def test_webrtc_negotiator_builds_rtsp_url_for_mjpeg_bridge() -> None:
    issuer = MediaMTXTokenIssuer()
    access = resolve_stream_access(
        camera_id=uuid4(),
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        privacy={"blur_faces": True, "blur_plates": True},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )
    opened_urls: list[str] = []

    async def fake_mjpeg_stream_factory(rtsp_url_source):
        rtsp_url = rtsp_url_source() if callable(rtsp_url_source) else rtsp_url_source
        opened_urls.append(rtsp_url)
        from argus.streaming.webrtc import UpstreamProxyStream

        return UpstreamProxyStream(byte_iterator=_empty_chunks())

    negotiator = WebRTCNegotiator(
        token_issuer=issuer,
        mjpeg_stream_factory=fake_mjpeg_stream_factory,
    )

    await negotiator.open_mjpeg_stream(
        access=access,
        camera_id=UUID(str(access.camera_id)),
        subject="viewer-1",
    )

    assert len(opened_urls) == 1
    split_url = urlsplit(opened_urls[0])
    assert f"{split_url.scheme}://{split_url.netloc}{split_url.path}" == access.rtsp_url
    token = parse_qs(split_url.query)["jwt"][0]
    claims = jwt.get_unverified_claims(token)
    assert claims["mediamtx_permissions"] == [
        {"action": "read", "path": access.path_name}
    ]

    await negotiator.close()


@pytest.mark.asyncio
async def test_open_rtsp_mjpeg_stream_retries_during_startup_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_cv2 = object()
    open_attempts: list[str] = []
    sleep_delays: list[float] = []

    class FakeCapture:
        def __init__(self) -> None:
            self.release_calls = 0

        def release(self) -> None:
            self.release_calls += 1

    capture = FakeCapture()

    def fake_load_cv2() -> object:
        return fake_cv2

    def fake_open_rtsp_capture(rtsp_url: str, cv2: object) -> FakeCapture:
        assert cv2 is fake_cv2
        open_attempts.append(rtsp_url)
        if len(open_attempts) < 3:
            raise RuntimeError("stream not ready")
        return capture

    def fake_read_rtsp_frame(current_capture: FakeCapture) -> object | None:
        assert current_capture is capture
        return object()

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    monkeypatch.setattr(webrtc_module, "_load_cv2", fake_load_cv2)
    monkeypatch.setattr(webrtc_module, "_open_rtsp_capture", fake_open_rtsp_capture)
    monkeypatch.setattr(webrtc_module, "_read_rtsp_frame", fake_read_rtsp_frame)
    monkeypatch.setattr(webrtc_module.asyncio, "sleep", fake_sleep)

    stream = await _open_rtsp_mjpeg_stream("rtsp://mediamtx.internal:8554/cameras/test/annotated")

    assert stream.media_type == MJPEG_CONTENT_TYPE
    assert open_attempts == [
        "rtsp://mediamtx.internal:8554/cameras/test/annotated",
        "rtsp://mediamtx.internal:8554/cameras/test/annotated",
        "rtsp://mediamtx.internal:8554/cameras/test/annotated",
    ]
    assert sleep_delays == [0.25, 0.25]


@pytest.mark.asyncio
async def test_open_rtsp_mjpeg_stream_reconnects_after_runtime_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_cv2 = object()
    sleep_delays: list[float] = []
    open_attempts: list[str] = []

    class FakeCapture:
        def __init__(self, name: str) -> None:
            self.name = name
            self.release_calls = 0

        def release(self) -> None:
            self.release_calls += 1

    initial_capture = FakeCapture("initial")
    recovered_capture = FakeCapture("recovered")
    frame_reads = {
        initial_capture.name: [b"frame-one", None],
        recovered_capture.name: [b"frame-two"],
    }

    def fake_load_cv2() -> object:
        return fake_cv2

    def fake_open_rtsp_capture(rtsp_url: str, cv2: object) -> FakeCapture:
        assert cv2 is fake_cv2
        open_attempts.append(rtsp_url)
        if len(open_attempts) == 1:
            return initial_capture
        if len(open_attempts) in (2, 3):
            raise RuntimeError("annotated stream offline")
        return recovered_capture

    def fake_read_rtsp_frame(current_capture: FakeCapture) -> bytes | None:
        remaining_frames = frame_reads[current_capture.name]
        if not remaining_frames:
            return None
        return remaining_frames.pop(0)

    def fake_encode_mjpeg_frame(_cv2: object, frame: bytes) -> bytes:
        return frame

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    monkeypatch.setattr(webrtc_module, "_load_cv2", fake_load_cv2)
    monkeypatch.setattr(webrtc_module, "_open_rtsp_capture", fake_open_rtsp_capture)
    monkeypatch.setattr(webrtc_module, "_read_rtsp_frame", fake_read_rtsp_frame)
    monkeypatch.setattr(webrtc_module, "_encode_mjpeg_frame", fake_encode_mjpeg_frame)
    monkeypatch.setattr(webrtc_module.asyncio, "sleep", fake_sleep)

    stream = await _open_rtsp_mjpeg_stream("rtsp://mediamtx.internal:8554/cameras/test/annotated")
    iterator = stream.iter_bytes()

    assert await anext(iterator) == b"frame-one"
    assert await anext(iterator) == b"frame-two"

    await iterator.aclose()

    assert sleep_delays == [0.25, 0.5]
    assert open_attempts == [
        "rtsp://mediamtx.internal:8554/cameras/test/annotated",
        "rtsp://mediamtx.internal:8554/cameras/test/annotated",
        "rtsp://mediamtx.internal:8554/cameras/test/annotated",
        "rtsp://mediamtx.internal:8554/cameras/test/annotated",
    ]
    assert initial_capture.release_calls == 1


@pytest.mark.asyncio
async def test_open_rtsp_mjpeg_stream_refreshes_rtsp_url_on_runtime_reconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_cv2 = object()
    issued_urls = iter(
        (
            "rtsp://mediamtx.internal:8554/cameras/test/annotated?jwt=initial",
            "rtsp://mediamtx.internal:8554/cameras/test/annotated?jwt=retry-one",
            "rtsp://mediamtx.internal:8554/cameras/test/annotated?jwt=retry-two",
            "rtsp://mediamtx.internal:8554/cameras/test/annotated?jwt=recovered",
        )
    )
    open_attempts: list[str] = []

    class FakeCapture:
        def __init__(self, name: str) -> None:
            self.name = name

        def release(self) -> None:
            return None

    initial_capture = FakeCapture("initial")
    recovered_capture = FakeCapture("recovered")
    frame_reads = {
        initial_capture.name: [b"frame-one", None],
        recovered_capture.name: [b"frame-two"],
    }

    def fake_load_cv2() -> object:
        return fake_cv2

    def next_url() -> str:
        return next(issued_urls)

    def fake_open_rtsp_capture(rtsp_url: str, cv2: object) -> FakeCapture:
        assert cv2 is fake_cv2
        open_attempts.append(rtsp_url)
        if rtsp_url.endswith("jwt=initial"):
            return initial_capture
        if rtsp_url.endswith(("jwt=retry-one", "jwt=retry-two")):
            raise RuntimeError("stale token or stream not ready")
        if rtsp_url.endswith("jwt=recovered"):
            return recovered_capture
        raise AssertionError(f"Unexpected RTSP URL: {rtsp_url}")

    def fake_read_rtsp_frame(current_capture: FakeCapture) -> bytes | None:
        remaining_frames = frame_reads[current_capture.name]
        if not remaining_frames:
            return None
        return remaining_frames.pop(0)

    def fake_encode_mjpeg_frame(_cv2: object, frame: bytes) -> bytes:
        return frame

    async def fake_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(webrtc_module, "_load_cv2", fake_load_cv2)
    monkeypatch.setattr(webrtc_module, "_open_rtsp_capture", fake_open_rtsp_capture)
    monkeypatch.setattr(webrtc_module, "_read_rtsp_frame", fake_read_rtsp_frame)
    monkeypatch.setattr(webrtc_module, "_encode_mjpeg_frame", fake_encode_mjpeg_frame)
    monkeypatch.setattr(webrtc_module.asyncio, "sleep", fake_sleep)

    stream = await _open_rtsp_mjpeg_stream(next_url)
    iterator = stream.iter_bytes()

    assert await anext(iterator) == b"frame-one"
    assert await anext(iterator) == b"frame-two"

    await iterator.aclose()

    assert open_attempts == [
        "rtsp://mediamtx.internal:8554/cameras/test/annotated?jwt=initial",
        "rtsp://mediamtx.internal:8554/cameras/test/annotated?jwt=retry-one",
        "rtsp://mediamtx.internal:8554/cameras/test/annotated?jwt=retry-two",
        "rtsp://mediamtx.internal:8554/cameras/test/annotated?jwt=recovered",
    ]


@pytest.mark.asyncio
async def test_user_concurrency_limiter_blocks_eleventh_session() -> None:
    limiter = UserConcurrencyLimiter(limit=10)

    for _ in range(10):
        await limiter.acquire("viewer-1")

    with pytest.raises(ConcurrencyLimitExceeded):
        await limiter.acquire("viewer-1")

    await limiter.release("viewer-1")
    await limiter.acquire("viewer-1")


def _transport(handler):
    async def wrapped(request: Request) -> Response:
        response = handler(request)
        if isinstance(response, Response):
            return response
        return await response

    from httpx import MockTransport

    return MockTransport(wrapped)


async def _empty_chunks() -> AsyncIterator[bytes]:
    if False:
        yield b""
