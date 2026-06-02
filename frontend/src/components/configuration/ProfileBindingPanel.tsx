import { Link2, Unlink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { labelForKind } from "@/components/configuration/configuration-copy";
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import type {
  OperatorConfigBindingResponse,
  OperatorConfigKind,
  OperatorConfigProfile,
  OperatorConfigScope,
} from "@/hooks/use-configuration";

type BindingTarget = {
  id: string;
  label: string;
};

type ProfileBindingPanelProps = {
  kind: OperatorConfigKind;
  profiles: OperatorConfigProfile[];
  bindings?: OperatorConfigBindingResponse[];
  cameras: BindingTarget[];
  sites: BindingTarget[];
  edgeNodes: BindingTarget[];
  onBind: (payload: {
    kind: OperatorConfigKind;
    scope: OperatorConfigScope;
    scope_key: string;
    profile_id: string;
  }) => Promise<void> | void;
  onUnbind?: (bindingId: string) => Promise<void> | void;
};

export function ProfileBindingPanel({
  kind,
  profiles,
  bindings = [],
  cameras,
  sites,
  edgeNodes,
  onBind,
  onUnbind,
}: ProfileBindingPanelProps) {
  const [profileId, setProfileId] = useState(profiles[0]?.id ?? "");
  const [scope, setScope] = useState<OperatorConfigScope>("camera");
  const targets = useMemo(
    () => ({
      tenant: [{ id: "tenant", label: "Tenant default" }],
      site: sites,
      edge_node: edgeNodes,
      camera: cameras,
    }),
    [cameras, edgeNodes, sites],
  );
  const targetOptions = targets[scope];
  const [targetId, setTargetId] = useState(targetOptions[0]?.id ?? "tenant");

  useEffect(() => {
    if (!profiles.some((profile) => profile.id === profileId)) {
      setProfileId(profiles[0]?.id ?? "");
    }
  }, [profileId, profiles]);

  useEffect(() => {
    if (scope !== "tenant" && !targetOptions.some((target) => target.id === targetId)) {
      setTargetId(targetOptions[0]?.id ?? "");
    }
  }, [scope, targetId, targetOptions]);

  const resolvedTargetId =
    scope === "tenant" ? "tenant" : targetOptions.some((target) => target.id === targetId)
      ? targetId
      : targetOptions[0]?.id ?? "";
  const selectedProfile = profiles.find((profile) => profile.id === profileId) ?? null;
  const selectedTargetLabel = targetLabelForScope(scope, resolvedTargetId, targets);
  const directReplacement = bindings.find(
    (binding) =>
      binding.kind === kind
      && binding.scope === scope
      && binding.scope_key === resolvedTargetId,
  );
  const directReplacementProfile = directReplacement
    ? profiles.find((profile) => profile.id === directReplacement.profile_id)
    : undefined;

  async function handleBind() {
    if (!profileId || !resolvedTargetId) {
      return;
    }
    await onBind({
      kind,
      scope,
      scope_key: resolvedTargetId,
      profile_id: profileId,
    });
  }

  return (
    <section
      data-testid="configuration-binding-panel"
      className="space-y-3 border-t border-white/10 pt-4"
    >
      <div className="flex items-center gap-2 text-sm font-semibold text-[var(--vz-text-primary)]">
        <Link2 className="size-4 text-[#8fd3ff]" />
        <h3>{labelForKind(kind)} bindings</h3>
      </div>
      {bindings.length > 0 ? (
        <div className="grid gap-2">
          {bindings.map((binding) => {
            const profile = profiles.find((item) => item.id === binding.profile_id);
            const targetLabel = targetLabelForBinding(binding, targets);
            return (
              <div
                key={binding.id}
                data-testid={`configuration-binding-${binding.id}`}
                className="grid gap-3 rounded-lg border border-white/10 bg-[#07101b] px-3 py-3 md:grid-cols-[minmax(0,1fr)_auto]"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-semibold text-[#f4f8ff]">
                      {profile?.name ?? binding.profile_id}
                    </p>
                    <StatusToneBadge tone="muted">
                      {binding.scope.replaceAll("_", " ")}
                    </StatusToneBadge>
                  </div>
                  <p className="mt-1 text-xs text-[#93a7c5]">{targetLabel}</p>
                </div>
                {onUnbind ? (
                  <div className="flex items-center justify-end">
                    <Button
                      type="button"
                      variant="ghost"
                      className="px-3 py-1.5 text-xs"
                      onClick={() => void onUnbind(binding.id)}
                    >
                      <Unlink className="mr-2 size-3.5" />
                      Unbind
                    </Button>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="rounded-lg border border-white/10 bg-[#07101b] px-3 py-3 text-xs text-[#93a7c5]">
          No direct bindings for this profile kind.
        </p>
      )}
      <div className="rounded-lg border border-white/10 bg-[#07101b] px-3 py-3 text-xs leading-5 text-[#9fb2cf]">
        <p>
          Camera binding wins, then edge node, then site. Tenant default is the fallback.
        </p>
        <p className="mt-1">
          Test profiles before binding; workers apply the resolved profile after their
          next config refresh or lifecycle action.
        </p>
      </div>
      <BindingImpactPreview
        profile={selectedProfile}
        scope={scope}
        targetLabel={selectedTargetLabel}
        directReplacement={directReplacement}
        directReplacementProfile={directReplacementProfile}
      />
      <div className="grid gap-3 md:grid-cols-4">
        <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
          Profile
          <Select
            aria-label="Profile"
            value={profileId}
            onChange={(event) => setProfileId(event.target.value)}
          >
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </Select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
          Binding scope
          <Select
            aria-label="Binding scope"
            value={scope}
            onChange={(event) => {
              const nextScope = event.target.value as OperatorConfigScope;
              setScope(nextScope);
              setTargetId(targets[nextScope][0]?.id ?? "tenant");
            }}
          >
            <option value="camera">Camera</option>
            <option value="site">Site</option>
            <option value="edge_node">Edge node</option>
            <option value="tenant">Tenant</option>
          </Select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
          Target
          <Select
            aria-label="Target"
            value={resolvedTargetId}
            disabled={scope === "tenant"}
            onChange={(event) => setTargetId(event.target.value)}
          >
            {targetOptions.map((target) => (
              <option key={target.id} value={target.id}>
                {target.label}
              </option>
            ))}
          </Select>
        </label>
        <div className="flex items-end">
          <Button type="button" onClick={() => void handleBind()}>
            <Link2 className="mr-2 size-4" />
            Bind profile
          </Button>
        </div>
      </div>
    </section>
  );
}

function BindingImpactPreview({
  profile,
  scope,
  targetLabel,
  directReplacement,
  directReplacementProfile,
}: {
  profile: OperatorConfigProfile | null;
  scope: OperatorConfigScope;
  targetLabel: string;
  directReplacement: OperatorConfigBindingResponse | undefined;
  directReplacementProfile: OperatorConfigProfile | undefined;
}) {
  const sameDirectProfile = Boolean(
    profile && directReplacement?.profile_id === profile.id,
  );
  const replacementName =
    directReplacementProfile?.name ?? directReplacement?.profile_id ?? null;
  const shortHash = profile?.config_hash.slice(0, 8) ?? null;
  const validation = profile?.validation_status.replaceAll("_", " ") ?? "unvalidated";

  return (
    <div
      data-testid="configuration-binding-preview"
      className="rounded-lg border border-[#8fd3ff]/20 bg-[#07101b] px-3 py-3 text-xs leading-5 text-[#9fb2cf]"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8fd3ff]">
          Will affect
        </p>
        {profile ? (
          <StatusToneBadge tone={validationTone(profile.validation_status)}>
            validation {validation}
          </StatusToneBadge>
        ) : null}
      </div>
      <dl className="mt-2 grid gap-2 md:grid-cols-3">
        <div>
          <dt className="font-semibold text-[#d8e2f2]">Profile</dt>
          <dd>{profile?.name ?? "Select a profile"}</dd>
          {shortHash ? <dd className="text-[#7894bd]">desired hash {shortHash}</dd> : null}
        </div>
        <div>
          <dt className="font-semibold text-[#d8e2f2]">Scope</dt>
          <dd>{scopeLabel(scope)}</dd>
        </div>
        <div>
          <dt className="font-semibold text-[#d8e2f2]">Target</dt>
          <dd>{targetLabel}</dd>
        </div>
      </dl>
      <p className="mt-2">
        {directReplacement
          ? sameDirectProfile
            ? `Existing direct binding already uses ${replacementName}.`
            : `Replaces direct binding: ${replacementName}.`
          : "No direct binding exists for this scope and target yet."}
      </p>
      <p className="mt-1">
        {shortHash
          ? sameDirectProfile
            ? `Workers may already report applied hash ${shortHash}; use config refresh or lifecycle action if they have not refreshed.`
            : `Workers need a config refresh or lifecycle action, then should report applied hash ${shortHash}.`
          : "Workers apply the resolved profile after their next config refresh or lifecycle action."}
      </p>
      {profile?.validation_message ? (
        <p className="mt-1 text-amber-100">{profile.validation_message}</p>
      ) : null}
    </div>
  );
}

function targetLabelForBinding(
  binding: OperatorConfigBindingResponse,
  targets: Record<OperatorConfigScope, BindingTarget[]>,
) {
  if (binding.scope === "tenant") {
    return "Tenant default";
  }
  return (
    targets[binding.scope].find((target) => target.id === binding.scope_key)?.label
    ?? binding.scope_key
  );
}

function targetLabelForScope(
  scope: OperatorConfigScope,
  targetId: string,
  targets: Record<OperatorConfigScope, BindingTarget[]>,
) {
  if (scope === "tenant") {
    return "Tenant default";
  }
  return targets[scope].find((target) => target.id === targetId)?.label ?? targetId;
}

function scopeLabel(scope: OperatorConfigScope) {
  return scope.replaceAll("_", " ");
}

function validationTone(
  status: OperatorConfigProfile["validation_status"],
): "healthy" | "danger" | "accent" | "muted" {
  if (status === "valid") {
    return "healthy";
  }
  if (status === "invalid") {
    return "danger";
  }
  if (status === "unvalidated") {
    return "accent";
  }
  return "muted";
}
