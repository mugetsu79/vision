import { useId } from "react";

type CalibrationFlowIllustrationProps = {
  mode?: "source-destination" | "boundaries" | "regions";
  animated?: boolean;
};

type IllustrationCopy = {
  title: string;
  description: string;
  caption: string;
};

const SVG_FONT_FAMILY =
  'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

const sourcePoints = [
  { label: "S1", x: 52, y: 74 },
  { label: "S2", x: 118, y: 58 },
  { label: "S3", x: 158, y: 122 },
  { label: "S4", x: 36, y: 144 },
];

const destinationPoints = [
  { label: "D1", x: 260, y: 68 },
  { label: "D2", x: 342, y: 68 },
  { label: "D3", x: 342, y: 150 },
  { label: "D4", x: 260, y: 150 },
];

const illustrationCopy = {
  "source-destination": {
    title: "Source points map to top-down points",
    description:
      "Four source points in the camera image connect to four destination points in the top-down plane with a real-world ruler marker.",
    caption:
      "Match the same four real marks in the same order, then enter the real D1 to D2 distance.",
  },
  boundaries: {
    title: "Event lines and zones use the analytics still",
    description:
      "A line boundary and a polygon event zone are drawn on the camera analytics still where tracked motion passes.",
    caption:
      "Line boundaries emit crossing events; polygon zones emit enter and exit events as tracks move through the marked shape.",
  },
  regions: {
    title: "Detection regions gate the analytics still",
    description:
      "Include polygons keep detections eligible in the observation area; exclusion polygons suppress noisy pockets before events run.",
    caption:
      "Include keeps detections eligible inside the observation area; exclude suppresses noisy motion before event boundaries run.",
  },
} satisfies Record<
  NonNullable<CalibrationFlowIllustrationProps["mode"]>,
  IllustrationCopy
>;

