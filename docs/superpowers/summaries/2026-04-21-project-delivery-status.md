# Project Delivery Status

## Snapshot

- Repository: `/Users/yann.moren/vision`
- Active branch: `codex/argus-ui-refresh`
- Date: 2026-04-21
- Focus area: live camera delivery stability across `WebRTC`, `LL-HLS`, and `MJPEG`

## Delivery Status

### Overall

The live-stream stabilization work for this debugging cycle is delivered on the branch and pushed to origin. The current state is suitable for local redeploy and validation on the iMac.

### Latest pushed commits in this workstream

- `aecb3f6` `fix: stabilize live stream failure handling`
- `3b31bee` `fix: refresh mjpeg rtsp tokens on reconnect`
- `7e80621` `fix: add self-healing live stream recovery`

## What Has Been Delivered

### Backend delivery

The backend work completed in this cycle includes:

- safer HLS proxy handling for nested playlists
- proper translation of offline WHEP negotiation failures into clean HTTP errors
- fresh MediaMTX RTSP auth generation for MJPEG reconnect attempts

These changes addressed:

- duplicated `jwt` query propagation to MediaMTX child playlists
- backend `500` responses when the annotated path was offline
- MJPEG reconnect loops that failed with `401 Unauthorized`

### Frontend delivery

The frontend work completed in this cycle includes:

- removal of forced session teardown when telemetry goes stale
- delayed promotion back to `WebRTC` after recovery instead of immediate restart
- debounce handling for transient `RTCPeerConnection` disconnect pulses
- regression tests for the flapping patterns observed in live logs

These changes reduce unnecessary bouncing between:

- `WebRTC`
- `LL-HLS`
- `MJPEG`

## Documents Added

- `/Users/yann.moren/vision/docs/superpowers/specs/2026-04-21-live-stream-self-healing-design.md`
- `/Users/yann.moren/vision/docs/superpowers/plans/2026-04-21-live-stream-self-healing-implementation-plan.md`
- `/Users/yann.moren/vision/docs/superpowers/summaries/2026-04-21-live-stream-debugging-handoff.md`
- `/Users/yann.moren/vision/docs/superpowers/summaries/2026-04-21-project-delivery-status.md`

## Verification Status

### Backend

Earlier in the cycle, targeted backend tests and checks were run successfully for:

- stream routing and HLS proxy behavior
- WebRTC negotiator behavior
- lint checks on modified backend files

### Frontend

The following were run successfully before the latest push:

```bash
corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx
corepack pnpm --dir frontend build
```

Additional targeted regressions were also run for:

- stale telemetry not restarting healthy `WebRTC`
- delayed recovery promotion
- transient disconnect debounce

## Known Remaining Issues

### 1. Real publisher drops still cause transport loss

If the annotated MediaMTX path actually disappears, the UI will still lose the live stream temporarily. That is expected behavior. The delivered work only removes avoidable churn layered on top of genuine upstream loss.

### 2. Test file emits React `act(...)` warnings

`frontend/src/components/live/VideoStream.test.tsx` still emits non-failing `act(...)` warnings in stderr. The suite passes, but the test harness remains a little noisy.

### 3. Observability stack remains degraded in local dev

The logs still show failures related to `otel-collector` hostname resolution. That did not block live-stream recovery work, but observability remains partially broken in the local stack.

## Current Confidence

### High confidence

- backend-side auth and error-handling regressions are fixed on the branch
- frontend no longer treats stale telemetry as a reason to tear down healthy video
- the browser recovery policy is calmer and better aligned with real transport health

### Medium confidence

- the user still needs to test the full live path on the iMac after pulling the newest frontend commit
- there may still be some flapping if the upstream publisher itself is unstable enough to repeatedly disappear and reappear in short windows

## Recommended Next Validation

After pulling the branch on the target machine:

```bash
cd /path/to/vision
git checkout codex/argus-ui-refresh
git pull --rebase origin codex/argus-ui-refresh
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend frontend
```

Then validate:

1. a healthy `WebRTC` session stays up during telemetry gaps
2. fallback remains stable while the publisher is actually down
3. promotion back to `WebRTC` is calmer and does not immediately flap
4. no MJPEG reconnect `401 Unauthorized` loop reappears

## Recommended Next Engineering Tasks

If more stabilization work is needed after live validation, the next likely steps are:

1. make transport health and publisher health more explicit in tile UI messaging
2. reduce or eliminate the remaining React `act(...)` test warnings
3. investigate whether dev-only `React.StrictMode` remounts are contributing noticeable local churn
4. repair local observability stack startup so debugging traces are available again

## Operator Notes

- Recreating the backend container is important when env values have changed. `restart` alone is not always enough.
- Recreating the frontend container is the easiest way to guarantee the latest browser-side recovery logic is active in Docker.
- Site and camera records are persisted in Postgres and should survive backend/frontend container recreation unless Postgres storage is wiped.

## Short Resume Summary

If someone needs to continue from here:

> The live-stream delivery stabilization work is pushed on `codex/argus-ui-refresh`. Backend fixes already landed for HLS nested playlist auth handling, WHEP error translation, and MJPEG RTSP token refresh. Frontend `VideoStream` now avoids tearing down healthy media on stale telemetry, delays promotion back to `WebRTC` after recovery, and debounces transient disconnects. The next step is to redeploy `backend` and `frontend` on the target machine and validate live recovery behavior against a real unstable publisher.
