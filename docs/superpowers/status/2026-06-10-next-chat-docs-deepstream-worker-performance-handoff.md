# Docs, DeepStream Plan, And Jetson Worker Performance Handoff

Date: 2026-06-10
Branch: `codex/sceneops-pack-registry`
Last completed docs/spec commit before this handoff: `ddb67478`

## Purpose

The next chat should pick up from the committed documentation refresh and the
new optional Jetson DeepStream edge-runtime design. It should also continue from
the current Jetson worker performance observation: the active worker is running,
but the path is CPU-heavy and mostly not using Jetson GPU/GR3D.

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

1. If the user wants implementation, execute the DeepStream plan task-by-task
   with `superpowers:subagent-driven-development` or
   `superpowers:executing-plans`.
2. Before DeepStream, a narrower optimization option is to add hardware
   decode/resize/encode support to the current edge worker:
   `nvv4l2decoder`, `nvvidconv`/`nvvideoconvert`, and `nvv4l2h264enc`.
3. For any worker performance change, write a regression/performance smoke that
   captures CPU, memory, GR3D, frame rate, and stream availability before and
   after the change.
4. Do not mark DeepStream, TensorRT, billing, evidence, RTSP, or fresh-stack
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
