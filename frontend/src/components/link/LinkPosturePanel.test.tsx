import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { LinkPosturePanel } from "@/components/link/LinkPosturePanel";

describe("LinkPosturePanel", () => {
  test("uses fallback active path details instead of unknown active connection labels", () => {
    render(
      <LinkPosturePanel
        status={{
          active_connection: null,
          fallback_active_path: {
            detail: "Latest edge-agent sample 4 ms / 128 Mbps / 0% loss",
            label: "Vezor Master reflector via jetson-orin-1 Core Link",
          },
          latest_probe: null,
          link_state: "healthy",
          passport_hash: "abcdef123456",
          queue_depth: {},
        }}
      />,
    );

    expect(
      screen.getByText("Vezor Master reflector via jetson-orin-1 Core Link"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Latest edge-agent sample 4 ms / 128 Mbps / 0% loss"),
    ).toBeInTheDocument();
    expect(screen.queryByText("unknown / unknown")).not.toBeInTheDocument();
  });
});
