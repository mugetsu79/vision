# Edge NATS Telemetry And Lifecycle Stop Design

Date: 2026-06-12
Branch: `codex/sceneops-pack-registry`

## Context

The current edge telemetry path is:

```text
Jetson worker -> HTTP /api/v1/edge/telemetry -> master DB insert -> evt.tracking.<camera_id> -> WebSocket
```

That path preserves tracking history, but it caps live edge cadence because the
edge worker uses a latest-only HTTP publisher. The target path is:

```text
Jetson worker -> local NATS leaf -> master NATS -> master consumer -> DB + WebSocket
```

The change must not bypass history. A direct edge NATS frame must become both a
persisted tracking event set and one live WebSocket frame. HTTP remains a
fallback path. If HTTP fallback and NATS both deliver the same frame, the master
must deduplicate persistence and live broadcast.

A separate lifecycle bug also needs to close in this change: a central stop
request can complete while a matching local `argus.inference.engine` child is
still alive because `LocalWorkerProcessAdapter.stop()` trusts only its
in-memory process map.

## Decision

Use a separate edge-ingress NATS subject and keep the existing live subject as
the post-persistence broadcast subject:

```text
edge worker publishes:       evt.edge.tracking.<camera_id>
master consumer subscribes:  evt.edge.tracking.*
master live broadcast:       evt.tracking.<camera_id>
WebSocket subscribes:        evt.tracking.*
```

This avoids loops and avoids double-persisting central workers. Central workers
continue to persist locally through `TrackingEventStore` and publish live frames
to `evt.tracking.<camera_id>`. Edge workers publish primarily to
`evt.edge.tracking.<camera_id>` and fall back to HTTP ingest only when NATS
publish fails or is disabled.

The master consumer and HTTP ingest share one persistence/broadcast service.
That service computes deterministic tracking row ids from
`camera_id:timestamp:track_id`, inserts with `ON CONFLICT DO NOTHING`, and only
broadcasts a frame once. It uses database insert results for frames with tracks
and a small in-memory frame-key cache for no-track frames.

The master consumer is durable on `ARGUS_TRACKING` so a master restart does not
turn streamed edge frames into best-effort-only live telemetry after the
consumer has been created.

## Requirements

- Edge primary telemetry uses NATS through the local leaf when NATS is enabled.
- HTTP edge telemetry remains available and is used as fallback.
- Direct edge NATS frames are persisted before live broadcast.
- WebSocket delivery remains on the existing `evt.tracking.*` live subject.
- Duplicate NATS and HTTP deliveries for the same frame do not create duplicate
  history rows or duplicate live frames.
- Runtime/reporting surfaces expose active telemetry path, fallback state,
  publish cadence, dropped live frames, and consumer health.
- Edge leaf permissions must scope edge publishing to
  `evt.edge.tracking.*` and required edge support subjects, not broad master
  subjects.
- DeepStream remains a later runtime family and is not implemented here.
- Central Apple Silicon acceleration remains a future native macOS/CoreML lane.
  This work does not claim Dockerized central GPU acceleration.
- Stop/reconcile must not mark a lifecycle request completed while a matching
  local worker process still exists.
- Worker runtime truth in UI/API remains based on fresh per-camera heartbeats,
  not supervisor node health or stale lifecycle state.

## Components

### Edge Worker Publisher

`build_runtime_engine()` should select:

- edge mode: `ResilientPublisher(NatsPublisher(evt.edge.tracking), HttpPublisher(...))`
- non-edge mode with HTTP fallback configured: current NATS primary plus HTTP
  fallback behavior
- non-edge mode without fallback: current `evt.tracking` NATS publisher

The edge live publisher remains buffered and latest-biased for live delivery.

### Master Telemetry Ingest Service

Add a service owned by `AppServices`:

- subscribes to `evt.edge.tracking.*` on startup
- uses a durable JetStream consumer on `ARGUS_TRACKING`
- validates each message as `TelemetryFrame`
- persists deterministic tracking rows with conflict handling
- publishes exactly one live frame to `evt.tracking.<camera_id>` when the frame
  is new
- reports active transport, path, cadence, fallback state, dropped/pending
  frames, and last error without logging raw credentials

HTTP ingest delegates to the same service so fallback and NATS share dedup and
broadcast semantics.

### NATS Streams And Permissions

Add `evt.edge.tracking.*` to the master stream definitions. Update master and
leaf NATS configs/templates with an edge user/permissions shape that allows edge
publish to `evt.edge.tracking.*` and subscribe only to scoped command/support
subjects needed by existing edge behavior.

### Lifecycle Stop Verification

`LocalWorkerProcessAdapter.stop()` should:

- terminate the tracked process when present
- inspect the local process table for a matching worker process when the
  in-memory map is missing or stale
- terminate matching external worker processes without logging raw command
  arguments
- rescan after termination and return an error if a matching process remains

`SupervisorReconciler` already marks lifecycle completion as failed when a
process adapter returns `last_error`; the adapter must therefore return a
truthful error instead of `stopped` when verification fails.

## Testing

Backend tests cover:

- edge runtime selects NATS primary on `evt.edge.tracking` with HTTP fallback
- NATS consumer persists edge frames and broadcasts post-persistence
- NATS plus HTTP duplicate frame inserts once and broadcasts once
- WebSocket subscribers consume only post-persistence `evt.tracking.*`
- stream definitions include `evt.edge.tracking.*`
- edge NATS configs include scoped permissions
- `LocalWorkerProcessAdapter.stop()` terminates matching stale-map processes
- stop returns an error when a matching worker remains after termination

Live smoke covers:

- master and Jetson rebuilt/redeployed from this branch
- Jetson worker FPS
- master NATS received edge FPS
- WebSocket/browser live cadence
- `tracking_events` insert cadence/history correctness
- HTTP fallback by temporarily breaking the NATS primary path
- central stop request does not leave a matching central worker process alive
- no raw RTSP credentials, sudo passwords, bearer tokens, node credentials,
  registry credentials, or process args with secrets in outputs
