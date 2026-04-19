type NetworkInformationLike = {
  effectiveType?: string;
  saveData?: boolean;
};

type PlaybackNavigator = {
  connection?: NetworkInformationLike;
  deviceMemory?: number;
  hardwareConcurrency?: number;
};

export type StreamRuntimeHints = {
  lowPower: boolean;
  maxConcurrentHlsSessions: number;
  saveData: boolean;
};

let activeHlsPlaybackSessions = 0;
const slotListeners = new Set<() => void>();

export function getStreamRuntimeHints(
  playbackNavigator: PlaybackNavigator | undefined = navigator,
): StreamRuntimeHints {
  const memory = playbackNavigator?.deviceMemory;
  const cpu = playbackNavigator?.hardwareConcurrency;
  const effectiveType = playbackNavigator?.connection?.effectiveType;
  const saveData = playbackNavigator?.connection?.saveData === true;
  const slowNetwork = effectiveType === "slow-2g" || effectiveType === "2g" || effectiveType === "3g";
  const lowPower =
    saveData ||
    slowNetwork ||
    (typeof memory === "number" && memory <= 4) ||
    (typeof cpu === "number" && cpu <= 4);

  return {
    lowPower,
    maxConcurrentHlsSessions: lowPower ? 1 : 2,
    saveData,
  };
}

export function acquireHlsPlaybackSlot(maxConcurrentHlsSessions: number): (() => void) | null {
  if (activeHlsPlaybackSessions >= maxConcurrentHlsSessions) {
    return null;
  }

  activeHlsPlaybackSessions += 1;
  let released = false;

  return () => {
    if (released) {
      return;
    }

    released = true;
    activeHlsPlaybackSessions = Math.max(0, activeHlsPlaybackSessions - 1);
    for (const listener of slotListeners) {
      listener();
    }
  };
}

export function subscribeToHlsPlaybackBudget(listener: () => void): () => void {
  slotListeners.add(listener);
  return () => {
    slotListeners.delete(listener);
  };
}

export function __resetHlsPlaybackBudgetForTests() {
  activeHlsPlaybackSessions = 0;
  slotListeners.clear();
}
