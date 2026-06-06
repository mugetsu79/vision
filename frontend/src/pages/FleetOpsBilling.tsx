import { BillingRollupPanel } from "@/components/fleetops/BillingRollupPanel";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import {
  useBillingInvoiceRuns,
  useBillingMeters,
  useBillingUsage,
} from "@/hooks/use-billing";
import type {
  BillingUsagePayload,
  InvoiceRun,
  JsonRecord,
} from "@/components/fleetops/types";

export function FleetOpsBilling() {
  const invoiceRuns = useBillingInvoiceRuns();
  const meters = useBillingMeters();
  const usage = useBillingUsage();

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        accent="violet"
        description="Track FleetOps commercial usage and capacity guardrails through the existing core billing baseline."
        eyebrow="FleetOps"
        title="Billing"
      />
      <BillingRollupPanel
        invoiceRuns={(invoiceRuns.data ?? []) as InvoiceRun[]}
        meters={(meters.data ?? []) as JsonRecord[]}
        usage={usage.data as BillingUsagePayload | undefined}
      />
    </main>
  );
}

export const FleetOpsBillingPage = FleetOpsBilling;
