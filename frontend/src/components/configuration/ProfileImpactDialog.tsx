import { AlertTriangle, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import type {
  OperatorConfigProfile,
  OperatorConfigProfileImpact,
} from "@/hooks/use-configuration";

type ProfileImpactDialogProps = {
  profile: OperatorConfigProfile;
  impact?: OperatorConfigProfileImpact | null;
  isLoading?: boolean;
  replacementCandidates: OperatorConfigProfile[];
  onCancel: () => void;
  onConfirm: (payload: {
    profileId: string;
    replacementDefaultProfileId?: string | null;
  }) => Promise<void> | void;
};

export function ProfileImpactDialog({
  profile,
  impact,
  isLoading = false,
  replacementCandidates,
  onCancel,
  onConfirm,
}: ProfileImpactDialogProps) {
  const candidates = useMemo(
    () =>
      replacementCandidates.filter(
        (candidate) =>
          candidate.id !== profile.id
          && candidate.kind === profile.kind
          && candidate.enabled,
      ),
    [profile.id, profile.kind, replacementCandidates],
  );
  const [replacementDefaultProfileId, setReplacementDefaultProfileId] = useState(
    candidates[0]?.id ?? "",
  );
  const requiresReplacement = Boolean(impact?.requires_replacement_default);
  const canConfirm = !requiresReplacement || Boolean(replacementDefaultProfileId);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Delete profile"
      className="fixed inset-0 z-50 grid place-items-center bg-black/70 px-4"
    >
      <div className="w-full max-w-xl rounded-lg border border-white/10 bg-[#0b111b] p-4 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div className="flex gap-3">
            <div className="grid size-9 place-items-center rounded-full border border-red-300/30 bg-red-500/10 text-red-200">
              <AlertTriangle className="size-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[#f4f8ff]">Delete profile</h3>
              <p className="mt-1 text-sm text-[#9fb2cf]">{profile.name}</p>
            </div>
          </div>
          <button
            type="button"
            className="rounded-full p-1.5 text-[#9fb2cf] transition hover:bg-white/10 hover:text-[#f4f8ff]"
            onClick={onCancel}
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <ImpactMetric
            label="Resolved targets"
            value={impact?.affected_targets_count ?? 0}
            loading={isLoading}
          />
          <ImpactMetric
            label="Direct bindings"
            value={impact?.direct_bindings?.length ?? 0}
            loading={isLoading}
          />
        </div>

        {requiresReplacement ? (
          <label className="mt-4 grid gap-1 text-sm font-medium text-[#d8e2f2]">
            Replacement default profile
            <Select
              aria-label="Replacement default profile"
              value={replacementDefaultProfileId}
              onChange={(event) => setReplacementDefaultProfileId(event.target.value)}
            >
              {candidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.name}
                </option>
              ))}
            </Select>
          </label>
        ) : null}

        {requiresReplacement && candidates.length === 0 ? (
          <p className="mt-3 rounded-lg border border-red-300/20 bg-red-500/10 px-3 py-2 text-sm text-red-100">
            Create another enabled profile of this kind before deleting this default.
          </p>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {profile.is_default ? <StatusToneBadge tone="accent">Default</StatusToneBadge> : null}
            <StatusToneBadge tone={profile.validation_status === "valid" ? "healthy" : "muted"}>
              {profile.validation_status}
            </StatusToneBadge>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={!canConfirm || isLoading}
              onClick={() =>
                void onConfirm({
                  profileId: profile.id,
                  replacementDefaultProfileId: requiresReplacement
                    ? replacementDefaultProfileId
                    : undefined,
                })
              }
            >
              <Trash2 className="mr-2 size-4" />
              Delete
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ImpactMetric({
  label,
  value,
  loading,
}: {
  label: string;
  value: number;
  loading: boolean;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-[#07101b] px-3 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7894bd]">
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold text-[#f4f8ff]">
        {loading ? "Loading" : pluralize(value, label.toLowerCase())}
      </p>
    </div>
  );
}

function pluralize(value: number, label: string) {
  if (label === "resolved targets") {
    return `${value} resolved ${value === 1 ? "target" : "targets"}`;
  }
  if (label === "direct bindings") {
    return `${value} direct ${value === 1 ? "binding" : "bindings"}`;
  }
  return String(value);
}
