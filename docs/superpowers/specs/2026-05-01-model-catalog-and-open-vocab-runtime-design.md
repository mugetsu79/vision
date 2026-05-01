# Model Catalog And Open-Vocab Runtime Design

**Date:** 2026-05-01
**Status:** Proposed
**Scope:** Recommended detector model options, model registration/catalog flow, Jetson runtime profile support, and a true open-vocabulary detector backend for central and edge workers.

## 0. Current Checkpoint

The product already has the important control-plane foundation:

- `Model` records are stored in Postgres and served through `/api/v1/models`.
- Camera setup selects models dynamically from registered `Model` records.
- `Model.capability` supports `fixed_vocab` and `open_vocab`.
- Camera runtime vocabulary state is persisted and included in worker config.
- The query path can produce fixed-vocab filters or open-vocab runtime vocabulary updates.
- The worker has a capability-aware detector factory.
- The `vision` dependency group already includes `ultralytics`, so a true open-vocab adapter can use Ultralytics model APIs without creating a new dependency family.

The remaining gaps are concrete:

- The UI can only select models that have already been registered. There is no first-class recommended model catalog.
- `models/` is a local artifact location, not a registry. The repository does not ship model binaries.
- Current `open_vocab` runtime still wraps the fixed-vocab YOLO detector. It changes the class list but does not run YOLO-World or YOLOE prompt behavior.
- `ModelFormat.ENGINE` exists, but the current detector path always uses ONNX Runtime `InferenceSession`. Raw TensorRT `.engine` files should not be advertised as ready until a real TensorRT engine detector exists.
- Jetson Orin Nano Super is Linux `aarch64`; current runtime profile selection handles NVIDIA providers on Linux `x86_64`, but not Jetson as a first-class host profile.

## 1. Goals

1. Make recommended model options explicit and easy to register:
   - YOLO26n COCO ONNX
   - YOLO26s COCO ONNX
   - YOLO11n COCO ONNX
   - YOLO11s COCO ONNX
   - YOLO12n COCO ONNX as the current lab/legacy option
2. Add open-vocab catalog entries that are honest about runtime readiness:
   - YOLOE-26N or YOLOE-26S as the preferred modern open-vocab path
   - YOLOv8s-worldv2 as the smaller YOLO-World fallback path
3. Support true open-vocab inference by adding an Ultralytics-backed detector adapter that can call `set_classes(...)` or the equivalent prompt setup on vocabulary changes.
4. Add Jetson runtime classification so workers can report and select NVIDIA acceleration on Linux `aarch64`.
5. Preserve downstream analytics contracts. Detections must still leave the detector as normalized `Detection` objects with `class_name`, `class_id`, `confidence`, and `bbox`.
6. Avoid committing model binaries to git.

## 2. Non-Goals

- No automatic model download in the first implementation. The system can document download/export commands, but model files remain operator-provided local artifacts.
- No full production model marketplace.
- No training workflow.
- No raw TensorRT `.engine` detector in the first pass. The catalog may describe this as a future optimization, but the selectable ready path remains ONNX Runtime for fixed-vocab models and Ultralytics `.pt` for open-vocab models.
- No scheduler reconciliation or worker process lifecycle automation. This remains separate fleet-supervisor work.

## 3. Source Model Recommendations

The recommended catalog should follow the current Ultralytics direction:

- YOLO26 is the forward default for fixed-vocab detection because it is positioned for edge and low-power deployment with end-to-end inference and faster CPU characteristics.
- YOLO11 remains a stable production fallback.
- YOLO12 remains useful for the existing lab checkpoint but should not be the default forward recommendation.
- YOLOE is the preferred open-vocab direction because it supports text and visual prompting and includes YOLOE-26 variants.
- YOLO-World remains useful as a smaller open-vocab fallback, especially `yolov8s-worldv2`.

Reference docs:

- https://docs.ultralytics.com/models/yolo26/
- https://docs.ultralytics.com/models/yolo11/
- https://docs.ultralytics.com/models/yolo12/
- https://docs.ultralytics.com/models/yoloe/
- https://docs.ultralytics.com/models/yolo-world/
- https://docs.ultralytics.com/guides/nvidia-jetson/
- https://docs.ultralytics.com/integrations/tensorrt/

## 4. Model Catalog

### 4.1 Catalog Entry Shape

Add a versioned in-repo catalog for recommended model presets. It should be code, not JSON, because it needs typed enums and path helpers.

Each catalog entry describes:

