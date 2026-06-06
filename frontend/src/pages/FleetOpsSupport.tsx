import { SupportDiagnosticsPanel } from "@/components/fleetops/SupportDiagnosticsPanel";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import {
  useMaritimeSupportDiagnostics,
  useSupportBundles,
  useSupportOnboardingChecks,
} from "@/hooks/use-support";
import { useMaritimeVessels } from "@/hooks/use-maritime";
import type {
  FleetOpsVessel,
  OnboardingChecksPayload,
  SupportDiagnosticsPayload,
} from "@/components/fleetops/types";
import { firstFleetOpsSiteId } from "@/components/fleetops/types";

export function FleetOpsSupport() {
  const bundles = useSupportBundles();
  const diagnostics = useMaritimeSupportDiagnostics();
  const vessels = useMaritimeVessels();
  const siteId = firstFleetOpsSiteId((vessels.data ?? []) as FleetOpsVessel[]);
  const onboardingChecks = useSupportOnboardingChecks(siteId);

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Coordinate shipboard diagnostics, supervisor tunnels, emergency access controls, and setup readiness."
        eyebrow="FleetOps"
        title="Support"
      />
      <SupportDiagnosticsPanel
        bundles={bundles.data ?? []}
        diagnostics={diagnostics.data as SupportDiagnosticsPayload | undefined}
        onboardingChecks={
          onboardingChecks.data as OnboardingChecksPayload | null | undefined
        }
      />
    </main>
  );
}

export const FleetOpsSupportPage = FleetOpsSupport;
