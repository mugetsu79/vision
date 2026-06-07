import { useMemo, useState } from "react";

import { FleetOpsScopeSelector } from "@/components/fleetops/FleetOpsScopeSelector";
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

export function FleetOpsOnboarding() {
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
      <FleetOpsScopeSelector
        emptyLabel="Choose a vessel or site to review onboarding."
        onSearchChange={setScopeSearch}
        onSelectVessel={setSelectedVesselId}
        searchValue={scopeSearch}
        selectedVesselId={selectedVesselId}
        vessels={fleetVessels}
      />
      {selectedVessel ? (
        <OnboardingChecklistPanel
          checks={
            onboardingChecks.data as OnboardingChecksPayload | null | undefined
          }
          isRunningChecks={runChecks.isPending}
          onRunChecks={() => void handleRunChecks()}
          siteId={siteId}
        />
      ) : null}
    </main>
  );
}

export const FleetOpsOnboardingPage = FleetOpsOnboarding;
