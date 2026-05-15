# Product Installer And No-Console First Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Current Status As Of 2026-05-15

This band has been implemented on branch `codex/omnisight-installer` as the
installer-managed validation path. The checkbox steps below remain as the
original execution plan, but the active continuation state is now captured in:

```text
docs/superpowers/status/2026-05-15-next-chat-omnisight-installer-portable-demo-handoff.md
```

Latest pushed checkpoint at this status update:

```text
8c37f50e Wire installed edge NATS leaf
```

Implemented since this plan was written:

- macOS master installer and launchd appliance wrapper
- Linux master installer and systemd appliance wrapper
- Jetson edge installer and systemd appliance wrapper
- `vezor-master`, `vezor-edge`, and `vezorctl` package wrappers
- product master and edge Compose profiles
- first-run bootstrap UI/API
- central and Jetson pairing flows
- raw supervisor credential storage and redacted support bundles
- Deployment unpair action and Sites delete action
- model registration and runtime artifact validation guide paths
- local installed Jetson NATS leaf service for worker event publication

Current validation checkpoint:

```bash
make verify-installers
```

passed with installer tests, shell syntax, manifest validation, product secret
scan, and master/edge Compose rendering.

Remaining hardware validation:

- rerun the Jetson edge installer after `8c37f50e`
- confirm `vezor-edge-nats-leaf` runs and no worker logs point at
  `127.0.0.1:4222`
- confirm Jetson-owned camera Live video and telemetry
- create/review one evidence clip
- run reboot/restart validation
- record Track A/B Jetson soak evidence before opening Task 24 / DeepStream

**Goal:** Replace Docker development commands and foreground supervisor terminals with product installers and UI-managed first-run/lifecycle operation for macOS master, Linux master, and Jetson edge nodes.

**Architecture:** Build an OS-service-owned appliance layer around the existing Deployment, pairing, credential, supervisor, Operations, and runtime contracts. Installers run locally on each host and own privileged setup; the Vezor UI remains a control plane for first-run setup, pairing, health, lifecycle, diagnostics, and credentials.

**Tech Stack:** Python 3.12, FastAPI, Alembic, React, TanStack Query, systemd, launchd, Docker/Podman Compose compatible appliance profiles, shell installers with dry-run validation, Playwright/Vitest/Pytest.

---

## Scope Check

This plan implements the packaging and first-run layer only. It does not add
DeepStream, Kubernetes, cloud update channels, or a native signed macOS GUI
application. It may use containers under the hood, but no normal operator flow
requires `make dev-up`, manual `docker compose up`, copied bearer tokens, or a
foreground `argus.supervisor.runner` terminal after installation.

Insert this band before Task 24. If real hardware soak evidence has not been
recorded yet, run that evidence on the installer-managed topology.

## File Structure

Create a focused installer package tree:

- `installer/vezor_installer/manifest.py`: typed release manifest parser and
  validation helpers.
- `installer/vezor_installer/cli.py`: local `vezorctl` commands for status,
  bootstrap, pairing, support bundle, and local diagnostics.
- `installer/vezor_installer/paths.py`: shared path constants for Linux,
  macOS, and Jetson.
- `installer/linux/install-master.sh`: Linux master package entrypoint.
- `installer/linux/install-edge.sh`: Linux/Jetson edge package entrypoint.
- `installer/linux/uninstall.sh`: data-preserving uninstall entrypoint.
- `installer/macos/install-master.sh`: macOS portable master entrypoint.
- `installer/macos/uninstall.sh`: data-preserving macOS uninstall entrypoint.
- `infra/install/compose/compose.master.yml`: production master appliance
  profile.
- `infra/install/systemd/vezor-master.service`: Linux master service wrapper.
- `infra/install/systemd/vezor-edge.service`: Linux/Jetson edge service
  wrapper.
- `infra/install/launchd/com.vezor.master.plist`: macOS master service wrapper.
- Backend first-run code stays in `backend/src/argus/api/v1/deployment.py`,
  `backend/src/argus/services/deployment_nodes.py`, and
  `backend/src/argus/api/contracts.py` to avoid a second deployment domain.
- Frontend first-run code uses `frontend/src/pages/FirstRun.tsx`,
  `frontend/src/hooks/use-bootstrap.ts`, and the existing Deployment page.

## Task 23A: Installer Manifest And Local Tooling Skeleton

**Files:**

