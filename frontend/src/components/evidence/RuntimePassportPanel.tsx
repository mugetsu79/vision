import type { components } from "@/lib/api.generated";

type RuntimePassportSummary = components["schemas"]["RuntimePassportSummary"];
type RuntimePassportSnapshot =
  components["schemas"]["RuntimePassportSnapshotResponse"];

export function RuntimePassportPanel({
  summary,
  snapshot,
  loading = false,
  compact = false,
}: {
  summary?: RuntimePassportSummary | null;
  snapshot?: RuntimePassportSnapshot | null;
  loading?: boolean;
  compact?: boolean;
}) {
  const passport = snapshot?.summary ?? summary ?? null;
  const providerVersions = passport?.provider_versions
    ? Object.entries(passport.provider_versions)
    : [];

  return (
    <section
      data-testid="runtime-passport-panel"
      aria-label="Runtime passport"
      className={
        compact
          ? "mt-3 border-t border-white/8 pt-3"
          : "border-t border-white/8 px-4 py-3"
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
            Runtime passport
          </h4>
          <p className="mt-1 text-sm font-semibold text-[#eef4ff]">
            {passport?.selected_backend ?? (loading ? "Loading" : "Not attached")}
          </p>
        </div>
        {passport?.fallback_reason ? (
          <span className="rounded-full border border-amber-300/35 bg-amber-950/30 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-amber-100">
            Fallback
          </span>
        ) : null}
      </div>

      {passport ? (
        <>
          <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
            <RuntimeFact label="Model hash" value={hashPrefix(passport.model_hash)} />
            <RuntimeFact
              label="Artifact hash"
              value={hashPrefix(passport.runtime_artifact_hash)}
            />
            <RuntimeFact
              label="Target profile"
              value={passport.target_profile ?? "Dynamic runtime"}
            />
            <RuntimeFact label="Precision" value={passport.precision ?? "Default"} />
            <RuntimeFact
              label="Validated"
              value={formatRuntimeDate(passport.validated_at)}
            />
            <RuntimeFact
              label="Profile"
              value={
                passport.runtime_selection_profile_name ??
                hashPrefix(passport.runtime_selection_profile_hash)
              }
            />
            <RuntimeFact
              label="Fallback reason"
              value={passport.fallback_reason ?? "None"}
            />
            <RuntimeFact
              label="Passport"
              value={hashPrefix(passport.passport_hash)}
            />
          </dl>
          {providerVersions.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {providerVersions.map(([name, version]) => (
                <span
                  key={name}
                  className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-[#aebfde]"
                >
                  {name} {String(version)}
                </span>
              ))}
            </div>
          ) : null}
        </>
      ) : (
        <p className="mt-2 text-xs text-[#8fa4c4]">
          {loading ? "Loading runtime metadata." : "No runtime metadata attached."}
        </p>
      )}
    </section>
  );
}

function RuntimeFact({ label, value }: { label: string; value: string }) {
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

function hashPrefix(hash: string | null | undefined): string {
  return hash ? hash.slice(0, 12) : "Not recorded";
}

function formatRuntimeDate(value: string | null | undefined): string {
  if (!value) {
    return "Not validated";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
