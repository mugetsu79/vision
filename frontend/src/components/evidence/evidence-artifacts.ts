import type { Incident } from "@/hooks/use-incidents";

export type EvidenceArtifact = NonNullable<
  Incident["evidence_artifacts"]
>[number];

type EvidenceArtifactWithSync = EvidenceArtifact & {
  sync_status?: string | null;
  sync_error?: string | null;
};

export function primaryClipArtifact(
  incident: Incident,
): EvidenceArtifact | undefined {
  return incident.evidence_artifacts?.find(
    (artifact) => artifact.kind === "event_clip",
  );
}

export function primarySnapshotArtifact(
  incident: Incident,
): EvidenceArtifact | undefined {
  return incident.evidence_artifacts?.find(
    (artifact) => artifact.kind === "snapshot",
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

export function evidenceSnapshotHref(incident: Incident): string | null {
  const artifact = primarySnapshotArtifact(incident);
  if (artifact?.review_url) {
    return artifact.review_url;
  }
  if (incident.snapshot_url) {
    return incident.snapshot_url;
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

export function artifactStatusLabel(artifact: EvidenceArtifact): string {
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
