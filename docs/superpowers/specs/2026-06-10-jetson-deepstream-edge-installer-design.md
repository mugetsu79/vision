# Jetson DeepStream Edge Installer Design

Date: 2026-06-10

## Research Summary

NVIDIA positions DeepStream as an accelerated intelligent video analytics framework for Jetson and GPU platforms. For the current Jetson Orin product lane, the first supported target should be DeepStream 7.1 on JetPack 6.1 / L4T 36.4. NVIDIA's DeepStream 7.1 install guide maps Jetson setup to JetPack 6.1 GA / L4T 36.4 and lists Jetson Orin devices as supported platforms: https://docs.nvidia.com/metropolis/deepstream/7.1/text/DS_Installation.html. The current DeepStream install guide maps DeepStream 9.0 Jetson setup to JetPack 7.1, so DeepStream 9.0 is a future lane rather than the first Orin package target: https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Installation.html.

NVIDIA publishes DeepStream containers for Jetson and dGPU, but the images are platform-specific. The Jetson container family is `deepstream-l4t`, and NVIDIA notes that some multimedia libraries may need installation through `user_additional_install.sh` inside the container depending on stream and codec needs: https://docs.nvidia.com/metropolis/deepstream/7.1/text/DS_docker_containers.html.

DeepStream custom detector support is centered on `nvinfer` configuration. For ONNX and prebuilt TensorRT engines, the config must point at model and engine files, and detectors usually require a custom bounding-box parser shared library loaded through `custom-lib-path` / `parse-bbox-func-name`: https://docs.nvidia.com/metropolis/deepstream/7.1/text/DS_using_custom_model.html.

The `deepstream-app` reference configuration has the pieces Vezor needs for a first production pipeline: sources, streammux, primary inference, tracker, on-screen display, sinks, message conversion/consumer, analytics, and performance measurement controls: https://docs.nvidia.com/metropolis/deepstream/7.1/text/DS_ref_app_deepstream.html.

Ultralytics documents a YOLO26 + DeepStream + TensorRT Jetson path and maps JetPack 6.1 to DeepStream 7.1. Their guide uses the community `DeepStream-Yolo` project for YOLO parser/config support; Vezor should treat that repository as a reference or vendored dependency only after license and ABI review, not as an unpinned runtime fetch: https://docs.ultralytics.com/guides/deepstream-nvidia-jetson. Ultralytics also documents ONNX and TensorRT exports for YOLO models, including the TensorRT optimization benefits and export arguments: https://docs.ultralytics.com/integrations/tensorrt and https://docs.ultralytics.com/modes/export.

NVIDIA's DeepStream Python bindings repository currently states DeepStream SDK 9.0 support and says Python bindings are deprecated, recommending PyServiceMaker from DeepStream 9 onward. Vezor should avoid making Python bindings the long-term core pipeline API. A small Python bridge can remain acceptable for the first DeepStream 7.1 lane if the DeepStream metadata extraction itself is native or process-output based: https://github.com/NVIDIA-AI-IOT/deepstream_python_apps.

## Decision

Add a second Jetson edge installer/runtime family named `deepstream`, separate from the current Python/ONNX Runtime/TensorRT worker family.

The existing `jetson-edge` package remains the default portable edge installer. The DeepStream lane is opt-in, installed with an explicit runtime-family flag and backed by a DeepStream-specific image, runtime artifact bundle, worker launcher, service evidence, and live smoke.

Before implementing the DeepStream lane, add a no-DeepStream optimization track for the current `python` Jetson runtime. The live Orin evidence on 2026-06-10 showed TensorRT and CUDA providers are present, but the active worker is spending most of its CPU in RTSP/H.264 decode, raw BGR transfer, and preview encode. That can be improved without DeepStream by fixing the existing Jetson GStreamer capture path, preferring NVIDIA decode/resize, avoiding misleading software-fallback logs, and using hardware H.264 encode where the product publishes processed renditions.

This avoids three bad product outcomes:

- The normal edge installer does not become blocked by DeepStream registry access, NGC login, or JetPack/DeepStream compatibility.
- A plain TensorRT `.engine` is not treated as a complete DeepStream deployment; DeepStream needs engine, labels, `nvinfer` config, parser library, pipeline config, and ABI metadata.
- Operators can see which scenes run through the current Vezor worker and which scenes run through the NVIDIA Metropolis / DeepStream pipeline.
- The immediate Jetson performance work does not wait for the larger DeepStream packaging and parser ABI work.

## Goals

