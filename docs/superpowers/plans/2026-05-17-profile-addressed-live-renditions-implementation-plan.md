# Profile Addressed Live Renditions Implementation Plan

Status: Deferred after May 2026 field validation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Live tile rendition changes enforce the selected resolution and frame rate by routing browser playback to profile-specific stream paths.

**Architecture:** Keep rendition selection global per camera, but make stream access profile-aware. The frontend sends `profile_id`, the backend validates it against the camera's browser delivery profiles, stream access resolves profile-specific MediaMTX paths for dimensioned processed profiles, and the worker publishes the active profile to the same path.

**Tech Stack:** FastAPI, Pydantic, MediaMTX, pytest, React, TypeScript, Vitest, Testing Library, existing Vezor stream services.

---

## File Structure

- Modify `backend/src/argus/api/contracts.py`: add optional `profile_id` to `StreamOfferRequest`.
- Modify `backend/src/argus/api/v1/streams.py`: accept `profile_id` for HLS and MJPEG routes and preserve it through playlist rewrites.
- Modify `backend/src/argus/services/app.py`: validate requested profile ids and pass selected profile settings into stream access.
- Modify `backend/src/argus/streaming/webrtc.py`: make stream access paths profile-specific for dimensioned processed profiles.
- Modify `backend/src/argus/streaming/mediamtx.py`: register and publish active dimensioned profiles on profile-specific paths.
- Modify `backend/src/argus/inference/engine.py`: pass `self.config.stream.profile_id` into stream registration.
- Modify `backend/src/argus/supervisor/stream_provisioner.py`: pass worker config stream profile ids into registration.
- Modify backend tests in `backend/tests/streaming`, `backend/tests/services`, `backend/tests/api`, `backend/tests/inference`, and `backend/tests/supervisor`.
- Modify `frontend/src/components/live/VideoStream.tsx`: include profile id in HLS, MJPEG, and WebRTC stream requests; display profile badge clearly.
- Modify `frontend/src/components/live/VideoStream.test.tsx`: prove profile-aware requests and badge behavior.
- Regenerate `frontend/src/lib/api.generated.ts` after backend contract changes.

---

### Task 1: Make Stream Access Paths Profile-Specific

**Files:**
- Modify: `backend/src/argus/streaming/webrtc.py`
- Test: `backend/tests/streaming/test_webrtc.py`

- [ ] **Step 1: Write the failing stream path tests**

Add tests to `backend/tests/streaming/test_webrtc.py`:

```python
def test_resolve_stream_access_uses_profile_specific_transcode_path() -> None:
    camera_id = uuid4()

    access = resolve_stream_access(
        camera_id=camera_id,
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        stream_kind="transcode",
        profile_id="540p5",
        privacy={"blur_faces": False, "blur_plates": False},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    assert access.mode is StreamMode.ANNOTATED_WHIP
    assert access.profile_id == "540p5"
    assert access.path_name == f"cameras/{camera_id}/annotated-540p5"
    assert access.rtsp_url == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/annotated-540p5"
    assert access.whep_url == f"http://mediamtx.internal:8889/cameras/{camera_id}/annotated-540p5/whep"
    assert access.hls_url == f"http://mediamtx.internal:8888/cameras/{camera_id}/annotated-540p5/index.m3u8"
    assert access.mjpeg_url == f"http://mediamtx.internal:8890/cameras/{camera_id}/annotated-540p5/mjpeg"


def test_resolve_stream_access_keeps_legacy_paths_for_native_and_annotated() -> None:
    camera_id = uuid4()

    native = resolve_stream_access(
        camera_id=camera_id,
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        stream_kind="passthrough",
        profile_id="native",
        privacy={"blur_faces": False, "blur_plates": False},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )
    annotated = resolve_stream_access(
        camera_id=camera_id,
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
        stream_kind="transcode",
        profile_id="annotated",
        privacy={"blur_faces": False, "blur_plates": False},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    assert native.path_name == f"cameras/{camera_id}/passthrough"
    assert annotated.path_name == f"cameras/{camera_id}/annotated"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/streaming/test_webrtc.py::test_resolve_stream_access_uses_profile_specific_transcode_path backend/tests/streaming/test_webrtc.py::test_resolve_stream_access_keeps_legacy_paths_for_native_and_annotated -q
```

