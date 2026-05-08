# Next Chat Handoff: Jetson Capture Tuning Next, UI Work After

Date: 2026-05-08

Purpose: paste this document into a fresh chat to continue from current `main`.
The next chat should keep optimizing the Jetson edge worker first, then move to
the OmniSight UI/UX work once the live pipeline is stable enough.

## Repository State

Start from `main` on both the iMac and Jetson:

```bash
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only origin main
git status -sb
git log --oneline -8
```

Expected:

- the performance and edge-runtime code is already merged through
  `93c93c99 fix(camera): use current ffmpeg rtsp timeout option`
- later docs-only commits may be above that optimization commit
- untracked local scratch files may exist; do not stage them unless the user
  explicitly asks

Last full verification before the docs cleanup:

- backend: `python3 -m uv run pytest -q` passed with 365 tests
- frontend unit: `corepack pnpm --dir frontend test` passed with 161 tests
- frontend build: `corepack pnpm --dir frontend build` passed
- known test noise: React `act(...)` warnings from `VideoStream.test.tsx`

## What Is Now Closed

These are not the next bottlenecks:

- model catalog and fixed/open-vocabulary runtime implementation
- iMac native-stream and processed-stream contracts
- edge MediaMTX relay from Jetson to iMac, including the missing `JETSON_IP`
  configuration issue that caused browser video to be unavailable
- Jetson edge image on Python 3.10 for cp310 ONNX Runtime GPU wheels
- Jetson provider selection with `TensorrtExecutionProvider`
- Orin Nano processed stream publishing through FFmpeg/libx264 instead of NVENC
- live profile switching between direct/native/annotated/reduced profiles
- tracking persistence buffering and bounded live telemetry publishing
- macOS FFmpeg 8.1 RTSP timeout option compatibility

Do not re-open these unless fresh evidence contradicts the current logs.

## Current Lab Shape

iMac master:

- dev backend, frontend, Keycloak, Postgres, NATS, MinIO, and MediaMTX
- central worker can run locally for iMac/CoreML tests
- backend must be recreated after setting the Jetson relay map:

```bash
cd "$HOME/vision"
JETSON_IP="PUT_THE_JETSON_IP_HERE"
export ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS="{\"*\":\"rtsp://$JETSON_IP:8554\"}"
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend
curl -fsS http://127.0.0.1:8000/healthz
```

Jetson Orin Nano edge:

- camera id used in recent tests:
  `d1588564-f5c8-4d6b-8584-45697bca2dba`
- edge model: `YOLO26n COCO Edge` at `/models/yolo26n.onnx`
- provider evidence:

```text
Resolved inference runtime policy profile=linux-aarch64-nvidia-jetson ...
detection_provider=TensorrtExecutionProvider
available_providers=['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
Loaded detection model YOLO26n COCO Edge with provider TensorrtExecutionProvider
```

Recommended Jetson pull/rebuild/restart:

```bash
cd "$HOME/vision"
git switch main
git pull --ff-only origin main
export JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"
docker compose -f infra/docker-compose.edge.yml up -d --build inference-worker
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

Provider sanity check:

```bash
docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint /app/.venv/bin/python inference-worker \
  -c "import sys, onnxruntime as ort; print(sys.version); print(ort.__version__); print(ort.get_available_providers())"
