# Claude Code Handoff

Last updated: 2026-04-23, Europe/Zurich.

## Repo State

- Workspace: `/Users/yann.moren/vision`.
- Current branch: `codex/argus-ui-refresh`.
- Branch is aligned with `origin/codex/argus-ui-refresh` at `ee6f74e`.
- Latest commit: `ee6f74e debug: instrument host worker frame loop`.
- Dirty local files not related to the stream/debug work:
  - `frontend/src/components/layout/AppShell.test.tsx`
  - `.superpowers/brainstorm/10607-1776629414/`
  - `.superpowers/brainstorm/53189-1776681215/`
- Do not overwrite or revert those unrelated local changes unless explicitly asked.

## Deployment Snapshot

Local dev compose file: `infra/docker-compose.dev.yml`.

Observed `docker compose -f infra/docker-compose.dev.yml ps --all` state on 2026-04-23:

- Running: `postgres`, `redis`, `nats`, `minio`, `keycloak`, `mediamtx`, `frontend`, `backend`, `grafana`, `loki`, `alertmanager`.
- Stopped/exited: `otel-collector` exited 137, `prometheus` exited 137, `tempo` exited 1.
- Frontend answered `HTTP/1.1 200 OK` on `http://127.0.0.1:3000`.
- Backend container was listed as Up on port `8000`, but `curl --max-time 2 http://127.0.0.1:8000/healthz` failed with connection refused while Uvicorn was stuck in a WatchFiles reload shutdown. Backend logs showed:
  - `WatchFiles detected changes in 'src/argus/streaming/webrtc.py'. Reloading...`
  - `Shutting down`
  - `Waiting for background tasks to complete. (CTRL+C to force quit)`
- Backend logs also show OTLP exporter errors because `otel-collector` is not resolvable/running.

The user-side test machine is separate from this workspace in logs: `morya@printer`, repo path `/Users/morya/vision`. The live camera under test there is:

- Camera ID: `4f6380b8-75d6-4e92-90b8-d870f4ca06c0`
- Camera label: `CAMERA 1`
- RTSP source observed in logs: `rtsp://***@192.168.1.195:8554/ch2`
- Current known working browser mode: `native` with both privacy blur options disabled.

Do not put raw RTSP credentials or bearer tokens into commits.

## What Was Done

Recent stream/model/debug commits on `codex/argus-ui-refresh`:

- `706a03d fix: restore tracker compatibility with detected objects`
  - Fixed missing BotSORT config expected by current Ultralytics tracker.
  - This showed up only once real detections were flowing.
- `4dce0dc fix: honor passthrough browser delivery on central workers`
  - Worker/runtime now respects `stream.kind=passthrough` for central workers.
- `45188d4 fix: honor native browser delivery in stream access`
  - Backend stream-serving paths now honor native browser delivery instead of always resolving central cameras to `/annotated`.
- `c763230 fix: prefer coreml on intel mac workers`
  - Intel macOS profile now prefers `CoreMLExecutionProvider` before CPU.
- `e1e47b5 debug: log ffmpeg capture fallback reasons`
  - Logs why Intel Mac ffmpeg rawvideo capture falls back.
- `f20c0de fix: time out intel mac rtsp ffmpeg ingest`
  - Adds ffmpeg RTSP socket timeout for the Intel Mac rawvideo ingest path.
  - Adds warning when `native`/passthrough is requested but privacy filtering forces a processed stream.
- `4ae967d fix: clarify live tile telemetry status`
  - Dashboard no longer labels stale telemetry as `offline`.
  - It now shows `telemetry live`, `telemetry stale`, or `awaiting telemetry`.
- `ee6f74e debug: instrument host worker frame loop`
  - Adds `ARGUS_WORKER_DIAGNOSTICS_ENABLED`.
  - Logs frame-loop progress around capture, detect, publish_stream, and completion.

Verification already run during this debugging session:

