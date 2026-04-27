import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { productBrand } from "@/brand/product";
import { BoundaryAuthoringCanvas } from "@/components/cameras/BoundaryAuthoringCanvas";
import {
  type FrameSize,
  denormalizePointList,
  normalizePointList,
} from "@/components/cameras/boundary-geometry";

type Point = [number, number];

function pointLabel(point: Point) {
  return `${point[0]}, ${point[1]}`;
}

export function HomographyEditor({
  src,
  dst,
  refDistanceM,
  onChange,
  sourceFrameSize,
  sourcePreviewSrc,
  destinationFrameSize,
}: {
  src: Point[];
  dst: Point[];
  refDistanceM: number;
  onChange: (value: { src: Point[]; dst: Point[]; refDistanceM: number }) => void;
  sourceFrameSize?: FrameSize;
  sourcePreviewSrc?: string | null;
  destinationFrameSize?: FrameSize;
}) {
  const brandName = productBrand.name;
  const resolvedSourceFrameSize =
    sourceFrameSize ?? derivePlaneSize(src, { width: 100, height: 100 });
  const resolvedDestinationFrameSize =
    destinationFrameSize ?? derivePlaneSize(dst, { width: 100, height: 100 });

  function updateRefDistance(value: string) {
    const parsed = Number(value);
    onChange({
      src,
      dst,
      refDistanceM: Number.isFinite(parsed) ? parsed : 0,
    });
  }

  function updateSourcePoints(pointsNormalized: readonly (readonly [number, number])[]) {
    onChange({
      src: denormalizePointList(pointsNormalized, resolvedSourceFrameSize),
      dst,
      refDistanceM,
    });
  }

  function updateDestinationPoints(pointsNormalized: readonly (readonly [number, number])[]) {
    onChange({
      src,
      dst: denormalizePointList(pointsNormalized, resolvedDestinationFrameSize),
      refDistanceM,
    });
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-[1.5rem] border border-[#243853] bg-[#09121c] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
                Analytics still
              </p>
              <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">Source points</h3>
            </div>
            <Button
              className="px-3 py-2"
              disabled={src.length >= 4}
              onClick={() =>
                onChange({
                  src: [...src, [src.length * 10, src.length * 10]],
                  dst,
                  refDistanceM,
                })
              }
            >
              Add source point
            </Button>
          </div>
          <div className="mt-4">
            <BoundaryAuthoringCanvas
              ariaLabel="Source points canvas"
              backgroundContent={
                <p className="max-w-sm text-sm text-[#9eb2cf]">
                  Place four source points directly on the captured analytics still. If the
                  still is temporarily unavailable, keep using the authoring plane and refresh
                  the still once the camera source responds.
                </p>
              }
              frameSize={resolvedSourceFrameSize}
              helperText="This captured analytics still anchors the source plane for calibration and count-boundary authoring across the rest of setup."
              maxPoints={4}
              mode="points"
              pointLabelPrefix="Source"
              previewSrc={sourcePreviewSrc}
              value={normalizePointList(src, resolvedSourceFrameSize)}
              variant="source"
              onChange={updateSourcePoints}
            />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {src.length === 0 ? (
              <p className="text-sm text-[#8ea4c7]">Add four source points from the camera frame.</p>
            ) : (
              src.map((point, index) => (
                <span
                  key={`src-${index}-${pointLabel(point)}`}
                  className="rounded-full border border-[#284066] bg-[#101a2a] px-3 py-1.5 text-xs font-medium text-[#d8e2f2]"
                >
                  S{index + 1}: {pointLabel(point)}
                </span>
              ))
            )}
          </div>
        </section>

        <section className="rounded-[1.5rem] border border-[#243853] bg-[#09121c] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
                World plane
              </p>
              <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">
                Destination points
              </h3>
            </div>
            <Button
              className="px-3 py-2"
              disabled={dst.length >= 4}
              onClick={() =>
                onChange({
                  src,
                  dst: [...dst, [dst.length * 5, dst.length * 5]],
                  refDistanceM,
                })
              }
            >
              Add destination point
            </Button>
          </div>
          <div className="mt-4">
            <BoundaryAuthoringCanvas
              ariaLabel="Destination points canvas"
              backgroundContent={
                <p className="max-w-sm text-sm text-[#cbbaf4]">
                  Shape a simple top-down reference plane here so motion can map into a
                  real-world calibration.
                </p>
              }
              frameSize={resolvedDestinationFrameSize}
              helperText="Destination points can use the same interaction model even though this plane is abstract instead of a camera frame."
              maxPoints={4}
              mode="points"
              pointLabelPrefix="Destination"
              value={normalizePointList(dst, resolvedDestinationFrameSize)}
              variant="destination"
              onChange={updateDestinationPoints}
            />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {dst.length === 0 ? (
              <p className="text-sm text-[#8ea4c7]">
                Add four destination points that map to the real-world plane.
              </p>
            ) : (
              dst.map((point, index) => (
                <span
                  key={`dst-${index}-${pointLabel(point)}`}
                  className="rounded-full border border-[#3e3566] bg-[#131426] px-3 py-1.5 text-xs font-medium text-[#e7e2ff]"
                >
                  D{index + 1}: {pointLabel(point)}
                </span>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-4 rounded-[1.5rem] border border-white/8 bg-[#0b1320] p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <label className="grid gap-2 text-sm text-[#d8e2f2]">
          <span>Reference distance (m)</span>
          <Input
            aria-label="Reference distance (m)"
            min={0}
            step="0.1"
            type="number"
            value={refDistanceM}
            onChange={(event) => updateRefDistance(event.target.value)}
          />
        </label>
        <div className="flex gap-3">
          <Button
            className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
            onClick={() => onChange({ src: [], dst, refDistanceM })}
          >
            Reset source
          </Button>
          <Button
            className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
            onClick={() => onChange({ src, dst: [], refDistanceM })}
          >
            Reset destination
          </Button>
        </div>
      </div>

      <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
        Source points: {src.length} / 4. Destination points: {dst.length} / 4. {brandName}
        uses this calibration to translate image motion into real-world distance and
        direction later in the pipeline.
      </p>
    </div>
  );
}

function derivePlaneSize(points: Point[], fallback: FrameSize): FrameSize {
  if (points.length === 0) {
    return fallback;
  }

  const maxX = Math.max(...points.map((point) => point[0]), 0);
  const maxY = Math.max(...points.map((point) => point[1]), 0);

  return {
    width: Math.max(fallback.width, roundPlaneEdge(maxX)),
    height: Math.max(fallback.height, roundPlaneEdge(maxY)),
  };
}

function roundPlaneEdge(value: number) {
  const padded = Math.max(100, value + 20);
  return Math.ceil(padded / 10) * 10;
}
