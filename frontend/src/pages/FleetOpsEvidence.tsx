import { EvidenceExportBuilder } from "@/components/fleetops/EvidenceExportBuilder";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import {
  firstFleetOpsSiteId,
  type FleetOpsVessel,
  type JsonRecord,
  type MaritimeVesselLinkStatus,
} from "@/components/fleetops/types";
import {
  useLinkSiteQueue,
  useLinkSiteStatus,
  useRetryLinkQueueItem,
} from "@/hooks/use-link";
import {
  useMaritimeEvidenceContext,
  useMaritimeVessels,
} from "@/hooks/use-maritime";

export function FleetOpsEvidence() {
  const evidenceContext = useMaritimeEvidenceContext();
  const vessels = useMaritimeVessels();
  const fleetVessels = (vessels.data ?? []) as FleetOpsVessel[];
  const siteId = firstFleetOpsSiteId(fleetVessels);
  const vesselId =
    fleetVessels.find((vessel) => vessel.site_id === siteId)?.id ?? null;
  const queue = useLinkSiteQueue(siteId);
  const linkStatus = useLinkSiteStatus(siteId);
  const retryQueueItem = useRetryLinkQueueItem({ siteId, vesselId });

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Assemble maritime context for evidence exports while the core incident and artifact pipeline remains pack-neutral."
        eyebrow="FleetOps"
        title="Evidence"
      />
      <EvidenceExportBuilder
        evidenceContext={evidenceContext.data as JsonRecord | null | undefined}
        isRetrying={retryQueueItem.isPending}
        linkStatus={
          linkStatus.data as MaritimeVesselLinkStatus | JsonRecord | null | undefined
        }
        queueItems={(queue.data ?? []) as JsonRecord[]}
        onRetryQueueItem={(queueItemId) => {
          void retryQueueItem.mutateAsync(queueItemId);
        }}
      />
    </main>
  );
}

export const FleetOpsEvidencePage = FleetOpsEvidence;
