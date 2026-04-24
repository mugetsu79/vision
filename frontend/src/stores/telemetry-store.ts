import { create } from "zustand";

import { parseTelemetryPayload, type TelemetryFrame } from "@/lib/live";
import { buildWebSocketUrl } from "@/lib/ws";

export type TelemetryConnectionState = "connecting" | "open" | "closed" | "error";

export type CreateTelemetryStoreOptions = {
  accessToken: string | null;
  tenantId: string | null;
  idleGraceMs?: number;
  ringBufferCapacity?: number;
};

export interface TelemetryStore {
  subscribe: (cameraId: string) => void;
  unsubscribe: (cameraId: string) => void;
  getLatest: (cameraId: string) => TelemetryFrame | null;
  getBuffer: (cameraId: string) => TelemetryFrame[];
  connectionState: () => TelemetryConnectionState;
  onChange: (listener: () => void) => () => void;
}

const DEFAULT_IDLE_GRACE_MS = 10_000;
const DEFAULT_RING_BUFFER_CAPACITY = 6_000;

export function createTelemetryStore(options: CreateTelemetryStoreOptions): TelemetryStore {
  const idleGraceMs = options.idleGraceMs ?? DEFAULT_IDLE_GRACE_MS;
  const capacity = options.ringBufferCapacity ?? DEFAULT_RING_BUFFER_CAPACITY;

  const subscribers = new Map<string, number>();
  const buffers = new Map<string, TelemetryFrame[]>();
  const latest = new Map<string, TelemetryFrame>();
  const listeners = new Set<() => void>();
  let socket: WebSocket | null = null;
  let connectionState: TelemetryConnectionState = "closed";
  let idleTimer: ReturnType<typeof setTimeout> | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const notify = () => {
    listeners.forEach((l) => l());
  };

  const openSocket = () => {
    if (socket || !options.accessToken) return;
    connectionState = "connecting";
    const ws = new WebSocket(
      buildWebSocketUrl("/ws/telemetry", {
        access_token: options.accessToken,
        tenant_id: options.tenantId,
      }),
    );
    socket = ws;
    ws.onopen = () => {
      connectionState = "open";
      notify();
    };
    ws.onerror = () => {
      connectionState = "error";
      notify();
    };
    ws.onclose = () => {
      socket = null;
      connectionState = "closed";
      notify();
      if (subscribers.size > 0) {
        reconnectTimer = setTimeout(openSocket, 1_500);
      }
    };
    ws.onmessage = (event) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(String(event.data));
      } catch {
        return;
      }
      const frames = parseTelemetryPayload(parsed);
      if (frames.length === 0) return;
      for (const frame of frames) {
        if (!subscribers.has(frame.camera_id)) continue;
        latest.set(frame.camera_id, frame);
        const buffer = buffers.get(frame.camera_id) ?? [];
        buffer.push(frame);
        if (buffer.length > capacity) {
          buffer.splice(0, buffer.length - capacity);
        }
        buffers.set(frame.camera_id, buffer);
      }
      notify();
    };
  };

  const closeSocket = () => {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    socket?.close();
    socket = null;
  };

  const scheduleIdleClose = () => {
    if (idleTimer !== null) clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      if (subscribers.size === 0) {
        closeSocket();
      }
      idleTimer = null;
    }, idleGraceMs);
  };

  return {
    subscribe(cameraId) {
      if (idleTimer !== null) {
        clearTimeout(idleTimer);
        idleTimer = null;
      }
      subscribers.set(cameraId, (subscribers.get(cameraId) ?? 0) + 1);
      if (!socket) openSocket();
    },
    unsubscribe(cameraId) {
      const next = (subscribers.get(cameraId) ?? 1) - 1;
      if (next <= 0) {
        subscribers.delete(cameraId);
      } else {
        subscribers.set(cameraId, next);
      }
      if (subscribers.size === 0) scheduleIdleClose();
    },
    getLatest(cameraId) {
      return latest.get(cameraId) ?? null;
    },
    getBuffer(cameraId) {
      return buffers.get(cameraId) ?? [];
    },
    connectionState() {
      return connectionState;
    },
    onChange(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

type StoreHolder = {
  instance: TelemetryStore | null;
  accessToken: string | null;
  tenantId: string | null;
};

export const useTelemetryStore = create<StoreHolder>(() => ({
  instance: null,
  accessToken: null,
  tenantId: null,
}));

export function ensureTelemetryStore(
  accessToken: string | null,
  tenantId: string | null,
): TelemetryStore | null {
  if (!accessToken) return null;
  const state = useTelemetryStore.getState();
  if (
    state.instance &&
    state.accessToken === accessToken &&
    state.tenantId === tenantId
  ) {
    return state.instance;
  }
  const instance = createTelemetryStore({ accessToken, tenantId });
  useTelemetryStore.setState({ instance, accessToken, tenantId });
  return instance;
}
