# Product Installer And No-Console First Run Design

Date: 2026-05-14

## Status

New band to insert after the installable supervisor, credential rotation, and
runtime soak recording contracts, and before Task 24 / DeepStream.

Suggested band name:

```text
Band 8.5: Product Installer And No-Console First Run
```

This band closes the gap between the current state and the product expectation
that operators should not run Docker development commands, paste bearer tokens,
or keep supervisor processes in foreground terminals after installation.

## Product Intent

Vezor should install like a product:

1. Run a master installer on macOS for portable pilot/demo systems, or on Linux
   for production master systems.
2. Run an edge installer on Jetson or Linux edge nodes.
3. Open the Vezor UI.
4. Complete first-run bootstrap, node pairing, site, camera, storage, runtime,
   privacy, and recording setup from the UI.
5. Start, stop, restart, drain, rotate credentials, and export diagnostics from
   the UI.

The UI is a control plane. It can show install packages, setup state, pairing
codes, service health, and lifecycle buttons. It must not become a generic
remote shell and must not execute arbitrary host commands on the MacBook,
Linux master, or Jetson.

## Why Band 7.5 Was Not Enough

Band 7.5 created the correct product contracts:

- Deployment UI
- deployment nodes
- service reports
- one-time pairing sessions
- node credentials
- credential rotation/revocation
- supervisor product config mode
- launchd, systemd, and Compose service templates

Those contracts make installed operation possible, but they do not yet provide
the package layer that creates a master stack, starts services after reboot,
runs migrations, exposes the first-run UI, and installs edge services without
manual Docker development commands.

This band turns those contracts into installable flows.

## Core Decision

Recommended v1 installer shape:

- Linux master: systemd-owned container appliance package.
- macOS master: launchd-owned portable appliance package for pilot/demo use.
- Jetson edge: systemd-owned edge appliance package.
- UI first-run: product setup wizard backed by local bootstrap state and
  Deployment/Operations contracts.

The container appliance package may still use Docker, Podman, or a Compose
compatible engine under the hood. The difference is that the operator does not
run `make dev-up`, `docker compose up`, copied worker commands, or foreground
supervisor commands. The installer owns service creation, configuration,
startup, restart, and uninstall.

## Alternatives Considered

### A. UI Executes Docker Commands Remotely

Rejected.

It would make the backend/browser a remote shell, enlarge the attack surface,
make auditability poor, and violate the existing control-plane rule.

### B. Native Packages For Every Service In v1

Deferred.

Native Postgres, Redis, NATS, MediaMTX, MinIO, Keycloak, backend, frontend,
and observability packages are possible, but they are slower to harden across
macOS, Linux, and Jetson. They also make portable demos harder.

### C. Kubernetes/Helm First

Deferred.

The Helm chart remains useful for future production clusters, but the immediate
need is a single-machine master plus Jetson field rig and a small production
Linux master. A systemd/launchd appliance is easier to install and demonstrate.

### D. OS Service Manager Owns An Appliance

Selected.

The installer creates stable directories, writes config, validates
dependencies, installs service units, runs migrations, starts a supervised
appliance, and leaves day-to-day control to the Vezor UI and local supervisor.

## Deployment Targets

### macOS Master Installer

Purpose:

- portable MacBook Pro demo and pilot master
- local operator UI
- optional central RTSP camera processing
- control plane for Jetson edge cameras

Service manager:

- `launchd`

Expected package:

- signed `.pkg` when signing is available
- unsigned local package or scripted installer for internal pilot builds

Runtime:

- launchd-managed Vezor master service
- launchd-managed Vezor supervisor service
- appliance runtime may use Docker Desktop or a compatible local container
  engine in v1

Important constraint:

- macOS master is a pilot/demo target, not the long-term production HQ target.
  It should still avoid manual dev commands after installation.

### Linux Master Installer

Purpose:

- production master / HQ node
- long-running control plane
- stable base for later real-site validation

Service manager:

- `systemd`

Expected package:

- `.deb` first, because Ubuntu is the likely first Linux master target
- `.rpm` can follow after the layout is stable

Runtime:

- systemd-managed Vezor master appliance
- systemd-managed central supervisor
- pinned images or release artifacts
- persistent volumes under `/var/lib/vezor`
- config under `/etc/vezor`
- logs under `/var/log/vezor`