- `python3 -m uv run pytest tests/core/test_config.py tests/inference/test_engine.py tests/streaming/test_mediamtx.py tests/vision/test_camera.py tests/vision/test_runtime.py -q`
- `python3 -m uv run ruff check src/argus/core/config.py src/argus/inference/engine.py tests/core/test_config.py tests/inference/test_engine.py`
- `python3 -m uv run pytest tests/vision/test_tracker.py tests/inference/test_engine.py -q`
- `python3 -m uv run pytest tests/inference/test_engine.py tests/streaming/test_mediamtx.py tests/inference/test_e2e_worker.py -q`
- `python3 -m uv run pytest tests/inference/test_engine.py tests/streaming/test_mediamtx.py tests/inference/test_e2e_worker.py tests/streaming/test_webrtc.py tests/services/test_stream_service.py -q`
- `python3 -m uv run pytest tests/vision/test_runtime.py tests/vision/test_detector.py tests/inference/test_engine.py -q`
- `python3 -m uv run pytest tests/vision/test_camera.py tests/vision/test_runtime.py tests/vision/test_detector.py tests/inference/test_engine.py -q`
- `python3 -m uv run pytest tests/vision/test_camera.py tests/streaming/test_mediamtx.py tests/streaming/test_webrtc.py tests/services/test_stream_service.py tests/inference/test_engine.py -q`
- `corepack pnpm --dir frontend exec vitest run src/pages/Dashboard.test.tsx`
- `corepack pnpm --dir frontend exec vitest run src/components/live/VideoStream.test.tsx src/pages/Dashboard.test.tsx`

The `VideoStream` frontend tests pass but emit pre-existing React `act(...)` warnings.

## Current Working Theory

The streaming problem was not one single bug.

Confirmed pieces:

- `native` plus privacy blur disabled registers `cameras/<camera-id>/passthrough` through MediaMTX and works.
- If blur is enabled, even `native` cannot be true passthrough because privacy filtering requires processed frames.
- If browser delivery is not `native`, `stream.kind` becomes `transcode`; on central processing this goes to the host-published `annotated` path.
- The `annotated` path depends on the host worker reading camera frames, optionally filtering/annotating them, and publishing frames back into MediaMTX.
- The Intel iMac host-published path is the unstable part.
- WebRTC/LL-HLS behavior is downstream. When the processed stream disappears, MediaMTX correctly returns `404` / no stream available.

Relevant code:

- `backend/src/argus/streaming/mediamtx.py`
  - `_build_registration(...)` selects true passthrough only when `stream_kind == "passthrough"` and privacy filtering is off.
  - Central processing with non-passthrough chooses `StreamMode.ANNOTATED_WHIP` and path `cameras/<id>/annotated`.
- `backend/src/argus/inference/engine.py`
  - In passthrough mode, `publish_stream` is skipped.
  - Telemetry is still published per frame.
  - Latest diagnostics can log the precise stage where the worker stalls.
- `frontend/src/pages/Dashboard.tsx`
  - Status badge now describes telemetry freshness, not stream liveness.

Important observation from user testing on 2026-04-23:

- User did not pull the latest timeout/diagnostic commits initially.
- They simply disabled blur/privacy while staying in `native`.
- It worked and the host worker logged a successful MediaMTX path add for `/passthrough`.
- Screenshot showed live video with `WEBRTC LIVE`, stream mode `passthrough`, and stale telemetry. That is expected because passthrough video can remain live even if inference telemetry stops updating.

## How To Reproduce / Continue Debugging On The iMac

Pull latest branch on the iMac:

```bash
cd "$HOME/vision"
git checkout codex/argus-ui-refresh
git pull --rebase origin codex/argus-ui-refresh
```

Recreate backend after pulling:

```bash
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend
```

The host worker is not a Docker service in this debug flow. Its logs are the
stdout/stderr from the local `python -m argus.inference.engine` process. Capture
them unbuffered with `tee` so the last emitted frame breadcrumb survives if the
worker stalls:

