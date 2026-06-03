import { Link } from "react-router-dom";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import {
  healthToTone,
  type HealthSignal,
  type SceneHealthRow,
} from "@/lib/operational-health";

type SceneIntelligenceMatrixProps = {
  rows: SceneHealthRow[];
};

export function SceneIntelligenceMatrix({
  rows,
}: SceneIntelligenceMatrixProps) {
  return (
    <WorkspaceSurface data-testid="scene-intelligence-matrix">
      <div className="border-b border-white/8 px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
          Operational readiness
        </p>
        <h2 className="mt-2 text-lg font-semibold text-[var(--vz-text-primary)]">
          Scene readiness
        </h2>
      </div>

      {rows.length === 0 ? (
        <p className="px-4 py-5 text-sm text-[var(--vz-text-secondary)]">
          No scenes configured.
        </p>
      ) : (
        <div className="grid gap-3 p-4">
          {rows.map((row) => (
            <article
              key={row.cameraId}
              className="grid min-w-0 gap-4 rounded-lg border border-white/8 bg-white/[0.025] p-4 xl:grid-cols-[minmax(14rem,0.8fr)_minmax(0,1fr)_minmax(0,1fr)_auto] xl:items-start"
            >
              <div className="min-w-0">
                <h3 className="break-words text-base font-semibold text-[var(--vz-text-primary)]">
                  {row.cameraName}
                </h3>
                <p className="mt-1 break-words text-sm text-[var(--vz-text-secondary)]">
                  {row.siteName}
                </p>
                <p className="mt-2 break-words text-sm text-[var(--vz-text-muted)]">
                  {placementLabel(row)}
                </p>
              </div>

              <SignalGroup
                title="Runtime"
                signals={[
                  { label: "Worker", signal: row.worker },
                  { label: "Telemetry", signal: row.telemetry },
                  { label: "Rules", signal: row.rules },
                ]}
              />

              <SignalGroup
                title="Stream"
                signals={[
                  { label: "Transport", signal: row.transport },
                  { label: "Live rendition", signal: row.liveRendition },
                  { label: "Privacy", signal: row.privacy },
                ]}
              />

              <Link
                to={row.actionHref}
                aria-label={`${row.actionLabel} for ${row.cameraName}`}
                className="min-w-0 self-start break-words text-sm font-semibold text-[var(--vz-lens-cerulean)] transition hover:text-[var(--vz-text-primary)]"
              >
                {row.actionLabel}
              </Link>
            </article>
          ))}
        </div>
      )}
    </WorkspaceSurface>
  );
}

function placementLabel(row: SceneHealthRow) {
  const mode = row.processingMode.toLowerCase();
  const nodeLabel = row.nodeLabel.trim() || "assigned node";

  if (mode === "edge") {
    return `Edge processing on ${nodeLabel}`;
  }

  const centralLabel =
    nodeLabel.toLowerCase() === "central" ? "master supervisor" : nodeLabel;

  if (mode === "central") {
    return `Central processing on ${centralLabel}`;
  }

  if (mode === "hybrid") {
    return `Hybrid processing on ${centralLabel}`;
  }

  return `${row.processingMode} processing on ${nodeLabel}`;
}

function SignalGroup({
  title,
  signals,
}: {
  title: string;
  signals: Array<{ label: string; signal: HealthSignal }>;
}) {
  return (
    <div className="min-w-0 rounded-lg border border-white/8 bg-black/15 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
        {title}
      </p>
      <div className="mt-2 grid gap-2">
        {signals.map(({ label, signal }) => (
          <div key={label} className="grid min-w-0 gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
              {label}
            </span>
            <HealthCell signal={signal} />
          </div>
        ))}
      </div>
    </div>
  );
}

function HealthCell({ signal }: { signal: HealthSignal }) {
  return (
    <div className="min-w-0 space-y-1">
      <StatusToneBadge
        tone={healthToTone(signal.health)}
        className="max-w-full whitespace-normal break-words text-left leading-4"
      >
        {signal.label}
      </StatusToneBadge>
      {signal.detail ? (
        <p className="break-words text-xs text-[var(--vz-text-muted)]">
          {signal.detail}
        </p>
      ) : null}
    </div>
  );
}
