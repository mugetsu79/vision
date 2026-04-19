from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient, Request, Response
from jose import jwt

from argus.models.enums import ProcessingMode
from argus.streaming.mediamtx import StreamMode
from argus.streaming.webrtc import (
    ConcurrencyLimitExceeded,
    MediaMTXTokenIssuer,
    UserConcurrencyLimiter,
    WebRTCNegotiator,
    resolve_stream_access,
)


def test_resolve_stream_access_returns_annotated_variant_for_central_processing() -> None:
    camera_id = uuid4()

    access = resolve_stream_access(
        camera_id=camera_id,
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        privacy={"blur_faces": True, "blur_plates": True},
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    assert access.mode is StreamMode.ANNOTATED_WHIP
    assert access.path_name == f"cameras/{camera_id}/annotated"
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
