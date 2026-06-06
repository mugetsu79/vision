import { OnboardingChecklistPanel } from "@/components/fleetops/OnboardingChecklistPanel";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import {
  useRunSupportOnboardingChecks,
  useSupportOnboardingChecks,
} from "@/hooks/use-support";
import { useMaritimeVessels } from "@/hooks/use-maritime";
import type {
  FleetOpsVessel,
  OnboardingChecksPayload,
} from "@/components/fleetops/types";
import { firstFleetOpsSiteId } from "@/components/fleetops/types";

export function FleetOpsOnboarding() {
  const vessels = useMaritimeVessels();
  const siteId = firstFleetOpsSiteId((vessels.data ?? []) as FleetOpsVessel[]);
  const onboardingChecks = useSupportOnboardingChecks(siteId);
  const runChecks = useRunSupportOnboardingChecks(siteId);

  async function handleRunChecks() {
    if (!siteId) {
      return;
    }
    await runChecks.mutateAsync({
      metadata: { source: "fleetops_onboarding" },
      pack_id: "maritime-fleet",
      site_id: siteId,
    });
  }

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Shipboard setup checks for vessel networks, satellite fallback, ETO handoff, camera naming, and support roles."
        eyebrow="FleetOps"
        title="Onboarding"
      />
      <OnboardingChecklistPanel
        checks={onboardingChecks.data as OnboardingChecksPayload | null | undefined}
        isRunningChecks={runChecks.isPending}
        onRunChecks={() => void handleRunChecks()}
        siteId={siteId}
      />
    </main>
  );
}

export const FleetOpsOnboardingPage = FleetOpsOnboarding;
