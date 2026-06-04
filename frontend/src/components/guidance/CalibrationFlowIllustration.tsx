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

type LegendItem = {
  id: string;
  number: string;
  label: string;
  detail: string;
  tone: "blue" | "green" | "amber" | "neutral";
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

const eventLegend: LegendItem[] = [
  {
    id: "line-crossing",
    number: "1",
    label: "Line boundary",
    detail: "crossing trigger",
    tone: "green",
  },
  {
    id: "crossing-event",
    number: "2",
    label: "Crossing event",
    detail: "anchor changes side",
    tone: "green",
  },
  {
    id: "event-zone",
    number: "3",
    label: "Event zone",
    detail: "enter/exit event",
    tone: "blue",
  },
  {
    id: "tracked-anchor",
    number: "4",
    label: "Tracked anchor",
    detail: "object path point",
    tone: "neutral",
  },
];

const regionLegend: LegendItem[] = [
  {
    id: "include-region",
    number: "1",
    label: "Include area",
    detail: "detections stay eligible",
    tone: "green",
  },
  {
    id: "exclusion-region",
    number: "2",
    label: "Exclude mask",
    detail: "noisy motion ignored",
    tone: "amber",
  },
  {
    id: "tracked-anchor",
    number: "3",
    label: "Tracked anchor",
    detail: "object path after mask",
    tone: "neutral",
  },
];

const toneColors = {
  blue: {
    bg: "#0d2235",
    fill: "#102339",
    stroke: "#8fd3ff",
    text: "#d3efff",
  },
  green: {
    bg: "#092823",
    fill: "#0a2a2c",
    stroke: "#6fe0c5",
    text: "#c3fff1",
  },
  amber: {
    bg: "#2a1c0e",
    fill: "#352414",
    stroke: "#ffb86b",
    text: "#ffe2ad",
  },
  neutral: {
    bg: "#111b2d",
    fill: "#162235",
    stroke: "#9fb2cf",
    text: "#d8e2f2",
  },
} satisfies Record<
  LegendItem["tone"],
  { bg: string; fill: string; stroke: string; text: string }
>;

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
  const stillGradientId = `${idPrefix}-analytics-still`;
  const sceneGlowId = `${idPrefix}-scene-glow`;
  const includeGradientId = `${idPrefix}-include-region`;
  const exclusionGradientId = `${idPrefix}-exclusion-region`;
  const eventZoneGradientId = `${idPrefix}-event-zone`;
  const legend = mode === "boundaries" ? eventLegend : regionLegend;

  return (
    <figure className="rounded-lg border border-white/10 bg-[#050b13] p-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_15rem]">
        <div className="min-w-0 rounded-[0.9rem] border border-[#253a5b] bg-[#06101a] p-3">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <p className="text-sm font-semibold text-[#e6eefc]">
              Analytics still
            </p>
            <p className="text-[0.68rem] font-medium uppercase tracking-[0.18em] text-[#7f93b2]">
              camera coordinates
            </p>
          </div>
          <svg
            role="img"
            aria-label={copy.title}
            className="block h-auto w-full overflow-visible"
            height="360"
            shapeRendering="geometricPrecision"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 640 360"
            width="640"
          >
            <desc>{copy.description}</desc>
            <defs>
              <radialGradient id={sceneGlowId} cx="48%" cy="52%" r="62%">
                <stop offset="0%" stopColor="#1c3352" stopOpacity="0.5" />
                <stop offset="70%" stopColor="#0c1829" stopOpacity="0.18" />
                <stop offset="100%" stopColor="#06101a" stopOpacity="0" />
              </radialGradient>
              <linearGradient id={stillGradientId} x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stopColor="#132a44" />
                <stop offset="62%" stopColor="#0d2034" />
                <stop offset="100%" stopColor="#071321" />
              </linearGradient>
              <linearGradient
                id={eventZoneGradientId}
                x1="0"
                x2="1"
                y1="0"
                y2="1"
              >
                <stop offset="0%" stopColor="#8fd3ff" stopOpacity="0.34" />
                <stop offset="100%" stopColor="#8fd3ff" stopOpacity="0.08" />
              </linearGradient>
              <linearGradient
                id={includeGradientId}
                x1="0"
                x2="1"
                y1="0"
                y2="1"
              >
                <stop offset="0%" stopColor="#7ee7a8" stopOpacity="0.34" />
                <stop offset="100%" stopColor="#7ee7a8" stopOpacity="0.1" />
              </linearGradient>
              <linearGradient
                id={exclusionGradientId}
                x1="0"
                x2="1"
                y1="0"
                y2="1"
              >
                <stop offset="0%" stopColor="#ffb86b" stopOpacity="0.36" />
                <stop offset="100%" stopColor="#ffb86b" stopOpacity="0.1" />
              </linearGradient>
              <clipPath id={`${idPrefix}-still-clip`}>
                <path d="M76 82 L528 58 L568 280 L48 304 Z" />
              </clipPath>
            </defs>

            <rect x="0" y="0" width="640" height="360" rx="18" fill="#06101a" />
            <ellipse
              cx="300"
              cy="190"
              rx="300"
              ry="172"
              fill={`url(#${sceneGlowId})`}
            />
            <path
              d="M76 82 L528 58 L568 280 L48 304 Z"
              fill={`url(#${stillGradientId})`}
              stroke="#355372"
              strokeWidth="3"
              vectorEffect="non-scaling-stroke"
            />
            <g clipPath={`url(#${idPrefix}-still-clip)`}>
              <path
                d="M124 88 L104 300 M256 72 L260 302 M392 66 L432 300 M64 176 L560 164 M82 228 L570 218"
                fill="none"
                stroke="#7b91af"
                strokeDasharray="9 14"
                strokeWidth="2"
                opacity="0.5"
                vectorEffect="non-scaling-stroke"
              />
              <path
                d="M86 250 C150 204 214 208 272 218 C330 228 386 230 484 198"
                data-motion-path="path-1"
                fill="none"
                stroke="#9fb2cf"
                strokeDasharray="9 13"
                strokeLinecap="round"
                strokeWidth="3"
                opacity="0.7"
                vectorEffect="non-scaling-stroke"
              />
              <path
                d="M260 156 C318 194 374 224 486 236"
                data-motion-path="path-2"
                fill="none"
                stroke="#9fb2cf"
                strokeDasharray="9 13"
                strokeLinecap="round"
                strokeWidth="3"
                opacity="0.62"
                vectorEffect="non-scaling-stroke"
              />
            </g>

            {mode === "boundaries" ? (
              <EventGeometry eventZoneGradientId={eventZoneGradientId} />
            ) : (
              <RegionGeometry
                exclusionGradientId={exclusionGradientId}
                includeGradientId={includeGradientId}
              />
            )}

            <NeutralTrackLayer />
          </svg>
        </div>

        <LegendPanel items={legend} mode={mode} />
      </div>
      <figcaption className="mt-4 border-t border-white/10 pt-3 text-sm leading-6 text-[#a8bad6]">
        {copy.caption}
      </figcaption>
    </figure>
  );
}

