# Next Chat Handoff: Accountable Scene Intelligence Task 14

Date: 2026-05-12

Purpose: paste this document into a fresh chat to continue from the current
`codex/omnisight-ui-spec-implementation` branch. The accountable scene,
evidence, UI-managed configuration, and runtime-consumption runway is complete
through Task 13J. The next task is Task 14.

## Repository State

Continue from the pushed branch:

```text
codex/omnisight-ui-spec-implementation
```

Latest implementation checkpoint before this documentation refresh:

```text
6f8360eb fix(db): shorten evidence expiry migration revision
```

Recent checkpoints:

```text
6f8360eb fix(db): shorten evidence expiry migration revision
55fe0993 feat(llm): consume provider configuration profiles
8032ddf2 feat(privacy): consume privacy policy profiles
93e730f0 feat(runtime): consume runtime selection profiles
2fbeed2a feat(streams): route browser delivery profiles
33e22bae feat(config): show effective runtime configuration
473603e1 feat(evidence): sync local-first artifacts
2dc2e401 fix(db): shorten operator configuration migration id
9f1c1611 feat(evidence): route recording storage profiles
c83f2d9f feat(config): add configuration workspace
bf35d20e feat(config): expose UI-managed configuration API
280343e9 feat(config): add operator configuration profiles
cb2ae3f6 feat(evidence): add accountable timeline and case context
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
- keep WebGL off

## Required Dev DB Migration

After pulling this checkpoint, migrate the dev database:

```bash
cd "$HOME/vision/backend"
python3 -m uv run alembic upgrade head
```

If the backend only reaches Postgres inside the Docker dev network, run:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
```

Current Alembic head:

```text
0014_evidence_expiry_action
```

Note: the migration file is
`backend/src/argus/migrations/versions/0014_evidence_expiry_ledger_action.py`,
but its revision id is intentionally shortened to fit
`alembic_version.version_num varchar(32)`.

## What Is Implemented Through Task 13J

Implemented and pushed:

- Band 1, Tasks 1-3: accountable data foundation, scene contracts, privacy
  manifests, evidence artifacts, ledger primitives, and deterministic hashes
- Band 2, Tasks 4-8: edge USB/UVC sources, local/remote storage, artifact-aware
  clip capture, evidence ledger writes, and artifact content routes
- Band 3, Tasks 9-13: accountability strip, Evidence Desk context, camera
  source/recording controls, docs, validation sweep, timeline and case context
  polish
- Task 13A: operator configuration data model, encrypted secrets, and contracts
- Task 13B: configuration service, API, validation, resolution, and bootstrap
  defaults
- Task 13C: Settings configuration workspace UI
- Task 13D: runtime recording storage profile routing
- Task 13E: local-first evidence upload sync
- Task 13F: effective configuration runtime diagnostics
- Task 13G: stream delivery and browser playback runtime routing
- Task 13H: runtime-selection profile consumption
- Task 13I: privacy-policy runtime consumption, retention expiry marker, and
  evidence expiry ledger action
- Task 13J: LLM-provider runtime consumption with service-only secret access

Fresh validation before stopping after Task 13:

```text
Backend focused Task 13 suite: 134 passed, 3 skipped
Backend Ruff: passed
Frontend TypeScript: passed
Frontend configuration/camera/settings Vitest: 35 passed
git diff --check: passed
```

Migration fix validation:

```text
backend/tests/core/test_db.py: 13 passed
alembic heads: 0014_evidence_expiry_action (head)
offline alembic SQL from 0013 to head updates version_num to 0014_evidence_expiry_action
```

## Current Product Posture

Operator-facing configuration is now UI/API managed after bootstrap:

- evidence storage
- stream delivery
- runtime selection
- privacy policy
- LLM provider
- operations mode, with runtime consumption intentionally deferred to Tasks
  20-22

Storage options are wired beyond UI metadata:

- local filesystem
- edge-local
- central MinIO/S3-compatible
- cloud S3-compatible
- local-first local review plus remote sync

Incident clips remain reviewable in edge/local-first mode when recording is
enabled. Local-first artifacts are not promoted to remote-available until upload
is confirmed.

## Next Implementation Step

Start with:

```text
Task 14: Optional Still Snapshot Evidence Artifacts
```

Use this spec:

```text
docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md
```

Use this plan:

```text
docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md
```

Task 14 scope:

- add optional snapshot fields to `EvidenceRecordingPolicy`
- create `snapshot` evidence artifacts only when snapshot capture is enabled
- keep `incidents.snapshot_url` nullable when disabled or unavailable
- write snapshot artifact ledger entries
- ensure snapshot quota or encode failures do not break clip capture
- show snapshot availability in Evidence Desk as optional evidence, not as a
  missing-data error when disabled

Expected focused verification for Task 14:

```bash
cd "$HOME/vision/backend"
python3 -m uv run pytest \
  tests/services/test_incident_capture.py \
  tests/services/test_evidence_storage.py \
  -q

cd "$HOME/vision"
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

After Task 14, commit and push, then pause for validation before Band 5
Tasks 15-16.

## Guardrails To Carry Forward

- Execute one task at a time.
- Commit and push after each completed task.
- Pause and report after Task 14 before starting Task 15.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Treat edge USB/UVC camera source support as production edge-first.
- Make incident clips reviewable in edge mode when recording is enabled.
- Support local edge storage and remote/cloud S3-compatible storage options.
- Do not start Track C / DeepStream before Task 23 records passing Track A/B
  Jetson soak evidence unless the user explicitly accepts the risk.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- If dev DB errors mention `cameras.vision_profile`,
  `cameras.detection_regions`, `model_runtime_artifacts`,
  `scene_contract_snapshots`, `runtime_passport_snapshots`,
  `worker_assignments`, or any new plan table, run `alembic upgrade head`.

## Suggested Next Prompt

```text
We are continuing Vezor/OmniSight work from branch codex/omnisight-ui-spec-implementation.

Read the handoff first:
docs/superpowers/status/2026-05-12-next-chat-accountable-scene-task14-handoff.md

Use the spec:
docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md

Use the plan:
docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md

Start with:
Band 4: Evidence Media Completion
Task 14: Optional Still Snapshot Evidence Artifacts

Working rules:
- Pull latest first:
  git fetch origin
  git switch codex/omnisight-ui-spec-implementation
  git pull --ff-only origin codex/omnisight-ui-spec-implementation
- Run alembic upgrade head before backend validation.
- Execute one task at a time.
- Use sub-agents where useful.
- Commit after the completed task.
- Push to origin after the commit so I can test.
- Pause and report after Task 14 before starting Task 15.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Treat edge USB/UVC camera source support as production edge-first.
- Make incident clips reviewable in edge mode when recording is enabled.
- Support local edge storage and remote/cloud S3-compatible storage options.
- Do not start Track C / DeepStream before Task 23 records passing Track A/B Jetson soak evidence unless I explicitly accept the risk.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- If dev DB errors mention cameras.vision_profile, cameras.detection_regions, model_runtime_artifacts, scene_contract_snapshots, runtime_passport_snapshots, worker_assignments, or any new plan table, run alembic upgrade head.
```