- stable id, for example `yolo26n-coco-onnx`
- display name
- model family
- version label
- task
- format
- capability
- expected local path hints
- input shape
- license label
- recommended execution profiles
- runtime backend
- readiness state
- short operational note

Readiness states:

- `ready`: supported by the current runtime path once the model file is present and registered
- `experimental`: supported by the contract but should be used for lab validation only
- `planned`: visible in docs/catalog but not selectable as a camera model

### 4.2 Initial Catalog

Ready fixed-vocab presets:

| Preset | Format | Capability | Runtime backend | Notes |
|---|---|---|---|---|
| YOLO26n COCO ONNX | ONNX | fixed_vocab | onnxruntime | Default fast detector |
| YOLO26s COCO ONNX | ONNX | fixed_vocab | onnxruntime | Balanced accuracy/speed |
| YOLO11n COCO ONNX | ONNX | fixed_vocab | onnxruntime | Stable fallback |
| YOLO11s COCO ONNX | ONNX | fixed_vocab | onnxruntime | Stable balanced fallback |
| YOLO12n COCO ONNX | ONNX | fixed_vocab | onnxruntime | Current lab compatibility |

Experimental open-vocab presets:

| Preset | Format | Capability | Runtime backend | Notes |
|---|---|---|---|---|
| YOLOE-26N Open Vocab | PT | open_vocab | ultralytics_yoloe | Preferred open-vocab lab path |
| YOLOE-26S Open Vocab | PT | open_vocab | ultralytics_yoloe | Higher quality, heavier |
| YOLOv8s-Worldv2 Open Vocab | PT | open_vocab | ultralytics_yolo_world | Smaller fallback |

Planned acceleration presets:

| Preset | Format | Capability | Runtime backend | Notes |
|---|---|---|---|---|
| YOLO26n COCO TensorRT Engine | ENGINE | fixed_vocab | tensorrt_engine | Hidden until a raw engine detector exists |
| YOLO26s COCO TensorRT Engine | ENGINE | fixed_vocab | tensorrt_engine | Hidden until a raw engine detector exists |

## 5. API And Persistence

### 5.1 Existing Model Records Stay Canonical

The existing `models` table remains the canonical inventory of selectable runtime models.

The catalog is not a replacement for `Model`; it is a source of recommended presets that can be registered into `Model` after the corresponding local artifact exists.

### 5.2 Contract Extensions

Extend `ModelFormat`:

- existing: `onnx`, `engine`
- add: `pt`

Extend `ModelCapabilityConfig` with optional structured fields:

- `model_family`
- `runtime_backend`
- `readiness`
- `recommended_profiles`
- `requires_gpu`
- `supports_masks`
- `source_url`

The existing `execution_profiles` field stays because worker capability matching already uses it.

### 5.3 Catalog API

Add:

- `GET /api/v1/model-catalog`

Response entries include:

- the catalog entry
- whether a matching `Model` is registered
- the registered model id if found
- whether the configured local path exists from the backend runtime
- a validation message if the artifact is missing or unsupported

Registration remains through the existing `POST /api/v1/models` in the first implementation. A CLI helper can call that endpoint using catalog defaults.

## 6. Runtime Architecture

### 6.1 Detector Backends

Keep the existing detector factory, but make backend selection explicit:

- `onnxruntime`:
  - current fixed-vocab `YoloDetector`
  - supported for `ModelFormat.ONNX`
- `ultralytics_yolo_world`:
  - new open-vocab adapter using Ultralytics YOLO-World APIs
  - supported for `ModelFormat.PT`
- `ultralytics_yoloe`:
  - new open-vocab adapter using Ultralytics YOLOE APIs
  - supported for `ModelFormat.PT`
- `tensorrt_engine`:
  - planned future backend
  - not selectable as `ready` until implemented

### 6.2 Open-Vocab Adapter Contract

The open-vocab adapter must:

- load the configured model once
- normalize initial runtime vocabulary
- set text prompt classes on load
- update prompt classes when `update_runtime_vocabulary(...)` is called
- run prediction on BGR frames from OpenCV
- normalize output boxes into existing `Detection` values
- expose selected provider/device information in `describe_runtime_state()`
- tolerate empty vocabulary by returning no detections

The worker must not care whether boxes came from a fixed COCO model or an open-vocab model.

### 6.3 Runtime Vocabulary Behavior

For open-vocab cameras:

