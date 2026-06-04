import { useId } from "react";

type CalibrationScaleExampleProps = {
  compact?: boolean;
};

export function CalibrationScaleExample({
  compact = false,
}: CalibrationScaleExampleProps) {
  const titleId = useId();
  const descId = useId();

  return (
    <figure
      className={`overflow-hidden rounded-[1rem] border border-white/10 bg-[#07101b] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${
        compact ? "" : "mt-4"
      }`}
    >
      <svg
        aria-labelledby={`${titleId} ${descId}`}
        className="block h-auto w-full"
        role="img"
        viewBox="0 0 760 360"
      >
        <title id={titleId}>Parking bay measured distance example</title>
        <desc id={descId}>
          A street camera view and a top-down world plane show the same parking
          bay width used as the D1 to D2 measured distance.
        </desc>

        <rect width="760" height="360" fill="#050b13" />

        <g aria-label="Camera still source points">
          <rect
            x="26"
            y="28"
            width="338"
            height="246"
            rx="18"
            fill="#081421"
            stroke="#284066"
          />
          <text x="50" y="58" fill="#f4f8ff" fontSize="16" fontWeight="700">
            Camera still
          </text>
          <text x="50" y="78" fill="#8ea4c7" fontSize="12">
            Source pixels S1-S4
          </text>

          <polygon
            points="62,232 330,250 302,86 91,104"
            fill="#122339"
            stroke="#5ea8ff"
            strokeWidth="2"
          />
          <polygon
            points="74,222 174,229 165,106 98,112"
            fill="#22324a"
            opacity="0.72"
            stroke="#86bfff"
            strokeDasharray="7 7"
            strokeWidth="1.5"
          />
          <polygon
            points="174,229 318,240 288,92 165,106"
            fill="#17283d"
            opacity="0.82"
            stroke="#86bfff"
            strokeDasharray="7 7"
            strokeWidth="1.5"
          />
          <path
            d="M122 226 L115 110"
            stroke="#e7edf8"
            strokeDasharray="12 9"
            strokeLinecap="round"
            strokeWidth="4"
          />
          <path
            d="M226 235 L210 101"
            stroke="#e7edf8"
            strokeDasharray="12 9"
            strokeLinecap="round"
            strokeWidth="4"
            opacity="0.88"
          />
          <path
            d="M74 222 L174 229"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="5"
          />
          <text x="84" y="212" fill="#9ef8e7" fontSize="12" fontWeight="700">
            measure this real span
          </text>

          <g transform="translate(246 153) rotate(-6)">
            <rect
              x="0"
              y="0"
              width="58"
              height="26"
              rx="7"
              fill="#c9d7e9"
              opacity="0.92"
            />
            <rect x="9" y="5" width="20" height="10" rx="3" fill="#42566f" />
            <circle cx="14" cy="27" r="5" fill="#07101b" />
            <circle cx="47" cy="27" r="5" fill="#07101b" />
          </g>
          <g transform="translate(201 187)">
            <circle cx="0" cy="0" r="7" fill="#f3c68b" />
            <path
              d="M0 7 L0 26 M0 14 L-10 23 M0 14 L10 23"
              stroke="#f3c68b"
              strokeLinecap="round"
              strokeWidth="4"
            />
          </g>

          <SourcePoint label="S1" x={74} y={222} />
          <SourcePoint label="S2" x={174} y={229} />
          <SourcePoint label="S3" x={288} y={92} />
          <SourcePoint label="S4" x={98} y={112} />
        </g>

        <g aria-label="World plane destination points">
          <rect
            x="396"
            y="28"
            width="338"
            height="246"
            rx="18"
            fill="#0a1020"
            stroke="#3e3566"
          />
          <text x="420" y="58" fill="#f4f8ff" fontSize="16" fontWeight="700">
            World plane
          </text>
          <text x="420" y="78" fill="#aa9ad8" fontSize="12">
            Top-down destination sketch
          </text>

          <rect
            x="440"
            y="106"
            width="250"
            height="130"
            rx="8"
            fill="#17142a"
            stroke="#a985ff"
            strokeWidth="2"
          />
          <path
            d="M503 106 L503 236 M565 106 L565 236 M628 106 L628 236"
            stroke="#342a55"
            strokeWidth="2"
          />
          <path
            d="M440 171 L690 171"
            stroke="#e7edf8"
            strokeDasharray="13 10"
            strokeLinecap="round"
            strokeWidth="4"
            opacity="0.9"
          />
          <rect x="488" y="128" width="64" height="32" rx="9" fill="#c9d7e9" />
          <rect x="496" y="135" width="24" height="12" rx="3" fill="#42566f" />
          <circle cx="502" cy="163" r="5" fill="#07101b" />
          <circle cx="540" cy="163" r="5" fill="#07101b" />
          <circle cx="606" cy="210" r="7" fill="#f3c68b" />
          <path
            d="M606 217 L606 235 M606 224 L595 232 M606 224 L617 232"
            stroke="#f3c68b"
            strokeLinecap="round"
            strokeWidth="4"
          />

          <path
            d="M440 236 L690 236"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="5"
          />
          <path
            d="M440 250 L690 250"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="3"
          />
          <path
            d="M440 240 L440 260 M690 240 L690 260"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="4"
          />
          <text
            x="565"
            y="268"
            fill="#9ef8e7"
            fontSize="13"
            fontWeight="700"
            textAnchor="middle"
          >
            D1-D2 = 2.5 m
          </text>

          <DestinationPoint label="D1" x={440} y={236} />
          <DestinationPoint label="D2" x={690} y={236} />
          <DestinationPoint label="D3" x={690} y={106} />
          <DestinationPoint label="D4" x={440} y={106} />
        </g>

        <g aria-label="Mapping explanation">
          <path
            data-calibration-link="s1-d1"
            d="M74 222 C230 310 330 310 440 236"
            fill="none"
            stroke="#6ce3d0"
            strokeDasharray="8 8"
            strokeLinecap="round"
            strokeWidth="2"
          />
          <path
            data-calibration-link="s2-d2"
            d="M174 229 C330 334 500 334 690 236"
            fill="none"
            stroke="#6ce3d0"
            strokeDasharray="8 8"
            strokeLinecap="round"
            strokeWidth="2"
            opacity="0.65"
          />
        </g>
      </svg>

      <figcaption className="border-t border-white/10 p-3 text-xs leading-5 text-[#9eb2cf]">
        <p className="font-semibold text-[#f4f8ff]">
          Example: parking bay width = 2.5 m. Put S1 and S2 on the two painted
          bay corners, draw those same corners as D1 and D2, then enter 2.5.
        </p>
        <div className={`mt-2 grid gap-2 ${compact ? "" : "sm:grid-cols-3"}`}>
          <p>
            S points are camera pixels. They show where each physical mark
            appears in the still.
          </p>
          <p>
            D points are a top-down sketch. Their coordinates are the world
            plane you draw.
          </p>
          <p>
            S1 is D1 and S2 is D2 because they are the same physical floor
            marks. The coordinates do not need to match.
          </p>
        </div>
        <p className="mt-2 text-[#8ea4c7]">
          Use the current analytics still to pick the marks; the distance is the
          real span between the two physical marks.
        </p>
      </figcaption>
    </figure>
  );
}

function SourcePoint({ label, x, y }: { label: string; x: number; y: number }) {
  return (
    <g>
      <circle
        cx={x}
        cy={y}
        fill="#071b2f"
        r="17"
        stroke="#6cb0ff"
        strokeWidth="3"
      />
      <text
        x={x}
        y={y + 5}
        fill="#f4f8ff"
        fontSize="14"
        fontWeight="700"
        textAnchor="middle"
      >
        {label}
      </text>
    </g>
  );
}

function DestinationPoint({
  label,
  x,
  y,
}: {
  label: string;
  x: number;
  y: number;
}) {
  return (
    <g>
      <circle
        cx={x}
        cy={y}
        fill="#1a1430"
        r="17"
        stroke="#b28fff"
        strokeWidth="3"
      />
      <text
        x={x}
        y={y + 5}
        fill="#f7f2ff"
        fontSize="14"
        fontWeight="700"
        textAnchor="middle"
      >
        {label}
      </text>
    </g>
  );
}
