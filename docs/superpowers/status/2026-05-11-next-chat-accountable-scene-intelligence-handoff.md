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

Latest pushed checkpoint before this validation-band update:

```text
f045e01f docs(plan): unify accountable runtime runway
```

Recent checkpoints on this branch:

```text
f045e01f docs(plan): unify accountable runtime runway
c316d4db docs(handoff): carry forward production hardening
22730157 docs(handoff): carry forward evidence desk polish
5fadfae7 docs(handoff): refresh accountable scene next steps
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
`0010_model_runtime_artifacts`. The unified plan starts with
`0011_accountable_scene_evidence` and later adds runtime passport, operational
memory, policy draft, cross-camera, supervisor operations, and runtime soak
tables.

If the dev UI shows 500s with either of these errors:

```text
column cameras.vision_profile does not exist
column cameras.detection_regions does not exist
relation model_runtime_artifacts does not exist
relation scene_contract_snapshots does not exist
relation runtime_passport_snapshots does not exist
relation worker_assignments does not exist
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
- The code supports registered TensorRT `.engine` artifacts, but production
  artifacts still need to be built, registered, validated, and soaked on the
  target Jetson for the chosen fixed-vocab model, for example YOLO26n.
- Dynamic `.pt` open vocab remains the discovery/live vocabulary-change path.
- Compiled scene artifacts are for saved stable scene vocabularies.
- Compiled YOLOE S/open-vocab scene artifacts are supported by the build and
  selection path, but each stable scene vocabulary still needs its own
  target-specific artifact build, registration, validation, and soak.
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

The plan now includes every still-pertinent handoff item as an ordered
implementation runway:

- Tasks 1-12: accountable scene/evidence foundation
- Task 13: Evidence Desk Timeline And Case Context polish, retuned around
  accountable evidence
- Task 14: optional still snapshot evidence artifacts
- Tasks 15-16: Runtime Passport
- Task 17: Operational Memory
- Task 18: Prompt-To-Policy
- Task 19: Identity-Light Cross-Camera Intelligence
- Tasks 20-22: Fleet/Operations production hardening, supervisor lifecycle,
  assignment, per-worker runtime truth, and edge credential rotation
- Task 23: production Linux master plus Jetson runtime artifact soak validation
- Task 24: Track C / DeepStream, gated behind Task 23 soak evidence
- Task 25: full runway verification and handoff refresh

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

After Task 1, continue the plan one task at a time through Task 25. Task 4 is
the edge USB/UVC source implementation and should remain edge-first. Task 24 is
DeepStream and remains gated until Task 23 records real Track A/B runtime
artifact soak evidence, or until the user explicitly accepts implementing it
before that evidence exists.

## Integrated Former Follow-Up Queue

Do not recreate a separate follow-up queue for these items. They are now
included directly in the latest plan:

- Evidence Desk Timeline And Case Context polish: Task 13
- incident still snapshot evidence artifacts: Task 14
- Runtime Passport: Tasks 15-16
- Operational Memory: Task 17
- Prompt-To-Policy: Task 18
- Identity-Light Cross-Camera Intelligence: Task 19
- supervisor-backed Start/Stop/Restart/Drain, per-worker runtime truth,
  persistent assignment/reassignment, and edge credential rotation: Tasks 20-22
- production Linux master plus Jetson runtime artifact soak validation: Task 23
- Track C / DeepStream: Task 24, gated by Task 23

## Validation Bands

Execute one task at a time with task-level tests, commit, and push. Pause at
these band gates so the user can validate the product shape along the way:

1. **Band 1: Accountable Data Foundation** — Tasks 1-3
   - validate migrations, camera source/recording contracts, privacy manifest
     hashes, scene contract hashes, and snapshot dedupe
2. **Band 2: Capture, Storage, Ledger, API** — Tasks 4-8
   - validate USB/UVC worker config, local edge storage, MinIO/S3-compatible
     storage, clip artifacts, ledger entries, and artifact content routes
