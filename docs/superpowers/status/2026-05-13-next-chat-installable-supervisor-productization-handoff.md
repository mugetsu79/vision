# Next Chat Handoff: Installable Supervisor Productization

Date: 2026-05-13

Purpose: paste this document into a fresh chat to continue from the current
`codex/omnisight-ui-spec-implementation` branch. The accountable scene,
Evidence, UI-managed configuration, runtime passport, per-worker incident rule,
Operational Memory, Prompt-To-Policy, Identity-Light, supervisor operations,
hardware admission, runnable supervisor, and installable-supervisor planning
runway is complete through Task 21C plus the Band 7.5 plan. The next
implementation task is Task 21D.

## Repository State

Continue from the pushed branch:

```text
codex/omnisight-ui-spec-implementation
```

The development branch should also have been merged into `main` during the
handoff wrap-up, but do not continue implementation from `main`. Continue from
`codex/omnisight-ui-spec-implementation`.

Latest planning checkpoint before this handoff refresh:

```text
aa59b64a docs(plan): add installable supervisor productization band
```

Recent checkpoints:

```text
aa59b64a docs(plan): add installable supervisor productization band
986e07bc fix(live): refresh fleet worker status
189f260c fix(operations): allow first supervised start
c93e3415 fix(operations): refresh supervisor controls
5a3162fd fix(operations): scope central hardware to central workers
649e8023 feat(operations): add runnable supervisor reporter
443483b6 docs(plan): add runnable supervisor reporter task
379d7e11 feat(operations): add supervisor reconciler admission
df347781 docs(operations): plan supervisor hardware admission
cf087c5d fix(inference): avoid duplicate capture wait percentiles
4d39d29c feat(operations): add supervisor lifecycle controls
64291019 feat(operations): add supervisor runtime contract
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

After pulling this checkpoint, migrate the dev database before backend
validation:

```bash
cd "$HOME/vision/backend"
python3 -m uv run alembic upgrade head
```

If the backend only reaches Postgres inside the Docker dev network, run the
container's installed Alembic entrypoint instead:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml exec backend \
  alembic upgrade head
```

Current Alembic head before Task 21D:

```text
0023_supervisor_reconciler
```

Task 21D will add the next migration:

```text
0024_installable_supervisor_productization
```

## What Is Implemented Through Task 21C

Implemented and pushed:

- Tasks 1-13J: accountable evidence foundation, Evidence Desk polish,
  UI-managed configuration profiles, and runtime consumption for storage,
  stream delivery, runtime selection, privacy policy, and LLM provider profiles
- Task 14: optional still snapshot evidence artifacts
- Tasks 15-16: runtime passport snapshots and incident surfacing
- Tasks 16A-16E: per-worker incident rule contract, API, worker consumption,
  Control -> Scenes builder, Evidence/Operations provenance, and docs
- Tasks 17-19: Operational Memory, Prompt-To-Policy, and Identity-Light
  Cross-Camera Intelligence
- Tasks 20-21B: supervisor operations data contract, Operations lifecycle and
  assignment UI, supervisor reconciler contract, hardware admission, and model
  recommendations
- Task 21C: runnable iMac/Jetson supervisor hardware reporter, metrics scraper,
  operations client, bounded child-process adapter, edge Compose profile, token
  refresh support, first supervised start, fresh Operations controls, scoped
  central hardware reporting, and Live fleet status refresh

Important user validation from the iMac:

- supervisor-managed Start works from Control -> Operations
- Live can show video and telemetry while the worker is running
- Live worker status needed the pushed fleet refetch fix
- the user does not want a manual `supervisor.runner` terminal workflow as the
  final product path

## New Productization Decision

The next product step is not Task 22 yet. Before credential rotation, implement
the new installable/no-console band:

```text
Band 7.5: Installable Supervisor And First-Run Productization
Tasks: 21D-21H, then Task 22
```

Design spec:

```text
docs/superpowers/specs/2026-05-13-installable-supervisor-and-first-run-productization-design.md
```

Master spec:

```text
docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md
```

Implementation plan:

```text
docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md
```

The final-product deployment target is:

- install once on macOS or Linux
- pair nodes from the UI with short-lived one-time material
- store node credentials through a platform credential boundary
- run the supervisor as systemd, launchd, or production Compose service
- manage workers through Control -> Deployment and Control -> Operations
- use terminal commands only for installer/bootstrap, local development,
  smoke-test, and break-glass support

## Next Implementation Step

Start with:

```text
Band 7.5: Installable Supervisor And First-Run Productization
Task 21D: Deployment Node And Service Status Contract
```

Task 21D scope:

- add deployment-node install state separate from worker runtime state
- add supervisor service status reports
- add pairing-session, node-credential, and credential-event tables for later
  Task 21F and Task 22
- add `DeploymentNodeService`
- add `/api/v1/deployment` routes
- register the deployment router from `argus.main`
- keep plaintext pairing codes and credential material out of persisted tables

Task 21D files from the plan:

- `backend/src/argus/models/enums.py`
- `backend/src/argus/models/tables.py`
- `backend/src/argus/migrations/versions/0024_installable_supervisor_productization.py`
- `backend/src/argus/api/contracts.py`
- `backend/src/argus/services/deployment_nodes.py`
- `backend/src/argus/services/app.py`
- `backend/src/argus/api/v1/deployment.py`
- `backend/src/argus/main.py`
- `backend/tests/services/test_deployment_nodes.py`
- `backend/tests/api/test_deployment_routes.py`
- `backend/tests/core/test_db.py`

Expected focused verification for Task 21D:

```bash
cd "$HOME/vision/backend"
python3 -m uv run alembic upgrade head
python3 -m uv run pytest tests/services/test_deployment_nodes.py tests/api/test_deployment_routes.py tests/core/test_db.py -q
python3 -m uv run ruff check src/argus/services/deployment_nodes.py src/argus/api/v1/deployment.py tests/services/test_deployment_nodes.py tests/api/test_deployment_routes.py
```

Commit after Task 21D:

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0024_installable_supervisor_productization.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/services/deployment_nodes.py \
  backend/src/argus/services/app.py \
  backend/src/argus/api/v1/deployment.py \
  backend/src/argus/main.py \
  backend/tests/services/test_deployment_nodes.py \
  backend/tests/api/test_deployment_routes.py \
  backend/tests/core/test_db.py
git commit -m "feat(deployment): add supervisor install state"
git push origin codex/omnisight-ui-spec-implementation
```

## Guardrails To Carry Forward

- Execute one task at a time.
- Use subagents where useful.
- Commit and push after each completed task.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Keep the backend/browser as a control plane, not a remote shell.
- Final product operation must not depend on copied bearer tokens or foreground
  terminal supervisor processes after installation.
- Treat edge USB/UVC camera source support as production edge-first.
- Make incident clips reviewable in edge mode when recording is enabled.
- Support local edge storage and remote/cloud S3-compatible storage options.
- Do not start Task 22 until Tasks 21D-21H establish the installable node
  credential/pairing model.
- Do not start Track C / DeepStream before Task 23 records passing Track A/B
  Jetson soak evidence unless the user explicitly accepts the risk.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- If dev DB errors mention `cameras.vision_profile`,
  `cameras.detection_regions`, `model_runtime_artifacts`,
  `scene_contract_snapshots`, `runtime_passport_snapshots`,
  `worker_assignments`, `detection_rules`, `rule_events`,
  `operational_memory_patterns`, `policy_drafts`, `cross_camera_threads`,
  `edge_node_hardware_reports`, `worker_model_admission_reports`,
  `deployment_nodes`, or any new plan table, run `alembic upgrade head`.

## Suggested Next Prompt

```text
We are continuing Vezor/OmniSight work from branch codex/omnisight-ui-spec-implementation.

Read the handoff first:
docs/superpowers/status/2026-05-13-next-chat-installable-supervisor-productization-handoff.md

Use the installable supervisor spec:
docs/superpowers/specs/2026-05-13-installable-supervisor-and-first-run-productization-design.md

Use the master spec:
docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md

Use the plan:
docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md

Start with:
Band 7.5: Installable Supervisor And First-Run Productization
Task 21D: Deployment Node And Service Status Contract

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
- Keep the backend/browser as a control plane, not a remote shell.
- Final product operation must not depend on copied bearer tokens or foreground terminal supervisor processes after installation.
- Treat edge USB/UVC camera source support as production edge-first.
- Make incident clips reviewable in edge mode when recording is enabled.
- Support local edge storage and remote/cloud S3-compatible storage options.
- Do not start Task 22 until Tasks 21D-21H establish the installable node credential/pairing model.
- Do not start Track C / DeepStream before Task 23 records passing Track A/B Jetson soak evidence unless I explicitly accept the risk.
- Do not reopen RTSP/TensorRT debugging unless fresh logs prove it is needed.
- If dev DB errors mention cameras.vision_profile, cameras.detection_regions, model_runtime_artifacts, scene_contract_snapshots, runtime_passport_snapshots, worker_assignments, detection_rules, rule_events, operational_memory_patterns, policy_drafts, cross_camera_threads, edge_node_hardware_reports, worker_model_admission_reports, deployment_nodes, or any new plan table, run alembic upgrade head.
```