Expected: FAIL because `resolve_stream_access` does not accept `profile_id` and `StreamAccess` has no `profile_id`.

- [ ] **Step 3: Add profile-aware path resolution**

In `backend/src/argus/streaming/webrtc.py`, update `StreamAccess`:

```python
@dataclass(slots=True, frozen=True)
class StreamAccess:
    camera_id: UUID
    mode: StreamMode
    path_name: str
    rtsp_url: str
    whep_url: str
    hls_url: str
    mjpeg_url: str
    profile_id: str | None = None
```

Update `resolve_stream_access` signature:

```python
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
    profile_id: str | None = None,
    mjpeg_path_template: str = "{base}/{path}/mjpeg",
) -> StreamAccess:
```

Add this helper near `resolve_stream_access`:

```python
_LEGACY_PROFILE_PATH_IDS = {"native", "annotated", None}


def _stream_path_name(*, camera_id: UUID, variant: str, profile_id: str | None) -> str:
    if variant in {"annotated", "preview"} and profile_id not in _LEGACY_PROFILE_PATH_IDS:
        return f"cameras/{camera_id}/{variant}/{profile_id}"
    return f"cameras/{camera_id}/{variant}"
```

Replace:

```python
path_name = f"cameras/{camera_id}/{variant}"
```

with:

```python
path_name = _stream_path_name(
    camera_id=camera_id,
    variant=variant,
    profile_id=profile_id,
)
```

Return `profile_id=profile_id` in the `StreamAccess` constructor.

- [ ] **Step 4: Run focused stream path tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/streaming/test_webrtc.py::test_resolve_stream_access_uses_profile_specific_transcode_path backend/tests/streaming/test_webrtc.py::test_resolve_stream_access_keeps_legacy_paths_for_native_and_annotated -q
```

Expected: PASS.

- [ ] **Step 5: Run existing WebRTC path tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/streaming/test_webrtc.py -q
```

Expected: PASS. Existing tests that omit `profile_id` keep the legacy paths.

---

### Task 2: Validate Requested Profiles In The Stream Service

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_stream_service.py`

- [ ] **Step 1: Write failing service tests**

In `backend/tests/services/test_stream_service.py`, update imports:

```python
from fastapi import HTTPException

