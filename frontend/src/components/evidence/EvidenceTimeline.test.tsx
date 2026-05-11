import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import type { Incident } from "@/hooks/use-incidents";

import { EvidenceTimeline } from "./EvidenceTimeline";

function incident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "incident-1",
    camera_id: "camera-1",
    camera_name: "Dock",
    ts: "2026-05-11T10:05:00Z",
    type: "ppe-missing",
    payload: {},
    snapshot_url: null,
    clip_url: null,
    storage_bytes: 0,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
    ...overrides,
  };
}

describe("EvidenceTimeline", () => {
  test("renders density buckets and selects a bucket incident", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <EvidenceTimeline
        incidents={[
          incident({ id: "a", ts: "2026-05-11T10:05:00Z" }),
          incident({ id: "b", ts: "2026-05-11T10:35:00Z", type: "zone-entry" }),
          incident({ id: "c", ts: "2026-05-11T11:10:00Z" }),
        ]}
        selectedIncidentId="b"
        onSelect={onSelect}
      />,
    );

    const timeline = screen.getByRole("navigation", {
      name: /evidence timeline/i,
    });
    const buckets = within(timeline).getAllByRole("button");

    expect(buckets).toHaveLength(2);
    expect(buckets[0]).toHaveTextContent("2 records");
    expect(buckets[0]).toHaveTextContent("Selected");
    expect(buckets[1]).toHaveTextContent("1 record");

    await user.click(buckets[1]);

    expect(onSelect).toHaveBeenCalledWith("c");
  });
});
