# Worker Telemetry Tracking Optimization Design

Date: 2026-06-12
Branch: `codex/sceneops-pack-registry`

## Goal

Make edge and central cameras best-in-class for local vision, tracking
stability, canonical telemetry persistence, and live operator delivery.

The product boundary is explicit:

```text
Edge Jetson worker: capture, decode, detection, tracking, lifecycle IDs, annotation, preview publish, telemetry publish
Central worker on master host: capture, decode, detection, tracking, lifecycle IDs, annotation, preview publish, telemetry publish
Master backend: canonical telemetry ingest, dedupe, batching, persistence, health, history, post-persistence live WebSocket fanout
```

The master must not run inference, detection, NMS, ReID, tracker update, or
lifecycle association for Jetson-assigned cameras. Central camera vision also
stays in a supervised central worker process, not inside the backend
ingest/persistence/fanout services.

## Current Evidence

The NATS architecture is deployed from local uncommitted branch changes. It
routes edge telemetry through:

```text
Jetson worker -> edge NATS leaf -> master NATS -> master canonical ingest -> DB -> evt.tracking -> WebSocket
```

Live evidence shows:

- Jetson worker CPU is real and high, about 4.5 to 4.7 CPU cores in samples.
- Edge NATS leaf, master NATS, MediaMTX, and Postgres are not the direct CPU
  burners.
- The TensorRT/Ultralytics detector path exposes only one broad `detect` stage,
  so CPU-heavy preprocessing, inference, postprocessing, and filtering are not
  yet separable in metrics.
- Runtime reports are awaited inside the frame loop and can appear as
  `publish_telemetry` spikes.
- MediaMTX path churn was a live instability source and must remain a Phase 0
  gate even if the current local patch already appears to reduce repeated path
  replacement.
- Tracking has shown real person ID churn: a max-two-person scene produced many
  distinct persisted person track IDs across five-minute windows.
- Central cameras are also production cameras and must not remain on a separate
  direct persistence/live path. Central workers need the same canonical frame
  contract, persistence-before-live behavior, CPU evidence, and tracker
  diagnostics as edge workers.

## Architecture Decision

Use a canonical worker telemetry pipeline with separated history and live
delivery semantics:

```text
Edge camera:
Jetson processed frame
  -> canonical telemetry frame_id + sequence
  -> evt.edge.tracking.<camera_id> through local NATS leaf primary, HTTP fallback
  -> master worker telemetry ingest
  -> frame-level dedupe
  -> processed-cadence persistence
  -> evt.tracking.<camera_id> post-persistence live fanout
  -> WebSocket

Central camera:
Central worker processed frame on master host
  -> canonical telemetry frame_id + sequence
  -> evt.worker.tracking.<camera_id> local worker ingest
  -> master worker telemetry ingest
  -> frame-level dedupe
  -> processed-cadence persistence
  -> evt.tracking.<camera_id> post-persistence live fanout
  -> WebSocket
```

The master becomes the canonical authority for accepted telemetry, persisted
history, dedupe, ordering, and live fanout. `evt.tracking.*` is reserved for
post-persistence live fanout; worker publishers must not publish directly to
that subject. The Jetson remains the only vision runtime for Jetson cameras.
The central worker remains the local vision runtime for central cameras.

## Phase 0: Stream Stability Gate

Before optimizing telemetry cadence or tracker tuning, stabilize the stream
plumbing so metadata work is not blamed for video transport churn.

Requirements:

- MediaMTX dynamic path registration is idempotent for edge passthrough paths
  and central camera paths.
- Identical desired path config does not call `/v3/config/paths/replace`.
- RTSP source pulls use TCP transport where MediaMTX supports it.
- Path logs remain sanitized and never include raw RTSP credentials or tokens.
- Live edge and central smoke windows show no repeated path replacement and
  materially reduced capture wait spikes.

Passing Phase 0 does not require zero capture jitter forever. It requires
removing path replacement as a recurring source of reconnects and proving it in
a timed live sample.

## Persistence Semantics

Persist canonical frame and track observations from all workers at processed
cadence, subject to product retention policy.

This means:

- The system should retain full processed-cadence observations for the active
  operational/history window.
- The design does not promise infinite high-cardinality retention forever.
- Later retention work may compact older observations into rollups, summaries,
  or evidence-linked windows without changing the live ingest boundary.

Additive persistence model:

- Keep `tracking_events` as the compatibility table for existing history APIs.
- Add canonical frame metadata so a telemetry frame is deduplicated as a frame,
  not only as individual rows.
- Enrich track observation rows with both identity surfaces:
  - `stable_track_id`: lifecycle-stable ID shown to operators
  - `source_track_id`: raw tracker ID from BoT-SORT/ByteTrack
  - `track_state`: `active` or `coasting`
  - `last_seen_age_ms`
  - `frame_id`
  - `frame_sequence`
  - `telemetry_transport`
  - `worker_origin`: `edge` or `central`

The canonical dedupe key is `camera_id + frame_id`. If HTTP fallback and NATS
deliver the same frame, master persistence and live broadcast happen once.
Central local worker retries use the same dedupe key, so a repeated central
worker frame also persists and broadcasts once.