from argus.api.contracts import BrowserDeliverySettings, TenantContext
```

Add these tests near the existing `_resolve_stream_access` tests:

```python
@pytest.mark.asyncio
async def test_stream_access_uses_requested_browser_delivery_profile(
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
        browser_delivery=BrowserDeliverySettings(default_profile="720p10").model_dump(
            mode="python"
        ),
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

    access = await service._resolve_stream_access(
        tenant_context,
        camera_id,
        requested_profile_id="540p5",
    )

    assert access.profile_id == "540p5"
    assert access.path_name == f"cameras/{camera_id}/annotated-540p5"


@pytest.mark.asyncio
async def test_stream_access_rejects_unknown_requested_profile(
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
        browser_delivery=BrowserDeliverySettings(default_profile="720p10").model_dump(
            mode="python"
        ),
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

    with pytest.raises(HTTPException) as exc_info:
        await service._resolve_stream_access(
            tenant_context,
            camera_id,
            requested_profile_id="../540p5",
        )

    assert exc_info.value.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_stream_service.py::test_stream_access_uses_requested_browser_delivery_profile backend/tests/services/test_stream_service.py::test_stream_access_rejects_unknown_requested_profile -q
```

Expected: FAIL because `_resolve_stream_access` does not accept `requested_profile_id`.

- [ ] **Step 3: Implement requested profile validation**

In `backend/src/argus/services/app.py`, update public methods:

```python
async def create_offer(
    self,
    tenant_context: TenantContext,
    *,
    camera_id: UUID,
    offer: StreamOfferRequest,
) -> StreamOfferResponse:
    access = await self._resolve_stream_access(
        tenant_context,
        camera_id,
        requested_profile_id=offer.profile_id,
    )
```

```python
async def get_hls_playlist_url(
    self,
    tenant_context: TenantContext,
    *,
    camera_id: UUID,
    requested_profile_id: str | None = None,
) -> str:
    access = await self._resolve_stream_access(
        tenant_context,
        camera_id,
        requested_profile_id=requested_profile_id,
    )
```

```python
async def open_mjpeg_proxy(
    self,
    tenant_context: TenantContext,
    *,
    camera_id: UUID,
    user: Any,
    requested_profile_id: str | None = None,
) -> UpstreamProxyStream:
    access = await self._resolve_stream_access(
        tenant_context,
        camera_id,
        requested_profile_id=requested_profile_id,
    )
```

Update `_resolve_stream_access`:

```python
async def _resolve_stream_access(
    self,
    tenant_context: TenantContext,
    camera_id: UUID,
    *,
    requested_profile_id: str | None = None,
) -> StreamAccess:
```

Add helper functions near `_resolve_worker_stream_settings`:

```python
_STREAM_PROFILE_PATH_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _select_browser_delivery_profile(
    browser_delivery: BrowserDeliverySettings,
    requested_profile_id: str | None,
) -> BrowserDeliverySettings:
    selected_profile_id = requested_profile_id or browser_delivery.default_profile
    if not _STREAM_PROFILE_PATH_RE.fullmatch(selected_profile_id):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Invalid stream profile id.",
        )
    profile_payloads = browser_delivery.profiles or BrowserDeliverySettings().profiles
    profiles_by_id = {str(profile["id"]): dict(profile) for profile in profile_payloads}
    if "native" not in profiles_by_id:
        profiles_by_id["native"] = {"id": "native", "kind": "passthrough"}
    if "annotated" not in profiles_by_id:
        profiles_by_id["annotated"] = {"id": "annotated", "kind": "transcode"}
    if selected_profile_id not in profiles_by_id:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Unsupported stream profile id.",
        )
    return browser_delivery.model_copy(update={"default_profile": selected_profile_id})
```

Add `import re` at the top of the file.

Inside `_resolve_stream_access`, after `_browser_delivery_with_stream_profile(...)`, call:

```python
browser_delivery = _select_browser_delivery_profile(
    browser_delivery,
    requested_profile_id,
)
```

Pass the selected profile into `resolve_stream_access`:

```python
access = resolve_stream_access(
    camera_id=camera.id,
    processing_mode=camera.processing_mode,
    edge_node_id=effective_edge_node_id,
    stream_kind=stream_settings.kind,
    profile_id=stream_settings.profile_id,
    privacy=camera.privacy,
    rtsp_base_url=base_urls["rtsp"],
    webrtc_base_url=base_urls["webrtc"],
    hls_base_url=base_urls["hls"],
    mjpeg_base_url=base_urls["mjpeg"],
    mjpeg_path_template=self.settings.mediamtx_mjpeg_path_template,
)
```

- [ ] **Step 4: Run focused service tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_stream_service.py::test_stream_access_uses_requested_browser_delivery_profile backend/tests/services/test_stream_service.py::test_stream_access_rejects_unknown_requested_profile -q
```

Expected: PASS.

- [ ] **Step 5: Run existing stream service tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_stream_service.py -q
```

Expected: PASS.

---

### Task 3: Thread Profile Id Through Stream API Routes

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/streams.py`
- Test: `backend/tests/api/test_prompt6_streaming_routes.py`

