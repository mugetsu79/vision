import { useId } from "react";

type CalibrationFlowIllustrationProps = {
  mode?: "source-destination" | "boundaries" | "regions";
  animated?: boolean;
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
    title: "Event boundaries belong on the calibrated plane",
    description:
      "Four mapped calibration points anchor the top-down plane, then an event line is placed across the measured movement path.",
    caption:
      "Draw event lines or zones after calibration so crossings are measured in the same mapped plane.",
  },
  regions: {
    title: "Detection regions refine the calibrated plane",
    description:
      "Four mapped calibration points anchor the top-down plane, then include and exclusion regions limit where detections count.",
    caption:
      "Use include regions for valid operating space and exclusion regions for dead zones or irrelevant motion.",
  },
} satisfies Record<
  NonNullable<CalibrationFlowIllustrationProps["mode"]>,
  { title: string; description: string; caption: string }
>;

export function CalibrationFlowIllustration({
  mode = "source-destination",
  animated = true,
}: CalibrationFlowIllustrationProps) {
  const idPrefix = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const sourcePlaneId = `${idPrefix}-source-plane`;
  const destinationPlaneId = `${idPrefix}-destination-plane`;
  const copy = illustrationCopy[mode];

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

        {mode === "boundaries" ? (
          <g>
            <line x1="276" x2="328" y1="104" y2="104" stroke="#6fe0c5" strokeWidth="4" />
            <text x="302" y="94" textAnchor="middle" fill="#bcefe3" fontSize="10">
              event line
            </text>
          </g>
        ) : null}

        {mode === "regions" ? (
          <g>
            <rect
              data-region="include"
              x="284"
              y="96"
              width="48"
              height="38"
              rx="8"
              fill="#6fe0c5"
              opacity="0.18"
              stroke="#6fe0c5"
              strokeWidth="1.5"
            />
            <text x="308" y="88" textAnchor="middle" fill="#bcefe3" fontSize="10">
              include region
            </text>
            <rect
              data-region="exclusion"
              x="318"
              y="108"
              width="30"
              height="28"
              rx="6"
              fill="#ffb86b"
              opacity="0.18"
              stroke="#ffb86b"
              strokeWidth="1.5"
            />
            <text x="333" y="148" textAnchor="middle" fill="#ffd9a1" fontSize="10">
              exclusion region
            </text>
          </g>
        ) : null}
      </svg>
      <figcaption className="mt-2 text-xs leading-5 text-[#9fb2cf]">
        {copy.caption}
      </figcaption>
    </figure>
  );
}