- Create: `installer/pyproject.toml`
- Create: `installer/README.md`
- Create: `installer/vezor_installer/__init__.py`
- Create: `installer/vezor_installer/manifest.py`
- Create: `installer/vezor_installer/paths.py`
- Create: `installer/tests/test_manifest.py`
- Create: `installer/manifests/dev-example.json`

- [ ] **Step 1: Write manifest tests**

Create `installer/tests/test_manifest.py` with tests for:

- required manifest fields: `version`, `release_channel`, `images`,
  `package_targets`, and `minimum_versions`
- image digest presence for every product service
- Linux master, macOS master, and Jetson edge targets
- rejection of `latest` image tags in production manifests

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_manifest.py -q
```

Expected: fail because the installer package does not exist.

- [ ] **Step 2: Add installer package metadata**

Create `installer/pyproject.toml` with Python 3.12, pytest, pydantic, rich, and
httpx dependencies. Add console script `vezorctl = vezor_installer.cli:main`
even though `cli.py` lands in a later task.

- [ ] **Step 3: Implement manifest parser**

Create `Manifest`, `ImageSpec`, `PackageTarget`, and `MinimumVersions` models
in `installer/vezor_installer/manifest.py`.

Validation rules:

- production image references must include `@sha256:`
- `release_channel` is one of `dev`, `pilot`, `stable`
- package targets include `linux-master`, `macos-master`, and `jetson-edge`
- port numbers are unique inside a target

- [ ] **Step 4: Add path constants**

Create `installer/vezor_installer/paths.py` with constants for:

- `/opt/vezor/current`
- `/etc/vezor`
- `/var/lib/vezor`
- `/var/log/vezor`
- `/run/vezor`
- macOS launchd plist directory
- systemd unit directory

- [ ] **Step 5: Add dev manifest**

Create `installer/manifests/dev-example.json` using clearly marked dev image
references and local ports. Mark `release_channel` as `dev` so the manifest can
use non-digest image references only in development.

- [ ] **Step 6: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_manifest.py -q
git diff --check -- installer
```

Expected: pass.

Commit:

```bash
git add installer/pyproject.toml installer/README.md installer/vezor_installer installer/tests/test_manifest.py installer/manifests/dev-example.json
git commit -m "feat(installer): add release manifest contract"
git push origin codex/omnisight-installer
```

## Task 23B: Linux Master Appliance Installer

**Files:**

- Create: `infra/install/compose/compose.master.yml`
- Create: `infra/install/systemd/vezor-master.service`
- Create: `installer/linux/install-master.sh`
- Create: `installer/linux/uninstall.sh`
- Create: `installer/tests/test_linux_master_artifacts.py`
- Modify: `installer/README.md`

- [ ] **Step 1: Write artifact tests**

Create tests that read the service and Compose files and assert:

- `vezor-master.service` uses `Restart=on-failure`
- service starts a pinned appliance command, not `make dev-up`
- service references `/etc/vezor/master.json`
- Compose profile includes backend, frontend, Postgres, Redis, NATS, MinIO,
  MediaMTX, Keycloak, and central supervisor
- no file contains `ARGUS_API_BEARER_TOKEN`, `Bearer `, or seeded
  `admin-dev` credentials

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_linux_master_artifacts.py -q
```

Expected: fail until artifacts exist.

- [ ] **Step 2: Add master Compose profile**

Create `infra/install/compose/compose.master.yml` from the dev stack shape but
with production names, pinned image variables, persistent volume paths under
`/var/lib/vezor`, and config mounted from `/etc/vezor`.

Do not include frontend dev server, bind-mounted source code, `admin-dev`
fixtures, or development hot reload commands.

- [ ] **Step 3: Add systemd master service**

Create `infra/install/systemd/vezor-master.service` that runs the appliance
through the local container engine and Compose profile. It must:

- wait for network
- run as root only for service orchestration
- store application data under `/var/lib/vezor`
- log under `/var/log/vezor`
- restart on failure
- never embed bearer tokens

- [ ] **Step 4: Add Linux install script**

Create `installer/linux/install-master.sh` with:

- `--dry-run`
- `--version`
- `--manifest`
- `--public-url`
- `--data-dir`
- `--config-dir`

The script validates OS, architecture, ports, disk space, container engine, and
write permissions. It creates directories, writes `/etc/vezor/master.json`,
installs `vezor-master.service`, enables it, starts it, and prints the local
first-run URL.

- [ ] **Step 5: Add data-preserving uninstall script**

Create `installer/linux/uninstall.sh` with:

- default behavior: stop and disable services but preserve data
- `--purge-data` behavior: require the exact confirmation string
  `delete-vezor-data`

- [ ] **Step 6: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_linux_master_artifacts.py -q
bash -n installer/linux/install-master.sh
bash -n installer/linux/uninstall.sh
git diff --check -- infra/install/compose/compose.master.yml infra/install/systemd/vezor-master.service installer/linux installer/README.md
```

