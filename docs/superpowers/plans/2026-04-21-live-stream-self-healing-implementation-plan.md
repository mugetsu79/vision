# Live Stream Self-Healing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the browser live tile recover cleanly from unstable connectivity without restarting healthy `WebRTC` video just because telemetry is stale.

**Architecture:** Keep the existing transport ladder, but add explicit hysteresis in the frontend. Media failures still drive transport changes, while telemetry freshness becomes a recovery hint instead of a teardown trigger. `WebRTC` loss detection also gets a short debounce window so transient peer state changes do not immediately restart the tile.

**Tech Stack:** React, TypeScript, Vitest, Vite

---

### Task 1: Encode the Self-Healing Rules in `VideoStream`

**Files:**
- Modify: `frontend/src/components/live/VideoStream.tsx`
- Test: `frontend/src/components/live/VideoStream.test.tsx`

- [ ] **Step 1: Write the failing stale-heartbeat regression**

```tsx
test("does not restart an active WebRTC session just because telemetry heartbeat becomes stale", async () => {
  vi.useFakeTimers();
  const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ sdp_answer: "v=0" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  render(
    <VideoStream
      cameraId="56565656-5656-5656-5656-565656565656"
      cameraName="Stable WebRTC"
      defaultProfile="720p10"
      heartbeatTs={new Date(Date.now() - 10_000).toISOString()}
    />,
  );

  expect(fetchMock).toHaveBeenCalledTimes(1);

  await act(async () => {
    await vi.advanceTimersByTimeAsync(6_500);
  });

  expect(fetchMock).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Run the regression to verify it fails**

Run: `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "does not restart an active WebRTC session just because telemetry heartbeat becomes stale"`

Expected: FAIL because the current heartbeat timer triggers a second `/offer` fetch.

- [ ] **Step 3: Make telemetry staleness passive instead of destructive**

Update [frontend/src/components/live/VideoStream.tsx](/Users/yann.moren/vision/frontend/src/components/live/VideoStream.tsx) so the heartbeat-stale timer only updates internal freshness state and no longer calls `requestSessionRestart()`.

```ts
if (previousStatus === "stale" && nextStatus === "fresh" && transport !== "connecting") {
  requestSessionRestart("immediate");
}

if (nextStatus === "fresh") {
  staleTimer = window.setTimeout(() => {
    if (heartbeatStatusRef.current !== "fresh") {
      return;
    }

    heartbeatStatusRef.current = "stale";
  }, remainingFreshMs + 50);
}
```

- [ ] **Step 4: Run the regression to verify it passes**

Run: `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "does not restart an active WebRTC session just because telemetry heartbeat becomes stale"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/live/VideoStream.tsx frontend/src/components/live/VideoStream.test.tsx
git commit -m "fix: avoid tearing down healthy video on stale telemetry"
```

### Task 2: Add Recovery Hysteresis for Promotion Back to WebRTC

**Files:**
- Modify: `frontend/src/components/live/VideoStream.tsx`
- Test: `frontend/src/components/live/VideoStream.test.tsx`

- [ ] **Step 1: Write the failing delayed-promotion regression**

Replace the immediate-restart expectation in the heartbeat recovery test with a delayed-promotion expectation:

```tsx
test("restarts the live tile after telemetry recovery only after sustained freshness", async () => {
  vi.useFakeTimers();
  const fetchMock = vi
    .spyOn(global, "fetch")
    .mockResolvedValue(new Response("upstream failed", { status: 502 }));

  const { rerender } = render(
    <VideoStream
      cameraId="45454545-4545-4545-4545-454545454545"
      cameraName="Heartbeat Recovery"
      defaultProfile="720p10"
      heartbeatTs={new Date(Date.now() - 20_000).toISOString()}
    />,
  );

  const initialFetchCount = fetchMock.mock.calls.length;

  rerender(
    <VideoStream
      cameraId="45454545-4545-4545-4545-454545454545"
      cameraName="Heartbeat Recovery"
      defaultProfile="720p10"
      heartbeatTs={new Date().toISOString()}
    />,
  );

  expect(fetchMock.mock.calls.length).toBe(initialFetchCount);

  await act(async () => {
    await vi.advanceTimersByTimeAsync(3_500);
  });

  expect(fetchMock.mock.calls.length).toBeGreaterThan(initialFetchCount);
});
```

- [ ] **Step 2: Run the targeted heartbeat recovery test and confirm the old behavior is too eager**

Run: `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "restarts the live tile"`

Expected: FAIL or mismatch because current code restarts immediately.

- [ ] **Step 3: Add a promotion delay constant and use it on `stale -> fresh` recovery**

Update [frontend/src/components/live/VideoStream.tsx](/Users/yann.moren/vision/frontend/src/components/live/VideoStream.tsx) to delay promotion back to `WebRTC`:

```ts
const HEARTBEAT_RECOVERY_PROMOTION_DELAY_MS = 3_000;

