import { Link } from "react-router-dom";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import {
  healthToTone,
  type AttentionItem,
  type FleetHealth,
} from "@/lib/operational-health";

type AttentionStackProps = {
  items: AttentionItem[];
  fleetHealth: FleetHealth;
};

export function AttentionStack({ items, fleetHealth }: AttentionStackProps) {
  return (
    <WorkspaceSurface data-testid="attention-stack" className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
            Operational readiness
          </p>
          <h2 className="mt-2 text-lg font-semibold text-[var(--vz-text-primary)]">
            Attention stack
          </h2>
        </div>
        <StatusToneBadge tone={healthToTone(fleetHealth.health)}>
          {fleetHealth.label}
        </StatusToneBadge>
      </div>

      {items.length === 0 ? (
        <div className="mt-4 rounded-[var(--vz-r-md)] border border-[rgba(111,224,163,0.22)] bg-[rgba(10,36,24,0.38)] px-4 py-3">
          <p className="text-sm font-semibold text-[var(--vz-state-healthy)]">
            No operational attention needed
          </p>
          <p className="mt-1 text-sm text-[var(--vz-text-secondary)]">
            {fleetHealth.reasons[0] ?? "Fleet data is ready."}
          </p>
        </div>
      ) : (
        <div className="mt-4 divide-y divide-white/8 overflow-hidden rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)]">
          {items.map((item) => (
            <Link
              key={item.id}
              to={item.href}
              className="grid gap-3 px-4 py-3 transition hover:bg-white/[0.04] sm:grid-cols-[auto_minmax(0,1fr)_auto]"
            >
              <StatusToneBadge tone={healthToTone(item.health)}>
                {item.health}
              </StatusToneBadge>
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-[var(--vz-text-primary)]">
                  {item.title}
                </span>
                <span className="mt-1 block text-sm text-[var(--vz-text-secondary)]">
                  {item.detail}
                </span>
              </span>
              <span className="text-sm font-semibold text-[var(--vz-lens-cerulean)]">
                Open
              </span>
            </Link>
          ))}
        </div>
      )}
    </WorkspaceSurface>
  );
}
