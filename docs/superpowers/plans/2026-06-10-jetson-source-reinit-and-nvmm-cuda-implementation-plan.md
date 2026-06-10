# Jetson Source Reinitialization And NVMM/CUDA Frame Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dynamic camera source/profile reinitialization and an opt-in NVMM/CUDA inference frame path for Jetson, without DeepStream and without hardware encode.

**Architecture:** Extend the existing camera command and runtime report contracts with a redacted source profile hash. Reuse the current `CameraSource.reconfigure()` seam for atomic capture reopen, and add a frame-envelope fast path so TensorRT can consume GPU-prepared input before CPU BGR materialization. Keep `gstreamer_appsink` as the default until the native lane has separate live PASS evidence.

**Tech Stack:** Python, pytest, Pydantic, SQLAlchemy/Alembic, NumPy, PyGObject/GStreamer, optional Jetson native extension, React/TypeScript camera wizard, real Jetson live smoke.

---

## File Map

- Modify `backend/src/argus/api/contracts.py`: add command/report/setup-preview fields for source profile identity.
- Modify `backend/src/argus/models/tables.py`: persist `WorkerRuntimeReport.source_profile_hash`.
- Create `backend/src/argus/migrations/versions/0048_worker_runtime_report_source_profile_hash.py`: add/drop source profile hash column.
- Modify `backend/src/argus/services/app.py`: compute source profile hashes, publish camera-source commands, invalidate setup preview cache by hash.
- Modify `backend/src/argus/inference/engine.py`: accept source update commands, reconfigure frame source, report source profile hash, use detector frame fast path.
- Modify `backend/src/argus/vision/camera.py`: reopen capture when source URI/hash changes.
- Create `backend/src/argus/vision/frames.py`: shared captured-frame protocols and CPU frame wrapper.
- Modify `backend/src/argus/vision/jetson_nvmm_capture.py`: optional native capture wrapper and fake-extension-friendly probe contract.
- Modify `backend/native/jetson_capture/README.md`: document no-encode native extension contract.
- Modify `backend/src/argus/services/deployment_nodes.py` and/or fleet summary service files: present awaiting profile heartbeat.
- Modify `frontend/src/hooks/use-camera-setup-preview.ts`: include source hash/stale fields.
- Modify `frontend/src/components/cameras/CameraWizard.tsx`: block current calibration source-point edits when preview is stale.
- Update generated OpenAPI files after backend schema changes.
- Tests:
  - `backend/tests/services/test_camera_service.py`
  - `backend/tests/inference/test_engine.py`
  - `backend/tests/vision/test_camera.py`
  - `backend/tests/vision/test_jetson_nvmm_capture.py`
  - `backend/tests/services/test_deployment_nodes.py`
  - `backend/tests/api/test_operations_endpoints.py`
  - `frontend/src/components/cameras/CameraWizard.test.tsx`

## Task 1: Source Profile Hash And Camera Command Contract

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_camera_service.py`

- [ ] **Step 1: Write failing hash and command tests**

Add to `backend/tests/services/test_camera_service.py`:

```python
def test_source_profile_hash_changes_with_source_and_stream_without_leaking_uri() -> None:
    capability = SourceCapability(width=1280, height=720, fps=20, codec="h264", aspect_ratio="16:9")
    stream = WorkerStreamSettings(profile_id="720p20", kind="transcode", width=1280, height=720, fps=20)

    first = app_services._source_profile_hash(
        source_kind=CameraSourceKind.RTSP,
        source_uri="rtsp://camera.local:8554/ch1?token=fake-token-a",
        source_capability=capability,
        stream=stream,
    )
    second = app_services._source_profile_hash(
        source_kind=CameraSourceKind.RTSP,
        source_uri="rtsp://camera.local:8554/ch2?token=fake-token-b",
        source_capability=capability,
        stream=stream,
    )

    assert first != second
    assert len(first) == 64
    assert "fake-token-a" not in first
    assert "camera.local" not in first
