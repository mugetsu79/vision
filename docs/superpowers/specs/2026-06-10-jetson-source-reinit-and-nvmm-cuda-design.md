# Jetson Source Reinitialization And NVMM/CUDA Frame Handling Design

Date: 2026-06-10

Status: follow-on spec after `f862b891` appsink closure.

## Coverage Audit

The previous native capture spec and plan did cover the first no-DeepStream optimization: Jetson RTSP now prefers in-process GStreamer `appsink` with `nvv4l2decoder` and `nvvidconv`, with truthful fallback reporting. They also reserved a `jetson_nvmm_native` lane, but only as an optional interface/scaffold.

They did not fully specify dynamic camera source reinitialization. Existing code can reconfigure the capture target dimensions when a browser-delivery stream profile changes, and camera updates already reprobe source capability when the RTSP URL/source changes. The missing product behavior is tying a source/profile change to a worker-side source reopen, fresh setup preview/calibration still, and runtime evidence that the worker is using the same source profile the UI reports.

This spec covers only the remaining no-DeepStream work:

1. Dynamic source reinitialization on camera source/profile changes.
2. A deeper opt-in NVMM/CUDA frame path that avoids BGR host copies before inference when the TensorRT detector can consume GPU-prepared input.

Hardware H.264 encode is explicitly out of scope for this track because the target Jetson SKU does not have a usable hardware encoder. Processed stream publishing may continue to report `encoder_mode=software`.

## Goals

- When an operator changes the camera source from one RTSP profile/path to another, the worker reopens capture without a service restart.
- Runtime reports, source capability, browser delivery options, setup preview stills, and calibration frame sizes converge on the same source profile.
- Operators see `awaiting first heartbeat` after a source-profile change until a fresh per-camera worker report confirms the new profile.
- The NVMM/CUDA lane remains opt-in and does not change the default appsink path until live evidence beats the appsink baseline.
- The NVMM/CUDA lane avoids converting to CPU BGR before inference when the selected detector supports a GPU frame/input path.

## Non-Goals

- No DeepStream implementation.
- No Dockerized central GPU acceleration claim.
- No hardware encode claim on Jetson SKUs without a verified encoder.
- No registry publishing.
- No calibration math redesign; this track only prevents stale frame-size/still evidence from masquerading as current.

## Dynamic Source Reinitialization

### Current Behavior

- `CameraService.update_camera()` can re-encrypt a changed source, reprobe `source_capability`, and rebuild browser delivery profiles.
- `_publish_camera_command()` publishes runtime, stream, privacy, zones, homography, and detection region updates.
- `InferenceEngine.apply_command()` calls `CameraSource.reconfigure()` only when `CameraCommand.stream` changes.
- `CameraSource.reconfigure()` can reopen capture for target width/height/FPS changes, but it does not receive a new source URI or source profile hash from live commands.
- Setup preview caching invalidates on `camera.updated_at`, but responses do not expose a source profile hash that the UI can use to discard old calibration/still state.

### Source Profile Identity

Add a source profile hash that never exposes raw credentials. The hash input is a canonical JSON object:

```json
{
  "source_kind": "rtsp",
  "source_uri_fingerprint": "64-character sha256 of normalized capture URI",
  "source_capability": {"width": 1280, "height": 720, "fps": 20, "codec": "h264"},
  "stream": {"profile_id": "720p20", "kind": "transcode", "width": 1280, "height": 720, "fps": 20}
}
```

The fingerprint is computed from the normalized capture URI but only the hash is persisted in reports and setup-preview responses. Evidence must continue to redact RTSP credentials.

### Worker Command Contract

Extend camera commands with:

- `camera`: optional `WorkerCameraSettings` containing the current worker source URI/source kind and capture caps.
- `source_capability`: optional `SourceCapability`.
- `source_profile_hash`: optional 64-character hash.

On a source change, the command must include `camera`, `stream`, `source_capability`, and `source_profile_hash`. On a browser-delivery-only profile change, the command may include only `stream` and the new `source_profile_hash`.

### Worker Reopen Rules

The worker reopens capture when any of these change:

- source URI or camera source kind
- source profile hash
- target width/height/FPS for capture
- frame skip

The reopen is atomic: if the new capture cannot produce its first frame, the worker keeps the previous capture running, reports a redacted `last_error`, and does not claim the new source hash as running. Once a first frame arrives, the next runtime report uses the new source profile hash and heartbeat time.

