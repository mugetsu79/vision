import type { Incident } from "@/hooks/use-incidents";

type EvidenceArtifact = NonNullable<Incident["evidence_artifacts"]>[number];
type EvidenceArtifactWithSync = EvidenceArtifact & {
  sync_status?: string | null;
  sync_error?: string | null;
};

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
        detail={clipArtifact ? artifactStatusLabel(clipArtifact) : "No artifact"}
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

export function primaryClipArtifact(
  incident: Incident,
): EvidenceArtifact | undefined {
  return incident.evidence_artifacts?.find(
    (artifact) => artifact.kind === "event_clip",
  );
}

export function evidenceClipHref(incident: Incident): string | null {
  const artifact = primaryClipArtifact(incident);
  if (artifact?.review_url) {
    return artifact.review_url;
  }
  if (incident.clip_url) {
    return incident.clip_url;
  }
  if (artifact) {
    return `/api/v1/incidents/${incident.id}/artifacts/${artifact.id}/content`;
  }
  return null;
}

export function evidenceStorageLabel(incident: Incident): string {
  const artifact = primaryClipArtifact(incident);
  if (artifact?.storage_scope === "cloud") {
    return "Cloud evidence";
  }
  if (artifact?.storage_scope === "central") {
    return "Central evidence";
  }
  if (artifact?.storage_scope === "edge") {
    return "Local evidence";
  }

  const profile = incident.recording_policy?.storage_profile;
  if (profile === "cloud") {
    return "Cloud evidence";
  }
  if (profile === "central") {
    return "Central evidence";
  }
  if (profile === "edge_local" || profile === "local_first") {
    return "Local evidence";
  }
  return "No evidence clip";
}

export function hashPrefix(hash: string | null | undefined): string {
  return hash ? hash.slice(0, 8) : "Not attached";
}

function artifactStatusLabel(artifact: EvidenceArtifact): string {
  if (artifact.status === "local_only") {
    return "Local only";
  }
  if (artifact.status === "remote_available") {
    return "Reviewable";
  }
  if (artifact.status === "available") {
    return "Available";
  }
  if (artifact.status === "upload_pending") {
    const syncStatus = (artifact as EvidenceArtifactWithSync).sync_status;
    if (syncStatus === "failed") {
      return "Upload failed; local copy available";
    }
    if (syncStatus === "uploading" || syncStatus === "retrying") {
      return "Retrying upload";
    }
    return "Upload pending";
  }
  return "Expired";
}
