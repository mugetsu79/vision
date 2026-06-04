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

type RailItem = {
  id: string;
  number: string;
  label: string;
  detail: string;
  tone: "blue" | "green" | "amber" | "neutral";
};

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

const neutralAnchors = [
  { id: "alpha", x: 78, y: 140, envelope: "circle" },
  { id: "bravo", x: 154, y: 122, envelope: "capsule" },
  { id: "charlie", x: 220, y: 150, envelope: "diamond" },
] as const;

const neutralMotionPaths = [
  "M48 170 C84 146 112 136 150 148",
  "M130 106 C164 124 192 140 226 146",
] as const;

const eventRails: RailItem[] = [
  {
    id: "line-crossing",
    number: "1",
    label: "Line boundary",
    detail: "crossing events",
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
    detail: "event position",
    tone: "neutral",
  },
  {
    id: "object-path",
    number: "5",
    label: "Object path",
    detail: "motion path",
    tone: "neutral",
  },
];

const regionRails: RailItem[] = [
  {
    id: "include-region",
    number: "1",
    label: "Include area",
    detail: "detections in scope",
    tone: "green",
  },
  {
    id: "exclusion-region",
    number: "2",
    label: "Exclude mask",
    detail: "noisy motion off",
    tone: "amber",
  },
  {
    id: "tracked-anchor",
    number: "3",
    label: "Tracked anchor",
    detail: "after masking",
    tone: "neutral",
  },
  {
    id: "object-path",
    number: "4",
    label: "Object path",
    detail: "through still",
    tone: "neutral",
  },
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

const toneColors = {
  blue: {
    fill: "#102339",
    stroke: "#8fd3ff",
    text: "#c5e9ff",
  },
  green: {
    fill: "#0a2a2c",
    stroke: "#6fe0c5",
    text: "#bcefe3",
  },
  amber: {
    fill: "#352414",
    stroke: "#ffb86b",
    text: "#ffd9a1",
  },
  neutral: {
    fill: "#162235",
    stroke: "#9fb2cf",
    text: "#d8e2f2",
  },
} satisfies Record<RailItem["tone"], { fill: string; stroke: string; text: string }>;

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
      <SceneAuthoringIllustration
        copy={copy}
        idPrefix={idPrefix}
        mode={mode}
      />
    );
  }

  return (
    <figure className="rounded-lg border border-white/10 bg-[#050b13] p-3">
      <svg
        role="img"
        aria-label={copy.title}
        className="h-auto w-full"
        viewBox="0 0 400 210"
      >
        <title>{copy.title}</title>
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
        <text x="24" y="28" fill="#d8e2f2" fontSize="11">
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
        <text x="248" y="28" fill="#d8e2f2" fontSize="11">
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
        <line x1="260" x2="260" y1="177" y2="191" stroke="#6fe0c5" strokeWidth="2" />
        <line x1="342" x2="342" y1="177" y2="191" stroke="#6fe0c5" strokeWidth="2" />
        <text x="301" y="202" textAnchor="middle" fill="#bcefe3" fontSize="11">
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
  const includeGradientId = `${idPrefix}-include-region`;
  const exclusionGradientId = `${idPrefix}-exclusion-region`;
  const eventZoneGradientId = `${idPrefix}-event-zone`;
  const rails = mode === "boundaries" ? eventRails : regionRails;

  return (
    <figure className="rounded-lg border border-white/10 bg-[#050b13] p-3">
      <svg
        role="img"
        aria-label={copy.title}
        className="h-auto w-full"
        viewBox="0 0 440 260"
      >
        <title>{copy.title}</title>
        <desc>{copy.description}</desc>

        <defs>
          <linearGradient id={stillGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#10233a" />
            <stop offset="62%" stopColor="#0a1826" />
            <stop offset="100%" stopColor="#060b12" />
          </linearGradient>
          <linearGradient id={eventZoneGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#8fd3ff" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#8fd3ff" stopOpacity="0.08" />
          </linearGradient>
          <linearGradient id={includeGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#7ee7a8" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#7ee7a8" stopOpacity="0.08" />
          </linearGradient>
          <linearGradient id={exclusionGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#ffb86b" stopOpacity="0.32" />
            <stop offset="100%" stopColor="#ffb86b" stopOpacity="0.08" />
          </linearGradient>
        </defs>

        <rect x="8" y="12" width="424" height="236" rx="12" fill="#050b13" />
        <text x="22" y="31" fill="#d8e2f2" fontSize="11" fontWeight="700">
          Analytics still
        </text>
        <text x="278" y="31" fill="#8ea4c7" fontSize="9">
          annotation rail
        </text>

        <g aria-label="Neutral camera analytics still">
          <path
            d="M26 72 L238 60 L252 184 L16 194 Z"
            fill={`url(#${stillGradientId})`}
            stroke="#314966"
            strokeWidth="2"
          />
          <path
            d="M58 78 L50 186 M124 72 L128 188 M194 68 L212 186 M24 146 L248 138 M36 104 L240 98"
            fill="none"
            stroke="#7b91af"
            strokeDasharray="5 7"
            strokeWidth="1.4"
            opacity="0.55"
          />

          {mode === "boundaries" ? (
            <EventGeometry eventZoneGradientId={eventZoneGradientId} />
          ) : (
            <RegionGeometry
              exclusionGradientId={exclusionGradientId}
              includeGradientId={includeGradientId}
            />
          )}

          <NeutralTrackLayer />
        </g>

        <AnnotationRail items={rails} />
      </svg>
      <figcaption className="mt-2 text-xs leading-5 text-[#9fb2cf]">
        {copy.caption}
      </figcaption>
    </figure>
  );
}

function EventGeometry({ eventZoneGradientId }: { eventZoneGradientId: string }) {
  return (
    <g>
      <line
        data-boundary="line-crossing"
        x1="58"
        x2="158"
        y1="172"
        y2="162"
        stroke="#6fe0c5"
        strokeLinecap="round"
        strokeWidth="5"
      />
      <polygon
        data-boundary="event-zone"
        points="176,98 236,104 246,162 164,170"
        fill={`url(#${eventZoneGradientId})`}
        stroke="#8fd3ff"
        strokeLinejoin="round"
        strokeWidth="2.4"
      />
      <SceneCallout label="1" tone="green" x={54} y={156} />
      <SceneCallout label="2" tone="green" x={116} y={148} />
      <SceneCallout label="3" tone="blue" x={204} y={102} />
      <SceneCallout label="4" tone="neutral" x={76} y={118} />
      <SceneCallout label="5" tone="neutral" x={178} y={132} />
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
        points="52,104 184,92 224,170 42,184"
        fill={`url(#${includeGradientId})`}
        stroke="#7ee7a8"
        strokeLinejoin="round"
        strokeWidth="2.4"
      />
      <polygon
        data-region="exclusion"
        points="198,108 240,104 248,150 204,156"
        fill={`url(#${exclusionGradientId})`}
        stroke="#ffb86b"
        strokeDasharray="6 5"
        strokeLinejoin="round"
        strokeWidth="2.4"
      />
      <SceneCallout label="1" tone="green" x={70} y={112} />
      <SceneCallout label="2" tone="amber" x={214} y={116} />
      <SceneCallout label="3" tone="neutral" x={132} y={144} />
      <SceneCallout label="4" tone="neutral" x={182} y={122} />
    </g>
  );
}

function NeutralTrackLayer() {
  return (
    <g data-scene-glyph="neutral-tracks" opacity="0.96">
      {neutralMotionPaths.map((path, index) => (
        <path
          key={path}
          data-motion-path={`path-${index + 1}`}
          d={path}
          fill="none"
          stroke="#9fb2cf"
          strokeDasharray="5 7"
          strokeLinecap="round"
          strokeWidth="1.8"
          opacity="0.68"
        />
      ))}

      {neutralAnchors.map((anchor) => (
        <g key={anchor.id}>
          {anchor.envelope === "capsule" ? (
            <rect
              data-object-envelope={anchor.id}
              x={anchor.x - 19}
              y={anchor.y - 9}
              width="38"
              height="18"
              rx="9"
              fill="#c5d6e8"
              opacity="0.15"
              stroke="#c5d6e8"
              strokeWidth="1.4"
            />
          ) : null}
          {anchor.envelope === "circle" ? (
            <circle
              data-object-envelope={anchor.id}
              cx={anchor.x}
              cy={anchor.y}
              r="14"
              fill="#c5d6e8"
              opacity="0.14"
              stroke="#c5d6e8"
              strokeWidth="1.4"
            />
          ) : null}
          {anchor.envelope === "diamond" ? (
            <path
              data-object-envelope={anchor.id}
              d={`M${anchor.x} ${anchor.y - 15} L${anchor.x + 17} ${anchor.y} L${anchor.x} ${
                anchor.y + 15
              } L${anchor.x - 17} ${anchor.y} Z`}
              fill="#c5d6e8"
              opacity="0.14"
              stroke="#c5d6e8"
              strokeWidth="1.4"
            />
          ) : null}
          <circle
            data-track-anchor={anchor.id}
            cx={anchor.x}
            cy={anchor.y}
            r="4.3"
            fill="#f4f8ff"
            stroke="#08111a"
            strokeWidth="1.5"
          />
        </g>
      ))}
    </g>
  );
}

function AnnotationRail({ items }: { items: RailItem[] }) {
  return (
    <g aria-label="Annotation rail">
      <rect
        x="270"
        y="44"
        width="154"
        height="184"
        rx="10"
        fill="#07101b"
        stroke="#253a5b"
      />
      {items.map((item, index) => {
        const colors = toneColors[item.tone];
        const y = 56 + index * 34;
        return (
          <g
            key={item.id}
            data-annotation-label={item.id}
            data-annotation-rail=""
          >
            <rect
              x="278"
              y={y}
              width="138"
              height="28"
              rx="7"
              fill="#0c1522"
              stroke="#253a5b"
            />
            <circle
              cx="291"
              cy={y + 14}
              r="9"
              fill={colors.fill}
              stroke={colors.stroke}
              strokeWidth="1.4"
            />
            <text
              x="291"
              y={y + 18}
              textAnchor="middle"
              fill="#f6faff"
              fontSize="8"
              fontWeight="700"
            >
              {item.number}
            </text>
            <text
              x="304"
              y={y + 12}
              fill={colors.text}
              fontSize="8.4"
              fontWeight="700"
            >
              {item.label}
            </text>
            <text x="304" y={y + 23} fill="#9fb2cf" fontSize="7.2">
              {item.detail}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function SceneCallout({
  label,
  tone,
  x,
  y,
}: {
  label: string;
  tone: RailItem["tone"];
  x: number;
  y: number;
}) {
  const colors = toneColors[tone];
  return (
    <g data-scene-callout={label}>
      <circle
        cx={x}
        cy={y}
        r="10"
        fill={colors.fill}
        stroke={colors.stroke}
        strokeWidth="1.7"
      />
      <text
        x={x}
        y={y + 4}
        textAnchor="middle"
        fill="#f6faff"
        fontSize="9.5"
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
        fontSize="10"
        fontWeight="700"
      >
        {label}
      </text>
    </g>
  );
}
