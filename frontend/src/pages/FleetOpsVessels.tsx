import { useDeferredValue, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";

import { VesselFormDialog } from "@/components/fleetops/VesselFormDialog";
import { VesselSummaryTable } from "@/components/fleetops/VesselSummaryTable";
import { asRecord, type FleetOpsVessel } from "@/components/fleetops/types";
import { WorkspaceBand } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  useCreateMaritimeVessel,
  useMaritimeVessels,
  type MaritimeVesselCreateInput,
} from "@/hooks/use-maritime";
import { useSites } from "@/hooks/use-sites";

const PAGE_SIZE_OPTIONS = [10, 25, 50] as const;
const DEFAULT_PAGE_SIZE = 10;
type PageSizeOption = (typeof PAGE_SIZE_OPTIONS)[number];
type VesselStatusFilter = "all" | "active" | "inactive";

function normalize(value: unknown): string {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}

function vesselLinkState(vessel: FleetOpsVessel): string {
  const metadata = asRecord(vessel.metadata);
  const value = metadata.link_state;
  return typeof value === "string" && value.trim().length > 0
    ? value
    : "unknown";
}

function vesselStatus(
  vessel: FleetOpsVessel,
): Exclude<VesselStatusFilter, "all"> {
  return vessel.active === false ? "inactive" : "active";
}

function vesselSearchText(vessel: FleetOpsVessel): string {
  const metadata = asRecord(vessel.metadata);
  const site = asRecord(vessel.site);
  return [
    vessel.name,
    vessel.id,
    vessel.site_id,
    site.name,
    vessel.imo_number,
    vessel.mmsi,
    vessel.call_sign,
    metadata.home_port,
    metadata.link_state,
    vesselStatus(vessel),
  ]
    .map((value) => (typeof value === "string" ? value : ""))
    .join(" ")
    .toLowerCase();
}

function parsePageSize(value: string | null): PageSizeOption {
  const parsed = Number(value);
  return PAGE_SIZE_OPTIONS.includes(parsed as PageSizeOption)
    ? (parsed as PageSizeOption)
    : DEFAULT_PAGE_SIZE;
}

function parsePage(value: string | null): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export function FleetOpsVessels() {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const vessels = useMaritimeVessels();
  const sites = useSites();
  const createVessel = useCreateMaritimeVessel();
  const vesselRows = useMemo(
    () => (vessels.data ?? []) as FleetOpsVessel[],
    [vessels.data],
  );
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get("q") ?? "";
  const deferredSearchTerm = useDeferredValue(searchTerm);
  const linkStateFilter = searchParams.get("link") ?? "all";
  const rawStatusFilter = searchParams.get("status");
  const statusFilter: VesselStatusFilter =
    rawStatusFilter === "active" || rawStatusFilter === "inactive"
      ? rawStatusFilter
      : "all";
  const pageSize = parsePageSize(searchParams.get("pageSize"));
  const requestedPage = parsePage(searchParams.get("page"));

  const linkStateOptions = useMemo(
    () =>
      Array.from(new Set(vesselRows.map(vesselLinkState))).sort((left, right) =>
        left.localeCompare(right),
      ),
    [vesselRows],
  );

  const filteredVessels = useMemo(() => {
    const normalizedSearch = normalize(deferredSearchTerm);
    return vesselRows.filter((vessel) => {
      const matchesSearch =
        normalizedSearch.length === 0 ||
        vesselSearchText(vessel).includes(normalizedSearch);
      const matchesLinkState =
        linkStateFilter === "all" ||
        vesselLinkState(vessel) === linkStateFilter;
      const matchesStatus =
        statusFilter === "all" || vesselStatus(vessel) === statusFilter;
      return matchesSearch && matchesLinkState && matchesStatus;
    });
  }, [deferredSearchTerm, linkStateFilter, statusFilter, vesselRows]);

  const totalPages = Math.max(1, Math.ceil(filteredVessels.length / pageSize));
  const currentPage = Math.min(requestedPage, totalPages);
  const pageStart = (currentPage - 1) * pageSize;
  const pagedVessels = filteredVessels.slice(pageStart, pageStart + pageSize);
  const hasActiveListFilters =
    searchTerm.trim().length > 0 ||
    linkStateFilter !== "all" ||
    statusFilter !== "all";

  async function handleCreateVessel(payload: MaritimeVesselCreateInput) {
    const created = await createVessel.mutateAsync(payload);
    setDialogOpen(false);

    if (typeof created?.id === "string") {
      navigate(`/fleetops/vessels/${created.id}`);
    }
  }

  function updateListQuery(updates: Record<string, string | number | null>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === "" || value === "all") {
        next.delete(key);
      } else {
        next.set(key, String(value));
      }
    }
    setSearchParams(next, { replace: true });
  }

  return (
    <main className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        description="Scan vessels, site bindings, link posture, and pending evidence movement from one fleet table."
        eyebrow="FleetOps"
        title="Vessels"
        actions={
          <Button variant="primary" onClick={() => setDialogOpen(true)}>
            <Plus className="mr-2 size-4" aria-hidden="true" />
            Add vessel
          </Button>
        }
      />
      <VesselSummaryTable
        vessels={pagedVessels}
        totalVessels={vesselRows.length}
        totalMatches={filteredVessels.length}
        page={currentPage}
        pageSize={pageSize}
        pageStart={pageStart}
        totalPages={totalPages}
        searchTerm={searchTerm}
        linkStateFilter={linkStateFilter}
        statusFilter={statusFilter}
        linkStateOptions={linkStateOptions}
        hasActiveFilters={hasActiveListFilters}
        onSearchTermChange={(value) => updateListQuery({ q: value, page: 1 })}
        onLinkStateFilterChange={(value) =>
          updateListQuery({ link: value, page: 1 })
        }
        onStatusFilterChange={(value) =>
          updateListQuery({ status: value, page: 1 })
        }
        onPageSizeChange={(value) =>
          updateListQuery({ pageSize: value, page: 1 })
        }
        onPageChange={(value) => updateListQuery({ page: value })}
        onClearFilters={() =>
          updateListQuery({ q: null, link: null, status: null, page: 1 })
        }
        onAddVessel={() => setDialogOpen(true)}
      />
      <VesselFormDialog
        open={dialogOpen}
        sites={sites.data ?? []}
        isSubmitting={createVessel.isPending}
        onClose={() => setDialogOpen(false)}
        onSubmit={(payload) =>
          handleCreateVessel(payload as MaritimeVesselCreateInput)
        }
      />
    </main>
  );
}

export const FleetOpsVesselsPage = FleetOpsVessels;
