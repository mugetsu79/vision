# Browser Delivery Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `native` true passthrough everywhere, make non-native profiles worker-published processed streams, and label central versus edge bandwidth scope clearly.

**Architecture:** Treat browser delivery as a resolved stream contract that is independent from inference ingest. Backend profile resolution produces stable ids plus source-aware labels, worker config uses the resolved profile to decide passthrough versus processed publishing, MediaMTX registers matching central or edge paths, and the Live UI displays the actual stream mode instead of hiding it behind profile names.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, MediaMTX, pytest, React/TypeScript, Vitest, Playwright.

---

## File Map

- Modify `backend/src/argus/api/contracts.py`
  - Add the `annotated` browser delivery profile id.
  - Add optional profile display fields.
  - Keep `native`, `1080p15`, `720p10`, and `540p5` ids stable.

- Modify `backend/src/argus/services/app.py`
  - Resolve profiles with processing-mode-aware labels.
  - Remove the central-only processed-native branch.
  - Normalize worker config through source-aware browser delivery.
  - Generalize edge MediaMTX relay from passthrough-only to any edge browser stream path.

- Modify `backend/src/argus/streaming/webrtc.py`
  - Resolve edge transcode streams to `cameras/<id>/annotated`.
  - Treat hybrid without an edge assignment as central-like for stream access only.

- Modify `backend/src/argus/streaming/mediamtx.py`
  - Register Jetson non-native profiles as worker-published annotated streams instead of falling back to passthrough.

- Modify `backend/tests/services/test_browser_delivery_profiles.py`
  - New unit tests for source-aware labels and privacy-native fallback.

- Modify `backend/tests/services/test_camera_worker_config.py`
  - Update central native expectations.
  - Add annotated worker config expectations.

- Modify `backend/tests/services/test_stream_service.py`
  - Update service-level central native expectations.
  - Add edge transcode relay coverage.

- Modify `backend/tests/streaming/test_webrtc.py`
  - Add edge transcode stream access coverage.

- Modify `backend/tests/streaming/test_mediamtx.py`
  - Add Jetson transcode registration coverage.

- Modify `frontend/src/components/cameras/CameraWizard.tsx`
  - Render profile labels instead of raw ids.
  - Use mode-aware fallback labels when older API payloads do not include labels.

- Modify `frontend/src/components/cameras/CameraWizard.test.tsx`
  - Assert central and edge labels distinguish viewer preview versus edge bandwidth saver.

- Modify `frontend/src/pages/Live.tsx`
  - Display profile label plus actual telemetry stream mode.
  - Remove the current `native clean` masking rule.

- Modify `frontend/src/pages/Live.test.tsx`
  - Update the stale native test and add an actual passthrough display assertion.

- Modify `docs/deployment-modes-and-matrix.md`
  - Document that central reduced profiles reduce master-to-browser bandwidth only.

- Modify `docs/imac-master-orin-lab-test-guide.md`
  - Update lab language for central and edge browser delivery profiles.

---

## Task 1: Backend Profile Catalog And Labels

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Create: `backend/tests/services/test_browser_delivery_profiles.py`

- [ ] **Step 1: Write failing source-aware profile tests**

Create `backend/tests/services/test_browser_delivery_profiles.py`:

```python
from __future__ import annotations

from uuid import uuid4

from argus.api.contracts import BrowserDeliverySettings, SourceCapability
from argus.models.enums import ProcessingMode
from argus.services.app import _build_source_aware_browser_delivery


def _profiles_by_id(settings: BrowserDeliverySettings) -> dict[str, dict[str, object]]:
    return {str(profile["id"]): profile for profile in settings.profiles}


def test_central_browser_delivery_labels_preview_scope() -> None:
    settings = _build_source_aware_browser_delivery(
        requested=BrowserDeliverySettings(default_profile="720p10"),
        source_capability=SourceCapability(width=1920, height=1080, fps=25),
        privacy={"blur_faces": False, "blur_plates": False},
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
    )

    profiles = _profiles_by_id(settings)

    assert settings.default_profile == "720p10"
    assert profiles["native"]["label"] == "Native camera"
    assert profiles["annotated"]["label"] == "Annotated"
    assert profiles["720p10"]["label"] == "720p10 viewer preview"
    assert profiles["720p10"]["description"] == (
        "Reduces master-to-browser bandwidth only; central inference still ingests "
        "the native camera stream."
    )


def test_edge_browser_delivery_labels_edge_bandwidth_scope() -> None:
    edge_node_id = uuid4()

    settings = _build_source_aware_browser_delivery(
        requested=BrowserDeliverySettings(default_profile="720p10"),
        source_capability=SourceCapability(width=1920, height=1080, fps=25),
        privacy={"blur_faces": False, "blur_plates": False},
        processing_mode=ProcessingMode.EDGE,
        edge_node_id=edge_node_id,
    )

    profiles = _profiles_by_id(settings)

    assert profiles["native"]["label"] == "Native edge passthrough"
    assert profiles["annotated"]["label"] == "Annotated edge stream"
    assert profiles["720p10"]["label"] == "720p10 edge bandwidth saver"
    assert profiles["720p10"]["description"] == (
        "Downscaled on the edge node before remote browser delivery."
    )


def test_native_with_privacy_resolves_to_processed_profile() -> None:
    settings = _build_source_aware_browser_delivery(
        requested=BrowserDeliverySettings(default_profile="native"),
        source_capability=SourceCapability(width=1920, height=1080, fps=25),
        privacy={"blur_faces": True, "blur_plates": False},
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
    )

    assert settings.default_profile == "annotated"
    assert settings.native_status.available is False
    assert settings.native_status.reason == "privacy_filtering_required"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_browser_delivery_profiles.py -q
```

Expected: FAIL because `annotated` is not a valid profile id and `_build_source_aware_browser_delivery()` does not accept `processing_mode` or `edge_node_id`.

- [ ] **Step 3: Extend the profile schema**

In `backend/src/argus/api/contracts.py`, replace the existing browser profile id and default profiles with:

```python
BrowserDeliveryProfileId = Literal["native", "annotated", "1080p15", "720p10", "540p5"]


def _default_browser_delivery_profiles() -> list[dict[str, Any]]:
    return [
        {"id": "native", "kind": "passthrough"},
        {"id": "annotated", "kind": "transcode"},
        {"id": "1080p15", "kind": "transcode", "w": 1920, "h": 1080, "fps": 15},
        {"id": "720p10", "kind": "transcode", "w": 1280, "h": 720, "fps": 10},
        {"id": "540p5", "kind": "transcode", "w": 960, "h": 540, "fps": 5},
    ]
```

In `BrowserDeliveryProfile`, add optional label fields:

```python
class BrowserDeliveryProfile(BaseModel):
    id: BrowserDeliveryProfileId
    kind: Literal["passthrough", "transcode"]
    w: int | None = Field(default=None, gt=0)
    h: int | None = Field(default=None, gt=0)
    fps: int | None = Field(default=None, ge=1)
    label: str | None = None
    description: str | None = None
    reason: str | None = None

    model_config = ConfigDict(extra="allow")
```

- [ ] **Step 4: Add source-aware profile labeling**

In `backend/src/argus/services/app.py`, update `_build_source_aware_browser_delivery()` to accept `processing_mode` and `edge_node_id`, and add these helpers near it:

```python
def _is_edge_delivery_context(
    *,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> bool:
    return processing_mode is ProcessingMode.EDGE or edge_node_id is not None


def _decorate_browser_delivery_profile(
    profile: BrowserDeliveryProfile,
    *,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> BrowserDeliveryProfile:
    is_edge = _is_edge_delivery_context(
        processing_mode=processing_mode,
        edge_node_id=edge_node_id,
    )
    if profile.id == "native":
        return profile.model_copy(
            update={
                "label": "Native edge passthrough" if is_edge else "Native camera",
                "description": (
                    "Clean edge MediaMTX passthrough relayed to the browser."
                    if is_edge
                    else "Clean camera passthrough through master MediaMTX."
                ),
            }
        )
    if profile.id == "annotated":
        return profile.model_copy(
            update={
                "label": "Annotated edge stream" if is_edge else "Annotated",
                "description": (
                    "Full-rate processed stream published by the edge worker."
                    if is_edge
                    else "Full-rate processed stream published by the central worker."
                ),
            }
        )
    if is_edge:
        return profile.model_copy(
            update={
                "label": f"{profile.id} edge bandwidth saver",
                "description": "Downscaled on the edge node before remote browser delivery.",
            }
        )
    return profile.model_copy(
        update={
            "label": f"{profile.id} viewer preview",
            "description": (
                "Reduces master-to-browser bandwidth only; central inference still ingests "
                "the native camera stream."
            ),
        }
    )
```

