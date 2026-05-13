# Next Chat Handoff: Accountable Scene Intelligence Task 17

> Superseded by:
> `docs/superpowers/status/2026-05-13-next-chat-installable-supervisor-productization-handoff.md`.
> This May 12 handoff is retained as historical context for the earlier Task 17
> continuation point.

Date: 2026-05-12

Purpose: paste this document into a fresh chat to continue from the current
`codex/omnisight-ui-spec-implementation` branch. The accountable scene,
evidence, UI-managed configuration, runtime passport, and per-worker incident
rule runway is complete through Task 16E. The next task is Task 17.

## Repository State

Continue from the pushed branch:

```text
codex/omnisight-ui-spec-implementation
```

Latest implementation checkpoint before this documentation refresh:

```text
b3b651bd feat(evidence): show incident rule provenance
```

Recent checkpoints:

```text
b3b651bd feat(evidence): show incident rule provenance
a12b33a0 feat(ui): add scene incident rule builder
e561148c feat(worker): consume per-scene incident rules
a217f955 feat(rules): add per-scene incident rule API
6f29b0ac docs(rules): plan per-worker incident rules
931284d6 feat(ui): surface runtime passports
46b9c8be feat(runtime): add incident runtime passports
2c51853e feat(evidence): support optional snapshot artifacts
2d2c517c docs(handoff): refresh accountable scene task 14 handoff
6f8360eb fix(db): shorten evidence expiry migration revision
55fe0993 feat(llm): consume provider configuration profiles
8032ddf2 feat(privacy): consume privacy policy profiles
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

If the backend only reaches Postgres inside the Docker dev network, run the
container's installed Alembic entrypoint instead of `python -m uv`:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml exec backend \
  alembic upgrade head
```

Current Alembic head:

```text
0018_incident_rule_ledger
```

## What Is Implemented Through Task 16E

Implemented and pushed:

- Band 1, Tasks 1-3: accountable data foundation, scene contracts, privacy
  manifests, evidence artifacts, ledger primitives, and deterministic hashes
- Band 2, Tasks 4-8: edge USB/UVC sources, local/remote storage, artifact-aware
  clip capture, evidence ledger writes, and artifact content routes
- Band 3, Tasks 9-13: accountability strip, Evidence Desk context, camera
  source/recording controls, docs, validation sweep, timeline and case context
  polish
- Tasks 13A-13C: UI-managed configuration profile data model, API,
  validation/resolution service, and Settings workspace
- Tasks 13D-13J: runtime consumption for recording storage, local-first sync,
  effective diagnostics, stream delivery, runtime selection, privacy policy, and
  LLM provider profiles
- Task 14: optional still snapshot evidence artifacts
- Tasks 15-16: runtime passport snapshots, incident attachment, incident API,
  and Operations/Evidence surfacing
- Task 16A: camera-scoped incident rule data contract, service, validation,
  audit, API, and migration `0017_detection_rule_incident_metadata`
- Task 16B: worker config, camera command, scene contract, rule engine,
  persisted rule event, and rule-generated incident runtime consumption
- Task 16C: Control -> Scenes incident rule builder and generated API hooks
- Task 16D: Evidence trigger rule summary, `incident_rule.attached` ledger
  action, incident API trigger rule contract, and Operations rule runtime truth
- Task 16E: operator docs, plan/spec/handoff refresh, and full per-worker
  incident rule band validation

## Task 16E Validation

Fresh validation before this handoff refresh:

```text
alembic upgrade head: passed
backend targeted band suite: 140 passed, 46 warnings
backend Ruff: passed
frontend generate:api: passed
frontend targeted Vitest: 6 files passed, 26 tests passed
frontend TypeScript: passed
git diff --check: passed
alembic heads: 0018_incident_rule_ledger (head)
```

The frontend Vitest warnings were React Router v7 future-flag warnings only.
The backend warnings were the known missing `/run/secrets` warnings from local
test settings.

## Current Product Posture

Operator-facing configuration is UI/API managed after bootstrap:

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

Per-worker incident rules are now first-class scene policy:

- define rules from Control -> Scenes
- validate predicates against scene classes, vocabulary, zones, confidence, and
  supported non-biometric attributes
- use `record_clip` as the default rule action for reviewable incidents
- let the camera recording policy and storage profile decide clip/snapshot
  artifacts and local, edge-local, central, cloud, or local-first storage
- confirm worker rule consumption in Control -> Operations by active count,
  effective hash, latest rule event, and load status
- review trigger rule name, type, severity, action, cooldown, rule hash, scene
  contract hash, and detection context in Intelligence -> Evidence
- keep Prompt-To-Policy as a future draft producer only; prompt workflows must
  not auto-apply production incident rules

Incident clips remain reviewable in edge/local-first mode when recording is
enabled. Local-first artifacts are not promoted to remote-available until upload
is confirmed.

## Next Implementation Step

Start with:

```text
Band 6: Product Differentiators
Task 17: Operational Memory
```

Use this spec:

```text
docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md
```

Use this plan:

```text
docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md
```

Task 17 scope:

- create `backend/src/argus/migrations/versions/0019_operational_memory_patterns.py`
- add `operational_memory_patterns`
- detect repeated event bursts by site/camera/zone/class/time window
- detect repeated clip/storage failures by provider and edge node
- detect zone hot spots after scene contract changes
- cite source incident ids and contract hashes in every pattern
- expose current patterns through Operations and selected incident context
- show observed pattern cards in Evidence Desk and Operations without
  predictive language

Expected focused verification for Task 17:

```bash
cd "$HOME/vision/backend"
python3 -m uv run pytest tests/services/test_operational_memory.py tests/api/test_operations_endpoints.py -q

cd "$HOME/vision"
corepack pnpm --dir frontend generate:api
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/OperationalMemoryPanel.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Settings.test.tsx
```

## Guardrails To Carry Forward

- Execute one task at a time.
- Commit and push after each completed task.
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
  `worker_assignments`, `detection_rules`, `rule_events`,
  `operational_memory_patterns`, or any new plan table, run
  `alembic upgrade head`.

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
Band 6: Product Differentiators
Task 17: Operational Memory

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
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Treat edge USB/UVC camera source support as production edge-first.
- Make incident clips reviewable in edge mode when recording is enabled.
- Support local edge storage and remote/cloud S3-compatible storage options.
- Do not start Track C / DeepStream before Task 23 records passing Track A/B Jetson soak evidence unless I explicitly accept the risk.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- If dev DB errors mention cameras.vision_profile, cameras.detection_regions, model_runtime_artifacts, scene_contract_snapshots, runtime_passport_snapshots, worker_assignments, detection_rules, rule_events, operational_memory_patterns, or any new plan table, run alembic upgrade head.
```