Expected: pass.

Commit:

```bash
git add infra/install/compose/compose.master.yml infra/install/systemd/vezor-master.service installer/linux/install-master.sh installer/linux/uninstall.sh installer/tests/test_linux_master_artifacts.py installer/README.md
git commit -m "feat(installer): add Linux master package artifacts"
git push origin codex/omnisight-installer
```

## Task 23C: macOS Master Installer

**Files:**

- Create: `infra/install/launchd/com.vezor.master.plist`
- Create: `installer/macos/install-master.sh`
- Create: `installer/macos/uninstall.sh`
- Create: `installer/tests/test_macos_master_artifacts.py`
- Modify: `installer/README.md`
- Modify: `docs/macbook-pro-jetson-portable-demo-install-guide.md`

- [ ] **Step 1: Write macOS artifact tests**

Tests assert:

- launchd plist has label `com.vezor.master`
- plist starts at load and keeps alive
- plist references `/etc/vezor/master.json`
- plist does not contain bearer tokens or development credentials
- installer validates Apple Silicon and Intel macOS but labels Linux as wrong
  target

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_macos_master_artifacts.py -q
```

Expected: fail until artifacts exist.

- [ ] **Step 2: Add launchd master plist**

Create `com.vezor.master.plist` that starts the local Vezor master appliance
through a stable wrapper command under `/opt/vezor/current/bin/vezor-master`.

- [ ] **Step 3: Add macOS install script**

Create `installer/macos/install-master.sh` with:

- `--dry-run`
- `--version`
- `--manifest`
- `--public-url`
- `--data-dir`
- dependency validation for Docker Desktop or selected appliance engine
- launchd plist installation
- first-run bootstrap token creation

The script must not ask the user to run Docker Compose manually.

- [ ] **Step 4: Add macOS uninstall script**

Create `installer/macos/uninstall.sh` with data-preserving default behavior and
explicit `--purge-data delete-vezor-data` behavior.

- [ ] **Step 5: Update portable guide**

Modify the MacBook Pro + Jetson guide so the primary future product path points
to the macOS master installer and keeps Docker dev commands clearly labeled as
current pre-installer fallback.

- [ ] **Step 6: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_macos_master_artifacts.py -q
bash -n installer/macos/install-master.sh
bash -n installer/macos/uninstall.sh
git diff --check -- infra/install/launchd/com.vezor.master.plist installer/macos docs/macbook-pro-jetson-portable-demo-install-guide.md
```

Expected: pass.

Commit:

```bash
git add infra/install/launchd/com.vezor.master.plist installer/macos/install-master.sh installer/macos/uninstall.sh installer/tests/test_macos_master_artifacts.py installer/README.md docs/macbook-pro-jetson-portable-demo-install-guide.md
git commit -m "feat(installer): add macOS master package artifacts"
git push origin codex/omnisight-installer
```

## Task 23D: Jetson Edge Installer

**Files:**

- Create: `infra/install/systemd/vezor-edge.service`
- Create: `installer/linux/install-edge.sh`
- Create: `installer/tests/test_edge_installer_artifacts.py`
- Modify: `scripts/jetson-preflight.sh`
- Modify: `infra/install/compose/compose.supervisor.yml`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Write edge installer tests**

Tests assert:

- edge service uses systemd and restarts after failure
- edge install script calls Jetson preflight when target is Jetson
- edge install script accepts `--api-url`, `--pairing-code`, and `--unpaired`
- edge service reads `/etc/vezor/edge.json` and `/etc/vezor/supervisor.json`
- no edge service file embeds bearer tokens

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: fail until artifacts exist.

- [ ] **Step 2: Add edge service**

Create `infra/install/systemd/vezor-edge.service` for the edge appliance. It
should start local MediaMTX, supervisor, and edge support services through a
stable wrapper command.

- [ ] **Step 3: Add edge install script**

Create `installer/linux/install-edge.sh` that validates JetPack, NVIDIA
Container Toolkit, camera devices, ports, model directory, and reachability to
the master API when `--api-url` is supplied.

