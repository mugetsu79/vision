import { afterEach, describe, expect, test } from "vitest";

import {
  __resetHlsPlaybackBudgetForTests,
  acquireHlsPlaybackSlot,
  getStreamRuntimeHints,
} from "@/lib/stream-playback";

describe("stream-playback", () => {
  afterEach(() => {
    __resetHlsPlaybackBudgetForTests();
  });

  test("detects constrained playback environments from device and network hints", () => {
    const lowPower = getStreamRuntimeHints({
      connection: {
        effectiveType: "3g",
        saveData: false,
      },
      deviceMemory: 4,
      hardwareConcurrency: 4,
    });

    expect(lowPower.lowPower).toBe(true);
    expect(lowPower.maxConcurrentHlsSessions).toBe(1);

    const standard = getStreamRuntimeHints({
      connection: {
        effectiveType: "4g",
        saveData: false,
      },
      deviceMemory: 8,
      hardwareConcurrency: 8,
    });

    expect(standard.lowPower).toBe(false);
    expect(standard.maxConcurrentHlsSessions).toBe(2);
  });

  test("limits HLS playback slots until an active session releases one", () => {
    const releaseFirst = acquireHlsPlaybackSlot(1);
    expect(releaseFirst).toBeTypeOf("function");

    const second = acquireHlsPlaybackSlot(1);
    expect(second).toBeNull();

    releaseFirst?.();

    const releaseReplacement = acquireHlsPlaybackSlot(1);
    expect(releaseReplacement).toBeTypeOf("function");
    releaseReplacement?.();
  });
});
