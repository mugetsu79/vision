import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Input } from "@/components/ui/input";
import {
  paginateItems,
  type PaginationPageSize,
} from "@/components/ui/pagination";
import { PaginationControls } from "@/components/ui/pagination-controls";
import {
  asRecord,
  linkSiteRole,
  linkSiteRoleLabel,
  textValue,
  type LinkSiteSummaryItem,
} from "@/components/link/types";

type LinkSiteSelectorProps = {
  summaries: LinkSiteSummaryItem[];
  searchValue: string;
  selectedSiteId?: string | null;
  onSearchChange: (value: string) => void;
  onSelectSite: (siteId: string) => void;
};

export function LinkSiteSelector({
  summaries,
  searchValue,
  selectedSiteId,
  onSearchChange,
  onSelectSite,
}: LinkSiteSelectorProps) {
  const [pageSize, setPageSize] = useState<PaginationPageSize>(10);
  const [pageIndex, setPageIndex] = useState(0);
  const filtered = useMemo(
    () => filterSummaries(summaries, searchValue),
    [searchValue, summaries],
  );
  const paginated = paginateItems(filtered, pageSize, pageIndex);
  const selectedSummary =
    summaries.find((summary) => summary.site_id === selectedSiteId) ?? null;
  const hasSearch = searchValue.trim().length > 0;
  const showScopedSelection = Boolean(selectedSummary && !hasSearch);
  const visibleItems = showScopedSelection && selectedSummary
    ? [selectedSummary]
    : paginated.items;

  useEffect(() => {
    setPageIndex(0);
  }, [pageSize, searchValue, filtered.length]);

  return (
    <WorkspaceSurface data-testid="link-site-selector" className="p-4">
      <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
          Search
        </span>
        <span className="relative block">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[var(--vz-text-muted)]"
            aria-hidden="true"
          />
          <Input
            aria-label="Search link sites"
            className="pl-10"
            placeholder="Search site, transport, provider, or link state"
            value={searchValue}
            onChange={(event) => onSearchChange(event.currentTarget.value)}
          />
        </span>
      </label>
      <div className="mt-4 grid gap-2">
        {visibleItems.map((summary) => {
          const role = linkSiteRole(summary);
          return (
            <button
              key={summary.site_id}
              aria-pressed={summary.site_id === selectedSiteId}
              aria-label={`Select ${summary.site_name}`}
              className="grid gap-2 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3 text-left transition hover:border-[color:var(--vz-hair-strong)] aria-pressed:border-[color:var(--vz-hair-focus)] aria-pressed:bg-[rgba(23,52,70,0.48)] sm:grid-cols-[minmax(0,1fr)_auto]"
              type="button"
              onClick={() => onSelectSite(summary.site_id)}
            >
              <span className="min-w-0">
                <span className="block truncate font-[family-name:var(--vz-font-display)] text-base font-semibold text-[var(--vz-text-primary)]">
                  {summary.site_name}
                </span>
                <span className="mt-1 block truncate text-xs text-[var(--vz-text-muted)]">
                  {summary.site_tz}
                </span>
              </span>
              <span className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-secondary)]">
                <span>{summary.link_state}</span>
                <span>{linkSiteRoleLabel(role)}</span>
                {role === "edge" ? (
                  <span>{summary.connection_count} paths</span>
                ) : null}
              </span>
            </button>
          );
        })}
      </div>
      {filtered.length === 0 ? (
        <p className="mt-4 text-sm text-[var(--vz-text-secondary)]">
          No link sites match this search.
        </p>
      ) : null}
      {!showScopedSelection ? (
        <PaginationControls
          className="mt-3"
          itemLabel="sites"
          pageIndex={paginated.currentPageIndex}
          pageSize={pageSize}
          pageSizeLabel="Link sites per page"
          totalCount={filtered.length}
          onPageIndexChange={setPageIndex}
          onPageSizeChange={setPageSize}
        />
      ) : null}
    </WorkspaceSurface>
  );
}

function filterSummaries(
  summaries: LinkSiteSummaryItem[],
  searchValue: string,
): LinkSiteSummaryItem[] {
  const normalized = searchValue.trim().toLowerCase();
  if (!normalized) {
    return summaries;
  }
  return summaries.filter((summary) =>
    summarySearchText(summary).includes(normalized),
  );
}

function summarySearchText(summary: LinkSiteSummaryItem): string {
  const activeConnection = asRecord(summary.active_connection);
  return [
    summary.site_name,
    summary.site_id,
    summary.site_tz,
    summary.link_state,
    linkSiteRoleLabel(linkSiteRole(summary)),
    textValue(activeConnection.label, ""),
    textValue(activeConnection.transport_kind, ""),
    textValue(activeConnection.provider, ""),
    textValue(activeConnection.status, ""),
  ]
    .join(" ")
    .toLowerCase();
}