function EventGeometry({
  eventZoneGradientId,
}: {
  eventZoneGradientId: string;
}) {
  return (
    <g>
      <line
        data-boundary="line-crossing"
        x1="116"
        x2="302"
        y1="252"
        y2="232"
        stroke="#6fe0c5"
        strokeLinecap="round"
        strokeWidth="11"
        vectorEffect="non-scaling-stroke"
      />
      <polygon
        data-boundary="event-zone"
        points="350,132 500,146 524,242 322,262"
        fill={`url(#${eventZoneGradientId})`}
        stroke="#8fd3ff"
        strokeLinejoin="round"
        strokeWidth="4"
        vectorEffect="non-scaling-stroke"
      />
      <SceneCallout label="1" tone="green" x={112} y={232} />
      <SceneCallout label="2" tone="green" x={252} y={226} />
      <SceneCallout label="3" tone="blue" x={422} y={150} />
      <SceneCallout label="4" tone="neutral" x={174} y={180} />
    </g>
  );
}

function RegionGeometry({
  exclusionGradientId,
  includeGradientId,
}: {
  exclusionGradientId: string;
  includeGradientId: string;
}) {
  return (
    <g>
      <polygon
        data-region="include"
        points="118,150 394,124 462,250 82,284"
        fill={`url(#${includeGradientId})`}
        stroke="#7ee7a8"
        strokeLinejoin="round"
        strokeWidth="4"
        vectorEffect="non-scaling-stroke"
      />
      <polygon
        data-region="exclusion"
        points="432,158 526,148 540,224 450,238"
        fill={`url(#${exclusionGradientId})`}
        stroke="#ffb86b"
        strokeDasharray="10 8"
        strokeLinejoin="round"
        strokeWidth="4"
        vectorEffect="non-scaling-stroke"
      />
      <SceneCallout label="1" tone="green" x={154} y={164} />
      <SceneCallout label="2" tone="amber" x={470} y={174} />
      <SceneCallout label="3" tone="neutral" x={300} y={218} />
    </g>
  );
}

