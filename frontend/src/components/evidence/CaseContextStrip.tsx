import { useId, useState } from "react";

import type { Incident } from "@/hooks/use-incidents";

import {
  evidenceStorageLabel,
  hashPrefix,
  primaryClipArtifact,
} from "./evidence-artifacts";
import { describeEvidenceState } from "./evidence-signals";

export function CaseContextStrip({ incident }: { incident: Incident }) {
  const [payloadOpen, setPayloadOpen] = useState(false);
  const rawPayloadId = useId();
  const evidenceState = describeEvidenceState(incident);
  const artifact = primaryClipArtifact(incident);
  const ledgerCount = incident.ledger_summary?.entry_count ?? 0;

  return (
    <section
      data-testid="case-context-strip"
      aria-label="Case context"
      className="border-b border-white/8 bg-[#07101b] px-5 py-4"
    >
      <div className="grid gap-3 md:grid-cols-5">
        <ContextCell
          label="Evidence state"
          value={evidenceState.label}
          detail={evidenceState.detail}
        />
        <ContextCell
          label="Scene contract"
          value={hashPrefix(incident.scene_contract_hash)}
          detail={incident.scene_contract_hash ? "Attached" : "Missing"}
        />
        <ContextCell
          label="Privacy manifest"
          value={hashPrefix(incident.privacy_manifest_hash)}
          detail={incident.privacy_manifest_hash ? "Attached" : "Missing"}
        />
        <ContextCell
          label="Evidence clip"
          value={evidenceStorageLabel(incident)}
          detail={
            artifact ? artifactStatusLabel(artifact.status) : "No artifact"
          }
        />
        <ContextCell
          label="Ledger"
          value={ledgerCount === 1 ? "1 entry" : `${ledgerCount} entries`}
          detail={`${ledgerCount} ledger ${ledgerCount === 1 ? "entry" : "entries"}`}
        />
      </div>

      <div className="mt-3 border-t border-white/8 pt-3">
        <button
          type="button"
          aria-expanded={payloadOpen}
          aria-controls={rawPayloadId}
          onClick={() => setPayloadOpen((current) => !current)}
          className="text-xs font-semibold uppercase tracking-[0.16em] text-[#9fc8ff] transition hover:text-white"
        >
          {payloadOpen ? "Hide raw payload" : "Show raw payload"}
        </button>
        {payloadOpen ? (
          <pre
            id={rawPayloadId}
            className="mt-3 max-h-48 overflow-auto rounded-md bg-black/35 p-3 text-xs text-[#d8e2f2]"
          >
            {JSON.stringify(incident.payload, null, 2)}
          </pre>
        ) : null}
      </div>
    </section>
  );
}

function ContextCell({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7894bd]">
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-semibold text-[#eef4ff]">
        {value}
      </p>
      <p className="mt-1 line-clamp-2 text-xs text-[#8fa4c4]">{detail}</p>
    </div>
  );
}

function artifactStatusLabel(status: string): string {
  if (status === "local_only") {
    return "Local only";
  }
  if (status === "remote_available") {
    return "Reviewable";
  }
  if (status === "available") {
    return "Available";
  }
  if (status === "upload_pending") {
    return "Upload pending";
  }
  return "Unavailable";
}
