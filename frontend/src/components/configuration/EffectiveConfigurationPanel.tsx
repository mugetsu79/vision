import { useMemo, useState } from "react";
import { Copy } from "lucide-react";

import {
  CONFIGURATION_KINDS,
  labelForKind,
} from "@/components/configuration/configuration-copy";
import { kindCapability } from "@/components/configuration/configuration-capabilities";
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import {
  useResolvedConfiguration,
  type ConfigurationCatalog,
  type OperatorConfigKind,
  type OperatorConfigSupportState,
  type ResolvedConfigurationTarget,
  type ResolvedOperatorConfigEntry,
} from "@/hooks/use-configuration";

type TargetOption = {
  id: string;
  label: string;
  target?: ResolvedConfigurationTarget;
};

type NamedTarget = {
  id: string;
  label?: string;
  name?: string;
  hostname?: string | null;
};

type EffectiveConfigurationPanelProps = {
  cameras?: NamedTarget[];
  sites?: NamedTarget[];
  edgeNodes?: NamedTarget[];
  catalog?: ConfigurationCatalog;
};

export function EffectiveConfigurationPanel({
  cameras = [],
  sites = [],
  edgeNodes = [],
  catalog,
}: EffectiveConfigurationPanelProps) {
  const targetOptions = useMemo<TargetOption[]>(
    () => [
      { id: "tenant", label: "Tenant" },
      ...sites.map((site) => ({
        id: `site:${site.id}`,
        label: site.label ?? site.name ?? site.id,
        target: { siteId: site.id },
      })),
      ...edgeNodes.map((node) => ({
        id: `edge_node:${node.id}`,
        label: node.label ?? node.hostname ?? node.id,
        target: { edgeNodeId: node.id },
      })),
      ...cameras.map((camera) => ({
        id: `camera:${camera.id}`,
        label: camera.label ?? camera.name ?? camera.id,
        target: { cameraId: camera.id },
      })),
    ],
    [cameras, edgeNodes, sites],
  );
  const defaultTarget = targetOptions.find((option) => option.id.startsWith("camera:"))
    ?? targetOptions[0];
  const [selectedTargetId, setSelectedTargetId] = useState(defaultTarget.id);
  const selectedTarget =
    targetOptions.find((option) => option.id === selectedTargetId) ?? defaultTarget;
  const resolved = useResolvedConfiguration(selectedTarget.target);
  const entries = resolved.data?.entries ?? {};

  return (
    <section
      data-testid="effective-configuration-panel"
      className="rounded-lg border border-white/10 bg-black/15 p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#7894bd]">
            Runtime view
          </p>
          <h3 className="mt-1 text-sm font-semibold text-[#f4f8ff]">
            Effective configuration
          </h3>
          <p className="mt-2 max-w-2xl text-xs leading-5 text-[#9fb2cf]">
            Desired configuration is the profile set resolved by binding precedence.
            Runtime-applied hash shows what a worker has actually reported. A mismatch
            means the UI has saved intent that the runtime has not applied yet.
          </p>
          <ul className="mt-2 grid max-w-2xl gap-1 text-xs leading-5 text-[#9fb2cf]">
            <li>
              Direct camera binding means the camera won; inherited from edge node, site,
              or tenant default means a broader binding supplied the profile.
            </li>
            <li>
              Validation status shows tested state: valid, invalid, or unvalidated before
              operators rely on the binding.
            </li>
            <li>
              Desired-only rows are saved intent without a worker report; applied hash
              and aligned mean the worker reported the same profile hash.
            </li>
          </ul>
        </div>
        <label className="grid gap-1 text-xs font-semibold text-[#9fb2cf]">
          <span>Resolved target</span>
          <select
            aria-label="Resolved target"
            className="min-w-48 rounded-lg border border-[color:var(--argus-border)] bg-[color:var(--argus-surface)] px-3 py-2 text-sm text-[var(--argus-text)] outline-none"
            value={selectedTargetId}
            onChange={(event) => setSelectedTargetId(event.target.value)}
          >
            {targetOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-4 grid gap-2 lg:grid-cols-2">
        {CONFIGURATION_KINDS.map((kind) => (
          <EffectiveConfigurationRow
            key={kind}
            entry={entries[kind]}
            fallbackKind={kind}
            catalog={catalog}
          />
        ))}
      </div>
    </section>
  );
}

function EffectiveConfigurationRow({
  entry,
  fallbackKind,
  catalog,
}: {
  entry: ResolvedOperatorConfigEntry | undefined;
  fallbackKind: OperatorConfigKind;
  catalog?: ConfigurationCatalog;
}) {
  const kind = entry?.kind ?? fallbackKind;
  const profileName = entry?.profile_name ?? "No profile";
  const status = entry?.resolution_status === "resolved" ? "Resolved" : "Unresolved";
  const capability = kindCapability(catalog, kind);
  const support = capability?.runtime_support;
  const desiredHash = entry?.profile_hash ?? null;
  const appliedHash = appliedProfileHash(entry);
  const aligned = desiredHash && appliedHash && desiredHash === appliedHash;
  const secretLabels = Object.entries(entry?.secret_state ?? {}).map(
    ([key, state]) => `${key} ${state === "present" ? "stored" : "missing"}`,
  );
  const diagnosticPayload = {
    kind,
    profile_id: entry?.profile_id ?? null,
    profile_hash: desiredHash,
    applied_profile_hash: appliedHash,
    winner_scope: entry?.winner_scope ?? null,
    validation_status: entry?.validation_status ?? null,
    resolution_status: entry?.resolution_status ?? "unresolved",
    runtime_support: support ?? null,
    operator_message: entry?.operator_message ?? null,
  };

  return (
    <div
      data-testid={`effective-config-${kind}`}
      className="min-w-0 rounded-lg border border-white/10 bg-[#07101b] px-3 py-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-[#dbe8ff]">{labelForKind(kind)}</p>
        <div className="flex flex-wrap gap-2">
          {support ? (
            <StatusToneBadge tone={supportTone(support)}>
              {support.replaceAll("_", " ")}
            </StatusToneBadge>
          ) : null}
          <StatusToneBadge
            tone={entry?.resolution_status === "resolved" ? "healthy" : "danger"}
          >
            {status}
          </StatusToneBadge>
        </div>
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-[#f4f8ff]">
        {profileName}
      </p>
      <div className="mt-2 flex flex-wrap gap-2 text-xs text-[#8fa4c4]">
        {entry?.winner_scope ? <span>{entry.winner_scope}</span> : null}
        {entry?.validation_status ? <span>{entry.validation_status}</span> : null}
        {desiredHash ? <span>desired {desiredHash.slice(0, 8)}</span> : null}
        {appliedHash ? <span>applied {appliedHash.slice(0, 8)}</span> : null}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <StatusToneBadge tone={entry?.applies_to_runtime ? "accent" : "muted"}>
          {entry?.applies_to_runtime ? "runtime-wired now" : "runtime-wired later"}
        </StatusToneBadge>
        {appliedHash ? (
          <StatusToneBadge tone={aligned ? "healthy" : "danger"}>
            {aligned ? "aligned" : "drift"}
          </StatusToneBadge>
        ) : (
          <StatusToneBadge tone="muted">applied not reported</StatusToneBadge>
        )}
        {secretLabels.map((label) => (
          <StatusToneBadge key={label} tone="muted">
            {label}
          </StatusToneBadge>
        ))}
      </div>
      {entry?.operator_message ? (
        <p className="mt-2 text-xs leading-5 text-[#9fb2cf]">{entry.operator_message}</p>
      ) : null}
      <button
        type="button"
        className="mt-3 inline-flex items-center rounded-full border border-white/10 px-3 py-1.5 text-xs font-semibold text-[#9fb2cf] transition hover:border-[#8fd3ff]/60 hover:text-[#f4f8ff]"
        onClick={() => {
          void navigator.clipboard?.writeText(JSON.stringify(diagnosticPayload, null, 2));
        }}
      >
        <Copy className="mr-2 size-3.5" />
        Copy diagnostics
      </button>
    </div>
  );
}

function appliedProfileHash(entry: ResolvedOperatorConfigEntry | undefined) {
  const value = entry?.config?.applied_profile_hash;
  return typeof value === "string" ? value : null;
}

function supportTone(
  support: OperatorConfigSupportState,
): "healthy" | "danger" | "accent" | "muted" {
  if (support === "active") {
    return "healthy";
  }
  if (support === "unsupported") {
    return "danger";
  }
  if (support === "requires_service") {
    return "accent";
  }
  return "muted";
}
