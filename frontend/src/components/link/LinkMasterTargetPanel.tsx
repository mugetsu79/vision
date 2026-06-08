import { KeyRound, Power, PowerOff, X } from "lucide-react";
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
import type { LinkReflectorProfileUpdateInput } from "@/hooks/use-link";

type LinkMasterTargetPanelProps = {
  summary: LinkSiteSummaryItem;
  status: unknown;
  probes: unknown[];
  reflectorProfile?: unknown;
  reflectorIsLoading?: boolean;
  reflectorError?: unknown;
  reflectorActionPending?: boolean;
  isLoading?: boolean;
  error?: unknown;
  onClearSelection?: () => void;
  onEnableReflector?: (
    payload: LinkReflectorProfileUpdateInput,
  ) => Promise<unknown>;
  onDisableReflector?: () => Promise<unknown>;
  onRotateReflectorKey?: () => Promise<unknown>;
};

export function LinkMasterTargetPanel({
  summary,
  status,
  probes,
  reflectorProfile,
  reflectorIsLoading = false,
  reflectorError,
  reflectorActionPending = false,
  isLoading = false,
  error,
  onClearSelection,
  onEnableReflector,
  onDisableReflector,
  onRotateReflectorKey,
}: LinkMasterTargetPanelProps) {
  const payload = asRecord(status);
  const reflector = asRecord(reflectorProfile);
  const latestProbe = asRecord(payload.latest_probe ?? summary.latest_probe);
  const hasLatestProbe = Boolean(payload.latest_probe ?? summary.latest_probe);
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
              {hasLatestProbe ? (
                <>
                  {numberValue(latestProbe.latency_ms)} ms /{" "}
                  {probePacketLossLabel(latestProbe)}
                </>
              ) : (
                "No edge sample"
              )}
            </Metric>
            <Metric label="Source edges">{sourceCount}</Metric>
          </div>
          <ReflectorPanel
            profile={reflector}
            isLoading={reflectorIsLoading}
            error={reflectorError}
            actionPending={reflectorActionPending}
            onEnable={onEnableReflector}
            onDisable={onDisableReflector}
            onRotateKey={onRotateReflectorKey}
          />
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

function ReflectorPanel({
  profile,
  isLoading,
  error,
  actionPending,
  onEnable,
  onDisable,
  onRotateKey,
}: {
  profile: Record<string, unknown>;
  isLoading: boolean;
  error: unknown;
  actionPending: boolean;
  onEnable?: (payload: LinkReflectorProfileUpdateInput) => Promise<unknown>;
  onDisable?: () => Promise<unknown>;
  onRotateKey?: () => Promise<unknown>;
}) {
  const enabled = profile.enabled === true;
  const publicAddress = textValue(profile.public_address, "");
  const bindAddress = textValue(profile.bind_address, "");
  const udpPort = numberValue(profile.udp_port, 8622);
  const endpointAddress = publicAddress || bindAddress;
  const endpoint = endpointAddress ? `${endpointAddress}:${udpPort}` : "No endpoint";
  const status = enabled ? textValue(profile.last_status, "enabled") : "disabled";
  const secretState = textValue(profile.secret_state, "missing");
  const keyId = textValue(profile.key_id, "No key");
  const rateLimit = numberValue(profile.rate_limit_pps_per_source, 0);

  async function handleEnable() {
    await onEnable?.({
      public_address: publicAddress || null,
      udp_port: udpPort,
    });
  }

  return (
    <div className="mt-5 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
            Reflector
          </p>
          <h3 className="mt-1 font-[family-name:var(--vz-font-display)] text-sm font-semibold text-[var(--vz-text-primary)]">
            Master reflector
          </h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {enabled ? (
            <Button
              type="button"
              variant="ghost"
              disabled={actionPending || !onDisable}
              onClick={() => void onDisable?.()}
            >
              <PowerOff className="mr-2 size-4" aria-hidden="true" />
              Disable master reflector
            </Button>
          ) : (
            <Button
              type="button"
              variant="ghost"
              disabled={actionPending || !onEnable}
              onClick={() => void handleEnable()}
            >
              <Power className="mr-2 size-4" aria-hidden="true" />
              Enable master reflector
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            disabled={actionPending || !onRotateKey}
            onClick={() => void onRotateKey?.()}
          >
            <KeyRound className="mr-2 size-4" aria-hidden="true" />
            Rotate reflector key
          </Button>
        </div>
      </div>
      {isLoading ? (
        <p className="mt-3 text-sm text-[var(--vz-text-secondary)]">
          Loading reflector profile...
        </p>
      ) : error ? (
        <p className="mt-3 text-sm text-[var(--vz-state-risk)]">
          Reflector profile could not be loaded.
        </p>
      ) : (
        <>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Status">
              <StatusToneBadge tone={enabled ? linkTone(status) : "muted"}>
                {titleCase(status)}
              </StatusToneBadge>
            </Metric>
            <Metric label="UDP endpoint">{endpoint}</Metric>
            <Metric label="Key ID">{keyId}</Metric>
            <Metric label="Secret">{titleCase(secretState)}</Metric>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
            <span>{rateLimit} pps per source</span>
            <span>{textValue(profile.mode, "reply")}</span>
            <span>{enabled ? "measurable" : "not measurable"}</span>
          </div>
        </>
      )}
    </div>
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
          {typeof item.latency_ms === "number" ? `${item.latency_ms} ms` : "No latency"}
        </p>
      </div>
      <div className="mt-2 flex flex-wrap gap-2 text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
        <span>{textValue(item.probe_type, "probe")}</span>
        <span>{probePacketLossLabel(probe)}</span>
        <span>
          {typeof item.reachable === "boolean"
            ? item.reachable
              ? "reachable"
              : "unreachable"
            : "reachability unknown"}
        </span>
      </div>
      {textValue(item.source_type, "") === "edge_agent" ? (
        <p className="mt-2 text-xs text-[var(--vz-text-muted)]">
          {probeMeasurementSummary(probe)}
        </p>
      ) : null}
    </div>
  );
}

function titleCase(value: string) {
  const normalized = value.replaceAll("_", " ").trim();
  return normalized
    ? `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)}`
    : "Unknown";
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