Then update `_build_source_aware_browser_delivery()` so allowed profiles are decorated and native is blocked when privacy requires filtering:

```python
def _build_source_aware_browser_delivery(
    *,
    requested: BrowserDeliverySettings,
    source_capability: SourceCapability | None,
    privacy: dict[str, object],
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> BrowserDeliverySettings:
    derived_profiles = derive_browser_profiles(source_capability)
    native_available = (
        requested.allow_native_on_demand
        and not bool(privacy.get("blur_faces", True))
        and not bool(privacy.get("blur_plates", True))
    )
    blocked_profile_ids: set[BrowserDeliveryProfileId] = set()
    native_reason = None
    if not requested.allow_native_on_demand:
        native_reason = "native_disabled"
        blocked_profile_ids.add("native")
    elif not native_available:
        native_reason = "privacy_filtering_required"
        blocked_profile_ids.add("native")

    allowed_profile_ids = {
        profile.id for profile in derived_profiles.allowed if profile.id not in blocked_profile_ids
    }
    default_profile = _resolve_default_browser_profile(
        requested.default_profile,
        allowed_profile_ids,
    )
    decorated_allowed = [
        _decorate_browser_delivery_profile(
            profile,
            processing_mode=processing_mode,
            edge_node_id=edge_node_id,
        )
        for profile in derived_profiles.allowed
    ]
    decorated_unsupported = [
        _decorate_browser_delivery_profile(
            profile,
            processing_mode=processing_mode,
            edge_node_id=edge_node_id,
        )
        for profile in derived_profiles.unsupported
    ]

    return BrowserDeliverySettings(
        default_profile=default_profile,
        allow_native_on_demand=requested.allow_native_on_demand,
        profiles=[
            profile.model_dump(exclude_none=True, mode="python")
            for profile in decorated_allowed
        ],
        unsupported_profiles=[
            profile.model_dump(exclude_none=True, mode="python")
            for profile in decorated_unsupported
        ],
        native_status=NativeAvailability(available=native_available, reason=native_reason),
    )
```

Update `_resolve_default_browser_profile()`:

```python
def _resolve_default_browser_profile(
    requested_profile: BrowserDeliveryProfileId,
    allowed_profile_ids: set[BrowserDeliveryProfileId],
) -> BrowserDeliveryProfileId:
    fallback_order: tuple[BrowserDeliveryProfileId, ...]
    if requested_profile == "native":
        fallback_order = ("native", "annotated", "720p10", "540p5")
    else:
        fallback_order = (requested_profile, "720p10", "540p5", "annotated", "native")
    for profile_id in fallback_order:
        if profile_id in allowed_profile_ids:
            return profile_id
    return "annotated" if "annotated" in allowed_profile_ids else "native"
```

- [ ] **Step 5: Update call sites**

Every call to `_build_source_aware_browser_delivery()` in `backend/src/argus/services/app.py` must pass:

```python
processing_mode=camera.processing_mode,
edge_node_id=camera.edge_node_id,
```

For create/update paths that use a payload before a `Camera` row exists, pass:

```python
processing_mode=payload.processing_mode,
edge_node_id=payload.edge_node_id,
```

Use `rg -n "_build_source_aware_browser_delivery\\(" backend/src/argus/services/app.py` to verify every call includes both new arguments.

- [ ] **Step 6: Run backend profile tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_browser_delivery_profiles.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/tests/services/test_browser_delivery_profiles.py
git commit -m "feat(streams): label browser delivery profiles by source"
```

---

## Task 2: Worker Config Uses Honest Native And Annotated Settings

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Update central native worker config test**

In `backend/tests/services/test_camera_worker_config.py`, rename `test_central_native_browser_delivery_without_privacy_uses_clean_processed_stream` to:

```python
def test_central_native_browser_delivery_without_privacy_keeps_passthrough_stream() -> None:
```

Update its final assertion:

```python
    assert config.stream.model_dump() == {
        "profile_id": "native",
        "kind": "passthrough",
        "width": None,
        "height": None,
        "fps": 17,
    }
