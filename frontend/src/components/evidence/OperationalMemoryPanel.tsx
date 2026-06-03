import type { components } from "@/lib/api.generated";

type OperationalMemoryPattern =
  components["schemas"]["OperationalMemoryPatternResponse"];

export function OperationalMemoryPanel({
  patterns,
  loading = false,
  compact = false,
}: {
  patterns?: OperationalMemoryPattern[] | null;
  loading?: boolean;
  compact?: boolean;
}) {
  const visiblePatterns = patterns ?? [];

  return (
    <section
      data-testid="operational-memory-panel"
      aria-label="Observed operational patterns"
      className={
        compact
          ? "mt-3 border-t border-white/8 pt-3"
          : "border-t border-white/8 px-4 py-3"
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
            Observed patterns
          </h4>
          <p className="mt-1 text-sm font-semibold text-[#eef4ff]">
            {loading
              ? "Loading"
              : visiblePatterns.length
                ? `${visiblePatterns.length} active`
                : "No observed patterns"}
          </p>
        </div>
      </div>

      {visiblePatterns.length ? (
        <div className="mt-3 space-y-3">
          {visiblePatterns.map((pattern) => (
            <MemoryPatternCard key={pattern.id} pattern={pattern} />
          ))}
        </div>
      ) : (
        <p className="mt-2 text-xs text-[#8fa4c4]">
          {loading
            ? "Loading observed operational patterns."
            : "No observed patterns for this context."}
        </p>
      )}
    </section>
  );
}

function MemoryPatternCard({ pattern }: { pattern: OperationalMemoryPattern }) {
  const sourceIncidentIds = pattern.source_incident_ids ?? [];
  const sourceContractHashes = pattern.source_contract_hashes ?? [];

  return (
    <article className="grid gap-3 rounded-[0.8rem] border border-white/8 bg-white/[0.03] px-3 py-3">
      <MemoryPatternGlyph pattern={pattern} />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8ea4c7]">
            {formatPatternType(pattern.pattern_type)}
          </span>
          <span className={severityBadgeClass(pattern.severity)}>
            {pattern.severity}
          </span>
        </div>
        <p className="mt-2 text-sm text-[#eef4ff]">{pattern.summary}</p>
        <dl className="mt-3 grid gap-2 text-xs">
          <MemoryFact
            label="Window"
            value={`${formatMemoryDate(pattern.window_started_at)} - ${formatMemoryDate(
              pattern.window_ended_at,
            )}`}
          />
          <MemoryFact label="Pattern" value={hashPrefix(pattern.pattern_hash)} />
          <MemoryFact
            label="Source incidents"
            value={`${sourceIncidentIds.length} cited`}
          />
          <MemoryFact
            label="Contract hashes"
            value={`${sourceContractHashes.length} cited`}
          />
        </dl>
        <CitationChips
          label="Source incidents"
          values={sourceIncidentIds.map(shortUuid)}
        />
        <CitationChips
          label="Contract hashes"
          values={sourceContractHashes.map(hashPrefix)}
        />
      </div>
    </article>
  );
}

function MemoryPatternGlyph({
  pattern,
}: {
  pattern: OperationalMemoryPattern;
}) {
  const patternSlug = slugPatternType(pattern.pattern_type);
  const label = formatPatternType(pattern.pattern_type);
  const count = readPatternCount(pattern);
  const tone = pattern.severity === "critical" ? "#ff6f9d" : "#f7c56b";

  return (
    <svg
      aria-label={`${label} pattern`}
      className="h-20 w-full rounded-[0.7rem] border border-white/8 bg-[#050b13] text-[#dce6f7] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
      data-testid={`pattern-glyph-${patternSlug}`}
      role="img"
      viewBox="0 0 96 72"
    >
      <title>{label} pattern</title>
      <rect x="10" y="10" width="76" height="52" rx="10" fill="rgba(255,255,255,0.03)" />
      {renderPatternGlyphBody(patternSlug, tone, count)}
      <text
        x="48"
        y="60"
        fill="#eef4ff"
        fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
        fontSize="10"
        fontWeight="700"
        textAnchor="middle"
      >
        {count}
      </text>
    </svg>
  );
}

