import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { components } from "@/lib/api.generated";

import { OperationalMemoryPanel } from "./OperationalMemoryPanel";

type OperationalMemoryPattern =
  components["schemas"]["OperationalMemoryPatternResponse"];

function pattern(
  overrides: Partial<OperationalMemoryPattern> = {},
): OperationalMemoryPattern {
  return {
    id: "00000000-0000-0000-0000-000000000901",
    tenant_id: "00000000-0000-0000-0000-000000000101",
    site_id: "00000000-0000-0000-0000-000000000201",
    camera_id: "00000000-0000-0000-0000-000000000301",
    pattern_type: "event_burst",
    severity: "warning",
    summary: "Observed pattern: 3 incidents in one zone.",
    window_started_at: "2026-05-12T08:00:00Z",
    window_ended_at: "2026-05-12T08:15:00Z",
    source_incident_ids: [
      "00000000-0000-0000-0000-000000000701",
      "00000000-0000-0000-0000-000000000702",
    ],
    source_contract_hashes: ["a".repeat(64)],
    dimensions: { zone_id: "server-room", incident_count: 3 },
    evidence: { incident_count: 3 },
    pattern_hash: "b".repeat(64),
    created_at: "2026-05-12T08:20:00Z",
    ...overrides,
  };
}

describe("OperationalMemoryPanel", () => {
  test("renders observed memory patterns with source citations", () => {
    render(<OperationalMemoryPanel patterns={[pattern()]} />);

    const panel = screen.getByTestId("operational-memory-panel");
    expect(within(panel).getByText("Observed patterns")).toBeInTheDocument();
    expect(
      within(panel).getByText("Observed pattern: 3 incidents in one zone."),
    ).toBeInTheDocument();
    expect(within(panel).getByText("warning")).toBeInTheDocument();
    expect(within(panel).getByText("event burst")).toBeInTheDocument();
    expect(within(panel).getByText("00000000-0701")).toBeInTheDocument();
    expect(within(panel).getByText("aaaaaaaaaaaa")).toBeInTheDocument();
    expect(within(panel).queryByText(/predicted/i)).not.toBeInTheDocument();
  });

  test("shows an empty state without predictive language", () => {
    render(<OperationalMemoryPanel patterns={[]} />);

    const panel = screen.getByTestId("operational-memory-panel");
    expect(within(panel).getByText("No observed patterns")).toBeInTheDocument();
    expect(within(panel).queryByText(/forecast/i)).not.toBeInTheDocument();
  });
});
