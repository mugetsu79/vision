# Docs, No-DeepStream Optimization, DeepStream Plan, And Worker Performance Handoff

Date: 2026-06-10
Branch: `codex/sceneops-pack-registry`
Last completed docs/spec commit before this handoff update: `47c4b105`

## Purpose

The next chat should pick up from the committed documentation refresh, the
optional Jetson DeepStream edge-runtime design, and the newer no-DeepStream
Jetson optimization path. It should also continue from the current worker
performance observation: the active Jetson worker is running, but the path is
CPU-heavy in media decode/encode, while the central Docker worker on the MacBook
Pro M4 is CPU-only today.

Use Superpowers. For implementation work, read the relevant spec/plan first,
write failing tests before code changes, and verify before claiming pass.

## Current Branch State

Start with:

```bash
cd /Users/yann.moren/vision
git fetch origin codex/sceneops-pack-registry
git status --short --branch
git log -3 --oneline
```

Expected branch: `codex/sceneops-pack-registry`.

Commit `ddb67478` was pushed to `origin/codex/sceneops-pack-registry` with:

- product documentation index
- Vezor user guide with sanitized screenshots
- full installation guide
- admin and operations guide
- first release notes
- updates to README, runbook, installer docs, model guide, Core Link guide, and
  operator playbook
- DeepStream Jetson edge installer design spec
- DeepStream Jetson edge installer implementation plan

Commit `47c4b105` was pushed after that with:

- this handoff
- DeepStream handoff additions
- Jetson worker performance snapshot

Current session changes after `47c4b105`:

- Central supervised state fix in `backend/src/argus/services/app.py`
- Regression in `backend/tests/services/test_operations_service.py` proving
  central-supervisor fleet rows are `supervised`, not `manual`
- Regression in `backend/tests/supervisor/test_runner.py` proving a running
  central worker without an assignment row still refreshes runtime reports
- Spec/plan updates making the current no-DeepStream Jetson optimization path
  the immediate next implementation target before the optional DeepStream lane

This workspace still has unrelated local untracked scratch files and folders
such as `.claude/`, `.codex/`, `.playwright-*`, `.superpowers/brainstorm/...`,
old screenshots, strategy drafts, `output/`, and `taste-skill/`. Do not stage
them. Use explicit `git add -- path ...`; do not use `git add -A`.

## Read First

1. `docs/superpowers/specs/2026-06-10-jetson-deepstream-edge-installer-design.md`
2. `docs/superpowers/plans/2026-06-10-jetson-deepstream-edge-installer-implementation-plan.md`
3. `docs/README.md`
4. `docs/vezor-user-guide.md`
5. `docs/full-installation-guide.md`
6. `docs/admin-and-operations-guide.md`
7. `docs/release-notes/2026.1.md`
8. `docs/model-loading-and-configuration-guide.md`
9. `docs/core-link-performance-guide.md`
10. `docs/product-installer-and-first-run-guide.md`
11. `docs/operator-deployment-playbook.md`
12. `docs/runbook.md`
13. `README.md`

## DeepStream Design State

Research and design are complete; implementation has not started.

The plan now has two implementation tracks:

1. Optimize the current `python` Jetson runtime without DeepStream.
2. Add the optional `deepstream` runtime family after the narrower path is
   measured.

The no-DeepStream path should be implemented first because current live evidence
shows the Orin has TensorRT/CUDA providers and Jetson media plugins, but the
active worker is CPU-heavy in RTSP/H.264 decode, raw frame transfer, and preview
encode.

The chosen design is an optional second Jetson edge runtime family:

- default remains `python`
- new opt-in runtime family is `deepstream`
- new image key: `edge-worker-deepstream`
- new Dockerfile: `backend/Dockerfile.edge.deepstream`
- new runtime artifact kind: `deepstream_bundle`
- new runtime backend: `deepstream_tensorrt`
- first supported target: DeepStream 7.1 on JetPack 6.1 / L4T 36.4
- JetPack 6.2 / L4T 36.5 is candidate-only until live smoke proves it
- DeepStream 9.0 is future JetPack 7.x work, not the first Orin lane

Do not treat a plain TensorRT `.engine` as enough for DeepStream. The bundle
must include engine, labels, `nvinfer` config, parser shared library, pipeline
template, and ABI/version metadata.

## Fix Applied In This Session

Problem:

- The central worker UI showed `MANUAL` while also saying Central Supervisor
  owns the process.
- The central worker had no `worker_assignments` row, so the fleet summary kept
  `desired_state=manual`.
- Because the supervisor poller only heartbeats workers whose desired state is
  `desired` or `supervised`, runtime reports could stop refreshing after a
  manual restart even though the process was running.

Change:

- `OperationsService.get_fleet_overview` now promotes central workers to
  `WorkerDesiredState.SUPERVISED` when operations mode resolves to
  `central_supervisor` and supervisor mode is enabled.
