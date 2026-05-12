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
    <article className="rounded-[0.8rem] border border-white/8 bg-white/[0.03] px-3 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8ea4c7]">
          {formatPatternType(pattern.pattern_type)}
        </span>
        <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#d8e2f2]">
          {pattern.severity}
        </span>
      </div>
      <p className="mt-2 text-sm text-[#eef4ff]">{pattern.summary}</p>
      <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
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
    </article>
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
