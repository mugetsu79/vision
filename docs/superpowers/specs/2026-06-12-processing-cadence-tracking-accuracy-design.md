# Processing Cadence And Tracking Accuracy Design

Date: 2026-06-12
Branch: `codex/sceneops-pack-registry`

## Goal

Increase central and edge tracking accuracy without regressing the canonical
telemetry architecture. The immediate root cause to address is that central
processing FPS is currently coupled to the selected browser delivery profile.
The broader goal is to make tracking quality measurable, tunable, and
repeatable before introducing heavier runtime families such as ReID or
DeepStream.

## Current Evidence

The current central worker is running at about 5 FPS because its selected
browser delivery profile is `360p5`. The worker config path resolves browser
delivery into `WorkerStreamSettings.fps`, then the frame source uses
`min(camera.fps_cap, stream.fps)` as the capture throttle. Live stage timings
show the throttle clearly:

- central total: about 190 ms per processed frame
- central `capture_throttle`: about 157-163 ms
- central `detect`: about 27-32 ms
- central `track`: below 1 ms

This means the central worker is not low-FPS because NATS, persistence, or
tracking is expensive. It is paced by live preview profile selection.

The edge worker is not affected by the central `360p5` profile, but it still
needs the same tracking-quality instrumentation and replay harness because edge
tracking has shown ID churn in simple scenes.

## Architecture Decision

Split worker processing cadence from browser delivery cadence.

```text
camera processing cadence
  -> capture throttle
  -> detection
  -> tracking
  -> canonical telemetry persistence cadence

browser delivery profile
  -> processed preview stream size/fps
  -> WebRTC/HLS/operator bandwidth
  -> never lowers the worker's processing cadence
```

The camera's `fps_cap` remains the processing cap in Phase 0. Browser delivery
profiles continue to decide the preview stream profile. If a camera uses a
`360p5` preview, the UI stream may remain 5 FPS, but the worker should still
process at the camera processing cap unless an explicit operator-facing
processing setting says otherwise.

The master backend remains the canonical telemetry authority:

- workers perform capture, detection, tracking, lifecycle association, and
  annotation locally
- master ingest deduplicates canonical frame observations by `camera_id +
  frame_id`
- master persists accepted observations before post-persistence live fanout
- HTTP edge telemetry remains fallback
- `evt.tracking.*` remains post-persistence live fanout only

## Phase 0: Decouple Processing FPS From Preview FPS

Implement the smallest safe cadence fix:

- keep `Camera.fps_cap` as the processing FPS cap
- keep `WorkerStreamSettings.fps` as preview/output stream FPS
- stop using `min(camera.fps_cap, stream.fps)` for frame-source capture throttle
- use `camera.fps_cap` for `CameraSourceConfig.fps_cap`
- use `camera.fps_cap` for tracker `frame_rate`
- preserve `stream.fps` when registering MediaMTX output paths

Expected result:

- central worker no longer drops to 5 processed FPS because default preview is
  `360p5`
- central should target 10-15 FPS initially in live validation if CPU allows
- edge remains around its current 15-16 processed FPS unless camera cap changes
- live browser bandwidth remains governed by delivery profile

## Phase 1: Tracking Diagnostics

Make tracking quality observable in every worker runtime:

- per-frame accepted raw detections by class
- per-frame tracker outputs by class
- lifecycle decisions by reason:
  - `source_id_match`
  - `spatial_reassociation`
  - `new_track`
  - `coasting`
  - `forgotten`
  - `duplicate_suppressed`
  - `duplicate_replaced`
- stable track births
- stable track losses
- source-track-to-stable-track remaps
- estimated ID switches
- coasting age and recovered age
- association confidence inputs: IoU and center-distance ratio

Diagnostics must be emitted as metrics and structured runtime fields without
logging raw frame data or source credentials. Persisted canonical observations
already include `stable_track_id`, `source_track_id`, `track_state`, and
`last_seen_age_ms`; Phase 1 adds enough counters and optional diagnostic rows
to explain why those IDs changed.

## Phase 2: Replay Benchmark Harness

Add an offline replay tool that can evaluate tracker changes repeatably:

- input: sanitized short clips or frame directories captured from central and
  edge scenes
- output: JSON and markdown summaries
- metrics:
  - processed FPS
  - CPU time per stage
  - detection count by class
  - stable track count by class
  - ID switches
  - track fragmentation
  - average track lifetime
  - lost/recovered counts
  - duplicate suppression count
- comparison mode for baseline versus candidate config

The replay harness should not require a live NATS or MediaMTX path. It should
exercise detector, tracker, candidate quality gate, lifecycle manager, and
telemetry frame construction.

## Phase 3: Tracker And Detection Tuning

Tune with benchmark evidence, not intuition:

- separate display confidence from tracker association confidence
- allow lower-confidence person detections into tracker association when the
  box is spatially plausible
- make lifecycle memory time-based so behavior is stable across 5, 10, 15, and
  20 FPS
- tune central person scene defaults separately from edge mixed vehicle/person
  scene defaults
- prefer improving current BoT-SORT/ByteTrack plus lifecycle logic before
  adding appearance ReID

Candidate starting point:

- central person scene:
  - processing cap: 12-15 FPS
  - lifecycle coast TTL: 2.5-4.0 seconds
  - tentative hits: 2
  - lower tracker candidate confidence for person than display confidence
- edge mixed scene:
  - processing cap: 15-18 FPS
  - class-specific thresholds for vehicles versus person
  - keep current TensorRT runtime path

## Phase 4: Live A/B Smoke

Run controlled live tests after replay tuning:

- central before/after window: 5 minutes each
- edge before/after window: 5 minutes each
- record:
  - processed FPS
  - stage averages and p95
  - CPU and RSS
  - MediaMTX replace count
  - capture wait spike count
  - persisted frames
  - broadcasted frames
  - ID switches and fragmentation
  - stable track continuity for the simple two-person central scene

Success is not just higher FPS. Success means better or equal tracking
continuity at an acceptable CPU cost, with no fallback, no duplicate frame
growth, no stream churn, and no telemetry backlog.

## Non-Goals

- Do not implement DeepStream in this track.
- Do not claim Dockerized central GPU or M4 acceleration.
- Do not move Jetson inference or tracking to the master backend.
- Do not reduce persistence fidelity to make live UI easier.
- Do not commit raw RTSP credentials, sudo passwords, bearer tokens, node
  credentials, registry credentials, or process args containing secrets.

## Acceptance Criteria

- Central processing FPS is no longer capped by `browser_delivery.default_profile`.
- Live browser delivery profile can remain low-FPS while canonical telemetry
  persists at processing cadence.
- Runtime health reports expose enough tracking diagnostics to explain ID churn.
- Replay benchmark can compare baseline and candidate tracker configs.
- Phase 4 smoke evidence shows central and edge telemetry still persist through
  canonical ingest and broadcast post-persistence.
- Any tracking accuracy improvement is backed by replay and live A/B evidence.
