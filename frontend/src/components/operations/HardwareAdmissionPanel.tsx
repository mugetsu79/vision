import { Cpu } from "lucide-react";

import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import type { FleetOverview } from "@/hooks/use-operations";

type Worker = FleetOverview["camera_workers"][number];

export function HardwareAdmissionPanel({ worker }: { worker: Worker }) {
  const hardware = worker.latest_hardware_report ?? null;
  const admission = worker.latest_model_admission ?? null;
  const sample = hardware?.observed_performance?.[0] ?? null;
  const manualBypass = worker.lifecycle_owner === "manual_dev";

  return (
    <section
      data-testid="hardware-admission-panel"
      className="mt-3 rounded-[0.85rem] border border-white/8 bg-white/[0.025] p-3"
      aria-label={`Hardware admission for ${worker.camera_name}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8ea8cf]">
            <Cpu className="size-3.5" />
            Hardware admission
          </h4>
          <p className="mt-1 text-sm text-[#d8e2f2]">
            {manualBypass
              ? "Manual worker: production admission bypass."
              : admission?.rationale ?? "Model admission not reported."}
          </p>
        </div>
        <StatusToneBadge tone={admissionTone(admission?.status)}>
          {manualBypass ? "bypass" : admission?.status ?? "unknown"}
        </StatusToneBadge>
      </div>

      <dl className="mt-3 grid gap-2 text-xs md:grid-cols-2">
        <AdmissionFact label="Host" value={hardware?.host_profile ?? "Not reported"} />
        <AdmissionFact label="Memory" value={formatMemory(hardware?.memory_total_mb)} />
        <AdmissionFact
          label="Accelerators"
          value={formatList(hardware?.accelerators)}
        />
        <AdmissionFact
          label="Providers"
          value={formatProviders(hardware?.provider_capabilities)}
        />
        <AdmissionFact
          label="Model"
          value={admission?.model_name ?? sample?.model_name ?? "Not reported"}
        />
        <AdmissionFact
          label="Runtime"
          value={admission?.selected_backend ?? sample?.runtime_backend ?? "Not reported"}
        />
        <AdmissionFact label="Performance" value={formatPerformance(sample)} />
        <AdmissionFact label="Thermal" value={hardware?.thermal_state ?? "Not reported"} />
      </dl>

      {admission?.recommended_model_name || admission?.recommended_backend ? (
        <p className="mt-3 rounded-md border border-sky-300/20 bg-sky-950/20 px-3 py-2 text-xs text-sky-100">
          Recommendation:{" "}
          {[admission.recommended_model_name, admission.recommended_backend]
            .filter(Boolean)
            .join(" on ")}
        </p>
      ) : null}
    </section>
  );
}

function AdmissionFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
        {label}
      </dt>
      <dd className="mt-1 truncate text-[#d8e2f2]" title={value}>
        {value}
      </dd>
    </div>
  );
}

function admissionTone(status: string | null | undefined) {
  if (status === "recommended" || status === "supported") return "healthy";
  if (status === "degraded") return "attention";
  if (status === "unsupported") return "danger";
  return "muted";
}

function formatMemory(value: number | null | undefined): string {
  return value ? `${value} MB` : "Not reported";
}

function formatList(values: string[] | null | undefined): string {
  return values && values.length > 0 ? values.join(", ") : "Not reported";
}

function formatProviders(values: Record<string, boolean> | null | undefined): string {
  if (!values) return "Not reported";
  const enabled = Object.entries(values)
    .filter(([, available]) => available)
    .map(([provider]) => provider);
  return enabled.length > 0 ? enabled.join(", ") : "Not available";
}

function formatPerformance(
  sample: NonNullable<Worker["latest_hardware_report"]>["observed_performance"][number] | null,
): string {
  if (!sample) return "Not reported";
  const p95 = sample.stage_p95_ms?.total;
  const p99 = sample.stage_p99_ms?.total;
  const pieces = [
    `${sample.input_width}x${sample.input_height}@${sample.target_fps}fps`,
    p95 != null ? `p95 ${Number(p95).toFixed(1)} ms` : null,
    p99 != null ? `p99 ${Number(p99).toFixed(1)} ms` : null,
  ].filter(Boolean);
  return pieces.join(" / ");
}
