import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import { healthToTone, type SceneHealthRow } from "@/lib/operational-health";

type SceneStatusStripProps = {
  row: SceneHealthRow;
};

export function SceneStatusStrip({ row }: SceneStatusStripProps) {
  return (
    <div
      role="group"
      aria-label={`${row.cameraName} operational status`}
      className="flex flex-wrap gap-2"
    >
      <StatusToneBadge tone="muted">{row.processingMode}</StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.privacy.health)}>
        {row.privacy.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.worker.health)}>
        {row.worker.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.delivery.health)}>
        {row.delivery.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.telemetry.health)}>
        {row.telemetry.label}
      </StatusToneBadge>
    </div>
  );
}