If `--pairing-code` is supplied, the script stores it only long enough for
`vezorctl pair` to claim the session and write node credentials.

- [ ] **Step 4: Tighten Jetson preflight**

Extend `scripts/jetson-preflight.sh` so it can run in installer mode and output
machine-readable status for missing NVIDIA runtime, camera devices, or required
ports.

- [ ] **Step 5: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_edge_installer_artifacts.py -q
bash -n installer/linux/install-edge.sh
bash -n scripts/jetson-preflight.sh
git diff --check -- infra/install/systemd/vezor-edge.service installer/linux/install-edge.sh scripts/jetson-preflight.sh infra/install/compose/compose.supervisor.yml docs/runbook.md
```

Expected: pass.

Commit:

```bash
git add infra/install/systemd/vezor-edge.service installer/linux/install-edge.sh installer/tests/test_edge_installer_artifacts.py scripts/jetson-preflight.sh infra/install/compose/compose.supervisor.yml docs/runbook.md
git commit -m "feat(installer): add Jetson edge installer"
git push origin codex/omnisight-installer
```

## Task 23E: Master First-Run Bootstrap Backend

**Files:**

- Create: `backend/src/argus/migrations/versions/0028_master_first_run_bootstrap.py`
- Modify: `backend/src/argus/models/tables.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/deployment.py`
- Modify: `backend/src/argus/services/deployment_nodes.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/api/test_deployment_routes.py`
- Test: `backend/tests/services/test_deployment_nodes.py`

- [ ] **Step 1: Write failing bootstrap backend tests**

Cover:

- fresh master reports `first_run_required`
- bootstrap complete requires one-time local bootstrap token
- bootstrap token hash is persisted, not plaintext
- bootstrap token can be consumed once
- bootstrap creates initial tenant/admin and central deployment node
- normal admin routes cannot be called with a bootstrap token

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_deployment_routes.py tests/services/test_deployment_nodes.py -q
```

Expected: fail until bootstrap contracts exist.

- [ ] **Step 2: Add migration and table**

Create `master_bootstrap_sessions` with tenant nullable during first-run,
token hash, status, consumed timestamp, created subject, and expiry. Use a
short expiry and one active local bootstrap session.

- [ ] **Step 3: Add contracts and routes**

Add:

- `GET /api/v1/deployment/bootstrap/status`
- `POST /api/v1/deployment/bootstrap/complete`
- `POST /api/v1/deployment/bootstrap/rotate-local-token`

The rotate route is local/bootstrap protected, not normal remote admin setup.

- [ ] **Step 4: Implement service logic**

`DeploymentNodeService` should create and consume bootstrap sessions, create or
resolve the central deployment node, and return a safe status response that
never includes the bootstrap token plaintext.

- [ ] **Step 5: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run alembic upgrade head
python3 -m uv run pytest tests/api/test_deployment_routes.py tests/services/test_deployment_nodes.py -q
python3 -m uv run ruff check src/argus/api/v1/deployment.py src/argus/services/deployment_nodes.py tests/api/test_deployment_routes.py tests/services/test_deployment_nodes.py
```

Expected: pass.

Commit:

```bash
git add backend/src/argus/migrations/versions/0028_master_first_run_bootstrap.py backend/src/argus/models/tables.py backend/src/argus/api/contracts.py backend/src/argus/api/v1/deployment.py backend/src/argus/services/deployment_nodes.py backend/src/argus/services/app.py backend/tests/api/test_deployment_routes.py backend/tests/services/test_deployment_nodes.py
git commit -m "feat(deployment): add master first-run bootstrap"
git push origin codex/omnisight-installer
```

## Task 23F: First-Run UI And Deployment Installer Surface

**Files:**

- Create: `frontend/src/hooks/use-bootstrap.ts`
- Create: `frontend/src/pages/FirstRun.tsx`
- Create: `frontend/src/pages/FirstRun.test.tsx`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/pages/Deployment.tsx`
- Modify: `frontend/src/pages/Deployment.test.tsx`
- Modify: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Regenerate API types**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend generate:api
```

Expected: generated deployment bootstrap routes appear in `api.generated.ts`.

- [ ] **Step 2: Write first-run UI tests**

Cover:

- fresh install redirects unauthenticated local user to `/first-run`
- first-run form requires bootstrap code, admin email, password, tenant name,
  and central node name
- successful completion routes to sign-in
- Deployment page shows package target guidance for macOS master, Linux master,
  and Jetson edge
- Deployment page never exposes copied bearer tokens

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/FirstRun.test.tsx src/pages/Deployment.test.tsx
```

