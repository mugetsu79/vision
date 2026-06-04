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
  { id: "alpha", x: 118, y: 128, envelope: "circle" },
  { id: "bravo", x: 218, y: 104, envelope: "capsule" },
  { id: "charlie", x: 310, y: 134, envelope: "diamond" },
] as const;

const neutralMotionPaths = [
  "M84 154 C118 132 146 124 190 138",
  "M188 90 C224 108 260 126 326 130",
] as const;

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
      "A line crossing and a polygon event zone are drawn on the camera analytics still where tracked motion passes.",
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
} satisfies Record<NonNullable<CalibrationFlowIllustrationProps["mode"]>, IllustrationCopy>;

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
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="11" fill="#09192c" stroke="#6cb0ff" />
            <text
              x={point.x}
              y={point.y + 4}
              textAnchor="middle"
              fill="#eef6ff"
              fontSize="10"
              fontWeight="700"
            >
              {point.label}
            </text>
          </g>
        ))}

        {destinationPoints.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="11" fill="#161428" stroke="#b28fff" />
            <text
              x={point.x}
              y={point.y + 4}
              textAnchor="middle"
              fill="#f3eeff"
              fontSize="10"
              fontWeight="700"
            >
              {point.label}
            </text>
          </g>
        ))}

        <line x1="260" x2="342" y1="184" y2="184" stroke="#6fe0c5" strokeWidth="3" />
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
          opacity="0.72"
        />
      ))}

      {neutralAnchors.map((anchor) => (
        <g key={anchor.id}>
          {anchor.envelope === "capsule" ? (
            <rect
              data-object-envelope={anchor.id}
              x={anchor.x - 20}
              y={anchor.y - 10}
              width="40"
              height="20"
              rx="10"
              fill="#c5d6e8"
              opacity="0.16"
              stroke="#c5d6e8"
              strokeWidth="1.5"
            />
          ) : null}
          {anchor.envelope === "circle" ? (
            <circle
              data-object-envelope={anchor.id}
              cx={anchor.x}
              cy={anchor.y}
              r="15"
              fill="#c5d6e8"
              opacity="0.14"
              stroke="#c5d6e8"
              strokeWidth="1.5"
            />
          ) : null}
          {anchor.envelope === "diamond" ? (
            <path
              data-object-envelope={anchor.id}
              d={`M${anchor.x} ${anchor.y - 16} L${anchor.x + 18} ${anchor.y} L${anchor.x} ${
                anchor.y + 16
              } L${anchor.x - 18} ${anchor.y} Z`}
              fill="#c5d6e8"
              opacity="0.14"
              stroke="#c5d6e8"
              strokeWidth="1.5"
            />
          ) : null}
          <circle
            data-track-anchor={anchor.id}
            cx={anchor.x}
            cy={anchor.y}
            r="4.5"
            fill="#f4f8ff"
            stroke="#08111a"
            strokeWidth="1.5"
          />
        </g>
      ))}

    </g>
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
          <linearGradient id={stillGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#10233a" />
            <stop offset="56%" stopColor="#0a1826" />
            <stop offset="100%" stopColor="#060b12" />
          </linearGradient>
          <linearGradient id={eventZoneGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#8fd3ff" stopOpacity="0.32" />
            <stop offset="100%" stopColor="#8fd3ff" stopOpacity="0.08" />
          </linearGradient>
          <linearGradient id={includeGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#7ee7a8" stopOpacity="0.32" />
            <stop offset="100%" stopColor="#7ee7a8" stopOpacity="0.08" />
          </linearGradient>
          <linearGradient id={exclusionGradientId} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#ffb86b" stopOpacity="0.34" />
            <stop offset="100%" stopColor="#ffb86b" stopOpacity="0.08" />
          </linearGradient>
        </defs>

        <rect x="8" y="12" width="384" height="186" rx="12" fill="#050b13" />
        <path
          d="M30 42 L356 26 L382 174 L16 184 Z"
          fill={`url(#${stillGradientId})`}
          stroke="#314966"
          strokeWidth="2"
        />
        <text x="28" y="28" fill="#d8e2f2" fontSize="11">
          Analytics still
        </text>
        <text x="292" y="28" fill="#8ea4c7" fontSize="9" textAnchor="middle">
          frame geometry
        </text>

        <path
          d="M72 48 L62 177"
          stroke="#9fb2cf"
          strokeDasharray="6 8"
          strokeWidth="2"
          opacity="0.72"
        />
        <path
          d="M162 43 L174 178"
          stroke="#9fb2cf"
          strokeDasharray="6 8"
          strokeWidth="2"
          opacity="0.72"
        />
        <path
          d="M260 37 L300 176"
          stroke="#9fb2cf"
          strokeDasharray="6 8"
          strokeWidth="2"
          opacity="0.72"
        />
        <path
          d="M28 136 L380 126"
          stroke="#6b7f9d"
          strokeDasharray="5 7"
          strokeWidth="1.4"
          opacity="0.5"
        />
        <path
          d="M40 78 L366 70"
          stroke="#6b7f9d"
          strokeDasharray="5 7"
          strokeWidth="1.2"
          opacity="0.35"
        />

        {mode === "boundaries" ? (
          <g>
            <polygon
              data-boundary="event-zone"
              points="242,70 338,76 356,145 232,154"
              fill={`url(#${eventZoneGradientId})`}
              stroke="#8fd3ff"
              strokeLinejoin="round"
              strokeWidth="2.4"
            />
            <path
              data-label-leader="event-zone"
              d="M304 64 L304 82"
              fill="none"
              stroke="#8fd3ff"
              strokeDasharray="4 5"
              strokeLinecap="round"
              strokeWidth="1.4"
              opacity="0.82"
            />
            <text
              data-annotation-label="event-zone"
              x="304"
              y="60"
              textAnchor="middle"
              fill="#c5e9ff"
              fontSize="8"
              paintOrder="stroke"
              stroke="#050b13"
              strokeWidth="2.4"
            >
              polygon event zone
            </text>
            <path
              data-label-leader="enter-exit-event"
              d="M318 176 L316 146"
              fill="none"
              stroke="#8fd3ff"
              strokeDasharray="4 5"
              strokeLinecap="round"
              strokeWidth="1.4"
              opacity="0.72"
            />
            <text
              data-annotation-label="enter-exit-event"
              x="318"
              y="186"
              textAnchor="middle"
              fill="#eef9ff"
              fontSize="8"
              paintOrder="stroke"
              stroke="#050b13"
              strokeWidth="2.4"
            >
              enter/exit event
            </text>

            <line
              data-boundary="line-crossing"
              x1="70"
              x2="222"
              y1="150"
              y2="136"
              stroke="#6fe0c5"
              strokeLinecap="round"
              strokeWidth="5"
            />
            <circle cx="104" cy="147" r="5" fill="#6fe0c5" />
            <circle cx="190" cy="139" r="5" fill="#6fe0c5" />
            <path
              d="M136 118 C150 126 166 136 184 155"
              fill="none"
              stroke="#6fe0c5"
              strokeDasharray="5 6"
              strokeLinecap="round"
              strokeWidth="1.8"
              opacity="0.75"
            />
            <path
              data-label-leader="line-crossing"
              d="M102 190 L108 148"
              fill="none"
              stroke="#6fe0c5"
              strokeDasharray="4 5"
              strokeLinecap="round"
              strokeWidth="1.4"
              opacity="0.82"
            />
            <text
              data-annotation-label="line-crossing"
              x="102"
              y="202"
              textAnchor="middle"
              fill="#bcefe3"
              fontSize="8"
              paintOrder="stroke"
              stroke="#050b13"
              strokeWidth="2.4"
            >
              line crossing
            </text>
            <path
              data-label-leader="crossing-event"
              d="M206 186 L178 154"
              fill="none"
              stroke="#6fe0c5"
              strokeDasharray="4 5"
              strokeLinecap="round"
              strokeWidth="1.4"
              opacity="0.72"
            />
            <text
              data-annotation-label="crossing-event"
              x="206"
              y="198"
              textAnchor="middle"
              fill="#effff9"
              fontSize="8"
              paintOrder="stroke"
              stroke="#050b13"
              strokeWidth="2.4"
            >
              crossing event
            </text>
          </g>
        ) : null}

        {mode === "regions" ? (
          <g>
            <polygon
              data-region="include"
              points="56,64 268,50 306,164 36,176"
              fill={`url(#${includeGradientId})`}
              stroke="#7ee7a8"
              strokeLinejoin="round"
              strokeWidth="2.4"
            />
            <path
              data-label-leader="include-region"
              d="M154 54 L164 86"
              fill="none"
              stroke="#7ee7a8"
              strokeDasharray="4 5"
              strokeLinecap="round"
              strokeWidth="1.4"
              opacity="0.82"
            />
            <text
              data-annotation-label="include-region"
              x="154"
              y="50"
              textAnchor="middle"
              fill="#c8f7d6"
              fontSize="8"
              paintOrder="stroke"
              stroke="#050b13"
              strokeWidth="2.4"
            >
              include detection area
            </text>

            <polygon
              data-region="exclusion"
              points="266,76 342,72 352,128 276,134"
              fill={`url(#${exclusionGradientId})`}
              stroke="#ffb86b"
              strokeDasharray="6 5"
              strokeLinejoin="round"
              strokeWidth="2.4"
            />
            <path
              data-label-leader="exclusion-region"
              d="M326 72 L328 92"
              fill="none"
              stroke="#ffb86b"
              strokeDasharray="4 5"
              strokeLinecap="round"
              strokeWidth="1.4"
              opacity="0.82"
            />
            <text
              data-annotation-label="exclusion-region"
              x="326"
              y="68"
              textAnchor="middle"
              fill="#ffd9a1"
              fontSize="8"
              paintOrder="stroke"
              stroke="#050b13"
              strokeWidth="2.4"
            >
              exclusion mask
            </text>
          </g>
        ) : null}

        <NeutralTrackLayer />
        <g aria-label="Track annotation labels">
          <path
            data-label-leader="tracked-anchor"
            d="M78 112 L116 128"
            fill="none"
            stroke="#d8e2f2"
            strokeDasharray="4 5"
            strokeLinecap="round"
            strokeWidth="1.3"
            opacity="0.58"
          />
          <text
            data-annotation-label="tracked-anchor"
            x="72"
            y="110"
            textAnchor="middle"
            fill="#d8e2f2"
            fontSize="8"
            paintOrder="stroke"
            stroke="#050b13"
            strokeWidth="2.4"
          >
            tracked anchor
          </text>
          <path
            data-label-leader="object-path"
            d="M224 86 L214 104"
            fill="none"
            stroke="#9fb2cf"
            strokeDasharray="4 5"
            strokeLinecap="round"
            strokeWidth="1.3"
            opacity="0.58"
          />
          <text
            data-annotation-label="object-path"
            x="224"
            y="82"
            textAnchor="middle"
            fill="#9fb2cf"
            fontSize="8"
            paintOrder="stroke"
            stroke="#050b13"
            strokeWidth="2.4"
          >
            object path
          </text>
        </g>
      </svg>
      <figcaption className="mt-2 text-xs leading-5 text-[#9fb2cf]">
        {copy.caption}
      </figcaption>
    </figure>
  );
}
