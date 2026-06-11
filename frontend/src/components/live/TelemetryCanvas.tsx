import { useEffect, useRef } from "react";

import { filterTracks } from "@/lib/live";
import type { components } from "@/lib/api.generated";
import {
  colorForClass,
  shouldDrawBrowserTelemetryOverlay,
  signalAgeMsForTelemetryTrack,
  signalStateForTelemetryTrack,
  trackKey,
  type SignalTrack,
} from "@/lib/live-signal-stability";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];
type SourceSize = { width: number; height: number };
type ResolvedSourceSize = SourceSize & { explicit: boolean };
type CoordinateTransform = {
  scaleX: number;
  scaleY: number;
  offsetX: number;
  offsetY: number;
};
type TrailPoint = {
  x: number;
  y: number;
};

const MAX_TRAIL_POINTS = 18;
const RESERVED_TOP_STATUS_BAND = 42;

export function TelemetryCanvas({
  frame,
  activeClasses,
  tracks,
  sourceSize,
  disabled = false,
}: {
  frame: TelemetryFrame | null | undefined;
  activeClasses: string[] | null;
  tracks?: SignalTrack[];
  sourceSize?: SourceSize | null;
  disabled?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sizeRef = useRef({ width: 0, height: 0 });
  const frameRef = useRef<TelemetryFrame | null | undefined>(frame);
  const activeClassesRef = useRef<string[] | null>(activeClasses);
  const tracksRef = useRef<SignalTrack[] | undefined>(tracks);
  const sourceSizeRef = useRef<SourceSize | null | undefined>(sourceSize);
  const disabledRef = useRef(disabled);
  const trailPointsRef = useRef(new Map<string, TrailPoint[]>());
  const skippedInitialPropDrawRef = useRef(false);
  const drawFrameRef = useRef<() => void>(() => undefined);

  frameRef.current = frame;
  activeClassesRef.current = activeClasses;
  tracksRef.current = tracks;
  sourceSizeRef.current = sourceSize;
  disabledRef.current = disabled;

  const drawFrame = () => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    const { width, height } = sizeRef.current;
    context.clearRect(0, 0, width, height);

    if (
      disabledRef.current ||
      !shouldDrawBrowserTelemetryOverlay(frameRef.current?.stream_mode)
    ) {
      trailPointsRef.current.clear();
      return;
    }

    const visibleSignals = resolveVisibleSignals(
      tracksRef.current,
      frameRef.current,
      activeClassesRef.current,
    );

    if (visibleSignals.length === 0) {
      trailPointsRef.current.clear();
      return;
    }

    const source = resolveSourceSize(
      visibleSignals,
      frameRef.current,
      sourceSizeRef.current,
    );
    const transform = resolveCoordinateTransform(width, height, source);
    updateSignalTrails(trailPointsRef.current, visibleSignals);

    context.lineWidth = 2;
    context.font = "12px ui-sans-serif, system-ui, sans-serif";

    for (const signal of visibleSignals) {
      drawSignalTrail(context, trailPointsRef.current.get(signal.key) ?? [], signal, transform);
    }

    context.lineWidth = 2;
    for (const signal of visibleSignals) {
      const { track } = signal;
      const x1 = projectCoordinate(
        getCoordinate(track.bbox, "x1"),
        transform.scaleX,
        transform.offsetX,
      );
      const y1 = projectCoordinate(
        getCoordinate(track.bbox, "y1"),
        transform.scaleY,
        transform.offsetY,
      );
      const x2 = projectCoordinate(
        getCoordinate(track.bbox, "x2"),
        transform.scaleX,
        transform.offsetX,
      );
      const y2 = projectCoordinate(
        getCoordinate(track.bbox, "y2"),
        transform.scaleY,
        transform.offsetY,
      );
      const label = [
        track.class_name,
        signal.state === "held" ? "last seen" : null,
        typeof track.speed_kph === "number" ? `${Math.round(track.speed_kph)} km/h` : null,
      ]
        .filter(Boolean)
        .join(" ");
      const labelWidth = context.measureText(label).width;
      const labelX = Math.max(4, Math.min(x1 + 4, width - labelWidth - 4));
      const preferredLabelY = y1 - 6;
      const labelY =
        preferredLabelY < RESERVED_TOP_STATUS_BAND
          ? Math.min(height - 4, y2 + 14)
          : Math.min(height - 4, Math.max(14, preferredLabelY));

      context.globalAlpha = signal.state === "held" ? 0.55 : 1;
      context.setLineDash?.(signal.state === "held" ? [6, 5] : []);
      context.strokeStyle = signal.color.stroke;
      context.strokeRect(x1, y1, Math.max(4, x2 - x1), Math.max(4, y2 - y1));
      drawLabelBacking(context, labelX - 4, labelY - 12, labelWidth + 8, 16);
      context.fillStyle = signal.color.text;
      context.fillText(label, labelX, labelY);
    }

    context.globalAlpha = 1;
    context.setLineDash?.([]);
  };

  drawFrameRef.current = drawFrame;

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
      drawFrameRef.current();
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
    if (!skippedInitialPropDrawRef.current) {
      skippedInitialPropDrawRef.current = true;
      return;
    }
    drawFrameRef.current();
  }, [frame, activeClasses, tracks, sourceSize, disabled]);

  return (
    <canvas
      ref={canvasRef}
      aria-label="Telemetry overlay"
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
}

