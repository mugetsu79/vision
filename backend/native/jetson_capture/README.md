# Jetson Native NVMM Capture

This directory is reserved for the opt-in `jetson_nvmm_native` capture lane. Code
here must remain separate from the product default path unless the native lane is
explicitly selected.

The native extension should build only on Jetson/Linux aarch64 systems with the
required NVIDIA multimedia and GStreamer development headers installed. It is an
optional acceleration path, not a cross-platform dependency.

Decode and resize work should stay in NVIDIA media surfaces for as long as
possible. The lane should cross into Python memory only when Python asks for a
BGR NumPy frame. TensorRT inference must be able to run against the native
NVMM/CUDA-backed frame before `NativeJetsonFrame.as_bgr_numpy()` is called.

The native module contract is intentionally small and does not include
DeepStream or hardware encode:

- `open_rtsp(source_uri, width, height, fps_cap) -> handle`
- `read(handle) -> NativeJetsonFrame | None`
- `close(handle) -> None`

`NativeJetsonCapture` wraps that handle API and exposes worker-compatible
semantics:

- `read()`
- `release()`
- `last_stage_timings()`
- `media_pipeline_mode()`
- `media_capture_backend()`

When the extension is absent, the backend reports `jetson_nvmm_native` as
unavailable instead of changing the product default or failing import-time
startup.

The product default remains `gstreamer_appsink` until live Jetson smoke testing
proves the native lane improves FPS by at least 15% or lowers supervisor CPU by
at least 20% at equivalent FPS.

This lane is not DeepStream. DeepStream remains a later, separate optional
runtime family.
