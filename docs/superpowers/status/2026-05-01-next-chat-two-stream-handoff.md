# Next Chat Handoff: Stream 1 Closed, Jetson Validation Next, Stream 2 Later

Date: 2026-05-04

Purpose: paste this document into a fresh chat after `model-catalog-open-vocab-runtime` has been merged. The next chat should treat point 1 as closed, but should finish the iMac master + Jetson Orin edge validation before continuing with point 2: OmniSight UI/UX distinctiveness.

## Repository State To Start From

Start from `main` after pulling origin:

```bash
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only
git status -sb
git log --oneline -8
```

Expected:

- `main` includes the native-stream stability fixes from `codex/omnisight-ui-distinctiveness-followup`.
- `main` includes the completed model catalog and open-vocab runtime implementation from `model-catalog-open-vocab-runtime`.
- `main` includes the OmniSight UI/UX phase plans from Claude Code.
- untracked local scratch files may exist; do not stage them unless the user explicitly asks.

## Recently Closed: Point 1

Point 1 was:

```text
model catalog and open-vocabulary runtime implementation
```

Status: **closed on 2026-05-02**.

Primary docs:

- `docs/superpowers/specs/2026-05-01-model-catalog-and-open-vocab-runtime-design.md`
- `docs/superpowers/plans/2026-05-01-model-catalog-and-open-vocab-runtime-implementation-plan.md`
- `docs/imac-master-orin-lab-test-guide.md`
- `docs/runbook.md`

What landed:

- `ModelFormat.PT` and migration support for `.pt` model records.
- `GET /api/v1/model-catalog`.
- recommended catalog presets for YOLO26, YOLO11, YOLO12, YOLOE, YOLO-World, and planned TensorRT engine rows.
- `backend/scripts/register_model_preset.py` for registering operator-provided local artifacts from catalog defaults.
- validation for model format, capability, backend, and readiness combinations.
- Linux `aarch64` NVIDIA Jetson runtime profile selection.
- fixed-vocab ONNX Runtime path for YOLO26/YOLO11/YOLO12.
- experimental Ultralytics-backed open-vocab `.pt` path for YOLOE and YOLO-World.
- runtime vocabulary hot-swap for open-vocab workers.
- capability-aware Live query behavior for fixed-vocab filters versus open-vocab detector vocabulary.
- dynamic camera setup behavior: fixed-vocab active class scope uses the selected registered model classes, while open-vocab models use runtime vocabulary.
- model catalog UI cards are hidden once all ready presets are registered or intentionally planned, so registered rows do not keep cluttering camera setup.
- live stream recovery for delayed worker startup.
- worker resilience for telemetry publish timeouts and camera reconnect open failures.
- verify-all repair for the seeded model selector.

Manual lab notes from iMac testing:

- YOLO26n was much faster than YOLO12n on the tested Intel iMac/CoreML path.
- YOLO12n may still track more smoothly in some scenes because detector confidence and temporal consistency matter more than speed alone.
- for tracking accuracy, prefer frame skip `1`; start with FPS cap `20`; raise only if both workers stay stable.
- privacy blur strength affects rendering only; it does not change detector or tracker accuracy.

Still intentionally not done:

- raw TensorRT `.engine` detector runtime.

TensorRT follow-up is documented here:

- `docs/superpowers/specs/2026-05-02-tensorrt-engine-artifact-runtime-design.md`

The current TensorRT posture is: keep ONNX as the canonical portable model row; let ONNX Runtime use TensorRT/CUDA providers when available; later attach validated target-specific `.engine` artifacts to the ONNX model instead of exposing standalone `.engine` files as normal camera models.

## Current Priority: Finish Jetson Validation

Do this before Stream 2. The lab is currently testing:

- iMac master at `192.168.1.229`
- Jetson Orin Nano edge worker
- camera 2 id `d1588564-f5c8-4d6b-8584-45697bca2dba`
- edge model `YOLO26n COCO Edge` at `/models/yolo26n.onnx`
- camera 2 active classes: `person`, `car`, `bicycle`, `motorcycle`, `bus`, `truck`
- camera 2 browser delivery profile from the worker config: `720p10`, `kind=transcode`

Known-good evidence from 2026-05-04:

```text
HTTP Request: GET http://192.168.1.229:8000/api/v1/cameras/d1588564-f5c8-4d6b-8584-45697bca2dba/worker-config "HTTP/1.1 200 OK"
Worker ingesting directly from camera RTSP while browser delivery uses MediaMTX passthrough at rtsp://mediamtx:8554/cameras/d1588564-f5c8-4d6b-8584-45697bca2dba/passthrough
Jetson native GStreamer rawvideo capture is active
Inference stage timing summary ... stage_avg_ms={capture=9.4, detect=143.6, publish_stream=0.0, total=285.0, track=123.3}
Inference stage timing summary ... stage_avg_ms={capture=7.9, detect=144.4, publish_stream=0.0, total=285.2, track=124.2}
```

This closes the RTSP/NVDEC/GStreamer capture problem. The worker is reading frames on the Jetson through the native GStreamer rawvideo path.

### Open Jetson Issue 1: ONNX Runtime Is CPU Only

Current evidence:

```text
Resolved inference runtime policy profile=cpu-fallback system=linux machine=aarch64 cpu_vendor=unknown detection_provider=CPUExecutionProvider attribute_provider=<disabled> provider_override=False profile_override=False available_providers=['AzureExecutionProvider', 'CPUExecutionProvider']
Loaded detection model YOLO26n COCO Edge with provider CPUExecutionProvider
```

Root cause hypothesis:

- prior to `525b9824`, `backend/Dockerfile.edge` created a Python 3.12 virtualenv.
- the accelerated Jetson ONNX Runtime wheel found during debugging is `onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl`, which is Python 3.10, not Python 3.12.
- `525b9824` changes the Jetson edge image to use the Jetson base image's system Python 3.10 virtualenv and wires `JETSON_ORT_WHEEL_URL` through edge Compose.
- if `JETSON_ORT_WHEEL_URL` is unset during build, the image falls back to CPU `onnxruntime` and CPU provider output remains expected.
- the central/backend image remains Python 3.12; there is no separate generic non-Jetson Python 3.12 edge image in the current Compose stack.

Verification command:

```bash
docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint /app/.venv/bin/python inference-worker \
  -c "import onnxruntime as ort; print(ort.__version__); print(ort.get_available_providers())"
```

Bad current output: only `AzureExecutionProvider` and `CPUExecutionProvider`.

Target output: includes `TensorrtExecutionProvider` or at least `CUDAExecutionProvider`.

Current validation order:

1. Test `dd66ec7b` first if you want to isolate the Jetson processed-stream publisher fix. This still uses the previous Python runtime and should only be used to validate native plus annotated/reduced delivery behavior.
2. Then pull the branch tip (`525b9824` or newer), export a compatible Jetson cp310 `JETSON_ORT_WHEEL_URL`, rebuild with `--no-cache`, and verify Python 3.10 plus ONNX Runtime providers inside the container.
3. If provider output is still CPU-only after setting `JETSON_ORT_WHEEL_URL`, treat it as a wheel/runtime compatibility problem, not a browser delivery problem.

### Open Jetson Issue 2: iMac Live Page Does Not Show Jetson Video

Current symptom:

- the worker is running on the Jetson and telemetry timings are printed
- the iMac Live page does not show a video stream for the Jetson camera

Important evidence:

```text
Worker ingesting directly from camera RTSP while browser delivery uses MediaMTX passthrough at rtsp://mediamtx:8554/cameras/d1588564-f5c8-4d6b-8584-45697bca2dba/passthrough
publish_stream=0.0
```

Root cause hypothesis:

- for `ARGUS_PUBLISH_PROFILE=jetson-nano`, `MediaMTXClient._build_registration()` falls back to `StreamMode.PASSTHROUGH` when privacy filtering is off, even when the worker config says browser delivery `kind=transcode`
- in passthrough mode, `InferenceEngine.run_once()` intentionally skips `push_frame()`, so no annotated/transcoded frames are published by the worker
- the Jetson worker registers `cameras/<camera_id>/passthrough` on the Jetson's local MediaMTX service (`http://mediamtx:9997`, `rtsp://mediamtx:8554`)
- the iMac backend resolves browser playback URLs against the iMac/master MediaMTX settings, not the Jetson MediaMTX instance
- result: the browser likely asks iMac MediaMTX for `cameras/<camera_id>/passthrough`, while the available path is on Jetson MediaMTX

Evidence to collect next:

```bash
# On the iMac/master
curl -i "http://127.0.0.1:8888/cameras/d1588564-f5c8-4d6b-8584-45697bca2dba/passthrough/index.m3u8"
docker compose -f infra/docker-compose.dev.yml logs --tail=120 mediamtx

# On the Jetson
curl -i "http://127.0.0.1:8888/cameras/d1588564-f5c8-4d6b-8584-45697bca2dba/passthrough/index.m3u8"
docker compose -f infra/docker-compose.edge.yml logs --tail=120 mediamtx
```

Expected if the hypothesis is right:

- iMac MediaMTX returns no stream / 404 for the edge camera path
- Jetson MediaMTX has the camera path or has attempted to source it

Likely fixes to design after confirming:

- lab bridge: have iMac MediaMTX proxy the Jetson MediaMTX path for edge cameras, so existing browser URLs continue to work
- worker publish path: for edge browser delivery, publish a processed/annotated stream to a path the iMac can read, or register that path centrally
- API contract path: teach stream access resolution about edge node stream endpoints instead of always using master MediaMTX URLs

Implementation update on 2026-05-05:

- The lab bridge path is now implemented behind `ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS`.
- When an edge camera resolves to `passthrough` and an edge RTSP base is configured, the iMac backend keeps browser playback on the iMac MediaMTX URLs but configures the iMac MediaMTX path to pull `rtsp://<jetson>:8554/cameras/<camera_id>/passthrough` with an internal read JWT.
- The iMac relay path is cached and refreshed before the internal read token expires instead of being replaced on every HLS resource request.
- `infra/docker-compose.edge.yml` now points edge MediaMTX JWT validation at the iMac backend JWKS through `ARGUS_API_BASE_URL`.
- Next lab validation: set `ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS='{"*":"rtsp://<JETSON_IP>:8554"}'` before recreating the iMac backend, then recreate Jetson `mediamtx` and `inference-worker`.

Do not treat this as a capture failure; capture is already green.

Implementation update on 2026-05-06:

- `dd66ec7b` routes Jetson processed browser streams through the GStreamer/NVIDIA encoder publisher instead of the central FFmpeg/libx264 publisher.
- At `dd66ec7b`, validate native, annotated, and reduced profiles on Jetson without mixing in the Python 3.10 runtime change.
- `525b9824` then changes the Jetson edge image runtime to Python 3.10 for cp310 accelerated ONNX Runtime wheels.
- Pulling branch tip includes both fixes; use the detached `dd66ec7b` checkpoint first only when you want a clean A/B test.

## Later: Point 2

Point 2 is:

```text
OmniSight UI/UX distinctiveness implementation
```

Primary docs:

- `docs/brand/omnisight-ui-spec-sheet.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-codex-handoff.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-1-foundations.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-2-spatial-cockpit.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-3-motion.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-4-webgl.md`

Mission:

- make OmniSight feel less generic
- land token, typography, surface, hero, motion, and optional WebGL lens phases in order
- keep the working video and setup flows stable while making pages more distinctive

Recommended execution mode:

```text
Use docs/superpowers/plans/2026-04-30-omnisight-spec-codex-handoff.md as the operating guide.
Execute phases in order.
Do not start Phase N until Phase N-1 is green and committed.
Phase 4 is gated and opt-in.
```

Pre-flight:

```bash
cd "$HOME/vision"
git status --short
corepack pnpm --dir frontend install
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Important UI notes:

- keep the obsidian/near-black canvas
- reduce default violet/blue dashboard wash
- use roughly 75% neutral dark surfaces, 15% cerulean, 5% violet, 5% status colors
- violet is a brand/entry accent, not a generic dashboard default
- avoid landing-page marketing composition inside the product
- keep video/evidence zones sharply black and inspection-oriented

## Known Cautions

- Do not use `git add -A`; unrelated untracked scratch files may exist.
- Do not mark TensorRT `.engine` support as ready until a real detector adapter and validation workflow exist.
- Do not reintroduce double RTSP reads for native/no-privacy delivery.
- Do not revert user-created or Claude-created untracked files unless explicitly asked.
- Stream 2 may touch camera/setup surfaces visually; preserve the model selection behavior from Stream 1.

## Suggested Branch Name

For Stream 2:

```bash
git switch -c codex/omnisight-ui-spec-implementation
```

## Completion Target

Stream 2 is complete when:

- phases 1-3 are committed and green
- Phase 4 is either explicitly skipped or landed behind the feature flag
- sign-in, dashboard, Live, Patterns, Evidence, Sites, Scenes, and Operations pass visual QA
