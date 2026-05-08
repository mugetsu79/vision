import { describe, expect, test } from "vitest";

import { motionPresets } from "@/lib/motion";

describe("motionPresets", () => {
  test("rise preset uses 240ms ease-product duration tokens", () => {
    expect(motionPresets.rise.transition.duration).toBeCloseTo(0.24);
    expect(motionPresets.rise.transition.ease).toEqual([0.22, 1, 0.36, 1]);
  });

  test("evidenceSwap is slide-from-right + fade", () => {
    expect(typeof motionPresets.evidenceSwap.initial.x).toBe("number");
    expect(motionPresets.evidenceSwap.initial.opacity).toBe(0);
    expect(motionPresets.evidenceSwap.animate).toMatchObject({
      x: 0,
      opacity: 1,
    });
  });

  test("lensSnap uses spring or product easing within 320ms cap", () => {
    expect(motionPresets.lensSnap.transition.duration).toBeLessThanOrEqual(
      0.32,
    );
  });
});
