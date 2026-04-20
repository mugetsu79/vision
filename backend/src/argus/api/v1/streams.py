from __future__ import annotations

import asyncio
from collections.abc import Mapping
import posixpath
import re
from typing import Annotated
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from argus.api.contracts import StreamOfferRequest, StreamOfferResponse, TenantContext
from argus.api.dependencies import get_app_services, get_media_tenant_context, get_tenant_context
from argus.core.security import (
    AuthenticatedUser,
    enforce_role,
    get_current_media_user,
    require,
)
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(tags=["streams"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
MediaUser = Annotated[AuthenticatedUser, Depends(get_current_media_user)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
MediaTenantDependency = Annotated[TenantContext, Depends(get_media_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]

WEBRTC_TEST_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Vezor WebRTC Test</title>
    <style>
      body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; color: #132238; }
      form { display: grid; gap: 0.75rem; max-width: 52rem; }
      input, textarea, button { font: inherit; padding: 0.75rem; }
      video { margin-top: 1rem; width: min(100%, 960px); background: #081018; border-radius: 12px; }
      pre { white-space: pre-wrap; background: #f5f7fa; padding: 1rem; border-radius: 12px; }
    </style>
  </head>
  <body>
    <h1>Vezor WebRTC Offer Test</h1>
    <p>
      Paste a bearer token, choose a camera id, and this page will negotiate
      against <code>/api/v1/streams/&lt;camera_id&gt;/offer</code>.
    </p>
    <form id="webrtc-form">
      <label>
        Camera ID
        <input id="camera-id" placeholder="00000000-0000-0000-0000-000000000000" />
      </label>
      <label>
        Bearer token
        <textarea id="auth-token" rows="4" placeholder="eyJhbGciOi..."></textarea>
      </label>
      <button type="submit">Start WebRTC Session</button>
    </form>
    <video id="stream" autoplay muted playsinline controls></video>
    <pre id="status">Idle.</pre>
    <script>
      const form = document.getElementById("webrtc-form");
      const statusEl = document.getElementById("status");
      const videoEl = document.getElementById("stream");
      let peerConnection = null;

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        statusEl.textContent = "Creating RTCPeerConnection...";
        if (peerConnection !== null) {
          peerConnection.close();
        }

        const cameraId = document.getElementById("camera-id").value.trim();
        const token = document.getElementById("auth-token").value.trim();
        peerConnection = new RTCPeerConnection();
        peerConnection.addTransceiver("video", { direction: "recvonly" });
        peerConnection.ontrack = (trackEvent) => {
          videoEl.srcObject = trackEvent.streams[0];
        };

        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        statusEl.textContent = "Negotiating against backend...";

        const response = await fetch(`/api/v1/streams/${cameraId}/offer`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({ sdp_offer: offer.sdp }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          statusEl.textContent =
            `Offer request failed: ${response.status} ${errorText}`;
          return;
        }

        const payload = await response.json();
        await peerConnection.setRemoteDescription({
          type: "answer",
          sdp: payload.sdp_answer,
        });
        statusEl.textContent =
          "WebRTC answer applied. If the path is live, the video element " +
          "will attach shortly.";
      });
    </script>
  </body>
</html>
"""


@router.post("/api/v1/streams/{camera_id}/offer", response_model=StreamOfferResponse)
async def create_stream_offer(
    camera_id: UUID,
    payload: StreamOfferRequest,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> StreamOfferResponse:
    return await services.streams.create_offer(
        tenant_context,
        camera_id=camera_id,
        offer=payload,
    )


@router.get("/api/v1/streams/{camera_id}/hls.m3u8")
async def get_hls_playlist(
    request: Request,
    camera_id: UUID,
    current_user: MediaUser,
    tenant_context: MediaTenantDependency,
    services: ServicesDependency,
) -> Response:
    enforce_role(current_user, RoleEnum.VIEWER)
    playlist_url = await services.streams.get_hls_playlist_url(
        tenant_context,
        camera_id=camera_id,
    )
    payload, headers = await _fetch_hls_upstream(
        _merge_upstream_playlist_query(playlist_url, request=request)
    )
    rewritten_playlist = _rewrite_hls_playlist(
        playlist=payload.decode("utf-8"),
        camera_id=camera_id,
        request=request,
    )
    response_headers = _passthrough_upstream_headers(headers)
    media_type = headers.get("content-type", "application/vnd.apple.mpegurl")
    response_headers["Cache-Control"] = "no-store"
    return Response(
        content=rewritten_playlist,
        media_type=media_type,
        headers=response_headers,
    )


@router.get("/api/v1/streams/{camera_id}/hls/{resource_path:path}")
async def get_hls_resource(
    request: Request,
    camera_id: UUID,
    resource_path: str,
    current_user: MediaUser,
    tenant_context: MediaTenantDependency,
    services: ServicesDependency,
) -> Response:
    enforce_role(current_user, RoleEnum.VIEWER)
    playlist_url = await services.streams.get_hls_playlist_url(
        tenant_context,
        camera_id=camera_id,
    )
    upstream_url = _build_hls_resource_url(playlist_url, resource_path)
    payload, headers = await _fetch_hls_upstream(
        _merge_upstream_playlist_query(upstream_url, request=request)
        if _looks_like_hls_playlist(resource_path)
        else upstream_url
    )
    response_headers = _passthrough_upstream_headers(headers)
    response_headers["Cache-Control"] = "no-store"
    media_type = headers.get("content-type", "application/octet-stream")
    if _is_hls_playlist_content_type(media_type) or _looks_like_hls_playlist(resource_path):
        rewritten_playlist = _rewrite_hls_playlist(
            playlist=payload.decode("utf-8"),
            camera_id=camera_id,
            request=request,
        )
        return Response(
            content=rewritten_playlist,
            media_type=media_type,
            headers=response_headers,
        )
    return Response(content=payload, media_type=media_type, headers=response_headers)


@router.get("/video_feed/{camera_id}")
async def get_video_feed(
    camera_id: UUID,
    current_user: MediaUser,
    tenant_context: MediaTenantDependency,
    services: ServicesDependency,
) -> StreamingResponse:
    enforce_role(current_user, RoleEnum.VIEWER)
    proxy_stream = await services.streams.open_mjpeg_proxy(
        tenant_context,
        camera_id=camera_id,
        user=current_user,
    )
    return StreamingResponse(
        proxy_stream.iter_bytes(),
        media_type=proxy_stream.media_type,
        headers=proxy_stream.headers,
    )


@router.get(
    "/.well-known/argus/mediamtx/jwks.json",
    include_in_schema=False,
)
async def mediamtx_jwks(services: ServicesDependency) -> Mapping[str, object]:
    return services.streams.jwks()


@router.get(
    "/webrtc-test.html",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def webrtc_test_page() -> HTMLResponse:
    return HTMLResponse(WEBRTC_TEST_PAGE)


async def _fetch_hls_upstream(url: str) -> tuple[bytes, dict[str, str]]:
    retry_delays = (0.25, 0.5, 1.0, 1.0) if _looks_like_hls_playlist_url(url) else ()
    async with httpx.AsyncClient(timeout=10.0) as client:
        attempt = 0
        while True:
            response = await client.get(url)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code == status.HTTP_404_NOT_FOUND
                    and attempt < len(retry_delays)
                ):
                    await asyncio.sleep(retry_delays[attempt])
                    attempt += 1
                    continue
                raise _translate_hls_upstream_error(exc, url=url) from exc
            return await response.aread(), dict(response.headers)


def _rewrite_hls_playlist(*, playlist: str, camera_id: UUID, request: Request) -> str:
    query_params = _media_request_query_params(request)

    def rewrite_uri(uri: str) -> str:
        return _build_hls_proxy_uri(
            camera_id=camera_id,
            resource_uri=uri,
            query_params=query_params,
        )

    rewritten_lines: list[str] = []
    for line in playlist.splitlines():
        stripped = line.strip()
        if stripped == "":
            rewritten_lines.append(line)
            continue
        if stripped.startswith("#"):
            rewritten_lines.append(
                re.sub(
                    r'URI="([^"]+)"',
                    lambda match: f'URI="{rewrite_uri(match.group(1))}"',
                    line,
                )
            )
            continue
        rewritten_lines.append(rewrite_uri(stripped))
    return "\n".join(rewritten_lines) + ("\n" if playlist.endswith("\n") else "")


def _media_request_query_params(request: Request) -> dict[str, str]:
    values: dict[str, str] = {}
    for key in ("access_token", "tenant_id"):
        value = request.query_params.get(key)
        if value:
            values[key] = value
    return values


def _merge_upstream_playlist_query(url: str, *, request: Request) -> str:
    split_url = urlsplit(url)
    query_items = list(parse_qsl(split_url.query, keep_blank_values=True))
    auth_keys = {"access_token", "tenant_id"}
    query_items.extend(
        (key, value)
        for key, value in request.query_params.multi_items()
        if key not in auth_keys
    )
    query = urlencode(query_items)
    return urlunsplit(
        (split_url.scheme, split_url.netloc, split_url.path, query, split_url.fragment)
    )


def _build_hls_proxy_uri(
    *,
    camera_id: UUID,
    resource_uri: str,
    query_params: Mapping[str, str],
) -> str:
    split_resource = urlsplit(resource_uri)
    resource_path = split_resource.path.lstrip("/")
    query_items = list(parse_qsl(split_resource.query, keep_blank_values=True))
    query_items.extend(query_params.items())
    query = urlencode(query_items)
    return urlunsplit(
        (
            "",
            "",
            f"/api/v1/streams/{camera_id}/hls/{resource_path}",
            query,
            split_resource.fragment,
        )
    )


def _build_hls_resource_url(playlist_url: str, resource_path: str) -> str:
    if resource_path == "":
        raise ValueError("resource_path must not be empty")

    normalized_resource = posixpath.normpath(resource_path.lstrip("/"))
    if normalized_resource.startswith("../") or normalized_resource == "..":
        raise ValueError("resource_path must remain inside the HLS directory")

    split_playlist = urlsplit(playlist_url)
    base_directory = posixpath.dirname(split_playlist.path)
    upstream_path = posixpath.normpath(posixpath.join(base_directory, normalized_resource))
    expected_prefix = f"{base_directory.rstrip('/')}/"
    if upstream_path != base_directory and not upstream_path.startswith(expected_prefix):
        raise ValueError("resource_path escaped the HLS directory")

    return urlunsplit(
        (
            split_playlist.scheme,
            split_playlist.netloc,
            upstream_path,
            split_playlist.query,
            split_playlist.fragment,
        )
    )


def _passthrough_upstream_headers(headers: Mapping[str, str]) -> dict[str, str]:
    allowed_headers = {
        "cache-control",
        "etag",
        "last-modified",
        "content-range",
        "accept-ranges",
    }
    return {
        key: value
        for key, value in headers.items()
        if key.lower() in allowed_headers and key.lower() != "content-type"
    }


def _looks_like_hls_playlist(resource_path: str) -> bool:
    return resource_path.endswith(".m3u8")


def _looks_like_hls_playlist_url(url: str) -> bool:
    return _looks_like_hls_playlist(urlsplit(url).path)


def _is_hls_playlist_content_type(content_type: str | None) -> bool:
    if content_type is None:
        return False
    normalized = content_type.lower()
    return (
        "application/vnd.apple.mpegurl" in normalized
        or "application/x-mpegurl" in normalized
    )


def _translate_hls_upstream_error(exc: httpx.HTTPStatusError, *, url: str) -> HTTPException:
    if exc.response.status_code == status.HTTP_404_NOT_FOUND:
        detail = (
            "Stream playlist is not ready yet."
            if _looks_like_hls_playlist_url(url)
            else "Stream resource is unavailable."
        )
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unable to load upstream stream asset.",
    )
