# Edge NATS Telemetry Architecture Next-Chat Handoff

Date: 2026-06-12
Branch: `codex/sceneops-pack-registry`
Latest pushed code-fix head before this handoff: `c0d8aabe`

## Purpose

The next chat should spec and plan the edge telemetry architecture change:

```text
Jetson worker -> NATS leaf -> master NATS -> master telemetry consumer persists + WebSocket broadcasts
```

This handoff records the current evidence, the committed short-term fix, and
the constraints from the previous whole-product and Jetson handoffs. Start the
next chat with design/spec work, not DeepStream implementation.

## Read First In Next Chat

1. `docs/superpowers/status/2026-06-12-next-chat-edge-nats-telemetry-architecture-handoff.md`
2. `docs/superpowers/status/2026-06-11-jetson-live-overlay-stability-handoff.md`
3. `docs/superpowers/status/2026-06-10-jetson-source-reinit-nvmm-cuda-closure-report.md`
4. `docs/superpowers/status/2026-06-10-jetson-native-capture-optimization-closure-report.md`
5. `docs/superpowers/status/2026-06-10-next-chat-docs-deepstream-worker-performance-handoff.md`
6. `docs/superpowers/status/2026-06-09-whole-product-live-smoke-closure-report.md`
7. `docs/superpowers/status/2026-06-09-next-chat-remaining-live-smoke-closure-handoff.md`
8. `docs/superpowers/status/2026-06-08-next-chat-whole-product-live-smoke-handoff.md`
9. `docs/model-loading-and-configuration-guide.md`
10. `docs/core-link-performance-guide.md`
11. `docs/product-installer-and-first-run-guide.md`
12. `docs/operator-deployment-playbook.md`
13. `docs/runbook.md`
14. `README.md`

Use Superpowers. For implementation, use systematic debugging for live
behavior, write failing tests before code changes, and verify before claiming
pass.

## Current Branch State

Start with:

```bash
cd /Users/yann.moren/vision
git fetch origin codex/sceneops-pack-registry
git status --short --branch
git rev-parse --short HEAD
git rev-list --left-right --count origin/codex/sceneops-pack-registry...HEAD
```

Expected branch: `codex/sceneops-pack-registry` at or after `c0d8aabe`.

This workspace has unrelated untracked local files and folders such as
`.claude/`, `.codex/`, `.superpowers/brainstorm/...`, `.vite/`, old
screenshots, strategy drafts, `output/`, and `taste-skill/`. Do not stage them.
Use explicit `git add -- path ...`; do not use `git add -A`.

## Short-Term Fix Committed

Commit `c0d8aabe` (`fix: increase edge telemetry cadence`) was pushed to
`origin/codex/sceneops-pack-registry`.

It changed:

- Edge HTTP telemetry ingest flush interval from the old hard-coded `0.5s`
  cadence to a configurable `0.1s` default:
  `ARGUS_EDGE_TELEMETRY_FLUSH_INTERVAL_SECONDS`.
- Edge HTTP telemetry remains latest-only (`max_buffer_size=1`) to avoid a
  stale backlog.
- Browser telemetry overlays are now enabled only for `passthrough` streams.
- The Live page disables and greys out the Browser overlay checkbox for
  `annotated-whip` and `filtered-preview` processed/transcoded streams.

Verification for `c0d8aabe`:

```bash
backend/.venv/bin/pytest \
  backend/tests/inference/test_publisher.py \
  backend/tests/inference/test_engine.py \
  backend/tests/vision/test_track_lifecycle.py -q

corepack pnpm --dir frontend exec vitest run \
  src/lib/live-signal-stability.test.ts \
  src/hooks/use-stable-signal-frame.test.tsx \
  src/components/live/TelemetryCanvas.test.tsx \
  src/components/live/TelemetryTerrain.test.tsx \
  src/pages/Live.test.tsx

corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
backend/.venv/bin/ruff check \
  backend/src/argus/core/config.py \
  backend/src/argus/inference/engine.py \
  backend/tests/inference/test_engine.py
git diff --check
```

