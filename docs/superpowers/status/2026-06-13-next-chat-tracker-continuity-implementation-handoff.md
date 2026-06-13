# Tracker Continuity Implementation Next-Chat Handoff

Date: 2026-06-13
Branch: `codex/sceneops-pack-registry`
Local HEAD at handoff creation: `edca1a6a`
Remote branch at handoff creation: `origin/codex/sceneops-pack-registry` at `75e95b8f`

## Purpose

The next chat should implement the tracker-continuity improvement work from the
new spec and plan, using subagent-driven development and TDD.

The product goal is best-in-class tracking continuity and persistence for the
current detector/tracker architecture:

```text
detector outputs
  -> candidate quality gate
  -> Ultralytics tracker
  -> lifecycle manager
  -> canonical telemetry ingest
  -> persistence + WebSocket fanout
```

Do not introduce DeepStream, ReID downloads, central Dockerized GPU claims, or a
new telemetry contract in this work.

## Read First In Next Chat

1. `docs/superpowers/status/2026-06-13-next-chat-tracker-continuity-implementation-handoff.md`
2. `docs/superpowers/specs/2026-06-13-tracker-continuity-improvements-design.md`
3. `docs/superpowers/plans/2026-06-13-tracker-continuity-improvements-implementation-plan.md`
4. `docs/superpowers/status/2026-06-12-next-chat-edge-nats-telemetry-architecture-handoff.md`
5. `docs/superpowers/status/2026-06-11-jetson-live-overlay-stability-handoff.md`
6. `docs/superpowers/status/2026-06-10-jetson-source-reinit-nvmm-cuda-closure-report.md`
7. `docs/superpowers/status/2026-06-10-jetson-native-capture-optimization-closure-report.md`
8. `docs/superpowers/status/2026-06-10-next-chat-docs-deepstream-worker-performance-handoff.md`
9. `docs/superpowers/status/2026-06-09-whole-product-live-smoke-closure-report.md`
10. `docs/model-loading-and-configuration-guide.md`
11. `docs/core-link-performance-guide.md`
12. `docs/product-installer-and-first-run-guide.md`
13. `docs/operator-deployment-playbook.md`
14. `docs/runbook.md`
15. `README.md`

Use Superpowers. For implementation, use
`superpowers:subagent-driven-development` unless the user explicitly asks for
inline execution. Use `superpowers:test-driven-development` before code
changes, `superpowers:systematic-debugging` for unexpected behavior, and
`superpowers:verification-before-completion` before claiming done.

## Current Branch State

Start with:

```bash
cd /Users/yann.moren/vision
git fetch origin codex/sceneops-pack-registry
git status --short --branch
git rev-parse --short HEAD
git rev-list --left-right --count origin/codex/sceneops-pack-registry...HEAD
git log --oneline --decorate -8
```

At handoff creation, expected local state was:

```text
## codex/sceneops-pack-registry...origin/codex/sceneops-pack-registry [ahead 2]
 M docs/superpowers/specs/2026-06-13-tracker-continuity-improvements-design.md
?? docs/superpowers/plans/2026-06-13-tracker-continuity-improvements-implementation-plan.md
?? docs/superpowers/status/2026-06-13-next-chat-tracker-continuity-implementation-handoff.md
```

The actual workspace also has many unrelated untracked files and folders such as
`.claude/`, `.codex/`, `.superpowers/brainstorm/...`, `.vite/`, old
screenshots, strategy drafts, `output/`, and `taste-skill/`. Preserve them.
Use explicit `git add -- path ...`; do not use `git add -A`.

Local commits ahead of origin at handoff creation:

```text
edca1a6a docs: revise tracker and EVE-OS specs per review
1bd0fea5 docs: spec tracker continuity, dev stack stability, and EVE-OS edge
```

The new tracker spec edits, implementation plan, and this handoff are not
pushed. Do not commit or push unless the user explicitly asks.

## What Was Done In This Chat

The tracker-continuity spec was rewritten and the implementation plan was
created:

- `docs/superpowers/specs/2026-06-13-tracker-continuity-improvements-design.md`
- `docs/superpowers/plans/2026-06-13-tracker-continuity-improvements-implementation-plan.md`

Then a review pass was incorporated into both documents:

- `_freeze_attributes(...)` must be idempotent for `MappingProxyType`.
- Runtime tracker rebuilds must use the same effective processing FPS as
  initial engine construction.
- The replay gate must reject a weak baseline with fewer than five total
  continuity defects across `id_switches + track_fragmentation_sum`.
- Replay fixture manifests include `tracker_scene_profile`, defaulting to
  `"difficult"`.
- Baseline/current replay comparisons must use byte-identical fixture contents.

Docs sanity checks already run:

