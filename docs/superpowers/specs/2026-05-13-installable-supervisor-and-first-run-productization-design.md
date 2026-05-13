# Installable Supervisor And First-Run Productization Design

Date: 2026-05-13

## Status

New productization band to insert after Task 21C and before Task 22 in the
Accountable Scene Intelligence implementation runway.

This design turns the current runnable supervisor from a pilot/developer tool
into an installable Vezor product component for macOS and Linux. The target
operator experience is:

1. Install Vezor on the central node and any edge nodes.
2. Open the UI.
3. Complete first-run setup, node pairing, storage, runtime, model, camera, and
   privacy configuration in the UI.
4. Use Operations for day-to-day Start, Stop, Restart, Drain, assignment,
   hardware admission, and diagnostics.

After installation, normal operation must not require terminal commands,
hand-edited env files, copied bearer tokens, or shell-based worker starts.

## Product Goal

Make Vezor deployable as a final product rather than a developer-operated lab
stack.

The browser and backend API remain a control plane. They must not become a
generic remote shell. A node-local supervisor owns host process reconciliation,
reports truth, manages local credentials, and applies only bounded lifecycle
actions that the control plane authorized.

The operator should be able to answer:

- Is this node installed correctly?
- Is the supervisor running after reboot?
- Which OS/service manager owns it?
- Which credentials are bound to the node?
- Which workers can this node safely run?
- Which service, storage, stream, and model configuration is active?
- What changed, who changed it, and what should I do if it fails?

## Best-Practice Basis

This spec uses current primary-source guidance available on 2026-05-13:

- OAuth security should follow RFC 9700, published as OAuth 2.0 Security Best
  Current Practice in January 2025. Vezor should avoid password-grant style
  product flows, restrict token privilege, and treat refresh/device credentials
  as scoped node authenticators.
- Edge/node pairing should follow the shape of RFC 8628 where a constrained
  device can be authorized through a separate browser-capable device. Vezor does
  not need to expose raw OAuth device flow immediately, but it should copy the
  product properties: one-time code, short expiry, outbound HTTPS polling, and
  user approval in the UI.
- NIST SP 800-63B authenticator lifecycle guidance says binding codes should be
  one-time, short lived, and not sent over insecure channels. Vezor pairing
  codes should expire quickly, store only hashes server-side, and be revocable.
- Linux services should use systemd units with a dedicated service user,
  restart policy, explicit state/log directories, and hardening. Newer systemd
  supports unit credentials through `LoadCredential=` and exposes
  `$CREDENTIALS_DIRECTORY` for service-local secret files.
- macOS services should be represented as launchd-managed background helpers.
  For a bundled signed macOS app on macOS 13+, Apple's `SMAppService` is the
  preferred management API for helper LaunchAgents and LaunchDaemons. For the
  near-term CLI/server product, the installer can still install a signed
  LaunchDaemon plist while the design keeps the helper boundary compatible with
  later `SMAppService` registration.
- Containerized deployments should use Docker restart policies, healthchecks,
  and dependency health conditions rather than manual foreground processes.

References:

- https://www.rfc-editor.org/rfc/rfc9700.html
- https://www.rfc-editor.org/info/rfc8628
- https://pages.nist.gov/800-63-4/sp800-63b.html
- https://www.freedesktop.org/software/systemd/man/systemd.exec.html
- https://www.freedesktop.org/software/systemd/man/systemd.service.html
- https://developer.apple.com/documentation/servicemanagement/smappservice
- https://docs.docker.com/reference/compose-file/services/
- https://docs.docker.com/compose/how-tos/startup-order/

## Scope

In scope:

- macOS and Linux central-node supervisor installation.
- Linux/Jetson edge-node supervisor installation.
- A single Vezor Supervisor Agent contract across macOS, Linux, and container
  deployment forms.
- Service-manager adapters that hide OS differences from the UI.
- First-run setup UI for install health, node pairing, service health, storage,
  runtime/model admission, and deployment diagnostics.
- Short-lived node pairing sessions.
- Node-bound supervisor credentials that are refreshable, scoped, revocable,
  and never copied as normal operator workflow.