## Live Delivery Semantics

History fidelity and live UI cadence are separate.

- Persistence accepts canonical processed-cadence observations.
- WebSocket fanout may coalesce by camera and send the latest accepted frame at a
  configured live cadence.
- Broadcast still happens only after master ingest accepts the frame.
- Coalescing never changes persisted history.
- WebSocket delivery uses a shared fanout inside the backend instead of one NATS
  subscription per WebSocket client.
- Edge and central frames use the same live fanout contract after persistence.

## Worker Hot Path

All vision worker frame loops must avoid avoidable synchronous work:

- Runtime health/reporting runs in a background task.
- Edge mode does not enqueue to a no-op local tracking store.
- Central mode does not write tracking history directly or publish live frames
  before canonical ingest accepts them.
- Central mode publishes canonical telemetry to local worker ingest using the
  same frame identity and track observation contract as edge.
- Telemetry publisher accepts already-prepared lightweight payloads or
  serializes outside the critical frame path.
- Pydantic validation remains at trust boundaries, primarily master ingest and
  API contracts.
- NATS publisher supports bytes payloads so frame-loop code does not require
  `BaseModel.model_dump_json()` every frame.

## Metrics And A/B Evidence

Add evidence before tuning:

- TensorRT/Ultralytics detector substages:
  - predict total
  - result conversion
  - class filtering
  - postprocess/NMS when visible from the API
- Runtime report latency and queue backlog.
- Telemetry serialization time and payload bytes.
- NATS publish queue pending, drops, fallback state, and active path.
- Worker origin and processing mode for every telemetry path: edge, central, or
  hybrid where applicable.
- Master ingest queue, batch size, inserted frames, duplicate frames, inserted
  track rows, and broadcast frames.
- Tracking diagnostics:
  - accepted/rejected candidate reason counts
  - raw source ID to stable ID mapping
  - lifecycle match reason
  - duplicate suppression action
  - active/coasting/lost transitions

Run measured A/B checks for:

- `OMP_NUM_THREADS`
- `OPENBLAS_NUM_THREADS`
- `torch.set_num_threads`
- pre-encoded telemetry payloads
- `orjson` versus Pydantic JSON serialization
- bytes-based NATS publish versus `BaseModel.model_dump_json()` in the frame
  loop

Run the evidence collection for edge and central workers. Central CPU evidence
must stay honest about the current Dockerized runtime: do not claim M4 GPU
acceleration. Native macOS/CoreML acceleration remains future work.

## Tracking Accuracy

Tracking improvement must be evidence-led for both edge and central cameras.

The first implementation should add diagnostics and persistence shape before
changing tracker behavior. Then tune against real churn evidence.

Likely tuning axes for all worker modes:

- Align tracker frame rate to observed processed FPS.
- Extend lifecycle memory/coasting for simple person scenes.
- Loosen lifecycle reassociation for same-class nearby boxes when raw tracker
  IDs switch.
- Improve duplicate-fragment handling for overlapping people so a real second
  person is not collapsed, but a fragment does not become a long-lived third ID.
- Keep ReID as an optional later capability after CPU budget and diagnostics
  justify it.
- Keep DeepStream as a later runtime-family track, not part of this change.

## Security And Logging

No logs, docs, test output, or smoke evidence may expose:

- raw RTSP credentials
- sudo passwords
- bearer tokens
- node credentials
- registry credentials
- process arguments that contain secrets

Backend access logs must not print WebSocket query strings containing bearer
tokens.

RTSP URLs must be redacted as:

```text
rtsp://***:***@<host>:8554/<path>
```

## Acceptance Criteria

Phase 0:

- Identical MediaMTX path registrations skip `/replace`.
- RTSP MediaMTX paths request TCP pull transport.
- Timed live edge and central windows show zero repeated path replacement after
  startup.

Telemetry:

- Edge NATS and HTTP fallback frames dedupe by `frame_id`.
- Central local worker frames dedupe by `frame_id`.
- Direct edge NATS frames and central worker frames persist before live
  broadcast.
- Master does not run Jetson vision logic.
- Central camera vision runs in a central worker process, not in backend
  ingest/fanout services.
- `evt.tracking.*` is post-persistence live fanout only.
- WebSocket fanout can coalesce live delivery without dropping persistence.
- Active transport/path/cadence/drops/fallback/runtime health are visible.

Optimization:

- Runtime reports no longer block any worker frame loop.
- Edge no-op tracking persistence path is removed.
- Central direct history/live bypass is removed.
- Detector, serialization, and threadpool evidence identifies the main CPU
  sources for edge and central.
- Live A/B smoke quantifies CPU and FPS before and after optimization for both
  worker modes.

Tracking:

- Persisted data can explain stable ID, raw source ID, track state, and churn.
- For max-two-person scenes, no sustained windows show more than two active
  person tracks unless diagnostics identify a real third detection.
- Distinct person ID churn decreases across five-minute live windows for edge
  and central cameras.