- Manual and disabled-supervisor modes stay manual/disabled.

Verification:

```bash
backend/.venv/bin/pytest backend/tests/services/test_operations_service.py \
  -k "central_start_when_supervisor_hardware_is_fresh"
backend/.venv/bin/pytest backend/tests/supervisor/test_runner.py \
  -k "refreshes_runtime_report_for_already_running_worker or refreshes_central_runtime_report_without_assignment or recovers_desired_worker_from_unknown_running_report_after_restart"
backend/.venv/bin/pytest backend/tests/supervisor/test_reconciler.py \
  -k "recovers_desired_worker_after_restart"
```

All three focused verification runs passed.

## Current No-DeepStream Optimization Findings

Jetson EDGE after the user changed scene settings:

- Host: `orin1`, address used: `192.168.1.203`, SSH user `ai-user`
- 5-sample window: 2026-06-10 08:07:08 to 08:07:36 UTC
- `vezor-supervisor` CPU samples: about 185%, 211%, 222%, 216%, 259%
- `vezor-supervisor` memory: about 1.56 GiB of 7.43 GiB
- Sanitized process breakdown:
  - supervisor runner Python: about 0.5% CPU
  - inference Python: about 48% CPU
  - GStreamer media process: about 90% CPU
  - FFmpeg preview process: about 36% CPU
- `tegrastats`: RAM about 2685 to 2700 MiB of 7607 MiB, GR3D mostly 0%,
  temperatures about 51 C to 52 C
- Inside the edge container, ONNX Runtime providers include
  `TensorrtExecutionProvider`, `CUDAExecutionProvider`, and
  `CPUExecutionProvider`
- PyTorch CUDA is available
- GStreamer plugin check:
  - `nvv4l2decoder`: present
  - `nvvidconv`: present
  - `nvv4l2h264enc`: present
  - `nvvideoconvert`: missing
  - `omxh264dec`: missing
  - `avdec_h264`: present
  - `x264enc`: present

Interpretation:

- No-DeepStream optimization is possible and should target hardware
  decode/resize/encode in the existing Python runtime.
- The current logs can mislabel a software GStreamer fallback as native; fix
  this before measuring PASS/FAIL.
- Expected win is lower decode/resize/encode CPU and visible NVIDIA media/GPU
  activity, not full DeepStream zero-copy batching.

Central reference after the central worker was restarted:

- Host: MacBook Pro M4 running the central stack in Linux Docker containers
- `vezor-master-vezor-supervisor-1` CPU samples averaged about 281%
- Process breakdown showed Python inference about 264% CPU and FFmpeg about 9%
- ONNX Runtime providers inside the central container were
  `AzureExecutionProvider` and `CPUExecutionProvider`
- Runtime policy selected `CPUExecutionProvider`

Interpretation:

- Central can be optimized, but the current Linux Docker mode on MacBook Pro M4
  is CPU-only.
- Apple GPU/Neural Engine acceleration requires a separate native macOS
  supervisor/worker lane that can probe and use CoreML outside Docker.
- Until that lane exists and is live-smoked, central M4 GPU acceleration is
  NOT RUN/BLOCKED, not PASS.

## Known UI Runtime Display Issue

The central scene's Models & Tracking step can show a valid Jetson TensorRT
artifact because the model option currently summarizes all runtime artifacts on
the shared model row. It does not scope the artifact summary by selected scene
target/profile.

This is display scoping, not proof the central Docker worker used TensorRT. The
latest central runtime evidence selected ONNX Runtime CPU.

Next fix should filter runtime artifact display by processing mode, assigned
node, target profile, and selected provider.

## Registry Publishing Todo

Future packaging/release work is BLOCKED until a registry target and credentials
are provided.

Needed inputs:

- registry host and namespace, for example GHCR, Docker Hub, or a private
  registry
- repository/image names for master backend, frontend, and edge images
- authentication method, preferably an existing local `docker login` session or
  local-only token file/environment variable
- tag policy, such as branch SHA, release candidate, `portable-demo`, or stable
  release tag

Once available, rebuild and publish the master and edge images from the final
committed branch. Do not rely on live container hot patches for closure.

## Central Runtime Status Recommendation

Central-supervisor-owned cameras should not emit `runtime_status=running` from
central node health alone. A healthy central supervisor proves the control
process is alive; it does not prove a specific camera worker is running.

Recommended behavior:

- Fleet rows should show `desired_state=supervised` when operations mode assigns
  the scene to the central supervisor.
- `runtime_status=running` should require a fresh per-camera runtime report from
  the worker/supervisor poll loop.
- If no per-camera runtime report exists, keep `runtime_status=not_reported`
  and improve UI copy to `awaiting first heartbeat` or equivalent.
- If a report exists but is stale, show stale/unknown rather than running.
- Keep central node health visible separately from per-camera worker runtime
  health.

## Current Jetson Worker Performance Snapshot

