import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { productBrand } from "@/brand/product";
import { BoundaryAuthoringCanvas } from "@/components/cameras/BoundaryAuthoringCanvas";
import {
  SCENE_FIELD_GUIDANCE,
  SCENE_STEP_GUIDANCE,
} from "@/components/cameras/scene-guidance";
import { CalibrationFlowIllustration } from "@/components/guidance/CalibrationFlowIllustration";
import { CalibrationScaleExample } from "@/components/guidance/CalibrationScaleExample";
import { FieldHelp } from "@/components/guidance/FieldHelp";
import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
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
  onChange: (value: {
    src: Point[];
    dst: Point[];
    refDistanceM: number;
  }) => void;
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

  function updateSourcePoints(
    pointsNormalized: readonly (readonly [number, number])[],
  ) {
    onChange({
      src: denormalizePointList(pointsNormalized, resolvedSourceFrameSize),
      dst,
      refDistanceM,
    });
  }

  function updateDestinationPoints(
    pointsNormalized: readonly (readonly [number, number])[],
  ) {
    onChange({
      src,
      dst: denormalizeDestinationPointList(
        pointsNormalized,
        resolvedDestinationFrameSize,
      ),
      refDistanceM,
    });
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.15rem] border border-white/8 bg-[#0b1320] px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
            Calibration map
          </p>
          <h3 className="mt-1 text-sm font-semibold text-[#f4f8ff]">
            Match camera marks to a top-down floor plane
          </h3>
        </div>
        <GuidanceDisclosure
          id="homography-calibration-help"
          label="calibration mapping"
          guidance={SCENE_STEP_GUIDANCE.Calibration}
        >
          <CalibrationFlowIllustration />
        </GuidanceDisclosure>
      </div>
      <section
        aria-labelledby="measured-distance-heading"
        className="grid gap-4 rounded-[1.15rem] border border-[#284066] bg-[#0c1522] p-4 md:grid-cols-[minmax(0,1fr)_minmax(16rem,22rem)] md:items-start"
      >
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
            Measured distance
          </p>
          <h3
            id="measured-distance-heading"
            className="mt-1 text-sm font-semibold text-[#f4f8ff]"
          >
            Measure D1 to D2 on the same floor plane
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#9eb2cf]">
            Use one measured floor-plane span: S1/S2 in the camera still,
            D1/D2 in the drawn world plane.
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium text-[#c7d5eb]">
            <span className="rounded-full border border-white/8 bg-black/20 px-3 py-1.5">
              Scale segment D1-D2
            </span>
            <span className="rounded-full border border-white/8 bg-black/20 px-3 py-1.5">
              Same physical marks
            </span>
            <span className="rounded-full border border-white/8 bg-black/20 px-3 py-1.5">
              Meters on the moving floor
            </span>
          </div>
        </div>
        <div className="grid gap-2 text-sm text-[#d8e2f2]">
          <span className="inline-flex items-center gap-2">
            <label htmlFor="measured-distance-m">Measured distance (m)</label>
            <FieldHelp
              id="measured-distance-help"
              guidance={SCENE_FIELD_GUIDANCE.referenceDistance}
            >
              <CalibrationScaleExample compact />
            </FieldHelp>
          </span>
          <Input
            id="measured-distance-m"
            aria-label="Measured distance (m)"
            min={0}
            step="0.1"
            type="number"
            value={refDistanceM}
            onChange={(event) => updateRefDistance(event.target.value)}
          />
          <p className="text-xs leading-5 text-[#8ea4c7]">
            Scale segment: D1-D2. If your known length is another side, make
            that side points 1 and 2 before saving.
          </p>
        </div>
      </section>
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-[1.5rem] border border-[#243853] bg-[#09121c] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
                Analytics still
              </p>
              <div className="mt-2 flex items-center gap-2">
                <h3 className="text-lg font-semibold text-[#f4f8ff]">
                  Source points
                </h3>
                <FieldHelp
                  id="source-points-help"
                  guidance={SCENE_FIELD_GUIDANCE.sourcePoints}
                />
              </div>
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
                  Click four fixed floor marks in the camera image. If this is a
                  new camera, use this temporary plane now and refresh the still
                  after saving.
                </p>
              }
              frameSize={resolvedSourceFrameSize}
              helperText="These camera image points should sit on the same flat floor plane where people or vehicles move."
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
              <p className="text-sm text-[#8ea4c7]">
                Add four source points from the camera frame.
              </p>
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
              <div className="mt-2 flex items-center gap-2">
                <h3 className="text-lg font-semibold text-[#f4f8ff]">
                  Destination points
                </h3>
                <FieldHelp
                  id="destination-points-help"
                  guidance={SCENE_FIELD_GUIDANCE.destinationPoints}
                />
              </div>
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
                  Draw the same four marks from above. This is a drawn world
                  plane, not a camera still. Keep the order the same as the
                  camera image points.
                </p>
              }
              frameSize={resolvedDestinationFrameSize}
              helperText="The top-down drawing is not captured from the camera; it only needs to preserve the same mark order and shape."
              maxPoints={4}
              mode="points"
              pointLabelPrefix="Destination"
              value={normalizeDestinationPointList(
                dst,
                resolvedDestinationFrameSize,
              )}
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

      <div className="flex flex-wrap gap-3 rounded-[1.15rem] border border-white/8 bg-[#0b1320] p-4 sm:justify-end">
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
        <Button
          className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
          onClick={() => onChange({ src: [], dst: [], refDistanceM: 0 })}
        >
          Clear calibration
        </Button>
      </div>

      <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
        Camera image points: {src.length} / 4. Top-down points: {dst.length} /
        4. {brandName}
        saves calibration only when all four pairs and a measured distance are
        set.
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

function normalizeDestinationPointList(
  points: readonly Point[],
  frameSize: FrameSize,
) {
  return normalizePointList(
    points.map(([x, y]) => [x, frameSize.height - y]),
    frameSize,
  );
}

function denormalizeDestinationPointList(
  points: readonly (readonly [number, number])[],
  frameSize: FrameSize,
) {
  return denormalizePointList(points, frameSize).map(
    ([x, y]): Point => [x, frameSize.height - y],
  );
}
