import { KpiTile } from "@/components/dashboard/KpiTile";
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import {
  healthToTone,
  type DeploymentPosture,
} from "@/lib/operational-health";

type DeploymentPostureStripProps = {
  posture: DeploymentPosture;
};

export function DeploymentPostureStrip({ posture }: DeploymentPostureStripProps) {
  return (
    <section
      data-testid="deployment-posture-strip"
      aria-label="Deployment posture"
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6"
    >
      <KpiTile
        eyebrow="Sites"
        value={posture.siteCount}
        caption={`${posture.sceneCount} operational scenes`}
      />
      <KpiTile
        eyebrow="Central / Edge / Hybrid"
        value={`${posture.centralScenes} / ${posture.edgeScenes} / ${posture.hybridScenes}`}
        caption={`${posture.assignedEdgeNodes} assigned edge nodes`}
      />
      <KpiTile
        eyebrow="Privacy configured"
        value={posture.privacyConfiguredScenes}
        caption="face or plate controls present"
      />
      <KpiTile
        eyebrow="Evidence awaiting review"
        value={posture.pendingEvidence}
        caption="pending records"
      />
      <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite-up)] px-4 py-3 shadow-[var(--vz-elev-1)] sm:col-span-2 xl:col-span-2">
        <p className="text-[11px] font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
          Fleet health
        </p>
        <div className="mt-2">
          <StatusToneBadge tone={healthToTone(posture.fleetHealth.health)}>
            {posture.fleetHealth.label}
          </StatusToneBadge>
        </div>
        <p className="mt-2 text-xs text-[var(--vz-text-secondary)]">
          {posture.fleetHealth.reasons[0] ?? "No reported fleet issues"}
        </p>
      </div>
    </section>
  );
}
