import { useState } from "react";
import { Plus } from "lucide-react";

import { LinkProbeDialog } from "@/components/link/LinkActionDialogs";
import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { useCreateLinkProbe, type LinkProbeCreateInput } from "@/hooks/use-link";
import { asRecord, numberValue, textValue } from "@/components/link/types";

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
  const sortedProbes = [...probes].sort((left, right) =>
    textValue(asRecord(right).recorded_at, "").localeCompare(
      textValue(asRecord(left).recorded_at, ""),
    ),
  );

  async function handleSubmit(payload: LinkProbeCreateInput) {
    await createProbe.mutateAsync(payload);
  }

  return (
    <WorkspaceSurface className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
          Probe history
        </h2>
        <Button onClick={() => setDialogOpen(true)} disabled={!siteId}>
          <Plus className="mr-2 size-4" aria-hidden="true" />
          Record probe
        </Button>
      </div>
      <div className="mt-4 grid gap-2">
        {sortedProbes.length === 0 ? (
          <p className="text-sm text-[var(--vz-text-secondary)]">
            No probes recorded.
          </p>
        ) : (
          sortedProbes.map((probe, index) => {
            const item = asRecord(probe);
            return (
              <div
                key={textValue(item.id, `probe-${index}`)}
                className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3 text-sm text-[var(--vz-text-secondary)]"
              >
                {numberValue(item.latency_ms)} ms /{" "}
                {numberValue(item.throughput_mbps)} Mbps /{" "}
                {numberValue(item.packet_loss_percent)}% loss from{" "}
                {textValue(item.source)}
              </div>
            );
          })
        )}
      </div>
      <LinkProbeDialog
        open={dialogOpen}
        connections={connections}
        isSubmitting={createProbe.isPending}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleSubmit}
      />
    </WorkspaceSurface>
  );
}