- [ ] **Step 1: Write failing route tests**

In `backend/tests/api/test_prompt6_streaming_routes.py`, extend `FakeStreamService`:

```python
class FakeStreamService:
    def __init__(self) -> None:
        self.offer_calls: list[StreamOfferRequest] = []
        self.hls_profile_ids: list[str | None] = []
        self.mjpeg_profile_ids: list[str | None] = []

    async def create_offer(
        self,
        context: TenantContext,
        *,
        camera_id: UUID,
        offer: StreamOfferRequest,
    ) -> StreamOfferResponse:
        self.offer_calls.append(offer)
        return StreamOfferResponse(
            camera_id=camera_id,
            sdp_answer="v=0\r\no=mediamtx 1 1 IN IP4 127.0.0.1\r\n",
        )

    async def get_hls_playlist_url(
        self,
        context: TenantContext,
        *,
        camera_id: UUID,
        requested_profile_id: str | None = None,
    ) -> str:
        self.hls_profile_ids.append(requested_profile_id)
        return f"http://mediamtx.internal:8888/cameras/{camera_id}/preview/index.m3u8?jwt=test-token"

    async def open_mjpeg_proxy(
        self,
        context: TenantContext,
        *,
        camera_id: UUID,
        user: AuthenticatedUser,
        requested_profile_id: str | None = None,
    ) -> FakeProxyStream:
        self.mjpeg_profile_ids.append(requested_profile_id)
        return FakeProxyStream(
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store"},
            chunks=(
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\nframe-one\r\n",
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\nframe-two\r\n",
            ),
        )
```

Add these tests:

```python
@pytest.mark.asyncio
async def test_stream_offer_forwards_requested_profile_id() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    stream_service = FakeStreamService()
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
        streams=stream_service,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            f"/api/v1/streams/{camera_id}/offer",
            json={"sdp_offer": "v=0\r\n", "profile_id": "540p5"},
        )

    assert response.status_code == 200
    assert stream_service.offer_calls[-1].profile_id == "540p5"


@pytest.mark.asyncio
async def test_hls_route_forwards_requested_profile_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _sample_user()
    context = _tenant_context(user)
    stream_service = FakeStreamService()
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
        streams=stream_service,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_media_user] = lambda: user
    camera_id = uuid4()

    async def fake_fetch(url: str) -> tuple[bytes, dict[str, str]]:
        assert url.endswith("index.m3u8?jwt=test-token")
        return (b"#EXTM3U\n", {"content-type": "application/vnd.apple.mpegurl"})

    monkeypatch.setattr(streams_module, "_fetch_hls_upstream", fake_fetch)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            f"/api/v1/streams/{camera_id}/hls.m3u8",
            params={"profile_id": "540p5"},
        )

    assert response.status_code == 200
    assert stream_service.hls_profile_ids[-1] == "540p5"


@pytest.mark.asyncio
async def test_video_feed_route_forwards_requested_profile_id() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    stream_service = FakeStreamService()
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
        streams=stream_service,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_media_user] = lambda: user
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            f"/video_feed/{camera_id}",
            params={"profile_id": "540p5"},
        )

    assert response.status_code == 200
    assert stream_service.mjpeg_profile_ids[-1] == "540p5"
```

Add this playlist rewrite assertion to `test_hls_route_proxies_playlist_and_rewrites_media_uris` by including `profile_id` in the request params and expected rewritten URLs:

```python
response = await client.get(
    f"/api/v1/streams/{camera_id}/hls.m3u8",
    params={
        "access_token": "viewer-token",
        "tenant_id": str(context.tenant_id),
        "profile_id": "540p5",
        "_HLS_msn": "42",
        "_HLS_part": "2",
    },
)

assert (
    f"/api/v1/streams/{camera_id}/hls/init.mp4?"
    f"access_token=viewer-token&tenant_id={context.tenant_id}&profile_id=540p5"
    in response.text
)
assert (
    f"/api/v1/streams/{camera_id}/hls/segment0.mp4?"
    f"access_token=viewer-token&tenant_id={context.tenant_id}&profile_id=540p5"
    in response.text
)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_prompt6_streaming_routes.py::test_stream_offer_forwards_requested_profile_id backend/tests/api/test_prompt6_streaming_routes.py::test_hls_route_forwards_requested_profile_id backend/tests/api/test_prompt6_streaming_routes.py::test_video_feed_route_forwards_requested_profile_id backend/tests/api/test_prompt6_streaming_routes.py::test_hls_route_proxies_playlist_and_rewrites_media_uris -q
```

Expected: FAIL because route signatures and fake service calls do not carry `profile_id`.

- [ ] **Step 3: Add profile id to the API contract**

In `backend/src/argus/api/contracts.py`, update `StreamOfferRequest`:

```python
class StreamOfferRequest(BaseModel):
    sdp_offer: str = Field(min_length=1)
    profile_id: BrowserDeliveryProfileId | None = None
```

- [ ] **Step 4: Pass profile ids from routes into services**

In `backend/src/argus/api/v1/streams.py`, import `Query`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
```

Update HLS playlist route:

```python
async def get_hls_playlist(
    request: Request,
    camera_id: UUID,
    current_user: MediaUser,
    tenant_context: MediaTenantDependency,
    services: ServicesDependency,
    profile_id: str | None = Query(default=None),
) -> Response:
    playlist_url = await services.streams.get_hls_playlist_url(
        tenant_context,
        camera_id=camera_id,
        requested_profile_id=profile_id,
    )
```

Update HLS resource route the same way:

```python
async def get_hls_resource(
    request: Request,
    camera_id: UUID,
    resource_path: str,
    current_user: MediaUser,
    tenant_context: MediaTenantDependency,
    services: ServicesDependency,
    profile_id: str | None = Query(default=None),
) -> Response:
    playlist_url = await services.streams.get_hls_playlist_url(
        tenant_context,
        camera_id=camera_id,
        requested_profile_id=profile_id,
    )
```

Update MJPEG route:

```python
async def get_video_feed(
    camera_id: UUID,
    current_user: MediaUser,
    tenant_context: MediaTenantDependency,
    services: ServicesDependency,
    profile_id: str | None = Query(default=None),
) -> StreamingResponse:
    proxy_stream = await services.streams.open_mjpeg_proxy(
        tenant_context,
        camera_id=camera_id,
        user=current_user,
        requested_profile_id=profile_id,
    )
```

- [ ] **Step 5: Preserve profile id while rewriting HLS playlists**

In `_media_request_query_params`, preserve `profile_id`:

```python
def _media_request_query_params(request: Request) -> dict[str, str]:
    values: dict[str, str] = {}
    for key in ("access_token", "tenant_id", "profile_id"):
        value = request.query_params.get(key)
        if value:
            values[key] = value
    return values
```

- [ ] **Step 6: Run route tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_prompt6_streaming_routes.py -q
```

Expected: PASS.

---

### Task 4: Publish Worker Streams To Profile-Specific MediaMTX Paths

**Files:**
- Modify: `backend/src/argus/streaming/mediamtx.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/supervisor/stream_provisioner.py`
- Test: `backend/tests/streaming/test_mediamtx.py`
- Test: `backend/tests/inference/test_engine.py`
- Test: `backend/tests/supervisor/test_stream_provisioner.py`

- [ ] **Step 1: Write the failing MediaMTX registration test**

Add to `backend/tests/streaming/test_mediamtx.py`:

```python
@pytest.mark.asyncio
async def test_mediamtx_client_registers_profile_specific_processed_path() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def handler(request: Request) -> Response:
        requests.append(
            (
                request.method,
                str(request.url),
                json.loads(request.content.decode("utf-8")) if request.content else None,
            )
        )
        return Response(200, json={"ok": True})

    camera_id = uuid4()
    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        http_client=AsyncClient(transport=_transport(handler)),
    )

    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.JETSON_NANO,
        stream_kind="transcode",
        privacy=PrivacyPolicy(blur_faces=False, blur_plates=False),
        profile_id="540p5",
        target_width=960,
        target_height=540,
        target_fps=5,
    )

    assert registration.path_name == f"cameras/{camera_id}/annotated-540p5"
    assert registration.publish_path == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/annotated-540p5"
    assert registration.target_width == 960
    assert registration.target_height == 540
    assert registration.target_fps == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/streaming/test_mediamtx.py::test_mediamtx_client_registers_profile_specific_processed_path -q
```

Expected: FAIL because `register_stream` does not accept `profile_id` and uses the generic annotated path.

- [ ] **Step 3: Add `profile_id` to stream registration APIs**

Update `MediaMTXClient.register_stream`, the engine `StreamClient` protocol, and the supervisor `StreamClient` protocol with:

```python
profile_id: str | None = None
```

Pass it into the internal registration builder.

In `backend/src/argus/streaming/mediamtx.py`, add the same helper shape used by `webrtc.py`:

```python
_LEGACY_PROFILE_PATH_IDS = {"native", "annotated", None}


def _stream_path_name(*, camera_id: UUID, variant: str, profile_id: str | None) -> str:
    if variant in {"annotated", "preview"} and profile_id not in _LEGACY_PROFILE_PATH_IDS:
        return f"cameras/{camera_id}/{variant}/{profile_id}"
    return f"cameras/{camera_id}/{variant}"
```

Use it for annotated and preview names:

```python
annotated_name = _stream_path_name(
    camera_id=camera_id,
    variant="annotated",
    profile_id=profile_id,
)
```

```python
preview_name = _stream_path_name(
    camera_id=camera_id,
    variant="preview",
    profile_id=profile_id,
)
```

Keep passthrough as `cameras/{camera_id}/passthrough`.

- [ ] **Step 4: Pass worker config profile ids into registration**

In `backend/src/argus/inference/engine.py`, update both initial start and command re-register calls:

```python
self._stream_registration = await self.stream_client.register_stream(
    camera_id=self.config.camera_id,
    rtsp_url=self.config.camera.resolved_source_uri,
    profile=self.profile,
    stream_kind=self.config.stream.kind,
    privacy=self._state.privacy,
    profile_id=self.config.stream.profile_id,
    target_fps=self.config.stream.fps,
    target_width=self.config.stream.width,
    target_height=self.config.stream.height,
)
```

In `backend/src/argus/supervisor/stream_provisioner.py`, update:

```python
registration = await self.stream_client.register_stream(
    camera_id=config.camera_id,
    rtsp_url=source_uri,
    profile=self.publish_profile,
    stream_kind=config.stream.kind,
    privacy=PrivacyPolicy.model_validate(config.privacy.model_dump(mode="python")),
    profile_id=config.stream.profile_id,
    target_fps=config.stream.fps,
    target_width=config.stream.width,
    target_height=config.stream.height,
)
```

- [ ] **Step 5: Add propagation assertions**

Update relevant fake stream clients in `backend/tests/inference/test_engine.py` and `backend/tests/supervisor/test_stream_provisioner.py` so captured calls include `profile_id`. Add focused assertions that a `WorkerStreamSettings(profile_id="540p5", kind="transcode", width=960, height=540, fps=5)` produces `profile_id == "540p5"` in the register call.