```

## Latest Performance Baseline

Jetson, annotated mode, no FPS cap, TensorRT:

```text
stage_avg_ms={
  capture=44.0-44.9,
  capture_wait=40.5-41.8,
  capture_decode_read=64.4-67.6,
  capture_throttle=2.3-3.1,
  detect=17.4-19.8,
  detect_prepare=7.5-9.6,
  detect_session=9.3-9.7,
  publish_stream=4.2-6.7,
  total=67.4-72.9,
  track=0.4
}
stage_max_ms={
  capture=516-549,
  capture_wait=501-533,
  total=535-569
}
```

Interpretation:

- TensorRT inference is healthy; `detect_session` is about 10 ms
- `detect_prepare` is improved but still costs roughly 7.5 to 9.6 ms
- the main live bottleneck is capture wait/jitter, not tracking or persistence
- the 500 ms spikes line up with `capture_wait`, so the next work should focus
  on RTSP/GStreamer/camera delivery stability
- `capture_decode_read` is a background pump diagnostic and should not be added
  directly to the frame `total`

iMac, annotated mode, CoreML:

```text
stage_avg_ms={
  capture=39-88,
  capture_wait=38-87,
  detect=91-103,
  detect_prepare=3.0-3.5,
  detect_session=87-99,
  publish_stream=7.5-11.5,
  total=146-205
}
```

Interpretation:

- the iMac is acceptable for lab/central validation, but it is an old Intel
  machine and should not be the main optimization target
- if live telemetry publishing times out, stale frames are dropped instead of
  blocking the worker

## Next Jetson Tuning Work

Work in this order:

1. Keep `jetson_clocks` enabled while testing.
2. Tune capture, not detector/tracker, unless new logs show otherwise.
3. Compare GStreamer RTSP settings:
   - `protocols=tcp` with `latency=50`, `100`, and `200`
   - UDP only if the camera/network path is clean enough
   - `drop-on-latency=true`
4. Compare direct camera RTSP versus any MediaMTX-relayed source.
5. Inspect camera settings:
   - CBR versus VBR
   - GOP/keyframe interval
   - substream resolution/FPS
   - Ethernet path and switch stability
6. If capture spikes persist, add percentile logging for `capture_wait` and log
   a compact warning when a single frame wait exceeds 250 ms.

Good next evidence to collect from Jetson logs:

```text
capture_wait avg and max
capture_read avg and max
capture_reconnect avg and max
detect_session avg and max
publish_stream avg and max
total avg and max
any GStreamer "Parse error" / "Could not read from resource" reconnect event
```

The recent GStreamer reconnect error looked like this:

```text
GStreamer rawvideo capture failed (no frame produced within 20s)
Could not receive message. (Parse error)
Camera capture lost, reconnecting
```

Treat that as a capture-source or RTSP-session stability problem first.

## Commands Worth Keeping Handy

iMac central worker test:

```bash
cd "$HOME/vision/backend"
ARGUS_API_BASE_URL="http://127.0.0.1:8000" \
ARGUS_API_BEARER_TOKEN="$TOKEN" \
python3 -m uv run python -m argus.inference.engine \
  --camera-id "c48cd041-0e7b-49ce-8058-4af896deecbd"
```

Jetson logs:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

Jetson metrics:

```bash
curl -s http://127.0.0.1:9108/metrics | head
```

Restart only the Jetson worker after a code/image update:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.edge.yml up -d --build inference-worker
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

## Later UI Work

After Jetson capture tuning is stable, continue OmniSight UI/UX distinctiveness.

Primary docs:

- `docs/brand/omnisight-ui-spec-sheet.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-codex-handoff.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-1-foundations.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-2-spatial-cockpit.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-3-motion.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-4-webgl.md`

Recommended branch:

```bash
git switch -c codex/omnisight-ui-spec-implementation
```

Pre-flight before UI edits:

```bash
cd "$HOME/vision"
corepack pnpm --dir frontend install
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
```

UI guardrails:

- preserve working video, camera setup, and profile switching flows
- keep product screens operational, not landing-page-like
- make OmniSight feel less generic through tokens, typography, surfaces, motion,
  and optional WebGL in phases
- do not start Phase 4 unless explicitly choosing the heavier WebGL path

## Cautions

- Do not use `git add -A`; unrelated scratch files commonly exist locally.
- Do not mark raw TensorRT `.engine` detector runtime as ready.
- Do not reintroduce double RTSP reads for native/no-privacy delivery.
- Do not optimize the old Intel iMac far beyond lab usefulness.
- Do not treat bounded telemetry frame drops as fatal unless UI telemetry becomes
  stale or the queue never recovers.
