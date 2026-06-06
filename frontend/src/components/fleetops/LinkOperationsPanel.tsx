import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import {
  asRecord,
  humanizeKey,
  scalarText,
  textValue,
  type JsonRecord,
  type MaritimeVesselLinkStatus,
} from "./types";

type LinkOperationsPanelProps = {
  linkStatus?: MaritimeVesselLinkStatus | JsonRecord | null;
};

export function LinkOperationsPanel({ linkStatus }: LinkOperationsPanelProps) {
  const status = asRecord(linkStatus);
  const queueDepth = asRecord(status.queue_depth);

  return (
    <WorkspaceSurface className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Link operations
          </p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
            {humanizeKey(textValue(status.link_state, "unknown"))}
          </h2>
        </div>
        <StatusToneBadge tone="accent">
          Passport {textValue(status.passport_hash, "pending").slice(0, 8)}
        </StatusToneBadge>
      </div>
      <dl className="mt-5 grid gap-3 sm:grid-cols-3">
        {["safety", "evidence", "bulk"].map((lane) => (
          <div
            className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3"
            key={lane}
          >
            <dt className="text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
              {lane}
            </dt>
            <dd className="mt-2 text-lg font-semibold text-[var(--vz-text-primary)]">
              {scalarText(queueDepth[lane])}
            </dd>
          </div>
        ))}
      </dl>
    </WorkspaceSurface>
  );
}