### Setup Preview And Calibration Coherence

`CameraSetupPreviewResponse` should include:

- `source_profile_hash`
- `source_capability`
- `stale` boolean

When a source profile hash changes, cached setup preview images with the old hash are not reused as current. If fresh capture fails and an old still exists, the API can return it only with `stale=true` and the old hash; the UI must display it as stale and keep calibration actions blocked for the new source until a fresh still exists.

Calibration source points remain valid only for the frame size/hash they were captured against. The implementation can either clear source points on hash mismatch or keep them as historical data while requiring a refresh before saving a new calibration.

### Runtime And UI Presentation

Runtime reports should include `source_profile_hash`. Fleet/API presentation should compare the camera's current source profile hash with the latest per-camera runtime report:

- no report: `runtime_status=not_reported`, presentation `awaiting_first_heartbeat`
- report exists but hash differs: `runtime_status=starting`, presentation `awaiting_profile_heartbeat`
- fresh report and hash matches: normal runtime state
- stale report: stale/not fresh, not inferred from supervisor node health

This preserves the decision that central camera workers are running only when a fresh per-camera runtime report exists.

## NVMM/CUDA Frame Handling

### Current Behavior

The appsink path uses Jetson hardware decode/resize, then maps a BGR CPU buffer into NumPy. That removed the `gst-launch` rawvideo process but still pays for host BGR conversion/copy before detection, annotation, privacy filtering, and software stream publishing.

### Target Architecture

Add an opt-in frame envelope and detector fast path:

```python
class CapturedFrame(Protocol):
    width: int
    height: int
    memory_kind: Literal["cpu_bgr", "nvmm", "cuda"]
    source_profile_hash: str | None

    def as_bgr_numpy(self) -> np.ndarray:
        ...

class CudaInferenceInput(Protocol):
    width: int
    height: int
    layout: Literal["nchw"]
    dtype: Literal["float16", "float32", "uint8"]
    device: Literal["cuda"]
```

The engine keeps the current NumPy path as the default. If the frame source returns a `CapturedFrame` and the detector exposes `detect_captured_frame(frame)`, the engine calls that method. The detector may prepare TensorRT input from NVMM/CUDA without calling `as_bgr_numpy()` first. Annotation, privacy, and software publishing may still request CPU BGR after detection because this SKU has no hardware encoder path in scope.

### Native Backend Boundaries

The optional native backend reports `media_capture_backend=jetson_nvmm_native` and records substage timings:

- `capture_wait`
- `capture_decode`
- `capture_resize`
- `capture_cuda_preprocess`
- `capture_bgr_materialize` only when CPU BGR is requested

It remains unavailable unless the Jetson aarch64 image has the required NVIDIA multimedia/GStreamer/CUDA headers and libraries. Missing native pieces are reported as unavailable, not as a product failure.

### Acceptance Criteria

Dynamic source reinitialization is PASS only when:

- Changing RTSP source/profile from 1296p to 720p causes the active worker to reopen capture without a service restart.
- The next fresh per-camera runtime report has the current `source_profile_hash`.
- Setup preview response and calibration UI report the 720p frame size and do not present stale 1296p source points as current.
- If the new source fails, the old worker remains running and UI/API says awaiting or failed profile heartbeat, not pass.

NVMM/CUDA frame handling is PASS only when:

- The lane is opt-in and reports `jetson_nvmm_native`.
- The TensorRT detector path can process at least one live 720p sample without calling `as_bgr_numpy()` before inference.
- Runtime reports are fresh and include source profile hash, media pipeline mode, capture backend, encoder mode, artifact id, provider, and scene contract hash.
- Live smoke beats the appsink baseline of `17.57` FPS or `133-137%` supervisor CPU by at least 10% on either FPS or CPU at the same 720p20 profile.
- If it does not beat appsink, the result is recorded as FAIL or experimental only, and `auto` keeps using appsink.

## Rollback

- Dynamic source reinitialization can be disabled by ignoring camera-source command fields and falling back to supervisor restart behavior.
- NVMM/CUDA remains behind an explicit local setting such as `ARGUS_JETSON_CAPTURE_BACKEND=nvmm` or `jetson_capture_backend=nvmm`.
- `auto` must not select `jetson_nvmm_native` until a live PASS exists for the target image and Jetson profile.
