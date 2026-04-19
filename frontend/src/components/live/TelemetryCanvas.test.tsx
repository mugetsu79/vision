import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { TelemetryCanvas } from "@/components/live/TelemetryCanvas";
import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];

const fillTextMock = vi.fn();
const strokeRectMock = vi.fn();
const clearRectMock = vi.fn();
const scaleMock = vi.fn();
const setTransformMock = vi.fn();
const beginPathMock = vi.fn();
const roundRectMock = vi.fn();
const fillMock = vi.fn();

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
      fillText: fillTextMock,
      strokeRect: strokeRectMock,
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
  });

  test("redraws overlays and filters tracks when the resolved classes change", async () => {
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

    view.rerender(
      <div style={{ width: 640, height: 360 }}>
        <TelemetryCanvas frame={frame} activeClasses={["car"]} />
      </div>,
    );

    await waitFor(() =>
      expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("car"))).toBe(true),
    );
    expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("bus"))).toBe(false);
    expect(strokeRectMock).toHaveBeenCalledTimes(1);
  });
});
