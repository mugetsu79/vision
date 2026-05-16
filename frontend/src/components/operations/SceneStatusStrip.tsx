import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import { healthToTone, type SceneHealthRow } from "@/lib/operational-health";

type SceneStatusStripProps = {
  row: SceneHealthRow;
};

export function SceneStatusStrip({ row }: SceneStatusStripProps) {
  const workerCopy =
    row.worker.label === "Worker not reported"
      ? "Worker awaiting report"
      : row.worker.label;
  const details = [
    row.liveRendition.detail
      ? `${row.liveRendition.label}: ${row.liveRendition.detail}`
      : null,
    row.transport.detail ? `${row.transport.label}: ${row.transport.detail}` : null,
  ].filter(Boolean);

  return (
    <div
      role="group"
      aria-label={`${row.cameraName} operational status`}
      className="flex flex-wrap items-center gap-2"
    >
      <StatusToneBadge tone={healthToTone(row.telemetry.health)}>
        {row.telemetry.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.liveRendition.health)}>
        {row.liveRendition.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.transport.health)}>
        {row.transport.label}
      </StatusToneBadge>
      <StatusToneBadge tone="muted">
        {row.processingMode} scene
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.worker.health)}>
        {workerCopy}
      </StatusToneBadge>
      {details.length > 0 ? (
        <span className="text-xs text-[color:var(--vz-text-muted)]">
          {details.join(" · ")}
        </span>
      ) : null}
    </div>
  );
}
