# Next Chat Handoff: Accountable Scene Intelligence And Evidence Recording

Date: 2026-05-11

Purpose: paste this document into a fresh chat to continue from the current
`codex/omnisight-ui-spec-implementation` branch. The next implementation stage
is Accountable Scene Intelligence And Evidence Recording.

## Repository State

Continue from the pushed branch:

```text
codex/omnisight-ui-spec-implementation
```

Latest pushed implementation checkpoint before this handoff update:

```text
712e0199 docs(cameras): add edge usb source support plan
```

Recent checkpoints on this branch:

```text
712e0199 docs(cameras): add edge usb source support plan
c4f64677 docs(evidence): plan accountable scene intelligence
654cfd31 docs(models): add loading and configuration guide
936d59bb fix(runtime): harden artifact verification
84334557 docs(runtime): explain optimized open-vocab artifacts
c9d6530f feat(ui): show runtime artifact status
be24bbcb feat(open-vocab): select compiled scene runtimes
c06e0432 feat(open-vocab): build compiled scene artifacts
97190300 feat(open-vocab): scope artifacts to scene vocabulary
16297f84 docs(jetson): document fixed-vocab runtime artifacts
0041f3ec feat(scripts): register and validate runtime artifacts
e2bca4dc feat(worker): select optimized runtime artifacts
397bc3f6 feat(vision): load TensorRT engine artifacts
5ecc8800 feat(runtime): select validated artifacts
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
`0009_scene_vision_profiles`. The runtime artifact work added
`0010_model_runtime_artifacts`.

If the dev UI shows 500s with either of these errors:

```text
column cameras.vision_profile does not exist
column cameras.detection_regions does not exist
relation model_runtime_artifacts does not exist
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

## What Is Now Implemented

### Live And Scene Stability

Implemented:

- Live signal stabilization and Telemetry Terrain
- authoritative backend track lifecycle
- class-colored telemetry overlays
- stream-session visibility gating
- scene vision profiles
- explicit speed metrics toggle
- include/exclusion detection regions
- candidate quality gate before tracking
- camera wizard controls for profile, compute tier, speed metrics, and regions
- scene configuration guide

Relevant docs:

- `docs/superpowers/specs/2026-05-09-live-signal-terrain-and-stability-design.md`
- `docs/superpowers/plans/2026-05-09-live-signal-terrain-and-stability-implementation-plan.md`
- `docs/superpowers/specs/2026-05-10-scene-vision-profiles-and-candidate-quality-design.md`
- `docs/superpowers/plans/2026-05-10-scene-vision-profiles-and-candidate-quality-implementation-plan.md`
- `docs/scene-vision-profile-configuration-guide.md`

### Model Runtime And Open Vocab

Track A and Track B from the Jetson optimized runtime plan are implemented.

Implemented:

- runtime artifact enums, table, API contracts, service, and routes
- model-scoped fixed-vocab runtime artifacts
- scene-scoped open-vocab artifacts keyed by camera and vocabulary hash
- worker runtime artifact candidates
- runtime artifact selector
- Ultralytics `.engine` detector wrapper
- worker integration for optimized runtime selection
- CLI scripts for registering/validating artifacts
- YOLOE scene artifact build/register path
- open-vocab fallback to dynamic `.pt` when vocabulary changes
- UI runtime artifact status in Operations/camera setup
- hardened artifact validation
- model loading/configuration guide

Important posture:

- ONNX model rows remain canonical camera choices for fixed-vocab production.
- Raw TensorRT `.engine` files are target-specific runtime artifacts, not
  primary camera models.
- Dynamic `.pt` open vocab remains the discovery/live vocabulary-change path.
- Compiled scene artifacts are for saved stable scene vocabularies.
- Track C / DeepStream is still not implemented.

Relevant docs:

- `docs/superpowers/specs/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-design.md`
- `docs/superpowers/plans/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-implementation-plan.md`
- `docs/model-loading-and-configuration-guide.md`
- `docs/runbook.md`
- `docs/imac-master-orin-lab-test-guide.md`

### Product Direction Locked For Next Stage

The next direction is to make Vezor more distinct as sovereign, auditable scene
intelligence.

Build the first three differentiators first:

1. Scene Contract Compiler
2. Evidence Ledger
3. Privacy Manifest Per Scene

The plan also includes short incident recording and edge USB/UVC camera source
support.

Use this spec:

```text
docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md
```

Use this plan:

```text
docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md
```

## Next Implementation Step

Start with:

```text
Task 1: Data Contract And Migration
```

Task 1 covers:

- camera source enums/contracts
- evidence recording policy contract
- scene contract snapshot table
- privacy manifest snapshot table
- evidence artifact table
- evidence ledger table
- incident columns for contract/manifest/recording policy
- camera columns for source and recording policy
- migration `0011_accountable_scene_evidence`

