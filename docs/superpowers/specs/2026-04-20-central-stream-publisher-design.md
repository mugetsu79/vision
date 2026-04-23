# Central Stream Publisher Design

## Goal

Make `central` and privacy-filtered live streams render real video in the UI by publishing processed worker frames into MediaMTX instead of only registering stream paths.

## Current Gap

- `InferenceEngine.run_once()` builds a stream frame and calls `stream_client.push_frame(...)` for non-`passthrough` modes.
- `MediaMTXClient.push_frame()` currently stores only debug metadata in `_pushed_frames`.
- MediaMTX read-side delivery is already wired through WHEP/HLS/MJPEG, so the browser can connect but receives no pixels for `annotated` / `preview`.

## Chosen Approach

Use a managed `ffmpeg` subprocess per active non-passthrough camera stream.

- The worker feeds processed BGR frames to `ffmpeg` on stdin as rawvideo.
- `ffmpeg` encodes H.264 and publishes to the existing MediaMTX publisher paths:
  - `cameras/<camera_id>/annotated`
  - `cameras/<camera_id>/preview`
- MediaMTX continues serving the browser via the existing WHEP/HLS/MJPEG read paths.

## Why This Approach

- It satisfies the real product behavior without changing the browser-side streaming contract.
- It matches the existing architecture choice of MediaMTX as the single stream delivery layer.
- It is much smaller and lower-risk than building a native WHIP/WebRTC publisher inside the worker.
- It aligns with the longer-term HQ deployment shape, where central nodes can use a system encoder pipeline.

## Scope

### In scope

- Add publisher lifecycle management to `MediaMTXClient`
- Feed non-passthrough frames into `ffmpeg`
- Use MediaMTX JWT publish tokens for authenticated publishing
- Restart publishers if the stream path changes or a subprocess dies
- Default x86 RTSP ingest to TCP to make host-side camera reads more reliable

### Out of scope

- Replacing MediaMTX or the browser read-side stack
- Building a native WHIP publisher in Python
- Reworking detection, tracking, or privacy logic
- Hardware-specific HQ encode optimization beyond a portable baseline

## Design Details

### Publisher lifecycle

- `register_stream()` still decides `annotated`, `preview`, or `passthrough`.
- `push_frame()` lazily creates a publisher process the first time a frame arrives for a given `camera_id + path`.
- If a camera re-registers onto a different path, the old publisher is closed and replaced.
- `MediaMTXClient.close()` shuts down all active publishers cleanly.

### Publish transport

- `ffmpeg` receives:
  - raw BGR frames from stdin
  - frame size from the frame shape
  - frame rate from timestamps or a default fallback
- Output target is MediaMTX RTSP publish URL with a JWT publish token attached.
- The first implementation targets correctness and portability, not advanced GPU encode tuning.

### Capture reliability

- x86 RTSP ingest should prefer TCP transport for OpenCV/FFmpeg capture.
- This reduces decode corruption and packet-loss sensitivity on unstable links like Wi-Fi test cameras.

## Testing

- Add failing tests first for:
  - publisher process creation on first `push_frame()`
  - publisher reuse on subsequent frames
  - publisher restart when the registration path changes
  - cleanup on client close
  - x86 RTSP capture forcing TCP transport
- Keep current engine tests green and extend them only where behavior changes are visible.

## Expected Outcome

After this change, a healthy `central` worker should:

- stay connected to the camera
- publish filtered/annotated frames into MediaMTX
- allow the existing Live dashboard stream readers to display actual video instead of a black tile
