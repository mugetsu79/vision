import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";

import { VesselFormDialog } from "@/components/fleetops/VesselFormDialog";
import { VesselSummaryTable } from "@/components/fleetops/VesselSummaryTable";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  useCreateMaritimeVessel,
  useMaritimeVessels,
  type MaritimeVesselCreateInput,
} from "@/hooks/use-maritime";
import { useSites } from "@/hooks/use-sites";
import type { FleetOpsVessel } from "@/components/fleetops/types";

export function FleetOpsVessels() {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const vessels = useMaritimeVessels();
  const sites = useSites();
  const createVessel = useCreateMaritimeVessel();
  const vesselRows = (vessels.data ?? []) as FleetOpsVessel[];

  async function handleCreateVessel(payload: MaritimeVesselCreateInput) {
    const created = await createVessel.mutateAsync(payload);
    setDialogOpen(false);

    if (typeof created?.id === "string") {
      navigate(`/fleetops/vessels/${created.id}`);
    }
  }

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Scan vessels, site bindings, link posture, and pending evidence movement from one fleet table."
        eyebrow="FleetOps"
        title="Vessels"
        actions={
          <Button variant="primary" onClick={() => setDialogOpen(true)}>
            <Plus className="mr-2 size-4" aria-hidden="true" />
            Add vessel
          </Button>
        }
      />
      <VesselSummaryTable
        vessels={vesselRows}
        onAddVessel={() => setDialogOpen(true)}
      />
      <VesselFormDialog
        open={dialogOpen}
        sites={sites.data ?? []}
        isSubmitting={createVessel.isPending}
        onClose={() => setDialogOpen(false)}
        onSubmit={(payload) =>
          handleCreateVessel(payload as MaritimeVesselCreateInput)
        }
      />
    </main>
  );
}

export const FleetOpsVesselsPage = FleetOpsVessels;
