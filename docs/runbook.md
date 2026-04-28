# Vezor Runbook

See also:

- [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md)
- [operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md)

## Worker Lifecycle And Operations

The Operations workbench currently lives at `/settings` in the frontend. It is the operator-facing view for fleet state, camera worker ownership, delivery diagnostics, edge bootstrap material, and copyable local-dev worker commands.

Local development can still start workers from a shell because there is no local supervisor process yet. Use the Operations copy button or the lab guide commands so the token fetch, API URL, database URL, NATS URL, and MinIO settings stay in sync with the current dev stack.

Production start, stop, restart, and drain actions must be supervisor-backed. The intended path is: UI action -> backend desired-state or lifecycle request -> central or edge supervisor reconciles the worker process on the correct node -> worker heartbeat/runtime reports truth back to Operations. The API must not become a generic remote shell.

## Production Topology

The supported production shape is not the local Docker Compose dev stack.

Run production as:

- Linux `amd64` master / HQ node
  - frontend
  - FastAPI backend
  - PostgreSQL/TimescaleDB
  - Keycloak
  - Redis
  - NATS JetStream
  - MinIO
  - MediaMTX
  - observability stack
  - central supervisor for central/hybrid workers
- Jetson Orin Nano Super 8 GB edge node where local inference is required
  - edge supervisor
  - inference worker service/container
  - local MediaMTX
  - NATS leaf
  - OTEL collector
- Tailscale or WireGuard between HQ and sites

An iMac can be used as a lab or pilot master, especially with a Jetson edge node, but production should move the master role to Linux with backups, TLS, real OIDC configuration, and supervisor-owned workers.

## Current Production Gaps

Before calling a deployment production-ready, verify that the following are implemented or supplied by the deployment platform:

- supervisor-backed Start/Stop/Restart/Drain for central and edge workers
- per-worker heartbeat with camera id, status, freshness, restart count, and last error
- persistent assignment/reassignment model or an equivalent supervised placement source
- backup and restore for Postgres/TimescaleDB and incident object storage
- TLS termination and stable DNS
- scoped edge credentials with a rotation path
- log and metric collection from both master and edge nodes
- soak testing for the first site before adding more cameras

The current Operations page should render unknown runtime precision honestly as `not_reported`, `unknown`, `stale`, or `offline`. Do not treat missing heartbeat detail as proof that a worker is running.

## Incident Evidence And Review

The Evidence Desk at `/incidents` reviews incidents that the worker pipeline already captured. It does not create new recordings or run a separate matching engine.

Current behavior:

- incident clips are captured by `IncidentClipCaptureService`
- `clip_url` is the primary evidence artifact today
- `snapshot_url` is supported by API/UI but may be null
- review state is persisted as `pending` or `reviewed`
- operator review/reopen actions write audit entries

If a still preview is required for a deployment, add snapshot generation as a separate feature rather than assuming every incident row has one.

## Secrets With SOPS And Age

Vezor stores operational secrets under `/Users/yann.moren/vision/infra/secrets/` as encrypted `*.enc.yaml`, `*.enc.json`, or `*.enc.env` files. The repository is configured for SOPS + age through `/Users/yann.moren/vision/.sops.yaml`.

Before the first production deployment:

1. Generate an age keypair on an operator workstation: `age-keygen -o ~/.config/sops/age/keys.txt`.
2. Replace the bootstrap recipient in `/Users/yann.moren/vision/.sops.yaml` with the real team recipient or recipients.
3. Export `SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt`.
4. Create encrypted secret material with `sops infra/secrets/<name>.enc.yaml`.

Recommended secret sets:

- central platform secrets: database password, MinIO credentials, RTSP encryption key, MediaMTX JWT key
- auth secrets: Keycloak admin bootstrap secret and confidential client secrets
- edge secrets: edge node API keys, NATS credentials, remote bootstrap tokens

## Secret Rotation Procedure

Use this sequence when rotating any production secret set:

1. Generate a fresh age recipient and update `/Users/yann.moren/vision/.sops.yaml`.
2. Re-encrypt every tracked secret file with `sops updatekeys infra/secrets/*.enc.yaml`.
3. Rotate the live runtime secret in the backing service first:
   - Postgres user password
   - MinIO root credentials
   - Keycloak client secrets
   - `ARGUS_RTSP_ENCRYPTION_KEY`
   - MediaMTX JWT signing key
   - edge API keys or NATS credentials
4. Roll the central workloads, verify `/healthz`, `/metrics`, login, and stream authorization.
5. Roll edge workers after central verification succeeds.
6. Revoke the previous secret material and remove the old age private key from operator workstations.

## Jetson Orin Nano Super 8 GB Bootstrap

Before starting the edge stack on Jetson Orin Nano Super 8 GB, enable the 25 W Super mode:

```bash
sudo nvpmodel -m 2 && sudo jetson_clocks
```

Then run the local preflight:

```bash
/Users/yann.moren/vision/scripts/jetson-preflight.sh
```

The preflight checks JetPack 6.2, CUDA 12.6, TensorRT 10.x, NVDEC availability, the expected lack of NVENC on Orin Nano, Docker, and `nvidia-container-toolkit`.

## Edge Bring-Up

For a single-node edge deployment:

1. Place the edge model weights under `/Users/yann.moren/vision/models/`.
2. Export the required HQ bootstrap values:
   - `ARGUS_API_BASE_URL`
   - `ARGUS_API_BEARER_TOKEN` or supervisor-provisioned edge credential
   - `ARGUS_EDGE_CAMERA_ID`
   - `ARGUS_NATS_URL` if the default leaf upstream does not match your HQ
3. Start the stack with `docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml up -d`.
4. Confirm MediaMTX, OTEL Collector, the worker metrics endpoint, and the Operations workbench state are reachable.

This Compose path is appropriate for lab and pilot bring-up. In production, the same edge responsibilities should be run under a supervisor so they restart after reboot, report per-worker status, and can receive constrained lifecycle requests from the control plane.

## Model Metadata And Scope

`/Users/yann.moren/vision/models/` is only where local model files live; it does not define semantic class scope by itself. In local Docker development, the backend bind-mounts this checkout's `models/` path so registration-time ONNX validation can read the same absolute host path that host-side workers use later. When an ONNX model exposes embedded class metadata, treat that as the source of truth for registration and runtime inventory. Use `Camera.active_classes` only to narrow the operational scope. Custom reduced-class models remain an advanced optional path.

The current branch also includes detector capability contracts for `fixed_vocab` and `open_vocab`, runtime vocabulary persistence, vocabulary snapshots, and capability-aware query commands. Treat this as the control-plane foundation for open-vocabulary detection. A true open-vocabulary model backend should still be validated separately on the target central and Jetson runtimes.

## Authentication Alternative

Keycloak is the default IdP. If an operator standardizes on Authentik instead, keep the same OIDC contract at the SPA and API layers, update the issuer and JWKS configuration, and record the deployment-specific divergence in a new ADR before rollout.
