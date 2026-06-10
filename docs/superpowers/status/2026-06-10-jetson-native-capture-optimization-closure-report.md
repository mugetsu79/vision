# Jetson Native Capture Optimization Closure Report

Date: 2026-06-10

Branch: `codex/sceneops-pack-registry`

Implementation commit deployed for smoke: `f862b8910d8008c6825d2ed7eb471e162655b94c`

Stack type: installed macOS master product stack plus real Jetson Orin edge stack. The master backend image and Jetson edge image were rebuilt locally from committed branch artifacts. Registry publishing was not attempted.

RTSP/source handling: live test streams were used only as local inputs. Credentials are intentionally omitted; evidence records source shape only.

## Summary

Task 0 native no-DeepStream Jetson closure is a **PASS** for the appsink Track 1 default path. The live EDGE worker now reports a fresh per-camera runtime heartbeat with `selected_provider=tensorrt_engine`, TensorRT runtime artifact `4e849c27-f03e-4ec6-b575-9ba525a8763f`, `media_pipeline_mode=jetson_gstreamer_native`, `media_capture_backend=gstreamer_appsink`, `encoder_mode=software`, and scene contract hash prefix `807268f487c1`.

The EDGE source capability is H.264 `1280x720` at `20` FPS, and the processed MediaMTX path `preview-720p20` is ready with H.264. The measured worker rate improved from the prior 13-15 FPS baseline to `17.57` FPS over a 20.03 second live sample. Container CPU dropped from the prior roughly 217-316% range to about `133-137%` in post-change samples. This satisfies the Track 1 acceptance threshold through both FPS and CPU improvement.

This is not a DeepStream implementation. DeepStream remains the later optional runtime-family track. Central Mac M4 acceleration remains a future native macOS/CoreML lane; the central Docker worker is not claimed as GPU accelerated.

## Pass/Fail Matrix

| Area | Status | Evidence |
|---|---:|---|
| Local implementation commit | PASS | `f862b8910d8008c6825d2ed7eb471e162655b94c` on `codex/sceneops-pack-registry`; branch is ahead of remote and not pushed. |
| Jetson deploy from committed branch | PASS | Jetson `/opt/vezor/current` points to `/home/ai-user/vision-f862b891`; `vezor/edge-worker:portable-demo` image `sha256:a285d3bb...` created `2026-06-10T16:41:32Z`; `vezor-supervisor` healthy. |
| Master backend schema/reporting deploy | PASS | Master backend image `sha256:a226ef9f...` created `2026-06-10T16:49:17Z`; backend and central supervisor healthy; `worker_runtime_reports.media_capture_backend` exists. |
| Jetson hardware decode/resize eligibility | PASS | Live container probe reports native appsink capabilities available; redacted native pipeline includes `nvv4l2decoder disable-dpb=true` and `nvvidconv` before BGR conversion at `1280x720`. |
| Jetson capture backend process shape | PASS | `docker top vezor-supervisor -eo pid,comm` shows Python worker plus `ffmpeg`; no `gst-launch-1.0` rawvideo helper is running. |
| Jetson runtime report | PASS | Fresh EDGE heartbeat age `3.95s`; `runtime_state=running`, `selected_provider=tensorrt_engine`, artifact `4e849c27-f03e-4ec6-b575-9ba525a8763f`, `media_pipeline_mode=jetson_gstreamer_native`, `media_capture_backend=gstreamer_appsink`, `encoder_mode=software`, scene hash prefix `807268f487c1`. |
| Central runtime report scoping | PASS | Fresh CENTRAL heartbeat age `4.78s`; `runtime_state=running`, `selected_provider=onnxruntime`, `media_pipeline_mode=ffmpeg_software`, `media_capture_backend=opencv_ffmpeg`, no Jetson TensorRT artifact shown as its effective runtime. |
| 720p ingest confirmation | PASS | EDGE camera source capability is H.264 `1280x720` at `20` FPS; browser delivery default is `720p20`; 1080p/900p options are unavailable because the source is smaller. |
| Processed stream readiness | PASS | EDGE MediaMTX `cameras/.../preview-720p20` is ready with H.264 and one reader; passthrough path is not ready because privacy processing disables native clean passthrough for this scene. |
| Live FPS | PASS | Two metrics scrapes over `20.03s`: `352` frames processed, `17.57` FPS. |
| Live stage timings | PASS | Average over same sample: frame `49.95ms`, capture `18.22ms`, capture decode/read `2.22ms`, capture wait `1.39ms`, preprocess `0.49ms`, detect `23.38ms`, track `0.67ms`, publish stream `5.11ms`. |
| CPU/memory | PASS | Post-change Jetson samples: `vezor-supervisor` CPU `137.43%` then `133.44%`, memory `1.437GiB/7.429GiB`; `vezor-edge-mediamtx` CPU `2.46%` then `2.25%`. Prior handoff baseline was roughly 217-316% supervisor CPU. |
| GR3D / system telemetry | PASS | `tegrastats` post-change samples show RAM about `2392-2411/7607MB`, GR3D ranging `0-76%`, temperatures about `50C`. |
| Encoder mode honesty | PASS | Orin Nano processed publishing reports `encoder_mode=software`; no unsupported Jetson hardware encoder claim is made. |
| Fallback taxonomy | PASS | Code/tests cover Jetson native GStreamer appsink, rawvideo pipe compatibility fallback, software GStreamer, FFmpeg rawvideo, and OpenCV/FFmpeg software reporting. |
| Core Link installation payload fixture | PASS | `/var/lib/vezor/link-throughput/vezor-speed-test-64MiB.bin` exists with size `67108864`. |
| DeepStream | NOT RUN | Not part of this implementation. Preserved as later optional runtime-family track. |
| Registry publishing | BLOCKED | Registry target, repository names, credentials/auth method, and tag policy are not provided. No publish was attempted. |
| Native macOS/CoreML central acceleration | NOT RUN | Central Docker worker remains CPU/FFmpeg software. Native macOS/CoreML is a future lane only. |

