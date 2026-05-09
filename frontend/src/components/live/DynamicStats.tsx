import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
import {
  colorForClass,
  type SignalCountRow,
} from "@/lib/live-signal-stability";

type DynamicStatsProps = {
  counts?: Record<string, number>;
  signalRows?: SignalCountRow[];
};

export function DynamicStats({ counts, signalRows }: DynamicStatsProps) {
  const entries = (
    signalRows ??
    Object.entries(counts ?? {})
      .filter(([, count]) => count > 0)
      .map(([className, count]) => ({
        className,
        color: colorForClass(className),
        liveCount: count,
        heldCount: 0,
        totalCount: count,
        state: "live" as const,
      }))
  )
    .filter((row) => row.totalCount > 0)
    .sort(
      (left, right) =>
        right.liveCount - left.liveCount ||
        right.totalCount - left.totalCount ||
        left.className.localeCompare(right.className),
    );

  return (
    <section className="overflow-hidden rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-rail)]">
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
          <p className="text-sm text-[#8ca2c5]">
            No live signals. {omniEmptyStates.noSignals}
          </p>
        ) : (
          entries.map((row) => (
            <div
              key={row.className}
              className="rounded-[0.85rem] border border-white/8 bg-black/25 px-4 py-3"
              style={{
                backgroundColor: row.color.fill,
                borderColor: row.color.stroke,
              }}
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#88a3cc]">
                {row.className}
              </p>
              <div className="mt-2 flex items-end justify-between gap-3">
                <p
                  className="text-2xl font-semibold"
                  style={{ color: row.color.text }}
                >
                  {row.totalCount}
                </p>
                {row.heldCount > 0 || row.state === "held" ? (
                  <p className="pb-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#8ca2c5]">
                    Held
                  </p>
                ) : null}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