- the wizard sets an initial `runtime_vocabulary`
- Live query can replace that vocabulary
- worker command handling hot-swaps the detector vocabulary without restart
- event telemetry continues to emit normalized class names

For fixed-vocab cameras:

- the wizard shows active class scope
- Live query continues to update filters/classes, not detector prompts

## 7. Jetson Runtime Profile

Add a first-class execution profile:

- `linux-aarch64-nvidia-jetson`

Classification rule:

- system is Linux
- machine is `aarch64` or `arm64`
- available providers include `TensorrtExecutionProvider` or `CUDAExecutionProvider`

Provider priority:

1. `TensorrtExecutionProvider`
2. `CUDAExecutionProvider`
3. `CPUExecutionProvider`

This does not mean raw `.engine` files are supported. It means ONNX Runtime can use NVIDIA acceleration providers on Jetson when those providers are installed.

## 8. Frontend Behavior

Camera setup continues to select from registered models. The UI should become more informative:

- show capability badge: fixed vocab or open vocab
- show runtime/backend badge: ONNX Runtime or Ultralytics
- show readiness badge: ready or experimental
- group recommended models when catalog data is available
- keep unsupported/planned catalog entries out of the primary camera model select

The model catalog can be surfaced as a small inventory/help panel near camera setup or in Operations. It should not block the current camera creation path.

## 9. Validation And Safety

Model registration must reject combinations that cannot run:

- `fixed_vocab` + `onnxruntime` requires `format=onnx`
- `open_vocab` + `ultralytics_yoloe` requires `format=pt`
- `open_vocab` + `ultralytics_yolo_world` requires `format=pt`
- `engine` + `tensorrt_engine` remains planned until the detector exists

Open-vocab registration must require:

- `supports_runtime_vocabulary_updates=true`
- `max_runtime_terms` greater than zero
- `prompt_format=labels` or `prompt_format=phrases`

The API should return precise validation messages instead of allowing a model that fails only when the worker starts.

## 10. Testing Strategy

Backend tests:

- catalog entry shape and uniqueness
- catalog status against existing registered models
- model create validation for valid/invalid backend combinations
- Jetson runtime profile selection
- detector factory selection by capability/backend
- fake Ultralytics open-vocab detector load, vocabulary update, and normalized detection output
- worker command hot-swap path for open-vocab vocabulary updates

Frontend tests:

- camera wizard receives and displays capability/config metadata
- model select shows capability/readiness badges
- open-vocab model shows runtime vocabulary editor
- fixed-vocab model shows active class scope
- catalog/inventory panel handles missing artifacts without blocking camera setup

Manual validation:

- register YOLO26n ONNX and run central/native clean stream
- register YOLO26s ONNX and run 720p10
- register YOLOE-26N `.pt` with a short vocabulary on a GPU host
- update runtime vocabulary from Live query and confirm detector output changes without worker restart
- run Jetson preflight and confirm runtime profile reports Jetson NVIDIA when providers are available

## 11. Rollout Order

1. Catalog and validation contracts.
2. Jetson runtime profile.
3. Fixed-vocab recommended model registration path.
4. Open-vocab Ultralytics adapter behind experimental readiness.
5. UI badges/catalog inventory.
6. Lab docs and model setup commands.

This order keeps the current working fixed-vocab video path stable while making open-vocab real in a controlled lab lane.

## 12. Acceptance Criteria

- An admin can see or register recommended YOLO26/YOLO11/YOLO12 model records without hand-writing JSON from scratch.
- Camera setup can clearly distinguish fixed-vocab and open-vocab model records.
- YOLO26n ONNX and YOLO26s ONNX can be registered as fixed-vocab models and selected by cameras.
- A YOLOE or YOLO-World `.pt` model can be registered as `open_vocab`.
- An open-vocab worker loads the Ultralytics-backed detector instead of the fixed-vocab YOLO wrapper.
- Updating runtime vocabulary updates the detector prompt/classes without a worker restart.
- Jetson workers are classified as an NVIDIA ARM64 profile when CUDA/TensorRT providers are available.
- Raw TensorRT `.engine` files are not presented as ready until a real engine detector is implemented.

## 13. Spec Self-Review

- Placeholder scan: no unresolved placeholders remain.
- Scope check: this is one coherent implementation track focused on model registry/runtime readiness.
- Ambiguity check: raw TensorRT engine support is explicitly planned, not ready.
- Consistency check: existing `Model` records remain canonical; the catalog is a registration aid, not a parallel runtime inventory.
