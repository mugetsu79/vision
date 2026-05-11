import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState, type CSSProperties } from "react";

import { CaseContextStrip } from "@/components/evidence/CaseContextStrip";
import { EvidenceTimeline } from "@/components/evidence/EvidenceTimeline";
import {
  evidenceClipHref,
} from "@/components/evidence/AccountabilityStrip";
import {
  describeEvidenceState,
  incidentTypeAccent,
} from "@/components/evidence/evidence-signals";
import {
  InstrumentRail,
  StatusToneBadge,
  WorkspaceBand,
} from "@/components/layout/workspace-surfaces";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
import { useCameras } from "@/hooks/use-cameras";
import {
  type Incident,
  type IncidentReviewStatus,
  useIncidents,
  useUpdateIncidentReview,
} from "@/hooks/use-incidents";
import { useToast } from "@/hooks/use-toast";
import { apiClient, toApiError } from "@/lib/api";
import type { components } from "@/lib/api.generated";
import { useReducedMotionSafe } from "@/lib/motion";

type ReviewFilter = IncidentReviewStatus | "all";
type SceneContractSnapshot =
  components["schemas"]["SceneContractSnapshotResponse"];
type PrivacyManifestSnapshot =
  components["schemas"]["PrivacyManifestSnapshotResponse"];
type EvidenceLedgerEntry =
  components["schemas"]["EvidenceLedgerEntryResponse"];

