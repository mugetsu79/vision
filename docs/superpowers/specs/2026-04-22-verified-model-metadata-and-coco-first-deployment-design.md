# Verified Model Metadata And COCO-First Deployment Design

## Goal

Make the default Vezor deployment path correct and easy to operate when using standard COCO-style ONNX detection models, while keeping custom reduced-class models as an advanced optional path. The system must stop accepting model metadata that disagrees with the actual ONNX file, because that mismatch breaks detection, query resolution, and live operations in ways that are hard to diagnose after deployment.

## Current State

- The current model API accepts operator-supplied `classes` and persists them as the model inventory in [backend/src/argus/api/contracts.py](/Users/yann.moren/vision/backend/src/argus/api/contracts.py:39) and [backend/src/argus/api/v1/models.py](/Users/yann.moren/vision/backend/src/argus/api/v1/models.py:25).
- The worker detector interprets output logits using `DetectionModelConfig.classes` in [backend/src/argus/vision/detector.py](/Users/yann.moren/vision/backend/src/argus/vision/detector.py:18).
- The natural-language query layer builds its allowed class vocabulary from `Model.classes` in [backend/src/argus/services/query.py](/Users/yann.moren/vision/backend/src/argus/services/query.py:124).
- Camera `active_classes` narrow what a camera operationally cares about in [backend/src/argus/inference/engine.py](/Users/yann.moren/vision/backend/src/argus/inference/engine.py:493), and the Dashboard mirrors that narrowing in [frontend/src/lib/live.ts](/Users/yann.moren/vision/frontend/src/lib/live.ts:15).
- The iMac/Jetson lab guide currently instructs operators to register `yolo12n.onnx` as if it were already a six-class model in [docs/imac-master-orin-lab-test-guide.md](/Users/yann.moren/vision/docs/imac-master-orin-lab-test-guide.md:498) and [docs/imac-master-orin-lab-test-guide.md](/Users/yann.moren/vision/docs/imac-master-orin-lab-test-guide.md:858).

## Problem Statement

The default path is currently unsafe because it lets operators describe a standard COCO ONNX model as if it were a custom reduced-class model. That creates a deep mismatch across the stack:

- the detector interprets class logits with the wrong class map
- query resolution uses the wrong allowed vocabulary
- `active_classes` and query scope operate on a false inventory
- the live wall shows zero detections or nonsensical detections even though the stream is healthy

This is not an operator-tweak problem. It is a deployment contract problem. The repository and the lab guide currently make it too easy to register a model incorrectly from the start.

## Requirements

### Functional

- The default deployment path must work with a standard COCO-style ONNX model without requiring operators to hand-author class lists.
- Model registration and update must validate operator metadata against the ONNX file when the ONNX is self-describing.
- If an ONNX file exposes class metadata, that metadata must become the source of truth for the stored model class inventory.
- Camera `active_classes` must remain the correct place to narrow the operational interest set for a camera.
- Natural-language query resolution must continue to narrow behavior at runtime, but only against the verified model inventory.

### Operational

- Default lab bring-up on the iMac must use a COCO-base model and then constrain the camera to the six classes Vezor cares about most.
- The lab guide must clearly distinguish the default COCO-first path from the advanced optional custom-model path.
- Error messages for model registration mismatches must be clear enough for operators to fix the issue without digging into code.

### API And UX

- Operators should be able to omit `classes` when registering a self-describing ONNX model.
- If supplied `classes` disagree with embedded ONNX metadata, the API should reject the request rather than warn and proceed.
- The frontend camera and model flows should stop implying that a standard YOLO filename such as `yolo12n.onnx` is already a six-class custom model.

## Non-Goals

- Replacing YOLO-style ONNX detectors with a different detector family.
- Making Vision Transformers part of the default deployment path.
- Designing a full model catalog/productization system in this slice.
- Supporting arbitrary override of verified ONNX metadata in the common deployment path.
- Removing the existing natural-language query feature.

## Vision Transformers

Alternative detector families, including Vision Transformer-based detectors, remain future-compatible but out of scope for this design. The current stack, deployment docs, and worker runtime are all built around YOLO-style ONNX object detection with explicit class inventories and tracker integration. The default deployment contract should become reliable before broadening the supported detector family surface.

## Approaches Considered

### Approach 1: Warning-Only Metadata Validation

Accept operator-supplied model classes even when the ONNX metadata disagrees, but emit warnings.

Pros:
- minimal API disruption
- preserves maximum flexibility

Cons:
- keeps the exact failure mode that broke the lab workflow
- allows deployments that look valid but fail during inference
- leaves query resolution and class filtering built on false metadata

### Approach 2: Strict Verified-Metadata Default With COCO-First Deployment

Treat embedded ONNX metadata as source of truth when available. Auto-populate classes from the ONNX by default, reject mismatches, and make class narrowing happen at the camera/query layer.

Pros:
- prevents silent class-map mismatches
- aligns the detector, query inventory, and UI filtering with the same truth
- fits the current codebase architecture
- gives operators the easiest default path with standard COCO models

Cons:
- introduces stricter API behavior for model registration
- requires docs and tests to be updated together

### Approach 3: Separate Model Profiles Up Front

Introduce explicit model families such as `coco-foundation` and `custom-reduced-class`, each with separate registration UX and validation rules.

Pros:
- more explicit long-term product model
- could support future detector families cleanly

Cons:
- larger change surface than needed
- slows the immediate fix for the broken default deployment path

## Recommendation

Choose **Approach 2**.

