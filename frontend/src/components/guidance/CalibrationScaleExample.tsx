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
        <title id={titleId}>Calibrated span measured distance example</title>
        <desc id={descId}>
          A camera still and a drawn top-down world plane show the same known
          mark-to-mark span used as the D1 to D2 measured distance.
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
          <path
            d="M78 212 L306 229 M82 176 L300 192 M88 140 L294 156"
            stroke="#4d7cad"
            strokeDasharray="6 8"
            strokeWidth="1.5"
            opacity="0.58"
          />
          <path
            d="M98 222 L96 112 M164 228 L158 106 M224 236 L212 100 M288 240 L274 94"
            stroke="#86bfff"
            strokeDasharray="7 8"
            strokeWidth="1.5"
            opacity="0.62"
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
          <text x="94" y="205" fill="#9ef8e7" fontSize="12" fontWeight="700">
            known physical span
          </text>
          <path
            d="M74 222 L74 206 M174 229 L174 213"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="3"
          />
          <circle cx="74" cy="222" r="5" fill="#9ef8e7" />
          <circle cx="174" cy="229" r="5" fill="#9ef8e7" />
          <path
            d="M120 146 C164 128 208 136 252 116"
            fill="none"
            stroke="#9fb2cf"
            strokeDasharray="7 8"
            strokeLinecap="round"
            strokeWidth="2"
            opacity="0.62"
          />
          <circle cx="206" cy="132" r="13" fill="#c5d6e8" opacity="0.13" />
          <circle cx="206" cy="132" r="4.5" fill="#f4f8ff" stroke="#08111a" strokeWidth="1.5" />

          <SourcePoint label="S1" x={74} y={222} />
          <SourcePoint label="S2" x={174} y={229} />
          <SourcePoint label="S3" x={288} y={92} />
          <SourcePoint label="S4" x={98} y={112} />
        </g>

        <g aria-label="Drawn world plane destination points">
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
            Drawn world plane
          </text>
          <text x="420" y="78" fill="#aa9ad8" fontSize="12">
            Operator sketch D1-D4
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
            d="M503 106 L503 236 M565 106 L565 236 M628 106 L628 236 M440 150 L690 150 M440 193 L690 193"
            stroke="#342a55"
            strokeWidth="2"
          />
          <path
            d="M485 142 C528 124 584 136 640 118"
            fill="none"
            stroke="#9fb2cf"
            strokeDasharray="7 8"
            strokeLinecap="round"
            strokeWidth="2"
            opacity="0.62"
          />
          <rect x="522" y="126" width="48" height="24" rx="12" fill="#c5d6e8" opacity="0.13" />
          <circle cx="546" cy="138" r="4.5" fill="#f4f8ff" stroke="#08111a" strokeWidth="1.5" />

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
          <circle cx="440" cy="236" r="5" fill="#9ef8e7" />
          <circle cx="690" cy="236" r="5" fill="#9ef8e7" />
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
          Example: known reference span = 2.5 m. Put S1 and S2 on two fixed
          marks you physically measured, draw those same marks as D1 and D2,
          then enter 2.5.
        </p>
        <div className={`mt-2 grid gap-2 ${compact ? "" : "sm:grid-cols-3"}`}>
          <p>
            S points are camera pixels. They show where each physical mark
            appears in the still.
          </p>
          <p>
            D points are a top-down sketch. Their coordinates are the world
            plane you draw. The destination plane is drawn by you, not captured
            from another camera still.
          </p>
          <p>
            S1 is D1 and S2 is D2 because they are the same physical reference
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
        data-reference-mark={label.toLowerCase()}
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
        data-reference-mark={label.toLowerCase()}
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
