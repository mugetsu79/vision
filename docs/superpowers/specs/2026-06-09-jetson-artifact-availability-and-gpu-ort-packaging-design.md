# Jetson Artifact Availability and Automatic GPU ORT Packaging Design

## Status

Planned follow-up from the 2026-06-09 installed-product smoke. The Jetson
TensorRT build can produce an engine, but the installed UI can still show stale
missing-artifact rows and the dev edge image still requires an operator-provided
Jetson GPU ONNX Runtime wheel URL unless CPU fallback is explicitly allowed.

## Problem

The Orin has TensorRT engine files on disk, including
`/var/lib/vezor/models/runtime-artifacts/6d0e6ffb-fa14-454d-bdbc-03225c22b922/yolo26n.engine`,
but the master UI still displays missing artifacts for static paths such as
`models/yolo26n.engine`. The master DB also recorded the live-built artifact as
`validation_status=unvalidated`, so runtime selection cannot safely treat it as
ready.

At the same time, the Jetson edge image build currently expects
`JETSON_ORT_WHEEL_URL` to be supplied manually. That is acceptable as a lab
escape hatch, but not as product packaging. A packaged Jetson install should
resolve the correct accelerated ONNX Runtime wheel from a trusted manifest or
prebaked release image and verify it by digest.

## Goals

- Make Jetson GPU ONNX Runtime packaging automatic for product and dev-manifest
  edge installs.
- Keep manual `--jetson-ort-wheel-url` only as an override, not the normal path.
- Verify the wheel by SHA256 before install and fail closed when no compatible
  GPU wheel is available.
- Remove stale static TensorRT artifact expectations from the operator UI.
- Reconcile the actual edge-built TensorRT engine path into the master runtime
  artifact registry.
- Mark runtime artifacts `valid` only after the edge confirms the file exists
  and the artifact metadata matches model hash, target profile, size, and SHA256.
- Show actionable UI state: no validated artifact, artifact building, artifact
  built but unvalidated, artifact valid, or artifact missing on target.

## Non-Goals

- Copying TensorRT engines from macOS to Jetson. Engines remain target-local.
- Making CPU ONNX Runtime a product fallback for Jetson packaged installs.
- Replacing TensorRT build/validation with static catalog engine rows.
- Shipping raw secrets or private wheel URLs in docs, logs, or manifests.

## Product Flow

1. The release manifest contains Jetson ORT wheel entries keyed by JetPack/L4T,
   architecture, Python ABI, URL, and SHA256.
2. The edge installer runs preflight, detects Jetson OS/Python/architecture, and
   resolves the matching wheel entry automatically.
3. `backend/Dockerfile.edge` downloads the resolved wheel, verifies SHA256, and
   installs it into the edge virtualenv. Product builds fail if the wheel is
   missing or digest verification fails.
4. After edge image build, the installer runs a small provider probe inside the
   image and records ONNX Runtime providers in installer evidence.
5. When a TensorRT build job completes on the Jetson, the edge supervisor posts
   the actual artifact path and digest to the master.
6. The master stores or updates a `model_runtime_artifacts` row for the actual
   path under `/models/runtime-artifacts/...`, then validates that the latest
   edge inventory contains the same file and SHA256 before marking it `valid`.
7. The Models UI lists actual runtime artifacts and does not show static
   `models/yolo26*.engine` entries as missing product artifacts.

## Acceptance Criteria

- A normal Jetson edge install does not require `--jetson-ort-wheel-url`.
- The installed edge image reports accelerated ONNX Runtime providers from
  inside the container.
- `--allow-cpu-onnx-runtime` remains available only for explicit diagnostics and
  is reported as non-product evidence.
- Building YOLO26n TensorRT on Orin creates a runtime artifact row with the
  actual `/models/runtime-artifacts/.../yolo26n.engine` path.
- The artifact row reaches `validation_status=valid` after inventory confirms
  the file exists on the target edge.
- The UI shows the valid artifact and no longer asks the operator to register a
  missing static `models/yolo26n.engine` path when the runtime-artifacts path is
  present and valid.
