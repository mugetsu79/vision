import type { Incident } from "@/hooks/use-incidents";

import { buildEvidenceTimelineBuckets } from "./evidence-signals";

export function EvidenceTimeline({
  incidents,
  selectedIncidentId,
  onSelect,
}: {
  incidents: Incident[];
  selectedIncidentId: string | null;
  onSelect: (incidentId: string) => void;
}) {
  const buckets = buildEvidenceTimelineBuckets(incidents, selectedIncidentId);

  if (buckets.length === 0) {
    return null;
  }

  return (
    <nav
      aria-label="Evidence timeline"
      data-testid="evidence-timeline"
      className="rounded-[0.75rem] border border-white/10 bg-[#07101b] px-4 py-3"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-[#eef4ff]">
          Evidence timeline
        </h2>
        <p className="text-xs text-[#8ea8cf]">
          {incidents.length} {incidents.length === 1 ? "record" : "records"}
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-4 xl:grid-cols-8">
        {buckets.map((bucket) => (
          <button
            key={bucket.id}
            type="button"
            onClick={() => onSelect(bucket.selectableIncidentId)}
            className={`min-h-20 rounded-md border px-3 py-2 text-left transition ${
              bucket.selected
                ? "border-[#76e0ff] bg-[#0d2232] text-white"
                : "border-white/10 bg-white/[0.025] text-[#c8d6eb] hover:bg-white/[0.055]"
            }`}
            style={{ borderTopColor: bucket.accent }}
          >
            <span className="block text-sm font-semibold">{bucket.label}</span>
            <span className="mt-1 block text-xs text-[#91a6c5]">
              {bucket.count} {bucket.count === 1 ? "record" : "records"}
            </span>
            <span className="mt-2 block truncate text-[11px] uppercase tracking-[0.14em] text-[#7894bd]">
              {bucket.dominantType}
            </span>
            {bucket.selected ? (
              <span className="mt-1 block text-[11px] font-semibold text-[#76e0ff]">
                Selected
              </span>
            ) : null}
          </button>
        ))}
      </div>
    </nav>
  );
}
