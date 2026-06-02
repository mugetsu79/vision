import {
  kindCapability,
  operatorMessagesForField,
} from "@/components/configuration/configuration-capabilities";
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import type {
  ConfigurationCatalog,
  OperatorConfigKind,
  OperatorConfigSupportState,
} from "@/hooks/use-configuration";

type RuntimeImpactPanelProps = {
  catalog?: ConfigurationCatalog;
  kind: OperatorConfigKind;
};

const SUPPORT_TONES: Record<
  OperatorConfigSupportState,
  "healthy" | "danger" | "accent" | "muted"
> = {
  active: "healthy",
  advisory: "accent",
  requires_service: "accent",
  unsupported: "danger",
};

export function RuntimeImpactPanel({ catalog, kind }: RuntimeImpactPanelProps) {
  const capability = kindCapability(catalog, kind);
  if (!capability) {
    return null;
  }

  const messages = [
    capability.operator_summary,
    ...(capability.fields ?? []).flatMap((field) => operatorMessagesForField(field)),
  ].filter((message): message is string => Boolean(message));

  if (messages.length === 0 && !capability.runtime_support) {
    return null;
  }

  return (
    <div className="rounded-lg border border-white/10 bg-[#07101b] px-3 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#7894bd]">
          Runtime impact
        </p>
        {capability.runtime_support ? (
          <StatusToneBadge tone={SUPPORT_TONES[capability.runtime_support]}>
            {capability.runtime_support.replaceAll("_", " ")}
          </StatusToneBadge>
        ) : null}
      </div>
      {messages.length > 0 ? (
        <div className="mt-2 grid gap-1">
          {messages.map((message) => (
            <p key={message} className="text-xs leading-5 text-[#9fb2cf]">
              {message}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