- Reduce CPU load in the current Jetson `python` runtime without DeepStream by using Jetson hardware decode/resize/encode where available.
- Provide an installable Jetson Orin edge runtime family that runs Ultralytics YOLO fixed-vocabulary models through DeepStream `nvinfer`, TensorRT, NVIDIA decode/encode, and NVIDIA tracker components.
- Keep the current Python edge worker available and fully supported.
- Build and distribute a DeepStream runtime artifact bundle from Vezor Model Management.
- Let Scene setup select a DeepStream-capable runtime only when the target edge node reports compatible DeepStream capabilities and the required bundle is synced.
- Preserve Vezor control-plane semantics: tenant ownership, node credentials, camera secret handling, runtime readiness, history, evidence, billing usage, and Core Link posture.
- Validate the lane through real Jetson service evidence and real RTSP live smoke before marking it PASS.
- Make central-worker runtime selection honest: Dockerized Linux central workers on a MacBook Pro M4 are CPU-only today; Apple GPU acceleration requires a separate native macOS/CoreML supervisor lane.

## Non-Goals

- Replacing the current Python edge worker.
- Supporting open-vocabulary YOLOE/YOLO-World in DeepStream in the first lane.
- Supporting DeepStream 9.0 on the current Orin package until the Jetson has a JetPack 7.x image and the product has a separate validation record.
- Depending on Python DeepStream bindings as the long-term production metadata path.
- Downloading third-party parser code at install time.
- Storing RTSP credentials, bearer tokens, bootstrap tokens, or node credentials in committed configs, screenshots, logs, or generated docs.

## Support Matrix

| Target | Status | Runtime | Notes |
| --- | --- | --- | --- |
| Jetson Orin, JetPack 6.1 / L4T 36.4 | First supported lane | DeepStream 7.1, `deepstream-l4t` | Official NVIDIA/Ultralytics mapping; required for first PASS. |
| Jetson Orin, JetPack 6.2 / L4T 36.5 | Candidate lane | DeepStream 7.1 only after live validation | Installer may allow a guarded `--accept-candidate-deepstream-l4t` flag, but smoke result is BLOCKED/FAIL until proven. |
| Jetson Thor / JetPack 7.1 | Future lane | DeepStream 9.0 | Separate package target, separate parser/build validation, and PyServiceMaker review. |
| x86 dGPU | Out of scope | DeepStream dGPU container | Useful later for lab validation, not part of this Jetson installer. |

## Runtime Families

Introduce an explicit runtime family dimension:

- `python`: current Vezor edge worker using ONNX Runtime, Ultralytics, TensorRT engine artifact support, and the existing `argus.inference.engine` entrypoint.
- `deepstream`: NVIDIA DeepStream worker using a DeepStream image, generated pipeline configs, YOLO parser library, `nvinfer`, `nvtracker`, GPU decode/encode, and a Vezor bridge.

Runtime family is independent from node role. The package target remains a Jetson edge node, but the installed worker implementation changes.

Within the `python` runtime family, add a hardware acceleration policy rather than a new family:

- `auto`: default. Probe host capabilities and choose the best safe path.
- `jetson-hw`: require Jetson GStreamer hardware decode/resize/encode support; fail clearly when unavailable.
- `software`: force the existing CPU fallback for diagnostics.

This policy must be visible in runtime reports and passport summaries so a scene cannot silently fall back from TensorRT or hardware media processing without operator-visible evidence.

Installer interface:

```bash
sudo /opt/vezor/current/installer/linux/install-edge.sh \
  --api-url https://MASTER.example/api \
  --pairing-code "$PAIRING_CODE" \
  --session-id "$SESSION_ID" \
  --edge-name EDGE \
  --runtime-family deepstream \
  --manifest /opt/vezor/current/installer/manifests/dev-example.json
```

The existing behavior is equivalent to `--runtime-family python`.

The current `python` family can also accept a hardware policy in the local edge config:

```json
{
  "runtime_family": "python",
  "media_acceleration": "auto"
}
```

Installer defaults should remain safe: `runtime_family=python`, `media_acceleration=auto`.

## No-DeepStream Jetson Optimization Path

The first optimization pass should improve the current worker before the DeepStream lane is built.

Live evidence from the Jetson Orin showed:

- ONNX Runtime providers inside the edge supervisor container include `TensorrtExecutionProvider`, `CUDAExecutionProvider`, and `CPUExecutionProvider`.
- PyTorch CUDA is available.
- TensorRT engine build passed on the Jetson.
- The active workload is CPU-heavy, with the highest CPU in GStreamer/FFmpeg media processes rather than in the supervisor runner.
- `nvv4l2decoder`, `nvvidconv`, and `nvv4l2h264enc` are present; `nvvideoconvert` and `omxh264dec` are not present.
- Logs currently make the fallback hard to interpret because a software GStreamer fallback can be reported as native.

