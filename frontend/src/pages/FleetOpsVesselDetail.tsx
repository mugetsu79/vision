import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Pencil, Power } from "lucide-react";

import { EvidenceExportBuilder } from "@/components/fleetops/EvidenceExportBuilder";
import { LinkOperationsPanel } from "@/components/fleetops/LinkOperationsPanel";
import { VesselFormDialog } from "@/components/fleetops/VesselFormDialog";
import { VoyageTimeline } from "@/components/fleetops/VoyageTimeline";
import {
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  useDeactivateMaritimeVessel,
  useFleetOpsVesselDetail,
  useUpdateMaritimeVessel,
  type MaritimeVesselUpdateInput,
} from "@/hooks/use-maritime";
import type {
  FleetOpsVessel,
  JsonRecord,
  MaritimeVesselLinkStatus,
} from "@/components/fleetops/types";
import { textValue } from "@/components/fleetops/types";

export function FleetOpsVesselDetail() {
  const { vesselId } = useParams();
  const navigate = useNavigate();
  const [editOpen, setEditOpen] = useState(false);
  const [deactivateError, setDeactivateError] = useState<string | null>(null);
  const detail = useFleetOpsVesselDetail(vesselId);
  const vessel = detail.vessel.data as FleetOpsVessel | null | undefined;
  const effectiveVesselId = typeof vessel?.id === "string" ? vessel.id : "";
  const updateVessel = useUpdateMaritimeVessel(effectiveVesselId);
  const deactivateVessel = useDeactivateMaritimeVessel();

  async function handleUpdateVessel(payload: MaritimeVesselUpdateInput) {
    if (!effectiveVesselId) {
      return;
    }

    await updateVessel.mutateAsync(payload);
    setEditOpen(false);
  }

  async function handleDeactivateVessel() {
    if (!effectiveVesselId) {
      return;
    }

    const vesselName = textValue(vessel?.name, "this vessel");
    if (!window.confirm(`Deactivate ${vesselName}?`)) {
      return;
    }

    setDeactivateError(null);
    try {
      await deactivateVessel.mutateAsync(effectiveVesselId);
      navigate("/fleetops/vessels");
    } catch (error) {
      setDeactivateError(
        error instanceof Error ? error.message : "Unable to deactivate vessel.",
      );
    }
  }

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        accent="cerulean"
        description="Review schedule state, scene templates, link passport state, telemetry, and incident context for a single vessel."
        eyebrow="FleetOps"
        title={vessel?.name ?? "Vessel detail"}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              disabled={!effectiveVesselId || updateVessel.isPending}
              onClick={() => setEditOpen(true)}
            >
              <Pencil className="mr-2 size-4" aria-hidden="true" />
              Edit vessel
            </Button>
            <Button
              variant="ghost"
              className="border-[#5a2330] bg-[#241118] text-[#ffc2cd] hover:border-[#7c3142] hover:text-[#ffe2e7]"
              disabled={!effectiveVesselId || deactivateVessel.isPending}
              onClick={() => void handleDeactivateVessel()}
            >
              <Power className="mr-2 size-4" aria-hidden="true" />
              Deactivate vessel
            </Button>
          </div>
        }
      />
      {deactivateError ? (
        <WorkspaceSurface
          role="alert"
          className="border-[#5a2330] bg-[#241118] px-4 py-3 text-sm font-medium text-[#ffc2cd]"
        >
          {deactivateError}
        </WorkspaceSurface>
      ) : null}
      <VoyageTimeline
        evidenceContext={detail.evidenceContext.data as JsonRecord | null | undefined}
        linkStatus={
          detail.linkStatus.data as MaritimeVesselLinkStatus | JsonRecord | null | undefined
        }
        telemetry={detail.telemetry.data as JsonRecord | null | undefined}
        vessel={vessel}
      />
      <LinkOperationsPanel
        linkStatus={
          detail.linkStatus.data as MaritimeVesselLinkStatus | JsonRecord | null | undefined
        }
      />
      <EvidenceExportBuilder
        evidenceContext={detail.evidenceContext.data as JsonRecord | null | undefined}
      />
      <VesselFormDialog
        mode="edit"
        open={editOpen}
        vessel={vessel}
        isSubmitting={updateVessel.isPending}
        onClose={() => setEditOpen(false)}
        onSubmit={(payload) =>
          handleUpdateVessel(payload as MaritimeVesselUpdateInput)
        }
      />
    </main>
  );
}

export const FleetOpsVesselDetailPage = FleetOpsVesselDetail;
