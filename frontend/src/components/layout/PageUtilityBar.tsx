import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type PageUtilityBarProps = {
  label?: string;
  title?: string;
  description?: string;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
};

export function PageUtilityBar({
  label,
  title,
  description,
  actions,
  children,
  className,
}: PageUtilityBarProps) {
  return (
    <section
      className={cn(
        "rounded-[1.1rem] border border-white/[0.08] bg-[color:var(--vezor-surface-depth)] px-4 py-3 shadow-[var(--vezor-shadow-depth)] backdrop-blur-md",
        className,
      )}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          {label ? (
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8fa2be]">
              {label}
            </p>
          ) : null}
          {title ? <p className="text-sm font-medium text-[#eef4ff]">{title}</p> : null}
          {description ? <p className="text-sm text-[#93a7c1]">{description}</p> : null}
        </div>

        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>

      {children ? <div className="mt-3 flex flex-wrap items-center gap-2">{children}</div> : null}
    </section>
  );
}
