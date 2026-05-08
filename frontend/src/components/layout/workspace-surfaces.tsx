import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type WorkspaceBandDensity = "standard" | "compact";
type WorkspaceBandAccent = "neutral" | "cerulean" | "violet";

type WorkspaceBandProps = HTMLAttributes<HTMLElement> & {
  eyebrow: string;
  title: string;
  description?: string;
  density?: WorkspaceBandDensity;
  accent?: WorkspaceBandAccent;
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

const accentClasses: Record<WorkspaceBandAccent, string> = {
  neutral: "",
  cerulean: "border-t-2 border-t-[color:var(--vz-lens-cerulean)]",
  violet: "border-t-2 border-t-[color:var(--vz-lens-violet)]",
};

const densityClasses: Record<WorkspaceBandDensity, string> = {
  standard: "px-5 py-5",
  compact: "px-5 py-4",
};

export function WorkspaceBand({
  eyebrow,
  title,
  description,
  density = "standard",
  accent = "neutral",
  actions,
  className,
  children,
  ...props
}: WorkspaceBandProps) {
  return (
    <section
      className={cn(
        "rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[linear-gradient(180deg,var(--vz-canvas-graphite)_0%,var(--vz-canvas-graphite-up)_100%)] shadow-[var(--vz-elev-1)]",
        densityClasses[density],
        accentClasses[accent],
        className,
      )}
      {...props}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
            {eyebrow}
          </p>
          <h1 className="mt-2 font-[family-name:var(--vz-font-display)] text-2xl font-semibold tracking-normal text-[var(--vz-text-primary)] sm:text-3xl">
            {title}
          </h1>
          {description ? (
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--vz-text-secondary)]">
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
