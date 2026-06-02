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
