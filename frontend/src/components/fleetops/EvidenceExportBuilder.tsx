import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { asRecord, humanizeKey, textValue, type JsonRecord } from "./types";

type EvidenceExportBuilderProps = {
  evidenceContext?: JsonRecord | null;
};

export function EvidenceExportBuilder({
  evidenceContext,
}: EvidenceExportBuilderProps) {
  const context = asRecord(evidenceContext);

  return (
    <WorkspaceSurface className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Evidence queue
          </p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
            Export builder
          </h2>
        </div>
        <Button>Prepare export</Button>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Metric label="Vessel" value={textValue(context.vessel_name, "Fleet vessel")} />
        <Metric label="Port" value={textValue(context.port_name, "At sea")} />
        <Metric
          label="Resolution"
          value={humanizeKey(textValue(context.resolution_source, "runtime context"))}
        />
      </div>
      <p className="mt-4 text-sm leading-6 text-[var(--vz-text-secondary)]">
        Evidence exports preserve maritime context, link state, and pack metadata
        while leaving the core evidence path unchanged.
      </p>
    </WorkspaceSurface>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3">
      <p className="text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
        {label}
      </p>
      <p className="mt-2 text-sm font-semibold text-[var(--vz-text-primary)]">
        {value}
      </p>
    </div>
  );
}