Required changes:

- Make the Jetson RTSP capture path prefer `rtspsrc ! rtph264depay ! h264parse ! nvv4l2decoder ! nvvidconv` and only fall back to `avdec_h264` with a distinct, truthful runtime report.
- Keep color conversion and host copies as late and small as possible. If a scene asks for 720p processing, resize on the NVIDIA media path before the BGR frames enter Python.
- Publish processed browser renditions with `nvv4l2h264enc` when available. Fall back to software encoder only with a readiness/runtime reason.
- Record media pipeline mode in runtime reports: `jetson_gstreamer_native`, `jetson_gstreamer_software`, `ffmpeg_software`, and `encoder_hardware`/`encoder_software`.
- Add a single installation-time link/performance `.bin` fixture and run one throughput test after edge installation so Core Link can report meaningful measured bandwidth instead of `0 Mbps`.
- Preserve the existing Python tracker and evidence/billing paths; this is not a semantic rewrite.

This path will not eliminate every CPU copy. The Python worker still consumes frames in host memory, and tracker/postprocess work still runs in Python. The target is a measurable drop in decode/resize/encode CPU and a nonzero GR3D/VIC/NVENC signal, not full DeepStream-level zero-copy batching.

## Central Hardware Acceleration

Central optimization is possible, but the current deployed central worker is a Linux Docker container on a MacBook Pro M4. That container currently reports only CPU-oriented ONNX Runtime providers. It cannot use Apple GPU/Neural Engine acceleration through CUDA or TensorRT, and it does not get CoreML acceleration while running as the existing Linux container.

Add central acceleration as a separate native-supervisor lane:

- `central-docker-linux`: current path, CPU provider only unless the host is a Linux GPU machine with a mapped provider.
- `central-native-macos`: future macOS supervisor/worker package that runs outside Docker and can probe/use `CoreMLExecutionProvider` when present.
- `central-native-linux-cuda`: future Linux dGPU control-plane worker using CUDA/TensorRT when a supported NVIDIA GPU and runtime are present.

Runtime selection must detect provider availability at worker startup and report the selected provider. It must not show a Jetson TensorRT artifact as the effective runtime for a central Mac scene. A shared model may have a Jetson artifact, but central scenes should display the central-compatible runtime selected for their target profile.

## Artifact Model

Add `deepstream_bundle` as a runtime artifact kind.

The bundle is target-specific and contains:

- `model.engine` or an ONNX source plus a deterministic engine build command record.
- `labels.txt` in the exact class order used by the model.
- `nvinfer_primary.txt` with `onnx-file`, `model-engine-file`, `custom-lib-path`, `parse-bbox-func-name`, `network-type`, precision, batch size, and input dimensions.
- `deepstream_app_template.txt` or a structured pipeline template rendered per scene.
- `libnvdsinfer_custom_impl_vezor_yolo.so` plus parser ABI metadata.
- `manifest.json` with model id, runtime artifact id, source model hash, target profile, DeepStream version, TensorRT version, CUDA/L4T fingerprint, precision, input shape, class hash, parser symbol name, and created-at timestamp.
- optional INT8 calibration cache when precision is `int8`.

Runtime backend string:

- `deepstream_tensorrt`

The artifact kind and backend are intentionally distinct from `tensorrt_engine`. A DeepStream bundle may include a TensorRT engine, but DeepStream needs additional configuration and parser material to run correctly.

## Installer And Packaging

Manifest additions:

```json
{
  "images": {
    "edge-worker": { "reference": "vezor/edge-worker:portable-demo" },
    "edge-worker-deepstream": { "reference": "vezor/edge-worker-deepstream:portable-demo" }
  },
  "deepstream": {
    "supported_l4t": [
      {
        "l4t": "36.4",
        "jetpack": "6.1",
        "deepstream": "7.1",
        "base_image": "nvcr.io/nvidia/deepstream-l4t:7.1"
      }
    ],
    "candidate_l4t": [
      {
        "l4t": "36.5",
        "jetpack": "6.2",
        "deepstream": "7.1",
        "requires_accept_flag": true
      }
    ]
  }
}
```

The exact NGC image tag is manifest-owned so release builds can pin a digest. Dev builds may use a tag, but pilot/stable manifests must use immutable digest references.

Packaging files:

- `backend/Dockerfile.edge.deepstream`: builds from the manifest DeepStream base image, runs the DeepStream multimedia install script, compiles the Vezor YOLO parser shared library, installs only the Vezor bridge dependencies, and copies source after dependency layers for rebuild cache efficiency.
- `infra/install/compose/compose.edge.deepstream.yml`: runs supervisor plus the DeepStream worker image with NVIDIA runtime/device access, model/artifact volumes, credentials, NATS leaf, and MediaMTX.
- `infra/install/systemd/vezor-edge.service`: remains the edge appliance service but receives `VEZOR_EDGE_RUNTIME_FAMILY=deepstream` through `/etc/vezor/edge.json` or `/etc/vezor/edge.env`.
- `installer/linux/install-edge.sh`: validates DeepStream compatibility before build/start, selects the correct image key, and refuses candidate L4T without the explicit candidate flag.

## DeepStream Worker Architecture

The first production design uses a native DeepStream runner plus a Vezor bridge:

```mermaid
flowchart LR
  A["Supervisor reconciler"] --> B["Worker launcher"]
  B --> C["DeepStream runner"]
  C --> D["RTSP source"]
  C --> E["nvinfer + YOLO parser"]
  E --> F["nvtracker"]
  F --> G["metadata JSONL over Unix socket"]
  G --> H["Vezor bridge"]
  H --> I["backend worker telemetry/events"]
  C --> J["annotated or clean stream sink"]
  J --> K["edge MediaMTX"]
```

Responsibilities:

- Supervisor still fetches desired scene state and starts/stops one worker per scene.
- Worker launcher chooses `argus.inference.engine` for `python` scenes and `argus.inference.deepstream_bridge` for `deepstream` scenes.
- DeepStream runner renders per-scene configs from the downloaded bundle and camera worker config.
- RTSP credentials are read from worker config or local secret files at process start and are never written into committed configs or unredacted logs.
- Native DeepStream metadata is normalized to Vezor detections: object id, class id/name, confidence, bounding box, frame timestamp, source timestamp, track id, and runtime stats.
- Vezor bridge posts detections, history samples, evidence triggers, runtime heartbeat, and billing usage through the same authenticated node credential path used by the current edge worker.

The first lane supports one scene per DeepStream runner process. Multi-scene batching can be added after the single-scene correctness smoke is green.

## Scene Capability And Readiness

Scene setup must display DeepStream as available only when all conditions are true:

- Target node reports `runtime_family=deepstream`.
- Target node reports compatible L4T, JetPack, DeepStream, TensorRT, CUDA, and NVIDIA container runtime.
- Selected model has a valid `deepstream_bundle` artifact for the node target profile.
- The artifact is synced to the node.
- The scene uses fixed-vocabulary detection.
- The selected tracker is a DeepStream-supported tracker mapping.

If any condition is missing, the UI must show a concrete readiness reason such as:

- `DeepStream runtime not installed on EDGE`
- `DeepStream bundle not built for linux-aarch64-nvidia-jetson`
- `DeepStream bundle not synced to EDGE`
- `Open-vocabulary models are not supported by DeepStream runtime`
- `JetPack/L4T candidate requires live validation`

## Hardware And Service Evidence

The edge supervisor hardware probe adds a DeepStream capability block:

```json
{
  "runtime_families": ["python", "deepstream"],
  "deepstream": {
    "installed": true,
    "version": "7.1",
    "l4t": "36.4",
    "jetpack": "6.1",
    "tensor_rt": "10.x",
    "cuda": "12.x",
    "plugins": ["nvinfer", "nvtracker", "nvurisrcbin", "nvdsosd"],
    "container_runtime": "nvidia",
    "base_image": "sha256:<pinned-digest>"
  }
}
```

The smoke report cannot mark DeepStream PASS without service-manager evidence:

- `systemctl status vezor-edge.service`
- `docker ps` or `podman ps` showing the DeepStream worker image
- `deepstream-app --version-all` from inside the container
- `gst-inspect-1.0 nvinfer nvtracker nvurisrcbin nvdsosd`
- generated pipeline config with RTSP credentials redacted
- runtime logs showing frames processed and model metadata loaded
- Vezor UI/API showing detections/history/evidence generated from the real RTSP stream

## Security And Secrets

- No RTSP URL with credentials may be written to committed docs, runtime artifact manifests, screenshots, or unredacted logs.
- Node credentials, bearer tokens, bootstrap tokens, reflector secrets, and Keycloak/admin credentials remain in local secret files or environment variables only.
- DeepStream config files generated on the edge must live under `/var/lib/vezor/runtime/deepstream/<camera_id>/` with owner-readable permissions.
- Logs must redact credentialed RTSP URIs to `rtsp://***:***@host`.
- Third-party parser code must be pinned by commit and reviewed for license compatibility before vendoring. Runtime install must never `git clone` parser code from the public internet.

