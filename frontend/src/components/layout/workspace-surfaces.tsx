import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type WorkspaceBandProps = HTMLAttributes<HTMLElement> & {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
};

type Tone = "healthy" | "attention" | "danger" | "muted" | "accent";

const toneClasses: Record<Tone, string> = {
  healthy:
    "border-[rgba(114,227,166,0.24)] bg-[rgba(10,35,24,0.72)] text-[var(--vezor-success)]",
  attention:
    "border-[rgba(242,189,92,0.26)] bg-[rgba(42,31,10,0.72)] text-[var(--vezor-attention)]",
  danger:
    "border-[rgba(240,138,162,0.28)] bg-[rgba(45,14,24,0.72)] text-[var(--vezor-risk)]",
  muted: "border-white/10 bg-white/[0.035] text-[#9db0cc]",
  accent:
    "border-[rgba(118,224,255,0.26)] bg-[rgba(23,52,70,0.56)] text-[var(--vezor-lens-cerulean)]",
};

export function WorkspaceBand({
  eyebrow,
  title,
  description,
  actions,
  className,
  children,
  ...props
}: WorkspaceBandProps) {
  return (
    <section
      className={cn(
        "rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-neutral)] px-5 py-5",
        className,
      )}
      {...props}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8fa4c4]">
            {eyebrow}
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-normal text-[#f4f8ff] sm:text-3xl">
            {title}
          </h1>
          {description ? (
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[#9eb0cb]">
              {description}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
      {children ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}

export function WorkspaceSurface({
  className,
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn(
        "rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-neutral)]",
        className,
      )}
      {...props}
    />
  );
}

export function MediaSurface({
  className,
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[0.9rem] border border-white/10 bg-[color:var(--vezor-media-black)]",
        className,
      )}
      {...props}
    />
  );
}

export function InstrumentRail({
  className,
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <aside
      className={cn(
        "rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-rail)]",
        className,
      )}
      {...props}
    />
  );
}

export function StatusToneBadge({
  tone = "muted",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em]",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
