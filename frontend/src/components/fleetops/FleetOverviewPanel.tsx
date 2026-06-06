import { Link } from "react-router-dom";

import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { VesselSummaryTable } from "./VesselSummaryTable";
import {
  asRecord,
  humanizeKey,
  textValue,
  type BillingUsagePayload,
  type FleetOpsVessel,
  type SupportDiagnosticsPayload,
} from "./types";

type FleetOverviewPanelProps = {
  vessels: FleetOpsVessel[];
  billingUsage?: BillingUsagePayload;
  supportDiagnostics?: SupportDiagnosticsPayload;
};

export function FleetOverviewPanel({
  vessels,
  billingUsage,
  supportDiagnostics,
}: FleetOverviewPanelProps) {
  const firstUsage = billingUsage?.items?.[0];
  const supportGroups = asRecord(supportDiagnostics?.groups);
  const supportLabel = textValue(
    asRecord(supportGroups.support_roles).label,
    "Open support sessions",
  );
  const evidenceQueue =
    vessels
      .map((vessel) => textValue(asRecord(vessel.metadata).evidence_queue, ""))
      .find(Boolean) ?? "No pending exports";

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.8fr)]">
      <VesselSummaryTable vessels={vessels} />
      <div className="grid gap-4">
        <WorkspaceSurface className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Evidence queue
          </p>
          <p className="mt-3 text-2xl font-semibold text-[var(--vz-text-primary)]">
            {evidenceQueue}
          </p>
          <p className="mt-2 text-sm leading-6 text-[var(--vz-text-secondary)]">
            Prioritized export work stays visible beside link health so operators can
            decide what waits for shore connectivity and what moves over satellite.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,#161c26,#0d121a)] px-4 py-2.5 text-sm font-medium text-[var(--vz-text-primary)] shadow-[var(--vz-elev-1)] transition hover:border-[color:var(--vz-hair-focus)]"
            to="/fleetops/evidence"
          >
            Review queue
          </Link>
        </WorkspaceSurface>
        <WorkspaceSurface className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Current billable usage
          </p>
          <p className="mt-3 text-xl font-semibold text-[var(--vz-text-primary)]">
            {textValue(firstUsage?.label, "vessel month")}
          </p>
          <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
            Quantity {textValue(firstUsage?.quantity, "0")} against FleetOps value
            meters.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[color:var(--vz-hair)] bg-transparent px-4 py-2.5 text-sm font-medium text-[var(--vz-text-secondary)] transition hover:border-[color:var(--vz-hair-strong)] hover:text-[var(--vz-text-primary)]"
            to="/fleetops/billing"
          >
            Open billing
          </Link>
        </WorkspaceSurface>
        <WorkspaceSurface className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            {supportLabel}
          </p>
          <p className="mt-3 text-xl font-semibold text-[var(--vz-text-primary)]">
            {Object.keys(supportGroups).length || 0} diagnostic groups
          </p>
          <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
            {Object.keys(supportGroups)
              .map(humanizeKey)
              .slice(0, 3)
              .join(" / ") || "support roles / evidence path"}
          </p>
        </WorkspaceSurface>
      </div>
    </div>
  );
}