Linux master v1 may use a production Compose profile managed by systemd. That
is acceptable if the package, not the operator, owns the Compose invocation.

### Jetson Edge Installer

Purpose:

- site-local edge inference
- USB/UVC edge camera support
- local MediaMTX and worker lifecycle
- hardware/model admission reporting

Service manager:

- `systemd`

Expected package:

- `.deb` for Jetson Ubuntu / JetPack

Runtime:

- systemd-managed edge appliance
- edge supervisor in product config mode
- local MediaMTX
- optional NATS leaf and OTEL collector
- worker processes/containers owned by the supervisor

## First-Run Master Bootstrap

The master has a bootstrapping problem: the UI is served by the master, but the
first admin and tenant may not exist yet.

The installer solves this with local bootstrap state:

1. Installer writes a one-time local bootstrap secret to a protected local path,
   for example `/var/lib/vezor/bootstrap/bootstrap.token`.
2. Installer starts the master service.
3. User opens the local UI.
4. UI detects `first_run_required`.
5. User enters the local bootstrap code or opens a local loopback bootstrap URL
   generated by the installer.
6. User creates the first tenant/admin, storage profile, and central node name.
7. Backend marks bootstrap consumed and deletes or invalidates the token.

The bootstrap token is not a bearer token for normal APIs. It can only complete
first-run setup on the local master and is one-time use.

## First-Run Edge Pairing

Edge pairing uses the existing deployment pairing contract:

1. Admin opens Control -> Deployment on the master UI.
2. Admin creates an edge node or chooses a pending edge node.
3. UI creates a short-lived pairing session.
4. Edge installer or local edge CLI claims the session with the one-time code.
5. Backend returns node credential material once.
6. Edge stores credential material in the local credential store.
7. Edge supervisor reports service health and hardware capability.
8. Operations can start workers on that edge only after admission allows it.

The edge installer may accept `--api-url` and `--pairing-code`, or it may
install unpaired and let an operator run a local `vezorctl pair` command later.
Both are bootstrap paths, not daily operation.

## UI Responsibilities

The UI owns workflow and truth:

- show whether the master is bootstrapped
- show package/version/build information
- show service health from reports
- show central and edge nodes
- create pairing sessions
- rotate/revoke credentials
- show install and credential status
- guide operator to install a package when a node is missing
- start/restart/drain workers through supervisor lifecycle contracts
- show blocked starts when service, storage, or model admission is unsafe
- export redacted support bundles

The UI does not:

- run shell commands on a remote node
- install systemd/launchd units directly
- edit service files directly
- store or show long-lived bearer tokens
- pretend a manual dev process is production managed

## Installer Responsibilities

The installer owns local host changes:

- validate OS, architecture, disk, ports, and container/runtime dependencies
- create `vezor` service user where appropriate
- create `/etc/vezor`, `/var/lib/vezor`, `/var/log/vezor`, and runtime dirs
- write master or edge config
- install service units or launchd plists
- install pinned images or release artifacts
- run database migrations on master install and upgrade
- create local first-run bootstrap material on master
- start and enable services
- provide status, uninstall, and support-bundle commands

The installer may call the local package manager and service manager because
the operator runs it on the target host with local privileges.

## Service Layout

### Linux Master

Recommended paths:

- `/opt/vezor/releases/<version>`
- `/opt/vezor/current`
- `/etc/vezor/master.json`
- `/etc/vezor/supervisor.json`
- `/var/lib/vezor/postgres`
- `/var/lib/vezor/minio`
- `/var/lib/vezor/nats`
- `/var/lib/vezor/mediamtx`
- `/var/lib/vezor/bootstrap`
- `/var/log/vezor`

Recommended services:

- `vezor-master.service`
- `vezor-supervisor.service`

`vezor-master.service` owns the appliance stack. `vezor-supervisor.service`
owns central worker lifecycle and service reports.

### macOS Master

Recommended paths:

- `/opt/vezor/current`
- `/etc/vezor/master.json`
- `/etc/vezor/supervisor.json`
- `/Library/LaunchDaemons/com.vezor.master.plist`
- `/Library/LaunchDaemons/com.vezor.supervisor.plist`
- `/var/lib/vezor`
- `/var/log/vezor`

The installer should provide a single local command or package receipt for
status and uninstall. The normal demo flow should not require opening a
terminal after installation.