if (previousStatus === "stale" && nextStatus === "fresh" && transport !== "connecting") {
  reconnectTimerRef.current = window.setTimeout(() => {
    reconnectTimerRef.current = null;
    reconnectAttemptRef.current = 0;
    restartSession();
  }, HEARTBEAT_RECOVERY_PROMOTION_DELAY_MS);
}
```

Make sure this path respects the existing timer cleanup rules so it does not race with normal reconnect backoff.

- [ ] **Step 4: Run the targeted heartbeat recovery test and verify the new hysteresis**

Run: `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "sustained freshness"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/live/VideoStream.tsx frontend/src/components/live/VideoStream.test.tsx
git commit -m "fix: delay webrtc promotion after telemetry recovery"
```

### Task 3: Debounce WebRTC Runtime Disconnects

**Files:**
- Modify: `frontend/src/components/live/VideoStream.tsx`
- Test: `frontend/src/components/live/VideoStream.test.tsx`

- [ ] **Step 1: Write the failing transient-disconnect regression**

Add a targeted test that proves a short `disconnected` pulse does not immediately trigger another `/offer` request.

```tsx
test("does not restart WebRTC on a transient disconnected pulse", async () => {
  // Render with successful offer negotiation.
  // Trigger a fake RTCPeerConnection state transition to "disconnected".
  // Advance less than the disconnect grace window and assert no new fetch.
  // Trigger recovery to "connected" and assert the pending restart is canceled.
});
```

- [ ] **Step 2: Run the targeted test and verify the current implementation is too sensitive**

Run: `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "transient disconnected pulse"`

Expected: FAIL because `onConnectionLost()` fires immediately today.

- [ ] **Step 3: Add a WebRTC disconnect grace window in `startWebRtc()`**

Refactor `startWebRtc()` in [frontend/src/components/live/VideoStream.tsx](/Users/yann.moren/vision/frontend/src/components/live/VideoStream.tsx) so transient `disconnected`/`failed` states are debounced:

```ts
const WEBRTC_DISCONNECT_GRACE_MS = 2_000;
let disconnectTimer: number | null = null;

const clearDisconnectTimer = () => {
  if (disconnectTimer !== null) {
    window.clearTimeout(disconnectTimer);
    disconnectTimer = null;
  }
};

const scheduleConnectionLoss = () => {
  if (disconnectTimer !== null) {
    return;
  }
  disconnectTimer = window.setTimeout(() => {
    disconnectTimer = null;
    onConnectionLost();
  }, WEBRTC_DISCONNECT_GRACE_MS);
};
```

Use `connected` / `completed` states to cancel the timer and make sure cleanup closes the peer and clears the timer.

- [ ] **Step 4: Run the transient-disconnect test and the whole `VideoStream` suite**

Run:
- `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx -t "transient disconnected pulse"`
- `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/live/VideoStream.tsx frontend/src/components/live/VideoStream.test.tsx
git commit -m "fix: debounce transient webrtc disconnects"
```

### Task 4: Final Verification

**Files:**
- Verify: `frontend/src/components/live/VideoStream.tsx`
- Verify: `frontend/src/components/live/VideoStream.test.tsx`
- Verify: `docs/superpowers/specs/2026-04-21-live-stream-self-healing-design.md`

- [ ] **Step 1: Run the focused frontend tests**

Run: `corepack pnpm --dir frontend test src/components/live/VideoStream.test.tsx`

Expected: PASS

- [ ] **Step 2: Build the frontend bundle**

Run: `corepack pnpm --dir frontend build`

Expected: production build completes successfully

- [ ] **Step 3: Check git status**

Run: `git status --short`

Expected: only intended stream self-healing files are staged/modified, plus any pre-existing unrelated user changes left untouched.

- [ ] **Step 4: Commit the finished self-healing work**

```bash
git add docs/superpowers/specs/2026-04-21-live-stream-self-healing-design.md docs/superpowers/plans/2026-04-21-live-stream-self-healing-implementation-plan.md frontend/src/components/live/VideoStream.tsx frontend/src/components/live/VideoStream.test.tsx
git commit -m "fix: stabilize live stream self-healing"
```
