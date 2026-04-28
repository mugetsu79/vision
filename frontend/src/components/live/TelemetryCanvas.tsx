import { useEffect, useRef } from "react";

import { filterTracks } from "@/lib/live";
import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];

export function TelemetryCanvas({
  frame,
  activeClasses,
}: {
  frame: TelemetryFrame | null | undefined;
  activeClasses: string[] | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sizeRef = useRef({ width: 0, height: 0 });
  const frameRef = useRef<TelemetryFrame | null | undefined>(frame);
  const activeClassesRef = useRef<string[] | null>(activeClasses);
  const animationFrameRef = useRef<number | null>(null);
  const drawFrameRef = useRef<() => void>(() => undefined);
  const scheduleDrawRef = useRef<() => void>(() => undefined);

  frameRef.current = frame;
  activeClassesRef.current = activeClasses;

  const drawFrame = () => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    const { width, height } = sizeRef.current;
    context.clearRect(0, 0, width, height);

    const visibleTracks = filterTracks(frameRef.current, activeClassesRef.current);
    if (visibleTracks.length === 0) {
      return;
    }

    const sourceWidth = Math.max(
      ...visibleTracks.map((track) => getCoordinate(track.bbox, "x2")),
      1,
    );
    const sourceHeight = Math.max(
      ...visibleTracks.map((track) => getCoordinate(track.bbox, "y2")),
      1,
    );
    const scaleX = width / sourceWidth;
    const scaleY = height / sourceHeight;

    context.lineWidth = 2;
    context.strokeStyle = "#6cb0ff";
    context.fillStyle = "#eef5ff";
    context.font = "12px ui-sans-serif, system-ui, sans-serif";

    for (const track of visibleTracks) {
      const x1 = getCoordinate(track.bbox, "x1") * scaleX;
      const y1 = getCoordinate(track.bbox, "y1") * scaleY;
      const x2 = getCoordinate(track.bbox, "x2") * scaleX;
      const y2 = getCoordinate(track.bbox, "y2") * scaleY;
      const label = [
        `${track.class_name} #${track.track_id}`,
        track.speed_kph ? `${Math.round(track.speed_kph)} km/h` : null,
      ]
        .filter(Boolean)
        .join(" ");

      context.strokeRect(x1, y1, Math.max(4, x2 - x1), Math.max(4, y2 - y1));
      context.fillText(label, x1 + 4, Math.max(14, y1 - 6));
    }
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
  }, [frame, activeClasses]);

  return (
    <canvas
      ref={canvasRef}
      aria-label="Telemetry overlay"
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
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
