# Next Chat Handoff: Jetson Optimized Runtime Artifacts And Open-Vocab

Date: 2026-05-10

Purpose: paste this document into a fresh chat to continue from the current
`codex/omnisight-ui-spec-implementation` branch. The next implementation step is
the Jetson Optimized Runtime Artifacts And Open-Vocab plan.

## Repository State

Continue from the pushed branch:

```text
codex/omnisight-ui-spec-implementation
```

Latest pushed checkpoint at the time of this handoff:

```text
f8c595d6 docs(runtime): plan jetson optimized artifacts
```

Recent implementation checkpoints on the branch:

```text
fb7ef76e docs(scene): add scene vision configuration guide
feb0975d feat(scene): show vision profile in cameras
5eb93d96 feat(scene): add vision profile setup controls
59eb3e14 chore(frontend): refresh scene vision API types
cb4077d4 feat(scene): add candidate quality metrics
eb13dcb2 feat(scene): make speed metrics explicit
09aff9dd feat(scene): add candidate quality gate
cd37bb1e feat(scene): gate detections by scene regions
f5934650 feat(scene): resolve vision profiles for workers
aee574ac feat(scene): add vision profile camera contracts
```

Start a fresh continuation like this:

```bash
cd "$HOME/vision"
git fetch origin
git switch codex/omnisight-ui-spec-implementation
git pull --ff-only origin codex/omnisight-ui-spec-implementation
git status -sb
git log --oneline -12
```

Known local state:

- unrelated untracked scratch files may exist locally
- do not use `git add -A`
- stage only files needed for the current task

## Required Dev DB Migration

The scene vision profile implementation added camera columns in migration
`0009_scene_vision_profiles`.

If the dev UI shows 500s with either of these errors:

```text
column cameras.vision_profile does not exist
column cameras.detection_regions does not exist
```

run:

```bash
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
```

Then restart backend if needed:

```bash
docker compose -f infra/docker-compose.dev.yml restart backend
```

This is a schema migration issue, not a token/API rebuild issue.

## What Is Now Implemented

### Live Signal Terrain And Stabilized Live Telemetry

The original next-chat target in this handoff was Live signal terrain. That work
has now landed on this branch.

Implemented highlights:

- shared stable signal model and hook
- class-colored telemetry boxes
- Telemetry Terrain surface
- calmer Live status presentation
- stable lifecycle telemetry from the backend
- active/coasting/lost track lifecycle support
- annotated overlay and WebSocket telemetry use the same stabilized backend
  track state
- stream-session visibility gating to recover when navigating away and back
- terrain occupancy rendering fixed to step style

Relevant plans/specs:

- `docs/superpowers/specs/2026-05-09-live-signal-terrain-and-stability-design.md`
- `docs/superpowers/plans/2026-05-09-live-signal-terrain-and-stability-implementation-plan.md`
- `docs/superpowers/specs/2026-05-09-authoritative-live-track-lifecycle-design.md`
- `docs/superpowers/plans/2026-05-09-authoritative-live-track-lifecycle-implementation-plan.md`

### Scene Vision Profiles And Candidate Quality Gate

The scene profile and false-positive/split-track mitigation work has also
landed on this branch.

Implemented highlights:

- persisted `vision_profile` and `detection_regions` camera fields
- optional homography unless speed metrics are enabled
- explicit speed metrics toggle
- worker profile resolver
- include/exclusion detection region gating
- candidate quality gate before tracking
- candidate and region metrics
- frontend wizard controls for profile, compute tier, speed metrics, and regions
- camera list vision profile summary
- scene configuration guide

Relevant docs:

- `docs/superpowers/specs/2026-05-10-scene-vision-profiles-and-candidate-quality-design.md`
- `docs/superpowers/plans/2026-05-10-scene-vision-profiles-and-candidate-quality-implementation-plan.md`
- `docs/scene-vision-profile-configuration-guide.md`

### Open-Vocab Runtime Baseline

Already implemented before this handoff update:

- model catalog open-vocab presets
- dynamic Ultralytics `.pt` open-vocab detector path
- runtime vocabulary persistence
- hot runtime vocabulary updates for open-vocab workers
- capability-aware query commands

Current limitation:

- dynamic `.pt` open vocab is real but still experimental for production Jetson
  use
- compiled per-scene open-vocab artifacts are planned next, not implemented yet

## Next Implementation: Jetson Optimized Runtime Artifacts And Open-Vocab

