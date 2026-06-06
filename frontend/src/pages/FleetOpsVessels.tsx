import { VesselSummaryTable } from "@/components/fleetops/VesselSummaryTable";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import { useMaritimeVessels } from "@/hooks/use-maritime";
import type { FleetOpsVessel } from "@/components/fleetops/types";

export function FleetOpsVessels() {
  const vessels = useMaritimeVessels();

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Scan vessels, site bindings, link posture, and pending evidence movement from one fleet table."
        eyebrow="FleetOps"
        title="Vessels"
      />
      <VesselSummaryTable vessels={(vessels.data ?? []) as FleetOpsVessel[]} />
    </main>
  );
}

export const FleetOpsVesselsPage = FleetOpsVessels;