- Superpowers placeholder/red-flag scan against the tracker spec and plan:
  clean
- `git diff --check -- docs/superpowers/specs/2026-06-13-tracker-continuity-improvements-design.md docs/superpowers/plans/2026-06-13-tracker-continuity-improvements-implementation-plan.md`:
  clean

No implementation tests were run for this handoff because the code has not been
changed for the tracker-continuity work yet.

## Implementation Goal

Reduce stable track ID churn in simple one-to-two person scenes while preserving
canonical telemetry and persistence behavior.

The implementation must:

- use effective processing FPS as the single cadence source for tracker and
  lifecycle timing
- keep browser delivery FPS decoupled from processing FPS
- keep Scene UI `fps_cap` as the processing FPS source of truth unless an
  explicit CPU fallback clamp is configured
- gate ReID by runtime capability and local model availability
- avoid implicit model downloads in worker startup or frame processing
- make GMC explicit through JSON profile configuration only
- prevent association-only detections from spawning new tracks
- stabilize lifecycle coasting with a constrained center motion filter
- add confidence EMA, class voting, and immutable detection attributes
- add a deterministic replay gate with ground-truth identities
- leave NATS, persistence, WebSocket fanout, and live telemetry frame schemas
  compatible with the current product

## Execute The Plan

Follow
`docs/superpowers/plans/2026-06-13-tracker-continuity-improvements-implementation-plan.md`
task-by-task.

Recommended execution mode:

```text
Use superpowers:subagent-driven-development.
Dispatch one fresh subagent per task.
Review each subagent result before moving to the next task.
Keep code edits small and test-first.
```

Task order from the plan:

1. Ground-truth replay benchmark
2. Effective processing FPS wiring
3. Runtime-gated ReID and GMC profile wiring
4. Candidate quality association semantics
5. Lifecycle motion, confidence, class, and attributes
6. Tracker adapter dtype and config propagation
7. Wire replay runner to actual tracker stack
8. Enable replay gate and final verification

The plan contains exact test snippets and commands. Do not skip the failing-test
steps. Update checkbox status in the plan as each step is completed.

## High-Risk Details To Preserve

### Effective Processing FPS

The only cadence value for tracker timing is:

```python
effective_processing_fps = _processing_fps_cap(
    camera.fps_cap,
    runtime_policy=runtime_policy,
    cpu_fallback_cap=settings.cpu_fallback_processing_fps_cap,
)
```

This value must feed:

- `CameraSourceConfig.fps_cap`
- `TrackerConfig.frame_rate`
- `TrackLifecycleConfig.nominal_frame_interval_ms`
- replay benchmark tracker config

`RuntimeInferenceEngine._build_tracker()` and
`RuntimeInferenceEngine._build_track_lifecycle()` must recompute through
`self._effective_processing_fps_cap()` whenever rebuilt, including runtime
tracker-type changes. Do not infer the value from browser output FPS.

### ReID Runtime Gate

ReID may turn on only when all are true:

1. the resolved profile requests appearance cues
2. tracker type is BoT-SORT
3. runtime is not CPU fallback
4. the appearance model is already locally available or available without a
   network download

Central CPU ONNX must keep ReID off. Report a diagnostic reason such as
`reid_unavailable_runtime` rather than downloading a model or silently changing
runtime assumptions.

### Candidate Quality

Detections below display/new-track confidence may extend existing nearby tracks
but must not create new tracks. This is the heart of the "two people should not
become many persisted stable IDs" fix.

### Lifecycle Coasting

Use a center-based motion filter:

- state `[cx, cy, vx, vy]`
- velocity in pixels per millisecond
- `last_seen_ts` advances only on real detections and controls TTL
- `updated_ts` advances on detection updates and coast predictions
- width/height freeze from the latest real detection
- clamp predicted bbox to frame bounds

### Immutable Attributes

`Detection.attributes` should become a frozen mapping. The freeze helper must
return an existing `MappingProxyType` unchanged so copied detections do not
allocate a fresh attribute dict on every frame.

## Verification Commands

Run targeted tests as tasks land. Final local verification should include:

```bash
./backend/.venv/bin/pytest \
  backend/tests/scripts/test_tracking_replay_benchmark.py \
  backend/tests/inference/test_engine.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/vision/test_candidate_quality.py \
  backend/tests/vision/test_track_lifecycle.py \
  backend/tests/vision/test_tracker.py -q

./backend/.venv/bin/ruff check \
  scripts/tracking_replay_benchmark.py \
  backend/src/argus/inference/engine.py \
  backend/src/argus/vision/candidate_quality.py \
  backend/src/argus/vision/track_lifecycle.py \
  backend/src/argus/vision/tracker.py \
  backend/src/argus/vision/profiles.py \
  backend/src/argus/vision/types.py \
  backend/src/argus/api/contracts.py \
  backend/tests/scripts/test_tracking_replay_benchmark.py \
  backend/tests/inference/test_engine.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/vision/test_candidate_quality.py \
  backend/tests/vision/test_track_lifecycle.py \
  backend/tests/vision/test_tracker.py

./backend/.venv/bin/python scripts/tracking_replay_benchmark.py \
  --fixture backend/tests/scripts/fixtures/tracker_continuity_people_001 \
  --baseline backend/tests/scripts/fixtures/tracking_replay_baseline.json \
  --assert-improvement

git diff --check
```

