import { Link } from "react-router-dom";

import { FleetOverviewPanel } from "@/components/fleetops/FleetOverviewPanel";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import { useBillingUsage } from "@/hooks/use-billing";
import { useFleetExceptions } from "@/hooks/use-fleet";
import {
  useMaritimeRuntime,
  useMaritimeVessels,
} from "@/hooks/use-maritime";
import { useMaritimeSupportDiagnostics } from "@/hooks/use-support";
import type {
  BillingUsagePayload,
  FleetOpsVessel,
  SupportDiagnosticsPayload,
} from "@/components/fleetops/types";

const fleetOpsLinks = [
  { label: "Add Vessel", to: "/fleetops/vessels" },
  { label: "Review Evidence", to: "/fleetops/evidence" },
  { label: "Open Billing", to: "/fleetops/billing" },
  { label: "Open Support", to: "/fleetops/support" },
  { label: "Open Onboarding", to: "/fleetops/onboarding" },
];

export function FleetOps() {
  const runtime = useMaritimeRuntime();
  const vessels = useMaritimeVessels();
  const billingUsage = useBillingUsage();
  const supportDiagnostics = useMaritimeSupportDiagnostics();
  const fleetExceptions = useFleetExceptions();

  const vesselItems = (vessels.data ?? []) as FleetOpsVessel[];
  const exceptionCount = Array.isArray(fleetExceptions.data?.items)
    ? fleetExceptions.data.items.length
    : 0;

  return (
    <main className="space-y-5 p-4 sm:p-6" data-testid="fleetops-workspace">
      <WorkspaceBand
        accent="cerulean"
        description="Maritime FleetOps brings vessel context, constrained links, evidence exports, billing usage, and support readiness into the existing command workspace."
        eyebrow="Runtime pack"
        title="FleetOps"
      >
        <div className="flex flex-wrap items-center gap-2">
          {fleetOpsLinks.map((link) => (
            <Link
              className="rounded-full border border-[color:var(--vz-hair)] bg-white/[0.035] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--vz-text-secondary)] transition hover:border-[color:var(--vz-hair-focus)] hover:text-[var(--vz-text-primary)]"
              key={link.to}
              to={link.to}
            >
              {link.label}
            </Link>
          ))}
        </div>
        <p className="mt-3 text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
          {runtime.data ? "maritime-fleet enabled" : "runtime pending"} /{" "}
          {exceptionCount} fleet exceptions
        </p>
      </WorkspaceBand>
      <FleetOverviewPanel
        billingUsage={billingUsage.data as BillingUsagePayload | undefined}
        supportDiagnostics={
          supportDiagnostics.data as SupportDiagnosticsPayload | undefined
        }
        vessels={vesselItems}
      />
    </main>
  );
}

export const FleetOpsPage = FleetOps;