```

Add to `test_update_camera_reprobes_source_capability_when_rtsp_changes` after the existing response assertions:

```python
    assert events.calls
    _subject, command, _serialized = events.calls[-1]
    payload = command.model_dump(mode="python")  # type: ignore[attr-defined]
    assert payload["camera"]["source_uri"] == "rtsp://new-camera/live"
    assert payload["source_capability"] == {
        "width": 1280,
        "height": 720,
        "fps": 20,
        "codec": "h264",
        "aspect_ratio": "16:9",
    }
    assert len(payload["source_profile_hash"]) == 64
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/services/test_camera_service.py -k "source_profile_hash or reprobes_source_capability" -q
```

Expected: FAIL because `_source_profile_hash` and camera command fields do not exist.

- [ ] **Step 3: Add contract fields**

In `backend/src/argus/api/contracts.py`, update `CameraCommandPayload`:

```python
class CameraCommandPayload(BaseModel):
    active_classes: list[str] | None = None
    runtime_vocabulary: list[str] | None = None
    runtime_vocabulary_source: RuntimeVocabularySource | None = None
    runtime_vocabulary_version: int | None = None
    tracker_type: TrackerType | None = None
    camera: WorkerCameraSettings | None = None
    source_capability: SourceCapability | None = None
    source_profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
    privacy: WorkerPrivacySettings | None = None
    stream: WorkerStreamSettings | None = None
    attribute_rules: list[dict[str, Any]] | None = None
    incident_rules: list[WorkerIncidentRule] | None = None
    zones: list[WorkerZone] | None = None
    vision_profile: SceneVisionProfile | None = None
    detection_regions: list[DetectionRegion] | None = None
    homography: dict[str, Any] | None = None
