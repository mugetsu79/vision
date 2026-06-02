import { Copy, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import type { OperatorConfigProfile } from "@/hooks/use-configuration";

type ProfileInventoryProps = {
  profiles: OperatorConfigProfile[];
  selectedProfileId?: string | null;
  bindingCountByProfileId?: Map<string, number>;
  onSelect: (profile: OperatorConfigProfile) => void;
  onSetDefault: (profile: OperatorConfigProfile) => void;
  onDuplicate: (profile: OperatorConfigProfile) => void;
  onDelete: (profile: OperatorConfigProfile) => void;
};

export function ProfileInventory({
  profiles,
  selectedProfileId,
  bindingCountByProfileId = new Map(),
  onSelect,
  onSetDefault,
  onDuplicate,
  onDelete,
}: ProfileInventoryProps) {
  if (profiles.length === 0) {
    return (
      <p className="rounded-lg border border-white/10 px-3 py-3 text-sm text-[#93a7c5]">
        No profiles yet.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {profiles.map((profile) => {
        const selected = selectedProfileId === profile.id;
        const bindingCount = bindingCountByProfileId.get(profile.id) ?? 0;
        return (
          <div
            key={profile.id}
            className={[
              "rounded-lg border bg-black/15 p-3 transition",
              selected ? "border-[#8fd3ff]/60" : "border-white/10",
            ].join(" ")}
          >
            <button
              type="button"
              className="block w-full text-left"
              onClick={() => onSelect(profile)}
            >
              <span className="block truncate text-sm font-semibold text-[#f4f8ff]">
                {profile.name}
              </span>
              <span className="mt-1 block truncate text-xs text-[#93a7c5]">
                {profile.slug}
              </span>
            </button>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {profile.is_default ? (
                <StatusToneBadge tone="accent">Default</StatusToneBadge>
              ) : (
                <Button
                  type="button"
                  variant="ghost"
                  className="px-3 py-1.5 text-xs"
                  onClick={() => onSetDefault(profile)}
                >
                  Set default
                </Button>
              )}
              <StatusToneBadge
                tone={profile.validation_status === "valid" ? "healthy" : "muted"}
              >
                {profile.validation_status === "unvalidated"
                  ? "not tested"
                  : profile.validation_status}
              </StatusToneBadge>
              <StatusToneBadge tone={bindingCount > 0 ? "accent" : "muted"}>
                {bindingCount} {bindingCount === 1 ? "binding" : "bindings"}
              </StatusToneBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                type="button"
                variant="ghost"
                className="px-3 py-1.5 text-xs"
                onClick={() => onDuplicate(profile)}
              >
                <Copy className="mr-2 size-3.5" />
                Duplicate
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="px-3 py-1.5 text-xs"
                onClick={() => onDelete(profile)}
              >
                <Trash2 className="mr-2 size-3.5" />
                Delete
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
