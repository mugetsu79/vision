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
    <WorkspaceSurface
      data-testid="scene-intelligence-matrix"
      className="overflow-hidden"
    >
      <div className="border-b border-white/8 px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
          Operational readiness
        </p>
        <h2 className="mt-2 text-lg font-semibold text-[var(--vz-text-primary)]">
          Scene intelligence matrix
        </h2>
      </div>

      {rows.length === 0 ? (
        <p className="px-4 py-5 text-sm text-[var(--vz-text-secondary)]">
          No scenes configured.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-black/20 text-[11px] uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
              <tr>
                <th className="px-4 py-3 font-semibold">Scene</th>
                <th className="px-4 py-3 font-semibold">Site</th>
                <th className="px-4 py-3 font-semibold">Mode</th>
                <th className="px-4 py-3 font-semibold">Privacy</th>
                <th className="px-4 py-3 font-semibold">Worker</th>
                <th className="px-4 py-3 font-semibold">Delivery</th>
                <th className="px-4 py-3 font-semibold">Telemetry</th>
                <th className="px-4 py-3 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/8">
              {rows.map((row) => (
                <tr key={row.cameraId}>
                  <td className="px-4 py-3 font-semibold text-[var(--vz-text-primary)]">
                    {row.cameraName}
                  </td>
                  <td className="px-4 py-3 text-[var(--vz-text-secondary)]">
                    {row.siteName}
                  </td>
                  <td className="px-4 py-3 text-[var(--vz-text-secondary)]">
                    {row.processingMode} / {row.nodeLabel}
                  </td>
                  <td className="px-4 py-3">
                    <HealthCell signal={row.privacy} />
                  </td>
                  <td className="px-4 py-3">
                    <HealthCell signal={row.worker} />
                  </td>
                  <td className="px-4 py-3">
                    <HealthCell signal={row.delivery} />
                  </td>
                  <td className="px-4 py-3">
                    <HealthCell signal={row.telemetry} />
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={row.actionHref}
                      aria-label={`${row.actionLabel} for ${row.cameraName}`}
                      className="text-sm font-semibold text-[var(--vz-lens-cerulean)] transition hover:text-[var(--vz-text-primary)]"
                    >
                      {row.actionLabel}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </WorkspaceSurface>
  );
}

function HealthCell({ signal }: { signal: HealthSignal }) {
  return (
    <div className="space-y-1">
      <StatusToneBadge tone={healthToTone(signal.health)}>
        {signal.label}
      </StatusToneBadge>
      {signal.detail ? (
        <p className="text-xs text-[var(--vz-text-muted)]">{signal.detail}</p>
      ) : null}
    </div>
  );
}
