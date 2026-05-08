import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type ToastTone = "healthy" | "attention" | "danger" | "accent";

const toneStripe: Record<ToastTone, string> = {
  healthy: "bg-[var(--vz-state-healthy)]",
  attention: "bg-[var(--vz-state-attention)]",
  danger: "bg-[var(--vz-state-risk)]",
  accent: "bg-[var(--vz-lens-cerulean)]",
};

export type ToastSpec = {
  id: string;
  tone: ToastTone;
  message: string;
  description?: ReactNode;
};

export function Toast({ spec }: { spec: ToastSpec }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "relative flex max-w-sm overflow-hidden rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair-strong)] bg-[color:var(--vz-canvas-graphite-up)] shadow-[var(--vz-elev-3)]",
      )}
    >
      <span className={cn("w-1 shrink-0", toneStripe[spec.tone])} />
      <div className="px-4 py-3">
        <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
          {spec.message}
        </p>
        {spec.description ? (
          <p className="mt-1 text-xs text-[var(--vz-text-secondary)]">
            {spec.description}
          </p>
        ) : null}
      </div>
    </div>
  );
}