Observed results:

- backend targeted tests: `115 passed`
- frontend targeted tests: `51 passed`
- frontend lint: passed
- frontend build: passed, with the existing non-fatal Vite warning about
  `src/lib/auth.ts` being statically and dynamically imported
- backend Ruff: passed
- diff whitespace check: passed

This fix was committed and pushed, but it was not rebuilt/redeployed or
live-smoked after the commit in this chat.

## Root Cause Evidence For The Architecture Work

The Jetson worker is not limited to the low UI cadence. Worker metrics from
inside the Jetson supervisor container showed:

- sample window: 15 seconds
- `frames_delta=234`
- observed worker FPS: `15.6`
- average frame time: `57.0ms`
- largest average stages:
  - `detect`: `22.0ms`
  - `capture`: `19.0ms`
  - `capture_throttle`: `16.5ms`
  - `publish_stream`: `8.8ms`

In the same investigation, master-side NATS live samples showed the edge UI was
receiving far fewer frames:

- 15-second master NATS sample for edge camera: `23` frames, about `1.5 fps`
- earlier side-by-side sample:
  - central: 73 frames, average interval about `61.5ms`
  - edge: 7 frames, average interval about `625.5ms`
- longer sample:
  - central: 536 frames
  - edge: 88 frames
  - edge counts briefly dropped `2 -> 1 -> 0 -> 1`, then the last 20 edge
    frames were steady at `2`

Code root cause:

- `build_runtime_engine()` switches edge workers to `HttpPublisher` whenever
  `config.mode is ProcessingMode.EDGE`.
- That path posts batches to `/api/v1/edge/telemetry`, and the master then
  persists rows and republishes each frame to `evt.tracking.<camera_id>`.
- Before `c0d8aabe`, the edge HTTP publisher was latest-only and flushed every
  `0.5s`, so master/UI saw roughly 1.5-2 fps even when the Jetson worker was
  processing around 15-18 fps.

Current path:

```text
Jetson worker -> HTTP /api/v1/edge/telemetry -> master DB insert -> master NATS/WebSocket
```

Target path:

```text
Jetson worker -> NATS leaf -> master NATS -> telemetry consumer -> DB + WebSocket
```

HTTP should remain as a fallback path, not be removed blindly.

## Architecture Requirements

The next architecture must not bypass history/persistence. A direct edge NATS
frame must still become:

- a live WebSocket frame for operators
- a persisted `tracking_events` row set for history/evidence
- deduplicated if fallback HTTP and NATS both deliver the same frame

Recommended design questions for the spec:

- Which subject should the edge worker publish to?
  Existing live subjects are `evt.tracking.<camera_id>`.
- Should the master telemetry consumer consume the same subject and persist
  without republishing, or should it republish on a separate post-persistence
  subject to avoid loops?
- How should WebSocket delivery avoid duplicate frames if it already subscribes
  to `evt.tracking.*`?
- What NATS leaf auth/permissions are required so edge nodes can publish only
  scoped telemetry subjects?
- How does fallback HTTP activate when the NATS path is unavailable?
- What health metrics prove the active telemetry path, publish cadence,
  persistence cadence, drops, and fallback state?
- What backpressure policy is acceptable for live UI versus durable history?

Likely implementation areas:

- `backend/src/argus/inference/engine.py`
- `backend/src/argus/inference/publisher.py`
- `backend/src/argus/services/app.py` edge telemetry ingestion and telemetry
  subscription services
- `backend/src/argus/core/config.py`
- supervisor/installer NATS leaf configuration and node credentials
- operations/runtime reporting so the active telemetry transport is visible
- frontend only if the API exposes transport/fallback status

## Test Plan For The Next Architecture

Write failing tests before implementation. Suggested regressions:

- edge runtime selects NATS publisher as primary when a NATS leaf path is
  configured and reachable
- HTTP publisher remains fallback when NATS publish fails or is disabled
- master telemetry consumer persists NATS-delivered edge frames into
  `tracking_events`