- Installer/service artifacts that do not embed long-lived bearer tokens.
- Support bundle and diagnostics surfaced in UI.
- Documentation for package-style install, container install, and lab/dev
  escape hatches.

Out of scope for this band:

- Track C / DeepStream runtime implementation.
- Kubernetes operator implementation.
- Cloud-hosted multi-tenant SaaS operations.
- Native signed macOS GUI app packaging.
- Fully automated binary update channel.
- Replacing Keycloak in the dev stack.

## Architecture

### Control Plane

The backend remains the source of desired configuration:

- deployment nodes
- supervisor installations
- node pairing sessions
- scoped supervisor credentials
- lifecycle requests
- worker assignments
- hardware reports
- model-admission decisions
- support bundle requests

The backend exposes intent and state. It does not execute shell commands on the
host.

### Supervisor Agent

Each central or edge node runs one Vezor Supervisor Agent. The agent:

- starts automatically after boot
- reports service status and version
- reports hardware capability and observed model performance
- stores node credentials through a platform credential backend
- refreshes access without requiring pasted bearer tokens
- polls for lifecycle requests
- starts/stops/restarts/drains local workers through a bounded adapter
- reconciles desired running workers after a supervisor restart
- produces local diagnostic summaries for the UI

The existing `argus.supervisor.runner` is the seed for this agent, but final
product mode cannot require command-line flags for normal operation.

### Service Manager Boundary

The supervisor has a cross-platform `ServiceManager` boundary:

- `systemd`: production Linux central and Linux/Jetson edge.
- `launchd`: macOS central and macOS lab/pilot nodes.
- `compose`: containerized edge or appliance deployments.
- `direct_child`: development-only fallback for local tests.

The UI should never expose these as different products. It can show the detected
service manager for diagnostics, but all actions remain Start, Stop, Restart,
Drain, Pair, Rotate, Update, and Export Diagnostics.

### Installation State

Vezor tracks install state separately from worker runtime state:

- `not_installed`: node exists in UI but has never paired.
- `pairing_pending`: one-time pairing session has been created.
- `installed`: supervisor paired and has reported service details.
- `healthy`: service report is fresh and dependencies are ready.
- `degraded`: service is up but dependencies, credentials, storage, or model
  admission have warnings.
- `offline`: service report is stale.
- `revoked`: node credential was revoked or rotated without re-pairing.

Worker lifecycle state remains separate:

- `not_reported`
- `starting`
- `running`
- `draining`
- `stopped`
- `error`

### First-Run UI

Add a deployment surface outside day-to-day Operations:

- Primary location: `Control -> Deployment`.
- Secondary access: a Settings card named `System setup`.

The deployment surface owns setup and health:

1. Core services: API, database, auth, media, NATS, object storage.
2. Nodes: central node, edge nodes, OS, service manager, version, heartbeat.
3. Pairing: create one-time pairing sessions and show status.
4. Credentials: rotate, revoke, and re-pair node credentials.
5. Storage: local, central, S3-compatible/cloud, local-first readiness.
6. Runtime and models: hardware report, provider support, recommendation.
7. Diagnostics: logs summary, support bundle, migration status.

Operations remains the daily workbench for camera workers and lifecycle
requests.

### Pairing And Credentials

Final product mode must replace pasted bearer tokens with node-bound
credentials.

Pairing flow:

1. Admin opens Control -> Deployment.
2. Admin creates a pairing session for central or edge node.
3. UI shows a short-lived pairing code and optional QR/deep link.
4. Installed supervisor claims the pairing session over outbound HTTPS.
5. Backend stores only a pairing-code hash and marks the session consumed.
6. Backend returns one-time node credential material.
7. Supervisor stores the credential in the platform credential backend.
8. Subsequent access uses short-lived access tokens refreshed by the
   supervisor.

Credential properties:

- one-time pairing material is returned once
- plaintext is never persisted server-side
- node credentials are scoped to supervisor/node APIs only
- rotation and revocation are auditable
- a revoked node cannot poll lifecycle requests or report health
- access is audience-restricted to Vezor APIs

