import { omniEmptyStates, omniLabels } from "@/copy/omnisight";

export function DynamicStats({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort(
      (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
    );

  return (
    <section className="overflow-hidden rounded-[1rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,15,24,0.98),rgba(5,8,13,0.96))]">
      <div className="border-b border-white/8 px-5 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">
          {omniLabels.signalsInViewTitle}
        </p>
        <h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">
          Live signals in view.
        </h3>
      </div>

      <div className="grid gap-3 px-5 py-5">
        {entries.length === 0 ? (
          <p className="text-sm text-[#8ca2c5]">{omniEmptyStates.noSignals}</p>
        ) : (
          entries.map(([className, count]) => (
            <div
              key={className}
              className="rounded-[0.85rem] border border-white/8 bg-[linear-gradient(180deg,rgba(14,24,39,0.98),rgba(8,14,23,0.98))] px-4 py-3"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#88a3cc]">
                {className}
              </p>
              <p className="mt-2 text-2xl font-semibold text-[#f3f7ff]">
                {count}
              </p>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
