# TensorRT Engine Artifact Runtime Design

**Date:** 2026-05-02
**Status:** Proposed
**Scope:** Add validated TensorRT `.engine` artifacts as optional target-specific accelerators beside canonical ONNX model records.

## 0. Current Checkpoint

The model catalog and open-vocab runtime stream established the safe baseline:

- `Model` rows remain the canonical selectable camera inventory.
- Fixed-vocab models use ONNX files and ONNX Runtime.
- ONNX Runtime can still use accelerated providers such as TensorRT or CUDA when those providers are installed.
- Open-vocab models use Ultralytics `.pt` files.
- Raw TensorRT `.engine` catalog entries are visible as planned only.

That is the correct product posture for portable testing, but it leaves a real performance path unexplored. Jetson and NVIDIA deployments often want a precompiled TensorRT engine because it can remove runtime graph conversion overhead and use target-specific precision and tactic selection.

The key constraint is that a TensorRT `.engine` is not a portable model source. It is a compiled artifact tied to a target class of hardware, TensorRT version, CUDA version, precision mode, and often input shape. Treating it like a normal registered model would be misleading and brittle.

## 1. Goals

1. Keep ONNX as the canonical portable model artifact.
2. Allow optional TensorRT engine artifacts for fixed-vocab models.
3. Use a TensorRT engine only when it is explicitly validated for the worker host profile.
4. Fall back to ONNX automatically when the engine is missing, invalid, or target-incompatible.
5. Make the active runtime path visible in worker logs, Operations, and camera/model UI.
6. Keep raw `.engine` support separate from open-vocab `.pt` support.

## 2. Non-Goals

- Do not replace ONNX registration.
- Do not treat `.engine` files as portable source models.
- Do not support arbitrary custom TensorRT output layouts in the first pass.
- Do not support dynamic shape engines until the fixed-shape path is proven.
- Do not add a production artifact registry or remote model download workflow.
- Do not require TensorRT on iMac central testing.
- Do not make TensorRT engine artifacts selectable unless they have passed validation.

## 3. Model And Artifact Relationship

The canonical model remains a normal `Model` row:

- name: `YOLO26n COCO`
- format: `onnx`
- path: `/models/yolo26n.onnx` or the host-specific path
- classes: resolved from ONNX metadata
- capability: `fixed_vocab`
- runtime backend: `onnxruntime`

A TensorRT engine should be modeled as a compiled runtime artifact attached to that canonical model, not as a separate standalone camera model.

The relationship should be:

```text
Model (portable ONNX source)
  -> RuntimeArtifact (TensorRT engine for linux-aarch64-nvidia-jetson)
  -> RuntimeArtifact (TensorRT engine for linux-x86_64-nvidia, optional later)
```

This keeps camera setup simple: the operator picks the model, while the worker picks the best validated runtime artifact for its host.

## 4. Runtime Artifact Contract

Add a persistent runtime artifact concept with fields like:

- `id`
- `model_id`
- `kind`: `tensorrt_engine`
- `path`
- `target_profile`: for example `linux-aarch64-nvidia-jetson`
- `precision`: `fp16`, `int8`, or `fp32`
- `input_shape`
- `output_layout`: initially a constrained YOLO layout enum
- `sha256`
- `size_bytes`
- `source_model_sha256`
- `builder`: optional metadata for the build command/tool
- `tensorrt_version`
- `cuda_version`
- `device_name`
- `compute_capability`
- `validation_status`: `unvalidated`, `valid`, `invalid`, `stale`
- `validation_error`
- `validated_at`
- `created_at`

The important invariant is that a `valid` artifact must prove it was built from the same source model hash and class inventory as the attached ONNX model.

## 5. Readiness States

Runtime artifacts should use explicit readiness:

- `unvalidated`: artifact is registered but has not been tested on a compatible target.
- `valid`: artifact loaded and produced structurally valid detections on the target.
- `invalid`: artifact failed validation.
- `stale`: source model hash, class inventory, input shape, or declared target metadata no longer match.
- `missing_artifact`: database record exists, but the worker cannot read the file.
- `target_mismatch`: artifact exists but does not match the current worker host profile.

Only `valid` artifacts can be used for live inference.

## 6. Worker Runtime Selection

At worker startup, build the runtime choice in this order:

1. Load camera config and canonical ONNX model.
2. Classify host profile using the existing runtime profile logic.
3. Find runtime artifacts attached to the model for the host profile.
4. Choose the best valid TensorRT artifact if available.
5. Otherwise use ONNX Runtime with the existing provider policy.

The worker should log a structured decision:

```text
model_runtime_selection model_id=... source_format=onnx selected_backend=tensorrt_engine
artifact_id=... target_profile=linux-aarch64-nvidia-jetson fallback=false
```

If fallback occurs, log why:

```text
model_runtime_selection selected_backend=onnxruntime fallback=true
fallback_reason=target_mismatch
```

Fallback is a feature, not a silent failure. Operators should see the current runtime path in Operations.

## 7. TensorRT Detector Adapter

Add a dedicated `TensorRtEngineDetector`, separate from the ONNX detector.

Responsibilities:

- load the serialized TensorRT engine
- allocate device and host buffers
- bind input/output tensors
- preprocess frames in the same way as the ONNX YOLO detector
- execute inference on CUDA
- decode outputs into existing `Detection` objects
- expose runtime state including engine path, target profile, precision, and validation hash

First-pass limitations:

