import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type KpiTileProps = {
  eyebrow: string;
  value: ReactNode;
  caption?: ReactNode;
  className?: string;
};

export function KpiTile({ eyebrow, value, caption, className }: KpiTileProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite-up)] px-4 py-3 shadow-[var(--vz-elev-1)]",
        className,
      )}
    >
      <p className="text-[11px] font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
        {eyebrow}
      </p>
      <p className="mt-2 font-[family-name:var(--vz-font-display)] text-2xl font-semibold tabular-nums text-[var(--vz-text-primary)]">
        {value}
      </p>
      {caption ? (
        <p className="mt-1 text-xs text-[var(--vz-text-secondary)]">
          {caption}
        </p>
      ) : null}
    </div>
  );
}
