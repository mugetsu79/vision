import { Ship } from "lucide-react";

import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  asRecord,
  textValue,
  type FleetOpsVessel,
} from "@/components/fleetops/types";

type FleetOpsScopeSelectorProps = {
  emptyLabel: string;
  onSearchChange: (value: string) => void;
  onSelectVessel: (vesselId: string) => void;
  searchValue: string;
  selectedVesselId: string | null;
  title?: string;
  vessels: FleetOpsVessel[];
};

export function FleetOpsScopeSelector({
  emptyLabel,
  onSearchChange,
  onSelectVessel,
  searchValue,
  selectedVesselId,
  title = "Choose vessel or site",
  vessels,
}: FleetOpsScopeSelectorProps) {
  const visibleVessels = filterFleetOpsVessels(vessels, searchValue);
  const hasSelection = Boolean(selectedVesselId);

  return (
    <WorkspaceSurface className="p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
            Scope
          </p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
            {title}
          </h2>
          {!hasSelection ? (
            <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
              {emptyLabel}
            </p>
          ) : null}
        </div>
        <span className="w-fit rounded-full border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-1 text-sm font-semibold text-[var(--vz-text-secondary)]">
          {selectedVesselId ? "1 scope selected" : "No scope selected"}
        </span>
      </div>

      <div className="mt-4">
        <Input
          aria-label="Search FleetOps vessel scope"
          className="max-w-xl border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-obsidian)] text-[var(--vz-text-primary)] placeholder:text-[var(--vz-text-muted)]"
          placeholder="Search vessel, site, port, or IMO"
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </div>

      <div className="mt-4 flex gap-3 overflow-x-auto pb-1">
        {visibleVessels.length === 0 ? (
          <div className="w-full rounded-lg border border-dashed border-[color:var(--vz-hair)] bg-white/[0.02] px-4 py-5 text-sm text-[var(--vz-text-secondary)]">
            No vessels match this search.
          </div>
        ) : (
          visibleVessels.map((vessel) => {
            const vesselId = textValue(vessel.id, "");
            const siteId = textValue(vessel.site_id, "No site");
            const metadata = asRecord(vessel.metadata);
            const name = textValue(vessel.name, "Unnamed vessel");
            const selected = vesselId === selectedVesselId;

            return (
              <button
                key={vesselId || name}
                aria-pressed={selected}
                className={cn(
                  "flex min-w-[16rem] items-start gap-3 rounded-lg border px-3 py-3 text-left transition",
                  selected
                    ? "border-[color:var(--vz-hair-focus)] bg-[rgba(118,224,255,0.12)]"
                    : "border-[color:var(--vz-hair)] bg-white/[0.025] hover:border-[color:var(--vz-hair-strong)]",
                )}
                disabled={!vesselId}
                type="button"
                onClick={() => onSelectVessel(vesselId)}
              >
                <Ship className="mt-0.5 size-4 shrink-0 text-[var(--vz-lens-cerulean)]" />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-[var(--vz-text-primary)]">
                    {name}
                  </span>
                  <span className="mt-1 block truncate text-xs uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
                    {siteId}
                  </span>
                  <span className="mt-2 block truncate text-xs text-[var(--vz-text-secondary)]">
                    {textValue(
                      metadata.port,
                      textValue(metadata.home_port, "FleetOps"),
                    )}
                  </span>
                </span>
              </button>
            );
          })
        )}
      </div>
    </WorkspaceSurface>
  );
}

function filterFleetOpsVessels(vessels: FleetOpsVessel[], searchValue: string) {
  const query = searchValue.trim().toLowerCase();
  if (!query) {
    return vessels;
  }
  const tokens = query.split(/\s+/);

  return vessels.filter((vessel) => {
    const metadata = asRecord(vessel.metadata);
    const haystack = [
      vessel.name,
      vessel.site_id,
      vessel.id,
      metadata.port,
      metadata.home_port,
      metadata.imo,
      metadata.mmsi,
    ]
      .map((value) => textValue(value, ""))
      .join(" ")
      .toLowerCase();

    return tokens.every((token) => haystack.includes(token));
  });
}
