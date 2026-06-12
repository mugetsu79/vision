# Worker Telemetry Tracking Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize edge and central streams, keep vision local to worker processes, make master ingest canonical for telemetry/persistence/live fanout, improve tracking accuracy evidence, and reduce worker CPU hot-path overhead.

**Architecture:** Edge Jetson workers publish canonical processed-frame telemetry with `frame_id` and sequence through NATS primary plus HTTP fallback. Central workers on the master host publish the same canonical telemetry contract through local worker ingest. The master deduplicates by frame, persists processed-cadence observations subject to retention policy, then coalesces accepted frames for live WebSocket fanout. `evt.tracking.*` is post-persistence live fanout only. Stream stability is a Phase 0 gate before telemetry and tracker tuning.

**Tech Stack:** Python/FastAPI, SQLAlchemy/Postgres/Timescale, NATS/JetStream, MediaMTX, Prometheus metrics, pytest, Vitest for affected frontend/runtime status surfaces.

---

## Commit Policy

Do not commit unless the user explicitly approves. If approval is given, use
explicit path-based staging only. Do not use `git add -A` because the workspace
contains unrelated and untracked local files.

## File Map

- Modify `backend/src/argus/streaming/mediamtx.py`: idempotent path registration and RTSP TCP transport.
- Modify `backend/src/argus/supervisor/stream_provisioner.py`: provision only changed stream signatures and keep sanitized logs.
- Modify `backend/src/argus/inference/publisher.py`: canonical frame IDs, edge and central ingest subjects, lightweight/bytes telemetry publishing, queue/drop/cadence state.
- Modify `backend/src/argus/core/events.py`: support bytes payload publish and `evt.worker.tracking.*` stream subjects while preserving BaseModel publish callers.
- Modify `backend/src/argus/inference/engine.py`: background runtime reporting, skip edge no-op persistence, remove central direct history/live bypass, canonical frame sequence, detector/tracker diagnostics.
- Modify `backend/src/argus/vision/ultralytics_engine_detector.py`: TensorRT/Ultralytics substage timings.
- Modify `backend/src/argus/vision/track_lifecycle.py`: lifecycle diagnostics and reassociation tuning after evidence.
- Modify `backend/src/argus/vision/tracker.py`: expose reassociation or tracker profile knobs if needed by tests.
- Modify `backend/src/argus/services/app.py`: canonical worker ingest for edge and central, frame-level dedupe, batched persistence, shared post-persistence live fanout.
- Modify `backend/src/argus/models/tables.py`: add canonical tracking frame table and enrich tracking event rows.
- Add migration `backend/src/argus/migrations/versions/0050_tracking_frame_observations.py`.
- Modify `backend/src/argus/core/metrics.py`: add ingest, serialization, detector, runtime report, and tracking diagnostic metrics.
- Modify contracts and generated frontend API only for health/status fields that are exposed to UI:
  - `backend/src/argus/api/contracts.py`
  - `frontend/src/lib/openapi.json`
  - `frontend/src/lib/api.generated.ts`
- Modify tests:
  - `backend/tests/streaming/test_mediamtx.py`
  - `backend/tests/supervisor/test_stream_provisioner.py`
  - `backend/tests/inference/test_publisher.py`
  - `backend/tests/inference/test_engine.py`
  - `backend/tests/core/test_events.py`
  - `backend/tests/services/test_telemetry_service.py`
  - `backend/tests/vision/test_tracker.py`
  - `backend/tests/vision/test_track_lifecycle.py`
  - `backend/tests/vision/test_ultralytics_engine_detector.py`
  - `backend/tests/services/test_history_service.py`

## Task 0: Phase 0 Stream Stability Gate For Edge And Central

**Files:**
- Modify: `backend/src/argus/streaming/mediamtx.py`
- Modify: `backend/src/argus/supervisor/stream_provisioner.py`
- Test: `backend/tests/streaming/test_mediamtx.py`
- Test: `backend/tests/supervisor/test_stream_provisioner.py`

- [ ] **Step 1: Write MediaMTX idempotency tests**

Add tests proving identical path config is not replaced twice and RTSP paths use
TCP. The same behavior must cover edge passthrough paths and central camera
paths because both can destabilize live capture if MediaMTX reloads a path on
every hardware report cycle:

```python
async def test_register_stream_skips_identical_path_replace() -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []
    client = MediaMTXClient(
        api_base_url="http://mediamtx.example",
        rtsp_base_url="rtsp://mediamtx.example:8554",
    )

    async def fake_request(method: str, path: str, **kwargs: object) -> dict[str, object]:
        calls.append((method, path, kwargs.get("json")))
        return {}

    client._request = fake_request  # type: ignore[method-assign]

    await client.ensure_path(
        "cameras/camera-1/passthrough",
        source="rtsp://***:***@camera.local:8554/ch2",
        source_on_demand=True,
    )
    await client.ensure_path(
        "cameras/camera-1/passthrough",
        source="rtsp://***:***@camera.local:8554/ch2",
        source_on_demand=True,
    )

    replace_calls = [call for call in calls if "/replace/" in call[1]]
    assert len(replace_calls) == 1
    assert replace_calls[0][2]["rtspTransport"] == "tcp"
```

- [ ] **Step 2: Run the red tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/streaming/test_mediamtx.py \
  backend/tests/supervisor/test_stream_provisioner.py -q
```

Expected before implementation: at least one idempotency/TCP assertion fails if
the current patch is absent or incomplete.

- [ ] **Step 3: Implement idempotent config comparison**

In `MediaMTXClient`, cache the last desired path config by path name:

```python
self._path_configs: dict[str, dict[str, Any]] = {}
```

Build desired config in `_ensure_path()`:

```python
path_config: dict[str, Any] = {
    "name": path_name,
    "source": source,
    "sourceOnDemand": source_on_demand,
}
if urlsplit(source).scheme.lower() in {"rtsp", "rtsps"}:
    path_config["rtspTransport"] = "tcp"
if self._path_configs.get(path_name) == path_config:
    LOGGER.debug("MediaMTX stream path already matches desired config", extra={"path_name": path_name})
    return
```

Only call `/replace` when the config differs, then update the cache.

- [ ] **Step 4: Make provisioner logging signature-based**

Cache stream signatures in `SupervisorStreamProvisioner`:

```python
self._stream_signatures: dict[UUID, tuple[object, ...]] = {}
```

Only log `Provisioned MediaMTX stream path` when the signature changes.
Add a test that central and edge camera configs with identical signatures do
not emit repeated provisioning work.

- [ ] **Step 5: Verify Phase 0 tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/streaming/test_mediamtx.py \
  backend/tests/supervisor/test_stream_provisioner.py -q
backend/.venv/bin/ruff check \
  backend/src/argus/streaming/mediamtx.py \
  backend/src/argus/supervisor/stream_provisioner.py \
  backend/tests/streaming/test_mediamtx.py \
  backend/tests/supervisor/test_stream_provisioner.py
```

Expected: tests and Ruff pass for edge and central path provisioning.

## Task 1: Canonical Telemetry Frame Contract

**Files:**
- Modify: `backend/src/argus/inference/publisher.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/inference/test_publisher.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write failing contract tests**

Add a test that a telemetry frame includes stable frame identity and worker
origin:

```python
def test_telemetry_frame_requires_frame_identity(camera_id: UUID) -> None:
    frame = TelemetryFrame(
        camera_id=camera_id,
        frame_id=uuid.uuid4(),
        frame_sequence=42,
        ts=datetime.now(tz=UTC),
        profile=PublishProfile.JETSON_NANO,
        stream_mode=StreamMode.FILTERED_PREVIEW,
        worker_origin=WorkerOrigin.EDGE,
        source_size={"width": 1280, "height": 720},
        counts={"person": 2},
        tracks=[],
    )

    dumped = frame.model_dump(mode="json")
    assert dumped["frame_id"]
    assert dumped["frame_sequence"] == 42
    assert dumped["worker_origin"] == "edge"
```

Add engine tests that two processed frames produce increasing sequences for
`ProcessingMode.EDGE` and `ProcessingMode.CENTRAL`.

Add subject-routing tests:

```python
def test_edge_worker_uses_edge_ingest_subject(camera_id: UUID) -> None:
    publisher = NatsTelemetryPublisher(origin=WorkerOrigin.EDGE, camera_id=camera_id, ...)
    assert publisher.subject == f"evt.edge.tracking.{camera_id}"


def test_central_worker_uses_worker_ingest_subject(camera_id: UUID) -> None:
    publisher = NatsTelemetryPublisher(origin=WorkerOrigin.CENTRAL, camera_id=camera_id, ...)
    assert publisher.subject == f"evt.worker.tracking.{camera_id}"
```

Worker publishers must never publish directly to `evt.tracking.*`; that subject
is reserved for master post-persistence live fanout.

- [ ] **Step 2: Run the red tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/inference/test_publisher.py::test_telemetry_frame_requires_frame_identity \
  backend/tests/inference/test_engine.py -q
```

Expected before implementation: `TelemetryFrame` rejects `frame_id` or lacks
sequence/origin fields, or publishers route central frames to the wrong subject.

- [ ] **Step 3: Add frame identity fields**

Update `TelemetryFrame`:

```python
class TelemetryFrame(BaseModel):
    model_config = ConfigDict(frozen=True)

    camera_id: UUID
    frame_id: UUID
    frame_sequence: int
    worker_origin: WorkerOrigin
    ts: datetime
    profile: PublishProfile
    stream_mode: StreamMode
    stream_profile_id: str = "native"
    source_size: dict[str, int] | None = None
    counts: dict[str, int]
    tracks: list[TelemetryTrack]
```

In `InferenceEngine.__init__`, initialize:

```python
self._frame_sequence = 0
```

When creating telemetry:

```python
self._frame_sequence += 1
telemetry = TelemetryFrame(
    camera_id=self.config.camera_id,
    frame_id=uuid.uuid4(),
    frame_sequence=self._frame_sequence,
    worker_origin=_worker_origin_for_mode(self.config.mode),
    ...
)
```

Add a subject helper:

```python
def telemetry_ingest_subject(origin: WorkerOrigin, camera_id: UUID) -> str:
    if origin is WorkerOrigin.EDGE:
        return f"evt.edge.tracking.{camera_id}"
    return f"evt.worker.tracking.{camera_id}"
```

- [ ] **Step 4: Verify contract tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/inference/test_publisher.py \
  backend/tests/inference/test_engine.py -q
```

Expected: targeted tests pass after fixture updates.

## Task 2: Canonical Worker Ingest, Persistence, And Frame-Level Dedupe

**Files:**
- Modify: `backend/src/argus/models/tables.py`
- Add: `backend/src/argus/migrations/versions/0050_tracking_frame_observations.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_telemetry_service.py`
- Test: `backend/tests/services/test_history_service.py`

- [ ] **Step 1: Write failing ingest tests**

Add tests for frame-level dedupe across edge NATS, HTTP fallback, and central
worker ingest:

```python
async def test_edge_ingest_dedupes_nats_and_http_by_frame_id(
    telemetry_ingest: WorkerTelemetryIngestService,
    telemetry_frame: TelemetryFrame,
    event_client: FakeEventClient,
) -> None:
    first = await telemetry_ingest.ingest_frame(telemetry_frame, source="edge_nats")
    second = await telemetry_ingest.ingest_frame(telemetry_frame, source="http")

    assert first == {"frames_inserted": 1, "tracks_inserted": 2, "broadcasted": 1, "duplicates": 0}
    assert second == {"frames_inserted": 0, "tracks_inserted": 0, "broadcasted": 0, "duplicates": 1}
    assert event_client.published_subjects == [f"evt.tracking.{telemetry_frame.camera_id}"]


async def test_central_worker_ingest_persists_before_live_broadcast(
    telemetry_ingest: WorkerTelemetryIngestService,
    central_telemetry_frame: TelemetryFrame,
    event_client: FakeEventClient,
) -> None:
    result = await telemetry_ingest.ingest_frame(central_telemetry_frame, source="worker_nats")

    assert result == {"frames_inserted": 1, "tracks_inserted": 2, "broadcasted": 1, "duplicates": 0}
    assert event_client.published_subjects == [f"evt.tracking.{central_telemetry_frame.camera_id}"]
    assert event_client.published_after_commit is True
```

Add tests that persisted rows include `stable_track_id`, `source_track_id`,
`track_state`, `last_seen_age_ms`, `frame_id`, `frame_sequence`, and
`worker_origin`.

- [ ] **Step 2: Run the red tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/services/test_telemetry_service.py \
  backend/tests/services/test_history_service.py -q
```

Expected before implementation: missing columns/table and mismatched result
shape failures.

- [ ] **Step 3: Add models**

Add a `TrackingFrame` table:

```python
class TrackingFrame(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tracking_frames"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False)
    frame_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    frame_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    stream_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    stream_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_size: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    telemetry_transport: Mapped[str] = mapped_column(String(32), nullable=False)
    worker_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    track_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

Enrich `TrackingEvent` with nullable compatibility columns:

```python
frame_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
frame_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
stable_track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
source_track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
track_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
last_seen_age_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
telemetry_transport: Mapped[str | None] = mapped_column(String(32), nullable=True)
worker_origin: Mapped[str | None] = mapped_column(String(32), nullable=True)
```

- [ ] **Step 4: Add migration**

Create migration `0050_tracking_frame_observations.py` with:

```python
op.create_table(
    "tracking_frames",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
    sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("frame_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("frame_sequence", sa.Integer(), nullable=False),
    sa.Column("stream_mode", sa.String(length=64), nullable=False),
    sa.Column("stream_profile_id", sa.String(length=128), nullable=False),
    sa.Column("source_size", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column("telemetry_transport", sa.String(length=32), nullable=False),
    sa.Column("worker_origin", sa.String(length=32), nullable=False),
    sa.Column("track_count", sa.Integer(), nullable=False, server_default="0"),
    sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
    sa.PrimaryKeyConstraint("id", "ts"),
)
op.create_index("ix_tracking_frames_camera_frame", "tracking_frames", ["camera_id", "frame_id"], unique=True)
```

Add the nullable `tracking_events` columns and indexes for
`camera_id/frame_id` and `camera_id/stable_track_id/ts`.

- [ ] **Step 5: Implement batched frame ingest**

Update the current edge ingest service into `WorkerTelemetryIngestService`. It
subscribes to both `evt.edge.tracking.*` and `evt.worker.tracking.*`, accepts
HTTP fallback frames, and inserts a frame row first with
`ON CONFLICT DO NOTHING`, inserts track rows only when the frame insert wins,
then publishes live once.

Use source names:

```python
TelemetryIngestSource = Literal["edge_nats", "http", "worker_nats"]
```

Map them to persisted transport values without trusting stale lifecycle state
as runtime truth.

Use result keys:

```python
{"frames_inserted": int, "tracks_inserted": int, "broadcasted": int, "duplicates": int}
```

- [ ] **Step 6: Verify persistence tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/services/test_telemetry_service.py \
  backend/tests/services/test_history_service.py -q
backend/.venv/bin/ruff check \
  backend/src/argus/models/tables.py \
  backend/src/argus/services/app.py \
  backend/src/argus/migrations/versions/0050_tracking_frame_observations.py
```

Expected: tests and Ruff pass.

## Task 3: Shared Coalesced WebSocket Fanout

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/api/v1/telemetry_ws.py`
- Test: `backend/tests/services/test_telemetry_service.py`
- Test: `backend/tests/api/test_prompt5_routes.py` if WebSocket tests live there

- [ ] **Step 1: Write failing fanout tests**

Test that two WebSocket subscriptions do not create two NATS subscriptions:

```python
async def test_telemetry_fanout_reuses_single_nats_subscription(
    services: AppServices,
    tenant_context: TenantContext,
    event_client: FakeEventClient,
) -> None:
    first = await services.telemetry.subscribe(tenant_context)
    second = await services.telemetry.subscribe(tenant_context)

    assert event_client.subscribe_count("evt.tracking.*") == 1

    await first.close()
    await second.close()
```

Test coalescing keeps latest frame:

```python
async def test_telemetry_fanout_coalesces_latest_frame_per_camera(
    telemetry_service: NatsTelemetryService,
    camera_id: UUID,
) -> None:
    await telemetry_service.publish_live_for_test(_frame(camera_id, sequence=1))
    await telemetry_service.publish_live_for_test(_frame(camera_id, sequence=2))

    subscription = await telemetry_service.subscribe(_tenant_for(camera_id))
    frame = await subscription.receive()
    assert frame.frame_sequence == 2
```

Add a test that a central frame received through `evt.worker.tracking.*` becomes
visible to WebSocket clients only after the ingest service accepts and persists
it.

- [ ] **Step 2: Run the red tests**

Run:

```bash
backend/.venv/bin/python -m pytest backend/tests/services/test_telemetry_service.py -q
```

Expected before implementation: each subscriber creates an independent NATS
subscription or coalescing API is missing.

- [ ] **Step 3: Implement shared fanout**

Add a backend-owned fanout service that subscribes once to `evt.tracking.*`,
keeps per-tenant subscriber queues, and drops stale queued frames per subscriber.
The only publisher to `evt.tracking.*` should be canonical ingest after
persistence; edge and central workers publish to their ingest subjects instead.

Keep the public WebSocket behavior unchanged:

```python
payload = await subscription.receive()
await websocket.send_json(payload.model_dump(mode="json"))
```

- [ ] **Step 4: Verify fanout tests**

Run:

```bash
backend/.venv/bin/python -m pytest backend/tests/services/test_telemetry_service.py -q
```

Expected: fanout tests pass and existing telemetry tests remain green.

## Task 4: Worker Hot-Path Optimization For Edge And Central

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/inference/publisher.py`
- Modify: `backend/src/argus/core/events.py`
- Test: `backend/tests/inference/test_engine.py`
- Test: `backend/tests/inference/test_publisher.py`
- Test: `backend/tests/core/test_events.py`

- [ ] **Step 1: Write failing runtime reporter test**

Add a test that a slow runtime reporter does not delay `process_frame()`:

```python
async def test_runtime_reporter_runs_off_frame_loop(engine_factory: Callable[..., InferenceEngine]) -> None:
    reporter = SlowRuntimeReporter(delay_seconds=0.25)
    engine = engine_factory(runtime_reporter=reporter, runtime_report_interval_seconds=0.0)

    started = time.perf_counter()
    await engine.process_frame()
    elapsed = time.perf_counter() - started

    assert elapsed < 0.20
    await reporter.wait_for_report()
```

- [ ] **Step 2: Write failing worker persistence-path tests**

Add a test that edge mode with no local tracking store does not create or use a
`BufferedTrackingStore`:

```python
async def test_edge_mode_skips_noop_tracking_persistence(build_engine_config: EngineConfig) -> None:
    config = build_engine_config.model_copy(update={"mode": ProcessingMode.EDGE})
    engine = await build_runtime_engine(config, settings=settings, events_client=events)

    assert isinstance(engine.tracking_store, NoopEdgeTrackingStore)
```

Add a central-mode test that the worker publishes canonical telemetry to worker
ingest and does not write tracking history or live `evt.tracking.*` directly:

```python
async def test_central_mode_uses_worker_ingest_not_direct_history_or_live(
    build_engine_config: EngineConfig,
) -> None:
    config = build_engine_config.model_copy(update={"mode": ProcessingMode.CENTRAL})
    engine = await build_runtime_engine(config, settings=settings, events_client=events)

    assert engine.telemetry_publisher.subject == f"evt.worker.tracking.{config.camera_id}"
    assert not engine.direct_tracking_history_enabled
    assert not any(subject.startswith("evt.tracking.") for subject in events.published_subjects)
```

- [ ] **Step 3: Write failing bytes-publish test**

Add an event-client test:

```python
async def test_publish_accepts_preencoded_bytes(nats_client: NatsJetStreamClient) -> None:
    await nats_client.publish_bytes("evt.edge.tracking.camera-1", b'{"frame_id":"abc"}')
    await nats_client.publish_bytes("evt.worker.tracking.camera-1", b'{"frame_id":"def"}')
    assert nats_client.raw_client.published[0].payload == b'{"frame_id":"abc"}'
    assert nats_client.raw_client.published[1].payload == b'{"frame_id":"def"}'
```

- [ ] **Step 4: Run red tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/inference/test_engine.py \
  backend/tests/inference/test_publisher.py \
  backend/tests/core/test_events.py -q
```

Expected before implementation: runtime reporter, no-op edge persistence,
central bypass removal, or bytes-publish tests fail.

- [ ] **Step 5: Implement background runtime reporter**

Replace awaited report calls in the frame loop with queueing:

```python
self._runtime_report_queue: asyncio.Queue[SupervisorRuntimeReportCreate | None] = asyncio.Queue(maxsize=1)
self._runtime_report_task: asyncio.Task[None] | None = None
```

On report interval, enqueue latest report and drop the older pending report if
the queue is full. The background task performs the HTTP call.

- [ ] **Step 6: Normalize worker persistence paths**

Use a no-op edge tracking store whose `record()` returns immediately without
copying detections or starting a queue:

```python
class NoopEdgeTrackingStore:
    async def record(self, *args: object, **kwargs: object) -> None:
        return None
```

In `build_runtime_engine()`, use it when `config.mode is ProcessingMode.EDGE`
and no explicit `tracking_store` is provided.

For `ProcessingMode.CENTRAL` and `ProcessingMode.HYBRID`, route tracking
observations through canonical worker telemetry ingest instead of a separate
direct history/live path. Central vision still runs locally in the worker; the
backend only ingests, persists, dedupes, and fans out accepted telemetry.

- [ ] **Step 7: Add bytes publish path**

Add:

```python
async def publish_bytes(self, subject: str, payload: bytes) -> None:
    if not self.settings.nats_manage_streams:
        await self._require_client().publish(subject, payload)
        return
    await self._require_jetstream().publish(subject, payload)
```

Keep `publish(subject, BaseModel)` as compatibility wrapper and make
`evt.worker.tracking.*` part of the managed stream subject list.

- [ ] **Step 8: Verify hot-path tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/inference/test_engine.py \
  backend/tests/inference/test_publisher.py \
  backend/tests/core/test_events.py -q
backend/.venv/bin/ruff check \
  backend/src/argus/inference/engine.py \
  backend/src/argus/inference/publisher.py \
  backend/src/argus/core/events.py
```

Expected: tests and Ruff pass.

## Task 5: Detector, Serialization, And Threadpool Evidence

**Files:**
- Modify: `backend/src/argus/vision/ultralytics_engine_detector.py`
- Modify: `backend/src/argus/core/metrics.py`
- Modify: `backend/src/argus/inference/publisher.py`
- Test: `backend/tests/vision/test_ultralytics_engine_detector.py`
- Test: `backend/tests/inference/test_publisher.py`

- [ ] **Step 1: Write detector timing test**

Add:

```python
def test_ultralytics_engine_detector_exposes_stage_timings(fake_model: FakeModel) -> None:
    detector = UltralyticsEngineDetector(artifact, model_loader=lambda path: fake_model)
    detector.detect(np.zeros((720, 1280, 3), dtype=np.uint8), allowed_classes={"person"})

    timings = detector.last_stage_timings()
    assert set(timings) >= {"predict", "convert", "filter"}
    assert all(value >= 0.0 for value in timings.values())
```

- [ ] **Step 2: Write serialization timing test**

Add:

```python
async def test_buffered_publisher_reports_serialization_bytes_and_origin(
    telemetry_frame: TelemetryFrame,
    fake_nats: FakeNatsPublisher,
) -> None:
    publisher = BufferedTelemetryPublisher(NatsPublisher(fake_nats))
    await publisher.publish(telemetry_frame)
    await publisher.close()

    state = publisher.describe_runtime_state()
    assert state["last_payload_bytes"] > 0
    assert state["worker_origin"] in {"edge", "central"}
```

- [ ] **Step 3: Run red tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/vision/test_ultralytics_engine_detector.py \
  backend/tests/inference/test_publisher.py -q
```

Expected before implementation: missing timing/state fields.

- [ ] **Step 4: Implement detector substage timings**

In `UltralyticsEngineDetector.detect()`:

```python
started_at = perf_counter()
results = self._model.predict(frame, verbose=False)
predicted_at = perf_counter()
detections = _detections_from_ultralytics_results(results, artifact_classes=self.artifact.classes)
converted_at = perf_counter()
filtered = [detection for detection in detections if detection.class_name in allowed]
completed_at = perf_counter()
self._last_stage_timings = {
    "predict": predicted_at - started_at,
    "convert": converted_at - predicted_at,
    "filter": completed_at - converted_at,
}
```

- [ ] **Step 5: Add A/B evidence script**

Create `scripts/worker_perf_probe.py` that reads:

- `/proc/<pid>/task/*/stat`
- worker metrics endpoint
- candidate counters
- process CPU seconds

The script must accept `--origin edge|central`, print sanitized JSON, and never
print process command lines. For central samples, report current Dockerized CPU
behavior only; do not claim M4 GPU acceleration. Native macOS/CoreML remains a
future runtime-family track.

- [ ] **Step 6: Verify evidence tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/vision/test_ultralytics_engine_detector.py \
  backend/tests/inference/test_publisher.py -q
backend/.venv/bin/ruff check \
  backend/src/argus/vision/ultralytics_engine_detector.py \
  backend/src/argus/inference/publisher.py
```

Expected: tests and Ruff pass.

## Task 6: Tracking Diagnostics And Stability Tuning

**Files:**
- Modify: `backend/src/argus/vision/track_lifecycle.py`
- Modify: `backend/src/argus/vision/candidate_quality.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/core/metrics.py`
- Test: `backend/tests/vision/test_track_lifecycle.py`
- Test: `backend/tests/vision/test_candidate_quality.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write diagnostics tests**

Add lifecycle diagnostics tests:

```python
def test_lifecycle_reports_source_reassociation_reason() -> None:
    manager = TrackLifecycleManager()
    first = Detection(class_name="person", confidence=0.9, bbox=(100, 100, 200, 300), track_id=7)
    second = Detection(class_name="person", confidence=0.88, bbox=(104, 102, 204, 302), track_id=11)

    manager.update([first], ts=_ts(0), frame_shape=(720, 1280, 3))
    manager.update([second], ts=_ts(1), frame_shape=(720, 1280, 3))

    diagnostics = manager.last_diagnostics()
    assert diagnostics[-1].reason == "spatial_reassociation"
    assert diagnostics[-1].source_track_id == 11
    assert diagnostics[-1].stable_track_id == 1
```

Add an engine-facing diagnostics test for both worker origins so central and
edge telemetry persist the same identity explanation fields:

```python
@pytest.mark.parametrize("mode", [ProcessingMode.EDGE, ProcessingMode.CENTRAL])
async def test_worker_telemetry_includes_tracking_diagnostics(mode: ProcessingMode) -> None:
    frame = await process_synthetic_two_person_frame(mode=mode)

    assert frame.worker_origin in {WorkerOrigin.EDGE, WorkerOrigin.CENTRAL}
    assert frame.tracks[0].stable_track_id is not None
    assert frame.tracks[0].source_track_id is not None
    assert frame.tracks[0].lifecycle_reason in {
        "source_id_match",
        "spatial_reassociation",
        "new_track",
    }
```

- [ ] **Step 2: Write tuning tests for max-two-person scenes**

Add a sequence test with two overlapping people and a brief raw ID switch. The
assertion is that lifecycle stable IDs remain two IDs, not three. Run the same
fixture through edge and central worker modes so central does not retain an old
tracking behavior after edge is tuned.

- [ ] **Step 3: Run red tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/vision/test_track_lifecycle.py \
  backend/tests/vision/test_candidate_quality.py \
  backend/tests/inference/test_engine.py -q
```

Expected before implementation: diagnostics API missing or ID-stability test
fails.

- [ ] **Step 4: Implement lifecycle diagnostics**

Add a small dataclass:

```python
@dataclass(frozen=True, slots=True)
class TrackLifecycleDecision:
    stable_track_id: int
    source_track_id: int | None
    class_name: str
    reason: str
```

Record reasons:

- `source_id_match`
- `spatial_reassociation`
- `new_track`
- `coasting`
- `forgotten`
- `duplicate_suppressed`
- `duplicate_replaced`

- [ ] **Step 5: Tune reassociation with tests**

Introduce config fields:

```python
reassociate_iou_threshold: float = 0.20
reassociate_center_distance_ratio: float = 0.65
```

Apply only where tests prove a same-class raw ID switch should remain the same
stable ID. Keep any profile knobs shared by worker mode unless live evidence
shows a camera/runtime-specific reason to split them.

- [ ] **Step 6: Verify tracking tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/vision/test_track_lifecycle.py \
  backend/tests/vision/test_candidate_quality.py \
  backend/tests/inference/test_engine.py -q
backend/.venv/bin/ruff check \
  backend/src/argus/vision/track_lifecycle.py \
  backend/src/argus/vision/candidate_quality.py \
  backend/src/argus/inference/engine.py
```

Expected: tests and Ruff pass.

## Task 7: Runtime Health And API Surfaces

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/models/tables.py`
- Modify: `backend/src/argus/services/supervisor_operations.py`
- Modify: `frontend/src/lib/openapi.json`
- Modify: `frontend/src/lib/api.generated.ts`
- Test: `backend/tests/services/test_supervisor_operations.py`
- Test: `backend/tests/api/test_openapi_export.py`
- Test: affected frontend tests if generated contracts alter UI assertions

- [ ] **Step 1: Write failing runtime health test**

Add:

```python
async def test_runtime_report_includes_telemetry_and_ingest_health(operations_service: SupervisorOperationsService) -> None:
    report = await operations_service.record_runtime_report(
        SupervisorRuntimeReportCreate(
            camera_id=camera_id,
            runtime_state=WorkerRuntimeState.RUNNING,
            telemetry_transport="nats",
            telemetry_path="evt.edge.tracking",
            telemetry_cadence_seconds=0.0,
            telemetry_publish_drops=0,
            telemetry_pending_frames=0,
            telemetry_fallback_active=False,
            telemetry_ingest_lag_ms=12.0,
        )
    )

    assert report.telemetry_transport == "nats"
    assert report.telemetry_ingest_lag_ms == 12.0
```

Add a central variant:

```python
async def test_central_runtime_report_uses_worker_ingest_path(
    operations_service: SupervisorOperationsService,
) -> None:
    report = await operations_service.record_runtime_report(
        SupervisorRuntimeReportCreate(
            camera_id=camera_id,
            runtime_state=WorkerRuntimeState.RUNNING,
            processing_mode=ProcessingMode.CENTRAL,
            telemetry_transport="worker_nats",
            telemetry_path="evt.worker.tracking",
            telemetry_cadence_seconds=0.0,
            telemetry_publish_drops=0,
            telemetry_pending_frames=0,
            telemetry_fallback_active=False,
            telemetry_ingest_lag_ms=8.0,
        )
    )

    assert report.telemetry_transport == "worker_nats"
    assert report.telemetry_path == "evt.worker.tracking"
```

- [ ] **Step 2: Run red tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/services/test_supervisor_operations.py \
  backend/tests/api/test_openapi_export.py -q
```

Expected before implementation: missing `telemetry_ingest_lag_ms` or generated
contract mismatch.

- [ ] **Step 3: Add health fields conservatively**

Expose only fields that the live system can measure:

- active transport
- subject/path
- worker origin and processing mode
- cadence
- fallback active
- drops
- pending frames
- last error
- ingest lag
- duplicate frame count

- [ ] **Step 4: Regenerate OpenAPI and frontend API**

Run:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python \
  -m argus.scripts.export_openapi_schema \
  frontend/src/lib/openapi.json
corepack pnpm --dir frontend generate:api
```

- [ ] **Step 5: Verify health/API tests**

Run:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/services/test_supervisor_operations.py \
  backend/tests/api/test_openapi_export.py -q
corepack pnpm --dir frontend exec vitest run \
  src/components/operations/SupervisorLifecycleControls.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: backend and affected frontend tests pass.

## Task 8: Live A/B Smoke And Closure Evidence

**Files:**
- Add: `docs/superpowers/status/2026-06-12-worker-telemetry-tracking-optimization-closure-report.md`

- [ ] **Step 1: Rebuild and redeploy from branch**

Rebuild and redeploy master and Jetson from the final branch state. This must
delete and recreate the stack on both the master and the Jetson for whole-product
smoke evidence. Do not paste raw secrets or process args.

- [ ] **Step 2: Run Phase 0 stream smoke**

Collect a 10-minute sanitized sample for both the central RTSP camera and the
edge RTSP camera:

- `Provisioned MediaMTX stream path` count
- capture wait spike count
- worker FPS per camera
- `publish_stream` p95/p99
- MediaMTX CPU

Expected PASS:

- repeated path provisioning count is zero after startup for both cameras
- no MediaMTX path replace loop on edge or central paths
- capture wait spikes are materially lower than before Phase 0 for both cameras

- [ ] **Step 3: Run telemetry smoke**

Collect:

- Jetson worker processed FPS
- central worker processed FPS
- edge NATS leaf CPU
- master NATS CPU and message rate
- master ingest frames inserted/duplicates/broadcasts by origin
- Postgres CPU
- WebSocket live cadence

Expected PASS:

- edge frame persists before broadcast
- central worker frame persists before broadcast
- NATS + HTTP duplicate frame inserts once
- central worker retry duplicate frame inserts once
- live WebSocket cadence can be lower than persistence cadence by design

- [ ] **Step 4: Run CPU A/B smoke**

Run one controlled 60-second sample for each setting group:

- current thread settings
- constrained `OMP_NUM_THREADS`
- constrained `OPENBLAS_NUM_THREADS`
- constrained torch thread count
- pre-encoded telemetry payload path

Expected output is a table with CPU, FPS, total frame ms, detect ms, track ms,
publish telemetry ms, and drops for edge and central workers. Central rows must
state that the current runtime is Dockerized CPU; native macOS/CoreML remains
future work.

- [ ] **Step 5: Run tracking churn smoke**

For the edge and central scenes with at most two people, collect five minutes:

```sql
select
  camera_id,
  class_name,
  count(*) as events,
  count(distinct stable_track_id) as stable_ids,
  count(distinct source_track_id) as source_ids,
  min(ts),
  max(ts)
from tracking_events
where camera_id in ('<edge-camera-id>', '<central-camera-id>')
  and ts > now() - interval '5 minutes'
group by camera_id, class_name;
```

Expected PASS:

- no sustained seconds with more than two active person stable IDs unless the
  diagnostics identify a real third person detection
- distinct stable ID churn decreases compared with the baseline evidence for
  edge and central

- [ ] **Step 6: Write closure report**

Write:

```markdown
# Worker Telemetry Tracking Optimization Closure Report

Date: 2026-06-12
Branch: codex/sceneops-pack-registry

## Summary

## Verification

## Live Smoke Evidence

## PASS / FAIL / BLOCKED / NOT RUN

## Residual Risks
```

Do not include raw RTSP URLs, sudo passwords, bearer tokens, node credentials,
registry credentials, or process args containing secrets.

## Full Verification Suite

Run before declaring completion:

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/streaming/test_mediamtx.py \
  backend/tests/supervisor/test_stream_provisioner.py \
  backend/tests/inference/test_publisher.py \
  backend/tests/inference/test_engine.py \
  backend/tests/core/test_events.py \
  backend/tests/services/test_telemetry_service.py \
  backend/tests/services/test_history_service.py \
  backend/tests/vision/test_tracker.py \
  backend/tests/vision/test_track_lifecycle.py \
  backend/tests/vision/test_candidate_quality.py \
  backend/tests/vision/test_ultralytics_engine_detector.py \
  backend/tests/services/test_supervisor_operations.py \
  backend/tests/api/test_openapi_export.py -q

backend/.venv/bin/ruff check \
  backend/src/argus/streaming/mediamtx.py \
  backend/src/argus/supervisor/stream_provisioner.py \
  backend/src/argus/inference/publisher.py \
  backend/src/argus/core/events.py \
  backend/src/argus/inference/engine.py \
  backend/src/argus/vision/ultralytics_engine_detector.py \
  backend/src/argus/vision/track_lifecycle.py \
  backend/src/argus/vision/candidate_quality.py \
  backend/src/argus/services/app.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/core/metrics.py

corepack pnpm --dir frontend exec vitest run \
  src/components/operations/SupervisorLifecycleControls.test.tsx \
  src/pages/Settings.test.tsx

git diff --check
```

Expected: all targeted tests pass, Ruff passes, frontend targeted tests pass,
and whitespace check passes.
