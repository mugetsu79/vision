import { describe, expect, test } from "vitest";

import type { Incident } from "@/hooks/use-incidents";

import {
  buildEvidenceTimelineBuckets,
  describeEvidenceState,
  incidentTypeAccent,
} from "./evidence-signals";

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

describe("evidence signals", () => {
  test("builds timeline buckets and marks the selected incident bucket", () => {
    const buckets = buildEvidenceTimelineBuckets(
      [
        incident({ id: "a", ts: "2026-05-11T10:05:00Z", type: "ppe-missing" }),
        incident({ id: "b", ts: "2026-05-11T10:35:00Z", type: "zone-entry" }),
        incident({ id: "c", ts: "2026-05-11T11:10:00Z", type: "ppe-missing" }),
      ],
      "b",
    );

    expect(buckets).toHaveLength(2);
    expect(buckets[0]).toMatchObject({
      count: 2,
      selected: true,
      dominantType: "ppe-missing",
    });
    expect(buckets[1]).toMatchObject({
      count: 1,
      selected: false,
      dominantType: "ppe-missing",
    });
  });

  test("describes clip, snapshot, combined, and metadata-only evidence states", () => {
    expect(
      describeEvidenceState(incident({ clip_url: "https://example.test/clip.mjpeg" }))
        .label,
    ).toBe("Clip only");
    expect(
      describeEvidenceState(
        incident({ snapshot_url: "https://example.test/still.jpg" }),
      ).label,
    ).toBe("Snapshot only");
    expect(
      describeEvidenceState(
        incident({
          clip_url: "https://example.test/clip.mjpeg",
          snapshot_url: "https://example.test/still.jpg",
        }),
      ).label,
    ).toBe("Clip and snapshot");
    expect(describeEvidenceState(incident()).label).toBe("Metadata only");
  });

  test("assigns stable accents for incident types", () => {
    expect(incidentTypeAccent("ppe-missing")).toBe(incidentTypeAccent("ppe-missing"));
    expect(incidentTypeAccent("ppe-missing")).toMatch(/^#[0-9a-f]{6}$/);
  });
});
