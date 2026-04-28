import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type InspectorPanelProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function InspectorPanel({
  title,
  description,
  actions,
  children,
  className,
}: InspectorPanelProps) {
  return (
    <aside
      className={cn(
        "rounded-[1.1rem] border border-white/[0.08] bg-[color:var(--vezor-surface-depth)] px-4 py-4 shadow-[var(--vezor-shadow-depth)]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3 border-b border-white/[0.06] pb-3">
        <div className="space-y-1">
          <h2 className="text-sm font-semibold text-[#f4f7fb]">{title}</h2>
          {description ? <p className="text-sm text-[#93a7c1]">{description}</p> : null}
        </div>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </div>

      <div className="pt-3">{children}</div>
    </aside>
  );
}
