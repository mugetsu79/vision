import { useEffect, useMemo, useState } from "react";

import { ensureTelemetryStore } from "@/stores/telemetry-store";
import type { TelemetryConnectionState } from "@/stores/telemetry-store";
import type { TelemetryFrame } from "@/lib/live";
import { useAuthStore } from "@/stores/auth-store";

export type { TelemetryConnectionState };

export function useLiveTelemetry(cameraIds: string[]) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const tenantId = useAuthStore((state) => state.user?.tenantId ?? null);
  const [framesByCamera, setFramesByCamera] = useState<Record<string, TelemetryFrame>>({});
  const [connectionState, setConnectionState] = useState<TelemetryConnectionState>("closed");

  const cameraKey = useMemo(() => [...cameraIds].sort().join(","), [cameraIds]);

  useEffect(() => {
    const store = ensureTelemetryStore(accessToken, tenantId);
    if (!store) {
      setConnectionState("closed");
      setFramesByCamera({});
      return;
    }

    const ids = cameraKey ? cameraKey.split(",") : [];
    ids.forEach((id) => store.subscribe(id));

    // Hydrate immediately from whatever the store already retained — otherwise
    // a remount into a still-open socket renders blank until the next WS frame.
    setConnectionState(store.connectionState());
    setFramesByCamera((current) => {
      const next: Record<string, TelemetryFrame> = { ...current };
      let changed = false;
      for (const id of ids) {
        const frame = store.getLatest(id);
        if (frame && next[id] !== frame) {
          next[id] = frame;
          changed = true;
        }
      }
      return changed ? next : current;
    });

    const unsubscribe = store.onChange(() => {
      setConnectionState(store.connectionState());
      setFramesByCamera((current) => {
        const next: Record<string, TelemetryFrame> = {};
        for (const id of ids) {
          const frame = store.getLatest(id);
          if (frame) {
            next[id] = frame;
          } else if (current[id]) {
            next[id] = current[id];
          }
        }
        return next;
      });
    });

    return () => {
      unsubscribe();
      ids.forEach((id) => store.unsubscribe(id));
    };
  }, [accessToken, tenantId, cameraKey]);

  return {
    connectionState,
    framesByCamera,
  } as const;
}
