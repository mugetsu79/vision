import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, FileDiff, Play, Send, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Camera } from "@/hooks/use-cameras";
import {
  useApplyPolicyDraft,
  useApprovePolicyDraft,
  useCreatePolicyDraft,
  useRejectPolicyDraft,
  type PolicyDraft,
} from "@/hooks/use-policy-drafts";
import { cn } from "@/lib/utils";

type PolicyDraftReviewProps = {
  camera: Camera;
  onClose?: () => void;
};

const DIFF_GROUPS = [
  ["scene_contract", "Scene contract"],
  ["privacy_manifest", "Privacy manifest"],
  ["recording_policy", "Recording policy"],
  ["runtime_vocabulary", "Vocabulary"],
  ["detection_regions", "Detection regions"],
  ["incident_rules", "Incident rules"],
] as const;

export function PolicyDraftReview({ camera, onClose }: PolicyDraftReviewProps) {
  const [prompt, setPrompt] = useState("");
  const [useLlm, setUseLlm] = useState(true);
  const [draft, setDraft] = useState<PolicyDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeDraft = draft?.camera_id === camera.id ? draft : null;
  const createDraft = useCreatePolicyDraft(camera.id);
  const approveDraft = useApprovePolicyDraft(camera.id);
  const rejectDraft = useRejectPolicyDraft(camera.id);
  const applyDraft = useApplyPolicyDraft(camera.id);
  const busy =
    createDraft.isPending ||
    approveDraft.isPending ||
    rejectDraft.isPending ||
    applyDraft.isPending;
  const canDecide = activeDraft?.status === "draft" && !busy;
  const canApply = activeDraft?.status === "approved" && !busy;
  const metadataRows = useMemo(
    () => draftMetadataRows(activeDraft),
    [activeDraft],
  );

  useEffect(() => {
    setPrompt("");
    setDraft(null);
    setError(null);
  }, [camera.id]);

  async function handleCreateDraft() {
    setError(null);
    try {
      const created = await createDraft.mutateAsync({
        prompt: prompt.trim(),
        use_llm: useLlm,
      });
      setDraft(created ?? null);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Failed to create policy draft.",
      );
    }
  }

  async function handleApprove() {
    if (!activeDraft) {
      return;
    }
    setError(null);
    try {
      const approved = await approveDraft.mutateAsync(activeDraft.id);
      setDraft(approved ?? activeDraft);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Failed to approve policy draft.",
      );
    }
  }

  async function handleReject() {
    if (!activeDraft) {
      return;
    }
    setError(null);
    try {
      const rejected = await rejectDraft.mutateAsync(activeDraft.id);
      setDraft(rejected ?? activeDraft);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Failed to reject policy draft.",
      );
    }
  }

  async function handleApply() {
    if (!activeDraft) {
      return;
    }
    setError(null);
    try {
      const applied = await applyDraft.mutateAsync(activeDraft.id);
      setDraft(applied ?? activeDraft);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Failed to apply policy draft.",
      );
    }
  }

  return (
    <section
      aria-labelledby="policy-draft-heading"
      className="rounded-[0.9rem] border border-white/8 bg-[#0b1320] p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
            Prompt-to-policy
          </p>
          <h3
            id="policy-draft-heading"
            className="mt-2 text-xl font-semibold text-[#f4f8ff]"
          >
            Policy drafts for {camera.name}
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {activeDraft ? <StatusPill status={activeDraft.status} /> : null}
          {onClose ? (
            <Button variant="ghost" onClick={onClose}>
              <XCircle aria-hidden="true" className="mr-2 h-4 w-4" />
              Close drafts
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(22rem,0.9fr)_minmax(32rem,1.4fr)]">
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (prompt.trim()) {
              void handleCreateDraft();
            }
          }}
        >
          <label
            className="block text-sm font-semibold text-[#dce7f8]"
            htmlFor="policy-intent"
          >
            Policy intent
          </label>
          <textarea
            id="policy-intent"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={8}
            className="min-h-40 w-full resize-y rounded-[0.85rem] border border-[color:var(--argus-border)] bg-[color:var(--argus-surface)] px-4 py-3 text-sm text-[var(--argus-text)] outline-none placeholder:text-[var(--argus-text-subtle)] transition duration-200 focus:border-[color:var(--argus-border-highlight)] focus:shadow-[0_0_0_4px_var(--argus-accent-soft)]"
            placeholder="Watch forklifts in the dock zone and record clips"
          />
          <label className="flex items-center gap-2 text-sm text-[#9eb2cf]">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(event) => setUseLlm(event.target.checked)}
              className="h-4 w-4 accent-[#5fb7ff]"
            />
            Use selected LLM profile
          </label>
          <Button type="submit" disabled={busy || !prompt.trim()}>
            <Send aria-hidden="true" className="mr-2 h-4 w-4" />
            Create draft
          </Button>
          <p className="text-xs uppercase tracking-[0.18em] text-[#8ea4c7]">
            Draft only
          </p>
        </form>

        <div className="space-y-4">
          {error ? (
            <div
              role="alert"
              className="rounded-[0.75rem] border border-[#65313b] bg-[#2a1218] px-3 py-2 text-sm text-[#ffc7d0]"
            >
              {error}
            </div>
          ) : null}

          {activeDraft ? (
            <>
              <div className="grid gap-3 md:grid-cols-3">
                {metadataRows.map((row) => (
                  <div
                    key={row.label}
                    className="rounded-[0.75rem] border border-white/8 bg-white/[0.03] px-3 py-3"
                  >
                    <p className="text-[11px] uppercase tracking-[0.16em] text-[#7f96b8]">
                      {row.label}
                    </p>
                    <p className="mt-2 break-words text-sm font-semibold text-[#eef4ff]">
                      {row.value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => void handleApprove()}
                  disabled={!canDecide}
                >
                  <CheckCircle2 aria-hidden="true" className="mr-2 h-4 w-4" />
                  Approve draft
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => void handleReject()}
                  disabled={!canDecide}
                >
                  <XCircle aria-hidden="true" className="mr-2 h-4 w-4" />
                  Reject draft
                </Button>
                <Button onClick={() => void handleApply()} disabled={!canApply}>
                  <Play aria-hidden="true" className="mr-2 h-4 w-4" />
                  Apply approved draft
                </Button>
              </div>

              <div className="space-y-3">
                {DIFF_GROUPS.map(([key, label]) => (
                  <DiffBlock
                    key={key}
                    label={label}
                    value={activeDraft.structured_diff?.[key]}
                  />
                ))}
              </div>
            </>
          ) : (
            <div className="rounded-[0.75rem] border border-white/8 bg-white/[0.03] px-4 py-5 text-sm text-[#9eb2cf]">
              No policy draft selected
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function StatusPill({ status }: { status: PolicyDraft["status"] }) {
  const tone =
    status === "draft"
      ? "border-[#4d6585] bg-[#101b2a] text-[#b9c9e3]"
      : status === "approved" || status === "applied"
        ? "border-[#285b45] bg-[#102019] text-[#a9dfc0]"
        : "border-[#65313b] bg-[#2a1218] text-[#ffc7d0]";
  return (
    <span
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]",
        tone,
      )}
    >
      {status}
    </span>
  );
}

function DiffBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <section className="rounded-[0.75rem] border border-white/8 bg-black/20">
      <div className="flex items-center gap-2 border-b border-white/8 px-3 py-2 text-sm font-semibold text-[#eef4ff]">
        <FileDiff aria-hidden="true" className="h-4 w-4 text-[#8ecbff]" />
        {label}
      </div>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words px-3 py-3 text-xs leading-5 text-[#b8c7dd]">
        {JSON.stringify(value ?? {}, null, 2)}
      </pre>
    </section>
  );
}

function draftMetadataRows(draft: PolicyDraft | null) {
  if (!draft) {
    return [];
  }
  return [
    {
      label: "Provider",
      value: metadataValue(draft.metadata?.llm_provider, "local"),
    },
    {
      label: "Model",
      value: metadataValue(draft.metadata?.llm_model, "fallback"),
    },
    {
      label: "Profile hash",
      value: metadataValue(draft.metadata?.llm_profile_hash, "not selected"),
    },
  ];
}

function metadataValue(value: unknown, fallback: string): string {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  return fallback;
}