Expected: fail until UI exists.

- [ ] **Step 3: Implement first-run hook and page**

Create `useBootstrapStatus`, `useCompleteBootstrap`, and `FirstRunPage`.
Keep the UI operational and compact. Do not add marketing copy.

- [ ] **Step 4: Wire routing**

Update router logic so first-run required state sends the local operator to
`/first-run`, while normal auth continues to use existing sign-in flow.

- [ ] **Step 5: Update Deployment package cards**

Add install package cards for:

- macOS master
- Linux master
- Jetson edge

Each card can show package status and copy bootstrap commands only in an
explicit installer/download context. It must not imply that the backend will
execute commands on another host.

- [ ] **Step 6: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/FirstRun.test.tsx src/pages/Deployment.test.tsx
corepack pnpm --dir frontend exec tsc -b
git diff --check -- frontend/src/hooks/use-bootstrap.ts frontend/src/pages/FirstRun.tsx frontend/src/pages/Deployment.tsx frontend/src/app/router.tsx
```

Expected: pass.

Commit:

```bash
git add frontend/src/hooks/use-bootstrap.ts frontend/src/pages/FirstRun.tsx frontend/src/pages/FirstRun.test.tsx frontend/src/app/router.tsx frontend/src/pages/Deployment.tsx frontend/src/pages/Deployment.test.tsx frontend/src/lib/api.generated.ts
git commit -m "feat(deployment): add first-run bootstrap UI"
git push origin codex/omnisight-installer
```

## Task 23G: Local `vezorctl` Pairing, Status, And Support CLI

**Files:**

- Create: `installer/vezor_installer/cli.py`
- Create: `installer/vezor_installer/http.py`
- Create: `installer/tests/test_cli.py`
- Modify: `installer/pyproject.toml`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Write CLI tests**

Cover:

- `vezorctl status --json` reads local config and reports service state
- `vezorctl pair --api-url URL --session-id ID --pairing-code CODE` calls the
  pairing claim endpoint and writes credential material with mode `0600`
- `vezorctl support-bundle --redact` redacts token-like values
- CLI refuses to print credential material

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_cli.py -q
```

Expected: fail until CLI exists.

- [ ] **Step 2: Implement CLI**

Create commands:

- `status`
- `pair`
- `bootstrap-master`
- `support-bundle`
- `doctor`

All commands operate on the local host only.

- [ ] **Step 3: Implement HTTP helper**

Create `installer/vezor_installer/http.py` with a small typed client for
pairing claim and bootstrap status. Use timeouts and explicit error messages.

- [ ] **Step 4: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_cli.py -q
python3 -m uv run --project installer ruff check installer/vezor_installer installer/tests
git diff --check -- installer/vezor_installer docs/runbook.md
```

Expected: pass.

Commit:

```bash
git add installer/vezor_installer/cli.py installer/vezor_installer/http.py installer/tests/test_cli.py installer/pyproject.toml docs/runbook.md
git commit -m "feat(installer): add local vezorctl utility"
git push origin codex/omnisight-installer
```

## Task 23H: Hide Dev Worker Commands From Normal Product Operation

**Files:**

- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`
- Modify: `frontend/src/components/operations/SupervisorLifecycleControls.tsx`
- Modify: `frontend/src/components/operations/SupervisorLifecycleControls.test.tsx`
- Modify: `docs/operator-deployment-playbook.md`

- [ ] **Step 1: Write UI tests**

Cover:

- installed deployment nodes show Start/Stop/Restart/Drain controls
- no copyable bearer-token worker command appears for installed nodes
- dev command panel appears only when explicit dev/break-glass mode is active
- missing supervisor state directs operator to Deployment install/pairing, not
  to a generic Docker command

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx src/components/operations/SupervisorLifecycleControls.test.tsx
```

Expected: fail until UI copy is gated.

- [ ] **Step 2: Gate dev command panels**

Keep copyable commands available for local development and break-glass, but
label them explicitly and hide them from normal installed operation.

- [ ] **Step 3: Make missing supervisor guidance actionable**

When a camera has no installed eligible supervisor, Operations should direct
the operator to Control -> Deployment to install or pair a node.

- [ ] **Step 4: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx src/components/operations/SupervisorLifecycleControls.test.tsx
corepack pnpm --dir frontend exec tsc -b
git diff --check -- frontend/src/pages/Settings.tsx frontend/src/components/operations/SupervisorLifecycleControls.tsx docs/operator-deployment-playbook.md
```

