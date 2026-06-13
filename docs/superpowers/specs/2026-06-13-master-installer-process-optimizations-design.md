# Master Installer Process Optimizations Design

Date: 2026-06-13
Branch: `codex/sceneops-pack-registry`
Scope: Bare-metal Linux/macOS master/control-plane installer process only.

## Goal

Make the bare-metal Linux and macOS master installers easier to rerun,
diagnose, and release-harden without changing the edge installer or
EVE-OS edge VM image work.

This is a process optimization spec, not a master appliance redesign.
The master remains a systemd-owned Linux appliance and a launchd-owned
macOS pilot/demo appliance. Both still run the existing Docker Compose
master stack.

## Non-Goal Summary

This spec does not:

- change the EVE-OS edge VM packaging design;
- add the edge worker image matrix to the master installer;
- implement DeepStream;
- claim central Dockerized GPU or Apple M-series acceleration;
- introduce a new remote-shell control plane;
- change first-run tenant or platform bootstrap contracts;
- rotate or expose secrets in logs, dry-run output, or status output.

## Current Installer Status

The current master installers already provide the main product-mode
shape:

- `bin/vezor install master` delegates to the Linux or macOS master
  installer for the current host.
- Linux master is systemd-owned through `vezor-master.service`.
- macOS master is launchd-owned through `com.vezor.master`.
- Both installers resolve image references from the release manifest.
- Dev manifests build local backend and frontend images before service
  startup.
- The installers write `/etc/vezor/master.json`,
  `/etc/vezor/supervisor.json`, `/etc/vezor/master.env`, local secret
  files, NATS config, MediaMTX config, bundled models, and the link
  throughput payload.
- The master Compose profile provides Postgres, Redis, NATS, MinIO,
  Keycloak, MediaMTX, backend, frontend, and the central supervisor.
- Central worker CPU/thread caps are already exposed through Compose
  environment defaults.

The useful remaining work is reliability and supportability:

- clearer preflight output;
- safer reruns and reconfiguration;
- stricter release-manifest behavior;
- less duplicated Linux/macOS installer logic;
- better post-start health gating;
- documented central CPU tuning;
- tests that prove the installer does not leak secrets or raw process
  arguments.

## Recommended Approach

Use an incremental process optimization layer:

1. Keep the existing Linux and macOS shell entrypoints.
2. Extract shared validation and rendering behavior into small tested
   installer helpers.
3. Add explicit installer modes for preflight, install, and
   reconfigure.
4. Harden manifest image resolution for production releases.
5. Add bounded post-start health checks and redacted diagnostics.

This keeps the current installer shape, but removes the most fragile
operator experience points.

## Architecture

### Entry Points

Keep:

- `installer/linux/install-master.sh`
- `installer/macos/install-master.sh`
- `bin/vezor install master`

Add shared helpers under the installer tree:

```text
installer/
├── lib/
│   └── master_install_common.sh
└── vezor_installer/
    ├── master_manifest.py
    ├── master_preflight.py
    └── master_health.py
```

The shell entrypoints still own privileged host actions such as writing
systemd/launchd files and starting services. Python helpers own
structured parsing, validation, and redacted reporting where shell
string handling is brittle.

### Installer Modes

Add three explicit modes:

```bash
sudo ./bin/vezor install master --mode install --public-url http://MASTER_HOST:3000
sudo ./bin/vezor install master --mode preflight --public-url http://MASTER_HOST:3000
sudo ./bin/vezor install master --mode reconfigure --public-url http://MASTER_HOST:3000
```

Default mode remains `install` for compatibility.

Mode behavior:

| Mode | Behavior |
|---|---|
| `preflight` | validates host, manifest, ports, disk, Docker/Compose, URL shape, and required files; writes nothing |
| `install` | current first install behavior; fails if non-Vezor services own required ports |
| `reconfigure` | stops the existing Vezor master service if present, preserves data/secrets/supervisor id, rewrites non-secret config/env, restarts, and runs health checks |

Do not add a broad `upgrade` mode until release artifact replacement
and rollback semantics are designed. `reconfigure` is intentionally
limited to the installed checkout currently pointed at
`/opt/vezor/current`.

## Preflight Optimizations

Both Linux and macOS preflight should report:

- OS and architecture support;
- Docker or Podman availability where supported;
- Docker daemon readiness;
- Docker Compose v2 availability;
- required command availability;
- required port availability;
- whether a required port is owned by an existing Vezor service;
- disk space for images, Postgres, MinIO evidence, models, and logs;
- write access to configured config/data/log directories;
- public URL parse result and derived backend/Keycloak origins;
- release manifest presence and schema validity.

Diagnostics must not print:

- secrets;
- bearer tokens;
- bootstrap tokens;
- raw process command lines;
- raw environment values that may contain credentials.

For port owners, report process name and PID only when available. Do
not print full process arguments.

## Reconfigure Safety

Linux currently checks ports before starting the systemd service. That
is correct for first install but awkward for reruns when the existing
Vezor service owns those ports. macOS already stops the existing launchd
job and containers before checking ports.