function drawLabelBacking(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
) {
  if (!("roundRect" in context)) {
    return;
  }

  context.save();
  context.globalAlpha = 0.72;
  context.fillStyle = "rgba(3, 8, 14, 0.86)";
  context.beginPath();
  context.roundRect(x, y, width, height, 5);
  context.fill();
  context.restore();
}

function updateSignalTrails(
  trails: Map<string, TrailPoint[]>,
  visibleSignals: SignalTrack[],
) {
  const visibleKeys = new Set(visibleSignals.map((signal) => signal.key));

  for (const key of trails.keys()) {
    if (!visibleKeys.has(key)) {
      trails.delete(key);
    }
  }

  for (const signal of visibleSignals) {
    const center = sourceCenterForTrack(signal.track);
    const existing = trails.get(signal.key) ?? [];
    const previous = existing.at(-1);
    const hasMoved =
      !previous ||
      Math.abs(previous.x - center.x) > 0.5 ||
      Math.abs(previous.y - center.y) > 0.5;
    const next = hasMoved ? [...existing, center] : existing;
    trails.set(signal.key, next.slice(-MAX_TRAIL_POINTS));
  }
}

function drawSignalTrail(
  context: CanvasRenderingContext2D,
  trail: TrailPoint[],
  signal: SignalTrack,
  transform: CoordinateTransform,
) {
  if (trail.length < 2) {
    return;
  }

  const projected = trail.map((point) => ({
    x: projectCoordinate(point.x, transform.scaleX, transform.offsetX),
    y: projectCoordinate(point.y, transform.scaleY, transform.offsetY),
  }));

  context.beginPath();
  context.setLineDash?.(signal.state === "held" ? [3, 5] : []);
  context.globalAlpha = signal.state === "held" ? 0.22 : 0.34;
  context.lineWidth = 2.4;
  context.strokeStyle = signal.color.stroke;
  context.moveTo(projected[0].x, projected[0].y);
  for (const point of projected.slice(1)) {
    context.lineTo(point.x, point.y);
  }
  context.stroke();
}

function sourceCenterForTrack(track: TelemetryFrame["tracks"][number]): TrailPoint {
  return {
    x: (getCoordinate(track.bbox, "x1") + getCoordinate(track.bbox, "x2")) / 2,
    y: (getCoordinate(track.bbox, "y1") + getCoordinate(track.bbox, "y2")) / 2,
  };
}

function resolveVisibleSignals(
  tracks: SignalTrack[] | undefined,
  frame: TelemetryFrame | null | undefined,
  activeClasses: string[] | null,
): SignalTrack[] {
  if (tracks !== undefined) {
    return tracks;
  }

  if (!shouldDrawBrowserTelemetryOverlay(frame?.stream_mode)) {
    return [];
  }

  return filterTracks(frame, activeClasses).map((track): SignalTrack => ({
    key: trackKey(track),
    track,
    color: colorForClass(track.class_name),
    state: signalStateForTelemetryTrack(track),
    firstSeenMs: 0,
    lastSeenMs: 0,
    ageMs: signalAgeMsForTelemetryTrack(track),
  }));
}

function resolveSourceSize(
  visibleSignals: SignalTrack[],
  frame: TelemetryFrame | null | undefined,
  sourceSize: SourceSize | null | undefined,
): ResolvedSourceSize {
  const explicitSourceSize = readFrameSourceSize(frame) ?? normalizeSourceSize(sourceSize);
  if (explicitSourceSize) {
    return {
      width: explicitSourceSize.width,
      height: explicitSourceSize.height,
      explicit: true,
    };
  }

  return {
    width: Math.max(
      ...visibleSignals.map((signal) => getCoordinate(signal.track.bbox, "x2")),
      1,
    ),
    height: Math.max(
      ...visibleSignals.map((signal) => getCoordinate(signal.track.bbox, "y2")),
      1,
    ),
    explicit: false,
  };
}

function readFrameSourceSize(frame: TelemetryFrame | null | undefined): SourceSize | null {
  return normalizeSourceSize(frame?.source_size);
}

function normalizeSourceSize(source: unknown): SourceSize | null {
  if (!source || typeof source !== "object") {
    return null;
  }

  const { width, height } = source as {
    width?: unknown;
    height?: unknown;
  };
  if (
    typeof width === "number" &&
    Number.isFinite(width) &&
    width > 0 &&
    typeof height === "number" &&
    Number.isFinite(height) &&
    height > 0
  ) {
    return { width, height };
  }

  return null;
}

function resolveCoordinateTransform(
  canvasWidth: number,
  canvasHeight: number,
  source: ResolvedSourceSize,
): CoordinateTransform {
  if (!source.explicit) {
    return {
      scaleX: canvasWidth / source.width,
      scaleY: canvasHeight / source.height,
      offsetX: 0,
      offsetY: 0,
    };
  }

  const scale = Math.min(canvasWidth / source.width, canvasHeight / source.height);
  const renderedWidth = source.width * scale;
  const renderedHeight = source.height * scale;

  return {
    scaleX: scale,
    scaleY: scale,
    offsetX: (canvasWidth - renderedWidth) / 2,
    offsetY: (canvasHeight - renderedHeight) / 2,
  };
}

function projectCoordinate(value: number, scale: number, offset: number): number {
  return value * scale + offset;
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
