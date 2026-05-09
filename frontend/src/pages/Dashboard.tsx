import { useMemo } from "react";
import { Link } from "react-router-dom";

import { OmniSightLens } from "@/components/brand/OmniSightLens";
import { KpiTile } from "@/components/dashboard/KpiTile";
import {
  InstrumentRail,
  StatusToneBadge,
  WorkspaceHero,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { AttentionStack } from "@/components/operations/AttentionStack";
import { DeploymentPostureStrip } from "@/components/operations/DeploymentPostureStrip";
import { useCameras } from "@/hooks/use-cameras";
import { useIncidents } from "@/hooks/use-incidents";
import { useFleetOverview } from "@/hooks/use-operations";
import { useSites } from "@/hooks/use-sites";
import {
  deriveAttentionItems,
  deriveDeploymentPosture,
  deriveFleetHealth,
} from "@/lib/operational-health";

export function DashboardPage() {
  const { data: cameras = [] } = useCameras();
  const { data: sites = [] } = useSites();
  const { data: incidents = [] } = useIncidents({
    cameraId: null,
    incidentType: null,
    reviewStatus: "pending",
    limit: 12,
  });
  const fleet = useFleetOverview();

  const fleetHealth = deriveFleetHealth(fleet.data);
  const deploymentPosture = useMemo(
    () =>
      deriveDeploymentPosture({
        sites,
        cameras,
        fleet: fleet.data,
        pendingIncidents: incidents,
      }),
    [cameras, fleet.data, incidents, sites],
  );
  const attentionItems = useMemo(
    () =>
      deriveAttentionItems({
        fleet: fleet.data,
        cameras,
        pendingIncidents: incidents,
      }),
    [cameras, fleet.data, incidents],
  );

  const runningWorkers = fleet.data?.summary.running_workers ?? 0;
  const desiredWorkers = fleet.data?.summary.desired_workers ?? 0;
  const directUnavailable =
    fleet.data?.summary.native_unavailable_cameras ?? 0;

  const evidenceCaption = `${incidents.length} pending evidence ${
    incidents.length === 1 ? "record" : "records"
  }`;

  return (
    <div
      data-testid="omnisight-overview"
      className="grid gap-5 p-4 sm:p-6 xl:grid-cols-[minmax(0,1fr)_340px]"
    >
      <WorkspaceHero
        eyebrow="Dashboard"
        title="OmniSight Overview"
        description="A connected view of live scenes, evidence, patterns, deployment context, and edge operations."
        tone="cerulean"
        lens={<OmniSightLens variant="dashboard" />}
        className="xl:col-span-2"
        body={
          <div className="grid gap-3 sm:grid-cols-3">
            <KpiTile
              eyebrow="Live scenes"
              value={cameras.length}
              caption={`${cameras.length === 1 ? "scene" : "scenes"} streaming`}
            />
            <KpiTile
              eyebrow="Evidence queue"
              value={incidents.length}
              caption={evidenceCaption}
            />
            <KpiTile
              eyebrow="Edge workers"
              value={`${runningWorkers}/${desiredWorkers}`}
              caption="running / desired"
            />
          </div>
        }
      />

      <div className="xl:col-span-2">
        <DeploymentPostureStrip posture={deploymentPosture} />
      </div>

      <div className="xl:col-span-2">
        <AttentionStack items={attentionItems} fleetHealth={fleetHealth} />
      </div>

      <InstrumentRail aria-label="Overview instruments" className="space-y-3 p-4 xl:col-span-2">
        <StatusToneBadge tone={directUnavailable > 0 ? "attention" : "healthy"}>
          {directUnavailable > 0
            ? `${directUnavailable} direct streams unavailable`
            : "Streams healthy"}
        </StatusToneBadge>
        <p className="text-sm text-[var(--vz-text-secondary)]">
          {sites.length} deployment {sites.length === 1 ? "site" : "sites"}{" "}
          configured.
        </p>
      </InstrumentRail>

      <section className="grid gap-4 xl:col-span-2 lg:grid-cols-3">
        <OverviewLink
          title="Live Intelligence"
          copy="Open the portal wall and inspect active scene signals."
          href="/live"
          action="Open Live Intelligence"
        />
        <OverviewLink
          title="Patterns"
          copy="Explore time windows, buckets, speed, and event trends."
          href="/history"
          action="Explore Patterns"
        />
        <OverviewLink
          title="Evidence"
          copy="Review pending records and move evidence to a decision."
          href="/incidents"
          action="Review Evidence"
        />
        <OverviewLink
          title="Scenes"
          copy="Configure source streams, models, privacy, boundaries, and calibration."
          href="/cameras"
          action="Set Up Scenes"
        />
        <OverviewLink
          title="Sites"
          copy="Manage deployment locations and their scene context."
          href="/sites"
          action="Open Sites"
        />
        <OverviewLink
          title="Operations"
          copy="Inspect workers, bootstrap material, and stream diagnostics."
          href="/settings"
          action="Open Operations"
        />
      </section>
    </div>
  );
}

function OverviewLink({
  title,
  copy,
  href,
  action,
}: {
  title: string;
  copy: string;
  href: string;
  action: string;
}) {
  return (
    <WorkspaceSurface className="p-4 transition duration-200 hover:border-[color:var(--vz-hair-focus)] hover:shadow-[var(--vz-elev-2)]">
      <h2 className="font-[family-name:var(--vz-font-display)] text-lg font-semibold text-[var(--vz-text-primary)]">
        {title}
      </h2>
      <p className="mt-2 min-h-12 text-sm leading-6 text-[var(--vz-text-secondary)]">
        {copy}
      </p>
      <Link
        to={href}
        className="mt-4 inline-flex text-sm font-semibold text-[var(--vz-lens-cerulean)] transition hover:text-[var(--vz-text-primary)]"
      >
        {action}
      </Link>
    </WorkspaceSurface>
  );
}