The new behavior:

- In `install` mode, fail if required ports are already in use.
- In `reconfigure` mode, stop the existing Vezor service first, then
  recheck ports.
- If a required port is still owned by a non-Vezor process, fail with a
  redacted owner summary.
- Preserve existing secrets if present.
- Preserve existing `supervisor_id`.
- Rewrite `master.env`, `master.json`, `supervisor.json`, NATS config,
  and MediaMTX config from the selected options.
- Do not purge or recreate data volumes.
- Do not run global Docker prune or delete unrelated Docker resources.

Config writes should use temp files and atomic rename where practical.
Secret files should not be backed up automatically because backups can
create extra credential copies.

## Release Manifest Hardening

Current behavior uses fallback image tags when no manifest entry exists.
That is acceptable for dev but too loose for production.

Define manifest policy by `release_channel`:

| Release channel | Missing image key behavior | Reference policy |
|---|---|---|
| `dev` or no manifest | allow local fallback tags and local image builds |
| `pilot` | require all product images to be present; warn if references are mutable tags |
| `stable` | require all product images to be present and immutable by digest or approved release tag |

Required master image keys:

- `postgres`
- `redis`
- `nats`
- `minio`
- `keycloak`
- `mediamtx`
- `backend`
- `frontend`
- `supervisor` or explicit reuse of `backend`

Manifest validation should run in `preflight`, `install`, and
`reconfigure` modes before image pulls/builds or service changes.

## Shared Helper Extraction

Linux and macOS currently duplicate logic for:

- manifest image resolution;
- release channel parsing;
- public URL parsing;
- OIDC PKCE decision;
- supervisor id preservation;
- link throughput payload creation;
- secret writing patterns;
- local image build sequencing.

Move the lowest-risk shared logic first:

1. Manifest parsing and validation into `master_manifest.py`.
2. Public URL normalization into `master_preflight.py`.
3. Redacted port and host diagnostics into `master_preflight.py`.
4. Health checks into `master_health.py`.

Keep OS-specific service-manager operations in shell:

- systemd unit install/start/stop on Linux;
- launchd plist install/bootstrap/bootout on macOS;
- Docker Desktop permission handling on macOS.

## Post-Start Health Gate

After starting the master service, run a bounded health gate:

1. Wait for backend `/healthz`.
2. Wait for frontend HTTP response.
3. Wait for Keycloak reachable at the derived public origin.
4. Wait for the central supervisor healthcheck to pass.
5. Report service status summary.

The health gate should have a clear timeout and print next commands for
local diagnosis, such as service status and installer validate commands.
It must not dump container logs automatically because logs can contain
credentials or raw process details.

## Central Worker CPU Tuning

Master installers should document and optionally write CPU tuning
defaults for central workers. The existing Compose surface already
supports:

- `VEZOR_WORKER_OMP_NUM_THREADS`
- `VEZOR_WORKER_OPENBLAS_NUM_THREADS`
- `VEZOR_WORKER_MKL_NUM_THREADS`
- `VEZOR_WORKER_NUMEXPR_NUM_THREADS`
- `VEZOR_WORKER_OPENCV_THREADS`
- `VEZOR_WORKER_INFERENCE_SESSION_INTER_OP_THREADS`
- `VEZOR_WORKER_INFERENCE_SESSION_INTRA_OP_THREADS`
- `VEZOR_CPU_FALLBACK_PROCESSING_FPS_CAP`

Add documentation and optional installer flags only for CPU-safe
settings:

```text
--central-worker-cpu-fps-cap N
--central-worker-intra-op-threads N
--central-worker-inter-op-threads N
```

These flags write `VEZOR_*` values into `master.env`. They do not
claim or configure central GPU, M-series, CUDA, OpenVINO, TensorRT, or
DeepStream acceleration.

## CLI And Output Contract

Add or refine user-facing commands:

```bash
./bin/vezor install master --mode preflight --public-url http://MASTER_HOST:3000
./bin/vezor install master --mode reconfigure --public-url http://MASTER_HOST:3000
./bin/vezor validate master
./bin/vezor status
```

Output should be concise and structured enough for support:

- PASS/WARN/FAIL rows for preflight checks;
- redacted paths and service names;
- explicit remediation for missing Docker daemon, port conflict, missing
  manifest image, bad public URL, and insufficient disk;
- no secrets, tokens, raw RTSP credentials, or raw process args.

## Files Touched

