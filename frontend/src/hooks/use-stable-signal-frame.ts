import { useEffect, useMemo, useState } from "react";

import type { components } from "@/lib/api.generated";
import {
  DEFAULT_SIGNAL_HOLD_MS,
  deriveSignalCounts,
  updateSignalTracks,
  type SignalCounts,
  type SignalTrack,
} from "@/lib/live-signal-stability";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];

const SIGNAL_REFRESH_MS = 200;

export type StableSignalSnapshot = {
  tracks: SignalTrack[];
  counts: SignalCounts;
  latestFrame: TelemetryFrame | null | undefined;
};

export function useStableSignalFrame(
  frame: TelemetryFrame | null | undefined,
  activeClasses: string[] | null,
  holdMs = DEFAULT_SIGNAL_HOLD_MS,
): StableSignalSnapshot {
  const [tracks, setTracks] = useState<SignalTrack[]>([]);

  useEffect(() => {
    setTracks((previous) =>
      updateSignalTracks({
        previous,
        frame,
        activeClasses,
        nowMs: Date.now(),
        holdMs,
      }),
    );
  }, [activeClasses, frame, holdMs]);

  const hasTracks = tracks.length > 0;

  useEffect(() => {
    if (!hasTracks) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setTracks((previous) =>
        updateSignalTracks({
          previous,
          frame: null,
          activeClasses,
          nowMs: Date.now(),
          holdMs,
        }),
      );
    }, SIGNAL_REFRESH_MS);

    return () => {
      window.clearInterval(interval);
    };
  }, [activeClasses, hasTracks, holdMs]);

  const counts = useMemo(() => deriveSignalCounts(tracks), [tracks]);

  return {
    tracks,
    counts,
    latestFrame: frame,
  };
}
