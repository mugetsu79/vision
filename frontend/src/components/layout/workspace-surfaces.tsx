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
    "border-[rgba(111,224,163,0.28)] bg-[rgba(10,36,24,0.72)] text-[var(--vz-state-healthy)]",
  attention:
    "border-[rgba(245,196,106,0.28)] bg-[rgba(42,31,10,0.72)] text-[var(--vz-state-attention)]",
  danger:
    "border-[rgba(244,140,166,0.28)] bg-[rgba(45,14,24,0.72)] text-[var(--vz-state-risk)]",
  muted:
    "border-[color:var(--vz-hair)] bg-white/[0.035] text-[var(--vz-text-muted)]",
  accent:
    "border-[rgba(118,224,255,0.28)] bg-[rgba(23,52,70,0.56)] text-[var(--vz-lens-cerulean)]",
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
        "rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite)] shadow-[var(--vz-elev-1)]",
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
        "overflow-hidden rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair-strong)] bg-[color:var(--vz-media-black)]",
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
        "rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite)] shadow-[var(--vz-elev-1)]",
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

type WorkspaceHeroTone = "neutral" | "cerulean" | "violet";

type WorkspaceHeroProps = {
  eyebrow: string;
  title: string;
  description?: string;
  tone?: WorkspaceHeroTone;
  body?: ReactNode;
  lens?: ReactNode;
  className?: string;
};

const heroToneClasses: Record<WorkspaceHeroTone, string> = {
  neutral: "shadow-[var(--vz-elev-1)]",
  cerulean: "shadow-[var(--vz-elev-glow-cerulean)]",
  violet: "shadow-[var(--vz-elev-glow-violet)]",
};

export function WorkspaceHero({
  eyebrow,
  title,
  description,
  tone = "neutral",
  body,
  lens,
  className,
}: WorkspaceHeroProps) {
  return (
    <section
      data-testid="workspace-hero"
      data-tone={tone}
      className={cn(
        "relative overflow-hidden rounded-[var(--vz-r-xl)] border border-[color:var(--vz-hair)] bg-[linear-gradient(135deg,var(--vz-canvas-graphite)_0%,var(--vz-canvas-obsidian)_100%)] px-6 py-7 sm:px-8 sm:py-8",
        heroToneClasses[tone],
        className,
      )}
      style={{ perspective: "var(--vz-perspective)" }}
    >
      <div className="grid items-center gap-8 lg:grid-cols-[7fr_5fr]">
        <div className="min-w-0 space-y-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--vz-text-muted)]">
            {eyebrow}
          </p>
          <h1 className="font-[family-name:var(--vz-font-display)] text-3xl font-semibold tracking-normal text-[var(--vz-text-primary)] sm:text-4xl lg:text-5xl">
            {title}
          </h1>
          {description ? (
            <p className="max-w-2xl text-base leading-7 text-[var(--vz-text-secondary)]">
              {description}
            </p>
          ) : null}
          {body ? <div className="pt-2">{body}</div> : null}
        </div>
        {lens ? (
          <div className="relative grid place-items-center">{lens}</div>
        ) : null}
      </div>
    </section>
  );
}
