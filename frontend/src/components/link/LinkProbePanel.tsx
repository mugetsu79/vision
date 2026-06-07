import { useState } from "react";
import { Play, Plus, Trash2 } from "lucide-react";

import {
  LinkProbeDialog,
  type ProbeTargetOption,
} from "@/components/link/LinkActionDialogs";
import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  useCreateLinkProbe,
  useDeleteLinkProbe,
  useMeasureLinkProbeTargetThroughput,
  useRunLinkProbeTarget,
  type LinkProbeCreateInput,
} from "@/hooks/use-link";
import {
  asRecord,
  linkPathMetadata,
  monitoringSourceLabel,
  numberValue,
  probeLossMethodLabel,
  probeMeasurementSummary,
  probePacketLossLabel,
  probeSampleSourceLabel,
  probeSampleTargetLabel,
  probeThroughputLabel,
  textValue,
} from "@/components/link/types";

type LinkProbePanelProps = {
  siteId?: string | null;
  connections: unknown[];
  probes: unknown[];
};

export function LinkProbePanel({
  siteId,
  connections,
  probes,
}: LinkProbePanelProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const createProbe = useCreateLinkProbe({ siteId });
  const deleteProbe = useDeleteLinkProbe({ siteId });
  const runProbeTarget = useRunLinkProbeTarget({ siteId });
  const measureThroughput = useMeasureLinkProbeTargetThroughput({ siteId });
  const targets = monitoringTargetOptions(connections);
  const sortedProbes = [...probes].sort((left, right) =>
    textValue(asRecord(right).recorded_at, "").localeCompare(
      textValue(asRecord(left).recorded_at, ""),
    ),
  );

  async function handleSubmit(payload: LinkProbeCreateInput) {
    await createProbe.mutateAsync(payload);
  }

  async function handleDelete(probe: unknown) {
    const probeId = textValue(asRecord(probe).id, "");
    if (probeId) {
      await deleteProbe.mutateAsync(probeId);
    }
  }

  async function handleRunTarget(target: ProbeTargetOption) {
    await runProbeTarget.mutateAsync(target.id);
  }

  async function handleMeasureThroughput(target: ProbeTargetOption) {
    await measureThroughput.mutateAsync(target.id);
  }

  return (
    <WorkspaceSurface className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
          Monitoring
        </h2>
        <Button onClick={() => setDialogOpen(true)} disabled={!siteId}>
          <Plus className="mr-2 size-4" aria-hidden="true" />
          Add manual sample
        </Button>
      </div>
      <div className="mt-4 grid gap-3">
        {targets.length === 0 ? (
          <p className="text-sm text-[var(--vz-text-secondary)]">
            No monitoring targets configured.
          </p>
        ) : (
          targets.map((target) => (
            <div
              key={target.id}
              className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-[var(--vz-text-primary)]">
                    {target.label}
                  </p>
                  <p className="mt-1 break-all text-sm text-[var(--vz-text-secondary)]">
                    {target.address}
                  </p>
                </div>
                {canRunBackendSynthetic(target) ? (
                  <Button
                    variant="ghost"
                    onClick={() => void handleRunTarget(target)}
                    disabled={!siteId || runProbeTarget.isPending}
                    aria-label={`Run check now ${target.label}`}
                  >
                    <Play className="mr-2 size-4" aria-hidden="true" />
                    Run check now
                  </Button>
                ) : null}
                {canMeasureThroughput(target) ? (
                  <Button
                    variant="ghost"
                    onClick={() => void handleMeasureThroughput(target)}
                    disabled={!siteId || measureThroughput.isPending}
                    aria-label={`Measure throughput ${target.label}`}
                  >
                    <Play className="mr-2 size-4" aria-hidden="true" />
                    Measure throughput
                  </Button>
                ) : null}
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
                <span>
                  {target.probe_type.toUpperCase()}
                  {target.port ? `:${target.port}` : ""}
                </span>
                <span>{target.connection_label ?? "Link path"}</span>
              </div>
              <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
                {target.monitoring.enabled
                  ? monitoringSourceLabel(
                      target.monitoring.source_type,
                      target.monitoring.interval_seconds,
                    )
                  : "Monitoring disabled"}
              </p>
              {target.monitoring.source_type === "edge_agent" ? (
                <p className="mt-1 text-sm text-[var(--vz-text-secondary)]">
                  {probeLossMethodLabel(target.loss_method)}
                  {target.loss_packet_count
                    ? ` / ${target.loss_packet_count} packets`
                    : ""}
                </p>
              ) : null}
            </div>
          ))
        )}
      </div>
      <div className="mt-5 grid gap-2">
        <h3 className="font-[family-name:var(--vz-font-display)] text-sm font-semibold text-[var(--vz-text-primary)]">
          Sample history
        </h3>
        {sortedProbes.length === 0 ? (
          <p className="text-sm text-[var(--vz-text-secondary)]">
            No samples recorded.
          </p>
        ) : (
          sortedProbes.map((probe, index) => {
            const item = asRecord(probe);
            const label = probeSampleTargetLabel(probe);
            return (
              <div
                key={textValue(item.id, `probe-${index}`)}
                className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3 text-sm text-[var(--vz-text-secondary)]"
              >
                <div>
                  <p className="text-[var(--vz-text-primary)]">{label}</p>
                  <p className="mt-1">
                    {numberValue(item.latency_ms)} ms /{" "}
                    {probeThroughputLabel(probe)} /{" "}
                    {probePacketLossLabel(probe)} /{" "}
                    {item.reachable === false ? "unreachable" : "reachable"}
                  </p>
                  <p className="mt-1 text-xs text-[var(--vz-text-muted)]">
                    {probeSampleSourceLabel(probe)}
                  </p>
                  {textValue(item.source_type, "") === "edge_agent" ? (
                    <p className="mt-1 text-xs text-[var(--vz-text-muted)]">
                      {probeMeasurementSummary(probe)}
                    </p>
                  ) : null}
                </div>
                <Button
                  variant="ghost"
                  onClick={() => void handleDelete(probe)}
                  disabled={!siteId || deleteProbe.isPending}
                  aria-label="Delete sample"
                >
                  <Trash2 className="mr-2 size-4" aria-hidden="true" />
                  Delete
                </Button>
              </div>
            );
          })
        )}
      </div>
      <LinkProbeDialog
        open={dialogOpen}
        connections={connections}
        targets={targets}
        isSubmitting={createProbe.isPending}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleSubmit}
      />
    </WorkspaceSurface>
  );
}

function monitoringTargetOptions(connections: unknown[]): ProbeTargetOption[] {
  const targets: ProbeTargetOption[] = [];
  connections.forEach((connection, connectionIndex) => {
    const item = asRecord(connection);
    const connectionId = textValue(item.id, `connection-${connectionIndex}`);
    const connectionLabel = textValue(item.label, connectionId);
    const metadata = linkPathMetadata(item.metadata);
    metadata.monitoring_targets.forEach((target, targetIndex) => {
      targets.push({
        ...target,
        connection_id: connectionId,
        connection_label: connectionLabel,
        id: target.id || `${connectionId}-target-${targetIndex + 1}`,
      });
    });
  });
  return targets;
}

function canRunBackendSynthetic(target: ProbeTargetOption) {
  return (
    target.monitoring.enabled &&
    target.monitoring.source_type === "backend_synthetic" &&
    target.probe_type !== "icmp" &&
    target.probe_type !== "udp"
  );
}

function canMeasureThroughput(target: ProbeTargetOption) {
  return (
    target.monitoring.enabled &&
    target.monitoring.source_type === "backend_synthetic" &&
    target.probe_type !== "icmp" &&
    target.probe_type !== "udp" &&
    Boolean(target.throughput_test_url)
  );
}
