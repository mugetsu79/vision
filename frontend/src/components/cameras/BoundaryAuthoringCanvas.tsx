import { type ReactNode, useEffect, useMemo, useRef } from "react";

import {
  type FrameSize,
  type NormalizedPoint,
  normalizePointFromRect,
  toSvgPoint,
  toSvgPointString,
} from "@/components/cameras/boundary-geometry";

type BoundaryAuthoringMode = "line" | "points" | "polygon";
type BoundaryCanvasVariant = "boundary" | "destination" | "source";

const DEFAULT_MAX_POINTS: Partial<Record<BoundaryAuthoringMode, number>> = {
  line: 2,
};

const VARIANT_STYLES: Record<
  BoundaryCanvasVariant,
  {
    handleClassName: string;
    helperClassName: string;
    shapeClassName: string;
    surfaceClassName: string;
  }
> = {
  source: {
    handleClassName:
      "border-[#6cb0ff] bg-[#09192c] text-[#eef6ff] shadow-[0_0_0_4px_rgba(38,116,255,0.18)]",
    helperClassName: "border-[#284066] bg-[#0c1522]/90 text-[#9eb2cf]",
    shapeClassName: "stroke-[#6cb0ff] fill-[#6cb0ff]/12",
    surfaceClassName:
      "border-[#37537e] bg-[radial-gradient(circle_at_top,_rgba(55,124,255,0.18),_transparent_35%),linear-gradient(180deg,#0d1725_0%,#08101a_100%)]",
  },
  destination: {
    handleClassName:
      "border-[#b28fff] bg-[#161428] text-[#f3eeff] shadow-[0_0_0_4px_rgba(146,104,255,0.18)]",
    helperClassName: "border-[#3e3566] bg-[#141326]/90 text-[#d6cbff]",
    shapeClassName: "stroke-[#b28fff] fill-[#b28fff]/12",
    surfaceClassName:
      "border-[#553a79] bg-[radial-gradient(circle_at_top,_rgba(128,92,255,0.2),_transparent_35%),linear-gradient(180deg,#111426_0%,#090d19_100%)]",
  },
  boundary: {
    handleClassName:
      "border-[#6fe0c5] bg-[#0d1f1a] text-[#effff9] shadow-[0_0_0_4px_rgba(73,197,164,0.16)]",
    helperClassName: "border-[#24594f] bg-[#0d1717]/90 text-[#bcefe3]",
    shapeClassName: "stroke-[#6fe0c5] fill-[#6fe0c5]/10",
    surfaceClassName:
      "border-[#24594f] bg-[radial-gradient(circle_at_top,_rgba(50,168,142,0.18),_transparent_35%),linear-gradient(180deg,#0d1717_0%,#081113_100%)]",
  },
};

