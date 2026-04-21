# Live Stream Self-Healing Design

## Goal

Make browser delivery recover gracefully from unstable connectivity without flapping between `WebRTC`, `LL-HLS`, and `MJPEG`, and without tearing down healthy video just because telemetry updates are delayed.

## Problem Summary

The current live tile mixes three different health signals:

- media transport health (`WebRTC` / `HLS` / `MJPEG`)
- annotated publisher availability in MediaMTX
- telemetry freshness (`frame.ts` updates)

That coupling causes avoidable churn:

- a healthy `WebRTC` session can be restarted when telemetry goes stale
- short upstream outages can trigger immediate transport demotion and promotion
- dev-mode remounts and transient peer state changes can create very short-lived `WebRTC` sessions
- fallback transport retries were previously masking whether the root failure was auth, publisher loss, or browser-side teardown

## Design Principles

1. A healthy media session should stay alive until the media transport itself fails.
2. Telemetry staleness should affect UI messaging, not force media teardown.
3. Transport switching should use hysteresis:
   - retry the current transport first
   - demote only after sustained failure
   - promote only after sustained recovery
4. Recovery should self-heal from the best available transport, but should not flap.
5. Browser behavior should remain predictable in local dev, even under `React.StrictMode`.

## In Scope

- frontend browser-delivery recovery behavior in [frontend/src/components/live/VideoStream.tsx](/Users/yann.moren/vision/frontend/src/components/live/VideoStream.tsx)
- frontend regressions in [frontend/src/components/live/VideoStream.test.tsx](/Users/yann.moren/vision/frontend/src/components/live/VideoStream.test.tsx)
- preserving the already-landed backend MJPEG token refresh behavior

## Out of Scope

- changing MediaMTX server configuration
- redesigning backend telemetry transport
- replacing the existing browser delivery ladder

## Health Model

The tile should reason about three independent conditions:

### 1. Media Health

Is the current transport actively usable?

- `WebRTC`: peer connection remains established and playable
- `HLS`: manifest and media continue to load without fatal runtime errors
- `MJPEG`: image stream continues delivering frames

### 2. Publisher Health

Is the annotated MediaMTX path available right now?

- inferred from `WHEP 404` and HLS/RTSP unavailability
- used to explain why upgrades cannot happen yet

### 3. Telemetry Health

Is telemetry fresh enough to trust the overlay and activity badges?

- derived from `TelemetryFrame.ts`
- used only for messaging and recovery promotion decisions
- must not tear down active media

## Recovery Strategy

### Keep Active Media Alive

If `WebRTC` is currently connected, stale telemetry must not trigger `restartSession()`.

### Debounce Transient WebRTC Loss

`RTCPeerConnection` state changes such as `disconnected` can be transient. The tile should wait through a short grace window before declaring the session lost.

### Delayed Promotion Back To WebRTC

When the stream is currently on `HLS` or `MJPEG`, a `stale -> fresh` telemetry transition should not cause an immediate full restart. Instead, it should schedule a promotion attempt after a short sustained-freshness delay.

That provides hysteresis:

- if the publisher comes back briefly and disappears again, the tile stays on fallback
- if the publisher stays healthy long enough, the tile upgrades back to `WebRTC`

### Continue Using Existing Ladder

The ladder remains:

`WebRTC -> LL-HLS -> MJPEG`

but the transition policy changes from "restart aggressively" to "restart intentionally".

## Implementation Decisions

### Frontend

In [frontend/src/components/live/VideoStream.tsx](/Users/yann.moren/vision/frontend/src/components/live/VideoStream.tsx):

- stop calling `requestSessionRestart()` when heartbeat becomes stale
- keep the existing `stale -> fresh` recovery hook, but add a promotion delay instead of immediate restart
- debounce `WebRTC` connection-loss callbacks before restarting the session
- preserve the existing fallback path and backoff timers

### Tests

In [frontend/src/components/live/VideoStream.test.tsx](/Users/yann.moren/vision/frontend/src/components/live/VideoStream.test.tsx):

- prove stale telemetry no longer forces a healthy `WebRTC` renegotiation
- update heartbeat-recovery coverage to expect delayed promotion instead of immediate restart
- keep existing `HLS`/`MJPEG` fallback tests green

## Success Criteria

- a healthy `WebRTC` session does not churn just because telemetry pauses
- fallback transport remains stable while telemetry is stale
- the tile promotes back to `WebRTC` only after recovery is sustained
- the frontend test suite captures the no-flap behavior

## Verification

- `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx`
- `corepack pnpm --dir frontend build`

## Assumption

The user explicitly requested “do it” after approving the recommended direction, so that is treated as approval to proceed from design to plan to implementation without an extra written-spec review pause.