## Validation Strategy

Unit and integration tests:

- Jetson media pipeline selection prefers the NVIDIA hardware decode path when `nvv4l2decoder` and `nvvidconv` are present.
- Jetson media pipeline fallback labels software GStreamer and FFmpeg paths truthfully in runtime reports and logs.
- Processed browser-stream publishing selects `nvv4l2h264enc` when available and reports software fallback when not.
- Runtime reports include selected inference provider, runtime artifact id when applicable, media pipeline mode, encoder mode, scene contract hash, and fresh heartbeat timestamps.
- Central Docker workers never advertise a Jetson TensorRT artifact as the effective central runtime. Runtime summaries must filter artifacts by target profile and selected node.
- Native macOS central worker capability tests are pending until a native supervisor package exists. Until then, MacBook Pro M4 central acceleration remains NOT RUN/BLOCKED, not PASS.
- Manifest schema accepts `deepstream` metadata and `edge-worker-deepstream`.
- Installer help exposes `--runtime-family` and candidate L4T guard.
- Installer selects `edge-worker-deepstream` only for the DeepStream runtime family.
- DeepStream Dockerfile keeps dependency layers before source copy and includes parser build steps.
- Runtime artifact schema and OpenAPI include `deepstream_bundle` and `deepstream_tensorrt`.
- Runtime selection prefers `deepstream_tensorrt` only when the artifact target matches and fallback policy allows it.
- Worker launcher emits a DeepStream command for DeepStream scenes and the existing Python command for current scenes.
- Camera worker config includes DeepStream bundle paths without secret material.
- Hardware probe reports DeepStream capability only when commands and plugins are present.
- UI readiness messages distinguish missing runtime, missing bundle, missing sync, and unsupported model class.

Live smoke gates:

- Current `python` Jetson runtime runs the real RTSP scene with TensorRT artifact selected, hardware decode active, processed stream available, detections/history/evidence present, billing usage generated, and runtime reports heartbeating after restart.
- Current `python` Jetson runtime captures before/after CPU, memory, GR3D/VIC/NVENC, FPS, and stream availability. PASS requires a measured improvement, not merely provider availability.
- Central MacBook Pro M4 control-plane smoke reports CPU provider honestly for Docker mode. Native CoreML acceleration must be marked NOT RUN until a native macOS worker exists and is exercised.
- Fresh Jetson edge install with `--runtime-family deepstream`.
- DeepStream image builds or pulls without relying on hot patches.
- A YOLO26 fixed-vocabulary DeepStream bundle is built, registered, validated, and synced to the Jetson.
- A real RTSP scene runs through DeepStream and produces detections, track history, evidence, processed stream, billing usage, and supervisor heartbeat.
- Service evidence is captured before PASS.
- Candidate L4T combinations are marked BLOCKED or FAIL until the real smoke passes.

## Rollout

1. Dev lane: add optional DeepStream installer and run single-scene fixed-vocabulary YOLO smoke on the lab Orin.
2. Pilot lane: pin DeepStream image digests, parser commit, and model bundle hashes; require release gate coverage.
3. Stable lane: add multi-scene batching, INT8 calibration workflow, and an upgrade guide once soak evidence is recorded.

## Open Risks

- The current Orin may be JetPack 6.2 / L4T 36.5, while the official DeepStream 7.1 mapping is JetPack 6.1 / L4T 36.4. This must be a live compatibility gate, not a silent assumption.
- Jetson GStreamer plugin availability varies by JetPack/container image. The optimized Python runtime must probe the actual container and report a software fallback instead of assuming NVIDIA elements exist.
- Hardware decode can reduce CPU while still leaving Python postprocess/tracker work as the bottleneck. The acceptance gate must measure end-to-end worker CPU and FPS, not only whether the NVIDIA plugins load.
- Apple GPU acceleration for the central control plane requires a native macOS worker package. It cannot be validated from the current Linux Docker central stack on the MacBook Pro M4.
- Shared model records with target-specific runtime artifacts can confuse UI summaries. Runtime artifact display must be scoped by selected scene target, processing mode, and target profile.
- YOLO26 DeepStream parsing requires a maintained parser ABI. Vezor should own or vendor a reviewed parser instead of fetching community code during install.
- DeepStream Python bindings are not a durable long-term integration path. The first lane should constrain Python to Vezor-side process orchestration/bridge code.
- `deepstream-l4t` registry access may require NGC credentials. The installer must fail with a clear message and never ask users to paste credentials into committed manifests.
