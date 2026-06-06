import { Link } from "react-router-dom";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { asRecord, humanizeKey, textValue, type FleetOpsVessel } from "./types";

type VesselSummaryTableProps = {
  vessels: FleetOpsVessel[];
  onAddVessel?: () => void;
};

export function VesselSummaryTable({
  vessels,
  onAddVessel,
}: VesselSummaryTableProps) {
  if (vessels.length === 0) {
    return (
      <WorkspaceSurface className="p-6 text-center">
        <p className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
          No vessels are connected to FleetOps yet.
        </p>
        <p className="mx-auto mt-2 max-w-md text-sm text-[var(--vz-text-secondary)]">
          Add the first vessel to create its FleetOps site binding and start
          configuring connectivity, evidence, support, and onboarding.
        </p>
        {onAddVessel ? (
          <Button className="mt-5" variant="primary" onClick={onAddVessel}>
            Add vessel
          </Button>
        ) : null}
      </WorkspaceSurface>
    );
  }

  return (
    <WorkspaceSurface className="overflow-hidden">
      <div className="border-b border-[color:var(--vz-hair)] px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
          Vessel watch
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-[color:var(--vz-hair)] text-left text-sm">
          <thead className="bg-white/[0.025] text-[11px] uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            <tr>
              <th className="px-4 py-3 font-semibold">Vessel</th>
              <th className="px-4 py-3 font-semibold">Link state</th>
              <th className="px-4 py-3 font-semibold">Export status</th>
              <th className="px-4 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[color:var(--vz-hair)]">
            {vessels.map((vessel) => {
              const id = textValue(vessel.id, "unknown-vessel");
              const metadata = asRecord(vessel.metadata);
              const linkState = formatLinkState(metadata.link_state);
              const evidenceQueue = textValue(
                metadata.evidence_queue,
                "No pending exports",
              );
              return (
                <tr key={id} className="align-top">
                  <th className="px-4 py-3 font-medium text-[var(--vz-text-primary)]">
                    <Link
                      className="rounded-sm underline-offset-4 hover:text-[var(--vz-lens-cerulean)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--vz-hair-focus)]"
                      to={`/fleetops/vessels/${id}`}
                    >
                      {textValue(vessel.name, "Unnamed vessel")}
                    </Link>
                    <p className="mt-1 text-xs font-normal text-[var(--vz-text-muted)]">
                      Site {textValue(vessel.site_id, "unassigned")}
                    </p>
                  </th>
                  <td className="px-4 py-3">
                    <StatusToneBadge tone={linkTone(linkState)}>
                      {linkState}
                    </StatusToneBadge>
                  </td>
                  <td className="px-4 py-3 text-[var(--vz-text-secondary)]">
                    {evidenceQueue}
                  </td>
                  <td className="px-4 py-3 text-[var(--vz-text-secondary)]">
                    {vessel.active === false ? "Inactive" : "Active"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </WorkspaceSurface>
  );
}

function formatLinkState(value: unknown): string {
  if (typeof value !== "string" || value.length === 0) {
    return "unknown";
  }
  return humanizeKey(value);
}

function linkTone(
  state: string,
): "healthy" | "attention" | "danger" | "muted" | "accent" {
  const normalized = state.toLowerCase();
  if (normalized.includes("dark")) {
    return "danger";
  }
  if (normalized.includes("degraded") || normalized.includes("recovering")) {
    return "attention";
  }
  if (normalized.includes("wifi") || normalized.includes("healthy")) {
    return "healthy";
  }
  return "muted";
}
