import { X } from "lucide-react";
import type { ReactNode } from "react";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  asRecord,
  linkSiteRoleLabel,
  numberValue,
  probeMeasurementSummary,
  probePacketLossLabel,
  probeSampleSourceLabel,
  textValue,
  type LinkSiteSummaryItem,
} from "@/components/link/types";

type LinkMasterTargetPanelProps = {
  summary: LinkSiteSummaryItem;
  status: unknown;
  probes: unknown[];
  isLoading?: boolean;
  error?: unknown;
  onClearSelection?: () => void;
};

export function LinkMasterTargetPanel({
  summary,
  status,
  probes,
  isLoading = false,
  error,
  onClearSelection,
}: LinkMasterTargetPanelProps) {
  const payload = asRecord(status);
  const latestProbe = asRecord(payload.latest_probe ?? summary.latest_probe);
  const sortedProbes = [...probes].sort((left, right) =>
    textValue(asRecord(right).recorded_at, "").localeCompare(
      textValue(asRecord(left).recorded_at, ""),
    ),
  );
  const sourceCount = new Set(
    sortedProbes
      .map((probe) => textValue(asRecord(probe).site_id, ""))
      .filter(Boolean),
  ).size;

  return (
    <WorkspaceSurface className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            {linkSiteRoleLabel("control_plane")}
          </p>
          <h2 className="mt-2 font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
            Edge probe ingress
          </h2>
        </div>
        {onClearSelection ? (
          <Button variant="ghost" onClick={onClearSelection}>
            <X className="mr-2 size-4" aria-hidden="true" />
            Clear selection
          </Button>
        ) : null}
      </div>
      {isLoading ? (
        <p className="mt-4 text-sm text-[var(--vz-text-secondary)]">
          Loading target posture...
        </p>
      ) : error ? (
        <p className="mt-4 text-sm text-[var(--vz-state-risk)]">
          Target posture could not be loaded.
        </p>
      ) : (
        <>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric label="Target site">{summary.site_name}</Metric>
            <Metric label="Link state">
              <StatusToneBadge tone={linkTone(textValue(payload.link_state, summary.link_state))}>
                {textValue(payload.link_state, summary.link_state)}
              </StatusToneBadge>
            </Metric>
            <Metric label="Latest sample">
              {numberValue(latestProbe.latency_ms)} ms /{" "}
              {probePacketLossLabel(latestProbe)}
            </Metric>
            <Metric label="Source edges">{sourceCount}</Metric>
          </div>
          <div className="mt-5 grid gap-2">
            <h3 className="font-[family-name:var(--vz-font-display)] text-sm font-semibold text-[var(--vz-text-primary)]">
              Edge samples
            </h3>
            {sortedProbes.length === 0 ? (
              <p className="text-sm text-[var(--vz-text-secondary)]">
                No edge samples received.
              </p>
            ) : (
              sortedProbes.map((probe, index) => (
                <SampleRow
                  key={textValue(asRecord(probe).id, `target-probe-${index}`)}
                  probe={probe}
                />
              ))
            )}
          </div>
        </>
      )}
    </WorkspaceSurface>
  );
}

function SampleRow({ probe }: { probe: unknown }) {
  const item = asRecord(probe);
  return (
    <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3 text-sm text-[var(--vz-text-secondary)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-[var(--vz-text-primary)]">
            {probeSampleSourceLabel(probe)}
          </p>
          <p className="mt-1 break-all">
            {textValue(item.target_label, "Target")}{" "}
            {textValue(item.target_address, "")}
          </p>
        </div>
        <p className="text-sm font-medium text-[var(--vz-text-primary)]">
          {numberValue(item.latency_ms)} ms
        </p>
      </div>
      <div className="mt-2 flex flex-wrap gap-2 text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
        <span>{textValue(item.probe_type, "probe")}</span>
        <span>{probePacketLossLabel(probe)}</span>
        <span>{item.reachable === false ? "unreachable" : "reachable"}</span>
      </div>
      {textValue(item.source_type, "") === "edge_agent" ? (
        <p className="mt-2 text-xs text-[var(--vz-text-muted)]">
          {probeMeasurementSummary(probe)}
        </p>
      ) : null}
    </div>
  );
}

function Metric({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
        {label}
      </p>
      <div className="mt-2 text-sm font-medium text-[var(--vz-text-primary)]">
        {children}
      </div>
    </div>
  );
}

function linkTone(
  state: string,
): "healthy" | "attention" | "danger" | "muted" | "accent" {
  const normalized = state.toLowerCase();
  if (normalized.includes("healthy") || normalized.includes("online")) {
    return "healthy";
  }
  if (normalized.includes("degraded") || normalized.includes("recovering")) {
    return "attention";
  }
  if (normalized.includes("dark") || normalized.includes("offline")) {
    return "danger";
  }
  return "muted";
}