- fixed input shape only, starting with `640x640`
- fixed-vocab detection only
- YOLO26/YOLO11/YOLO12 style detection output layouts only when explicitly declared
- no masks
- no open-vocab runtime vocabulary
- no attribute classifier engine path unless added in a later stream

The detector factory should select this adapter only when the runtime selection phase chooses a valid TensorRT artifact.

## 8. Engine Build Workflow

The first implementation should provide a repeatable local command for Jetson:

```bash
python -m argus.scripts.build_tensorrt_engine \
  --model-id "$MODEL_ID" \
  --source-onnx /models/yolo26n.onnx \
  --output-engine /models/yolo26n.jetson.fp16.engine \
  --target-profile linux-aarch64-nvidia-jetson \
  --precision fp16 \
  --api-base-url http://$IMAC_IP:8000 \
  --bearer-token "$TOKEN"
```

The command should:

1. validate that the ONNX source exists and matches the registered model hash
2. build the TensorRT engine on the target device
3. compute engine hash and file size
4. register or update the runtime artifact record
5. optionally run validation and mark the artifact valid

The build should happen on the target machine whenever possible. A Jetson engine built elsewhere should be treated as unvalidated until loaded and tested on the Jetson.

## 9. Validation Workflow

Validation should be an explicit operation:

```bash
python -m argus.scripts.validate_tensorrt_engine \
  --artifact-id "$ARTIFACT_ID" \
  --sample-image models/bus.jpg \
  --api-base-url http://$IMAC_IP:8000 \
  --bearer-token "$TOKEN"
```

Validation should prove:

- file exists and hash matches the artifact record
- host profile matches target profile
- TensorRT and CUDA versions are discoverable
- engine loads successfully
- input shape matches declared shape
- output tensors match the declared layout
- at least one inference pass completes
- decoded detections are structurally valid

Validation does not need to guarantee semantic accuracy, but it must catch crashes and impossible output shapes before a camera can use the engine.

## 10. API Surface

Add endpoints under the existing model domain:

- `GET /api/v1/models/{model_id}/runtime-artifacts`
- `POST /api/v1/models/{model_id}/runtime-artifacts`
- `PATCH /api/v1/models/{model_id}/runtime-artifacts/{artifact_id}`
- `POST /api/v1/models/{model_id}/runtime-artifacts/{artifact_id}/validate`

Responses should include readiness, target profile, artifact existence, validation details, and whether the current backend can use the artifact.

Do not expose runtime artifacts as normal `/api/v1/models` rows in camera setup.

## 11. UI Behavior

Camera setup should continue to pick the canonical model.

Add runtime visibility in secondary surfaces:

- Model catalog card:
  - `ONNX ready`
  - `TensorRT artifact: none / unvalidated / valid / invalid`
- Camera wizard selected model details:
  - portable model path
  - available validated runtime artifacts
  - expected worker fallback behavior
- Operations worker card:
  - active backend: `onnxruntime` or `tensorrt_engine`
  - provider/artifact id
  - fallback reason if ONNX was used

Avoid making operators choose an engine manually in the first pass. The worker should pick the best validated artifact for its own host profile.

## 12. Error Handling

The worker must never crash solely because a TensorRT artifact is unavailable.

Fallback to ONNX when:

- the engine file is missing
- the target profile does not match
- the artifact is not `valid`
- TensorRT cannot load the engine
- output validation fails at startup

Crash only when:

- there is no usable ONNX model fallback
- the operator explicitly disables fallback for benchmark-only runs

Add an optional benchmark flag later, not in the first implementation.

## 13. Testing Strategy

Backend unit tests:

- runtime artifact contract validation
- stale detection when source model hash changes
- API permissions and response shapes
- worker runtime selection prefers valid TensorRT artifact
- worker runtime selection falls back to ONNX for each failure reason

Detector tests:

- fake TensorRT runtime adapter can normalize detections
- unsupported output layout is rejected
- missing engine file produces fallback status

Integration tests:

- register ONNX model
- attach runtime artifact
- mark artifact valid
- camera config includes artifact candidates
- worker logs selected backend or fallback reason

Manual Jetson validation:

- build `yolo26n.jetson.fp16.engine`
- validate with `bus.jpg`
- run one camera with TensorRT artifact active
- remove/rename engine and confirm ONNX fallback
- compare FPS, latency, CPU/GPU utilization, and detection stability against ONNX Runtime

## 14. Rollout Plan

1. Add runtime artifact schema and API with no worker use.
2. Add CLI registration and validation helpers.
3. Add worker runtime selection with ONNX fallback.
4. Add `TensorRtEngineDetector` behind valid artifact selection.
5. Add Operations visibility.
6. Update iMac/Jetson guide with build, validate, fallback, and benchmark steps.
7. Only then change catalog TensorRT entries from `planned` to a target-specific available state.

## 15. Open Questions

- Should runtime artifacts be global model attachments or per-site attachments?
- Should validation run through the API process, the worker process, or a dedicated CLI only?
- Which YOLO output layouts should be supported first: YOLO26 only, or YOLO11/12/26 together?
- Do we need INT8 calibration in the first engine stream, or is FP16 enough?
- Should the UI expose manual artifact preference after automatic selection is proven?

## 16. Success Criteria

- Operators register one ONNX model and one validated TensorRT artifact without duplicating camera model choices.
- Jetson worker chooses the TensorRT artifact only when compatible and valid.
- Jetson worker falls back to ONNX with a visible reason when the artifact is unavailable.
- Camera setup remains simple and portable.
- Raw `.engine` support is no longer advertised as ready until the validation workflow can prove it on the target hardware.
