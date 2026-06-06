import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  asRecord,
  humanizeKey,
  scalarText,
  textValue,
  type JsonRecord,
  type MaritimeVesselLinkStatus,
} from "./types";

type EvidenceExportBuilderProps = {
  evidenceContext?: JsonRecord | null;
  isRetrying?: boolean;
  linkStatus?: MaritimeVesselLinkStatus | JsonRecord | null;
  queueItems?: JsonRecord[];
  onRetryQueueItem?: (queueItemId: string) => void;
};

export function EvidenceExportBuilder({
  evidenceContext,
  isRetrying = false,
  linkStatus,
  queueItems = [],
  onRetryQueueItem,
}: EvidenceExportBuilderProps) {
  const context = asRecord(evidenceContext);
  const status = asRecord(linkStatus);
  const pendingItems = queueItems.filter((item) =>
    ["queued", "paused", "failed"].includes(textValue(item.status, "")),
  );

  return (
    <WorkspaceSurface className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Evidence queue
          </p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
            Export builder
          </h2>
        </div>
        <div className="rounded-full border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-1 text-xs font-medium text-[var(--vz-text-secondary)]">
          {pendingItems.length} pending
        </div>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Metric label="Vessel" value={textValue(context.vessel_name, "Fleet vessel")} />
        <Metric label="Port" value={textValue(context.port_name, "At sea")} />
        <Metric
          label="Resolution"
          value={humanizeKey(textValue(context.resolution_source, "runtime context"))}
        />
      </div>
      <div className="mt-4 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3">
        <p className="text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
          Link posture
        </p>
        <p className="mt-2 text-sm font-semibold text-[var(--vz-text-primary)]">
          {humanizeKey(textValue(status.link_state, "unknown"))}
        </p>
        <p className="mt-1 text-xs text-[var(--vz-text-muted)]">
          Passport {textValue(status.passport_hash, "pending").slice(0, 8)}
        </p>
      </div>
      <div className="mt-4 grid gap-2">
        {(queueItems.length
          ? queueItems
          : [
              {
                id: "empty",
                priority_lane: "evidence",
                status: "none",
                byte_size: 0,
              },
            ]
        ).map((item) => {
          const itemId = textValue(item.id, "");
          const canRetry = itemId.length > 0 && itemId !== "empty" && onRetryQueueItem;
          return (
            <div
              className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.02] px-3 py-3"
              key={itemId || textValue(item.status)}
            >
              <div>
                <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
                  {humanizeKey(textValue(item.priority_lane, "evidence"))} ·{" "}
                  {humanizeKey(textValue(item.status, "pending"))}
                </p>
                <p className="mt-1 text-xs text-[var(--vz-text-muted)]">
                  {scalarText(item.byte_size)} bytes ·{" "}
                  {humanizeKey(textValue(item.source_object_type, "evidence export"))}
                </p>
              </div>
              {canRetry ? (
                <Button
                  variant="ghost"
                  disabled={isRetrying}
                  onClick={() => onRetryQueueItem(itemId)}
                >
                  Retry
                </Button>
              ) : null}
            </div>
          );
        })}
      </div>
      <div className="mt-4 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.02] px-3 py-3">
        <p className="text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
          Export history
        </p>
        <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
          Latest context is ready for evidence export review.
        </p>
      </div>
      <p className="mt-4 text-sm leading-6 text-[var(--vz-text-secondary)]">
        Evidence exports preserve maritime context, link state, and pack metadata
        while leaving the core evidence path unchanged.
      </p>
    </WorkspaceSurface>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3">
      <p className="text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
        {label}
      </p>
      <p className="mt-2 text-sm font-semibold text-[var(--vz-text-primary)]">
        {value}
      </p>
    </div>
  );
}