The repository should default to a verified COCO-base deployment contract. The class inventory should come from the ONNX when possible. Cameras and natural-language queries should narrow from that verified class space. Custom reduced-class models should remain supported, but as an explicit advanced path rather than the default assumption.

## Chosen Design

### 1. Verified Model Metadata Contract

Model registration and update should follow this contract:

- If the uploaded or referenced ONNX model exposes embedded class metadata, Vezor extracts it and treats it as canonical.
- If the operator omits `classes`, Vezor stores the extracted class inventory automatically.
- If the operator supplies `classes` and they match the extracted inventory exactly, the request succeeds.
- If the operator supplies `classes` and they do not match the extracted inventory, the request fails with a `422` validation error explaining the mismatch.
- If the ONNX does not expose usable metadata, Vezor allows manual classes but should treat the model as operator-declared rather than verified.

This produces a fail-closed default path. Broken metadata should not reach runtime.

### 2. COCO-First Default Deployment

The default deployment path for local bring-up and the lab guide should assume:

- the operator is using a standard COCO-style ONNX model
- the model inventory remains the full model inventory
- the system narrows attention later through camera `active_classes`

For the current lab setup, that means:

- the model record for `yolo12n.onnx` should resolve to the embedded COCO class inventory
- the `HOME` camera should set `active_classes` to:
  - `person`
  - `car`
  - `bus`
  - `truck`
  - `motorcycle`
  - `bicycle`

This preserves a truthful detector class space while still letting Vezor focus on the six operationally important classes.

### 3. Clear Separation Of Responsibilities

The stack should explicitly treat these as different layers:

- **Model inventory:** the full class space the ONNX model can emit
- **Camera active classes:** what a specific camera operationally cares about
- **Query scope resolution:** runtime narrowing of a selected set of cameras based on user intent
- **Dashboard overlay filtering:** view-layer reflection of the active runtime class scope

The model layer must never be used as a shortcut to simulate per-camera filtering.

### 4. Query Layer Contract

The natural-language query feature already does the right conceptual job: it maps a prompt such as “only show cars” into a class subset from the allowed inventory in [backend/src/argus/llm/parser.py](/Users/yann.moren/vision/backend/src/argus/llm/parser.py:31). The design keeps that feature, but changes its foundation:

- allowed query vocabulary must come from verified `Model.classes`
- query scope should continue to publish runtime `active_classes` commands to cameras
- Dashboard filtering should continue to mirror the resolved class subset without redefining model truth

If query resolution fails, operators should still be able to understand whether the problem is:

- authorization/quota
- missing cameras
- missing NATS/query publisher
- or invalid model inventory

### 5. Advanced Optional Custom-Model Path

Custom reduced-class models remain supported, but the docs must present them as advanced:

- obtain or train a custom model
- export to ONNX
- register it with matching metadata
- optionally use a separate model record name such as `YOLO12n Custom 6-Class`

The guide should stop implying that a generic `yolo12n.onnx` file is already that custom model.

## Documentation Changes

### README And Runbook

- Clarify that `models/` is the local file location only, not proof that a file is a custom Vezor model.
- Add a short statement that standard YOLO ONNX files typically carry their own class inventory and that Vezor validates that metadata on registration.

### iMac / Jetson Lab Guide

Update [docs/imac-master-orin-lab-test-guide.md](/Users/yann.moren/vision/docs/imac-master-orin-lab-test-guide.md) so that:

- the default path registers `yolo12n.onnx` as a standard COCO model
- the camera setup step applies six-class `active_classes`
- the guide explicitly says the natural-language query layer and camera scope narrow from the full model inventory
- the advanced custom-model path is separated into its own section
- troubleshooting includes the exact symptom we saw: “model file is COCO, but model record was registered as reduced-class”

### UI Copy And Examples

- Any example or copy that currently implies `yolo12n.onnx` equals a six-class model should be corrected.
- Camera wizard defaults should continue to allow empty `active_classes`, but docs and examples should explain when to set them explicitly.

## Validation Plan

### Backend

- unit-test model creation/update against:
  - self-describing ONNX with omitted `classes`
  - self-describing ONNX with matching `classes`
  - self-describing ONNX with mismatched `classes`
  - non-self-describing ONNX with manual `classes`
- unit-test query inventory to ensure allowed classes come from verified model metadata
- unit-test worker config generation to ensure full model inventory and narrowed camera `active_classes` can coexist correctly

### Docs

- verify the lab guide’s default commands produce a truthful model registration path
- verify the guide’s camera configuration narrows via `active_classes` rather than falsifying model metadata

### Manual Operator Flow

- register a standard COCO `yolo12n.onnx`
- confirm the stored model class count matches embedded metadata
- set camera `active_classes` to the six operational classes
- run a query such as “only show cars”
- confirm the resolved classes and live overlay narrowing work without model-metadata edits

## Risks

- Some existing tests or fixtures may assume manual model classes are always authoritative and will need to be rewritten.
- Strict validation may initially surprise operators who are used to permissive model registration.
- Some ONNX exports may not expose useful metadata. The advanced manual path must remain available for those cases.
- If the current parser logic only handles one exported YOLO tensor layout correctly, additional output-shape normalization may still be required for robust COCO-first runtime behavior. That issue is adjacent to this contract change and should be validated during implementation.

## Success Criteria

The design is successful when:

- a standard COCO ONNX model can be registered correctly without hand-writing six classes
- the system rejects class metadata that contradicts the ONNX
- operators can narrow the deployment to the six classes they care about through `active_classes` and query scope
- the iMac/Jetson lab guide works from a clean checkout without relying on hidden model knowledge
- custom reduced-class models remain possible, but no longer contaminate the default path