Use this spec:

```text
docs/superpowers/specs/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-design.md
```

Use this plan:

```text
docs/superpowers/plans/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-implementation-plan.md
```

Implement A and B first:

1. **Track A: Fixed-vocab Jetson optimization**
   - keep ONNX as canonical model
   - add model-scoped validated runtime artifacts
   - allow Jetson TensorRT `.engine` artifacts to be selected only when valid
   - fallback visibly to ONNX Runtime
2. **Track B: Optimized open vocab**
   - keep dynamic `.pt` open vocab for discovery and live vocabulary changes
   - add scene-scoped compiled artifacts for saved runtime vocabularies
   - select compiled artifacts only when vocabulary hash and target profile match
   - fall back to dynamic `.pt` when vocabulary changes

Do not implement Track C yet:

- DeepStream/NvDCF/NvDeepSORT remains a later runtime lane after A/B pass soak
  validation.

Start with Task 1 from the new plan:

```text
Task 1: Runtime Artifact Data Contract
```

Task 1 creates or modifies:

- `backend/src/argus/models/enums.py`
- `backend/src/argus/models/tables.py`
- `backend/src/argus/migrations/versions/0010_model_runtime_artifacts.py`
- `backend/src/argus/api/contracts.py`
- `backend/tests/services/test_runtime_artifacts.py`

Task 1 expected verification:

```bash
cd "$HOME/vision/backend"
python3 -m uv run pytest tests/services/test_runtime_artifacts.py tests/core/test_db.py -q
```

## Remaining Earlier Work Still Pending

The old handoff also queued Evidence Desk polish. That work has not been
implemented yet and still needs to be executed after the optimized runtime A/B
path, unless the user redirects.

Evidence Desk plan:

```text
docs/superpowers/plans/2026-05-09-evidence-desk-timeline-and-case-context-implementation-plan.md
```

Evidence Desk Task 1 will create:

- `frontend/src/lib/evidence-signals.ts`
- `frontend/src/lib/evidence-signals.test.ts`

Expected Evidence work:

- Evidence Timeline density strip
- Case Context Strip
- type-colored review queue
- cleaner raw payload disclosure

Other production hardening still pending outside this immediate next step:

- supervisor-backed Start/Stop/Restart/Drain actions
- persistent worker assignment/reassignment workflows
- production edge credential rotation
- DeepStream/NvDCF/NvDeepSORT runtime lane for Track C

## Working Rules For The Next Chat

- Continue from `codex/omnisight-ui-spec-implementation`.
- Pull latest branch state first.
- Execute one task at a time.
- Commit after each completed task.
- Push to origin after commits so the user can test.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- For optimized runtime work, treat current fixed-vocab ONNX Runtime TensorRT
  provider selection as the baseline; the new work is validated runtime
  artifacts and compiled open-vocab scene artifacts.

## Useful Validation Commands

Frontend:

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Backend focused scene/live checks:

```bash
cd "$HOME/vision/backend"
python3 -m uv run pytest \
  tests/vision/test_track_lifecycle.py \
  tests/vision/test_tracker.py \
  tests/vision/test_candidate_quality.py \
  tests/vision/test_detection_regions.py \
  tests/inference/test_engine.py \
  tests/services/test_camera_worker_config.py \
  -q
```

Dev migrations:

```bash
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
```

## Jetson Lab Commands If Needed Later

Lab guide:

```text
docs/imac-master-orin-lab-test-guide.md
```

Jetson rebuild/restart:

```bash
cd "$HOME/vision"
export JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"
docker compose -f infra/docker-compose.edge.yml up -d --build inference-worker
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

Good evidence to collect if Jetson runtime artifact work starts:

```text
selected_backend
artifact_id
target_profile
fallback
fallback_reason
detect_session avg / max
detect avg / max
total avg / max
CPU/GPU/memory usage
artifact build duration
artifact validation duration
```

## Guardrails

- Keep camera setup, profile switching, video, telemetry, History, and Evidence
  Desk flows working.
- Keep backend as track truth; frontend should display track state, not invent
  identity or occupancy.
- Do not turn raw `.engine` files into primary camera model rows. The new design
  attaches validated target-specific artifacts to canonical models/scenes.
- Do not silently use stale open-vocab compiled artifacts after vocabulary
  changes.
- Preserve dynamic `.pt` open vocab as the fallback/discovery mode.
