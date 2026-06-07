import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  test("renders a distinct scalable glyph for each operational pattern type", () => {
    render(
      <OperationalMemoryPanel
        patterns={[
          pattern({
            id: "00000000-0000-0000-0000-000000000901",
            pattern_type: "event_burst",
            evidence: { incident_count: 5 },
          }),
          pattern({
            id: "00000000-0000-0000-0000-000000000902",
            pattern_type: "zone_hotspot",
            dimensions: { zone_id: "forklift-gate", contract_count: 3 },
            evidence: { incident_count: 8 },
          }),
          pattern({
            id: "00000000-0000-0000-0000-000000000903",
            pattern_type: "storage_failure",
            severity: "critical",
            dimensions: { provider: "minio", scope: "cloud" },
            evidence: { artifact_count: 4, statuses: ["capture_failed"] },
          }),
        ]}
      />,
    );

    const panel = screen.getByTestId("operational-memory-panel");
    expect(
      within(panel).getByTestId("pattern-glyph-event-burst"),
    ).toHaveAccessibleName(/event burst pattern/i);
    expect(
      within(panel).getByTestId("pattern-glyph-zone-hotspot"),
    ).toHaveAccessibleName(/zone hotspot pattern/i);
    expect(
      within(panel).getByTestId("pattern-glyph-storage-failure"),
    ).toHaveAccessibleName(/storage failure pattern/i);
  });

  test("paginates long observed-pattern sets with the shared page sizes", async () => {
    const user = userEvent.setup();
    render(
      <OperationalMemoryPanel
        patterns={Array.from({ length: 12 }, (_, index) =>
          pattern({
            id: `00000000-0000-0000-0000-${String(index + 1).padStart(12, "0")}`,
            summary: `Observed pattern ${String(index + 1).padStart(2, "0")}`,
          }),
        )}
      />,
    );

    const panel = screen.getByTestId("operational-memory-panel");
    expect(
      within(panel).getByText("Observed pattern 10"),
    ).toBeInTheDocument();
    expect(
      within(panel).queryByText("Observed pattern 11"),
    ).not.toBeInTheDocument();
    expect(within(panel).getByText("1-10 of 12 patterns")).toBeInTheDocument();

    await user.selectOptions(
      within(panel).getByLabelText(/observed patterns per page/i),
      "25",
    );

    expect(
      within(panel).getByText("Observed pattern 11"),
    ).toBeInTheDocument();
    expect(within(panel).getByText("1-12 of 12 patterns")).toBeInTheDocument();
  });
});
