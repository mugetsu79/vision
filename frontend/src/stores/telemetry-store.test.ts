import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { createTelemetryStore } from "@/stores/telemetry-store";

class MockWebSocket {
  public onopen: ((this: MockWebSocket, ev: Event) => void) | null = null;
  public onmessage: ((this: MockWebSocket, ev: MessageEvent) => void) | null = null;
  public onerror: ((this: MockWebSocket, ev: Event) => void) | null = null;
  public onclose: ((this: MockWebSocket, ev: CloseEvent) => void) | null = null;
  public readyState: number = 0;
  public closed = false;
  public static instances: MockWebSocket[] = [];

  constructor(public readonly url: string) {
    MockWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
    this.readyState = 3;
    this.onclose?.call(this, new CloseEvent("close"));
  }

  receive(payload: unknown) {
    this.onmessage?.call(this, new MessageEvent("message", { data: JSON.stringify(payload) }));
  }
}

describe("telemetry-store", () => {
  const originalWS = globalThis.WebSocket;
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = MockWebSocket;
  });
  afterEach(() => {
    vi.useRealTimers();
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = originalWS;
  });

  test("first subscribe opens a single WebSocket", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
    });
    store.subscribe("cam-1");
    store.subscribe("cam-2");
    expect(MockWebSocket.instances.length).toBe(1);
  });

  test("last unsubscribe keeps the WebSocket open during the idle grace period", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
    });
    store.subscribe("cam-1");
    store.unsubscribe("cam-1");
    vi.advanceTimersByTime(5_000);
    expect(MockWebSocket.instances[0].closed).toBe(false);
  });

  test("idle grace expires then the socket closes", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
    });
    store.subscribe("cam-1");
    store.unsubscribe("cam-1");
    vi.advanceTimersByTime(10_500);
    expect(MockWebSocket.instances[0].closed).toBe(true);
  });

  test("resubscribe within grace cancels the timer", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
    });
    store.subscribe("cam-1");
    store.unsubscribe("cam-1");
    vi.advanceTimersByTime(5_000);
    store.subscribe("cam-1");
    vi.advanceTimersByTime(20_000);
    expect(MockWebSocket.instances[0].closed).toBe(false);
  });

  test("ring buffer retains only allowed capacity", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
      ringBufferCapacity: 3,
    });
    store.subscribe("cam-1");
    const socket = MockWebSocket.instances[0];
    socket.onopen?.call(socket, new Event("open"));

    for (let i = 0; i < 5; i++) {
      socket.receive({
        camera_id: "cam-1",
        ts: new Date(2026, 3, 24, 14, i).toISOString(),
        counts: { person: i },
        tracks: [],
      });
    }

    const buffer = store.getBuffer("cam-1");
    expect(buffer.length).toBe(3);
    expect(buffer[0].counts.person).toBe(2);
    expect(buffer[2].counts.person).toBe(4);
  });
});
