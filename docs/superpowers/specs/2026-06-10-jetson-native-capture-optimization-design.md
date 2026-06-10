# Jetson Native Capture Optimization Design

Date: 2026-06-10

## Context

Live Jetson Orin evidence on 2026-06-10 showed the edge worker receiving a 720p RTSP source and publishing a 720p20 processed rendition, but the active Python worker sustained roughly 13-15 FPS. A direct source decode sample reached roughly the camera's advertised 20 FPS, so the primary limit is not the nano model alone and is not proven to be the WiFi link. The current no-DeepStream worker still pulls decoded BGR frames through a subprocess rawvideo pipe and copies each frame into NumPy before inference.

The current branch already improved truthful runtime reporting and NVIDIA GStreamer selection. This spec defines the next two optimization tracks:

1. Replace the `gst-launch` rawvideo subprocess capture path with an in-process GStreamer `appsink` backend.
2. Add a future native NVMM/CUDA capture lane that keeps decoded frames on Jetson media/CUDA surfaces longer, behind explicit capability gates and live evidence.

This work stays in the current no-DeepStream Python runtime family. DeepStream remains a later optional runtime family with its own installer, bundle, parser, and smoke evidence.

## Research Summary

NVIDIA's Jetson Linux documentation identifies `nvv4l2decoder` as the accelerated H.264 decoder path and `nvvidconv` as the Jetson conversion/scaling element for accelerated GStreamer pipelines: https://docs.nvidia.com/jetson/archives/r38.2/DeveloperGuide/SD/Multimedia/AcceleratedGstreamer.html.

GStreamer `appsink` is the correct in-process application boundary when frames need to enter Python, and it supports bounded queues and dropped frames through `max-buffers`, `drop`, and newer `leaky-type` controls: https://gstreamer.freedesktop.org/documentation/app/appsink.html.

GStreamer `queue` can be configured with one-buffer leaky behavior so stale decoded frames do not accumulate when inference is slower than source FPS: https://gstreamer.freedesktop.org/documentation/coreelements/queue.html.

GStreamer `rtspsrc` supports `drop-on-latency`, allowing the jitter buffer to preserve a latency bound instead of growing silently: https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html.

NVIDIA's Jetson Multimedia API exposes buffer conversion and layout primitives for native paths that need to work with pitch/block-linear memory and hardware-backed surfaces: https://docs.nvidia.com/jetson/l4t-multimedia/l4t_mm_07_video_convert.html.

NVIDIA's current DeepStream documentation recommends Service Maker for newer Python-facing DeepStream workflows, while Python bindings are deprecated in DeepStream 9. That supports keeping this work separate from the later DeepStream family: https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_service_maker_python.html.

## Goals

- Raise real Jetson no-DeepStream worker throughput for 720p RTSP ingest by removing the subprocess rawvideo pipe and unnecessary user-space buffering.
- Keep the current worker semantics: same scene contracts, detections, history, evidence, billing usage, stream registration, privacy, and runtime-report heartbeat.
- Make capture behavior observable without leaking RTSP credentials or JWTs.
- Keep fallback labels truthful: native Jetson GStreamer, software GStreamer, or FFmpeg software.
- Preserve operator confidence: a faster path is a PASS only with fresh per-camera reports, real RTSP frames, stream availability, and before/after performance evidence.
- Define a native NVMM/CUDA lane that can be built and measured without forcing DeepStream adoption or breaking the Python runtime.

## Non-Goals

- Replacing the Python worker with DeepStream.
- Claiming Dockerized central Mac GPU acceleration.
- Claiming Orin Nano hardware H.264 encode when the active hardware lacks NVENC support.
- Requiring CSI or USB cameras for this optimization.
- Storing raw RTSP credentials, registry credentials, bearer tokens, pairing codes, or JWTs in committed docs, screenshots, tests, logs, or reports.

## Runtime Reporting

The current `media_pipeline_mode` remains the operator-facing acceleration family:

- `jetson_gstreamer_native`: NVIDIA decode/resize path is active.
- `jetson_gstreamer_software`: GStreamer path is active but decode is software.
- `ffmpeg_software`: FFmpeg software decode path is active.

Add a more precise internal/runtime-report field named `media_capture_backend`:

- `gstreamer_appsink`: in-process GStreamer `appsink` backend.
- `gstreamer_rawvideo_pipe`: existing `gst-launch` rawvideo `fdsink` compatibility fallback.
- `opencv_gstreamer`: OpenCV GStreamer fallback.
- `ffmpeg_rawvideo`: FFmpeg rawvideo subprocess fallback.
- `jetson_nvmm_native`: future native NVMM/CUDA backend.

The value must be omitted or `null` only for old reports that predate the field. New reports from the edge worker must include it. A scene is still running only when a fresh per-camera runtime report exists; supervisor node health alone must not imply runtime status.

## Track 1: In-Process GStreamer AppSink

### Architecture

Create a focused `argus.vision.gstreamer_appsink` module that owns GStreamer initialization, pipeline rendering, sample pulling, frame mapping, and sanitized diagnostics. `argus.vision.camera` keeps source selection, reconnect, throttle, and fallback orchestration.

The native Jetson RTSP path becomes:

```text
rtspsrc location=<redacted> protocols=tcp latency=<ms> drop-on-latency=true !
  rtph264depay ! h264parse !
  nvv4l2decoder !
  queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream !
  nvvidconv !
  video/x-raw,format=BGRx,width=<target-width>,height=<target-height> !
  videoconvert !
  video/x-raw,format=BGR,width=<target-width>,height=<target-height> !
  appsink name=sink sync=false max-buffers=1 drop=true emit-signals=false
```

The software GStreamer fallback swaps the decoder path:

```text
rtph264depay ! h264parse ! avdec_h264 ! videoconvert !
  video/x-raw,format=BGR,width=<target-width>,height=<target-height> !
  appsink name=sink sync=false max-buffers=1 drop=true emit-signals=false
```

The first implementation keeps CPU BGR output because the current detector, annotator, privacy filters, and stream publisher operate on NumPy BGR frames. This intentionally does not claim zero-copy. The win is removing the subprocess pipe, bytearray assembly, extra bytes object copy, and process scheduling cost while preserving the worker contract.

### Capability Detection

At worker startup, probe:

- Python GI availability: `gi`, `Gst`, `GstApp`.
- GStreamer initialization.
- `rtspsrc`, `rtph264depay`, `h264parse`, `queue`, `appsink`.
- Native elements: `nvv4l2decoder`, `nvvidconv`.
- Software fallback elements: `avdec_h264`, `videoconvert`.
- Optional properties: `appsink leaky-type`, `nvv4l2decoder disable-dpb`.

Unsupported optional properties must not fail startup. They are enabled only when present on the target Jetson.

### Fallback Policy

For Jetson RTSP/H.264:

1. Try `gstreamer_appsink` with `nvv4l2decoder` and `nvvidconv`.
2. If the first frame is not produced within the configured timeout, release the pipeline and try the existing `gstreamer_rawvideo_pipe` native path.
3. If native GStreamer still fails, try software GStreamer with a truthful `jetson_gstreamer_software` mode.
4. If software GStreamer fails, use FFmpeg software fallback.

Fallback reasons must be recorded in logs and runtime diagnostics with redacted URIs only.

### Timing Metrics

Add capture substage timings:

- `capture_wait`: time waiting for a frame at the worker boundary.
- `capture_decode_read`: time from pull-sample start to NumPy frame availability.
- `capture_pipeline_restart`: time spent rebuilding a pipeline after source/profile changes.

The worker already emits stage summaries; the new backend should feed those summaries instead of adding a second telemetry path.

### Acceptance Criteria

Track 1 is PASS only when all of these are true on the Jetson:

- Active worker uses the sanitized 720p RTSP source selected by the scene.
- Runtime report is fresh and per-camera, not inferred from supervisor health.
- `selected_inference_provider` remains TensorRT when the TensorRT artifact is selected.
- `media_pipeline_mode=jetson_gstreamer_native`.
- `media_capture_backend=gstreamer_appsink`.
- Processed stream is available at the selected browser profile.
- RTSP credentials and JWTs are redacted in evidence.
- Before/after evidence shows FPS, CPU, memory, GR3D/VIC where available, stage timings, and stream readiness.

If FPS does not improve, the result is not a pass. It should be recorded as a truthful FAIL with the measured bottleneck.

## Track 2: Native NVMM/CUDA Lane

### Architecture

Create a separate native backend behind `media_capture_backend=jetson_nvmm_native`. This lane may use a small C++ extension or native helper library, but it must expose the same Python worker-facing capture interface:

```python
class NativeJetsonFrame:
    width: int
    height: int
    format: str
    captured_at_monotonic: float

    def as_bgr_numpy(self) -> np.ndarray:
        raise NotImplementedError
```

The first native milestone can still return NumPy BGR to the existing Python detector. The architectural reason for the native lane is that it creates a clean surface boundary for a later GPU preprocessor and TensorRT binding path, rather than forcing the whole product into DeepStream.

### Native Data Flow

```text
RTSP/H.264
  -> rtspsrc/depayload/parse
  -> nvv4l2decoder
  -> NVMM surface
  -> nvvidconv or NvBufSurfTransform resize/colorspace
  -> native frame object
  -> Python worker
  -> BGR NumPy copy only when the current detector contract requires it
```

The native component must record whether a frame remained in NVMM until the final boundary. A future detector path can then consume CUDA/DLPack-compatible surfaces without reworking camera source selection.

### Build And Packaging

The extension must be optional:

- Build only on Jetson/Linux aarch64 when NVIDIA headers and libraries are present.
- The portable edge image must continue to run when the extension is absent.
- Installer and runtime probes must show `jetson_nvmm_native` as unavailable instead of silently falling back.

### Acceptance Criteria

Track 2 is PASS only when all of these are true:

- The native backend builds from the final branch on the Jetson, not from live hot patches.
- The worker can run the same 720p RTSP scene with fresh runtime reports and no secret leakage.
- The native backend produces the same frame dimensions and timing semantics as Track 1.
- CPU or FPS improves materially against Track 1. The acceptance threshold is at least 15% FPS improvement or at least 20% lower supervisor CPU at equivalent FPS and profile.
- If the backend only matches Track 1, keep it behind an experimental gate and mark the live result NOT RUN or FAIL for product defaulting.

## Deployment And Rollback

Track 1 can become the default Jetson RTSP path after live PASS. It keeps the rawvideo pipe and FFmpeg paths as compatibility fallbacks.

Track 2 must remain opt-in until it has a separate live PASS record. It should be controlled by a local media acceleration setting such as:

```json
{
  "runtime_family": "python",
  "media_acceleration": "auto",
  "jetson_capture_backend": "auto"
}
```

`auto` may choose `gstreamer_appsink` after Track 1 passes. It must not choose `jetson_nvmm_native` until Track 2 passes on the target release profile.

## Security And Evidence

- Logs must redact credentialed RTSP URLs and JWT query parameters before they are written to docs, screenshots, or reports.
- Process listings used in reports must be sanitized before sharing.
- Test fixtures may use fake RTSP URLs only.
- Live closure reports must distinguish PASS, FAIL, BLOCKED, and NOT RUN.
- Missing RTSP, missing model files, missing billing usage, missing deterministic evidence, missing fresh reports, or missing branch rebuild proof are not passes.

## Open Product Decision

The next implementation should default Track 1 to `auto` only after the first Jetson live smoke. Before that smoke, it should be selectable by environment/config so the old rawvideo path remains available for immediate rollback.
