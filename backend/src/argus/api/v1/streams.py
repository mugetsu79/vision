from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from argus.api.contracts import StreamOfferRequest, StreamOfferResponse, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(tags=["streams"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]

WEBRTC_TEST_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Argus WebRTC Test</title>
    <style>
      body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; color: #132238; }
      form { display: grid; gap: 0.75rem; max-width: 52rem; }
      input, textarea, button { font: inherit; padding: 0.75rem; }
      video { margin-top: 1rem; width: min(100%, 960px); background: #081018; border-radius: 12px; }
      pre { white-space: pre-wrap; background: #f5f7fa; padding: 1rem; border-radius: 12px; }
    </style>
  </head>
  <body>
    <h1>Argus WebRTC Offer Test</h1>
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
    camera_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> RedirectResponse:
    playlist_url = await services.streams.get_hls_playlist_url(
        tenant_context,
        camera_id=camera_id,
    )
    return RedirectResponse(url=playlist_url, status_code=307)


@router.get("/video_feed/{camera_id}")
async def get_video_feed(
    camera_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> StreamingResponse:
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
