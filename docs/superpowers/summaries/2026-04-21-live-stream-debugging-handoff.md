# Live Stream Debugging Handoff

## Context

- Repository: `/Users/yann.moren/vision`
- Branch: `codex/argus-ui-refresh`
- Date: 2026-04-21
- Goal: stabilize live camera playback across `WebRTC`, `LL-HLS`, and `MJPEG` under unstable publisher and network conditions

## What Broke

The investigation started from a live camera tile that got stuck on `Loading live cameras...` and later showed unstable playback that bounced between:

- `WebRTC`
- `LL-HLS`
- `WebRTC` again
- back to `LL-HLS`

The logs initially suggested MediaMTX instability, but the real problem turned out to be a stack of separate issues across backend behavior, stale container configuration, and frontend restart policy.

## What We Found

### 1. `84c7b7b` was not the root regression

Commit `84c7b7b` only adjusted the MJPEG bridge reconnect behavior in:

- `/Users/yann.moren/vision/backend/src/argus/streaming/webrtc.py`
- `/Users/yann.moren/vision/backend/tests/streaming/test_webrtc.py`

It did not introduce the HLS proxy or WHEP negotiation breakage.

### 2. Nested HLS playlist proxying was forwarding the wrong query params

The backend HLS proxy path was forwarding frontend query params such as `jwt` and `session_token` upstream to MediaMTX child playlists. That produced duplicated `jwt` query parameters and `401 Unauthorized` responses on nested HLS asset requests.

This was fixed in backend code by filtering what gets forwarded upstream.

### 3. Offline WHEP negotiation returned a backend `500`

When MediaMTX returned `404 Not Found` for an unavailable WHEP path, the backend let that bubble into a server-side failure instead of translating it into a clean client-facing error.

This was fixed so offline stream negotiation now returns a normal HTTP error instead of crashing the route.

### 4. One backend container was running with stale MediaMTX env

Part of the breakage was operational, not code:

- the compose file already had the correct `mediamtx` hostnames
- the running backend container still had stale `localhost`-style env
- `docker compose restart` did not refresh those env vars
- recreating the backend container fixed that mismatch

### 5. MJPEG reconnects reused expired RTSP auth

After the first backend fixes, the camera could recover briefly, but the MJPEG bridge would later reconnect with an expired MediaMTX RTSP token and enter a `401 Unauthorized` loop.

This was fixed by minting a fresh signed RTSP URL for each MJPEG reconnect attempt.

### 6. The remaining playback flapping was frontend-driven

Once the backend and MJPEG auth issues were fixed, the logs showed:

- `POST /api/v1/streams/.../offer` returning `200 OK`
- MediaMTX reporting `peer connection established`
- then MediaMTX reporting `peer connection closed`
- followed by fallback attempts and later re-promotion

The key frontend problem was that the live tile treated telemetry freshness as if it were media health. In practice:

- a healthy `WebRTC` session could be restarted just because heartbeat telemetry went stale
- `stale -> fresh` transitions could trigger eager full-session restarts
- transient `RTCPeerConnection` `disconnected` pulses could trigger restart too quickly

## Backend Fixes Already Landed

These backend commits are already on the branch:

- `aecb3f6` `fix: stabilize live stream failure handling`
- `3b31bee` `fix: refresh mjpeg rtsp tokens on reconnect`

Those fixes cover:

- HLS nested-playlist query handling
- WHEP error translation
- MJPEG RTSP token refresh on reconnect

## Frontend Self-Healing Design

To stabilize playback, the frontend recovery model was changed conceptually to separate three signals:

### Media health

Whether the current transport is actually playing usable video.

### Publisher health

Whether the annotated MediaMTX path currently exists.

### Telemetry health

Whether overlay and activity metadata are fresh.

Telemetry staleness should change messaging and promotion decisions, but should not tear down healthy media.

## Frontend Self-Healing Implementation

Files changed:

- `/Users/yann.moren/vision/frontend/src/components/live/VideoStream.tsx`
- `/Users/yann.moren/vision/frontend/src/components/live/VideoStream.test.tsx`

New docs added:

- `/Users/yann.moren/vision/docs/superpowers/specs/2026-04-21-live-stream-self-healing-design.md`
- `/Users/yann.moren/vision/docs/superpowers/plans/2026-04-21-live-stream-self-healing-implementation-plan.md`

### Behavior changes

1. Stale telemetry no longer forces a restart of a healthy live session.
2. Promotion back toward `WebRTC` after `stale -> fresh` recovery is delayed slightly, so recovery must be sustained.
3. Short `RTCPeerConnection` disconnect pulses are debounced before the tile decides the session is really lost.
4. The existing fallback ladder stays the same:

`WebRTC -> LL-HLS -> MJPEG`

but the switching policy is calmer and less eager.

### New frontend regressions added

The test suite now covers:

- no restart of healthy `WebRTC` just because telemetry becomes stale
- delayed promotion after heartbeat recovery instead of immediate restart
- no restart on a transient WebRTC disconnect pulse

## Verification Run

The following commands were run successfully from `/Users/yann.moren/vision`:

```bash
corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "does not restart an active WebRTC session just because telemetry heartbeat becomes stale"
corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "short delay when the worker heartbeat recovers"
corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "transient disconnected pulse"
corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx
corepack pnpm --dir frontend build
```

Notes:

- The `VideoStream` test file still emits React `act(...)` warnings in stderr.
- Those warnings are pre-existing test-harness noise and did not fail the suite.

## How To Redeploy For Local Testing

### Backend

If the backend container has stale env or old code, recreate it:

```bash
docker compose -f /Users/yann.moren/vision/infra/docker-compose.dev.yml up -d --force-recreate backend
```

### Frontend

To pick up the new self-healing frontend logic:

```bash
docker compose -f /Users/yann.moren/vision/infra/docker-compose.dev.yml up -d --force-recreate frontend
```

## What To Expect In Logs Now

### Good signs

- `POST /api/v1/streams/.../offer HTTP/1.1" 200 OK`
- MediaMTX `peer connection established`
- fewer unnecessary `WebRTC -> fallback -> WebRTC` transitions during telemetry hiccups

### Still expected when the publisher really drops

- MediaMTX path unavailable
- WHEP `404 Not Found`
- fallback transport use while the annotated path is offline

That is not a frontend bug by itself. The bug was the avoidable restart churn layered on top of real publisher loss.

## Current State

At the end of this chat:

- backend-side HLS/WHEP/MJPEG reconnect issues were fixed
- frontend self-healing behavior was implemented and verified locally
- the work was not yet committed when this handoff file was first drafted

If you open a new chat, the useful short summary is:

> We stabilized live stream recovery on branch `codex/argus-ui-refresh`. Backend fixes already landed for HLS nested playlist auth, WHEP error translation, and MJPEG RTSP token refresh. Frontend `VideoStream.tsx` was then changed so stale telemetry no longer tears down healthy media, `stale -> fresh` promotion back to WebRTC is delayed, and transient WebRTC disconnects are debounced. The relevant files are `frontend/src/components/live/VideoStream.tsx`, `frontend/src/components/live/VideoStream.test.tsx`, and the design/plan docs under `docs/superpowers/`.
