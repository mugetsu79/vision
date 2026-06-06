import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  humanizeKey,
  textValue,
  type BillingUsagePayload,
  type JsonRecord,
} from "./types";

const capacityGuardrails = [
  "camera capacity tier",
  "managed edge node",
  "retained evidence GB",
  "managed link GB",
];

const valueMeters = [
  "evidence pack export",
  "support session hour",
  "managed link GB",
  "fleet runtime health",
  "operational incident resolved",
];

type BillingRollupPanelProps = {
  meters?: JsonRecord[];
  usage?: BillingUsagePayload;
};

export function BillingRollupPanel({
  meters = [],
  usage,
}: BillingRollupPanelProps) {
  const usageItems = usage?.items ?? [];
  const meterLabels = meters
    .map((meter) => textValue(meter.label, ""))
    .filter((meter) => !reservedMeterLabels.has(meter.toLowerCase()))
    .filter(Boolean);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <WorkspaceSurface className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
          Base commercial unit
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-[var(--vz-text-primary)]">
          vessel month
        </h2>
        <p className="mt-3 text-sm leading-6 text-[var(--vz-text-secondary)]">
          FleetOps keeps billing anchored to fleet operations labels while core
          billing routes stay pack-neutral.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {capacityGuardrails.map((guardrail) => (
            <MeterChip key={guardrail}>{guardrail}</MeterChip>
          ))}
        </div>
      </WorkspaceSurface>
      <WorkspaceSurface className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
              Value meters
            </p>
            <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
              {usageItems.length || 0} active usage records
            </h2>
          </div>
          <Button variant="ghost">Export usage</Button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {[...new Set([...valueMeters, ...meterLabels])].map((meter) => (
            <MeterChip key={meter}>{humanizeKey(meter)}</MeterChip>
          ))}
        </div>
      </WorkspaceSurface>
      <WorkspaceSurface className="p-4 lg:col-span-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
          Current billable usage
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {(usageItems.length
            ? usageItems
            : [{ label: "evidence pack export", quantity: "0" }]
          ).map((item) => (
            <div
              className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3"
              key={`${textValue(item.label)}-${textValue(item.quantity, "0")}`}
            >
              <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
                Usage record
              </p>
              <p className="mt-2 text-xs text-[var(--vz-text-muted)]">
                Quantity {textValue(item.quantity, "0")}
              </p>
            </div>
          ))}
        </div>
      </WorkspaceSurface>
    </div>
  );
}

function MeterChip({ children }: { children: string }) {
  return (
    <span className="rounded-full border border-[color:var(--vz-hair)] bg-white/[0.035] px-3 py-1 text-xs text-[var(--vz-text-secondary)]">
      {children}
    </span>
  );
}

const reservedMeterLabels = new Set([
  "vessel month",
  ...capacityGuardrails.map((meter) => meter.toLowerCase()),
  ...valueMeters.map((meter) => meter.toLowerCase()),
]);
