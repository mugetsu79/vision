# Remaining Whole-Product Live Smoke Closure Design

**Date:** 2026-06-09

**Status:** Proposed

**Related Plan:** `docs/superpowers/plans/2026-06-09-remaining-live-smoke-closure-implementation-plan.md`

## Summary

The previous whole-product smoke proved the MacBook installed master, first-run,
tenant auth, bundled YOLO26 model registration, Office RTSP live playback, and
central supervisor lifecycle. It did not prove the live product end to end
because six closure lanes remained: real Jetson supervisor/API sync and
inventory, deterministic detection/evidence/history generation, real billing
usage generation, TensorRT engine build on Jetson, master reflector secret
distribution plus a real UDP edge-agent probe, and a fresh destructive reset
after the central supervisor credential fix.

This design makes those lanes testable and repeatable. The product should gain
a deterministic live-smoke fixture and smoke harness that can prove each lane
without leaking secrets or treating missing infrastructure as a pass. Existing
central model/artifact lifecycle code remains the primary path for model sync
and TensorRT jobs. Existing billing, incident, evidence, history, Core Link, and
FleetOps APIs remain the validation surface. New product code should be narrow:
fixture orchestration, TensorRT builder wiring if the runner still lacks a real
builder, and supervisor-scoped reflector secret distribution if the edge cannot
retrieve a UDP probe secret from central.

## Goals

- Prove a fresh post-fix master install and first-run without manual supervisor
  credential repair.
- Pair a real Jetson edge node and validate supervisor API, service reports,
  support bundle, model sync jobs, and model inventory.
- Build a YOLO26 TensorRT engine on the Jetson through central model lifecycle
  jobs and register a target-specific runtime artifact.
- Create a deterministic detection/history/incident/evidence fixture that can
  run on a fresh stack and produce reviewable Evidence/Incidents content.
- Generate real tenant-scoped billing usage and invoice data tied to the
  deterministic fixture and live edge/link objects.
- Enable the master UDP reflector with real secret state and run an authenticated
  UDP sequence probe from an edge-agent source.
- Produce a final smoke report that clearly labels every lane as `PASS`, `FAIL`,
  `BLOCKED`, or `NOT RUN`.

## Non-Goals

- No global Docker prune or unrelated Docker cleanup.
- No deletion of `/var/lib/vezor/models` or model artifacts during reset.
- No arbitrary remote shell from central to edge.
- No registering TensorRT `.engine` files as primary camera models.
- No storing raw admin passwords, RTSP credentials, bearer tokens, bootstrap
  tokens, node credentials, or reflector secrets in reports or git.
- No broad FleetOps rewrite. FleetOps should consume generated real data through
  the existing APIs and UI.

## Status Semantics

- `PASS`: the lane was exercised on the fresh stack and evidence proves the
  expected behavior.
- `FAIL`: the lane was exercised and product behavior was wrong.
- `BLOCKED`: the lane could not be exercised because external access, hardware,
  credentials, model files, or required infrastructure were unavailable.
- `NOT RUN`: the lane was intentionally skipped and the report explains why.

The smoke harness and final report must keep these statuses distinct. Missing
Jetson access, missing RTSP source, missing reflector secret access, missing
billing usage, missing deterministic evidence, and missing fresh-stack proof are
never passes.

## Closure Lanes

### Fresh Reset And First-Run Proof

The reset must remove installed master DB/config/secret state while preserving
model artifacts. After reinstall, first-run must generate and bind the central
supervisor credential from scratch.

Acceptance:

- no Vezor validation containers or volumes survive the targeted reset.
- `/etc/vezor/secrets/central_supervisor_credential` did not exist before the
  reinstall and exists afterward.
- `/var/lib/vezor/credentials/supervisor.credential` matches the generated
  central credential file without exposing the material.
- bootstrap status reports `first_run_required=false`.
- central deployment node reports `credential_status=active`.
- central supervisor posts service reports and runtime reports without manual
  repair.

### Real Jetson Supervisor/API Sync And Inventory

The Jetson validation must use a real paired edge node, not an emulated node.
Central owns desired state; the Jetson supervisor polls bounded jobs and reports
inventory.

Acceptance:

- the Jetson is paired with an active node credential.
- support bundle includes Jetson service, hardware, runtime, and inventory
  diagnostics.
- model assignments for YOLO26n and YOLO26s are visible on the Jetson node.
- model sync job events show accepted, running, and succeeded states from the
  Jetson supervisor.
- `GET /api/v1/deployment/nodes/{node_id}/model-inventory` contains synced
  model paths, hashes, sizes, and target profile evidence.

### TensorRT Build On Jetson

TensorRT engines must be built on the target Jetson or a build host explicitly
matching the target profile. For this closure, use the Jetson. The central UI/API
creates an artifact build job; the Jetson supervisor runs the builder and
reports the artifact payload.

Acceptance:

- the Jetson has `trtexec` or an equivalent TensorRT builder available.
- the supervisor runner wires a real TensorRT builder into
  `SupervisorModelJobExecutor`.
- the job result creates a `ModelRuntimeArtifact` with
  `kind=tensorrt_engine`, `runtime_backend=tensorrt_engine`,
  `target_profile=linux-aarch64-nvidia-jetson`, valid hash, size, source model
  hash, input shape, precision, and runtime versions.
- runtime admission and worker configuration prefer the TensorRT artifact on
  compatible Jetson camera assignments, and fall back honestly if the artifact
  is absent or invalid.

### Deterministic Detection, History, Incident, And Evidence Fixture

The smoke needs a deterministic fixture because the real Office camera may not
produce a useful incident during a short validation run. The fixture should be
explicitly invoked and clearly labeled as smoke fixture data.

Acceptance:

- one deterministic `tracking_events` row appears for the selected camera and a
  stable class such as `person`.
- History endpoints return a non-empty datapoint for that camera.
- one deterministic incident appears in `/api/v1/incidents`.
- incident scene contract, privacy manifest, runtime passport, ledger, and
  artifact content endpoints return data.
- Evidence/Incidents UI can open and review the incident.
- fixture data is idempotent by a stable smoke run id, so rerunning the fixture
  updates or reuses the same smoke records instead of creating uncontrolled
  duplicates.

### Real Billing Usage

Billing validation must create actual tenant-scoped billing records through the
existing billing baseline. It may use deterministic fixture usage when the
source object is clearly tied to the smoke incident, evidence export, Jetson
node, or link probe.

Acceptance:

- billing node, account, entitlement, price book, usage, and invoice run are
  created and retrievable through `/api/v1/billing/*`.
- usage includes at least `evidence_pack_export` and `managed_edge_node`.
- link usage such as `managed_link_gb` is recorded when a real link probe or
  deterministic fixture source object exists.
- FleetOps billing UI shows non-empty usage and invoice data.
- the final report distinguishes product-generated live usage from deterministic
  smoke fixture usage.

### Master Reflector Secret Distribution And UDP Edge-Agent Probe

The master reflector already has persisted profile intent and a UDP listener.
Closure requires an edge-agent source to obtain the reflector secret safely and
post a real UDP sequence sample.

Acceptance:

- the master reflector profile reports `enabled=true` and
  `secret_state=present`.
- the backend binds UDP `8622` and records no reflector startup error.
- a supervisor-scoped or one-time admin-issued edge-agent config path returns
  reflector address, port, key id, target id, and secret only to an authorized
  edge/admin flow.
- raw reflector secret is never present in `GET /api/v1/link/reflectors/master`,
  site summaries, support bundles, logs, or final reports.
- `python3 -m argus.link.edge_agent --method udp_sequence --once` succeeds from
  an edge source and posts a sample to
  `/api/v1/link/sites/{site_id}/probe-targets/{target_id}/edge-samples`.
- Link Performance shows packet counts, loss, RTT metadata, and target site
  linkage.

## Product Boundaries

- `Vezor Master` remains a protected control-plane target. It can receive
  edge-originated samples and host the optional reflector, but it is not a normal
  camera/deployment site and should not own the Office scene.
- `Office` or another physical/operator site owns the real RTSP camera and
  Jetson edge node.
- TensorRT artifacts are runtime artifacts attached to source ONNX model rows.
- The deterministic fixture is an explicit smoke tool, not an always-on
  production automation.

## Security And Audit Requirements

- Any raw secret returned to an edge-agent or supervisor must be returned only
  over an authenticated path and never through normal viewer responses.
- The smoke report may show secret state, key id, and redacted URLs, but not raw
  material.
- Fixture-created incidents, artifacts, billing usage, and link samples must be
  labeled with `metadata.smoke_run_id` or equivalent payload context for audit.
- Support bundles must redact token-like and credential-like values.

## Test Strategy

- Unit tests prove status semantics, redaction, fixture idempotency, TensorRT
  builder command construction, secret distribution authorization, and billing
  usage creation.
- API tests prove fixture data is visible through History, Incidents, Evidence,
  Billing, FleetOps, Deployment, and Link endpoints.
- Supervisor tests prove model sync, inventory, TensorRT build jobs, and edge
  configuration reconciliation.
- Live smoke proves the same paths on the fresh installed stack and the real
  Jetson.

## Final Report Contract

The final report belongs in:

```text
docs/superpowers/status/YYYY-MM-DD-whole-product-live-smoke-closure-report.md
```

It must include the pass/fail matrix from the handoff and explicit evidence for:

- reset proof;
- first-run/auth/tenant claims;
- central supervisor credential binding;
- real Jetson sync/inventory;
- TensorRT build;
- Office RTSP native and annotated live;
- deterministic history/incident/evidence;
- billing usage/invoice/FleetOps billing;
- reflector secret distribution;
- real UDP edge-agent probe;
- Core Link master target-only behavior;
- docs/deployment posture.
