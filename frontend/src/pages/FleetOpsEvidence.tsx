import { EvidenceExportBuilder } from "@/components/fleetops/EvidenceExportBuilder";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import { useMaritimeEvidenceContext } from "@/hooks/use-maritime";
import type { JsonRecord } from "@/components/fleetops/types";

export function FleetOpsEvidence() {
  const evidenceContext = useMaritimeEvidenceContext();

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Assemble maritime context for evidence exports while the core incident and artifact pipeline remains pack-neutral."
        eyebrow="FleetOps"
        title="Evidence"
      />
      <EvidenceExportBuilder
        evidenceContext={evidenceContext.data as JsonRecord | null | undefined}
      />
    </main>
  );
}

export const FleetOpsEvidencePage = FleetOpsEvidence;