### Jetson Edge

Recommended paths:

- `/opt/vezor/current`
- `/etc/vezor/edge.json`
- `/etc/vezor/supervisor.json`
- `/var/lib/vezor/edge`
- `/var/lib/vezor/mediamtx`
- `/var/log/vezor`

Recommended services:

- `vezor-edge.service`
- `vezor-supervisor.service`

The edge package should run Jetson preflight checks and clearly report missing
NVIDIA runtime, wrong JetPack, unavailable camera devices, missing models, or
ports already in use.

## Configuration Model

Master config includes:

- node role: `master`
- public base URL
- local bind addresses
- OIDC mode
- storage paths
- object storage mode
- media relay settings
- package version
- first-run state

Supervisor config includes:

- supervisor id
- role: `central` or `edge`
- API base URL
- edge node id for edge supervisors
- credential store path
- worker metrics URL
- service manager
- version

Edge config includes:

- master API URL
- edge node name
- local MediaMTX URL
- local model path roots
- optional NATS leaf config
- camera device allowlist for USB/UVC

## Credential Model

Normal operation uses:

- local master bootstrap token only for first-run setup
- node pairing code only for pairing
- node credential material stored in local credential store
- short-lived access tokens derived from node credentials

Normal operation does not use:

- copied admin bearer tokens
- password grant for supervisors
- bearer tokens embedded in service files
- terminal sessions kept alive to run a supervisor

## Upgrade And Uninstall

Installer v1 must include:

- versioned install directory
- idempotent install
- idempotent upgrade
- preflight check before destructive changes
- migration backup point or explicit backup warning
- rollback to previous release when service health fails after upgrade
- uninstall that can preserve or remove data based on an explicit flag

Uninstall must never delete evidence, database, or object storage data without
an explicit destructive confirmation.

## Diagnostics

Installer and UI diagnostics should align:

- local `vezorctl status`
- local `vezorctl support-bundle`
- Deployment UI support bundle
- service logs with redacted secrets
- package version and image digest
- migration status
- node credential status
- last service report
- last hardware report
- last worker lifecycle request

Support bundles must redact:

- bearer tokens
- node credentials
- pairing codes
- passwords
- API keys
- database URLs with passwords
- MinIO secrets

## Validation Matrix

Minimum v1 validation:

| Target | Install | Reboot | Pair | Start Worker | Evidence | Upgrade | Uninstall |
|---|---|---|---|---|---|---|---|
| macOS master | required | required | central | optional central RTSP | required | smoke | preserve data |
| Linux master | required | required | central | optional central RTSP | required | required | preserve data |
| Jetson edge | required | required | edge | required | required | smoke | preserve data |

Installer tests should include dry-run rendering in CI. Real macOS and Jetson
install tests may be manual or hardware-lab gates until dedicated runners
exist.

## Acceptance Criteria

- A Linux master can be installed from a package and survive reboot without
  manual Docker commands.
- A macOS master can be installed for portable demos and survive reboot without
  manual Docker commands.
- A Jetson edge node can be installed, paired, and restarted without copied
  bearer tokens or foreground supervisors.
- The first admin/tenant can be created from the first-run UI with one-time
  local bootstrap material.
- Control -> Deployment shows the installed master and edge service health.
- Control -> Operations can start and restart a camera worker through the
  installed supervisor.
- Evidence, History, Live, Scenes, Settings, Operations, and Deployment remain
  usable after a master service restart.
- Package artifacts and service definitions do not embed long-lived secrets.
- Documentation makes clear which steps are install/bootstrap and which steps
  are normal UI operation.
- Task 24 / DeepStream remains deferred until installer validation and real
  Track A/B Jetson evidence are acceptable.

## Non-Goals

- No remote shell in the backend or browser.
- No DeepStream implementation in this band.
- No Kubernetes operator in this band.
- No automatic public update channel in v1.
- No promise that macOS is the long-term production HQ target.
- No silent deletion of operator data on uninstall or failed upgrade.

## Placement In The Roadmap

Insert this band before Task 24.

If real Task 23 hardware evidence has not been recorded yet, this band should
come before that hardware validation so the soak can test the product installer
shape instead of a developer Compose workflow.

If Task 23 record-contract implementation has already landed, keep it; this
band uses those records during final hardware validation.
