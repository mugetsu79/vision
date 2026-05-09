import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { TelemetryCanvas } from "@/components/live/TelemetryCanvas";
import type { components } from "@/lib/api.generated";
import { colorForClass, type SignalTrack } from "@/lib/live-signal-stability";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];

const fillTextMock = vi.fn();
const strokeRectMock = vi.fn();
const clearRectMock = vi.fn();
const scaleMock = vi.fn();
const setTransformMock = vi.fn();
const beginPathMock = vi.fn();
const roundRectMock = vi.fn();
const fillMock = vi.fn();
const strokeMock = vi.fn();
const setLineDashMock = vi.fn();

describe("TelemetryCanvas", () => {
  beforeEach(() => {
    vi.spyOn(window, "devicePixelRatio", "get").mockReturnValue(1);
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      clearRect: clearRectMock,
      scale: scaleMock,
      setTransform: setTransformMock,
      beginPath: beginPathMock,
      roundRect: roundRectMock,
      fill: fillMock,
      stroke: strokeMock,
      fillText: fillTextMock,
      strokeRect: strokeRectMock,
      setLineDash: setLineDashMock,
      measureText: () => ({ width: 60 }),
      font: "",
      lineWidth: 1,
      strokeStyle: "",
      fillStyle: "",
    } as unknown as CanvasRenderingContext2D);

    class ResizeObserverMock {
      constructor(private readonly callback: ResizeObserverCallback) {}

      observe(target: Element) {
        this.callback(
          [
            {
              target,
              contentRect: {
                width: 640,
                height: 360,
                x: 0,
                y: 0,
                top: 0,
                left: 0,
                bottom: 360,
                right: 640,
                toJSON: () => ({}),
              },
            } as ResizeObserverEntry,
          ],
          this as unknown as ResizeObserver,
        );
      }

      unobserve() {}

      disconnect() {}
    }

    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    vi.stubGlobal(
      "requestAnimationFrame",
      (callback: FrameRequestCallback) =>
        window.setTimeout(() => {
          callback(16);
        }, 0),
    );
    vi.stubGlobal("cancelAnimationFrame", (handle: number) => {
      window.clearTimeout(handle);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    fillTextMock.mockReset();
    strokeRectMock.mockReset();
    clearRectMock.mockReset();
    scaleMock.mockReset();
    setTransformMock.mockReset();
    beginPathMock.mockReset();
    roundRectMock.mockReset();
    fillMock.mockReset();
    strokeMock.mockReset();
    setLineDashMock.mockReset();
  });

  test("redraws overlays from stable tracks with held-state styling", async () => {
    const frame: TelemetryFrame = {
      camera_id: "11111111-1111-1111-1111-111111111111",
      ts: "2026-04-19T09:15:00Z",
      profile: "central-gpu",
      stream_mode: "annotated-whip",
      counts: { bus: 1, car: 1 },
      tracks: [
        {
          class_name: "car",
          confidence: 0.93,
          bbox: { x1: 100, y1: 120, x2: 340, y2: 260 },
          track_id: 7,
          speed_kph: 42,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
        {
          class_name: "bus",
          confidence: 0.88,
          bbox: { x1: 480, y1: 110, x2: 760, y2: 310 },
          track_id: 12,
          speed_kph: null,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
      ],
    };

    const view = render(
      <div style={{ width: 640, height: 360 }}>
        <TelemetryCanvas frame={frame} activeClasses={null} />
      </div>,
    );

    await waitFor(() =>
      expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("bus"))).toBe(true),
    );

    fillTextMock.mockClear();
    strokeRectMock.mockClear();
    setLineDashMock.mockClear();

    view.rerender(
      <div style={{ width: 640, height: 360 }}>
        <TelemetryCanvas
          frame={frame}
          activeClasses={["car"]}
          tracks={[signalTrack(frame.tracks[0]), signalTrack(frame.tracks[1], "held")]}
        />
      </div>,
    );

    await waitFor(() =>
      expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("car"))).toBe(true),
    );
    expect(strokeRectMock).toHaveBeenCalledTimes(2);
    expect(setLineDashMock).toHaveBeenCalledWith([6, 5]);
    expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("last seen"))).toBe(true);
  });

  test("filters raw frame tracks when stable tracks are omitted", async () => {
    const frame: TelemetryFrame = {
      camera_id: "11111111-1111-1111-1111-111111111111",
      ts: "2026-04-19T09:15:00Z",
      profile: "central-gpu",
      stream_mode: "annotated-whip",
      counts: { bus: 1, car: 1 },
      tracks: [
        {
          class_name: "car",
          confidence: 0.93,
          bbox: { x1: 100, y1: 120, x2: 340, y2: 260 },
          track_id: 7,
          speed_kph: 42,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
        {
          class_name: "bus",
          confidence: 0.88,
          bbox: { x1: 480, y1: 110, x2: 760, y2: 310 },
          track_id: 12,
          speed_kph: null,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
      ],
    };

    render(
      <div style={{ width: 640, height: 360 }}>
        <TelemetryCanvas frame={frame} activeClasses={["car"]} />
      </div>,
    );

    await waitFor(() =>
      expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("car"))).toBe(true),
    );
    expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("bus"))).toBe(false);
    expect(strokeRectMock.mock.calls.length).toBeGreaterThanOrEqual(1);
  });

  test("does not draw a frontend overlay when disabled", async () => {
    const frame: TelemetryFrame = {
      camera_id: "11111111-1111-1111-1111-111111111111",
      ts: "2026-04-19T09:15:00Z",
      profile: "central-gpu",
      stream_mode: "annotated-whip",
      counts: { person: 1 },
      tracks: [
        {
          class_name: "person",
          confidence: 0.93,
          bbox: { x1: 640, y1: 240, x2: 960, y2: 620 },
          track_id: 3,
          speed_kph: 0,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
      ],
    };

    render(
      <div style={{ width: 640, height: 360 }}>
        <TelemetryCanvas frame={frame} activeClasses={null} disabled />
      </div>,
    );

    await waitFor(() => expect(clearRectMock).toHaveBeenCalled());
    expect(strokeRectMock).not.toHaveBeenCalled();
    expect(fillTextMock).not.toHaveBeenCalled();
  });

  test("scales telemetry boxes from the real source size when provided", async () => {
    const frame: TelemetryFrame = {
      camera_id: "11111111-1111-1111-1111-111111111111",
      ts: "2026-04-19T09:15:00Z",
      profile: "central-gpu",
      stream_mode: "passthrough",
      counts: { person: 1 },
      tracks: [
        {
          class_name: "person",
          confidence: 0.93,
          bbox: { x1: 640, y1: 240, x2: 960, y2: 620 },
          track_id: 3,
          speed_kph: 0,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
      ],
    };

    render(
      <div style={{ width: 640, height: 360 }}>
        <TelemetryCanvas
          frame={frame}
          activeClasses={null}
          sourceSize={{ width: 1280, height: 720 }}
        />
      </div>,
    );

    await waitFor(() => expect(strokeRectMock).toHaveBeenCalled());
    expect(strokeRectMock).toHaveBeenCalledWith(320, 120, 160, 190);
  });

  test("matches object-cover crop offsets for non-widescreen sources", async () => {
    const frame: TelemetryFrame = {
      camera_id: "11111111-1111-1111-1111-111111111111",
      ts: "2026-04-19T09:15:00Z",
      profile: "central-gpu",
      stream_mode: "passthrough",
      counts: { person: 1 },
      tracks: [
        {
          class_name: "person",
          confidence: 0.93,
          bbox: { x1: 640, y1: 240, x2: 960, y2: 620 },
          track_id: 3,
          speed_kph: 0,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
      ],
    };

    render(
      <div style={{ width: 640, height: 360 }}>
        <TelemetryCanvas
          frame={frame}
          activeClasses={null}
          sourceSize={{ width: 1280, height: 960 }}
        />
      </div>,
    );

    await waitFor(() => expect(strokeRectMock).toHaveBeenCalled());
    expect(strokeRectMock).toHaveBeenCalledWith(320, 60, 160, 190);
  });

  test("does not expose raw tracker ids in user-facing labels", async () => {
    const frame: TelemetryFrame = {
      camera_id: "11111111-1111-1111-1111-111111111111",
      ts: "2026-04-19T09:15:00Z",
      profile: "central-gpu",
      stream_mode: "passthrough",
      counts: { person: 1 },
      tracks: [
        {
          class_name: "person",
          confidence: 0.93,
          bbox: { x1: 100, y1: 100, x2: 240, y2: 320 },
          track_id: 12,
          speed_kph: 0,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
      ],
    };

    render(
      <div style={{ width: 640, height: 360 }}>
        <TelemetryCanvas frame={frame} activeClasses={null} />
      </div>,
    );

    await waitFor(() =>
      expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("person"))).toBe(true),
    );
    expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("#12"))).toBe(false);
  });

  test("exposes the telemetry overlay canvas for inspection", () => {
    render(<TelemetryCanvas frame={null} activeClasses={null} />);

    expect(screen.getByLabelText(/telemetry overlay/i)).toBeInTheDocument();
  });
});

function signalTrack(
  track: TelemetryFrame["tracks"][number],
  state: "live" | "held" = "live",
): SignalTrack {
  return {
    key: `${track.class_name}:${track.track_id}`,
    track,
    color: colorForClass(track.class_name),
    state,
    firstSeenMs: 1_000,
    lastSeenMs: 1_000,
    ageMs: state === "held" ? 800 : 0,
  };
}
