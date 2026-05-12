import { useMemo, useState } from "react";

import {
  CONFIGURATION_KINDS,
  labelForKind,
} from "@/components/configuration/configuration-copy";
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import {
  useResolvedConfiguration,
  type OperatorConfigKind,
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
};

export function EffectiveConfigurationPanel({
  cameras = [],
  sites = [],
  edgeNodes = [],
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
          />
        ))}
      </div>
    </section>
  );
}

function EffectiveConfigurationRow({
  entry,
  fallbackKind,
}: {
  entry: ResolvedOperatorConfigEntry | undefined;
  fallbackKind: OperatorConfigKind;
}) {
  const kind = entry?.kind ?? fallbackKind;
  const profileName = entry?.profile_name ?? "No profile";
  const status = entry?.resolution_status === "resolved" ? "Resolved" : "Unresolved";
  const secretLabels = Object.entries(entry?.secret_state ?? {}).map(
    ([key, state]) => `${key} ${state === "present" ? "stored" : "missing"}`,
  );

  return (
    <div
      data-testid={`effective-config-${kind}`}
      className="min-w-0 rounded-lg border border-white/10 bg-[#07101b] px-3 py-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-[#dbe8ff]">{labelForKind(kind)}</p>
        <StatusToneBadge
          tone={entry?.resolution_status === "resolved" ? "healthy" : "danger"}
        >
          {status}
        </StatusToneBadge>
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-[#f4f8ff]">
        {profileName}
      </p>
      <div className="mt-2 flex flex-wrap gap-2 text-xs text-[#8fa4c4]">
        {entry?.winner_scope ? <span>{entry.winner_scope}</span> : null}
        {entry?.validation_status ? <span>{entry.validation_status}</span> : null}
        {entry?.profile_hash ? <span>{entry.profile_hash.slice(0, 8)}</span> : null}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <StatusToneBadge tone={entry?.applies_to_runtime ? "accent" : "muted"}>
          {entry?.applies_to_runtime ? "runtime-wired now" : "runtime-wired later"}
        </StatusToneBadge>
        {secretLabels.map((label) => (
          <StatusToneBadge key={label} tone="muted">
            {label}
          </StatusToneBadge>
        ))}
      </div>
      {entry?.operator_message ? (
        <p className="mt-2 text-xs leading-5 text-[#9fb2cf]">{entry.operator_message}</p>
      ) : null}
    </div>
  );
}
