# Next Chat Handoff: Live Signal Terrain Implementation

Date: 2026-05-09

Purpose: paste this document into a fresh chat to continue from current `main`.
The next chat should start the Live signal terrain and stabilization implementation
from the written plan. Jetson capture tuning can resume in a future pass if new
same-room or wired-network logs show the remaining capture jitter is still in
software.

## Repository State

`main` has the OmniSight UI work merged and pushed.

Base commit that contains the merged OmniSight UI/spec work:

```text
c7060043 docs(evidence): plan desk timeline polish
```

This handoff document update may appear as the latest commit above that base.

Start from `main`:

```bash
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only origin main
git status -sb
git log --oneline -8
```

If continuing implementation on the existing local branch:

```bash
git switch codex/omnisight-ui-spec-implementation
git merge --ff-only main
```

If the branch does not exist in a fresh clone, create a new implementation
branch from `main` instead of relying on `origin/codex/omnisight-ui-spec-implementation`,
which may lag behind `origin/main`:

```bash
git switch -c codex/omnisight-ui-spec-implementation
```

Known local state:

- unrelated untracked scratch files may exist locally
- do not use `git add -A`
- stage only files needed for the current task

Latest verification before merging to `main`:

- `corepack pnpm --dir frontend test` passed: 53 files, 203 tests
- `corepack pnpm --dir frontend lint` passed with 0 errors and 12 warnings
- `corepack pnpm --dir frontend build` passed
- known frontend test noise: React `act(...)` warnings from
  `VideoStream.test.tsx` and React Router future-flag warnings

Earlier backend verification from the edge/capture work:

- `python3 -m uv run pytest -q` passed with 365 tests

## What Was Completed In This Chat

### Jetson / Capture

Jetson TensorRT inference is healthy and should not be the default target for
more optimization.

Evidence already observed:

```text
Resolved inference runtime policy profile=linux-aarch64-nvidia-jetson
detection_provider=TensorrtExecutionProvider
available_providers=['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
Loaded detection model YOLO26n COCO Edge with provider TensorrtExecutionProvider
```

Recent Jetson timing shape:

```text
detect_session ~= 9-10 ms
detect ~= 17-23 ms
capture_wait avg ~= 32-46 ms
capture_wait p95 ~= 48-146 ms depending on RTSP settings
capture_wait p99/max ~= 500-570 ms during spikes
```

Interpretation:

- detector runtime is not the bottleneck
- tracking, stream relay, persistence buffering, and bounded telemetry drops are
  not the current bottlenecks
- remaining spikes line up with `capture_wait`, so treat them as
  RTSP/GStreamer/camera/network delivery jitter first

RTSP/GStreamer tests tried:

- `ARGUS_JETSON_RTSP_LATENCY_MS=50`
  - native GStreamer active
  - p95 often lower, but p99/max stayed near 500 ms
- `ARGUS_JETSON_RTSP_LATENCY_MS=100`
  - native GStreamer active
  - p95 often 70-90 ms, but p99/max stayed near 500 ms
- `ARGUS_JETSON_RTSP_LATENCY_MS=200`
  - produced GStreamer RTSP parse/read errors and no first frame within 20s
  - fallback path started, so 200 ms was not useful in that lab state
- `ARGUS_JETSON_RTSP_PROTOCOLS=udp`
  and `ARGUS_JETSON_RTSP_DROP_ON_LATENCY=true`
  - p95 improved in some windows
  - p99/max still showed 500 ms class waits

Camera ping from Jetson showed network jitter and packet loss:

```text
63 packets transmitted, 62 received, 1.5873% packet loss
rtt min/avg/max/mdev = 1.914/11.109/65.223/15.678 ms
```

The user planned to move the Jetson closer to the camera. Until fresh logs after
that move contradict it, treat connectivity/RTSP source stability as the reason
capture tuning was paused.

### OmniSight UI / UX

The OmniSight UI work through Phase 5A was merged to `main` and pushed.

Highlights:

- v2 `--vz-*` design tokens, Space Grotesk + Inter, updated workspace surfaces
- sign-in CSS 3D OmniSight lens replacing the large MP4 hero
- sign-in logo white-background flash fixed
- orbital/elliptic guide lines removed and hidden globally
- dashboard spatial cockpit with deployment posture and attention stack
- motion presets, workspace transition, nav focus shaft, evidence swap motion
- operations scene intelligence matrix
- Live scene operational status strip
- Sites inventory readiness cue
- frontend operational readiness derivation
- WebGL remains off/deferred

### Specs And Plans Added

Live signal terrain and anti-flap work:

- `docs/superpowers/specs/2026-05-09-live-signal-terrain-and-stability-design.md`
- `docs/superpowers/plans/2026-05-09-live-signal-terrain-and-stability-implementation-plan.md`

Evidence Desk polish work:

- `docs/superpowers/specs/2026-05-09-evidence-desk-timeline-and-case-context-design.md`
- `docs/superpowers/plans/2026-05-09-evidence-desk-timeline-and-case-context-implementation-plan.md`

