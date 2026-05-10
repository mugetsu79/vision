# Model Loading And Configuration Guide

This guide is the operator checklist for loading every currently supported
Vezor/OmniSight model, registering it in the backend, choosing it in scene
setup, and attaching optimized runtime artifacts when appropriate.

Use this when you want a clear model-by-model sequence instead of piecing
together the lab guide and runbook.

## Quick Rules

- Put local model files under `models/` in this checkout.
- Register portable camera models first. A camera can only select registered
  `/api/v1/models` rows.
- Fixed-vocab COCO models should be registered from ONNX files.
- Open-vocab discovery models should be registered from `.pt` files.
- Raw `.engine` files are not primary camera models. Attach them as runtime
  artifacts to an ONNX model.
- Compiled open-vocab ONNX/TensorRT exports are scene runtime artifacts tied to
  a camera vocabulary hash. They are not replacement primary camera models.

## Supported Model Catalog

| Catalog ID | File | Capability | Use |
|---|---|---|---|
| `yolo26n-coco-onnx` | `models/yolo26n.onnx` | Fixed vocab | Default fast detector |
| `yolo26s-coco-onnx` | `models/yolo26s.onnx` | Fixed vocab | More accuracy if hardware allows |
| `yolo11n-coco-onnx` | `models/yolo11n.onnx` | Fixed vocab | Stable fast fallback |
| `yolo11s-coco-onnx` | `models/yolo11s.onnx` | Fixed vocab | Stable balanced fallback |
| `yolo12n-coco-onnx` | `models/yolo12n.onnx` | Fixed vocab | Older lab compatibility baseline |
| `yoloe-26n-open-vocab-pt` | `models/yoloe-26n-seg.pt` | Open vocab | Preferred experimental open-vocab path |
| `yoloe-26s-open-vocab-pt` | `models/yoloe-26s-seg.pt` | Open vocab | Higher quality experimental open-vocab path |
| `yolov8s-worldv2-open-vocab-pt` | `models/yolov8s-worldv2.pt` | Open vocab | Smaller experimental open-vocab fallback |
| `yolo26n-coco-tensorrt-engine` | `models/yolo26n.engine` | Planned engine | Do not register as a camera model |
| `yolo26s-coco-tensorrt-engine` | `models/yolo26s.engine` | Planned engine | Do not register as a camera model |

## One-Time Setup

Run these from the iMac or master machine unless a section explicitly says
Jetson.

```bash
cd /Users/yann.moren/vision
```

Start the development stack if it is not already running:

```bash
make dev-up
```

If this is an existing dev database and the UI or API complains about
`cameras.vision_profile`, `cameras.detection_regions`, or runtime artifact
tables, run migrations:

```bash
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
```

Export API access for local-dev registration commands:

```bash
export ARGUS_API_BASE_URL="http://127.0.0.1:8000"
export ARGUS_API_BEARER_TOKEN="$(
  curl -s \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
```

Check the catalog status:

```bash
curl -s -H "Authorization: Bearer $ARGUS_API_BEARER_TOKEN" \
  "$ARGUS_API_BASE_URL/api/v1/model-catalog"
```

## Register Fixed-Vocab ONNX Models

Only run the command for a model if the file exists locally.

For fixed-vocab ONNX presets, do not pass `--class` in the normal path. The
backend reads embedded ONNX class metadata when available, which keeps the UI
class picker accurate.

### YOLO26n COCO

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo26n-coco-onnx \
  --artifact-path /Users/yann.moren/vision/models/yolo26n.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

### YOLO26s COCO

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo26s-coco-onnx \
  --artifact-path /Users/yann.moren/vision/models/yolo26s.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

### YOLO11n COCO

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo11n-coco-onnx \
  --artifact-path /Users/yann.moren/vision/models/yolo11n.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

### YOLO11s COCO

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo11s-coco-onnx \
  --artifact-path /Users/yann.moren/vision/models/yolo11s.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

### YOLO12n COCO

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo12n-coco-onnx \
  --artifact-path /Users/yann.moren/vision/models/yolo12n.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

## Register Open-Vocab PT Models

Open-vocab `.pt` models are for discovery and vocabulary tuning. They show a
Runtime vocabulary field in scene setup instead of the 80-class fixed-vocab
checkbox list.

### YOLOE-26N Open Vocab

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yoloe-26n-open-vocab-pt \
  --artifact-path /Users/yann.moren/vision/models/yoloe-26n-seg.pt \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

### YOLOE-26S Open Vocab

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yoloe-26s-open-vocab-pt \
  --artifact-path /Users/yann.moren/vision/models/yoloe-26s-seg.pt \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

### YOLOv8s-Worldv2 Open Vocab

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolov8s-worldv2-open-vocab-pt \
  --artifact-path /Users/yann.moren/vision/models/yolov8s-worldv2.pt \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

## Verify Registered Models

List registered models:

```bash
curl -s -H "Authorization: Bearer $ARGUS_API_BEARER_TOKEN" \
  "$ARGUS_API_BASE_URL/api/v1/models"
```

Then open:

- Frontend: [http://127.0.0.1:3000](http://127.0.0.1:3000)
- Scenes: `Cameras > Add scene` or `Cameras > Edit`
- Operations: `/settings`

What good looks like:

- Fixed-vocab ONNX models appear in the Primary model dropdown.
- Fixed-vocab models expose class checkboxes under Active class scope.
- Open-vocab `.pt` models expose Runtime vocabulary instead of class
  checkboxes.
- The model catalog panel marks registered rows as registered.

## Configure A Fixed-Vocab Scene

1. Open `Cameras`.
2. Click `Add scene` or edit an existing scene.
3. Fill the Identity step: name, site, processing mode, and RTSP URL.
4. In `Models & Tracking`, choose a fixed-vocab primary model, usually:
   - `YOLO26n COCO` for the default path
   - `YOLO26s COCO` when you want more accuracy
   - `YOLO11n COCO` or `YOLO12n COCO` for fallback comparison
5. Check only the classes you want active, or leave all unchecked to keep the
   full model inventory active.
6. Choose tracker type.
7. Continue through Privacy, Calibration, and Review.
8. Save the scene.
9. Open Operations and start/copy the worker command for that scene.

## Configure An Open-Vocab Scene

1. Open `Cameras`.
2. Click `Add scene` or edit an existing scene.
3. Fill the Identity step.
4. In `Models & Tracking`, choose one of:
   - `YOLOE-26N Open Vocab`
   - `YOLOE-26S Open Vocab`
   - `YOLOv8s-Worldv2 Open Vocab`
5. Enter Runtime vocabulary terms, for example:

```text
person, forklift, pallet jack
```

6. Keep terms short and concrete.
7. Continue through Privacy, Calibration, and Review.
8. Save the scene.
9. Start the worker from Operations.

Dynamic `.pt` open vocab is the correct mode while you are still changing
terms. Once the terms are stable, build scene runtime artifacts.

## Add Fixed-Vocab TensorRT Runtime Artifacts

Use this only after an ONNX model is registered and a matching `.engine` has
already been built for the target host.

Do not register `yolo26n-coco-tensorrt-engine` or
`yolo26s-coco-tensorrt-engine` as primary camera models. They are catalog
signals for runtime artifacts.

Register a prebuilt TensorRT engine against the ONNX model row:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.build_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN" \
  --model-id "$MODEL_ID" \
  --source-model /Users/yann.moren/vision/models/yolo26n.onnx \
  --prebuilt-engine /Users/yann.moren/vision/models/yolo26n.jetson.fp16.engine \
  --target-profile linux-aarch64-nvidia-jetson \
  --class person --class car --class bus --class truck \
  --input-width 640 --input-height 640
```

Validate it on the host that will run it:

```bash
python3 -m uv run python -m argus.scripts.validate_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN" \
  --model-id "$MODEL_ID" \
  --artifact-id "$ARTIFACT_ID" \
  --artifact-path /Users/yann.moren/vision/models/yolo26n.jetson.fp16.engine \
  --expected-sha256 "$ARTIFACT_SHA256" \
  --target-profile linux-aarch64-nvidia-jetson \
  --host-profile linux-aarch64-nvidia-jetson
```

Restart the worker. What good looks like in logs:

```text
Selected inference runtime ... selected_backend=tensorrt_engine ... fallback=False
```

## Add Open-Vocab Compiled Scene Artifacts

Use this after an open-vocab scene has a stable runtime vocabulary. The artifact
is scene-scoped and only selected when the camera vocabulary hash matches.

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.build_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN" \
  --model-id "$OPEN_VOCAB_MODEL_ID" \
  --camera-id "$CAMERA_ID" \
  --open-vocab-source-pt /Users/yann.moren/vision/models/yoloe-26n-seg.pt \
  --runtime-vocabulary "person,forklift,pallet jack" \
  --vocabulary-version "$RUNTIME_VOCAB_VERSION" \
  --export-format onnx \
  --export-format engine \
  --target-profile linux-aarch64-nvidia-jetson \
  --input-width 640 --input-height 640
```

Validate each returned artifact with `validate_runtime_artifact`.

What good looks like:

- matching TensorRT artifact: `selected_backend=tensorrt_engine`
- matching ONNX artifact: `selected_backend=onnxruntime`
- changed vocabulary: `fallback_reason=vocabulary_changed`
- mismatched saved vocabulary hash: `artifact_vocabulary_mismatch`

## Jetson Path Notes

For the iMac master + Jetson edge lab, the Jetson worker container sees model
files at `/models/<filename>`. You may need a second registered model row for
the same ONNX file with a container-visible path:

```bash
EDGE_MODEL_PATH="/models/yolo26n.onnx"
```

The iMac backend can validate that path because the dev backend container also
bind-mounts the checkout model directory at `/models`.

Use host paths for commands run on the host, such as:

```text
/Users/yann.moren/vision/models/yolo26n.onnx
```

Use container paths for model rows intended for Jetson worker containers, such
as:

```text
/models/yolo26n.onnx
```

## What Not To Do

- Do not register `.engine` files as primary camera models.
- Do not register `yolo26n.pt` or `yolo12n.pt` for the normal fixed-vocab path.
- Do not register compiled open-vocab `.onnx` or `.engine` exports as primary
  camera models.
- Do not expect `/api/v1/model-catalog` to download files. It only reports
  supported presets and registration status.

## Troubleshooting

If the model does not appear in the Primary model dropdown:

1. Confirm it is registered in `/api/v1/models`.
2. Confirm the token was valid when you ran registration.
3. Confirm the model file path exists from the backend container.
4. Refresh the scene setup wizard.

If fixed-vocab classes do not appear:

1. Confirm you registered the ONNX file, not a `.pt` file.
2. Confirm the ONNX file has embedded class metadata.
3. Re-register without `--class` unless you intentionally need a custom class
   list.

If open-vocab runtime artifacts are ignored:

1. Confirm the artifact is valid.
2. Confirm it is scene-scoped to the same camera.
3. Confirm its vocabulary version/hash matches the current scene runtime
   vocabulary.
4. Check worker logs for `artifact_vocabulary_mismatch` or
   `vocabulary_changed`.
