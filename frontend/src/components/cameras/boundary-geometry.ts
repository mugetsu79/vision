export type FrameSize = {
  width: number;
  height: number;
};

export type NormalizedPoint = readonly [number, number];
export type AbsolutePoint = readonly [number, number];

type RectLike = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const NORMALIZED_PRECISION = 6;

function roundNormalized(value: number) {
  return Number(value.toFixed(NORMALIZED_PRECISION));
}

export function clampNormalizedValue(value: number) {
  return Math.max(0, Math.min(1, value));
}

export function clampNormalizedPoint(point: NormalizedPoint): NormalizedPoint {
  return [
    roundNormalized(clampNormalizedValue(point[0])),
    roundNormalized(clampNormalizedValue(point[1])),
  ];
}

export function normalizeAbsolutePoint(
  point: AbsolutePoint,
  frameSize: FrameSize,
): NormalizedPoint {
  return clampNormalizedPoint([
    frameSize.width > 0 ? point[0] / frameSize.width : 0,
    frameSize.height > 0 ? point[1] / frameSize.height : 0,
  ]);
}

export function denormalizePoint(
  point: NormalizedPoint,
  frameSize: FrameSize,
): [number, number] {
  return [
    Math.round(clampNormalizedValue(point[0]) * frameSize.width),
    Math.round(clampNormalizedValue(point[1]) * frameSize.height),
  ];
}

export function normalizePointList(
  points: readonly AbsolutePoint[],
  frameSize: FrameSize,
): NormalizedPoint[] {
  return points.map((point) => normalizeAbsolutePoint(point, frameSize));
}

export function denormalizePointList(
  points: readonly NormalizedPoint[],
  frameSize: FrameSize,
): [number, number][] {
  return points.map((point) => denormalizePoint(point, frameSize));
}

export function normalizePointFromRect(
  clientPoint: { x: number; y: number },
  rect: RectLike,
): NormalizedPoint {
  const width = Math.max(rect.width, 1);
  const height = Math.max(rect.height, 1);
  return clampNormalizedPoint([
    (clientPoint.x - rect.left) / width,
    (clientPoint.y - rect.top) / height,
  ]);
}

export function toSvgPoint(point: NormalizedPoint, frameSize: FrameSize) {
  return {
    x: clampNormalizedValue(point[0]) * frameSize.width,
    y: clampNormalizedValue(point[1]) * frameSize.height,
  };
}

export function toSvgPointString(
  points: readonly NormalizedPoint[],
  frameSize: FrameSize,
) {
  return points
    .map((point) => {
      const svgPoint = toSvgPoint(point, frameSize);
      return `${svgPoint.x},${svgPoint.y}`;
    })
    .join(" ");
}