export function BoundaryAuthoringCanvas({
  ariaLabel,
  backgroundContent,
  frameSize,
  helperText,
  maxPoints,
  mode,
  onChange,
  pointLabelPrefix = "Point",
  previewSrc,
  value,
  variant = "boundary",
}: {
  ariaLabel: string;
  backgroundContent?: ReactNode;
  frameSize: FrameSize;
  helperText?: string;
  maxPoints?: number;
  mode: BoundaryAuthoringMode;
  onChange: (value: NormalizedPoint[]) => void;
  pointLabelPrefix?: string;
  previewSrc?: string | null;
  value: readonly NormalizedPoint[];
  variant?: BoundaryCanvasVariant;
}) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const valueRef = useRef(value);
  const draggingIndexRef = useRef<number | null>(null);
  const dragCleanupRef = useRef<(() => void) | null>(null);

  valueRef.current = value;

  const styles = VARIANT_STYLES[variant];
  const pointLimit = maxPoints ?? DEFAULT_MAX_POINTS[mode] ?? Number.POSITIVE_INFINITY;

  const polygonPreview = useMemo(() => {
    if (mode !== "polygon" || value.length < 3) {
      return null;
    }
    return toSvgPointString(value, frameSize);
  }, [frameSize, mode, value]);

  const openPointPath = useMemo(() => {
    if (mode !== "points" || value.length < 2) {
      return null;
    }
    return toSvgPointString(value, frameSize);
  }, [frameSize, mode, value]);

  function pointFromViewport(clientX: number, clientY: number): NormalizedPoint | null {
    const rect = rootRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    return normalizePointFromRect({ x: clientX, y: clientY }, rect);
  }

  function updatePoint(index: number, point: NormalizedPoint) {
    const nextPoints = [...valueRef.current];
    nextPoints[index] = point;
    valueRef.current = nextPoints;
    onChange(nextPoints);
  }

  function stopDragging() {
    draggingIndexRef.current = null;
    dragCleanupRef.current?.();
    dragCleanupRef.current = null;
  }

  function startDragging(index: number, interaction: "mouse" | "pointer") {
    stopDragging();
    draggingIndexRef.current = index;

    const moveEventName = interaction === "mouse" ? "mousemove" : "pointermove";
    const upEventName = interaction === "mouse" ? "mouseup" : "pointerup";

    const handleMove = (event: MouseEvent | PointerEvent) => {
      const point = pointFromViewport(event.clientX, event.clientY);
      if (!point || draggingIndexRef.current === null) {
        return;
      }
      updatePoint(draggingIndexRef.current, point);
    };

    const handleUp = () => {
      stopDragging();
    };

    window.addEventListener(moveEventName, handleMove);
    window.addEventListener(upEventName, handleUp);

    dragCleanupRef.current = () => {
      window.removeEventListener(moveEventName, handleMove);
      window.removeEventListener(upEventName, handleUp);
    };
  }

  function handleCanvasClick(event: React.MouseEvent<HTMLDivElement>) {
    if (draggingIndexRef.current !== null || valueRef.current.length >= pointLimit) {
      return;
    }
    const point = pointFromViewport(event.clientX, event.clientY);
    if (!point) {
      return;
    }
    const nextPoints = [...valueRef.current, point];
    valueRef.current = nextPoints;
    onChange(nextPoints);
  }

  useEffect(
    () => () => {
      stopDragging();
    },
    [],
  );

  return (
    <div className="space-y-3">
      <div
        ref={rootRef}
        aria-label={ariaLabel}
        className={`group relative isolate overflow-hidden rounded-[1.3rem] border ${styles.surfaceClassName} shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]`}
        role="application"
        style={{ aspectRatio: `${frameSize.width} / ${frameSize.height}` }}
        onClick={handleCanvasClick}
      >
        {previewSrc ? (
          <img
            alt=""
            aria-hidden="true"
            className="absolute inset-0 h-full w-full object-cover opacity-90"
            src={previewSrc}
          />
        ) : null}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
            backgroundPosition: "center",
            backgroundSize: "12% 12%",
          }}
        />
        {backgroundContent ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center px-6 text-center">
            {backgroundContent}
          </div>
        ) : null}
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 h-full w-full"
          preserveAspectRatio="none"
          viewBox={`0 0 ${frameSize.width} ${frameSize.height}`}
        >
          {mode === "line" && value.length === 2 ? (
            <line
              className={styles.shapeClassName}
              strokeLinecap="round"
              strokeWidth={4}
              x1={toSvgPoint(value[0], frameSize).x}
              x2={toSvgPoint(value[1], frameSize).x}
              y1={toSvgPoint(value[0], frameSize).y}
              y2={toSvgPoint(value[1], frameSize).y}
            />
          ) : null}
          {polygonPreview ? (
            <polygon
              className={styles.shapeClassName}
              points={polygonPreview}
              strokeLinejoin="round"
              strokeWidth={4}
            />
          ) : null}
          {openPointPath ? (
            <polyline
              className={styles.shapeClassName}
              fill="none"
              points={openPointPath}
              strokeDasharray="10 10"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
            />
          ) : null}
        </svg>
        {value.map((point, index) => (
          <button
            key={`${pointLabelPrefix}-${index}-${point[0]}-${point[1]}`}
            aria-label={`${pointLabelPrefix} point ${index + 1}`}
            className={`absolute z-10 flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border text-[11px] font-semibold transition-transform duration-150 hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 ${styles.handleClassName}`}
            style={{
              left: `${point[0] * 100}%`,
              top: `${point[1] * 100}%`,
            }}
            type="button"
            onClick={(event) => {
              event.stopPropagation();
            }}
            onPointerDown={(event) => {
              event.preventDefault();
              event.stopPropagation();
              if (event.button !== 0) {
                return;
              }
              startDragging(index, "pointer");
            }}
            onMouseDown={(event) => {
              event.preventDefault();
              event.stopPropagation();
              if (event.button !== 0) {
                return;
              }
              startDragging(index, "mouse");
            }}
          >
            {index + 1}
          </button>
        ))}
        <div className="pointer-events-none absolute left-3 top-3 rounded-full border border-white/10 bg-[#08111a]/85 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d9e4f7]">
          {frameSize.width} × {frameSize.height}
        </div>
      </div>
      {helperText ? (
        <p className={`rounded-[1rem] border px-3 py-2 text-xs ${styles.helperClassName}`}>
          {helperText}
        </p>
      ) : null}
    </div>
  );
}
