import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  asRecord,
  humanizeKey,
  textValue,
  type OnboardingChecksPayload,
  type SupportBundle,
  type SupportDiagnosticsPayload,
} from "./types";

type SupportDiagnosticsPanelProps = {
  bundles?: SupportBundle[];
  diagnostics?: SupportDiagnosticsPayload;
  onboardingChecks?: OnboardingChecksPayload | null;
};

export function SupportDiagnosticsPanel({
  bundles = [],
  diagnostics,
  onboardingChecks,
}: SupportDiagnosticsPanelProps) {
  const groups = asRecord(diagnostics?.groups);
  const checks = onboardingChecks?.checks ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
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
          <Button>Generate bundle</Button>
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
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
          Tunnel lifecycle
        </p>
        <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
          Supervisor handoff ready
        </h2>
        <p className="mt-3 text-sm leading-6 text-[var(--vz-text-secondary)]">
          Tunnel requests stay supervisor-managed and auditable, with credential
          references kept out of the browser.
        </p>
      </WorkspaceSurface>
      <WorkspaceSurface className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
          Break-glass
        </p>
        <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
          Approval required
        </h2>
        <p className="mt-3 text-sm leading-6 text-[var(--vz-text-secondary)]">
          Emergency support access is shown as a controlled lifecycle, not a
          background shortcut.
        </p>
      </WorkspaceSurface>
      <WorkspaceSurface className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
          Onboarding checks
        </p>
        <div className="mt-4 grid gap-2">
          {(checks.length
            ? checks
            : [{ key: "shipboard_roles", label: "Shipboard support roles", status: "ready" }]
          ).map((check) => (
            <div
              className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3"
              key={textValue(check.key)}
            >
              <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
                {textValue(check.label, humanizeKey(textValue(check.key)))}
              </p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
                {textValue(check.status, "pending")}
              </p>
            </div>
          ))}
        </div>
      </WorkspaceSurface>
      {Object.keys(groups).length ? (
        <WorkspaceSurface className="p-4 lg:col-span-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Diagnostic groups
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {Object.entries(groups).map(([key, value]) => (
              <span
                className="rounded-full border border-[color:var(--vz-hair)] bg-white/[0.035] px-3 py-1 text-xs text-[var(--vz-text-secondary)]"
                key={key}
              >
                {textValue(asRecord(value).label, humanizeKey(key))}
              </span>
            ))}
          </div>
        </WorkspaceSurface>
      ) : null}
    </div>
  );
}