export function IncidentsPage() {
  const { data: cameras = [] } = useCameras();
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedReviewStatus, setSelectedReviewStatus] =
    useState<ReviewFilter>("pending");
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(
    null,
  );

  const reviewStatus =
    selectedReviewStatus === "all" ? null : selectedReviewStatus;
  const {
    data: incidents = [],
    isLoading,
    error,
  } = useIncidents({
    cameraId: selectedCameraId,
    incidentType: selectedType,
    reviewStatus,
    limit: 50,
  });
  const reviewMutation = useUpdateIncidentReview();
  const resetReviewMutation = reviewMutation.reset;
  const toast = useToast();
  const evidenceSwapMotion = useReducedMotionSafe("evidenceSwap");

  const cameraNamesById = useMemo(
    () => new Map(cameras.map((camera) => [camera.id, camera.name])),
    [cameras],
  );

  const incidentTypes = useMemo(
    () =>
      Array.from(new Set(incidents.map((incident) => incident.type))).sort(),
    [incidents],
  );

  const selectedIncident = useMemo(
    () =>
      incidents.find((incident) => incident.id === selectedIncidentId) ??
      incidents[0] ??
      null,
    [incidents, selectedIncidentId],
  );

  useEffect(() => {
    if (incidents.length === 0) {
      setSelectedIncidentId(null);
      return;
    }

    if (
      !selectedIncidentId ||
      !incidents.some((incident) => incident.id === selectedIncidentId)
    ) {
      setSelectedIncidentId(incidents[0].id);
    }
  }, [incidents, selectedIncidentId]);

  useEffect(() => {
    if (!reviewMutation.isSuccess) {
      return;
    }

    toast.show({ tone: "healthy", message: "Review state saved." });
    resetReviewMutation();
  }, [resetReviewMutation, reviewMutation.isSuccess, toast]);

  useEffect(() => {
    if (!reviewMutation.isError) {
      return;
    }

    toast.show({
      tone: "danger",
      message: "Failed to update review state.",
      description: reviewMutationErrorMessage(reviewMutation.error),
    });
  }, [reviewMutation.error, reviewMutation.isError, toast]);

  useEffect(() => {
    resetReviewMutation();
  }, [
    resetReviewMutation,
    selectedCameraId,
    selectedIncidentId,
    selectedReviewStatus,
    selectedType,
  ]);

  const errorMessage =
    error instanceof Error ? error.message : "Failed to load incidents.";

  return (
    <div data-testid="evidence-desk-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Evidence"
        title={omniLabels.evidenceTitle}
        description="Review evidence records, confirm state, and move from signal to decision without leaving the desk."
        actions={
          <StatusToneBadge tone="accent">
            {incidents.length} records
          </StatusToneBadge>
        }
      />

      <section
        data-testid="evidence-filter-bar"
        className="grid gap-4 rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-rail)] px-5 py-5 lg:grid-cols-3"
      >
        <label className="space-y-2 text-sm text-[#d9e5f7]">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
            Scene filter
          </span>
          <Select
            aria-label="Scene filter"
            value={selectedCameraId ?? ""}
            onChange={(event) =>
              setSelectedCameraId(
                event.target.value.length > 0 ? event.target.value : null,
              )
            }
          >
            <option value="">All scenes</option>
            {cameras.map((camera) => (
              <option key={camera.id} value={camera.id}>
                {camera.name}
              </option>
            ))}
          </Select>
        </label>

        <label className="space-y-2 text-sm text-[#d9e5f7]">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
            Event type
          </span>
          <Select
            aria-label="Event type"
            value={selectedType ?? ""}
            onChange={(event) =>
              setSelectedType(
                event.target.value.length > 0 ? event.target.value : null,
              )
            }
          >
            <option value="">All types</option>
            {selectedType && !incidentTypes.includes(selectedType) ? (
              <option value={selectedType}>{selectedType}</option>
            ) : null}
            {incidentTypes.map((incidentType) => (
              <option key={incidentType} value={incidentType}>
                {incidentType}
              </option>
            ))}
          </Select>
        </label>

        <label className="space-y-2 text-sm text-[#d9e5f7]">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
            Review status
          </span>
          <Select
            aria-label="Review status"
            value={selectedReviewStatus}
            onChange={(event) =>
              setSelectedReviewStatus(event.target.value as ReviewFilter)
            }
          >
            <option value="pending">Pending</option>
            <option value="reviewed">Reviewed</option>
            <option value="all">All statuses</option>
          </Select>
        </label>
      </section>

      {isLoading ? (
        <StatusMessage>Loading evidence records...</StatusMessage>
      ) : error ? (
        <StatusMessage tone="danger">{errorMessage}</StatusMessage>
      ) : incidents.length === 0 ? (
        <StatusMessage>{omniEmptyStates.noEvidence}</StatusMessage>
      ) : selectedIncident ? (
        <>
          <EvidenceTimeline
            incidents={incidents}
            selectedIncidentId={selectedIncident.id}
            onSelect={setSelectedIncidentId}
          />
          <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)_320px]">
            <IncidentQueue
              incidents={incidents}
              selectedIncidentId={selectedIncident.id}
              cameraNamesById={cameraNamesById}
              onSelect={setSelectedIncidentId}
            />
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={selectedIncident.id}
                data-testid="evidence-media-swap"
                {...evidenceSwapMotion}
                className="min-w-0"
              >
                <IncidentEvidenceHero
                  incident={selectedIncident}
                  cameraName={cameraNameFor(selectedIncident, cameraNamesById)}
                  reviewMutation={reviewMutation}
                />
              </motion.div>
            </AnimatePresence>
            <IncidentFactsPanel
              incident={selectedIncident}
              cameraName={cameraNameFor(selectedIncident, cameraNamesById)}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

function IncidentQueue({
  incidents,
  selectedIncidentId,
  cameraNamesById,
  onSelect,
}: {
  incidents: Incident[];
  selectedIncidentId: string;
  cameraNamesById: Map<string, string>;
  onSelect: (incidentId: string) => void;
}) {
  return (
    <InstrumentRail
      aria-label="Review Queue"
      data-testid="review-queue"
      className="min-w-0 overflow-hidden"
    >
      <div className="border-b border-white/8 px-4 py-3">
        <h3 className="text-lg font-semibold text-[#eef4ff]">
          {omniLabels.reviewQueueTitle}
        </h3>
      </div>

      <div className="divide-y divide-white/8">
        {incidents.map((incident) => {
          const selected = incident.id === selectedIncidentId;
          const cameraName = cameraNameFor(incident, cameraNamesById);

          return (
            <button
              key={incident.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect(incident.id)}
              style={
                {
                  borderLeftColor: incidentTypeAccent(incident.type),
                } as CSSProperties
              }
              className={`block w-full border-l-4 px-4 py-3 text-left transition ${
                selected
                  ? "bg-[linear-gradient(135deg,rgba(110,189,255,0.16),rgba(126,83,255,0.14))] text-white shadow-[inset_3px_0_0_rgba(118,224,255,0.72)]"
                  : "text-[#c5d3ea] hover:bg-white/[0.04]"
              }`}
            >
              <span className="block truncate text-sm font-semibold">
                {cameraName}
              </span>
              <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[#8ea8cf]">
                <span>{incident.type}</span>
                <span>{formatIncidentTime(incident.ts)}</span>
              </span>
              <span className="mt-2 inline-flex rounded-full border border-white/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b7c8e4]">
                {incident.review_status}
              </span>
            </button>
          );
        })}
      </div>
    </InstrumentRail>
  );
}

function IncidentEvidenceHero({
  incident,
  cameraName,
  reviewMutation,
}: {
  incident: Incident;
  cameraName: string;
  reviewMutation: ReturnType<typeof useUpdateIncidentReview>;
}) {
  const nextReviewStatus: IncidentReviewStatus =
    incident.review_status === "pending" ? "reviewed" : "pending";
  const actionLabel =
    incident.review_status === "pending" ? "Review" : "Reopen";
  const clipHref = evidenceClipHref(incident);
  const evidenceState = describeEvidenceState(incident);

  return (
    <section
      aria-label="Selected evidence"
      data-testid="evidence-media"
      className="min-w-0 overflow-hidden rounded-[0.9rem] border border-white/10 bg-[color:var(--vezor-media-black)]"
    >
      <div className="border-b border-white/8 px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-xl font-semibold text-[#f3f7ff]">
              {cameraName}
            </h3>
            <p className="mt-1 text-sm text-[#8fa4c4]">
              {incident.type} at {formatIncidentTime(incident.ts)}
            </p>
          </div>
          <StatusToneBadge
            tone={incident.review_status === "pending" ? "attention" : "healthy"}
          >
            {incident.review_status}
          </StatusToneBadge>
        </div>
      </div>

      <CaseContextStrip incident={incident} />

      <div className="bg-black">
        {incident.snapshot_url ? (
          <img
            src={incident.snapshot_url}
            alt={`Evidence record for ${cameraName}`}
            className="aspect-video w-full object-cover"
          />
        ) : (
          <div className="flex aspect-video flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="text-base font-semibold text-[#eef4ff]">
              {evidenceHeroTitle(evidenceState.kind)}
            </p>
            <p className="max-w-md text-sm text-[#8799b8]">
              {evidenceState.detail}
            </p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <div className="flex flex-wrap items-center gap-3">
          {clipHref ? (
            <a
              href={clipHref}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center rounded-full border border-[#33528a] bg-[#08111d]/85 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#dce8ff] transition hover:border-[#5c7dd0] hover:text-white"
            >
              Open clip
            </a>
          ) : (
            <Badge className="border-[#2d3748] bg-[#0b1018] text-[#9cb0cf]">
              Clip unavailable
            </Badge>
          )}

          <span className="text-sm text-[#8fa4c4]">
            {storageLabel(incident.storage_bytes)}
          </span>
        </div>

        <Button
          onClick={() =>
            reviewMutation.mutate({
              incidentId: incident.id,
              reviewStatus: nextReviewStatus,
            })
          }
          disabled={reviewMutation.isPending}
        >
          {reviewMutation.isPending ? "Saving" : actionLabel}
        </Button>
      </div>
    </section>
  );
}

function IncidentFactsPanel({
  incident,
  cameraName,
}: {
  incident: Incident;
  cameraName: string;
}) {
  const accountability = useIncidentAccountabilityDetails(incident);
  const facts = [
    ["Scene", cameraName],
    ["Event type", incident.type],
    ["Timestamp", formatIncidentTime(incident.ts)],
    ["Review status", incident.review_status],
    [
      "Reviewed at",
      incident.reviewed_at
        ? formatIncidentTime(incident.reviewed_at)
        : "Not reviewed",
    ],
    ["Reviewed by", incident.reviewed_by_subject ?? "Not reviewed"],
    ["Storage", storageLabel(incident.storage_bytes)],
  ];

  return (
    <InstrumentRail
      aria-label="Facts"
      data-testid="facts-rail"
      className="min-w-0 overflow-hidden"
    >
      <div className="border-b border-white/8 px-4 py-3">
        <h3 className="text-lg font-semibold text-[#eef4ff]">
          {omniLabels.factsTitle}
        </h3>
      </div>

      <dl className="divide-y divide-white/8">
        {facts.map(([label, value]) => (
          <FactRow key={label} label={label} value={value} />
        ))}
      </dl>

      <div className="border-t border-white/8 px-4 py-3">
        <h4 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
          Accountability
        </h4>
        <div className="mt-3 space-y-2">
          <details open className="rounded-md border border-white/8 px-3 py-2">
            <summary className="cursor-pointer text-sm font-semibold text-[#eef4ff]">
              Scene contract
            </summary>
            <div className="mt-2 space-y-2">
              <FactRow
                label="Hash"
                value={incident.scene_contract_hash?.slice(0, 12) ?? "Not attached"}
                compact
              />
              {accountability.sceneContract.data ? (
                <FactRow
                  label="Schema"
                  value={`v${accountability.sceneContract.data.schema_version}`}
                  compact
                />
              ) : null}
            </div>
          </details>

          <details open className="rounded-md border border-white/8 px-3 py-2">
            <summary className="cursor-pointer text-sm font-semibold text-[#eef4ff]">
              Privacy manifest
            </summary>
            <div className="mt-2 space-y-2">
              <FactRow
                label="Hash"
                value={incident.privacy_manifest_hash?.slice(0, 12) ?? "Not attached"}
                compact
              />
              {accountability.privacyManifest.data ? (
                <>
                  <FactRow
                    label="Face ID"
                    value={identityStatusLabel(
                      accountability.privacyManifest.data,
                      "face_identification",
                    )}
                    compact
                  />
                  <FactRow
                    label="Biometric ID"
                    value={identityStatusLabel(
                      accountability.privacyManifest.data,
                      "biometric_identification",
                    )}
                    compact
                  />
                </>
              ) : null}
            </div>
          </details>

          <details open className="rounded-md border border-white/8 px-3 py-2">
            <summary className="cursor-pointer text-sm font-semibold text-[#eef4ff]">
              Ledger
            </summary>
            <div className="mt-2 space-y-2">
              {accountability.ledgerEntries.data?.length ? (
                accountability.ledgerEntries.data.map((entry) => (
                  <FactRow
                    key={entry.id}
                    label={`#${entry.sequence}`}
                    value={entry.action}
                    compact
                  />
                ))
              ) : (
                <FactRow label="Entries" value="No ledger entries" compact />
              )}
            </div>
          </details>
        </div>
      </div>

    </InstrumentRail>
  );
}

function useIncidentAccountabilityDetails(incident: Incident) {
  const sceneContract = useQuery<SceneContractSnapshot | null>({
    queryKey: ["incident-scene-contract", incident.id],
    enabled: Boolean(incident.scene_contract_id || incident.scene_contract_hash),
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/incidents/{incident_id}/scene-contract",
        { params: { path: { incident_id: incident.id } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load scene contract.");
      }
      return data ?? null;
    },
  });

  const privacyManifest = useQuery<PrivacyManifestSnapshot | null>({
    queryKey: ["incident-privacy-manifest", incident.id],
    enabled: Boolean(
      incident.privacy_manifest_id || incident.privacy_manifest_hash,
    ),
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/incidents/{incident_id}/privacy-manifest",
        { params: { path: { incident_id: incident.id } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load privacy manifest.");
      }
      return data ?? null;
    },
  });

  const ledgerEntries = useQuery<EvidenceLedgerEntry[]>({
    queryKey: ["incident-ledger", incident.id],
    enabled: (incident.ledger_summary?.entry_count ?? 0) > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/incidents/{incident_id}/ledger",
        { params: { path: { incident_id: incident.id } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load evidence ledger.");
      }
      return data ?? [];
    },
  });

  return { sceneContract, privacyManifest, ledgerEntries };
}

function identityStatusLabel(
  snapshot: PrivacyManifestSnapshot,
  key: "face_identification" | "biometric_identification",
) {
  const identity =
    snapshot.manifest.identity &&
    typeof snapshot.manifest.identity === "object" &&
    !Array.isArray(snapshot.manifest.identity)
      ? (snapshot.manifest.identity as Record<string, unknown>)
      : {};
  const status = identity[key] === "disabled" ? "disabled" : "unknown";
  return key === "face_identification"
    ? `Face ID ${status}`
    : `Biometric ID ${status}`;
}

function FactRow({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: string;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "" : "px-4 py-3"}>
      <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7087a8]">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm text-[#d7e3f5]">{value}</dd>
    </div>
  );
}

function StatusMessage({
  children,
  tone = "muted",
}: {
  children: string;
  tone?: "muted" | "danger";
}) {
  return (
    <div
      className={`rounded-[1rem] border px-4 py-3 text-sm ${
        tone === "danger"
          ? "border-[#6f2d3b] bg-[#2a0d16] text-[#f0b7c1]"
          : "border-white/10 bg-white/[0.025] text-[#9eb0cb]"
      }`}
    >
      {children}
    </div>
  );
}

function cameraNameFor(
  incident: Incident,
  cameraNamesById: Map<string, string>,
) {
  return (
    incident.camera_name ??
    cameraNamesById.get(incident.camera_id) ??
    incident.camera_id
  );
}

export function storageLabel(storageBytes: number) {
  if (storageBytes <= 0) {
    return "No clip storage";
  }

  return `${(storageBytes / (1024 * 1024)).toFixed(1)} MB secured`;
}

export function formatIncidentTime(timestamp: string) {
  return new Date(timestamp).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function evidenceHeroTitle(kind: ReturnType<typeof describeEvidenceState>["kind"]) {
  if (kind === "clip_only") {
    return "Clip-only evidence";
  }
  if (kind === "metadata_only") {
    return "Metadata-only evidence";
  }
  if (kind === "snapshot_only") {
    return "Snapshot-only evidence";
  }
  return "Clip and snapshot evidence";
}

function reviewMutationErrorMessage(error: unknown) {
  if (error instanceof Error) {
    if (/insufficient role/i.test(error.message)) {
      return "Operator access is required to change review state.";
    }

    return error.message;
  }

  return "Failed to update review state.";
}
