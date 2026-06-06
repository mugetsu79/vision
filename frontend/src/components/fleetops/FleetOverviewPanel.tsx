import { Link } from "react-router-dom";

import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { VesselSummaryTable } from "./VesselSummaryTable";
import {
  asRecord,
  type DiagnosticsGroup,
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
  const usageLabel = textValue(
    firstUsage?.label,
    humanizeKey(textValue(firstUsage?.meter_key, "vessel_month")),
  );
  const supportGroups = readinessGroups(supportDiagnostics?.groups);
  const supportLabel = textValue(supportDiagnostics?.label, "Support readiness");
  const readinessCountLabel = `${supportGroups.length} readiness ${
    supportGroups.length === 1 ? "group" : "groups"
  }`;
  const readinessSummary =
    supportGroups
      .map((group) =>
        textValue(group.label, humanizeKey(textValue(group.id, "readiness"))),
      )
      .slice(0, 3)
      .join(" / ") || "connection readiness / evidence path";
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
            decide what waits for a better connection window and what moves over the
            selected connection.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,#161c26,#0d121a)] px-4 py-2.5 text-sm font-medium text-[var(--vz-text-primary)] shadow-[var(--vz-elev-1)] transition hover:border-[color:var(--vz-hair-focus)]"
            to="/fleetops/evidence"
          >
            Review evidence
          </Link>
        </WorkspaceSurface>
        <WorkspaceSurface className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Current billable usage
          </p>
          <p className="mt-3 text-xl font-semibold text-[var(--vz-text-primary)]">
            {usageLabel}
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
            {readinessCountLabel}
          </p>
          <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
            {readinessSummary}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              className="inline-flex rounded-full border border-[color:var(--vz-hair)] bg-transparent px-4 py-2.5 text-sm font-medium text-[var(--vz-text-secondary)] transition hover:border-[color:var(--vz-hair-strong)] hover:text-[var(--vz-text-primary)]"
              to="/fleetops/support"
            >
              Open support
            </Link>
            <Link
              className="inline-flex rounded-full border border-[color:var(--vz-hair)] bg-transparent px-4 py-2.5 text-sm font-medium text-[var(--vz-text-secondary)] transition hover:border-[color:var(--vz-hair-strong)] hover:text-[var(--vz-text-primary)]"
              to="/fleetops/onboarding"
            >
              Open onboarding
            </Link>
          </div>
        </WorkspaceSurface>
      </div>
    </div>
  );
}

function readinessGroups(
  groups: SupportDiagnosticsPayload["groups"],
): DiagnosticsGroup[] {
  if (Array.isArray(groups)) {
    return groups
      .map((group) => asRecord(group) as DiagnosticsGroup)
      .filter((group) => Object.keys(group).length > 0);
  }

  return Object.entries(asRecord(groups)).map(([id, group]) => {
    const item = asRecord(group);
    return {
      ...item,
      id: textValue(item.id, id),
    } as DiagnosticsGroup;
  });
}
