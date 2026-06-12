# Edge NATS Telemetry And Lifecycle Stop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jetson edge telemetry use NATS leaf primary delivery while preserving tracking history, WebSocket live delivery, HTTP fallback, deduplication, and truthful worker stop lifecycle completion.

**Architecture:** Edge workers publish to `evt.edge.tracking.<camera_id>`. The master telemetry ingest service consumes that subject with a durable consumer on `ARGUS_TRACKING`, persists deterministic tracking rows, and broadcasts once on `evt.tracking.<camera_id>`. HTTP ingest delegates to the same service. Local worker stop verifies the matching process is actually gone before lifecycle completion can succeed.

**Tech Stack:** FastAPI services, NATS JetStream, SQLAlchemy/Postgres conflict inserts, pytest, installer/NATS config fixtures, supervisor process adapter.

---

## File Map

- Modify `backend/src/argus/core/events.py`: add edge tracking stream subject
  and durable subscription arguments.
- Modify `backend/src/argus/core/config.py`: add NATS stream-management
  control for leaf/local core NATS use.
- Modify `backend/src/argus/inference/engine.py`: edge runtime publisher
  becomes NATS primary on edge subject with HTTP fallback.
- Modify `backend/src/argus/services/app.py`: add shared telemetry ingest
  service, delegate HTTP ingest, start/close durable consumer lifecycle.
- Modify runtime report contracts/models/migration/generated frontend API for
  telemetry transport/path/cadence/drop/fallback fields.
- Modify `backend/src/argus/supervisor/process_adapter.py`: verify/terminate
  stale matching worker processes.
- Modify `infra/nats/nats.conf`, `infra/nats/leaf.conf`,
  `infra/install/compose/*`, and installer tests as needed for scoped edge leaf
  permissions.
- Modify tests:
  - `backend/tests/inference/test_engine.py`
  - `backend/tests/services/test_telemetry_service.py`
  - `backend/tests/core/test_events.py`
  - `backend/tests/supervisor/test_process_adapter.py`
  - installer/core config tests for NATS permissions

## Task 1: Red Tests For Telemetry Architecture

- [x] Update `test_build_runtime_engine_uses_edge_http_telemetry_ingest_for_edge_mode`
  into an edge NATS primary test. Expected red failure: wrapped publisher is
  still `HttpPublisher`, not `ResilientPublisher`.
- [x] Add a telemetry ingest service test that delivers a fake
  `evt.edge.tracking.<camera_id>` message and expects one deterministic DB
  insert plus one publish to `evt.tracking.<camera_id>`. Expected red failure:
  service does not exist.
- [x] Add duplicate NATS+HTTP test. Expected red failure: HTTP and NATS paths
  do not share dedup/broadcast state.
- [x] Add stream definition test for `evt.edge.tracking.*`. Expected red
  failure: subject is missing.

## Task 2: Implement Master Ingest Service

- [x] Add deterministic row conversion helper from `TelemetryFrame` to
  `TrackingEvent` insert dictionaries.
- [x] Add conflict insert using `on_conflict_do_nothing(index_elements=["id", "ts"])`.
- [x] Add live broadcast only for new frames.
- [x] Add subscription startup and close handling in `AppServices`.
- [x] Make `EdgeService.ingest_telemetry()` delegate to the shared service.
- [x] Make the master edge telemetry consumer durable on `ARGUS_TRACKING`.

## Task 3: Implement Edge NATS Primary Publisher

- [x] Add or reuse publish settings so edge mode uses `evt.edge.tracking`.
- [x] Build `ResilientPublisher(primary=NatsPublisher(...), fallback=HttpPublisher(...))`.
- [x] Keep latest-only HTTP fallback buffering and the current flush interval.
- [x] Preserve central `evt.tracking` behavior.
- [x] Report transport, path, cadence, fallback state, drops, pending frames,
  and last error in worker runtime reports.

## Task 4: Red Tests And Fix For Lifecycle Stop

- [x] Add a failing test where `_processes` is empty but a process-table match
  exists for the camera id; `stop()` must terminate it and return stopped.
- [x] Add a failing test where the matching process remains after terminate;
  `stop()` must return `runtime_state="error"` with a sanitized error.
- [x] Implement injected/default process finder and post-stop verification.
- [x] Ensure process inspection never logs raw argv or RTSP/token material.

## Task 5: NATS Permissions And Docs

- [x] Add scoped edge leaf permissions for `evt.edge.tracking.*`.
- [x] Update tests that render/check NATS configs.
- [x] Update relevant docs if the operator-facing subject/path changed.

## Task 6: Verification And Live Smoke

- [x] Run targeted backend tests for publisher, engine, telemetry service,
  events, process adapter, reconciler, and installer config.
- [x] Run targeted frontend tests if runtime health/status API changes affect
  UI generated contracts.
- [x] Run `ruff` on modified backend files and `git diff --check`.
- [ ] Rebuild/redeploy master and Jetson from the final branch.
- [ ] Create platform user `yann.moren@mugetsu.tech` with the requested
  password during whole-product smoke.
- [ ] Smoke Jetson and central live behavior; record PASS/FAIL/BLOCKED/NOT RUN
  with sanitized evidence.