```

- [ ] **Step 4: Implement source profile hash helper**

In `backend/src/argus/services/app.py`, add imports if missing:

```python
import hashlib
import json
```

Add helper functions near source helpers:

```python
def _source_profile_hash(
    *,
    source_kind: CameraSourceKind,
    source_uri: str,
    source_capability: SourceCapability | None,
    stream: WorkerStreamSettings,
) -> str:
    payload = {
        "source_kind": source_kind.value,
        "source_uri_fingerprint": hashlib.sha256(source_uri.strip().encode("utf-8")).hexdigest(),
        "source_capability": (
            source_capability.model_dump(mode="json") if source_capability is not None else None
        ),
        "stream": stream.model_dump(mode="json"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

- [ ] **Step 5: Publish camera source command data**

In `_publish_camera_command()`, compute worker camera settings and source hash before constructing `CameraCommandPayload`:

```python
        rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, self.settings)
        source_uri, camera_source, worker_rtsp_url = _worker_camera_source_payload(
            camera,
            rtsp_url=rtsp_url,
        )
        worker_camera = WorkerCameraSettings(
            rtsp_url=worker_rtsp_url,
            source_uri=source_uri,
            camera_source=camera_source,
            frame_skip=int(camera.frame_skip or 1),
            fps_cap=int(camera.fps_cap or 25),
        )
        source_capability = (
            SourceCapability.model_validate(camera.source_capability)
            if camera.source_capability is not None
            else None
        )
        worker_stream = _resolve_worker_stream_settings(
            browser_delivery=BrowserDeliverySettings.model_validate(
                camera.browser_delivery or BrowserDeliverySettings().model_dump(mode="python")
            ),
            fps_cap=int(camera.fps_cap or 25),
        )
        source_profile_hash = _source_profile_hash(
            source_kind=_source_kind_from_camera(camera),
            source_uri=source_uri,
            source_capability=source_capability,
            stream=worker_stream,
        )
```

Then include these in the command:

```python
            camera=worker_camera,
            source_capability=source_capability,
            source_profile_hash=source_profile_hash,
            stream=worker_stream,
```

- [ ] **Step 6: Run tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/services/test_camera_service.py -k "source_profile_hash or reprobes_source_capability or publishes_stream_profile_command" -q
```

Expected: PASS.

- [ ] **Step 7: Ask before committing**

Ask for approval before committing this task. Do not push.

## Task 2: Worker Runtime Report Source Profile Hash

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0048_worker_runtime_report_source_profile_hash.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/services/supervisor_operations.py`
- Modify: `backend/src/argus/supervisor/operations_client.py`
- Test: `backend/tests/inference/test_engine.py`
- Test: `backend/tests/api/test_operations_endpoints.py`
- Test: `backend/tests/supervisor/test_operations_client.py`

- [ ] **Step 1: Write failing report propagation tests**

In `backend/tests/inference/test_engine.py`, add:

```python
@pytest.mark.asyncio
async def test_engine_runtime_report_includes_source_profile_hash() -> None:
    camera_id = uuid4()
    runtime_reporter = _RecordingRuntimeReporter()
    engine = InferenceEngine(
        config=_engine_config(camera_id).model_copy(update={"source_profile_hash": "a" * 64}),
        frame_source=_FakeFrameSource([np.zeros((32, 32, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type=tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        runtime_reporter=runtime_reporter,
        runtime_report_interval_seconds=0,
    )

    await engine.start()
    await engine.run_once()
    await engine.close()

    assert runtime_reporter.payloads[-1].source_profile_hash == "a" * 64
```

Add API/client assertions wherever `SupervisorRuntimeReportCreate` round-trips are already tested:

```python
source_profile_hash="b" * 64,
```

and assert the response contains the same value.

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k source_profile_hash -q
backend/.venv/bin/pytest backend/tests/api/test_operations_endpoints.py backend/tests/supervisor/test_operations_client.py -k runtime_report -q
```

Expected: FAIL because the report schema has no source profile hash.

- [ ] **Step 3: Add schema fields and migration**

In `SupervisorRuntimeReportCreate` and `SupervisorRuntimeReportResponse`, add:

```python
source_profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
```

In `WorkerRuntimeReport`, add:

```python
source_profile_hash: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
```

Create migration:

```python
"""add source profile hash to worker runtime reports"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0048_runtime_source_profile_hash"
down_revision = "0047_runtime_capture_backend"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "worker_runtime_reports",
        sa.Column("source_profile_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("worker_runtime_reports", "source_profile_hash")
```

- [ ] **Step 4: Populate and persist the field**

Add `source_profile_hash: str | None = None` to `EngineConfig`.

In `_maybe_record_runtime_report()`, include:

```python
source_profile_hash=self.config.source_profile_hash,
```

In backend operation service/client mapping, carry `source_profile_hash` into and out of `WorkerRuntimeReport`.

- [ ] **Step 5: Run tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k source_profile_hash -q
backend/.venv/bin/pytest backend/tests/api/test_operations_endpoints.py backend/tests/supervisor/test_operations_client.py -k runtime_report -q
backend/.venv/bin/alembic heads
```

Expected: tests PASS and Alembic head is `0048_runtime_source_profile_hash`.

## Task 3: Atomic Capture Reopen On Source/Profile Changes

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/vision/camera.py`
- Test: `backend/tests/inference/test_engine.py`
- Test: `backend/tests/vision/test_camera.py`

- [ ] **Step 1: Write failing engine source reconfigure test**

Extend `_ReconfigurableFrameSource.reconfigure()` in `backend/tests/inference/test_engine.py` to accept and record source fields:

```python
    def reconfigure(
        self,
        *,
        target_width: int | None,
        target_height: int | None,
        fps_cap: int,
        source_uri: str | None = None,
        source_profile_hash: str | None = None,
    ) -> None:
        self.reconfigure_calls.append(
            {
                "target_width": target_width,
                "target_height": target_height,
                "fps_cap": fps_cap,
                "source_uri": source_uri,
                "source_profile_hash": source_profile_hash,
            }
        )
```

Add:

```python
@pytest.mark.asyncio
async def test_engine_reconfigures_capture_source_when_camera_source_changes() -> None:
    camera_id = uuid4()
    frame_source = _ReconfigurableFrameSource([np.zeros((64, 64, 3), dtype=np.uint8)])
    engine = InferenceEngine(
        config=_engine_config(camera_id),
        frame_source=frame_source,
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type=tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=_FakeStreamClient(),
    )

    await engine.start()
    await engine.apply_command(
        CameraCommand(
            camera=CameraSettings(source_uri="rtsp://new-camera/live", frame_skip=1, fps_cap=20),
            stream=StreamSettings(profile_id="720p20", kind="transcode", width=1280, height=720, fps=20),
            source_profile_hash="c" * 64,
        )
    )
    await engine.close()

    assert engine.config.camera.source_uri == "rtsp://new-camera/live"
    assert engine.config.source_profile_hash == "c" * 64
    assert frame_source.reconfigure_calls[-1] == {
        "target_width": 1280,
        "target_height": 720,
        "fps_cap": 20,
        "source_uri": "rtsp://new-camera/live",
        "source_profile_hash": "c" * 64,
    }
```

- [ ] **Step 2: Write failing camera source reopen test**

Add to `backend/tests/vision/test_camera.py`:

```python
def test_camera_source_reconfigure_reopens_capture_when_source_uri_changes() -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    opened: list[str] = []
    released: list[str] = []

    class _Capture:
        def __init__(self, source: str) -> None:
            self.source = source

        def read(self) -> tuple[bool, np.ndarray]:
            return True, frame

        def release(self) -> None:
            released.append(self.source)

    def capture_factory(source: str | int, backend: int | None) -> _Capture:
        assert isinstance(source, str)
        opened.append(source)
        return _Capture(source)

    source = CameraSource(
        config=CameraSourceConfig(source_uri="rtsp://camera.local/ch1", fps_cap=20),
        platform_info=PlatformInfo(machine="x86_64", jetson=False),
        capture_factory=capture_factory,
        monotonic=perf_counter,
        sleep=lambda seconds: None,
    )

    source.reconfigure(
        target_width=1280,
        target_height=720,
        fps_cap=20,
        source_uri="rtsp://camera.local/ch2",
        source_profile_hash="d" * 64,
    )

    assert opened == ["rtsp://camera.local/ch1", "rtsp://camera.local/ch2"]
    assert released == ["rtsp://camera.local/ch1"]
    assert source.config.source_profile_hash == "d" * 64
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "camera_source_changes" -q
backend/.venv/bin/pytest backend/tests/vision/test_camera.py -k "source_uri_changes" -q
```

Expected: FAIL because command/config/reconfigure do not accept source fields yet.

- [ ] **Step 4: Extend command and config types**

In `backend/src/argus/inference/engine.py`, add to `CameraCommand`:

```python
camera: CameraSettings | None = None
source_profile_hash: str | None = None
```

Add to `EngineConfig`:

```python
source_profile_hash: str | None = None
```

Update `ReconfigurableFrameSource`:

```python
class ReconfigurableFrameSource(Protocol):
    def reconfigure(
        self,
        *,
        target_width: int | None,
        target_height: int | None,
        fps_cap: int,
        source_uri: str | None = None,
        source_profile_hash: str | None = None,
    ) -> None: ...
```

In `backend/src/argus/vision/camera.py`, add to `CameraSourceConfig`:

```python
source_profile_hash: str | None = None
```

and extend `CameraSource.reconfigure()` with the same optional fields. Build `next_config` with:

```python
source_uri=source_uri or self.config.source_uri,
source_profile_hash=source_profile_hash or self.config.source_profile_hash,
```

- [ ] **Step 5: Reconfigure from source command**

In `InferenceEngine.apply_command()`, before stream registration, apply source changes:

```python
        source_changed = False
        if command.camera is not None and command.camera != self.config.camera:
            self.config.camera = command.camera
            source_changed = True
        if (
            command.source_profile_hash is not None
            and command.source_profile_hash != self.config.source_profile_hash
        ):
            self.config.source_profile_hash = command.source_profile_hash
            source_changed = True
```

After stream registration logic, call `_reconfigure_frame_source_for_stream()` when `stream_changed or source_changed`.

In `_reconfigure_frame_source_for_stream()`, pass:

```python
source_uri=self.config.camera.resolved_source_uri,
source_profile_hash=self.config.source_profile_hash,
```

- [ ] **Step 6: Run tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "reconfigures_capture_source or stream_profile_changes" -q
backend/.venv/bin/pytest backend/tests/vision/test_camera.py -k "reconfigure" -q
```

Expected: PASS.

## Task 4: Setup Preview And Calibration Stale-State Protection

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `frontend/src/hooks/use-camera-setup-preview.ts`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Test: `backend/tests/services/test_camera_service.py`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Update: `frontend/src/lib/openapi.json`
- Update: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Write failing backend preview hash tests**

Add to `backend/tests/services/test_camera_service.py`:

```python
@pytest.mark.asyncio
async def test_setup_preview_does_not_reuse_cached_still_for_new_source_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, tenant_context, camera = _setup_preview_service_with_camera()
    captures: list[tuple[int, int]] = [(2304, 1296), (1280, 720)]

    def fake_capture(camera_arg, settings_arg):  # noqa: ANN001
        width, height = captures.pop(0)
        return app_services._SetupPreviewSnapshot(
            image_bytes=b"jpeg",
            frame_size=FrameSize(width=width, height=height),
            captured_at=datetime.now(tz=UTC),
            source_profile_hash=app_services._source_profile_hash_for_camera(camera_arg),
        )

    monkeypatch.setattr(app_services, "_capture_setup_preview_snapshot", fake_capture)

    first = await service.get_setup_preview(tenant_context, camera.id)
    camera.updated_at = camera.updated_at + timedelta(seconds=1)
    camera.source_capability = {"width": 1280, "height": 720, "fps": 20, "codec": "h264"}
    second = await service.get_setup_preview(tenant_context, camera.id)

    assert first.frame_size == FrameSize(width=2304, height=1296)
    assert second.frame_size == FrameSize(width=1280, height=720)
    assert first.source_profile_hash != second.source_profile_hash
    assert second.stale is False
```

Create `_setup_preview_service_with_camera()` in the test file by moving the repeated camera/service setup from `test_get_setup_preview_returns_frame_size_and_preview_url()` into a local helper, then reuse that helper in the new test and the original test.

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
backend/.venv/bin/pytest backend/tests/services/test_camera_service.py -k "setup_preview_does_not_reuse" -q
```

Expected: FAIL because preview snapshots and responses do not carry source hashes/stale state.

- [ ] **Step 3: Add backend preview fields**

In `CameraSetupPreviewResponse`, add:

```python
source_profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
source_capability: SourceCapability | None = None
stale: bool = False
```

In `_SetupPreviewSnapshot`, add:

```python
source_profile_hash: str | None = None
source_capability: SourceCapability | None = None
stale: bool = False
```

In `_SetupPreviewCacheEntry`, add:

```python
source_profile_hash: str | None = None
```

When capturing a fresh still, populate the hash and capability from the camera. Reuse a cached still as current only when `camera.updated_at`, expiry, and `source_profile_hash` all match. If refresh fails and an old still exists for a different hash, return it only with `stale=True`.

- [ ] **Step 4: Add frontend stale handling test**

In `frontend/src/components/cameras/CameraWizard.test.tsx`, add a test that mocks setup preview metadata:

```ts
server.use(
  http.get("*/api/v1/cameras/:cameraId/setup-preview", () =>
    HttpResponse.json({
      camera_id: "camera-1",
      preview_url: "/api/v1/cameras/camera-1/setup-preview/image?rev=12345",
      frame_size: { width: 2304, height: 1296 },
      captured_at: "2026-06-10T16:00:00Z",
      source_profile_hash: "a".repeat(64),
      source_capability: { width: 1280, height: 720, fps: 20, codec: "h264" },
      stale: true,
    }),
  ),
);
```

Assert that source-point editing controls are disabled until a non-stale preview is loaded.

- [ ] **Step 5: Implement frontend metadata propagation**

Update `use-camera-setup-preview.ts` payload types:

```ts
type CameraSetupPreviewPayload = {
  camera_id: string;
  preview_url: string;
  frame_size: { width: number; height: number };
  captured_at: string;
  source_profile_hash?: string | null;
  source_capability?: { width: number; height: number; fps?: number | null; codec?: string | null } | null;
  stale?: boolean;
};
```

In `CameraWizard.tsx`, treat `setupPreview.stale === true` as not current for source-point editing. Keep destination/world-plane editing available.

- [ ] **Step 6: Regenerate OpenAPI and run tests**

Run:

```bash
backend/.venv/bin/python -m argus.scripts.export_openapi_schema frontend/src/lib/openapi.json
corepack pnpm --dir frontend generate:api
```

Then run:

```bash
backend/.venv/bin/pytest backend/tests/services/test_camera_service.py -k "setup_preview" -q
corepack pnpm --dir frontend test CameraWizard.test.tsx
```

Expected: PASS.

## Task 5: Fleet/API Awaiting Profile Heartbeat Presentation

**Files:**
- Modify: `backend/src/argus/services/deployment_nodes.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/services/test_deployment_nodes.py`
- Test: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Write failing presentation tests**

In `backend/tests/services/test_deployment_nodes.py`, add a case where the camera's current source hash is `"e" * 64` and the latest runtime report hash is `"f" * 64`.

Assert:

```python
assert worker.runtime_status == WorkerRuntimeState.STARTING
assert worker.runtime_presentation == "awaiting_profile_heartbeat"
```

Add a case where no runtime report exists:

```python
assert worker.runtime_status == WorkerRuntimeState.NOT_REPORTED
assert worker.runtime_presentation == "awaiting_first_heartbeat"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/services/test_deployment_nodes.py -k "profile_heartbeat or first_heartbeat" -q
```

Expected: FAIL because current presentation does not compare source profile hashes.

- [ ] **Step 3: Add presentation field**

In the camera worker summary contract, add:

```python
runtime_presentation: Literal[
    "running",
    "awaiting_first_heartbeat",
    "awaiting_profile_heartbeat",
    "stale",
    "failed",
] = "awaiting_first_heartbeat"
```

In the service that builds fleet/deployment camera worker summaries, compute:

```python
if latest_report is None:
    runtime_state = WorkerRuntimeState.NOT_REPORTED
    presentation = "awaiting_first_heartbeat"
elif not _runtime_report_is_fresh(latest_report):
    presentation = "stale"
elif current_source_profile_hash and latest_report.source_profile_hash != current_source_profile_hash:
    runtime_state = WorkerRuntimeState.STARTING
    presentation = "awaiting_profile_heartbeat"
else:
    presentation = latest_report.runtime_state.value
```

Do not infer `running` from supervisor node health.

- [ ] **Step 4: Run tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/services/test_deployment_nodes.py -k "runtime" -q
backend/.venv/bin/pytest backend/tests/services/test_camera_worker_config.py -k "source_capability or browser_delivery" -q
```

Expected: PASS.

## Task 6: Captured Frame Envelope And Detector Fast Path

**Files:**
- Create: `backend/src/argus/vision/frames.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write failing no-BGR-before-detect test**

Add fake frame and detector classes to `backend/tests/inference/test_engine.py`:

```python
class _GpuOnlyFrame:
    width = 1280
    height = 720
    memory_kind = "cuda"
    source_profile_hash = "g" * 64

    def __init__(self) -> None:
        self.materialized = False

    def as_bgr_numpy(self) -> np.ndarray:
        self.materialized = True
        return np.zeros((720, 1280, 3), dtype=np.uint8)


class _GpuFrameDetector(_FakeDetector):
    def __init__(self) -> None:
        super().__init__()
        self.used_gpu_frame = False

    def detect_captured_frame(self, frame: object, allowed_classes: list[str] | None = None) -> list[Detection]:
        self.used_gpu_frame = True
        assert getattr(frame, "memory_kind") == "cuda"
        return []
```

Add:

```python
@pytest.mark.asyncio
async def test_engine_uses_detector_captured_frame_fast_path_before_bgr_materialization() -> None:
    camera_id = uuid4()
    frame = _GpuOnlyFrame()
    detector = _GpuFrameDetector()
    engine = InferenceEngine(
        config=_engine_config(camera_id),
        frame_source=_FakeFrameSource([frame]),  # type: ignore[list-item]
        detector=detector,
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type=tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
    )

    await engine.start()
    await engine.run_once()
    await engine.close()

    assert detector.used_gpu_frame is True
    assert frame.materialized is True
```

The final assertion is true because publishing/annotation still need BGR on this no-encoder SKU; the important behavior is that materialization happens after detector fast path.

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "captured_frame_fast_path" -q
```

Expected: FAIL because the engine always passes NumPy frames to `detect()`.

- [ ] **Step 3: Add frame envelope protocols**

Create `backend/src/argus/vision/frames.py`:

```python
from __future__ import annotations

from typing import Literal, Protocol

import numpy as np
from numpy.typing import NDArray

Frame = NDArray[np.uint8]
MemoryKind = Literal["cpu_bgr", "nvmm", "cuda"]


class CapturedFrame(Protocol):
    width: int
    height: int
    memory_kind: MemoryKind
    source_profile_hash: str | None

    def as_bgr_numpy(self) -> Frame: ...


def is_captured_frame(value: object) -> bool:
    return callable(getattr(value, "as_bgr_numpy", None)) and hasattr(value, "memory_kind")
```

- [ ] **Step 4: Implement detector fast path**

In `InferenceEngine.run_once()` where detection starts, use:

```python
        raw_frame = self.frame_source.next_frame()
        captured_frame = raw_frame if is_captured_frame(raw_frame) else None
        frame = (
            captured_frame.as_bgr_numpy()
            if captured_frame is not None and captured_frame.memory_kind == "cpu_bgr"
            else raw_frame
        )
```

Before calling `self.detector.detect(...)`, check:

```python
        detect_captured_frame = getattr(self.detector, "detect_captured_frame", None)
        if captured_frame is not None and callable(detect_captured_frame):
            detections = detect_captured_frame(captured_frame, allowed_classes=detector_classes)
            processed = captured_frame.as_bgr_numpy()
        else:
            processed = self.preprocessor(frame.copy())
            detections = self.detector.detect(processed, allowed_classes=detector_classes)
```

Keep privacy, annotation, tracking, incidents, and publishing on CPU BGR until a separate renderer/publisher path exists.

- [ ] **Step 5: Run tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "captured_frame_fast_path or runtime_report" -q
```

Expected: PASS.

## Task 7: Optional NVMM/CUDA Native Capture Wrapper

**Files:**
- Modify: `backend/src/argus/vision/jetson_nvmm_capture.py`
- Modify: `backend/native/jetson_capture/README.md`
- Test: `backend/tests/vision/test_jetson_nvmm_capture.py`

- [ ] **Step 1: Write failing wrapper tests**

Add to `backend/tests/vision/test_jetson_nvmm_capture.py`:

```python
class _FakeNativeModule:
    def __init__(self) -> None:
        self.opened = []

    def open_rtsp(self, source_uri: str, width: int | None, height: int | None, fps_cap: int):
        self.opened.append((source_uri, width, height, fps_cap))
        return object()


def test_native_capture_wrapper_reports_backend_and_mode(monkeypatch) -> None:
    module = _FakeNativeModule()
    capture = NativeJetsonCapture.create(
        source_uri="rtsp://camera.local/ch2",
        target_width=1280,
        target_height=720,
        fps_cap=20,
        native_module=module,
    )

    assert capture.media_capture_backend() == "jetson_nvmm_native"
    assert capture.media_pipeline_mode() == "jetson_gstreamer_native"
    assert module.opened == [("rtsp://camera.local/ch2", 1280, 720, 20)]
```

Add a frame test:

```python
def test_native_frame_can_delay_bgr_materialization() -> None:
    calls = 0

    def materialize():
        nonlocal calls
        calls += 1
        return np.zeros((720, 1280, 3), dtype=np.uint8)

    frame = NativeJetsonFrame(
        width=1280,
        height=720,
        format="NV12",
        captured_at_monotonic=12.5,
        memory_kind="cuda",
        source_profile_hash="h" * 64,
        _bgr_materializer=materialize,
    )

    assert calls == 0
    observed = frame.as_bgr_numpy()
    assert observed.shape == (720, 1280, 3)
    assert calls == 1
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_jetson_nvmm_capture.py -q
```

Expected: FAIL because wrapper and delayed materializer fields do not exist.

- [ ] **Step 3: Extend native Python wrapper**

In `jetson_nvmm_capture.py`, update `NativeJetsonFrame`:

```python
@dataclass(slots=True)
class NativeJetsonFrame:
    width: int
    height: int
    format: str
    captured_at_monotonic: float
    memory_kind: str = "cuda"
    source_profile_hash: str | None = None
    _bgr: np.ndarray | None = None
    _bgr_materializer: Callable[[], np.ndarray] | None = None

    def as_bgr_numpy(self) -> np.ndarray:
        if self._bgr is not None:
            return self._bgr.copy()
        if self._bgr_materializer is None:
            raise NativeJetsonUnavailable("native frame cannot materialize BGR output")
        return self._bgr_materializer().copy()
```

Add `NativeJetsonCapture`:

```python
class NativeJetsonCapture:
    def __init__(self, handle: object, native_module: object) -> None:
        self._handle = handle
        self._native = native_module
        self._last_stage_timings: dict[str, float] = {}

    @classmethod
    def create(
        cls,
        *,
        source_uri: str,
        target_width: int | None,
        target_height: int | None,
        fps_cap: int,
        native_module: object,
    ) -> NativeJetsonCapture:
        handle = native_module.open_rtsp(source_uri, target_width, target_height, fps_cap)
        return cls(handle, native_module)

    def read(self) -> tuple[bool, NativeJetsonFrame | None]:
        frame = self._native.read(self._handle)
        return (frame is not None), frame

    def release(self) -> None:
        close = getattr(self._native, "close", None)
        if callable(close):
            close(self._handle)

    def last_stage_timings(self) -> dict[str, float]:
        return dict(self._last_stage_timings)

    def media_pipeline_mode(self) -> str:
        return "jetson_gstreamer_native"

    def media_capture_backend(self) -> str:
        return "jetson_nvmm_native"
```

- [ ] **Step 4: Document native extension contract**

Update `backend/native/jetson_capture/README.md` to state:

```markdown
This lane does not implement hardware encode. It only targets capture, resize,
color/preprocess, and TensorRT input preparation. Software preview publishing
may continue to materialize CPU BGR frames.

The native module contract is:

- `open_rtsp(source_uri, width, height, fps_cap) -> handle`
- `read(handle) -> NativeJetsonFrame | None`
- `close(handle) -> None`

The first production implementation must prove that `read()` can return a CUDA
or NVMM-backed frame and that TensorRT inference can run before
`NativeJetsonFrame.as_bgr_numpy()` is called.
```

- [ ] **Step 5: Run tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_jetson_nvmm_capture.py -q
```

Expected: PASS.

## Task 8: Opt-In NVMM Selection And Live Smoke Gate

**Files:**
- Modify: `backend/src/argus/vision/camera.py`
- Modify: `backend/tests/vision/test_camera.py`
- Create: `docs/superpowers/status/2026-06-10-jetson-source-reinit-nvmm-cuda-closure-report.md`

- [ ] **Step 1: Write failing opt-in selection test**

Add to `backend/tests/vision/test_camera.py`:

```python
def test_jetson_capture_backend_env_can_select_nvmm(monkeypatch: pytest.MonkeyPatch) -> None:
    selected: list[str] = []

    def open_nvmm(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        selected.append(source)
        return _FakeCapture(np.zeros((720, 1280, 3), dtype=np.uint8), backend="jetson_nvmm_native")

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "nvmm")
    monkeypatch.setattr(camera_module, "_open_native_jetson_nvmm_capture", open_nvmm)

    capture = camera_module._open_jetson_gstreamer_capture_with_fallback(
        "rtsp://camera.local/ch2",
        media_pipeline_mode=MediaPipelineMode.JETSON_GSTREAMER_NATIVE.value,
    )

    assert selected == ["rtsp://camera.local/ch2"]
    assert capture.media_capture_backend() == "jetson_nvmm_native"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py -k "select_nvmm" -q
```

Expected: FAIL because `nvmm` is not selectable.

- [ ] **Step 3: Implement opt-in selection**

Add `_JETSON_CAPTURE_BACKEND_NVMM = "nvmm"` and only try `_open_native_jetson_nvmm_capture()` when the env/config value is exactly `nvmm`. Do not include it in `auto`.

Fallback rules:

- `nvmm`: fail closed if native capture is unavailable.
- `appsink`: fail closed if appsink is unavailable.
- `rawvideo`: use rawvideo compatibility path.
- `auto`: appsink, rawvideo, software GStreamer, FFmpeg software.

- [ ] **Step 4: Run tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py backend/tests/vision/test_jetson_nvmm_capture.py -q
```

Expected: PASS.

- [ ] **Step 5: Live Jetson smoke**

After code is committed locally and rebuilt/deployed from the committed branch, run:

```bash
ssh ai-user@192.168.1.203 'docker top vezor-supervisor -eo pid,comm'
ssh ai-user@192.168.1.203 'docker stats --no-stream --format "{{.Name}} CPU={{.CPUPerc}} MEM={{.MemUsage}}" vezor-supervisor vezor-edge-mediamtx'
ssh ai-user@192.168.1.203 'timeout 20s tegrastats --interval 1000'
ssh ai-user@192.168.1.203 'curl -fsS http://127.0.0.1:9108/metrics'
```

Collect a 20 second FPS delta from `argus_inference_frames_processed_total`.

PASS requires either:

- FPS at least `19.33` at the same 720p20 profile, or
- `vezor-supervisor` CPU at or below `120%` while FPS remains at least `17.57`.

If neither threshold is met, keep `nvmm` experimental and record FAIL or NOT RUN.

## Task 9: Final Verification And Report

**Files:**
- All changed files
- Create or update: `docs/superpowers/status/YYYY-MM-DD-jetson-source-reinit-nvmm-cuda-closure-report.md`

- [ ] **Step 1: Run targeted backend tests**

Run:

```bash
backend/.venv/bin/pytest \
  backend/tests/services/test_camera_service.py \
  backend/tests/inference/test_engine.py \
  backend/tests/vision/test_camera.py \
  backend/tests/vision/test_jetson_nvmm_capture.py \
  backend/tests/api/test_operations_endpoints.py \
  backend/tests/services/test_deployment_nodes.py \
  backend/tests/supervisor/test_operations_client.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

Run:

```bash
corepack pnpm --dir frontend test CameraWizard.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Run lint and diff checks**

Run:

```bash
backend/.venv/bin/ruff check backend/src/argus backend/tests
git diff --check
```

Expected: PASS.

- [ ] **Step 4: Run secret scan over new docs and evidence**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import re

patterns = [
    re.compile("rtsp://" + r"[^ ]+:[^ ]+@"),
    re.compile("Bear" + "er "),
    re.compile("ey" + "J"),
    re.compile("JW" + "T"),
    re.compile("pass" + "word"),
    re.compile("ai-" + "user1"),
    re.compile("948" + ":759"),
    re.compile("741" + ":190"),
]
paths = [
    Path("docs/superpowers/specs/2026-06-10-jetson-source-reinit-and-nvmm-cuda-design.md"),
    Path("docs/superpowers/plans/2026-06-10-jetson-source-reinit-and-nvmm-cuda-implementation-plan.md"),
]
failures = []
for path in paths:
    text = path.read_text(encoding="utf-8")
    for pattern in patterns:
        if pattern.search(text):
            failures.append(f"{path}: {pattern.pattern}")
if failures:
    raise SystemExit("\n".join(failures))
PY
```

Expected: no matches except intentionally fake examples without real credentials.

- [ ] **Step 5: Write closure report**

The report must distinguish:

```text
PASS
FAIL
BLOCKED
NOT RUN
```

Required evidence:

- source profile hash before and after source change
- fresh per-camera runtime report, not supervisor health inference
- source capability and setup preview frame size after 720p source selection
- calibration stale/current behavior
- FPS, CPU, memory, GR3D samples
- media pipeline mode, capture backend, encoder mode
- explicit statement that hardware encode and DeepStream were NOT RUN

- [ ] **Step 6: Ask before committing**

Ask for explicit approval before staging or committing. Do not push unless separately approved.