Expected focused verification for Task 1:

```bash
cd "$HOME/vision/backend"
python3 -m uv run pytest \
  tests/services/test_scene_contracts.py \
  tests/services/test_evidence_ledger.py \
  tests/core/test_db.py \
  -q
```

After Task 1, continue the plan one task at a time. Task 4 is the edge USB/UVC
source implementation; it is part of this plan and should remain edge-first.

## Pending Follow-Up Queue

Do not lose these across chats. They remain important even though the immediate
next work is the Accountable Scene Intelligence foundation.

### Evidence Desk Timeline And Case Context Polish

This is still pending and not obsolete:

```text
docs/superpowers/plans/2026-05-09-evidence-desk-timeline-and-case-context-implementation-plan.md
```

Original scope:

- Evidence Timeline density strip
- Case Context Strip
- type-colored review queue
- cleaner raw payload disclosure

Current status:

- not executed yet
- superseded as the immediate next plan
- should be retuned after Accountable Scene Intelligence Tasks 1-9, because the
  Evidence Desk should first surface scene contracts, privacy manifests,
  evidence artifact status, and ledger summary
- after Task 9 lands, either adapt the old Evidence Desk polish plan into a new
  follow-up plan or explicitly fold its useful pieces into the accountable
  Evidence Desk UI before closing the evidence surface

### Later Product Differentiators

After the accountable evidence foundation and retuned Evidence Desk polish,
decide whether to implement:

- Runtime Passport
- Operational Memory
- Prompt-To-Policy
- Identity-Light Cross-Camera Intelligence

These should reuse the scene contract, privacy manifest, evidence artifact, and
ledger primitives from the current plan.

### Later Runtime Lane

Track C / DeepStream remains deferred until Track A/B runtime artifacts have
passed real Jetson soak validation.

## Working Rules For The Next Chat

- Continue from `codex/omnisight-ui-spec-implementation`.
- Pull latest branch state first.
- Execute one task at a time.
- Use sub-agents where useful for independent implementation/review slices.
- Commit after each completed task.
- Push to origin after commits so the user can test.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Implement Accountable Scene Intelligence plan Tasks 1-12 in order unless the
  user redirects.
- Keep the pending Evidence Desk polish queue visible; do not drop it from
  future handoffs.
- Do not implement Runtime Passport, Operational Memory, Prompt-To-Policy, or
  Identity-Light cross-camera intelligence until this foundation and the retuned
  Evidence Desk polish are complete or the user explicitly redirects.
- Do not implement Track C / DeepStream yet.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- Treat USB camera support as edge-first production support for Linux/Jetson
  UVC devices exposed as `/dev/video*`.
- When edge mode is used and recording is enabled, incident clips should be
  reviewable through local edge storage or central/cloud artifact storage.

## Known Verification Notes

The focused Track A/B verification previously passed:

```text
106 backend focused runtime tests passed
frontend vitest/build/lint passed, with existing lint warnings only
```

Known unrelated backend checks from the previous verification sweep:

- full backend Ruff had a pre-existing `F841` in
  `backend/tests/services/test_camera_service.py:518`
- full backend mypy had pre-existing errors around
  `src/argus/inference/engine.py` and `src/argus/services/app.py`

Do not fix unrelated lint/type debt unless it blocks the current task.

## Prompt For The Next Chat

Use this prompt:

```text
We are continuing Vezor/OmniSight work from branch codex/omnisight-ui-spec-implementation.

Read the handoff first:
docs/superpowers/status/2026-05-11-next-chat-accountable-scene-intelligence-handoff.md

Goal for this chat:
Start the Accountable Scene Intelligence And Evidence Recording implementation.

Use the spec:
docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md

Use the plan:
docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md

Start with:
Task 1: Data Contract And Migration

Working rules:
- Pull latest first:
  git fetch origin
  git switch codex/omnisight-ui-spec-implementation
  git pull --ff-only origin codex/omnisight-ui-spec-implementation
- Execute one task at a time.
- Use sub-agents where useful.
- Commit after each completed task.
- Push to origin after commits so I can test.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Implement the Accountable Scene Intelligence plan in order.
- Treat edge USB/UVC camera source support as production edge-first.
- Make incident clips reviewable in edge mode when recording is enabled.
- Support local edge storage and remote/cloud S3-compatible storage options.
- Do not implement Runtime Passport, Operational Memory, Prompt-To-Policy, or Identity-Light cross-camera intelligence yet.
- Do not implement Track C / DeepStream yet.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- If dev DB errors mention cameras.vision_profile, cameras.detection_regions, or model_runtime_artifacts, run alembic upgrade head.
```
