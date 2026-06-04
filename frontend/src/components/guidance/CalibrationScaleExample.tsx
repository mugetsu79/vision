import { useId } from "react";

type CalibrationScaleExampleProps = {
  compact?: boolean;
};

const SVG_FONT_FAMILY =
  'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

export function CalibrationScaleExample({
  compact = false,
}: CalibrationScaleExampleProps) {
  const descId = useId();

  return (
    <figure
      className={`overflow-hidden rounded-[1rem] border border-white/10 bg-[#07101b] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${
        compact ? "" : "mt-4"
      }`}
    >
      <svg
        aria-describedby={descId}
        aria-label="Calibrated span measured distance example"
        className="block h-auto w-full"
        height="360"
        role="img"
        shapeRendering="geometricPrecision"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 760 360"
        width="760"
      >
        <desc id={descId}>
          A camera still and a drawn top-down world plane show the same known
          mark-to-mark span used as the D1 to D2 measured distance.
        </desc>

        <rect width="760" height="360" fill="#050b13" />

        <g aria-label="Camera still source points">
          <rect
            x="24"
            y="28"
            width="340"
            height="248"
            rx="18"
            fill="#081421"
            stroke="#284066"
          />
          <text
            x="48"
            y="58"
            fill="#f4f8ff"
            fontFamily={SVG_FONT_FAMILY}
            fontSize="16"
            fontWeight="700"
          >
            1 Camera still
          </text>
          <text
            x="48"
            y="78"
            fill="#8ea4c7"
            fontFamily={SVG_FONT_FAMILY}
            fontSize="12"
          >
            Source pixels S1-S4
          </text>

          <polygon
            points="70,224 328,238 304,92 104,106"
            fill="#122339"
            stroke="#5ea8ff"
            strokeWidth="2"
          />
          <path
            d="M84 204 L314 216 M88 166 L310 178 M94 130 L306 142 M112 218 L112 112 M178 222 L170 104 M244 228 L232 98"
            fill="none"
            stroke="#4d7cad"
            strokeDasharray="6 8"
            strokeWidth="1.4"
            opacity="0.58"
          />
          <path
            d="M92 220 L202 224"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="5"
          />
          <path
            d="M92 220 L92 205 M202 224 L202 209"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="3"
          />
          <text
            x="147"
            y="203"
            fill="#9ef8e7"
            fontFamily={SVG_FONT_FAMILY}
            fontSize="12"
            fontWeight="700"
            textAnchor="middle"
          >
            measured physical span
          </text>

          <SourcePoint label="S1" x={92} y={220} />
          <SourcePoint label="S2" x={202} y={224} />
          <SourcePoint label="S3" x={316} y={94} />
          <SourcePoint label="S4" x={104} y={106} />
        </g>

        <g aria-label="Drawn world plane destination points">
          <rect
            x="396"
            y="28"
            width="340"
            height="248"
            rx="18"
            fill="#0a1020"
            stroke="#3e3566"
          />
          <text
            x="420"
            y="58"
            fill="#f4f8ff"
            fontFamily={SVG_FONT_FAMILY}
            fontSize="16"
            fontWeight="700"
          >
            Drawn world plane
          </text>
          <text
            x="420"
            y="78"
            fill="#aa9ad8"
            fontFamily={SVG_FONT_FAMILY}
            fontSize="12"
          >
            Operator sketch D1-D4
          </text>

          <rect
            x="430"
            y="106"
            width="240"
            height="130"
            rx="8"
            fill="#17142a"
            stroke="#a985ff"
            strokeWidth="2"
          />
          <path
            d="M490 106 L490 236 M550 106 L550 236 M610 106 L610 236 M430 150 L670 150 M430 193 L670 193"
            fill="none"
            stroke="#342a55"
            strokeWidth="2"
          />
          <path
            d="M430 236 L670 236"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="5"
          />
          <path
            d="M430 250 L670 250 M430 240 L430 260 M670 240 L670 260"
            stroke="#6ce3d0"
            strokeLinecap="round"
            strokeWidth="3"
          />
          <text
            x="550"
            y="268"
            fill="#9ef8e7"
            fontFamily={SVG_FONT_FAMILY}
            fontSize="13"
            fontWeight="700"
            textAnchor="middle"
          >
            D1-D2 = measured meters
          </text>

          <DestinationPoint label="D1" x={430} y={236} />
          <DestinationPoint label="D2" x={670} y={236} />
          <DestinationPoint label="D3" x={670} y={106} />
          <DestinationPoint label="D4" x={430} y={106} />
        </g>

        <g aria-label="Mapping explanation">
          <path
            data-calibration-link="s1-d1"
            d="M92 220 C214 304 336 304 430 236"
            fill="none"
            stroke="#6ce3d0"
            strokeDasharray="8 8"
            strokeLinecap="round"
            strokeWidth="2"
          />
          <path
            data-calibration-link="s2-d2"
            d="M202 224 C350 328 514 328 670 236"
            fill="none"
            stroke="#6ce3d0"
            strokeDasharray="8 8"
            strokeLinecap="round"
            strokeWidth="2"
            opacity="0.66"
          />
        </g>

        <g aria-label="Calibration rules">
          <RuleChip x={40} text="S1 = D1; S2 = D2" />
          <RuleChip x={280} text="Coordinates can differ" />
          <RuleChip x={520} text="Enter the real D1-D2 span" />
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

function RuleChip({ text, x }: { text: string; x: number }) {
  return (
    <g>
      <rect
        x={x}
        y="302"
        width="200"
        height="34"
        rx="10"
        fill="#0c1522"
        stroke="#253a5b"
      />
      <text
        x={x + 100}
        y="323"
        fill="#c8d7ee"
        fontFamily={SVG_FONT_FAMILY}
        fontSize="12"
        fontWeight="700"
        textAnchor="middle"
      >
        {text}
      </text>
    </g>
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
        fontFamily={SVG_FONT_FAMILY}
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
        fontFamily={SVG_FONT_FAMILY}
        fontSize="14"
        fontWeight="700"
        textAnchor="middle"
      >
        {label}
      </text>
    </g>
  );
}