Sample window: 2026-06-10 07:48:47 to 07:49:58 UTC.

Host:

- Jetson hostname: `orin1`
- Jetson address used: `192.168.1.203`
- Master API host observed in edge-agent config: `192.168.1.166`
- SSH key auth worked as `ai-user`
- sudo was not needed for the performance commands below

Containers observed:

- `vezor-supervisor`: `vezor/edge-worker:portable-demo`, up 11 hours, healthy
- `vezor-edge-agent`: `vezor/edge-worker:portable-demo`, up 2 hours
- `vezor-edge-nats-leaf`: `nats:2`, up 11 hours, healthy
- `vezor-edge-mediamtx`: `bluenviron/mediamtx:latest`, up 11 hours

Active inference worker:

- module: `argus.inference.engine`
- camera id: `819b9bdb-9ec2-4ea5-b4f5-1c1361bedd07`

Docker stats over six samples:

- `vezor-supervisor`: 217% to 316% CPU, average about 239% CPU
- `vezor-supervisor` memory: 1.576 GiB to 1.631 GiB of 7.429 GiB
- `vezor-supervisor` PIDs: 56 to 57
- `vezor-edge-mediamtx`: 1.57% to 3.19% CPU, roughly 85 MiB to 97 MiB
- `vezor-edge-agent`: 0% CPU, about 84 MiB
- `vezor-edge-nats-leaf`: about 0.3% to 0.5% CPU, about 51 MiB

Sanitized process breakdown inside `vezor-supervisor`:

- supervisor runner: about 0.5% CPU, 129 MiB RSS
- Python inference engine: about 47% CPU, 1.27 GiB RSS
- GStreamer RTSP/H.264 decode and raw BGR pipe process: about 90% CPU
- FFmpeg preview encoder process: about 50% CPU

Do not paste the raw process-argument output into docs. It contained raw RTSP
credentials and a MediaMTX publish JWT. Use sanitized commands below.

Jetson `tegrastats` snapshot:

- RAM: about 2707 to 2733 MiB of 7607 MiB
- swap: 697 MiB of 3804 MiB
- CPU: several active cores, frequently at 729 to 1728 MHz
- GR3D/GPU: mostly 0%, one brief 7% sample
- temperatures: roughly 50.9 C to 52.6 C
- power: roughly 5.0 W to 7.3 W during the sample

Interpretation:

- The current worker is CPU-bound on software video decode/resize and software
  x264 preview encoding.
- The Jetson GPU is not saturated and is mostly idle in this sample.
- This reinforces the value of either hardware-accelerating the current
  GStreamer/FFmpeg path or implementing the optional DeepStream lane.
- Memory is stable for the short sample; there is no immediate thermal issue.

## Safe Monitoring Commands

Use commands that avoid dumping process arguments with secrets:

```bash
ssh -o BatchMode=yes ai-user@192.168.1.203 \
  'docker stats --no-stream --format "{{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}} mempct={{.MemPerc}} pids={{.PIDs}}"'
```

```bash
ssh -o BatchMode=yes ai-user@192.168.1.203 \
  'docker top vezor-supervisor -eo pid,ppid,pcpu,pmem,rss,etime,comm'
```

```bash
ssh -o BatchMode=yes ai-user@192.168.1.203 \
  'timeout 12s tegrastats --interval 1000'
```

If full process args are required for debugging, keep that output local only,
redact RTSP credentials and JWTs immediately, and do not commit it.

## Recommended Next Work

1. Execute Task 0 in the implementation plan first: optimize the current
   no-DeepStream Jetson Python runtime media path with failing tests, then live
   smoke it on the Orin.
2. Fix the runtime artifact display scoping so central scenes do not show a
   Jetson TensorRT artifact as the effective central runtime.
3. Add a clearer central worker `awaiting first heartbeat` UI/API presentation
   for supervised cameras that do not yet have a per-camera runtime report.
4. Keep central M4 acceleration as a native macOS/CoreML design lane until a
   native worker exists; do not claim Dockerized central GPU acceleration.
5. Provide registry target/credentials, then rebuild and publish master/edge
   images from the final committed branch.
6. If the user wants DeepStream implementation, execute the DeepStream tasks
   with `superpowers:subagent-driven-development` or
   `superpowers:executing-plans`.
7. For any worker performance change, write a regression/performance smoke that
   captures CPU, memory, GR3D, frame rate, and stream availability before and
   after the change.
8. Do not mark DeepStream, TensorRT, billing, evidence, RTSP, or fresh-stack
   behavior as PASS without live evidence.

## Secrets And Safety

Do not commit or paste:

- raw RTSP URLs with credentials
- admin passwords
- sudo passwords
- bearer tokens
- bootstrap tokens
- node credentials
- reflector secrets
- MediaMTX publish JWTs
- NGC credentials

Use environment variables or local-only secret files outside git. If a required
secret is missing, report `BLOCKED` with the missing secret class, not the
secret value.