Task 22 remains the deeper credential rotation task. This band creates the
install/pairing surfaces that make rotation meaningful in the product.

### Platform Credential Storage

Preferred storage:

- Linux/systemd: root-owned credential file plus `LoadCredential=` where
  supported; service runs as a dedicated `vezor` user and reads secrets from the
  service credential directory.
- macOS: Keychain for packaged app/helper mode; root-owned LaunchDaemon
  configuration file as the near-term server installer fallback.
- Compose/container: Docker secrets or mounted credential files; env variables
  are allowed only for local dev and break-glass.

No service unit, plist, or Compose file should contain a long-lived bearer
token.

### Diagnostics And Support

The UI should expose a support bundle request that gathers:

- supervisor version and service manager
- last service reports
- recent lifecycle requests
- recent runtime reports
- hardware/model-admission summaries
- redacted config hashes and profile ids
- selected log excerpts

The bundle must redact secrets and tokens by default.

## Failure Handling

- If pairing expires, the UI shows `pairing_expired` and lets the admin create a
  new session.
- If a node is paired but stale, Operations disables production Start/Restart
  and Deployment shows the last report time.
- If credentials are revoked, the supervisor receives 401/403, stops claiming
  lifecycle requests, and reports only through a re-pair path.
- If storage or media services are unhealthy, worker Start remains blocked when
  the selected scene requires recording or browser stream delivery.
- If model admission is `unknown` or `unsupported`, Start/Restart remains
  blocked unless an explicit lab/dev override exists.
- If the supervisor restarts while workers should be running, it reconciles
  desired state instead of leaving the UI stale.

## Security Requirements

- No generic shell bridge from backend or browser.
- No password-grant product flow for supervisors.
- No long-lived bearer tokens in service definitions.
- Pairing codes are one-time, hashed at rest, and expire in minutes.
- Node credentials are scoped, revocable, and auditable.
- Supervisor APIs use least privilege and cannot mutate unrelated tenant data.
- Logs, support bundles, and UI responses redact secrets.
- Production service files run with least privilege and explicit writable
  directories.
- Local dev bypasses are visibly labeled and cannot silently become production
  defaults.

## UI Design Requirements

The deployment UI should feel operational, not marketing-like:

- dense but legible status tables for nodes and services
- cards only for repeated node/service items, not nested panels
- clear status chips: `healthy`, `degraded`, `offline`, `pairing`, `revoked`
- one primary action per setup step
- destructive actions such as revoke/rotate require confirmation
- service-manager details live under diagnostics, not in the primary workflow
- copyable commands appear only in dev/lab docs or a hidden break-glass panel

Suggested navigation:

- `Control -> Deployment`: install health, nodes, pairing, diagnostics.
- `Control -> Operations`: camera workers, assignments, lifecycle, runtime.
- `Settings -> Configuration`: product profiles and bindings.

## Acceptance Criteria

- A fresh central node can be installed, paired, and configured without manual
  bearer tokens after installation.
- A fresh edge node can be paired from the UI using one-time material.
- The supervisor starts after reboot on macOS or Linux.
- Operations lifecycle buttons work through supervisor-owned reconciliation.
- Workers can be started from the UI only when the target node has fresh
  hardware reports and model admission allows it.
- Service files and install manifests do not embed long-lived bearer tokens.
- The UI can show node install health, credential status, model recommendation,
  and diagnostics.
- Credential rotation from Task 22 can reuse the node credential model created
  by this band.
- Lab/dev command-line flows remain documented as break-glass only, not normal
  product operation.

## Implementation Placement

Insert this band after Task 21C and before Task 22:

- Task 21D: Deployment node and service status data contract.
- Task 21E: Cross-platform service manager and install artifact renderers.
- Task 21F: Pairing sessions and node credential exchange.
- Task 21G: Supervisor product mode and restart-safe reconciliation.
- Task 21H: Control -> Deployment first-run UI and diagnostics.

Then continue:

- Task 22: Edge credential rotation and bootstrap hardening.
- Task 23: Production Linux and Jetson runtime artifact soak.
- Task 24: Track C / DeepStream, gated by Task 23.
- Task 25: Full verification and handoff.