function renderPatternGlyphBody(
  patternSlug: string,
  tone: string,
  count: number,
) {
  if (patternSlug === "zone-hotspot") {
    const heat = Math.min(4, Math.max(2, Math.ceil(count / 2)));
    return (
      <>
        <path
          d="M24 22 L72 18 L78 42 L30 48 Z"
          fill="rgba(110,189,255,0.08)"
          stroke="rgba(206,224,255,0.22)"
          strokeWidth="1.2"
        />
        {Array.from({ length: heat }).map((_, index) => (
          <circle
            key={index}
            cx={48 + index * 3}
            cy={33 + index}
            r={18 - index * 4}
            fill="none"
            opacity={0.2 + index * 0.16}
            stroke={tone}
            strokeWidth="1.4"
          />
        ))}
        <circle cx="51" cy="35" r="4" fill={tone} opacity="0.9" />
      </>
    );
  }

  if (patternSlug === "storage-failure") {
    return (
      <>
        <path
          d="M18 38 H34 M62 38 H78"
          stroke="rgba(206,224,255,0.26)"
          strokeLinecap="round"
          strokeWidth="2"
        />
        <path
          d="M38 32 L46 44 M50 32 L58 44"
          stroke={tone}
          strokeLinecap="round"
          strokeWidth="2.4"
        />
        {[22, 78].map((x) => (
          <circle
            key={x}
            cx={x}
            cy="38"
            r="6"
            fill="rgba(255,255,255,0.04)"
            stroke="rgba(206,224,255,0.28)"
            strokeWidth="1.2"
          />
        ))}
        <rect
          x="38"
          y="22"
          width="20"
          height="8"
          rx="3"
          fill={tone}
          opacity="0.18"
        />
      </>
    );
  }

  const pulses = Math.min(5, Math.max(3, count));
  return (
    <>
      <path
        d="M16 42 H80"
        stroke="rgba(206,224,255,0.2)"
        strokeLinecap="round"
        strokeWidth="1.4"
      />
      {Array.from({ length: pulses }).map((_, index) => {
        const x = 22 + index * (52 / Math.max(1, pulses - 1));
        const radius = 3 + Math.min(index, 2);
        return (
          <g key={index}>
            <line
              x1={x}
              x2={x}
              y1={42 - radius * 3}
              y2="42"
              stroke={tone}
              strokeLinecap="round"
              strokeWidth="1.6"
              opacity={0.55 + index * 0.08}
            />
            <circle
              cx={x}
              cy={42 - radius * 3}
              r={radius}
              fill={tone}
              opacity={0.34 + index * 0.1}
            />
          </g>
        );
      })}
    </>
  );
}

function MemoryFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
        {label}
      </dt>
      <dd className="mt-1 truncate text-[#d8e2f2]" title={value}>
        {value}
      </dd>
    </div>
  );
}

function CitationChips({ label, values }: { label: string; values: string[] }) {
  if (!values.length) {
    return null;
  }
  return (
    <div className="mt-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
        {label}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {values.map((value) => (
          <span
            key={`${label}-${value}`}
            className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-[#aebfde]"
          >
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}

function formatPatternType(value: string): string {
  return value.replaceAll("_", " ");
}

function severityBadgeClass(severity: OperationalMemoryPattern["severity"]): string {
  const base =
    "rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em]";
  if (severity === "critical") {
    return `${base} border-[#6f2d3b] bg-[#2a0d16] text-[#ffd8e1]`;
  }
  return `${base} border-white/10 text-[#d8e2f2]`;
}

function slugPatternType(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function readPatternCount(pattern: OperationalMemoryPattern): number {
  const evidence = pattern.evidence ?? {};
  const dimensions = pattern.dimensions ?? {};
  return (
    readNumber(evidence.incident_count) ??
    readNumber(evidence.artifact_count) ??
    readNumber(dimensions.contract_count) ??
    pattern.source_incident_ids?.length ??
    0
  );
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function hashPrefix(hash: string | null | undefined): string {
  return hash ? hash.slice(0, 12) : "Not recorded";
}

function shortUuid(value: string): string {
  const parts = value.split("-");
  if (parts.length < 5) {
    return value.slice(0, 12);
  }
  return `${parts[0]}-${parts[4].slice(-4)}`;
}

function formatMemoryDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