| File | Change |
|---|---|
| `installer/linux/install-master.sh` | add `--mode`, shared helper calls, Linux reconfigure flow, better preflight, post-start health gate |
| `installer/macos/install-master.sh` | add `--mode`, shared helper calls, aligned preflight, post-start health gate |
| `installer/lib/master_install_common.sh` | shared shell helpers for safe output, mode parsing glue, atomic writes where shell is appropriate |
| `installer/vezor_installer/master_manifest.py` | manifest validation and image resolution policy |
| `installer/vezor_installer/master_preflight.py` | URL, host, Docker, disk, and redacted port diagnostics |
| `installer/vezor_installer/master_health.py` | bounded post-start health checks |
| `installer/tests/test_linux_master_artifacts.py` | extend Linux installer artifact and safety assertions |
| `installer/tests/test_macos_master_artifacts.py` | extend macOS installer artifact and safety assertions |
| `installer/tests/test_master_manifest.py` | new manifest policy tests |
| `installer/tests/test_master_preflight.py` | new preflight and redaction tests |
| `installer/tests/test_master_health.py` | new health gate tests |
| `installer/README.md` | document installer modes and support-safe diagnostics |
| `docs/full-installation-guide.md` | document preflight/reconfigure flow and central CPU tuning |

## Acceptance Criteria

1. **Master preflight works on Linux and macOS artifacts.**
   Tests prove `--mode preflight` is accepted, writes nothing, validates
   manifest policy, reports required checks, and redacts process args.
2. **Linux reconfigure is safe.**
   Tests prove `--mode reconfigure` stops existing Vezor-owned services
   before port checks, preserves secrets and `supervisor_id`, rewrites
   config/env, and does not purge data.
3. **macOS reconfigure remains safe.**
   Tests prove launchd bootout/container stop behavior remains bounded,
   Docker Desktop permissions are preserved, and data is not purged.
4. **Manifest policy is enforced.**
   Dev manifests allow local fallback builds. Pilot/stable manifests
   require the product image keys. Stable manifests reject mutable
   references unless explicitly approved by policy.
5. **Post-start health gate is bounded.**
   Tests cover success, timeout, backend failure, frontend failure,
   Keycloak failure, and supervisor failure without dumping logs or
   secrets.
6. **Central CPU tuning is documented and optional.**
   Installer flags or documented env values populate `master.env` and
   Compose continues to pass them to the central supervisor.
7. **No accelerator claims are introduced.**
   Documentation and installer output do not claim central Dockerized
   GPU, M-series, CUDA, OpenVINO, TensorRT, DeepStream, or edge-image
   acceleration.
8. **No secret leakage.**
   Tests scan installer scripts, helper output fixtures, docs, and
   generated sample output for bearer tokens, bootstrap tokens, raw
   secrets, RTSP credentials, sudo passwords, and raw process args.
9. **Existing product install behavior remains compatible.**
   `bin/vezor install master --public-url ...` still works as the
   default install path.

## Test Plan

- Add unit tests for `master_manifest.py`:
  - dev fallback behavior;
  - pilot required keys;
  - stable immutable reference policy;
  - supervisor image reusing backend when configured.
- Add unit tests for `master_preflight.py`:
  - valid and invalid public URLs;
  - loopback vs non-loopback PKCE decision;
  - Docker daemon unavailable;
  - Docker Compose missing;
  - insufficient disk;
  - Vezor-owned port vs non-Vezor port;
  - redaction of process args and environment-like values.
- Add unit tests for `master_health.py`:
  - successful health gate;
  - each dependency timeout path;
  - output contains no secrets and no raw logs.
- Extend Linux installer artifact tests:
  - `--mode` appears in usage;
  - `reconfigure` stops existing Vezor master before port checks;
  - `install` does not stop unrelated services;
  - config writes are atomic where implemented;
  - existing `supervisor_id` preservation remains.
- Extend macOS installer artifact tests:
  - `--mode` appears in usage;
  - Docker Desktop readiness is checked;
  - launchd behavior is preserved;
  - data and credential permissions remain Docker Desktop-readable.
- Run targeted installer tests and shell syntax checks.

## Rollout Plan

1. Land tests for manifest policy, preflight redaction, mode parsing,
   and current installer behavior.
2. Implement shared Python helpers.
3. Wire Linux `--mode preflight` and `--mode reconfigure`.
4. Wire macOS `--mode preflight` and align reconfigure behavior.
5. Add post-start health gate behind a shared helper.
6. Update installer docs and full installation guide.
7. Run a local Linux dry-run and macOS dry-run.
8. Run one real master reconfigure on a lab host and capture evidence
   under `docs/superpowers/status/`.

## Out Of Scope

- Edge installer runtime profile work.
- EVE-OS VM build or qcow2 packaging.
- Edge worker image matrix implementation.
- DeepStream.
- Central Dockerized GPU/M4 acceleration.
- Kubernetes, Helm, or native service packaging redesign.
- Signed release artifact distribution.
- Fleet-wide master upgrade orchestration.
- Automatic log upload or support bundle upload.

## Open Questions

1. Should `--mode reconfigure` be the only rerun mode for now, or do we
   want a separate `--mode repair` that rewrites services without
   touching config?
2. Should stable manifest policy require digests for every image, or
   allow semver release tags from a trusted registry namespace?
3. What minimum free disk threshold should preflight enforce for pilot
   installs?
4. Should post-start health gate be mandatory in install mode, or
   configurable with `--skip-health-wait` for constrained lab hosts?
5. Should central CPU tuning flags be installer options, or should the
   docs only describe editing `master.env`?