```

- [ ] **Step 2: Add annotated worker config test**

Add this test below the central native test:

```python
def test_annotated_browser_delivery_uses_processed_full_rate_stream() -> None:
    camera = Camera(
        id=uuid4(),
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={"blur_faces": False, "blur_plates": False, "method": "gaussian", "strength": 7},
        browser_delivery={
            "default_profile": "annotated",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=17,
    )
    primary_model = Model(
        id=camera.primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.stream.model_dump() == {
        "profile_id": "annotated",
        "kind": "transcode",
        "width": None,
        "height": None,
        "fps": 17,
    }
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_camera_worker_config.py -q
```

Expected: FAIL because central native still resolves through the processed-native branch and `annotated` transcode has no width/height/fps fields.

- [ ] **Step 4: Remove processed-native behavior**

In `backend/src/argus/services/app.py`, replace `_resolve_worker_stream_settings()` with:

```python
def _resolve_worker_stream_settings(
    *,
    browser_delivery: BrowserDeliverySettings,
    fps_cap: int,
) -> WorkerStreamSettings:
    profile_payloads = browser_delivery.profiles or BrowserDeliverySettings().profiles
    profiles_by_id = {str(profile["id"]): dict(profile) for profile in profile_payloads}
    if "native" not in profiles_by_id:
        profiles_by_id["native"] = {"id": "native", "kind": "passthrough"}
    if "annotated" not in profiles_by_id:
        profiles_by_id["annotated"] = {"id": "annotated", "kind": "transcode"}
    selected = profiles_by_id.get(browser_delivery.default_profile)
    if selected is None:
        selected = profiles_by_id["native"]
    kind = str(selected.get("kind", "passthrough"))
    if kind == "transcode":
        target_width = selected.get("w")
        target_height = selected.get("h")
        target_fps = selected.get("fps")
        return WorkerStreamSettings(
            profile_id=browser_delivery.default_profile,
            kind="transcode",
            width=int(target_width) if target_width is not None else None,
            height=int(target_height) if target_height is not None else None,
            fps=(
                min(max(1, fps_cap), int(target_fps))
                if target_fps is not None
                else max(1, fps_cap)
            ),
        )
    return WorkerStreamSettings(
        profile_id=browser_delivery.default_profile,
        kind="passthrough",
        width=None,
        height=None,
        fps=max(1, fps_cap),
    )
```

Delete `_uses_processed_native_delivery()`.

Update all call sites of `_resolve_worker_stream_settings()` to remove `processed_native=...`.

- [ ] **Step 5: Normalize worker config through source-aware delivery**

In `_camera_to_worker_config()`, replace the direct `BrowserDeliverySettings.model_validate(...)` assignment with:

```python
    requested_browser_delivery = BrowserDeliverySettings.model_validate(
        camera.browser_delivery or BrowserDeliverySettings().model_dump(mode="python")
    )
    source_capability = (
        SourceCapability.model_validate(camera.source_capability)
        if camera.source_capability is not None
        else None
    )
    browser_delivery = _build_source_aware_browser_delivery(
        requested=requested_browser_delivery,
        source_capability=source_capability,
        privacy=camera.privacy,
        processing_mode=camera.processing_mode,
        edge_node_id=camera.edge_node_id,
    )
```

This ensures old saved `native` plus privacy settings do not leak into worker config as passthrough.

- [ ] **Step 6: Run worker config tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_camera_worker_config.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/services/app.py backend/tests/services/test_camera_worker_config.py
git commit -m "fix(streams): make native worker config true passthrough"
```

---

## Task 3: Stream Access And Edge Relay Match Profile Kind

**Files:**
- Modify: `backend/src/argus/streaming/webrtc.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/streaming/test_webrtc.py`
- Modify: `backend/tests/services/test_stream_service.py`

- [ ] **Step 1: Add edge transcode stream access test**

In `backend/tests/streaming/test_webrtc.py`, add:

```python
def test_resolve_stream_access_returns_annotated_variant_for_edge_transcode_profile() -> None:
    camera_id = uuid4()

    access = resolve_stream_access(
        camera_id=camera_id,
        processing_mode=ProcessingMode.EDGE,
        edge_node_id=uuid4(),
        stream_kind="transcode",
        privacy={"blur_faces": False, "blur_plates": False},
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        webrtc_base_url="http://mediamtx.internal:8889",
        hls_base_url="http://mediamtx.internal:8888",
        mjpeg_base_url="http://mediamtx.internal:8890",
    )

    assert access.mode is StreamMode.ANNOTATED_WHIP
    assert access.path_name == f"cameras/{camera_id}/annotated"
    assert access.rtsp_url == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/annotated"
    assert access.whep_url == f"http://mediamtx.internal:8889/cameras/{camera_id}/annotated/whep"
```

- [ ] **Step 2: Update service-level central native test**

In `backend/tests/services/test_stream_service.py`, rename `test_stream_service_resolves_central_native_delivery_without_privacy_to_clean_processed` to:

```python
async def test_stream_service_resolves_central_native_delivery_without_privacy_to_passthrough(
```

Update the assertions:

```python
    assert access.mode is StreamMode.PASSTHROUGH
    assert access.path_name == f"cameras/{camera_id}/passthrough"
```

- [ ] **Step 3: Add edge transcode relay service test**

Add this test in `backend/tests/services/test_stream_service.py`:

```python
@pytest.mark.asyncio
async def test_stream_service_relay_edge_transcode_path_from_edge_mediamtx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    tenant_id = uuid4()
    edge_node_id = uuid4()
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=edge_node_id,
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
            "default_profile": "720p10",
            "allow_native_on_demand": True,
            "profiles": [
                {"id": "native", "kind": "passthrough"},
                {"id": "annotated", "kind": "transcode"},
                {"id": "720p10", "kind": "transcode", "w": 1280, "h": 720, "fps": 10},
            ],
        },
        frame_skip=1,
        fps_cap=25,
    )

    async def fake_load_camera(session, requested_tenant_id, requested_camera_id):
        assert requested_tenant_id == tenant_id
        assert requested_camera_id == camera_id
        return camera

    monkeypatch.setattr("argus.services.app._load_camera", fake_load_camera)

    mediamtx = _DummyMediaMTXClient()
    service = StreamService(
        session_factory=_DummySessionFactory(),
        mediamtx=mediamtx,
        negotiator=_DummyNegotiator(),
        settings=Settings(
            _env_file=None,
            enable_startup_services=False,
            edge_mediamtx_rtsp_base_urls={str(edge_node_id): "rtsp://jetson.local:8554"},
        ),
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
    assert len(mediamtx.ensured_paths) == 1
    path_name, source, source_on_demand = mediamtx.ensured_paths[0]
    assert path_name == f"cameras/{camera_id}/annotated"
    assert source.startswith(f"rtsp://jetson.local:8554/cameras/{camera_id}/annotated?")
    assert source_on_demand is True
```

- [ ] **Step 4: Run tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/streaming/test_webrtc.py tests/services/test_stream_service.py -q
```

Expected: FAIL because edge transcode still resolves to passthrough and the edge relay only runs for passthrough mode.

- [ ] **Step 5: Update stream access resolution**

In `backend/src/argus/streaming/webrtc.py`, replace the decision block at the start of `resolve_stream_access()` with:

```python
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
```

Update `_uses_central_delivery()`:

```python
def _uses_central_delivery(
    *,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> bool:
    return processing_mode in {ProcessingMode.CENTRAL, ProcessingMode.HYBRID} and edge_node_id is None
```

- [ ] **Step 6: Generalize edge relay**

In `backend/src/argus/services/app.py`, rename `_ensure_edge_passthrough_relay()` to `_ensure_edge_stream_relay()` and change the guard:

```python
    async def _ensure_edge_stream_relay(
        self,
        *,
        camera: Camera,
        access: StreamAccess,
    ) -> None:
        if camera.edge_node_id is None:
            return
```

Update the call site:

```python
        await self._ensure_edge_stream_relay(camera=camera, access=access)
```

Keep the rest of the function behavior the same, so the edge source URL is built from `access.path_name` for either `passthrough` or `annotated`.

- [ ] **Step 7: Run stream tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/streaming/test_webrtc.py tests/services/test_stream_service.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/streaming/webrtc.py backend/src/argus/services/app.py backend/tests/streaming/test_webrtc.py backend/tests/services/test_stream_service.py
git commit -m "fix(streams): resolve edge transcode to annotated relay"
```

---

## Task 4: MediaMTX Registers Jetson Non-Native Profiles As Processed Streams

**Files:**
- Modify: `backend/src/argus/streaming/mediamtx.py`
- Modify: `backend/tests/streaming/test_mediamtx.py`

- [ ] **Step 1: Add Jetson transcode registration test**

In `backend/tests/streaming/test_mediamtx.py`, add:

```python
@pytest.mark.asyncio
async def test_mediamtx_client_registers_annotated_for_jetson_transcode_profile() -> None:
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
        target_width=1280,
        target_height=720,
        target_fps=10,
    )

    assert registration.mode is StreamMode.ANNOTATED_WHIP
    assert registration.path_name == f"cameras/{camera_id}/annotated"
    assert registration.publish_path == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/annotated"
    assert registration.target_width == 1280
    assert registration.target_height == 720
    assert registration.target_fps == 10
    assert requests == [
        (
            "POST",
            f"http://mediamtx.internal:9997/v3/config/paths/replace/cameras/{camera_id}/passthrough",
            {
                "name": f"cameras/{camera_id}/passthrough",
                "source": "rtsp://camera.internal/live",
                "sourceOnDemand": True,
            },
        ),
        (
            "POST",
            f"http://mediamtx.internal:9997/v3/config/paths/replace/cameras/{camera_id}/annotated",
            {
                "name": f"cameras/{camera_id}/annotated",
                "source": "publisher",
                "sourceOnDemand": False,
            },
        ),
    ]

    await client.close()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/streaming/test_mediamtx.py::test_mediamtx_client_registers_annotated_for_jetson_transcode_profile -q
```

Expected: FAIL because Jetson transcode currently falls back to passthrough.

- [ ] **Step 3: Register annotated path for non-native Jetson delivery**

In `backend/src/argus/streaming/mediamtx.py`, replace the profile-specific central-only annotated branch with a branch that handles all non-privacy transcode profiles:

```python
        if not privacy.requires_filtering:
            annotated_name = f"cameras/{camera_id}/annotated"
            annotated_path = f"{self.rtsp_base_url}/{annotated_name}"
            await self._ensure_path(
                annotated_name,
                source="publisher",
                source_on_demand=False,
            )
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.ANNOTATED_WHIP,
                path_name=annotated_name,
                read_path=annotated_path,
                publish_path=annotated_path,
                managed_path_config=True,
                target_fps=max(1, target_fps),
                target_width=target_width,
                target_height=target_height,
                ingest_path=ingest_path,
            )
```

Keep the existing privacy preview branch after this block so privacy-enabled edge streams remain filtered previews.

- [ ] **Step 4: Run MediaMTX tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/streaming/test_mediamtx.py -q
```

Expected: PASS. If an existing test expected Jetson transcode fallback to passthrough, update it to the new contract.

- [ ] **Step 5: Commit**

Run:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/streaming/mediamtx.py backend/tests/streaming/test_mediamtx.py
git commit -m "fix(mediamtx): publish jetson non-native streams"
```

---

## Task 5: Camera Wizard Uses Honest Profile Labels

**Files:**
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Add label assertions to CameraWizard tests**

In `frontend/src/components/cameras/CameraWizard.test.tsx`, add or update tests so the Browser delivery selector is checked for mode-specific labels:

```tsx
expect(
  within(screen.getByLabelText(/browser delivery profile/i)).getByRole("option", {
    name: "720p10 viewer preview",
  }),
).toBeInTheDocument();
```

For an edge-mode flow, assert:

```tsx
expect(
  within(screen.getByLabelText(/browser delivery profile/i)).getByRole("option", {
    name: "720p10 edge bandwidth saver",
  }),
).toBeInTheDocument();
```

Use existing setup helpers and existing probe mocks. Include `label` and `description` in mocked profile payloads where the mock comes from `/api/v1/cameras/source-probe`.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: FAIL because options currently render raw ids.

- [ ] **Step 3: Add fallback label helpers**

In `frontend/src/components/cameras/CameraWizard.tsx`, extend `BrowserDeliveryProfilePayload`:

```ts
  label?: string | null;
  description?: string | null;
```

Add this helper near `resolveBrowserDeliveryProfile()`:

```ts
function formatBrowserDeliveryProfileLabel(
  profile: BrowserDeliveryProfilePayload,
  processingMode: CameraWizardData["processingMode"],
) {
  if (profile.label) {
    return profile.label;
  }
  const isEdge = processingMode === "edge";
  if (profile.id === "native") {
    return isEdge ? "Native edge passthrough" : "Native camera";
  }
  if (profile.id === "annotated") {
    return isEdge ? "Annotated edge stream" : "Annotated";
  }
  return isEdge ? `${profile.id} edge bandwidth saver` : `${profile.id} viewer preview`;
}
```

Update `BrowserDeliveryProfile` type:

```ts
type BrowserDeliveryProfile = "native" | "annotated" | "1080p15" | "720p10" | "540p5";
```

Update `DEFAULT_BROWSER_DELIVERY_PROFILES` to include:

```ts
  { id: "annotated", kind: "transcode" },
```

Update `isBrowserDeliveryProfile()` to accept `"annotated"`.

- [ ] **Step 4: Render labels in the select**

Replace the option content:

```tsx
                      {profile.id}
```

with:

```tsx
                      {formatBrowserDeliveryProfileLabel(profile, data.processingMode)}
```

Keep the option `value={profile.id}` unchanged.

- [ ] **Step 5: Adjust delivery copy**

Replace the context panel copy for `"Privacy, Processing & Delivery"` with:

```ts
        return data.processingMode === "edge"
          ? "Native is clean passthrough. Processed profiles are built on the edge before browser delivery."
          : "Native is clean passthrough. Processed preview profiles reduce master-to-browser viewing bandwidth only.";
```

Add `data.processingMode` to the `useMemo()` dependency list.

Replace the explanatory paragraph under the select with:

```tsx
                {data.processingMode === "edge"
                  ? "Native stays clean passthrough. Processed profiles are published by the edge worker for annotated or reduced remote viewing."
                  : "Native stays clean passthrough. Processed profiles are published by the central worker for annotated or reduced browser viewing."}
```

- [ ] **Step 6: Run CameraWizard tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/yann.moren/vision
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraWizard.test.tsx
git commit -m "feat(ui): label browser delivery profiles by deployment"
```

---

## Task 6: Live Page Shows Actual Stream Mode

**Files:**
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Update stale native test expectation**

In `frontend/src/pages/Live.test.tsx`, update the test currently expecting `native clean` while telemetry says `annotated-whip`. Keep the fake telemetry frame:

```ts
stream_mode: "annotated-whip",
```

Change expectations:

```ts
expect(await screen.findByText(/telemetry stale/i)).toBeInTheDocument();
expect(screen.getByText(/annotated-whip/i)).toBeInTheDocument();
expect(screen.queryByText(/native clean/i)).not.toBeInTheDocument();
expect(screen.queryByText(/^offline$/i)).not.toBeInTheDocument();
```

- [ ] **Step 2: Add real passthrough display assertion**

Add a Live test where camera `default_profile` is `native`, telemetry `stream_mode` is `passthrough`, and the expectation is:

```ts
expect(screen.getByText(/passthrough/i)).toBeInTheDocument();
expect(screen.queryByText(/annotated-whip/i)).not.toBeInTheDocument();
```

- [ ] **Step 3: Run Live tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx
```

Expected: FAIL because `formatStreamMode()` still masks native privacy-off telemetry as `native clean`.

- [ ] **Step 4: Replace Live stream mode formatter**

In `frontend/src/pages/Live.tsx`, replace `formatStreamMode()` with:

```ts
function formatStreamMode(
  _camera: CameraResponse,
  frame: TelemetryFrame,
): string {
  if (frame.stream_mode === "filtered-preview") {
    return "filtered-preview";
  }
  if (frame.stream_mode === "passthrough") {
    return "passthrough";
  }
  return frame.stream_mode;
}
```

Add a helper near it:

```ts
function formatDeliveryProfile(camera: CameraResponse): string {
  const defaultProfile = camera.browser_delivery?.default_profile ?? "720p10";
  const selectedProfile = camera.browser_delivery?.profiles?.find(
    (profile) => profile.id === defaultProfile,
  );
  const label = typeof selectedProfile?.label === "string" ? selectedProfile.label : null;
  return label ?? defaultProfile;
}
```

Update the camera subtitle:

```tsx
                          {camera.processing_mode} processing · {formatDeliveryProfile(camera)}
```

Where stream mode is displayed in the tile body, keep calling `formatStreamMode(camera, frame)` so it now shows the real mode.

- [ ] **Step 5: Run Live tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
cd /Users/yann.moren/vision
git add frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx
git commit -m "fix(live): show actual browser stream mode"
```

---

## Task 7: Docs And Generated API Types

**Files:**
- Modify: `frontend/src/lib/api.generated.ts`
- Modify: `docs/deployment-modes-and-matrix.md`
- Modify: `docs/imac-master-orin-lab-test-guide.md`

- [ ] **Step 1: Regenerate frontend API types**

Start the backend if it is not running, then run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend generate:api
```

Expected: `frontend/src/lib/api.generated.ts` updates `BrowserDeliveryProfileId` to include `annotated` and profile schema fields to include `label` and `description`.

- [ ] **Step 2: Update deployment mode docs**

In `docs/deployment-modes-and-matrix.md`, update the browser delivery terminology section so it says:

```markdown
- `native` browser delivery is always true passthrough. It never means a clean worker-published stream.
- Central reduced profiles reduce master-to-browser viewing bandwidth only. Central inference still ingests the native camera stream.
- Edge reduced profiles are built on the edge node before remote browser delivery, so they can reduce edge-to-master/browser video bandwidth.
- `annotated` is the full-rate worker-published processed stream with drawn boxes.
```

- [ ] **Step 3: Update Jetson lab guide**

In `docs/imac-master-orin-lab-test-guide.md`, update the central/edge browser delivery notes so they use these phrases:

```markdown
For central cameras, `720p10` is a viewer preview. It helps when a browser connects remotely to the iMac UI, but it does not reduce the camera-to-iMac inference ingest.
```

```markdown
For Jetson edge cameras, `720p10` is built on the Jetson and then relayed through the iMac MediaMTX, so it can reduce remote viewing bandwidth.
```

- [ ] **Step 4: Run doc and API diff check**

Run:

```bash
cd /Users/yann.moren/vision
git diff -- frontend/src/lib/api.generated.ts docs/deployment-modes-and-matrix.md docs/imac-master-orin-lab-test-guide.md
```

Expected: only delivery-contract wording and generated schema changes.

- [ ] **Step 5: Commit**

Run:

```bash
cd /Users/yann.moren/vision
git add frontend/src/lib/api.generated.ts docs/deployment-modes-and-matrix.md docs/imac-master-orin-lab-test-guide.md
git commit -m "docs: clarify browser delivery bandwidth scope"
```

---

## Task 8: Full Verification

**Files:**
- No source edits unless verification reveals a bug in the previous tasks.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_browser_delivery_profiles.py \
  tests/services/test_camera_worker_config.py \
  tests/services/test_stream_service.py \
  tests/streaming/test_webrtc.py \
  tests/streaming/test_mediamtx.py \
  -q
```

Expected: all pass.

- [ ] **Step 2: Run focused frontend tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/pages/Live.test.tsx
```

Expected: all pass.

- [ ] **Step 3: Run static checks**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run ruff check src tests
```

Expected: PASS.

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend build
```

Expected: PASS.

- [ ] **Step 4: Optional full validation**

Run this if local services are healthy and there is time:

```bash
cd /Users/yann.moren/vision
make verify-all
```

Expected: PASS.

- [ ] **Step 5: Manual lab smoke checks**

Central camera checks:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/api/v1/cameras/$CENTRAL_CAMERA_ID/worker-config |
  python3 -m json.tool | sed -n '/"stream"/,/},/p'
```

Expected for `native`:

```json
"stream": {
  "profile_id": "native",
  "kind": "passthrough",
  "width": null,
  "height": null,
  "fps": 25
}
```

Expected for `720p10`:

```json
"stream": {
  "profile_id": "720p10",
  "kind": "transcode",
  "width": 1280,
  "height": 720,
  "fps": 10
}
```

Edge camera checks:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/api/v1/cameras/$EDGE_CAMERA_ID/worker-config |
  python3 -m json.tool | sed -n '/"stream"/,/},/p'
```

Expected for edge `native`: passthrough.

Expected for edge `720p10`: transcode 1280x720 at 10 FPS, and Jetson worker logs should show a nonzero `publish_stream` stage once the reduced/annotated stream is active.

- [ ] **Step 6: Handle verification failures**

If verification fails, return to the task that introduced the failing behavior, adjust that task's implementation, and amend that task's focused commit before rerunning Task 8.

---

## Self-Review

Spec coverage:

- Native passthrough in central and edge: Tasks 2 and 3.
- Non-native processed streams in central and edge: Tasks 2, 3, and 4.
- Central reduced profile label scope: Tasks 1, 5, and 7.
- Edge reduced profile label scope: Tasks 1, 5, and 7.
- Actual Live stream mode display: Task 6.
- Telemetry/inference independence: covered by stream-only changes and Task 8 manual checks.
- Hybrid: documented as out of implementation scope while stream access treats unassigned hybrid as central-like.

Deferred-work scan:

- The plan contains no deferred blanks.

Type consistency:

- `annotated` is added to backend and frontend profile id unions.
- `label` and `description` are added to backend schema and frontend payload type.
- `WorkerStreamSettings.kind` remains `passthrough | transcode`.
- `StreamMode` remains unchanged.