function NeutralTrackLayer() {
  return (
    <g data-scene-glyph="neutral-tracks">
      <g>
        <circle
          data-object-envelope="alpha"
          cx="172"
          cy="212"
          r="42"
          fill="#c5d6e8"
          opacity="0.12"
          stroke="#c5d6e8"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
        <circle
          data-track-anchor="alpha"
          cx="172"
          cy="212"
          r="10"
          fill="#f4f8ff"
          stroke="#08111a"
          strokeWidth="4"
          vectorEffect="non-scaling-stroke"
        />
      </g>
      <g>
        <rect
          data-object-envelope="bravo"
          x="290"
          y="154"
          width="88"
          height="42"
          rx="21"
          fill="#c5d6e8"
          opacity="0.13"
          stroke="#c5d6e8"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
        <circle
          data-track-anchor="bravo"
          cx="334"
          cy="176"
          r="10"
          fill="#f4f8ff"
          stroke="#08111a"
          strokeWidth="4"
          vectorEffect="non-scaling-stroke"
        />
      </g>
      <g>
        <path
          data-object-envelope="charlie"
          d="M474 190 L536 240 L474 290 L412 240 Z"
          fill="#c5d6e8"
          opacity="0.13"
          stroke="#c5d6e8"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
        <circle
          data-track-anchor="charlie"
          cx="474"
          cy="240"
          r="10"
          fill="#f4f8ff"
          stroke="#08111a"
          strokeWidth="4"
          vectorEffect="non-scaling-stroke"
        />
      </g>
    </g>
  );
}

function LegendPanel({
  items,
  mode,
}: {
  items: LegendItem[];
  mode: "boundaries" | "regions";
}) {
  return (
    <aside className="rounded-[0.9rem] border border-[#284066] bg-[#07111d] p-3">
      <p className="mb-3 text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-[#8da3c2]">
        {mode === "boundaries" ? "Event semantics" : "Detection mask order"}
      </p>
      <ol className="space-y-2">
        {items.map((item) => {
          const colors = toneColors[item.tone];
          return (
            <li
              key={item.id}
              data-annotation-label={item.id}
              data-annotation-rail=""
              className="grid grid-cols-[2.2rem_minmax(0,1fr)] items-center gap-2 rounded-[0.7rem] border border-[#284066] bg-[#0c1522] px-2.5 py-2"
            >
              <span
                className="grid size-8 place-items-center rounded-full border-2 text-sm font-bold"
                style={{
                  backgroundColor: colors.fill,
                  borderColor: colors.stroke,
                  color: "#f6faff",
                }}
              >
                {item.number}
              </span>
              <span className="min-w-0">
                <span
                  className="block text-sm font-semibold leading-5"
                  style={{ color: colors.text }}
                >
                  {item.label}
                </span>
                <span className="block text-xs leading-4 text-[#9fb2cf]">
                  {item.detail}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}

function SceneCallout({
  label,
  tone,
  x,
  y,
}: {
  label: string;
  tone: LegendItem["tone"];
  x: number;
  y: number;
}) {
  const colors = toneColors[tone];
  return (
    <g data-scene-callout={label}>
      <circle
        cx={x}
        cy={y}
        r="23"
        fill={colors.fill}
        stroke={colors.stroke}
        strokeWidth="5"
        vectorEffect="non-scaling-stroke"
      />
      <text
        x={x}
        y={y + 8}
        textAnchor="middle"
        fill="#f6faff"
        fontFamily={SVG_FONT_FAMILY}
        fontSize="24"
        fontWeight="700"
      >
        {label}
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
