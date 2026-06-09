import type { ReactNode } from "react";
import { Copy } from "lucide-react";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  asRecord,
  linkPriorityLanes,
  numberValue,
  probePacketLossLabel,
  probeThroughputLabel,
  textValue,
} from "@/components/link/types";

type LinkPosturePanelProps = {
  status: unknown;
  isLoading?: boolean;
  error?: unknown;
  onClearSelection?: () => void;
};

export function LinkPosturePanel({
  status,
  isLoading = false,
  error,
  onClearSelection,
}: LinkPosturePanelProps) {
  const payload = asRecord(status);
  const activeConnection = asRecord(payload.active_connection);
  const fallbackActivePath = asRecord(payload.fallback_active_path);
  const activePath = activeConnectionDisplay(
    activeConnection,
    fallbackActivePath,
  );
  const latestProbe = asRecord(payload.latest_probe);
  const hasLatestProbe = Boolean(payload.latest_probe);
  const queueDepth = asRecord(payload.queue_depth);
  const passportHash = textValue(payload.passport_hash, "");
  const shortHash = passportHash ? passportHash.slice(0, 8) : "Not recorded";

  async function copyPassportHash() {
    if (!passportHash || !navigator.clipboard) {
      return;
    }
    await navigator.clipboard.writeText(passportHash);
  }

  return (
    <WorkspaceSurface className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Selected site
          </p>
          <h2 className="mt-2 font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
            Current posture
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="ghost"
            onClick={() => {
              void copyPassportHash();
            }}
          >
            <Copy className="mr-2 size-4" aria-hidden="true" />
            Copy hash
          </Button>
          {onClearSelection ? (
            <Button variant="ghost" onClick={onClearSelection}>
              Clear selection
            </Button>
          ) : null}
        </div>
      </div>
      {isLoading ? (
        <p className="mt-4 text-sm text-[var(--vz-text-secondary)]">
          Loading link posture...
        </p>
      ) : error ? (
        <p className="mt-4 text-sm text-[var(--vz-state-risk)]">
          Link posture could not be loaded.
        </p>
      ) : (
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Metric label="Link state">
            <StatusToneBadge tone={linkTone(textValue(payload.link_state, "unknown"))}>
              {textValue(payload.link_state, "unknown")}
            </StatusToneBadge>
          </Metric>
          <Metric label="Active connection">
            <span>{activePath.label}</span>
            {activePath.detail ? (
              <span className="mt-1 block text-xs font-normal text-[var(--vz-text-muted)]">
                {activePath.detail}
              </span>
            ) : null}
          </Metric>
          <Metric label="Latest probe">
            {hasLatestProbe ? (
              <>
                {numberValue(latestProbe.latency_ms)} ms /{" "}
                {probeThroughputLabel(latestProbe)} /{" "}
                {probePacketLossLabel(latestProbe)}
              </>
            ) : (
              "No probe sample"
            )}
          </Metric>
          <Metric label="Passport hash">{shortHash}</Metric>
          <Metric label="Reachable">
            {hasLatestProbe
              ? latestProbe.reachable === false
                ? "No"
                : "Yes"
              : "Unknown"}
          </Metric>
          <Metric label="Queued transfers">
            {queuedTransferLabel(queueDepth)}
          </Metric>
        </div>
      )}
    </WorkspaceSurface>
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

function queuedTransferLabel(queueDepth: Record<string, unknown>) {
  return (
    linkPriorityLanes
      .map((lane) => [lane, numberValue(queueDepth[lane])] as const)
      .filter(([, count]) => count > 0)
      .map(([lane, count]) => `${lane} ${count}`)
      .join(" / ") || "No queued transfers"
  );
}

function activeConnectionDisplay(
  activeConnection: Record<string, unknown>,
  fallbackActivePath: Record<string, unknown>,
) {
  const transportKind = meaningfulTextValue(activeConnection.transport_kind);
  const status = meaningfulTextValue(activeConnection.status);
  if (transportKind || status) {
    return {
      label: `${transportKind || "unknown"} / ${status || "unknown"}`,
    };
  }

  const activeLabel = meaningfulTextValue(activeConnection.label);
  if (activeLabel) {
    return { label: activeLabel };
  }

  const fallbackLabel = textValue(fallbackActivePath.label, "");
  if (fallbackLabel) {
    const detail = textValue(fallbackActivePath.detail, "");
    return { detail: detail || undefined, label: fallbackLabel };
  }

  return { label: "unknown / unknown" };
}

function meaningfulTextValue(value: unknown) {
  const text = textValue(value, "");
  return text.toLowerCase() === "unknown" ? "" : text;
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