- duplicate NATS + HTTP delivery for the same camera/timestamp/track id inserts
  once
- WebSocket subscribers receive one live frame per edge telemetry frame, not a
  duplicate from persistence republish
- edge telemetry transport/path is reported in runtime or supervisor status
- install/compose config grants the edge leaf only scoped publish permissions

Live validation after implementation should measure:

- Jetson worker FPS from `argus_inference_frames_processed_total`
- master NATS received FPS for the edge camera
- WebSocket/browser signal cadence
- tracking_events insert cadence and history series correctness
- fallback behavior by temporarily blocking the primary NATS path
- no raw credentials in logs/docs/screenshots

## Whole-Product Smoke Guidance

Yes, a whole-product smoke is worth rerunning later, but not necessarily for
the small `c0d8aabe` HTTP-cadence/UI-control fix alone.

Recommended validation order:

1. For `c0d8aabe`, if it is deployed before the architecture work, run a
   targeted live smoke:
   - rebuild/redeploy master and Jetson from the committed branch
   - confirm edge master-side telemetry cadence improves from about 1.5-2 fps
   - confirm Jetson worker FPS remains around the worker metrics baseline
   - confirm processed stream Browser overlay checkbox is disabled/unchecked
2. For the NATS architecture branch, run a targeted architecture smoke first:
   - NATS leaf to master NATS telemetry path
   - persistence/history correctness
   - WebSocket live cadence
   - HTTP fallback
3. After the architecture is committed and deployed, rerun the broader
   whole-product live smoke from the previous handoffs if the goal is product
   closure. Preserve the previous destructive reset constraints: do not delete
   model artifacts, do not global-prune Docker, and distinguish `PASS`, `FAIL`,
   `BLOCKED`, and `NOT RUN`.

Do not call missing RTSP, missing model files, missing billing usage, missing
deterministic evidence, missing TensorRT artifact, missing registry credentials,
or missing fresh-stack proof a pass.

## Important Constraints Carried Forward

- Do not infer `runtime_status=running` from central supervisor node health
  alone.
- A central camera worker is running only when a fresh per-camera runtime
  report exists.
- If no per-camera report exists, show `not_reported` / awaiting first
  heartbeat.
- Browser-drawn telemetry overlays are only for native/passthrough streams.
  `annotated-whip` and `filtered-preview` are worker-rendered processed streams.
- `filtered-preview` is currently misleading naming for the Jetson processed
  privacy-safe stream. A later contract cleanup should make this explicit.
- Preserve DeepStream as a later optional runtime-family track; do not implement
  DeepStream in this NATS telemetry architecture work.
- Keep central M4 acceleration as a future native macOS/CoreML lane. Do not
  claim Dockerized central GPU acceleration.
- Registry publishing remains blocked until registry target, repo names,
  credentials/auth method, and tag policy are provided.

## Live Environment Notes

Known lab addresses from recent validation:

- master host: `192.168.1.166`
- Jetson Orin EDGE: `192.168.1.203`, SSH as `ai-user`
- edge RTSP host used in smoke evidence: `192.168.1.165`
- central RTSP host used in smoke evidence: `192.168.1.195`

Do not commit or paste raw RTSP credentials, sudo passwords, bearer tokens,
bootstrap tokens, node credentials, reflector secrets, MediaMTX JWTs, or
registry credentials. Redact RTSP URLs as
`rtsp://***:***@<host>:8554/<path>`.

Safe monitoring examples:

```bash
ssh -o BatchMode=yes ai-user@192.168.1.203 \
  'docker stats --no-stream --format "{{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}} mempct={{.MemPerc}} pids={{.PIDs}}"'
```

```bash
ssh -o BatchMode=yes ai-user@192.168.1.203 \
  'docker top vezor-supervisor -eo pid,ppid,pcpu,pmem,rss,etime,comm'
```

```bash
ssh -o BatchMode=yes ai-user@192.168.1.203 \
  'timeout 12s tegrastats --interval 1000'
```

Avoid raw process-argument dumps; they can include RTSP credentials and publish
tokens.
