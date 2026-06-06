import { useParams } from "react-router-dom";

import { EvidenceExportBuilder } from "@/components/fleetops/EvidenceExportBuilder";
import { LinkOperationsPanel } from "@/components/fleetops/LinkOperationsPanel";
import { VoyageTimeline } from "@/components/fleetops/VoyageTimeline";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import { useFleetOpsVesselDetail } from "@/hooks/use-maritime";
import type {
  FleetOpsVessel,
  JsonRecord,
  MaritimeVesselLinkStatus,
} from "@/components/fleetops/types";

export function FleetOpsVesselDetail() {
  const { vesselId } = useParams();
  const detail = useFleetOpsVesselDetail(vesselId);
  const vessel = detail.vessel.data as FleetOpsVessel | null | undefined;

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        accent="cerulean"
        description="Review schedule state, scene templates, link passport state, telemetry, and incident context for a single vessel."
        eyebrow="FleetOps"
        title={vessel?.name ?? "Vessel detail"}
      />
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
    </main>
  );
}

export const FleetOpsVesselDetailPage = FleetOpsVesselDetail;
