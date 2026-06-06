import { SupportReadinessPanel } from "@/components/fleetops/SupportReadinessPanel";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import {
  useCreateSupportBundle,
  useCreateSupportSession,
  useOpenBreakGlass,
  useMaritimeSupportDiagnostics,
  useSupportBundles,
} from "@/hooks/use-support";
import { useMaritimeVessels } from "@/hooks/use-maritime";
import type {
  FleetOpsVessel,
  SupportDiagnosticsPayload,
} from "@/components/fleetops/types";
import { firstFleetOpsSiteId } from "@/components/fleetops/types";

export function FleetOpsSupport() {
  const bundles = useSupportBundles();
  const diagnostics = useMaritimeSupportDiagnostics();
  const vessels = useMaritimeVessels();
  const siteId = firstFleetOpsSiteId((vessels.data ?? []) as FleetOpsVessel[]);
  const createBundle = useCreateSupportBundle();
  const createSession = useCreateSupportSession();
  const openBreakGlass = useOpenBreakGlass();

  async function handleGenerateBundle() {
    if (!siteId) {
      return;
    }
    await createBundle.mutateAsync({
      diagnostics: { source: "fleetops_support" },
      include_logs: true,
      pack_id: "maritime-fleet",
      site_id: siteId,
    });
  }

  async function handleCreateSession() {
    if (!siteId) {
      return;
    }
    await createSession.mutateAsync({
      metadata: { source: "fleetops_support" },
      site_id: siteId,
    });
  }

  async function handleOpenBreakGlass() {
    if (!siteId) {
      return;
    }
    await openBreakGlass.mutateAsync({
      actor_id: "fleetops-operator",
      approver_id: "fleetops-supervisor",
      audit_payload: { source: "fleetops_support" },
      reason: "FleetOps operator support escalation",
      scope: { site_id: siteId },
    });
  }

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Coordinate shipboard diagnostics, supervisor tunnels, emergency access controls, and setup readiness."
        eyebrow="FleetOps"
        title="Support"
      />
      <SupportReadinessPanel
        bundles={bundles.data ?? []}
        diagnostics={diagnostics.data as SupportDiagnosticsPayload | undefined}
        isCreatingSession={createSession.isPending}
        isGeneratingBundle={createBundle.isPending}
        isOpeningBreakGlass={openBreakGlass.isPending}
        onCreateSession={() => void handleCreateSession()}
        onGenerateBundle={() => void handleGenerateBundle()}
        onOpenBreakGlass={() => void handleOpenBreakGlass()}
        siteId={siteId}
      />
    </main>
  );
}

export const FleetOpsSupportPage = FleetOpsSupport;