```bash
TOKEN="$(
  curl -s \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
export TOKEN

cd "$HOME/vision/backend"
PYTHONUNBUFFERED=1 \
ARGUS_ENABLE_WORKER_METRICS_SERVER="true" \
ARGUS_WORKER_METRICS_PORT="9108" \
ARGUS_WORKER_DIAGNOSTICS_ENABLED="true" \
ARGUS_API_BASE_URL="http://127.0.0.1:8000" \
ARGUS_API_BEARER_TOKEN="$TOKEN" \
ARGUS_DB_URL="postgresql+asyncpg://argus:argus@127.0.0.1:5432/argus" \
ARGUS_NATS_URL="nats://127.0.0.1:4222" \
ARGUS_MINIO_ENDPOINT="127.0.0.1:9000" \
ARGUS_MINIO_ACCESS_KEY="argus" \
ARGUS_MINIO_SECRET_KEY="argus-dev-secret" \
ARGUS_MINIO_SECURE="false" \
python3 -m uv run python -m argus.inference.engine --camera-id "4f6380b8-75d6-4e92-90b8-d870f4ca06c0" 2>&1 | tee /tmp/argus-worker-4f6380b8.log
```

Tail MediaMTX separately while the host worker is running:

```bash
docker compose -f "$HOME/vision/infra/docker-compose.dev.yml" logs -f mediamtx
```

Metrics check:

```bash
curl -s http://127.0.0.1:9108/metrics | grep -E 'argus_inference_frames_processed_total|argus_inference_stage_duration_seconds'
```

For processed/non-native failure investigation, the new diagnostics should show the last successful frame stage:

- `Worker frame capture starting`
- `Worker frame capture completed`
- `Worker frame detect starting`
- `Worker frame detect completed`
- `Worker frame publish_stream starting`
- `Worker frame publish_stream completed`
- `Worker frame completed`

If the metrics counter stops at frame 32, the next diagnostic clue is frame
attempt 33. The last emitted breadcrumb tells where frame 33 stopped.

If logs stop after `capture starting`, the RTSP ingest is blocked.
If logs stop around `publish_stream starting`, the MediaMTX publisher path is blocked.
If `publish_stream completed` and `Worker frame completed` continue after
MediaMTX drops the path, the remaining issue is downstream of the worker.

## Remaining Work

1. ✅ Confirmed 2026-04-23: iMac HEAD is current (≥ `ee6f74e`) with the
   timeout/diagnostic commits applied.

2. ✅ Confirmed 2026-04-23: true native passthrough works for camera
   `4f6380b8-75d6-4e92-90b8-d870f4ca06c0` with `blur_faces=false`,
   `blur_plates=false`. Registration path is `cameras/<id>/passthrough`;
   telemetry reports `stream mode = passthrough`; browser shows `WEBRTC LIVE`.

3. Re-test processed path with diagnostics enabled.
   - Turn on a non-native profile or re-enable privacy blur.
   - Expected registration: `cameras/<id>/annotated`.
   - Capture logs from the latest `ARGUS_WORKER_DIAGNOSTICS_ENABLED=true` run.
   - Determine whether the stall is in RTSP ingest, inference, privacy/annotate, or MediaMTX publish.

4. Decide product behavior for privacy + native.
   - Current backend behavior is correct for privacy: privacy filtering forces processed stream.
   - UI should probably warn users that enabling blur disables true native/passthrough and may be heavier on the iMac.

5. Fix or redesign processed streaming on Intel macOS.
   - Current processed path is fragile because Python host worker captures frames and republishes them.
   - Potential directions:
     - Keep timeout/reconnect and tune ffmpeg ingest.
     - Lower processed target FPS/profile on Intel Mac.
     - Avoid host-side republishing for browser transcode if MediaMTX can handle it directly.
     - Consider separate process supervision for ffmpeg ingest/publisher.

6. Stabilize local compose observability.
   - `otel-collector`, `prometheus`, and `tempo` are currently exited in this workspace.
   - Backend trace export errors are noisy and can make debugging harder.
   - Backend may need a clean restart if stuck in WatchFiles shutdown after file edits.

7. Do not forget unrelated local changes.
   - `frontend/src/components/layout/AppShell.test.tsx` is modified by the user and should be left alone unless asked.
   - `.superpowers/brainstorm/...` directories are untracked.

## Quick Mental Model

Use this framing when debugging:

- Video working does not necessarily mean inference telemetry is live.
- `WEBRTC LIVE` means browser transport is connected.
- `passthrough` means MediaMTX can read directly from the camera source.
- `telemetry stale` means the worker/websocket has not delivered a fresh telemetry frame within 15 seconds.
- `native + no blur` avoids the unstable processed publisher path.
- `non-native` or `blur enabled` re-enters the processed `annotated` path.
