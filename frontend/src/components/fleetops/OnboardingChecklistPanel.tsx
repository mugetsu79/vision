import { RefreshCw } from "lucide-react";

import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  humanizeKey,
  textValue,
  type OnboardingCheck,
  type OnboardingChecksPayload,
} from "./types";

type OnboardingChecklistPanelProps = {
  checks?: OnboardingChecksPayload | null;
  isRunningChecks?: boolean;
  onRunChecks?: () => void;
  siteId?: string | null;
};

export function OnboardingChecklistPanel({
  checks,
  isRunningChecks = false,
  onRunChecks,
  siteId,
}: OnboardingChecklistPanelProps) {
  const items = checks?.checks ?? [];

  return (
    <WorkspaceSurface className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Setup checks
          </p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
            {items.length} checks ready
          </h2>
        </div>
        <Button
          disabled={!siteId || isRunningChecks}
          onClick={onRunChecks}
          variant="secondary"
        >
          <RefreshCw className="mr-2 size-4" aria-hidden="true" />
          Run checks
        </Button>
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-2">
        {(items.length
          ? items
          : [
              {
                key: "shipboard_roles",
                label: "Shipboard support roles",
                status: "pending",
              },
            ]
        ).map((check) => (
          <CheckRow check={check} key={textValue(check.key, check.label)} />
        ))}
      </div>
    </WorkspaceSurface>
  );
}

function CheckRow({ check }: { check: OnboardingCheck }) {
  return (
    <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3">
      <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
        {textValue(check.label, humanizeKey(textValue(check.key)))}
      </p>
      <p className="mt-1 text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
        {textValue(check.status, "pending")}
      </p>
    </div>
  );
}
