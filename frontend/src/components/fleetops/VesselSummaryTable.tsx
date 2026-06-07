import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";
import { Link } from "react-router-dom";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { asRecord, humanizeKey, textValue, type FleetOpsVessel } from "./types";

type VesselSummaryTableProps = {
  vessels: FleetOpsVessel[];
  totalVessels?: number;
  totalMatches?: number;
  page?: number;
  pageSize?: number;
  pageStart?: number;
  totalPages?: number;
  searchTerm?: string;
  linkStateFilter?: string;
  statusFilter?: "all" | "active" | "inactive";
  linkStateOptions?: string[];
  hasActiveFilters?: boolean;
  onSearchTermChange?: (value: string) => void;
  onLinkStateFilterChange?: (value: string) => void;
  onStatusFilterChange?: (value: "all" | "active" | "inactive") => void;
  onPageSizeChange?: (value: number) => void;
  onPageChange?: (value: number) => void;
  onClearFilters?: () => void;
  onAddVessel?: () => void;
};

export function VesselSummaryTable(props: VesselSummaryTableProps) {
  const { vessels, onAddVessel } = props;
  const showControls = props.totalVessels !== undefined;
  const totalVessels = props.totalVessels ?? vessels.length;
  const totalMatches = props.totalMatches ?? vessels.length;
  const page = props.page ?? 1;
  const pageSize = props.pageSize ?? 10;
  const pageStart = props.pageStart ?? 0;
  const totalPages = props.totalPages ?? 1;
  const searchTerm = props.searchTerm ?? "";
  const linkStateFilter = props.linkStateFilter ?? "all";
  const statusFilter = props.statusFilter ?? "all";
  const linkStateOptions = props.linkStateOptions ?? [];
  const hasActiveFilters = props.hasActiveFilters ?? false;
  const onSearchTermChange = props.onSearchTermChange ?? (() => undefined);
  const onLinkStateFilterChange =
    props.onLinkStateFilterChange ?? (() => undefined);
  const onStatusFilterChange = props.onStatusFilterChange ?? (() => undefined);
  const onPageSizeChange = props.onPageSizeChange ?? (() => undefined);
  const onPageChange = props.onPageChange ?? (() => undefined);
  const onClearFilters = props.onClearFilters ?? (() => undefined);

  if (totalVessels === 0) {
    return (
      <WorkspaceSurface className="p-6 text-center">
        <p className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
          No vessels are connected to FleetOps yet.
        </p>
        <p className="mx-auto mt-2 max-w-md text-sm text-[var(--vz-text-secondary)]">
          Add the first vessel to create its FleetOps site binding and start
          configuring connectivity, evidence, support, and onboarding.
        </p>
        {onAddVessel ? (
          <Button className="mt-5" variant="primary" onClick={onAddVessel}>
            Add vessel
          </Button>
        ) : null}
      </WorkspaceSurface>
    );
  }

  return (
    <WorkspaceSurface className="overflow-hidden">
      <div className="border-b border-[color:var(--vz-hair)] px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
          Vessel watch
        </h2>
      </div>
      {showControls ? (
        <div className="border-b border-[color:var(--vz-hair)] px-4 py-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div className="grid flex-1 gap-3 md:grid-cols-[minmax(18rem,1fr)_12rem_10rem_10rem]">
              <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
                Search vessels
                <span className="relative mt-2 block">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[var(--vz-text-muted)]"
                    aria-hidden="true"
                  />
                  <Input
                    aria-label="Search vessels"
                    type="search"
                    value={searchTerm}
                    onChange={(event) => onSearchTermChange(event.target.value)}
                    className="pl-10"
                    placeholder="Name, IMO, MMSI, call sign, site, or state"
                  />
                </span>
              </label>
              <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
                Link state
                <Select
                  aria-label="Link state"
                  className="mt-2"
                  value={linkStateFilter}
                  onChange={(event) =>
                    onLinkStateFilterChange(event.target.value)
                  }
                >
                  <option value="all">All link states</option>
                  {linkStateOptions.map((option) => (
                    <option key={option} value={option}>
                      {formatLinkState(option)}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
                Status
                <Select
                  aria-label="Status"
                  className="mt-2"
                  value={statusFilter}
                  onChange={(event) =>
                    onStatusFilterChange(
                      event.target.value as "all" | "active" | "inactive",
                    )
                  }
                >
                  <option value="all">All statuses</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </Select>
              </label>
              <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
                Rows per page
                <Select
                  aria-label="Rows per page"
                  className="mt-2"
                  value={String(pageSize)}
                  onChange={(event) =>
                    onPageSizeChange(Number(event.target.value))
                  }
                >
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                </Select>
              </label>
            </div>
            {hasActiveFilters ? (
              <Button variant="ghost" onClick={onClearFilters}>
                <X className="mr-2 size-4" aria-hidden="true" />
                Clear filters
              </Button>
            ) : null}
          </div>
          <p
            className="mt-3 text-sm text-[var(--vz-text-secondary)]"
            aria-live="polite"
          >
            {totalMatches === 0
              ? `0 of ${totalVessels} vessels shown`
              : `${pageStart + 1}-${pageStart + vessels.length} of ${totalMatches} vessels shown`}
          </p>
        </div>
      ) : null}
      {vessels.length === 0 ? (
        <div className="px-4 py-12 text-center">
          <p className="font-[family-name:var(--vz-font-display)] text-lg font-semibold text-[var(--vz-text-primary)]">
            No vessels match these filters.
          </p>
          <p className="mx-auto mt-2 max-w-md text-sm text-[var(--vz-text-secondary)]">
            Clear filters or search for another vessel, site, IMO, MMSI, call
            sign, link state, or status.
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-[color:var(--vz-hair)] text-left text-sm">
              <thead className="bg-white/[0.025] text-[11px] uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
                <tr>
                  <th className="px-4 py-3 font-semibold">Vessel</th>
                  <th className="px-4 py-3 font-semibold">Link state</th>
                  <th className="px-4 py-3 font-semibold">Export status</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[color:var(--vz-hair)]">
                {vessels.map((vessel) => {
                  const id = textValue(vessel.id, "unknown-vessel");
                  const metadata = asRecord(vessel.metadata);
                  const linkState = formatLinkState(metadata.link_state);
                  const evidenceQueue = textValue(
                    metadata.evidence_queue,
                    "No pending exports",
                  );
                  return (
                    <tr key={id} className="align-top">
                      <th className="px-4 py-3 font-medium text-[var(--vz-text-primary)]">
                        <Link
                          className="rounded-sm underline-offset-4 hover:text-[var(--vz-lens-cerulean)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--vz-hair-focus)]"
                          to={`/fleetops/vessels/${id}`}
                        >
                          {textValue(vessel.name, "Unnamed vessel")}
                        </Link>
                        <p className="mt-1 text-xs font-normal text-[var(--vz-text-muted)]">
                          Site {textValue(vessel.site_id, "unassigned")}
                        </p>
                      </th>
                      <td className="px-4 py-3">
                        <StatusToneBadge tone={linkTone(linkState)}>
                          {linkState}
                        </StatusToneBadge>
                      </td>
                      <td className="px-4 py-3 text-[var(--vz-text-secondary)]">
                        {evidenceQueue}
                      </td>
                      <td className="px-4 py-3 text-[var(--vz-text-secondary)]">
                        {vessel.active === false ? "Inactive" : "Active"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {showControls ? (
            <div className="flex flex-col gap-3 border-t border-[color:var(--vz-hair)] px-4 py-3 text-sm text-[var(--vz-text-secondary)] sm:flex-row sm:items-center sm:justify-between">
              <span>
                Page {page} of {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={() => onPageChange(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  aria-label="Previous page"
                >
                  <ChevronLeft className="size-4" aria-hidden="true" />
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => onPageChange(Math.min(totalPages, page + 1))}
                  disabled={page >= totalPages}
                  aria-label="Next page"
                >
                  <ChevronRight className="size-4" aria-hidden="true" />
                </Button>
              </div>
            </div>
          ) : null}
        </>
      )}
    </WorkspaceSurface>
  );
}

function formatLinkState(value: unknown): string {
  if (typeof value !== "string" || value.length === 0) {
    return "unknown";
  }
  return humanizeKey(value);
}

function linkTone(
  state: string,
): "healthy" | "attention" | "danger" | "muted" | "accent" {
  const normalized = state.toLowerCase();
  if (normalized.includes("dark")) {
    return "danger";
  }
  if (normalized.includes("degraded") || normalized.includes("recovering")) {
    return "attention";
  }
  if (normalized.includes("wifi") || normalized.includes("healthy")) {
    return "healthy";
  }
  return "muted";
}