- [ ] **Step 6: Run focused backend worker tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/streaming/test_mediamtx.py::test_mediamtx_client_registers_profile_specific_processed_path backend/tests/inference/test_engine.py backend/tests/supervisor/test_stream_provisioner.py -q
```

Expected: PASS.

---

### Task 5: Make VideoStream Request The Selected Profile

**Files:**
- Modify: `frontend/src/components/live/VideoStream.tsx`
- Test: `frontend/src/components/live/VideoStream.test.tsx`

- [ ] **Step 1: Write failing frontend request tests**

Add tests to `frontend/src/components/live/VideoStream.test.tsx`:

```ts
test("adds the selected profile id to HLS requests", async () => {
  vi.spyOn(global, "fetch").mockResolvedValue(new Response("upstream failed", { status: 502 }));
  isSupportedMock.mockReturnValue(true);
  loadHlsClientMock.mockResolvedValue({
    isSupported: isSupportedMock,
    Hls: class FakeHls {
      static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
      static isSupported() {
        return true;
      }
      loadSource = loadSourceMock;
      attachMedia = attachMediaMock;
      on = onMock;
      destroy = destroyMock;
    },
  });

  render(
    <VideoStream
      cameraId="11111111-1111-1111-1111-111111111111"
      cameraName="North Gate"
      defaultProfile="540p5"
      deliveryMode="hls"
    />,
  );

  await waitFor(() => expect(loadSourceMock).toHaveBeenCalledTimes(1));
  const url = new URL(String(loadSourceMock.mock.calls[0]?.[0]));
  expect(url.searchParams.get("profile_id")).toBe("540p5");
  expect(screen.getByText("540p5")).toBeInTheDocument();
});


test("sends the selected profile id in WebRTC offers", async () => {
  const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ sdp_answer: "v=0\r\n" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  mockWebRtcAvailable();

  render(
    <VideoStream
      cameraId="11111111-1111-1111-1111-111111111111"
      cameraName="North Gate"
      defaultProfile="540p5"
    />,
  );

  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
  expect(body.profile_id).toBe("540p5");
});
```

Use the existing WebRTC mock helper names in the file; keep the assertions.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/VideoStream.test.tsx
```

Expected: FAIL because `profile_id` is missing and the badge can show only delivery mode.

- [ ] **Step 3: Add profile id to HLS and MJPEG URLs**

In `frontend/src/components/live/VideoStream.tsx`, update URL builders:

```ts
const hlsUrl = useMemo(
  () =>
    buildApiUrl(`/api/v1/streams/${cameraId}/hls.m3u8`, {
      access_token: accessToken,
      profile_id: defaultProfile,
      session_token: String(sessionToken),
      tenant_id: tenantId,
    }),
  [accessToken, cameraId, defaultProfile, sessionToken, tenantId],
);

const mjpegUrl = useMemo(
  () =>
    buildApiUrl(`/video_feed/${cameraId}`, {
      access_token: accessToken,
      profile_id: defaultProfile,
      session_token: String(sessionToken),
      tenant_id: tenantId,
    }),
  [accessToken, cameraId, defaultProfile, sessionToken, tenantId],
);
```

- [ ] **Step 4: Add profile id to WebRTC offers**

Add `defaultProfile` to `startWebRtc` parameters and call:

```ts
body: JSON.stringify({
  profile_id: defaultProfile,
  sdp_offer: offer.sdp ?? "",
}),
```

- [ ] **Step 5: Show the profile badge even with delivery mode**

Replace:

```tsx
{deliveryMode ?? defaultProfile}
```

with:

```tsx
{defaultProfile}
```

Keep the transport badge as the second badge.

