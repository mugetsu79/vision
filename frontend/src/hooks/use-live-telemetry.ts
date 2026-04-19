import { useEffect, useMemo, useState } from "react";

import { parseTelemetryPayload, type TelemetryFrame } from "@/lib/live";
import { buildWebSocketUrl } from "@/lib/ws";
import { useAuthStore } from "@/stores/auth-store";

export type TelemetryConnectionState = "connecting" | "open" | "closed" | "error";

export function useLiveTelemetry(cameraIds: string[]) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const tenantId = useAuthStore((state) => state.user?.tenantId ?? null);
  const [framesByCamera, setFramesByCamera] = useState<Record<string, TelemetryFrame>>({});
  const [connectionState, setConnectionState] =
    useState<TelemetryConnectionState>("connecting");

  const cameraKey = useMemo(() => [...cameraIds].sort().join(","), [cameraIds]);

  useEffect(() => {
    if (!accessToken) {
      setConnectionState("closed");
      setFramesByCamera({});
      return;
    }

    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let disposed = false;
    const allowedCameras = new Set(cameraKey ? cameraKey.split(",") : []);

    const connect = () => {
      if (disposed) {
        return;
      }

      setConnectionState("connecting");
      socket = new WebSocket(
        buildWebSocketUrl("/ws/telemetry", {
          access_token: accessToken,
          tenant_id: tenantId,
        }),
      );

      socket.onopen = () => {
        if (!disposed) {
          setConnectionState("open");
        }
      };

      socket.onmessage = (event) => {
        let parsed: unknown = null;
        try {
          parsed = JSON.parse(String(event.data));
        } catch {
          return;
        }

        const frames = parseTelemetryPayload(parsed);
        if (frames.length === 0) {
          return;
        }

        setFramesByCamera((current) => {
          const next = { ...current };
          for (const frame of frames) {
            if (allowedCameras.size > 0 && !allowedCameras.has(frame.camera_id)) {
              continue;
            }
            next[frame.camera_id] = frame;
          }
          return next;
        });
      };

      socket.onerror = () => {
        if (!disposed) {
          setConnectionState("error");
        }
      };

      socket.onclose = () => {
        if (disposed) {
          return;
        }
        setConnectionState("closed");
        reconnectTimer = window.setTimeout(connect, 1_500);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [accessToken, tenantId, cameraKey]);

  return {
    connectionState,
    framesByCamera,
  } as const;
}
