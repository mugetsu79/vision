import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-[0.7rem] border border-[color:var(--argus-border)] bg-[color:var(--argus-surface-soft)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--argus-text-muted)]",
        className,
      )}
      {...props}
    />
  );
}
