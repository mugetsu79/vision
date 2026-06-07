import { useMemo, useState } from "react";

import { EvidenceExportBuilder } from "@/components/fleetops/EvidenceExportBuilder";
import { FleetOpsLinkPerformanceLink } from "@/components/fleetops/FleetOpsLinkPerformanceLink";
import { FleetOpsScopeSelector } from "@/components/fleetops/FleetOpsScopeSelector";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import {
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
  const fleetVessels = useMemo(
    () => (vessels.data ?? []) as FleetOpsVessel[],
    [vessels.data],
  );
  const [scopeSearch, setScopeSearch] = useState("");
  const [selectedVesselId, setSelectedVesselId] = useState<string | null>(null);
  const selectedVessel = useMemo(
    () => fleetVessels.find((vessel) => vessel.id === selectedVesselId) ?? null,
    [fleetVessels, selectedVesselId],
  );
  const siteId = selectedVessel?.site_id ?? null;
  const vesselId = selectedVessel?.id ?? null;
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
      <FleetOpsScopeSelector
        emptyLabel="Choose a vessel or site to review evidence."
        onSearchChange={setScopeSearch}
        onSelectVessel={setSelectedVesselId}
        searchValue={scopeSearch}
        selectedVesselId={selectedVesselId}
        vessels={fleetVessels}
      />
      <FleetOpsLinkPerformanceLink siteId={siteId} />
      {selectedVessel ? (
        <EvidenceExportBuilder
          evidenceContext={
            evidenceContext.data as JsonRecord | null | undefined
          }
          isRetrying={retryQueueItem.isPending}
          linkStatus={
            linkStatus.data as
              | MaritimeVesselLinkStatus
              | JsonRecord
              | null
              | undefined
          }
          queueItems={(queue.data ?? []) as JsonRecord[]}
          onRetryQueueItem={(queueItemId) => {
            void retryQueueItem.mutateAsync(queueItemId);
          }}
        />
      ) : null}
    </main>
  );
}

export const FleetOpsEvidencePage = FleetOpsEvidence;