- [ ] **Step 6: Run VideoStream tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/VideoStream.test.tsx
```

Expected: PASS.

---

### Task 6: Regenerate API Types And Fix Type Consumers

**Files:**
- Modify: `frontend/src/lib/api.generated.ts`
- Modify: frontend tests using `components["schemas"]["StreamOfferRequest"]` if TypeScript reports the generated optional field in mocked bodies

- [ ] **Step 1: Run API generation**

Run:

```bash
corepack pnpm --dir frontend generate:api
```

Expected: `frontend/src/lib/api.generated.ts` includes `profile_id?: BrowserDeliveryProfileId | null` or the generator's equivalent for `StreamOfferRequest`.

If the local backend running on `127.0.0.1:8000` is stale, generate the schema from the checked-out backend code and feed that file to `openapi-typescript`:

```bash
python3 -m uv run --project backend python -c 'import json; from argus.main import create_app; from argus.core.config import Settings; app = create_app(Settings(enable_startup_services=False, enable_nats=False)); print(json.dumps(app.openapi()))' > /private/tmp/argus-openapi-profile.json
corepack pnpm --dir frontend exec openapi-typescript /private/tmp/argus-openapi-profile.json -o src/lib/api.generated.ts
```

- [ ] **Step 2: Run TypeScript build**

Run:

```bash
corepack pnpm --dir frontend exec tsc -b
```

Expected: PASS. When TypeScript reports an incompatible mocked `StreamOfferRequest`, add `profile_id` only to that mocked request shape.

- [ ] **Step 3: Run focused frontend tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/VideoStream.test.tsx src/pages/Live.test.tsx
```

Expected: PASS.

---

### Task 7: Full Focused Verification And Visual Validation

**Files:**
- No new source files unless a previous task found a scoped bug.

- [ ] **Step 1: Run focused backend verification**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/streaming/test_webrtc.py backend/tests/streaming/test_mediamtx.py backend/tests/services/test_stream_service.py backend/tests/api/test_prompt6_streaming_routes.py backend/tests/inference/test_engine.py backend/tests/supervisor/test_stream_provisioner.py -q
```

Expected: PASS.

- [ ] **Step 2: Run focused frontend verification**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/VideoStream.test.tsx src/pages/Live.test.tsx
corepack pnpm --dir frontend exec tsc -b
```

Expected: PASS.

- [ ] **Step 3: Run installer-relevant build check**

Run:

```bash
corepack pnpm --dir frontend build
```

Expected: PASS. This protects the MacBook installer Docker build from TypeScript regressions.

- [ ] **Step 4: Visual validation with WebGL off**

Start the existing frontend/backend dev stack with WebGL disabled. Open Live, apply `540p5`, and inspect network requests.

Required observations:

- HLS URL includes `profile_id=540p5` when HLS is active.
- WebRTC offer body includes `"profile_id":"540p5"` when WebRTC is active.
- The stream path resolved by backend or MediaMTX logs includes `cameras/{camera_id}/annotated-540p5`.
- The tile badge shows `540p5`.
- While the profile-specific path is not ready, the tile retries instead of showing the old profile as if it were current.

- [ ] **Step 5: Commit**

Stage only files touched for this feature:

```bash
git add backend/src/argus/api/contracts.py backend/src/argus/api/v1/streams.py backend/src/argus/services/app.py backend/src/argus/streaming/webrtc.py backend/src/argus/streaming/mediamtx.py backend/src/argus/inference/engine.py backend/src/argus/supervisor/stream_provisioner.py backend/tests/streaming/test_webrtc.py backend/tests/streaming/test_mediamtx.py backend/tests/services/test_stream_service.py backend/tests/api/test_prompt6_streaming_routes.py backend/tests/inference/test_engine.py backend/tests/supervisor/test_stream_provisioner.py frontend/src/components/live/VideoStream.tsx frontend/src/components/live/VideoStream.test.tsx frontend/src/lib/api.generated.ts
git commit -m "feat(live): enforce profile-addressed renditions"
```

Expected: commit succeeds with no unrelated untracked files staged.

---

## Plan Self-Review

- Spec coverage: backend stream path contract, route/API contract, worker MediaMTX publishing, frontend request behavior, compatibility, testing, and visual validation are covered.
- Placeholder scan: no implementation steps depend on unspecified deferred work; tests name concrete existing files, fixtures, and assertions.
- Type consistency: the plan uses `profile_id` consistently across API body/query, service methods, `StreamAccess`, worker registration, and frontend requests.
