import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import { healthToTone, type SceneHealthRow } from "@/lib/operational-health";

type SceneStatusStripProps = {
  row: SceneHealthRow;
};

export function SceneStatusStrip({ row }: SceneStatusStripProps) {
  const deliveryCopy =
    row.delivery.label === "Direct stream unavailable"
      ? "Native passthrough gated"
      : "Processed stream live";
  const workerCopy =
    row.worker.label === "Worker not reported"
      ? "Worker awaiting report"
      : row.worker.label;

  return (
    <div
      role="group"
      aria-label={`${row.cameraName} operational status`}
      className="flex flex-wrap items-center gap-2"
    >
      <StatusToneBadge tone={healthToTone(row.telemetry.health)}>
        {row.telemetry.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.delivery.health)}>
        {deliveryCopy}
      </StatusToneBadge>
      <StatusToneBadge tone="muted">
        {row.processingMode} scene
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.worker.health)}>
        {workerCopy}
      </StatusToneBadge>
      {row.delivery.detail ? (
        <span className="text-xs text-[color:var(--vz-text-muted)]">
          {deliveryCopy}: {row.delivery.detail}
        </span>
      ) : null}
    </div>
  );
}
