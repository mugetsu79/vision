import type { Incident } from "@/hooks/use-incidents";

const TYPE_ACCENTS = [
  "#6ed3ff",
  "#7ee0a3",
  "#f5c46a",
  "#ff8a90",
  "#b79cff",
  "#6ee7d8",
];

export type EvidenceStateKind =
  | "clip_only"
  | "snapshot_only"
  | "clip_and_snapshot"
  | "metadata_only";

export type EvidenceState = {
  kind: EvidenceStateKind;
  label: string;
  detail: string;
};

export type EvidenceTimelineBucket = {
  id: string;
  label: string;
  startMs: number;
  count: number;
  incidentIds: string[];
  selected: boolean;
  dominantType: string;
  accent: string;
  selectableIncidentId: string;
};

export function buildEvidenceTimelineBuckets(
  incidents: Incident[],
  selectedIncidentId: string | null,
): EvidenceTimelineBucket[] {
  const buckets = new Map<number, Incident[]>();

  for (const incident of incidents) {
    const timestamp = new Date(incident.ts);
    const start = new Date(timestamp);
    start.setUTCMinutes(0, 0, 0);
    const startMs = start.getTime();
    buckets.set(startMs, [...(buckets.get(startMs) ?? []), incident]);
  }

  return Array.from(buckets.entries())
    .sort(([left], [right]) => left - right)
    .map(([startMs, bucketIncidents]) => {
      const selected = bucketIncidents.some(
        (incident) => incident.id === selectedIncidentId,
      );
      const dominantType = dominantIncidentType(bucketIncidents);

      return {
        id: String(startMs),
        label: formatBucketLabel(startMs),
        startMs,
        count: bucketIncidents.length,
        incidentIds: bucketIncidents.map((incident) => incident.id),
        selected,
        dominantType,
        accent: incidentTypeAccent(dominantType),
        selectableIncidentId:
          bucketIncidents.find((incident) => incident.id === selectedIncidentId)
            ?.id ?? bucketIncidents[0].id,
      };
    });
}

export function describeEvidenceState(incident: Incident): EvidenceState {
  const hasClip = Boolean(
    incident.clip_url ||
      incident.evidence_artifacts?.some((artifact) => artifact.kind === "event_clip"),
  );
  const hasSnapshot = Boolean(
    incident.snapshot_url ||
      incident.evidence_artifacts?.some((artifact) => artifact.kind === "snapshot"),
  );

  if (hasClip && hasSnapshot) {
    return {
      kind: "clip_and_snapshot",
      label: "Clip and snapshot",
      detail: "Video and still evidence are both available.",
    };
  }
  if (hasClip) {
    return {
      kind: "clip_only",
      label: "Clip only",
      detail: "Video evidence is available without a still snapshot.",
    };
  }
  if (hasSnapshot) {
    return {
      kind: "snapshot_only",
      label: "Snapshot only",
      detail: "Still evidence is available without a clip artifact.",
    };
  }
  return {
    kind: "metadata_only",
    label: "Metadata only",
    detail: "Contract, manifest, ledger, and payload are available without media.",
  };
}

export function incidentTypeAccent(type: string): string {
  let hash = 0;
  for (const char of type) {
    hash = (hash + char.charCodeAt(0)) % TYPE_ACCENTS.length;
  }
  return TYPE_ACCENTS[hash];
}

function dominantIncidentType(incidents: Incident[]): string {
  const counts = new Map<string, number>();
  for (const incident of incidents) {
    counts.set(incident.type, (counts.get(incident.type) ?? 0) + 1);
  }
  return Array.from(counts.entries()).sort(
    ([leftType, leftCount], [rightType, rightCount]) =>
      rightCount - leftCount || leftType.localeCompare(rightType),
  )[0][0];
}

function formatBucketLabel(startMs: number): string {
  return new Date(startMs).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}
