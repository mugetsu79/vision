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
      "A line crossing and a polygon event zone are drawn on the camera analytics still where tracked anchors move.",
    caption:
      "Line boundaries emit crossing events; polygon zones emit enter and exit events as tracks move through the marked shape.",
  },
  regions: {
    title: "Detection regions gate the analytics still",
    description:
      "Include polygons keep detections eligible in the operating area; exclusion polygons suppress noisy pockets before events run.",
    caption:
      "Include keeps detections eligible inside operating space; exclude suppresses noisy motion before event boundaries run.",
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
            <text x="292" y="66" textAnchor="middle" fill="#c5e9ff" fontSize="10">
              polygon event zone
            </text>
            <text x="294" y="116" textAnchor="middle" fill="#eef9ff" fontSize="9">
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
            <text x="146" y="166" textAnchor="middle" fill="#bcefe3" fontSize="10">
              line crossing
            </text>
            <text x="164" y="112" textAnchor="middle" fill="#effff9" fontSize="9">
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
            <text x="154" y="54" textAnchor="middle" fill="#c8f7d6" fontSize="10">
              include detection area
            </text>
            <text x="144" y="112" textAnchor="middle" fill="#f0fff6" fontSize="9">
              include keeps detections eligible
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
            <text x="310" y="68" textAnchor="middle" fill="#ffd9a1" fontSize="10">
              exclusion mask
            </text>
            <text x="310" y="150" textAnchor="middle" fill="#fff1d6" fontSize="9">
              exclude suppresses noisy motion
            </text>
          </g>
        ) : null}

        <g opacity="0.95">
          <rect x="206" y="84" width="42" height="24" rx="6" fill="#c5d6e8" />
          <circle cx="216" cy="112" r="5" fill="#08111a" />
          <circle cx="238" cy="112" r="5" fill="#08111a" />
          <circle cx="118" cy="128" r="7" fill="#ffc978" />
          <line x1="118" x2="118" y1="135" y2="158" stroke="#ffc978" strokeWidth="3" />
          <line x1="106" x2="130" y1="150" y2="150" stroke="#ffc978" strokeWidth="3" />
        </g>
      </svg>
      <figcaption className="mt-2 text-xs leading-5 text-[#9fb2cf]">
        {copy.caption}
      </figcaption>
    </figure>
  );
}
