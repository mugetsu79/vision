import { useEffect, useRef } from "react";

import { filterTracks } from "@/lib/live";
import type { components } from "@/lib/api.generated";
import { colorForClass, type SignalTrack } from "@/lib/live-signal-stability";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];

export function TelemetryCanvas({
  frame,
  activeClasses,
  tracks,
}: {
  frame: TelemetryFrame | null | undefined;
  activeClasses: string[] | null;
  tracks?: SignalTrack[];
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sizeRef = useRef({ width: 0, height: 0 });
  const frameRef = useRef<TelemetryFrame | null | undefined>(frame);
  const activeClassesRef = useRef<string[] | null>(activeClasses);
  const tracksRef = useRef<SignalTrack[] | undefined>(tracks);
  const animationFrameRef = useRef<number | null>(null);
  const drawFrameRef = useRef<() => void>(() => undefined);
  const scheduleDrawRef = useRef<() => void>(() => undefined);

  frameRef.current = frame;
  activeClassesRef.current = activeClasses;
  tracksRef.current = tracks;

  const drawFrame = () => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    const { width, height } = sizeRef.current;
    context.clearRect(0, 0, width, height);

    const visibleSignals =
      tracksRef.current ??
      filterTracks(frameRef.current, activeClassesRef.current).map((track): SignalTrack => ({
        key: `${track.class_name}:${track.track_id}`,
        track,
        color: colorForClass(track.class_name),
        state: "live",
        firstSeenMs: 0,
        lastSeenMs: 0,
        ageMs: 0,
      }));

    if (visibleSignals.length === 0) {
      return;
    }

    const sourceWidth = Math.max(
      ...visibleSignals.map((signal) => getCoordinate(signal.track.bbox, "x2")),
      1,
    );
    const sourceHeight = Math.max(
      ...visibleSignals.map((signal) => getCoordinate(signal.track.bbox, "y2")),
      1,
    );
    const scaleX = width / sourceWidth;
    const scaleY = height / sourceHeight;

    context.lineWidth = 2;
    context.font = "12px ui-sans-serif, system-ui, sans-serif";

    for (const signal of visibleSignals) {
      const { track } = signal;
      const x1 = getCoordinate(track.bbox, "x1") * scaleX;
      const y1 = getCoordinate(track.bbox, "y1") * scaleY;
      const x2 = getCoordinate(track.bbox, "x2") * scaleX;
      const y2 = getCoordinate(track.bbox, "y2") * scaleY;
      const label = [
        `${track.class_name} #${track.track_id}`,
        signal.state === "held" ? `last seen ${formatAge(signal.ageMs)}` : null,
        typeof track.speed_kph === "number" ? `${Math.round(track.speed_kph)} km/h` : null,
      ]
        .filter(Boolean)
        .join(" ");

      context.globalAlpha = signal.state === "held" ? 0.55 : 1;
      context.setLineDash?.(signal.state === "held" ? [6, 5] : []);
      context.strokeStyle = signal.color.stroke;
      context.fillStyle = signal.color.text;
      context.strokeRect(x1, y1, Math.max(4, x2 - x1), Math.max(4, y2 - y1));
      context.fillText(label, x1 + 4, Math.max(14, y1 - 6));
    }

    context.globalAlpha = 1;
    context.setLineDash?.([]);
  };

  const scheduleDraw = () => {
    if (animationFrameRef.current !== null) {
      return;
    }

    animationFrameRef.current = requestAnimationFrame(() => {
      animationFrameRef.current = null;
      drawFrameRef.current();
    });
  };

  drawFrameRef.current = drawFrame;
  scheduleDrawRef.current = scheduleDraw;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const updateSize = (nextWidth?: number, nextHeight?: number) => {
      const rect = canvas.getBoundingClientRect();
      const measuredWidth = nextWidth ?? rect.width;
      const measuredHeight = nextHeight ?? rect.height;
      const width = Math.max(1, Math.round(measuredWidth));
      const height = Math.max(1, Math.round(measuredHeight));
      if (width === sizeRef.current.width && height === sizeRef.current.height) {
        return;
      }

      const devicePixelRatio = window.devicePixelRatio || 1;
      canvas.width = width * devicePixelRatio;
      canvas.height = height * devicePixelRatio;
      sizeRef.current = { width, height };
      const context = canvas.getContext("2d");
      context?.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      scheduleDrawRef.current();
    };

    updateSize();

    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver((entries) => {
        const entry = entries[0];
        updateSize(entry?.contentRect.width, entry?.contentRect.height);
      });
      observer.observe(canvas);
    } else {
      const handleWindowResize = () => updateSize();
      window.addEventListener("resize", handleWindowResize);

      return () => {
        window.removeEventListener("resize", handleWindowResize);
      };
    }

    return () => {
      observer?.disconnect();
    };
  }, []);

  useEffect(() => {
    scheduleDrawRef.current();

    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [frame, activeClasses, tracks]);

  return (
    <canvas
      ref={canvasRef}
      aria-label="Telemetry overlay"
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
}

function formatAge(ageMs: number): string {
  if (ageMs < 1_000) {
    return `${Math.max(0, Math.round(ageMs))}ms ago`;
  }

  return `${(ageMs / 1_000).toFixed(1)}s ago`;
}

function getCoordinate(
  bbox: Record<string, number>,
  axis: "x1" | "y1" | "x2" | "y2",
): number {
  const aliases: Record<typeof axis, string[]> = {
    x1: ["x1", "left", "x"],
    y1: ["y1", "top", "y"],
    x2: ["x2", "right", "w"],
    y2: ["y2", "bottom", "h"],
  };

  for (const key of aliases[axis]) {
    const value = bbox[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      if (axis === "x2" && key === "w") {
        return getCoordinate(bbox, "x1") + value;
      }
      if (axis === "y2" && key === "h") {
        return getCoordinate(bbox, "y1") + value;
      }
      return value;
    }
  }

  return 0;
}