3. **Band 3: Operator-Facing Evidence Foundation** — Tasks 9-13
   - validate Evidence Desk accountability, Camera Wizard recording/source
     controls, docs, focused sweep, timeline, and case context polish
4. **Band 4: Evidence Media Completion** — Task 14
   - validate optional still snapshots as first-class evidence without making
     `snapshot_url` mandatory
5. **Band 5: Runtime Passport** — Tasks 15-16
   - validate runtime passport snapshots, incident attribution, Operations
     visibility, TensorRT/open-vocab/fallback cases
6. **Band 6: Product Differentiators** — Tasks 17-19
   - validate Operational Memory, Prompt-To-Policy, and Identity-Light
     Cross-Camera Intelligence one task at a time with product-direction review
7. **Band 7: Edge-First Production Operations** — Tasks 20-22
   - validate persistent assignments, supervisor runtime truth, lifecycle
     requests, Operations controls, and edge credential rotation
8. **Band 8: Real Jetson Runtime Validation** — Task 23
   - validate Linux master plus Jetson soak for YOLO26n TensorRT and YOLOE
     S/open-vocab scene artifacts, including restart, rollback, evidence review,
     Operations truth, and credential rotation
9. **Band 9: DeepStream Gate** — Task 24
   - start only after Band 8 passes, unless the user explicitly accepts the risk
10. **Band 10: Final Hardening** — Task 25
    - validate full focused suites, build/lint/type checks, docs, and handoff

## Working Rules For The Next Chat

- Continue from `codex/omnisight-ui-spec-implementation`.
- Pull latest branch state first.
- Execute one task at a time.
- Use the validation bands above. Commit and push after every task, and pause
  for a band report after each band gate.
- Use sub-agents where useful for independent implementation/review slices.
- Commit after each completed task.
- Push to origin after commits so the user can test.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Implement the unified plan Tasks 1-25 in order unless the user redirects.
- Do not split former follow-up items back out of the plan; they now have task
  numbers in the unified runway.
- Runtime Passport, Operational Memory, Prompt-To-Policy, Identity-Light
  cross-camera intelligence, Fleet/Ops hardening, and runtime soak are part of
  this plan after the accountable evidence foundation.
- Do not start Track C / DeepStream before Task 23 records passing Track A/B
  Jetson soak evidence unless the user explicitly accepts the risk.
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
Start the unified Accountable Scene Intelligence, Evidence Recording, Runtime,
Operations, and Differentiator implementation runway.

Use the spec:
docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md

Use the plan:
docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md

Start with:
Band 1: Accountable Data Foundation
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
- Pause and report after each validation band:
  Band 1 Tasks 1-3, Band 2 Tasks 4-8, Band 3 Tasks 9-13, Band 4 Task 14,
  Band 5 Tasks 15-16, Band 6 Tasks 17-19, Band 7 Tasks 20-22, Band 8 Task 23,
  Band 9 Task 24, Band 10 Task 25.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Implement the unified plan Tasks 1-25 in order.
- Treat edge USB/UVC camera source support as production edge-first.
- Make incident clips reviewable in edge mode when recording is enabled.
- Support local edge storage and remote/cloud S3-compatible storage options.
- Evidence Desk polish, evidence snapshot artifacts, Runtime Passport,
  Operational Memory, Prompt-To-Policy, Identity-Light cross-camera
  intelligence, Fleet/Ops production hardening, credential rotation, and Jetson
  runtime soak validation are now tasks inside the plan; do not drop them from
  future handoffs.
- Do not start Track C / DeepStream before Task 23 records passing Track A/B Jetson soak evidence unless I explicitly accept the risk.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- If dev DB errors mention cameras.vision_profile, cameras.detection_regions, model_runtime_artifacts, scene_contract_snapshots, runtime_passport_snapshots, worker_assignments, or any new plan table, run alembic upgrade head.
```
