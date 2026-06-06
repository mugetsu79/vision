import { DoorOpen, PackagePlus, ShieldCheck } from "lucide-react";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  asRecord,
  humanizeKey,
  textValue,
  type DiagnosticsGroup,
  type JsonRecord,
  type SupportBundle,
  type SupportDiagnosticsPayload,
  type SupportReadinessCheck,
} from "./types";

type SupportReadinessPanelProps = {
  bundles?: SupportBundle[] | JsonRecord[];
  diagnostics?: SupportDiagnosticsPayload;
  isCreatingSession?: boolean;
  isGeneratingBundle?: boolean;
  isOpeningBreakGlass?: boolean;
  onCreateSession?: () => void;
  onGenerateBundle?: () => void;
  onOpenBreakGlass?: () => void;
  siteId?: string | null;
};

export function SupportReadinessPanel({
  bundles = [],
  diagnostics,
  isCreatingSession = false,
  isGeneratingBundle = false,
  isOpeningBreakGlass = false,
  onCreateSession,
  onGenerateBundle,
  onOpenBreakGlass,
  siteId,
}: SupportReadinessPanelProps) {
  const groups = readinessGroups(diagnostics);
  const status = overallStatus(groups);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <WorkspaceSurface className="p-4 lg:col-span-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
              Readiness
            </p>
            <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
              {textValue(diagnostics?.label, "Support readiness")}
            </h2>
          </div>
          <StatusToneBadge tone={overallTone(status)}>
            {humanizeKey(status)}
          </StatusToneBadge>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {groups.map((group) => (
            <ReadinessGroupCard group={group} key={textValue(group.id, group.label)} />
          ))}
        </div>
      </WorkspaceSurface>
      <WorkspaceSurface className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
              Support bundles
            </p>
            <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
              {bundles.length} prepared bundles
            </h2>
          </div>
          <Button
            disabled={!siteId || isGeneratingBundle}
            onClick={onGenerateBundle}
            variant="secondary"
          >
            <PackagePlus className="mr-2 size-4" aria-hidden="true" />
            Generate bundle
          </Button>
        </div>
        <div className="mt-4 grid gap-2">
          {(bundles.length ? bundles : [{ id: "pending", include_logs: false }]).map(
            (bundle) => (
              <div
                className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3 text-sm text-[var(--vz-text-secondary)]"
                key={textValue(bundle.id)}
              >
                Bundle {textValue(bundle.id).slice(0, 8)} / logs{" "}
                {bundle.include_logs ? "included" : "deferred"}
              </div>
            ),
          )}
        </div>
      </WorkspaceSurface>
      <WorkspaceSurface className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
              Tunnel lifecycle
            </p>
            <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
              Supervisor handoff ready
            </h2>
          </div>
          <Button
            disabled={!siteId || isCreatingSession}
            onClick={onCreateSession}
            variant="ghost"
          >
            <ShieldCheck className="mr-2 size-4" aria-hidden="true" />
            Start session
          </Button>
        </div>
        <p className="mt-3 text-sm leading-6 text-[var(--vz-text-secondary)]">
          Tunnel requests stay supervisor-managed and auditable, with credential
          references kept out of the browser.
        </p>
      </WorkspaceSurface>
      <WorkspaceSurface className="p-4 lg:col-span-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
              Break-glass
            </p>
            <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
              Approval required
            </h2>
          </div>
          <Button
            disabled={!siteId || isOpeningBreakGlass}
            onClick={onOpenBreakGlass}
            variant="ghost"
          >
            <DoorOpen className="mr-2 size-4" aria-hidden="true" />
            Open break-glass
          </Button>
        </div>
        <p className="mt-3 text-sm leading-6 text-[var(--vz-text-secondary)]">
          Emergency support access is shown as a controlled lifecycle, not a
          background shortcut.
        </p>
      </WorkspaceSurface>
    </div>
  );
}

function ReadinessGroupCard({ group }: { group: DiagnosticsGroup }) {
  const checks = Array.isArray(group.checks) ? group.checks : [];

  return (
    <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
            {textValue(group.label, humanizeKey(textValue(group.id, "readiness")))}
          </p>
          <p className="mt-1 text-xs text-[var(--vz-text-muted)]">
            {textValue(group.source, "FleetOps")}
          </p>
        </div>
        <StatusToneBadge tone={statusTone(textValue(group.status, ""))}>
          {humanizeKey(textValue(group.status, "unknown"))}
        </StatusToneBadge>
      </div>
      <div className="mt-3 grid gap-2">
        {checks.map((check) => {
          const item = normalizeCheck(check);
          return (
            <div
              className="rounded-[var(--vz-r-sm)] border border-[color:var(--vz-hair)] bg-white/[0.02] px-2 py-2"
              key={textValue(item.key, item.label)}
            >
              <p className="text-xs font-semibold text-[var(--vz-text-secondary)]">
                {textValue(item.label, humanizeKey(textValue(item.key, "check")))}
              </p>
              <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-[var(--vz-text-muted)]">
                {textValue(item.status, "pending")} / {textValue(item.source, "source")}
              </p>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-xs leading-5 text-[var(--vz-text-secondary)]">
        {textValue(group.next_action, "Review this readiness group.")}
      </p>
    </div>
  );
}

function readinessGroups(diagnostics?: SupportDiagnosticsPayload) {
  const groups = diagnostics?.groups;
  if (Array.isArray(groups)) {
    return groups;
  }
  const groupRecord = asRecord(groups);
  const values = Object.entries(groupRecord).map(([id, value]) => ({
    id,
    ...asRecord(value),
  }));
  return values.length
    ? (values as DiagnosticsGroup[])
    : [
        {
          id: "connectivity",
          label: "Connectivity readiness",
          status: "unknown",
          checks: [],
          next_action: "Run support readiness checks.",
        },
      ];
}

function normalizeCheck(check: SupportReadinessCheck | string): SupportReadinessCheck {
  if (typeof check === "string") {
    return { key: check, label: humanizeKey(check), status: "pending" };
  }
  return check;
}

function overallStatus(groups: DiagnosticsGroup[]) {
  if (groups.some((group) => textValue(group.status, "") === "attention")) {
    return "attention";
  }
  if (groups.some((group) => textValue(group.status, "") === "blocked")) {
    return "blocked";
  }
  if (groups.every((group) => textValue(group.status, "") === "ready")) {
    return "ready";
  }
  return "unknown";
}

function overallTone(status: string) {
  if (status === "ready") {
    return "healthy";
  }
  if (status === "attention") {
    return "attention";
  }
  if (status === "blocked") {
    return "danger";
  }
  return "muted";
}

function statusTone(status: string) {
  if (status === "ready") {
    return "healthy";
  }
  if (status === "blocked" || status === "failed") {
    return "danger";
  }
  if (status === "attention" || status === "pending") {
    return "attention";
  }
  return "muted";
}
