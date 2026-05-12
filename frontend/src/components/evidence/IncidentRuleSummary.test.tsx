import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { IncidentRuleSummary } from "@/components/evidence/IncidentRuleSummary";

describe("IncidentRuleSummary", () => {
  test("renders captured rule provenance and detection context", () => {
    render(
      <IncidentRuleSummary
        triggerRule={{
          id: "99999999-9999-9999-9999-999999999111",
          name: "Restricted person in server room",
          incident_type: "restricted_person",
          severity: "critical",
          action: "record_clip",
          cooldown_seconds: 45,
          predicate: {
            class_names: ["person"],
            zone_ids: ["server-room"],
            min_confidence: 0.82,
            attributes: { vest: "red" },
          },
          rule_hash:
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        }}
        detection={{
          class_name: "person",
          zone_id: "server-room",
          confidence: 0.91,
        }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: /trigger rule/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Restricted person in server room"),
    ).toBeInTheDocument();
    expect(screen.getByText("restricted_person")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("record_clip")).toBeInTheDocument();
    expect(screen.getByText("45s")).toBeInTheDocument();
    expect(screen.getByText("ffffffffffff")).toBeInTheDocument();
    expect(screen.getByText("person")).toBeInTheDocument();
    expect(screen.getAllByText("server-room").length).toBeGreaterThan(0);
    expect(screen.getByText("91%")).toBeInTheDocument();
  });
});