Broader backend/frontend checks may be needed if implementation touches shared
contracts or UI-visible runtime reports. Do not call work complete until the
targeted tests and replay gate pass, or until failures are explicitly reported
as `FAIL` or `BLOCKED` with evidence.

## Live A/B Smoke After Implementation

After implementation, commit/push only if the user asks. If the user asks for
live validation, rebuild and redeploy both master and Jetson from the final
branch before testing.

Recommended live evidence:

- master and Jetson image/build identifiers match the branch under test
- central and edge runtime report fresh per-camera heartbeats
- central processing FPS reflects the Scene UI `fps_cap`, not browser delivery
  FPS
- edge processing FPS reflects the Scene UI `fps_cap`, subject only to explicit
  CPU fallback clamp if configured
- NATS transport remains primary for telemetry
- HTTP edge telemetry remains fallback
- no duplicate persisted/live frames for the same canonical frame
- `tracking_events` history remains populated
- WebSocket live frames are delivered only after master ingest acceptance
- stable ID count in a simple one-to-two person scene is closer to real people
  than the pre-change baseline
- runtime diagnostics report transport, cadence, drops, duplicate frames,
  fallback state, and tracker diagnostics

Collect worker metrics for both central and Jetson:

- FPS
- total stage time
- detect stage time
- capture stage time
- publish stream stage time
- publish telemetry stage time
- track stage time
- worker CPU and RSS
- Docker container CPU and memory
- sanitized process list without command arguments

If running a whole-product smoke, create the platform user
`yann.moren@mugetsu.tech` using a password supplied out-of-band at smoke time.
Do not write that password into docs, logs, commit messages, screenshots, or
terminal transcripts.

## Live Environment Constraints

Known lab addresses from recent validation:

- master host: `192.168.1.166`
- Jetson Orin EDGE: `192.168.1.203`, SSH user `ai-user`
- edge RTSP host used in smoke evidence: `192.168.1.165`
- central RTSP host used in smoke evidence: `192.168.1.195`

Do not commit or paste raw RTSP credentials, sudo passwords, bearer tokens,
bootstrap tokens, node credentials, reflector secrets, MediaMTX JWTs, registry
credentials, or process args containing secrets. Redact RTSP URLs as:

```text
rtsp://***:***@<host>:8554/<path>
```

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

## Carry-Forward Issues

### Lifecycle Stop Bug

The central stop/reconcile bug remains important and should not be forgotten,
but it is not part of the tracker-continuity implementation unless the user
explicitly broadens scope.

Previous evidence:

- central worker stop request completed and assignment became `not_desired`
- the actual central `argus.inference.engine` child and `ffmpeg` child stayed
  alive under the supervisor
- manual recovery was terminating the matching central camera worker process
  inside `vezor-master-vezor-supervisor-1`
- likely root cause: `LocalWorkerProcessAdapter.stop()` only terminates workers
  present in its in-memory `_processes` map

Required later fix:

- add failing tests for stale/missing process-map entries
- stop/reconcile must verify no matching local worker process remains before
  marking lifecycle completed
- do not infer running/stopped from supervisor node health or stale lifecycle
  state alone
- fresh per-camera heartbeat remains the runtime source of truth
- keep process inspection sanitized

### Central Performance

Central camera performance is CPU ONNX in Docker. Do not claim M4/GPU
acceleration for central. Central native macOS/CoreML acceleration remains a
future lane.

### DeepStream

DeepStream remains a later optional runtime-family track. Do not implement it
inside the tracker-continuity PR.

### Registry Publishing

Registry publishing remains blocked until registry target, repo names,
credentials/auth method, and tag policy are provided.

## PASS / FAIL / BLOCKED / NOT RUN Standard

Use explicit closure evidence:

- `PASS`: command or live check ran and passed; include command/sample and key
  result
- `FAIL`: command or live check ran and failed; include exact failure summary
- `BLOCKED`: external dependency prevents execution; name the dependency and
  the next action
- `NOT RUN`: intentionally skipped; explain why

Do not call missing RTSP, missing model files, missing billing usage, missing
deterministic evidence, missing TensorRT artifact, missing registry credentials,
or missing fresh-stack proof a pass.
