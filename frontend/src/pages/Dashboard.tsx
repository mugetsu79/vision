import { Link } from "react-router-dom";

import { OmniSightField } from "@/components/brand/OmniSightField";
import {
  InstrumentRail,
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { useCameras } from "@/hooks/use-cameras";
import { useIncidents } from "@/hooks/use-incidents";
import { useFleetOverview } from "@/hooks/use-operations";
import { useSites } from "@/hooks/use-sites";

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

  const runningWorkers = fleet.data?.summary.running_workers ?? 0;
  const desiredWorkers = fleet.data?.summary.desired_workers ?? 0;
  const directUnavailable =
    fleet.data?.summary.native_unavailable_cameras ?? 0;

  return (
    <div
      data-testid="omnisight-overview"
      className="grid gap-5 p-4 sm:p-6 xl:grid-cols-[minmax(0,1fr)_340px]"
    >
      <section className="relative min-h-[22rem] overflow-hidden rounded-[1rem] border border-white/10 bg-[linear-gradient(135deg,rgba(9,14,23,0.98),rgba(7,10,16,0.96))] px-5 py-5">
        <OmniSightField variant="dashboard" className="opacity-80" />
        <div className="relative z-10 max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8fa4c4]">
            Dashboard
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-normal text-[#f4f8ff] sm:text-5xl">
            OmniSight Overview
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[#9eb0cb]">
            A connected view of live scenes, evidence, patterns, deployment
            context, and edge operations.
          </p>
        </div>
        <div className="relative z-10 mt-8 grid gap-3 sm:grid-cols-3">
          <OverviewMetric
            label="Live scenes"
            value={`${cameras.length} live scenes`}
          />
          <OverviewMetric
            label="Evidence queue"
            value={`${incidents.length} pending evidence ${
              incidents.length === 1 ? "record" : "records"
            }`}
          />
          <OverviewMetric
            label="Edge workers"
            value={`${runningWorkers}/${desiredWorkers} running`}
          />
        </div>
      </section>

      <InstrumentRail aria-label="Overview instruments" className="space-y-3 p-4">
        <StatusToneBadge tone={directUnavailable > 0 ? "attention" : "healthy"}>
          {directUnavailable > 0
            ? `${directUnavailable} direct streams unavailable`
            : "Streams healthy"}
        </StatusToneBadge>
        <p className="text-sm text-[#9eb0cb]">
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

function OverviewMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[0.85rem] border border-white/10 bg-black/25 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7f96b8]">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold text-[#f4f8ff]">{value}</p>
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
    <WorkspaceSurface className="p-4 transition duration-200 hover:border-[color:var(--vezor-border-focus)] hover:bg-[rgba(17,24,34,0.96)]">
      <h2 className="text-lg font-semibold text-[#f4f8ff]">{title}</h2>
      <p className="mt-2 min-h-12 text-sm leading-6 text-[#9eb0cb]">{copy}</p>
      <Link
        to={href}
        className="mt-4 inline-flex text-sm font-semibold text-[var(--vezor-lens-cerulean)] transition hover:text-white"
      >
        {action}
      </Link>
    </WorkspaceSurface>
  );
}
