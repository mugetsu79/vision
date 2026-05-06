from __future__ import annotations

import asyncio
import base64
import importlib
import os
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import UUID, uuid4

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, status
from jose import jwt  # type: ignore[import-untyped]

from argus.compat import UTC
from argus.models.enums import ProcessingMode
from argus.streaming.mediamtx import StreamMode
from argus.vision.capture_options import (
    _FFMPEG_ANALYZE_DURATION_US,
    _FFMPEG_PROBE_SIZE,
    _FFMPEG_RTSP_TIMEOUT_US,
    _OPENCV_CAPTURE_OPEN_TIMEOUT_MS,
    _OPENCV_CAPTURE_READ_TIMEOUT_MS,
)

if TYPE_CHECKING:
    from argus.core.config import Settings


DEFAULT_MEDIAMTX_DEV_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDkqxELjSR/UZg/
nIFGRKKB3OAbSY88GpXC7ymQ98gNPlj7lIX7qrCoFjfnjaqzgqmf73fpeBStFnAj
v99yfaEjFKPkW9RBK4XvWGMbuwViYWss+sLq+LkxmhwGOdjVzObPUJdRwYOb/dBD
30BMnboNZ74K8DpDtJb5BgloRXvRJdJBZhrdp/4tyCTv01y4tWJSCReL68P5KU+v
Ex4XJx1DND2OLBcL4M8FCWN8p1VVqSqAPkm9F+9L0m1v41JAYwJ5CIp9Og489Eg+
sgmdKaa7qNeg+lc2HHuLiWIiydoCJii8DNShN1DfxtS8UqaOeaCvfe0lkcyXaMSu
AX/DW3RXAgMBAAECggEAI+Wc8+YbhtHYJ5LvPQjfmqkCFME2ofX/G6PFhTNOAueO
OtRP4jhN/4fEDUQmj4P2vUZFBJrWuBiv0FTkhDR88Xph2M1M+VFr9wJg8Jn/7Y1N
22Oe6hnTTMTyGvdwIZlx2bVqQ9SFT3LdWRejdZjvJlU/treL61QJZ/IO06vQv6i3
DwOnnE+JRKHD239s1koPGtuQMbe6+uizn3B5ujq48kdmxvQzRpU7DUvB+QbTORAP
5FZRxMef0lkyB8bf7EK7PK5b4Ws3KtpC06fUKr6LEPq4j8NRWBBpVLZA4na6nzc4
raLcm8okLc/9k5iEAYnkoaeLGV60kWzpVHsYxAOy9QKBgQD/6c2F0gfDfJg4hRQR
tEzL0F4wOQlOEgACI08nuOqCcuVihIHMY1NO8s/Sn3KGE38K4BG8MfzbfYLmciuX
VOLAhpenijxP+C/4wAXGhdsbWhKGJI5Ni+KBYwwBCigwrdmSo3GXOIfg2ShTUVgv
lV9gTCBoXe6DOOIN2PSIi05q3QKBgQDkvuaN0mmEmk+Gbon8Q//hAQbdlmkY6XIw
PiYhOVHpoWQPA3hLyrVlkOeS8WqRMeJN3Wfd+Z4nc6DhiWV5fbBNcOTNX3Y+vvTU
/FP09fzJtVLY3tU9f8QBa8EstUIyIx0VT0PVGIblUBT1n4/jdQ4rtp+cGwm15auT
eeocaXxmwwKBgGOM+ewytd5v228xJYt1jeJDHkC4D0yVZ/ds8N/M6TzxoRXf4fY2
NTQi9IFEkXJipyr92yhQccKYYpFunFJ0LPkj4l7EQY4CR/cGC7kcXQ2YzlfsZIb6
AZS/iO3mm5fEKT0H46olzYXENBGlNR7dhoqZUooG8D+PozAr04RCXLDpAoGBAJzP
XX/1sY5Mtp2io4dDGmOl743yMYP5bOUzhbIa+FNf5xb/uvTCNs40ovux8estNkVI
tY6PM2M6OhzCssSxbC36aW98tLPY9kAX5no0M6IXYn73a1lof/a1Zsz+SS3TsnlM
SGUKFleXKXckdmBoe1luLUa3plWC57cGyX3Gtpg/AoGADptWit7m6dRYeF+6VYIu
asfoZR+s0DFHcaUKNkdq45xDctKlEJW3fn4QpqX3QXapTYM/X65C6gHnDjeP8RNV
hen+6DNpPkO2h1Cts+a5+hSktutoyJJqJTUzInbabRqV6JZrWCzObvLcwZ5rsGDw
0BSCO5Y9XJ1g34uzpaLsNns=
-----END PRIVATE KEY-----"""


@dataclass(slots=True, frozen=True)
class StreamAccess:
    camera_id: UUID
    mode: StreamMode
    path_name: str
    rtsp_url: str
    whep_url: str
    hls_url: str
    mjpeg_url: str


@dataclass(slots=True)
class UpstreamProxyStream:
    response: httpx.Response | None = None
    byte_iterator: AsyncIterator[bytes] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    media_type_override: str | None = None
    on_close: Callable[[], Awaitable[None]] | None = None

    @property
    def media_type(self) -> str:
        if self.media_type_override is not None:
            return self.media_type_override
        if self.response is None:
            return "application/octet-stream"
        content_type = self.response.headers.get("Content-Type")
        if content_type is None:
            return "application/octet-stream"
        return str(content_type)

    async def iter_bytes(self) -> AsyncIterator[bytes]:
        try:
            if self.byte_iterator is not None:
                async for chunk in self.byte_iterator:
                    yield chunk
            elif self.response is not None:
                async for chunk in self.response.aiter_bytes():
                    yield chunk
        finally:
            if self.response is not None:
                await self.response.aclose()
            if self.on_close is not None:
                await self.on_close()


class ConcurrencyLimitExceeded(RuntimeError):
    """Raised when a user exceeds the allowed concurrent proxy sessions."""


class UserConcurrencyLimiter:
    def __init__(self, *, limit: int) -> None:
        self.limit = limit
        self._counts: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> None:
        async with self._lock:
            current = self._counts[key]
            if current >= self.limit:
                raise ConcurrencyLimitExceeded(key)
            self._counts[key] = current + 1

    async def release(self, key: str) -> None:
        async with self._lock:
            current = self._counts.get(key, 0)
            if current <= 1:
                self._counts.pop(key, None)
                return
            self._counts[key] = current - 1


RtspUrlSource = str | Callable[[], str]
MjpegStreamFactory = Callable[[RtspUrlSource], Awaitable[UpstreamProxyStream]]


class MediaMTXTokenIssuer:
    def __init__(
        self,
        *,
        private_key_pem: str = DEFAULT_MEDIAMTX_DEV_PRIVATE_KEY_PEM,
        issuer: str = "argus-mediamtx",
        audience: str = "mediamtx",
        key_id: str = "argus-mediamtx-dev",
        ttl_seconds: int = 60,
    ) -> None:
        self.private_key_pem = private_key_pem
        self.issuer = issuer
        self.audience = audience
        self.key_id = key_id
        self.ttl_seconds = ttl_seconds
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise TypeError("MediaMTX JWT signing requires an RSA private key.")
        self._private_key = private_key

    @classmethod
    def from_settings(cls, settings: Settings) -> MediaMTXTokenIssuer:
        private_key_pem = DEFAULT_MEDIAMTX_DEV_PRIVATE_KEY_PEM
        if settings.mediamtx_jwt_private_key_pem is not None:
            private_key_pem = settings.mediamtx_jwt_private_key_pem.get_secret_value()
        return cls(
            private_key_pem=private_key_pem,
            issuer=settings.mediamtx_jwt_issuer,
            audience=settings.mediamtx_jwt_audience,
            key_id=settings.mediamtx_jwt_key_id,
            ttl_seconds=settings.mediamtx_jwt_ttl_seconds,
        )

    def issue_read_token(
        self,
        *,
        subject: str,
        camera_id: UUID,
        access: StreamAccess,
    ) -> str:
        return self._issue_token(
            subject=subject,
            camera_id=camera_id,
            permissions=[{"action": "read", "path": access.path_name}],
        )

    def issue_publish_token(
        self,
        *,
        subject: str,
        camera_id: UUID,
        path_name: str,
    ) -> str:
        return self._issue_token(
            subject=subject,
            camera_id=camera_id,
            permissions=[{"action": "publish", "path": path_name}],
        )

    def issue_internal_read_token(
        self,
        *,
        camera_id: UUID,
        path_name: str,
        ttl_seconds: int | None = None,
    ) -> str:
        """Long-lived read token for internal service-to-service RTSP reads.

        Browser-facing tokens use the default short TTL so that a leaked
        token is short-lived. Workers hold a single RTSP session for hours
        and reconnect over an unbounded period; they need a token that
        outlives MediaMTX reconnect backoff. Pass an explicit ttl_seconds
        to override the issuer default.
        """
        return self._issue_token(
            subject=f"worker-{camera_id}",
            camera_id=camera_id,
            permissions=[{"action": "read", "path": path_name}],
            ttl_seconds_override=ttl_seconds,
        )

    def build_hls_url(
        self,
        *,
        subject: str,
        camera_id: UUID,
        access: StreamAccess,
    ) -> str:
        token = self.issue_read_token(
            subject=subject,
            camera_id=camera_id,
            access=access,
        )
        return _append_query_parameter(access.hls_url, key="jwt", value=token)

    def build_rtsp_url(
        self,
        *,
        subject: str,
        camera_id: UUID,
        access: StreamAccess,
    ) -> str:
        token = self.issue_read_token(
            subject=subject,
            camera_id=camera_id,
            access=access,
        )
        return _append_query_parameter(access.rtsp_url, key="jwt", value=token)

    def build_internal_rtsp_url(
        self,
        *,
        camera_id: UUID,
        path_name: str,
        rtsp_url: str,
        ttl_seconds: int | None = None,
    ) -> str:
        token = self.issue_internal_read_token(
            camera_id=camera_id,
            path_name=path_name,
            ttl_seconds=ttl_seconds,
        )
        return _append_query_parameter(rtsp_url, key="jwt", value=token)

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        public_numbers = self._private_key.public_key().public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": self.key_id,
                    "use": "sig",
                    "alg": "RS256",
                    "n": _b64url_uint(public_numbers.n),
                    "e": _b64url_uint(public_numbers.e),
                }
            ]
        }

    def _issue_token(
        self,
        *,
        subject: str,
        camera_id: UUID,
        permissions: list[dict[str, str]],
        ttl_seconds_override: int | None = None,
    ) -> str:
        now = datetime.now(tz=UTC)
        ttl = ttl_seconds_override if ttl_seconds_override is not None else self.ttl_seconds
        claims = {
            "sub": subject,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ttl)).timestamp()),
            "jti": str(uuid4()),
            "camera_id": str(camera_id),
            "mediamtx_permissions": permissions,
        }
        return str(
            jwt.encode(
                claims,
                self.private_key_pem,
                algorithm="RS256",
                headers={"kid": self.key_id},
            )
        )


class WebRTCNegotiator:
    def __init__(
        self,
        *,
        token_issuer: MediaMTXTokenIssuer,
        http_client: httpx.AsyncClient | None = None,
        mjpeg_stream_factory: MjpegStreamFactory | None = None,
    ) -> None:
        self.token_issuer = token_issuer
        self._owned_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(timeout=10.0)
        self._mjpeg_stream_factory = mjpeg_stream_factory or _open_rtsp_mjpeg_stream

    async def close(self) -> None:
        if self._owned_client:
            await self._http_client.aclose()

    async def negotiate_offer(
        self,
        *,
        access: StreamAccess,
        camera_id: UUID,
        subject: str,
        sdp_offer: str,
    ) -> str:
        token = self.token_issuer.issue_read_token(
            subject=subject,
            camera_id=camera_id,
            access=access,
        )
        try:
            response = await self._http_client.post(
                access.whep_url,
                content=sdp_offer.encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/sdp",
                    "Content-Type": "application/sdp",
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise _translate_webrtc_upstream_status_error(exc) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to negotiate upstream WebRTC stream.",
            ) from exc
        return response.text

    async def open_mjpeg_stream(
        self,
        *,
        access: StreamAccess,
        camera_id: UUID,
        subject: str,
    ) -> UpstreamProxyStream:
        def rtsp_url_factory() -> str:
            return self.token_issuer.build_rtsp_url(
                subject=subject,
                camera_id=camera_id,
                access=access,
            )

        return await self._mjpeg_stream_factory(rtsp_url_factory)


def resolve_stream_access(
    *,
    camera_id: UUID,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
    stream_kind: str,
    privacy: Mapping[str, object] | None,
    rtsp_base_url: str,
    webrtc_base_url: str,
    hls_base_url: str,
    mjpeg_base_url: str,
    mjpeg_path_template: str = "{base}/{path}/mjpeg",
) -> StreamAccess:
    privacy_required = _privacy_requires_filtering(privacy)
    central_delivery = _uses_central_delivery(
        processing_mode=processing_mode,
        edge_node_id=edge_node_id,
    )
    requested_passthrough = stream_kind == StreamMode.PASSTHROUGH.value

    if requested_passthrough and not privacy_required:
        mode = StreamMode.PASSTHROUGH
        variant = "passthrough"
    elif privacy_required and not central_delivery:
        mode = StreamMode.FILTERED_PREVIEW
        variant = "preview"
    else:
        mode = StreamMode.ANNOTATED_WHIP
        variant = "annotated"

    path_name = f"cameras/{camera_id}/{variant}"
    rtsp_base = rtsp_base_url.rstrip("/")
    webrtc_base = webrtc_base_url.rstrip("/")
    hls_base = hls_base_url.rstrip("/")
    mjpeg_base = mjpeg_base_url.rstrip("/")
    mjpeg_url = mjpeg_path_template.format(base=mjpeg_base, path=path_name)
    return StreamAccess(
        camera_id=camera_id,
        mode=mode,
        path_name=path_name,
        rtsp_url=f"{rtsp_base}/{path_name}",
        whep_url=f"{webrtc_base}/{path_name}/whep",
        hls_url=f"{hls_base}/{path_name}/index.m3u8",
        mjpeg_url=mjpeg_url,
    )


def _append_query_parameter(url: str, *, key: str, value: str) -> str:
    split_url = urlsplit(url)
    query = split_url.query
    suffix = urlencode({key: value})
    combined = suffix if query == "" else f"{query}&{suffix}"
    return urlunsplit(
        (split_url.scheme, split_url.netloc, split_url.path, combined, split_url.fragment)
    )


def _translate_webrtc_upstream_status_error(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == status.HTTP_404_NOT_FOUND:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WebRTC stream is not ready yet.",
        )

    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unable to negotiate upstream WebRTC stream.",
    )


MJPEG_BOUNDARY = "argus-frame"
MJPEG_CONTENT_TYPE = f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}"
_MJPEG_FRAME_PREFIX = f"--{MJPEG_BOUNDARY}\r\nContent-Type: image/jpeg\r\n\r\n".encode()
_MJPEG_STARTUP_RETRY_DELAYS_SECONDS = (0.25, 0.25, 0.5, 1.0, 1.0)
_MJPEG_RUNTIME_RETRY_DELAYS_SECONDS = (0.25, 0.5, 1.0, 2.0, 2.0, 5.0)
_OPENCV_FFMPEG_CAPTURE_OPTIONS = (
    f"rtsp_transport;tcp|analyzeduration;{_FFMPEG_ANALYZE_DURATION_US}"
    f"|probesize;{_FFMPEG_PROBE_SIZE}|timeout;{_FFMPEG_RTSP_TIMEOUT_US}"
)


async def _open_rtsp_mjpeg_stream(rtsp_url_source: RtspUrlSource) -> UpstreamProxyStream:
    cv2 = _load_cv2()
    capture, first_frame = await _open_initial_rtsp_capture(rtsp_url_source, cv2)

    async def iterator() -> AsyncIterator[bytes]:
        current_capture: Any = capture
        current_frame: Any = first_frame
        try:
            while True:
                payload = await asyncio.to_thread(_encode_mjpeg_frame, cv2, current_frame)
                if payload is not None:
                    yield payload

                next_frame = await asyncio.to_thread(_read_rtsp_frame, current_capture)
                if next_frame is not None:
                    current_frame = next_frame
                    continue

                await asyncio.to_thread(current_capture.release)
                current_capture, current_frame = await _reopen_rtsp_capture(
                    rtsp_url_source,
                    cv2,
                )
        finally:
            await asyncio.to_thread(current_capture.release)

    return UpstreamProxyStream(
        byte_iterator=iterator(),
        media_type_override=MJPEG_CONTENT_TYPE,
    )


async def _open_initial_rtsp_capture(rtsp_url_source: RtspUrlSource, cv2: Any) -> tuple[Any, Any]:
    last_error: RuntimeError | None = None

    for attempt in range(len(_MJPEG_STARTUP_RETRY_DELAYS_SECONDS) + 1):
        rtsp_url = _resolve_rtsp_url(rtsp_url_source)
        try:
            capture = await asyncio.to_thread(_open_rtsp_capture, rtsp_url, cv2)
        except RuntimeError as exc:
            last_error = exc
        else:
            first_frame = await asyncio.to_thread(_read_rtsp_frame, capture)
            if first_frame is not None:
                return capture, first_frame
            await asyncio.to_thread(capture.release)
            last_error = RuntimeError("Unable to read first RTSP frame for MJPEG bridge.")

        if attempt >= len(_MJPEG_STARTUP_RETRY_DELAYS_SECONDS):
            assert last_error is not None
            raise last_error
        await asyncio.sleep(_MJPEG_STARTUP_RETRY_DELAYS_SECONDS[attempt])

    raise RuntimeError("Unable to initialize MJPEG bridge.")


async def _reopen_rtsp_capture(rtsp_url: RtspUrlSource, cv2: Any) -> tuple[Any, Any]:
    attempt = 0

    while True:
        current_rtsp_url = _resolve_rtsp_url(rtsp_url)
        try:
            capture = await asyncio.to_thread(_open_rtsp_capture, current_rtsp_url, cv2)
        except RuntimeError:
            pass
        else:
            reopened_frame = await asyncio.to_thread(_read_rtsp_frame, capture)
            if reopened_frame is not None:
                return capture, reopened_frame
            await asyncio.to_thread(capture.release)

        delay_seconds = _MJPEG_RUNTIME_RETRY_DELAYS_SECONDS[
            min(attempt, len(_MJPEG_RUNTIME_RETRY_DELAYS_SECONDS) - 1)
        ]
        attempt += 1
        await asyncio.sleep(delay_seconds)


def _resolve_rtsp_url(rtsp_url_source: RtspUrlSource) -> str:
    if callable(rtsp_url_source):
        return rtsp_url_source()
    return rtsp_url_source


def _open_rtsp_capture(rtsp_url: str, cv2: Any) -> Any:
    if "OPENCV_FFMPEG_CAPTURE_OPTIONS" not in os.environ:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = _OPENCV_FFMPEG_CAPTURE_OPTIONS
    capture = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    _configure_rtsp_capture_timeouts(capture, cv2)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Unable to open RTSP stream {rtsp_url}.")
    return capture


def _configure_rtsp_capture_timeouts(capture: Any, cv2: Any) -> None:
    setter = getattr(capture, "set", None)
    if not callable(setter):
        return

    for prop_id, value in (
        (getattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC", None), _OPENCV_CAPTURE_OPEN_TIMEOUT_MS),
        (getattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC", None), _OPENCV_CAPTURE_READ_TIMEOUT_MS),
    ):
        if prop_id is None:
            continue
        try:
            setter(prop_id, value)
        except Exception:  # pragma: no cover - backend-specific OpenCV failure
            continue


def _read_rtsp_frame(capture: Any) -> Any | None:
    ok, frame = capture.read()
    if not ok or frame is None:
        return None
    return frame


def _encode_mjpeg_frame(cv2: Any, frame: Any) -> bytes | None:
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        return None
    return b"".join((_MJPEG_FRAME_PREFIX, encoded.tobytes(), b"\r\n"))


def _load_cv2() -> Any:
    try:
        return importlib.import_module("cv2")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for the browser MJPEG bridge."
        ) from exc


def _b64url_uint(value: int) -> str:
    byte_length = max(1, (value.bit_length() + 7) // 8)
    return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).rstrip(b"=").decode(
        "utf-8"
    )


def _privacy_requires_filtering(privacy: Mapping[str, object] | None) -> bool:
    if privacy is None:
        return False
    return bool(privacy.get("blur_faces")) or bool(privacy.get("blur_plates"))


def _uses_central_delivery(
    *,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> bool:
    return (
        processing_mode in {ProcessingMode.CENTRAL, ProcessingMode.HYBRID}
        and edge_node_id is None
    )
