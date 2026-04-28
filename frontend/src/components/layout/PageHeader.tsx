import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-4 border-b border-white/[0.07] pb-5 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="space-y-2">
        {eyebrow ? (
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8fa2be]">
            {eyebrow}
          </p>
        ) : null}
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-[0.01em] text-[#f4f7fb]">
            {title}
          </h1>
          {description ? (
            <p className="max-w-3xl text-sm leading-6 text-[#93a7c1]">{description}</p>
          ) : null}
        </div>
      </div>

      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </header>
  );
}
