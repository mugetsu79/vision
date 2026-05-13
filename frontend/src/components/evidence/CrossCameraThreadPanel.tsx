import type { components } from "@/lib/api.generated";

type CrossCameraThread =
  components["schemas"]["CrossCameraThreadResponse"];

export function CrossCameraThreadPanel({
  threads,
  loading = false,
}: {
  threads?: CrossCameraThread[] | null;
  loading?: boolean;
}) {
  const visibleThreads = threads ?? [];

  return (
    <section
      data-testid="cross-camera-thread-panel"
      aria-label="Cross-camera context"
      className="border-t border-white/8 px-4 py-3"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
            Cross-camera context
          </h4>
          <p className="mt-1 text-sm font-semibold text-[#eef4ff]">
            {loading
              ? "Loading"
              : visibleThreads.length
                ? `${visibleThreads.length} thread${visibleThreads.length === 1 ? "" : "s"}`
                : "No cross-camera context"}
          </p>
        </div>
      </div>

      {visibleThreads.length ? (
        <div className="mt-3 space-y-3">
          {visibleThreads.map((thread) => (
            <ThreadCard key={thread.id} thread={thread} />
          ))}
        </div>
      ) : (
        <p className="mt-2 text-xs text-[#8fa4c4]">
          {loading
            ? "Loading cross-camera context."
            : "Identity-light correlation only; no matching context for this evidence record."}
        </p>
      )}
    </section>
  );
}

function ThreadCard({ thread }: { thread: CrossCameraThread }) {
  return (
    <article className="rounded-md border border-white/8 bg-white/[0.03] px-3 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-[#eef4ff]">
          {Math.round(thread.confidence * 100)}% confidence
        </span>
        <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#d8e2f2]">
          {hashPrefix(thread.thread_hash)}
        </span>
      </div>

      <PrivacyLabels labels={thread.privacy_labels} />
      <SignalGrid thread={thread} />
      <RationaleList rationale={thread.rationale} />
      <CitationChips
        label="Source incidents"
        values={thread.source_incident_ids.map(shortUuid)}
      />
      <CitationChips
        label="Manifest hashes"
        values={thread.privacy_manifest_hashes.map(hashPrefix)}
      />
    </article>
  );
}

function SignalGrid({ thread }: { thread: CrossCameraThread }) {
  const signals = thread.signals as Record<string, unknown>;
  const facts = [
    ["Class", stringSignal(signals.class_name)],
    ["Zone", stringSignal(signals.zone_id)],
    ["Direction", stringSignal(signals.direction)],
  ].filter((fact): fact is [string, string] => Boolean(fact[1]));

  if (!facts.length) {
    return null;
  }

  return (
    <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
      {facts.map(([label, value]) => (
        <ThreadFact key={label} label={label} value={value} />
      ))}
    </dl>
  );
}

function RationaleList({ rationale }: { rationale: string[] }) {
  if (!rationale.length) {
    return null;
  }

  return (
    <ul className="mt-3 space-y-1 text-xs text-[#c7d6ee]">
      {rationale.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function PrivacyLabels({ labels }: { labels: string[] }) {
  if (!labels.length) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {labels.map((label) => (
        <span
          key={label}
          className="rounded-full border border-[#315675] bg-[#092132] px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#aee6ff]"
        >
          {label}
        </span>
      ))}
    </div>
  );
}

function ThreadFact({ label, value }: { label: string; value: string }) {
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

function stringSignal(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function hashPrefix(hash: string | null | undefined): string {
  return hash ? hash.slice(0, 12) : "Not recorded";
}

function shortUuid(value: string): string {
  return value.slice(0, 13);
}