Expected: pass.

Commit:

```bash
git add frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx frontend/src/components/operations/SupervisorLifecycleControls.tsx frontend/src/components/operations/SupervisorLifecycleControls.test.tsx docs/operator-deployment-playbook.md
git commit -m "fix(operations): reserve dev commands for break-glass"
git push origin codex/omnisight-installer
```

## Task 23I: Installer Documentation And Runbooks

**Files:**

- Create: `docs/product-installer-and-first-run-guide.md`
- Modify: `README.md`
- Modify: `docs/runbook.md`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/macbook-pro-jetson-portable-demo-install-guide.md`
- Modify: `docs/deployment-modes-and-matrix.md`

- [ ] **Step 1: Write product installer guide**

Create a single operator guide with:

- Linux master install
- macOS master install
- Jetson edge install
- first-run bootstrap
- pairing
- UI lifecycle validation
- reboot validation
- upgrade
- uninstall
- support bundle
- what remains dev/break-glass

- [ ] **Step 2: Update existing docs**

Update existing docs so:

- Docker dev commands are labeled current pre-installer fallback or local dev
- final product operation points at installed services and first-run UI
- Linux master installer is described as the production master path
- MacBook installer is described as portable pilot/demo path
- Task 24 remains deferred

- [ ] **Step 3: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
git diff --check -- README.md docs/product-installer-and-first-run-guide.md docs/runbook.md docs/operator-deployment-playbook.md docs/macbook-pro-jetson-portable-demo-install-guide.md docs/deployment-modes-and-matrix.md
rg -n "make dev-up|docker compose|ARGUS_API_BEARER_TOKEN" docs/product-installer-and-first-run-guide.md
```

Expected: diff check passes. Any dev command hits in the product installer
guide are explicitly labeled `Development fallback` or `Break-glass`.

Commit:

```bash
git add README.md docs/product-installer-and-first-run-guide.md docs/runbook.md docs/operator-deployment-playbook.md docs/macbook-pro-jetson-portable-demo-install-guide.md docs/deployment-modes-and-matrix.md
git commit -m "docs(installer): add product first-run guide"
git push origin codex/omnisight-installer
```

## Task 23J: Installer Validation Harness And Release Gate

**Files:**

- Create: `scripts/validate-installers.sh`
- Create: `installer/tests/test_release_gate.py`
- Modify: `Makefile`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Write release gate tests**

Tests assert:

- all service files are present
- install scripts pass shell syntax checks
- manifest validation passes
- product docs exist
- dev-only commands are not present in product service files
- DeepStream files are not required by installer validation

Run:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project installer pytest installer/tests/test_release_gate.py -q
```

Expected: fail until validation harness exists.

- [ ] **Step 2: Add validation script**

Create `scripts/validate-installers.sh` that runs:

- installer pytest suite
- shell syntax checks
- manifest validation
- Compose config render for master and edge when Docker is available
- secret scan for service files and installer docs

- [ ] **Step 3: Add Makefile target**

Add:

```make
verify-installers:
	./scripts/validate-installers.sh
```

- [ ] **Step 4: Validate and commit**

Run:

```bash
cd /Users/yann.moren/vision
make verify-installers
git diff --check -- scripts/validate-installers.sh installer/tests/test_release_gate.py Makefile docs/runbook.md
```

Expected: pass in the local environment, or skip only the Compose render with a
clear `docker unavailable` message when Docker is not installed.

Commit:

```bash
git add scripts/validate-installers.sh installer/tests/test_release_gate.py Makefile docs/runbook.md
git commit -m "test(installer): add installer release gate"
git push origin codex/omnisight-installer
```

## Final Verification For The Band

Run after all tasks:

```bash
cd /Users/yann.moren/vision
make verify-installers
make lint
make test
```

For a real field validation, additionally run:

1. macOS master install on the MacBook Pro.
2. Linux master install on an Ubuntu host or VM.
3. Jetson edge install on the Jetson.
4. First-run bootstrap from the UI.
5. Edge pairing from Control -> Deployment.
6. One Jetson camera Start/Restart from Control -> Operations.
7. Live, History, Evidence, Scenes, Sites, Settings, Deployment, and Operations
   smoke checks after reboot.

Do not start Task 24 / DeepStream until this band is either complete or the
user explicitly accepts doing DeepStream before product installer validation.