export function CalibrationFlowIllustration({
  mode = "source-destination",
  animated = true,
}: CalibrationFlowIllustrationProps) {
  const idPrefix = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const sourcePlaneId = `${idPrefix}-source-plane`;
  const destinationPlaneId = `${idPrefix}-destination-plane`;
  const copy = illustrationCopy[mode];

  if (mode === "boundaries" || mode === "regions") {
    return (
      <SceneAuthoringIllustration copy={copy} idPrefix={idPrefix} mode={mode} />
    );
  }

  return (
    <figure className="rounded-lg border border-white/10 bg-[#050b13] p-3">
      <svg
        role="img"
        aria-label={copy.title}
        className="h-auto w-full"
        height="210"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 400 210"
        width="400"
      >
        <desc>{copy.description}</desc>

        <defs>
          <linearGradient id={sourcePlaneId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#17345c" />
            <stop offset="100%" stopColor="#09182a" />
          </linearGradient>
          <linearGradient id={destinationPlaneId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#2a1f56" />
            <stop offset="100%" stopColor="#111426" />
          </linearGradient>
        </defs>

        <path
          d="M20 48 L178 26 L188 166 L10 176 Z"
          fill={`url(#${sourcePlaneId})`}
          stroke="#6cb0ff"
          strokeWidth="2"
        />
        <text
          x="24"
          y="28"
          fill="#d8e2f2"
          fontFamily={SVG_FONT_FAMILY}
          fontSize="11"
        >
          Camera image
        </text>

        <rect
          x="242"
          y="42"
          width="124"
          height="124"
          rx="10"
          fill={`url(#${destinationPlaneId})`}
          stroke="#b28fff"
          strokeWidth="2"
        />
        <text
          x="248"
          y="28"
          fill="#d8e2f2"
          fontFamily={SVG_FONT_FAMILY}
          fontSize="11"
        >
          Top-down plane
        </text>

        {sourcePoints.map((sourcePoint, index) => {
          const destinationPoint = destinationPoints[index];
          return (
            <line
              key={`${sourcePoint.label}-${destinationPoint.label}`}
              className={animated ? "calibration-map-line" : undefined}
              x1={sourcePoint.x}
              y1={sourcePoint.y}
              x2={destinationPoint.x}
              y2={destinationPoint.y}
              stroke="#8fd3ff"
              strokeDasharray="4 6"
              strokeWidth="1.5"
              opacity="0.55"
            />
          );
        })}

        {sourcePoints.map((point) => (
          <PointMarker
            key={point.label}
            color="#6cb0ff"
            fill="#09192c"
            label={point.label}
            x={point.x}
            y={point.y}
          />
        ))}

        {destinationPoints.map((point) => (
          <PointMarker
            key={point.label}
            color="#b28fff"
            fill="#161428"
            label={point.label}
            x={point.x}
            y={point.y}
          />
        ))}

        <line
          x1="260"
          x2="342"
          y1="184"
          y2="184"
          stroke="#6fe0c5"
          strokeWidth="3"
        />
        <line
          x1="260"
          x2="260"
          y1="177"
          y2="191"
          stroke="#6fe0c5"
          strokeWidth="2"
        />
        <line
          x1="342"
          x2="342"
          y1="177"
          y2="191"
          stroke="#6fe0c5"
          strokeWidth="2"
        />
        <text
          x="301"
          y="202"
          textAnchor="middle"
          fill="#bcefe3"
          fontFamily={SVG_FONT_FAMILY}
          fontSize="11"
        >
          D1-D2 measured distance
        </text>
      </svg>
      <figcaption className="mt-2 text-xs leading-5 text-[#9fb2cf]">
        {copy.caption}
      </figcaption>
    </figure>
  );
}

function SceneAuthoringIllustration({
  copy,
  idPrefix,
  mode,
}: {
  copy: IllustrationCopy;
  idPrefix: string;
  mode: "boundaries" | "regions";
}) {
  const planeGradientId = `${idPrefix}-analytics-plane`;
  const includeGradientId = `${idPrefix}-include-region`;
  const exclusionGradientId = `${idPrefix}-exclusion-region`;
  const exclusionHatchId = `${idPrefix}-exclusion-hatch`;
  const eventZoneGradientId = `${idPrefix}-event-zone`;

  return (
    <figure className="rounded-lg border border-white/10 bg-[#050b13] p-3">
      <svg
        role="img"
        aria-label={copy.title}
        className="block h-auto w-full"
        data-guidance-scene={mode}
        height="450"
        shapeRendering="geometricPrecision"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 800 450"
        width="800"
      >
        <desc>{copy.description}</desc>
        <defs>
          <linearGradient id={planeGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#10233a" />
            <stop offset="64%" stopColor="#0c1a2b" />
            <stop offset="100%" stopColor="#07111d" />
          </linearGradient>
          <linearGradient id={eventZoneGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.1" />
          </linearGradient>
          <linearGradient id={includeGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#4ade80" stopOpacity="0.23" />
            <stop offset="100%" stopColor="#6fe0c5" stopOpacity="0.1" />
          </linearGradient>
          <linearGradient id={exclusionGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#ff7a7a" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#ffb86b" stopOpacity="0.08" />
          </linearGradient>
          <pattern
            id={exclusionHatchId}
            width="12"
            height="12"
            patternTransform="rotate(45 0 0)"
            patternUnits="userSpaceOnUse"
          >
            <line
              x1="0"
              x2="0"
              y1="0"
              y2="12"
              stroke="#ff7a7a"
              strokeOpacity="0.35"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
            />
          </pattern>
        </defs>

        <rect width="800" height="450" rx="18" fill="#07101b" />
        <ScenePerspectivePlane planeGradientId={planeGradientId} />

        {mode === "boundaries" ? (
          <EventGeometry eventZoneGradientId={eventZoneGradientId} />
        ) : (
          <RegionGeometry
            exclusionGradientId={exclusionGradientId}
            exclusionHatchId={exclusionHatchId}
            includeGradientId={includeGradientId}
          />
        )}
      </svg>
      <figcaption className="mt-3 text-sm leading-6 text-[#a8bad6]">
        {copy.caption}
      </figcaption>
    </figure>
  );
}

function ScenePerspectivePlane({
  planeGradientId,
}: {
  planeGradientId: string;
}) {
  return (
    <g aria-label="Analytics still perspective plane">
      <polygon
        data-camera-plane=""
        points="120,380 680,380 580,120 220,120"
        fill={`url(#${planeGradientId})`}
        stroke="#334b6c"
        strokeWidth="2.5"
        vectorEffect="non-scaling-stroke"
      />
      <path
        d="M265 120 L195 380 M355 120 L340 380 M445 120 L460 380 M535 120 L605 380"
        fill="none"
        stroke="#29415f"
        strokeDasharray="4 12"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
      <path
        d="M200 180 L600 180 M175 250 L625 250 M150 320 L650 320"
        fill="none"
        stroke="#203852"
        strokeDasharray="4 12"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </g>
  );
}

function EventGeometry({
  eventZoneGradientId,
}: {
  eventZoneGradientId: string;
}) {
  return (
    <g aria-label="Event boundary schematic">
      <polygon
        data-boundary="event-zone"
        points="450,170 580,200 540,330 400,300"
        fill={`url(#${eventZoneGradientId})`}
        stroke="#38bdf8"
        strokeLinejoin="round"
        strokeWidth="4"
        vectorEffect="non-scaling-stroke"
      />
      <line
        x1="180"
        x2="350"
        y1="270"
        y2="310"
        stroke="#34d399"
        strokeLinecap="round"
        strokeOpacity="0.22"
        strokeWidth="18"
        vectorEffect="non-scaling-stroke"
      />
      <line
        data-boundary="line-crossing"
        x1="180"
        x2="350"
        y1="270"
        y2="310"
        stroke="#34d399"
        strokeLinecap="round"
        strokeWidth="8"
        vectorEffect="non-scaling-stroke"
      />

      <MotionTrack
        anchorId="line-crossing"
        dataMotionPath="event-path-1"
        d="M220 210 Q270 270 260 350"
        endX={260}
        endY={350}
        startX={220}
        startY={210}
      />
      <MotionTrack
        anchorId="zone-entry"
        dataMotionPath="event-path-2"
        d="M350 190 Q420 220 480 290"
        endX={480}
        endY={290}
        startX={350}
        startY={190}
      />

      <SceneLabel
        dataLabel="line-boundary"
        detail="Crossing trigger"
        detailX={220}
        detailY={335}
        title="Line Boundary"
        titleX={190}
        titleY={255}
      />
      <SceneLabel
        dataLabel="event-zone"
        detail="Enter/Exit events"
        detailX={502}
        detailY={263}
        textAnchor="middle"
        title="Event Zone"
        titleX={520}
        titleY={242}
      />
    </g>
  );
}

function RegionGeometry({
  exclusionGradientId,
  exclusionHatchId,
  includeGradientId,
}: {
  exclusionGradientId: string;
  exclusionHatchId: string;
  includeGradientId: string;
}) {
  return (
    <g aria-label="Detection region schematic">
      <polygon
        data-region="include"
        points="170,340 610,350 510,150 250,140"
        fill={`url(#${includeGradientId})`}
        stroke="#4ade80"
        strokeLinejoin="round"
        strokeWidth="4"
        vectorEffect="non-scaling-stroke"
      />
      <polygon
        data-region="exclusion"
        points="450,220 560,240 540,320 420,290"
        fill={`url(#${exclusionGradientId})`}
        stroke="#ff7a7a"
        strokeDasharray="8 6"
        strokeLinejoin="round"
        strokeWidth="3.5"
        vectorEffect="non-scaling-stroke"
      />
      <polygon
        points="450,220 560,240 540,320 420,290"
        fill={`url(#${exclusionHatchId})`}
        pointerEvents="none"
      />

      <MotionTrack
        anchorId="included"
        dataMotionPath="region-path-1"
        d="M240 270 Q300 250 330 310"
        endX={330}
        endY={310}
        startX={240}
        startY={270}
      />
      <IgnoredAnchorMark x={500} y={285} />

      <SceneLabel
        dataLabel="include-region"
        detail="Detections eligible"
        detailX={210}
        detailY={200}
        title="Include Area"
        titleX={210}
        titleY={180}
      />
      <SceneLabel
        dataLabel="exclusion-region"
        detail="Noisy motion ignored"
        detailX={502}
        detailY={282}
        textAnchor="middle"
        title="Exclude Mask"
        titleX={502}
        titleY={262}
      />
    </g>
  );
}

function MotionTrack({
  anchorId,
  dataMotionPath,
  d,
  endX,
  endY,
  startX,
  startY,
}: {
  anchorId: string;
  dataMotionPath: string;
  d: string;
  endX: number;
  endY: number;
  startX: number;
  startY: number;
}) {
  return (
    <g data-scene-glyph="neutral-track">
      <path
        data-motion-path={dataMotionPath}
        d={d}
        fill="none"
        stroke="#94a3b8"
        strokeDasharray="4 6"
        strokeLinecap="round"
        strokeOpacity="0.72"
        strokeWidth="2.4"
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={startX} cy={startY} fill="#f8fafc" opacity="0.32" r="4" />
      <AnchorMark id={anchorId} x={endX} y={endY} />
    </g>
  );
}

function AnchorMark({ id, x, y }: { id: string; x: number; y: number }) {
  return (
    <g>
      <circle
        data-track-anchor={id}
        cx={x}
        cy={y}
        fill="#f8fafc"
        r="7"
        vectorEffect="non-scaling-stroke"
      />
      <circle
        cx={x}
        cy={y}
        fill="none"
        opacity="0.58"
        r="16"
        stroke="#f8fafc"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </g>
  );
}

function IgnoredAnchorMark({ x, y }: { x: number; y: number }) {
  return (
    <g data-track-anchor="ignored" data-track-anchor-state="ignored">
      <circle cx={x} cy={y} fill="#64748b" r="6" />
      <line
        x1={x - 8}
        x2={x + 8}
        y1={y - 8}
        y2={y + 8}
        stroke="#ff7a7a"
        strokeLinecap="round"
        strokeWidth="2.8"
        vectorEffect="non-scaling-stroke"
      />
      <line
        x1={x + 8}
        x2={x - 8}
        y1={y - 8}
        y2={y + 8}
        stroke="#ff7a7a"
        strokeLinecap="round"
        strokeWidth="2.8"
        vectorEffect="non-scaling-stroke"
      />
    </g>
  );
}

function SceneLabel({
  dataLabel,
  detail,
  detailX,
  detailY,
  textAnchor = "start",
  title,
  titleX,
  titleY,
}: {
  dataLabel: string;
  detail: string;
  detailX: number;
  detailY: number;
  textAnchor?: "start" | "middle";
  title: string;
  titleX: number;
  titleY: number;
}) {
  return (
    <g data-scene-label={dataLabel}>
      <text
        x={titleX}
        y={titleY}
        fill="#f8fafc"
        fontFamily={SVG_FONT_FAMILY}
        fontSize="18"
        fontWeight="700"
        paintOrder="stroke fill"
        stroke="#07101b"
        strokeLinejoin="round"
        strokeWidth="4"
        textAnchor={textAnchor}
      >
        {title}
      </text>
      <text
        x={detailX}
        y={detailY}
        fill="#a8bad6"
        fontFamily={SVG_FONT_FAMILY}
        fontSize="14"
        fontWeight="500"
        paintOrder="stroke fill"
        stroke="#07101b"
        strokeLinejoin="round"
        strokeWidth="3"
        textAnchor={textAnchor}
      >
        {detail}
      </text>
    </g>
  );
}

function PointMarker({
  color,
  fill,
  label,
  x,
  y,
}: {
  color: string;
  fill: string;
  label: string;
  x: number;
  y: number;
}) {
  return (
    <g>
      <circle cx={x} cy={y} r="11" fill={fill} stroke={color} />
      <text
        x={x}
        y={y + 4}
        textAnchor="middle"
        fill="#eef6ff"
        fontFamily={SVG_FONT_FAMILY}
        fontSize="10"
        fontWeight="700"
      >
        {label}
      </text>
    </g>
  );
}