## Remaining Notes

- The worker is now processing 720p ingest. Calibration still has historical source-point/still data that may need a separate UX/data refresh path when a camera source profile changes.
- The current bottleneck is no longer rawvideo pipe transfer. The 20 FPS cap is still missed because the sampled frame average is about `49.95ms`, with detection around `23.38ms`, capture around `18.22ms`, and stream publishing around `5.11ms`.
- Further non-DeepStream improvement candidates are dynamic source reinitialization on stream-profile changes, CUDA/NVMM frame handling to avoid BGR host copies, and hardware encode only on Jetson SKUs where the encoder is available and verified.

## Verification Commands

Representative commands run, with secrets omitted:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_gstreamer_appsink.py backend/tests/vision/test_camera.py -q
backend/.venv/bin/ruff check backend/src/argus/vision/gstreamer_appsink.py backend/tests/vision/test_gstreamer_appsink.py
docker build -f backend/Dockerfile -t vezor/backend:portable-demo .
VEZOR_MASTER_ENV_FILE=/etc/vezor/master.env VEZOR_MASTER_COMPOSE=/Users/yann.moren/vision/infra/install/compose/compose.master.yml /Users/yann.moren/vision/bin/vezor-master up --config /etc/vezor/master.json --no-deps --force-recreate backend
VEZOR_MASTER_ENV_FILE=/etc/vezor/master.env VEZOR_MASTER_COMPOSE=/Users/yann.moren/vision/infra/install/compose/compose.master.yml /Users/yann.moren/vision/bin/vezor-master up --config /etc/vezor/master.json --no-deps --force-recreate vezor-supervisor
ssh ai-user@192.168.1.203 'docker top vezor-supervisor -eo pid,comm'
ssh ai-user@192.168.1.203 'curl -fsS http://127.0.0.1:9108/metrics'
ssh ai-user@192.168.1.203 'timeout 12s tegrastats --interval 1000'
```
