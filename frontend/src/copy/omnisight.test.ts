import { describe, expect, test } from "vitest";

import {
  omniEmptyStates,
  omniLabels,
  omniNavGroups,
  omniPlaceExamples,
} from "@/copy/omnisight";

describe("omnisight copy", () => {
  test("uses broad product labels instead of traffic-specific framing", () => {
    expect(omniLabels.liveTitle).toBe("Live Intelligence");
    expect(omniLabels.historyTitle).toBe("History & Patterns");
    expect(omniLabels.evidenceTitle).toBe("Evidence Desk");
    expect(omniLabels.sceneSetupTitle).toBe("Scene Setup");
    expect(omniLabels.operationsTitle).toBe("Operations");
  });

  test("keeps navigation broad while preserving existing route paths", () => {
    expect(omniNavGroups).toEqual([
      {
        label: "Intelligence",
        items: [
          { label: "Dashboard", to: "/dashboard" },
          { label: "Live", to: "/live" },
          { label: "Patterns", to: "/history" },
          { label: "Evidence", to: "/incidents" },
        ],
      },
      {
        label: "Control",
        items: [
          { label: "Deployment", to: "/deployment" },
          { label: "Sites", to: "/sites" },
          { label: "Scenes", to: "/cameras" },
          { label: "Operations", to: "/settings" },
        ],
      },
    ]);
  });

  test("uses product-neutral empty states and examples", () => {
    expect(omniEmptyStates.noScenes).toBe("No scenes are connected yet.");
    expect(omniEmptyStates.noSignals).toBe(
      "Live telemetry has not produced visible signals yet.",
    );
    expect(omniPlaceExamples.askVezor).toBe(
      "show people near restricted zones",
    );
  });
});
