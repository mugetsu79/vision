import { SupportDiagnosticsPanel } from "@/components/fleetops/SupportDiagnosticsPanel";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import {
  useMaritimeSupportDiagnostics,
  useSupportOnboardingChecks,
} from "@/hooks/use-support";
import { useMaritimeVessels } from "@/hooks/use-maritime";
import type {
  FleetOpsVessel,
  OnboardingChecksPayload,
  SupportDiagnosticsPayload,
} from "@/components/fleetops/types";
import { firstFleetOpsSiteId } from "@/components/fleetops/types";

export function FleetOpsOnboarding() {
  const diagnostics = useMaritimeSupportDiagnostics();
  const vessels = useMaritimeVessels();
  const siteId = firstFleetOpsSiteId((vessels.data ?? []) as FleetOpsVessel[]);
  const onboardingChecks = useSupportOnboardingChecks(siteId);

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Shipboard setup checks for vessel networks, satellite fallback, ETO handoff, camera naming, and support roles."
        eyebrow="FleetOps"
        title="Onboarding"
      />
      <SupportDiagnosticsPanel
        diagnostics={diagnostics.data as SupportDiagnosticsPayload | undefined}
        onboardingChecks={
          onboardingChecks.data as OnboardingChecksPayload | null | undefined
        }
      />
    </main>
  );
}

export const FleetOpsOnboardingPage = FleetOpsOnboarding;
