import { describe, expect, test } from "vitest";

import type { Camera } from "@/hooks/use-cameras";
import type { HistoryClassesResponse, HistorySeriesResponse } from "@/hooks/use-history";
import { buildHistorySearchResults } from "@/lib/history-search";

const cameras = [
  {
    id: "cam-gate",
    name: "Gate camera",
    zones: [{ id: "gate-line", name: "Gate line" }],
  },
] as unknown as Camera[];

const classes = {
  from: "2026-04-27T10:00:00Z",
  to: "2026-04-27T12:00:00Z",
  classes: [
    { class_name: "gate", event_count: 4, has_speed_data: false },
    { class_name: "car", event_count: 14, has_speed_data: true },
  ],
} as HistoryClassesResponse;

const series = {
  granularity: "1h",
  class_names: ["gate", "car"],
  rows: [
    { bucket: "2026-04-27T10:00:00Z", values: { gate: 0, car: 0 }, total_count: 0 },
    {
      bucket: "2026-04-27T11:00:00Z",
      values: { gate: 6, car: 22 },
      total_count: 28,
      over_threshold_count: { car: 3 },
    },
  ],
  granularity_adjusted: false,
  speed_classes_capped: false,
  speed_classes_used: ["car"],
  bucket_count: 2,
  coverage_status: "populated",
  coverage_by_bucket: [
    { bucket: "2026-04-27T10:00:00Z", status: "zero" },
    { bucket: "2026-04-27T11:00:00Z", status: "populated" },
  ],
} as HistorySeriesResponse;

describe("buildHistorySearchResults", () => {
  test("searches cameras boundaries and classes", () => {
    const results = buildHistorySearchResults({ query: "gate", cameras, classes, series });

    expect(results).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "camera", label: "Gate camera", cameraId: "cam-gate" }),
        expect.objectContaining({
          type: "boundary",
          label: "Gate line",
          boundaryId: "gate-line",
          cameraId: "cam-gate",
        }),
        expect.objectContaining({ type: "class", label: "gate", className: "gate" }),
      ]),
    );
  });

  test("finds zero coverage buckets", () => {
    const results = buildHistorySearchResults({ query: "zero", cameras, classes, series });

    expect(results).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "bucket", bucket: "2026-04-27T10:00:00Z" }),
      ]),
    );
  });

  test("finds speed breach buckets", () => {
    const results = buildHistorySearchResults({ query: "speed", cameras, classes, series });

    expect(results).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "bucket",
          bucket: "2026-04-27T11:00:00Z",
          group: "Speed breaches",
        }),
      ]),
    );
  });

  test("maps response boundary summaries back to matching camera zones", () => {
    const results = buildHistorySearchResults({
      query: "entry-line",
      cameras: [
        {
          id: "cam-1",
          name: "Gate camera",
          zones: [{ name: "Entry Line" }],
        },
      ] as unknown as Camera[],
      classes: {
        ...classes,
        boundaries: [{ boundary_id: "entry-line", event_types: ["line_cross"] }],
      },
      series,
    });

    expect(results).toContainEqual(
      expect.objectContaining({
        type: "boundary",
        label: "entry-line",
        boundaryId: "entry-line",
        cameraId: "cam-1",
      }),
    );
  });

  test("keeps stable order while limiting results", () => {
    const crowdedSeries = {
      ...series,
      rows: Array.from({ length: 25 }, (_, index) => ({
        bucket: `2026-04-27T${String(index).padStart(2, "0")}:00:00Z`,
        values: { car: 10 + index },
        total_count: 10 + index,
      })),
    } as HistorySeriesResponse;

    const results = buildHistorySearchResults({
      query: "spike",
      cameras: [],
      classes: [],
      series: crowdedSeries,
    });

    expect(results).toHaveLength(20);
    expect(results[0]).toEqual(expect.objectContaining({ bucket: "2026-04-27T00:00:00Z" }));
    expect(results[19]).toEqual(expect.objectContaining({ bucket: "2026-04-27T19:00:00Z" }));
  });
});