Operational readiness UI work:

- `docs/superpowers/specs/2026-05-09-operational-readiness-ui-design.md`
- `docs/superpowers/plans/2026-05-09-operational-readiness-ui-phase-5a.md`

## Current Product Issue To Fix Next

The Live page is visually close to the desired direction, but the current
telemetry presentation flaps because it renders raw latest-frame detections.

Observed in the user's live capture:

- person box appears and disappears even while the person is plainly visible
- `0 visible now` can appear while a person is visible
- right-side live signal rows flap with the latest frame
- the line chart under the video looks weak and too graph-like
- top legends/chips above the video are too diagnostic and not as readable as
  the positioning report suggests

Chosen direction:

- stabilize object boxes and counts with a short held-signal window
- show held tracks as subdued/dashed rather than claiming they are live
- color tracking boxes by object class/family
- replace the line list under the video with the approved Telemetry Terrain
  gradient surface
- make the top legend/state area calmer and more product-readable

## Next Implementation: Live Signal Terrain

Use this plan:

```text
docs/superpowers/plans/2026-05-09-live-signal-terrain-and-stability-implementation-plan.md
```

User preference:

- execute one task at a time
- commit after each completed task
- report the result
- wait for the next `go`
- use subagents only if the user explicitly asks for subagent execution in the
  new chat

Start with Task 1 from the plan:

```text
Task 1: Shared Live Signal Stability Model
```

Task 1 creates:

- `frontend/src/lib/live-signal-stability.ts`
- `frontend/src/lib/live-signal-stability.test.ts`

Expected utility responsibilities:

- `DEFAULT_SIGNAL_HOLD_MS = 1200`
- stable `class_name + track_id` keys
- deterministic class/family colors
- live versus held track state
- held-track expiry after the hold window
- stable live/held counts by class

After Task 1, continue in order:

1. `useStableSignalFrame` hook
2. class-colored `TelemetryCanvas` overlay with held-state treatment
3. new `TelemetryTerrain` component
4. calmer `SceneStatusStrip` and stable `DynamicStats`
5. `Live.tsx` integration
6. final frontend verification and browser visual QA

Recommended pre-flight before Task 1:

```bash
cd "$HOME/vision"
git status -sb
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Task-level test command:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/live-signal-stability.test.ts
```

## After Live Signal Terrain

Once the Live page is stable and visually reviewed, move to the Evidence Desk
polish plan:

```text
docs/superpowers/plans/2026-05-09-evidence-desk-timeline-and-case-context-implementation-plan.md
```

Evidence Desk Task 1 will create:

- `frontend/src/lib/evidence-signals.ts`
- `frontend/src/lib/evidence-signals.test.ts`

The Evidence work should add:

- Evidence Timeline density strip
- Case Context Strip
- type-colored review queue
- cleaner raw payload disclosure

Do not start Evidence Desk implementation until Live signal terrain has landed,
unless the user explicitly redirects.

## Jetson Lab Commands If Needed Later

Lab guide:

```text
docs/imac-master-orin-lab-test-guide.md
```

Jetson rebuild/restart:

```bash
cd "$HOME/vision"
git switch main
git pull --ff-only origin main
export JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"
docker compose -f infra/docker-compose.edge.yml up -d --build inference-worker
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

Useful Jetson RTSP env combinations:

```bash
export ARGUS_JETSON_RTSP_PROTOCOLS=tcp
export ARGUS_JETSON_RTSP_LATENCY_MS=100
export ARGUS_JETSON_RTSP_DROP_ON_LATENCY=true
docker compose -f infra/docker-compose.edge.yml up -d --force-recreate inference-worker
docker compose -f infra/docker-compose.edge.yml logs -f --tail=50 inference-worker
```

UDP trial, only after camera path is stable:

```bash
export ARGUS_JETSON_RTSP_PROTOCOLS=udp
export ARGUS_JETSON_RTSP_LATENCY_MS=100
export ARGUS_JETSON_RTSP_DROP_ON_LATENCY=true
docker compose -f infra/docker-compose.edge.yml up -d --force-recreate inference-worker
docker compose -f infra/docker-compose.edge.yml logs -f --tail=50 inference-worker
```

Good evidence to collect if Jetson work resumes:

```text
capture_wait avg / p95 / p99 / max
capture_read avg / max
capture_reconnect avg / max
detect_session avg / max
publish_stream avg / max
total avg / max
GStreamer parse/read errors
camera ping packet loss and jitter after moving Jetson
```

## Guardrails

- Work from current `main`.
- Keep TensorRT, stream relay, persistence buffering, and telemetry drops treated
  as solved unless fresh logs contradict that.
- Do not optimize detector/tracker for the Live UI flapping issue; the planned
  fix is frontend stabilization of latest-frame presentation.
- Do not reintroduce double RTSP reads for native/no-privacy delivery.
- Do not start WebGL work; it is intentionally deferred.
- Preserve working video, camera setup, profile switching, and review flows.
- Do not stage unrelated untracked scratch files.
