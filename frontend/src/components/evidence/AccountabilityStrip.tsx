import type { Incident } from "@/hooks/use-incidents";
import {
  artifactStatusLabel,
  evidenceStorageLabel,
  hashPrefix,
  primaryClipArtifact,
} from "@/components/evidence/evidence-artifacts";

export function AccountabilityStrip({ incident }: { incident: Incident }) {
  const clipArtifact = primaryClipArtifact(incident);
  const ledgerCount = incident.ledger_summary?.entry_count ?? 0;

  return (
    <div
      data-testid="accountability-strip"
      className="grid border-b border-white/8 bg-[#07101b] sm:grid-cols-2 xl:grid-cols-4"
    >
      <AccountabilityCell
        label="Scene contract"
        value={hashPrefix(incident.scene_contract_hash)}
        detail={incident.scene_contract_hash ? "Attached" : "Missing"}
      />
      <AccountabilityCell
        label="Privacy manifest"
        value={hashPrefix(incident.privacy_manifest_hash)}
        detail={incident.privacy_manifest_hash ? "Identity policy" : "Missing"}
      />
      <AccountabilityCell
        label="Evidence clip"
        value={evidenceStorageLabel(incident)}
        detail={
          clipArtifact ? artifactStatusLabel(clipArtifact) : "No artifact"
        }
      />
      <AccountabilityCell
        label="Ledger"
        value={ledgerCount === 1 ? "1 entry" : `${ledgerCount} entries`}
        detail={incident.ledger_summary?.latest_action ?? "No events"}
      />
    </div>
  );
}

function AccountabilityCell({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="min-w-0 border-b border-r border-white/8 px-4 py-3 last:border-r-0 sm:[&:nth-child(3)]:border-b-0 sm:[&:nth-child(4)]:border-b-0 xl:border-b-0">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7894bd]">
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-semibold text-[#eef4ff]">
        {value}
      </p>
      <p className="mt-1 truncate text-xs text-[#8fa4c4]">{detail}</p>
    </div>
  );
}
