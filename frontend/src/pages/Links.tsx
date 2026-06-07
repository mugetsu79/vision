import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { LinkSiteSelector } from "@/components/link/LinkSiteSelector";
import {
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { useLinkSiteSummaries } from "@/hooks/use-link";

export function Links() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchValue, setSearchValue] = useState("");
  const selectedSiteId = searchParams.get("site");
  const summaries = useLinkSiteSummaries();
  const summaryItems = useMemo(() => summaries.data ?? [], [summaries.data]);
  const selectedSummary = useMemo(
    () =>
      summaryItems.find((summary) => summary.site_id === selectedSiteId) ??
      null,
    [selectedSiteId, summaryItems],
  );

  function selectSite(siteId: string) {
    setSearchParams({ site: siteId });
  }

  function clearSite() {
    setSearchParams({});
  }

  return (
    <main
      data-testid="link-performance-workspace"
      className="space-y-5 p-4 sm:p-6"
    >
      <WorkspaceBand
        eyebrow="Core Link"
        title="Link Performance"
        description="Monitor site connectivity, transfer posture, budgets, probes, and link passports across Vezor."
      />
      <LinkSiteSelector
        summaries={summaryItems}
        searchValue={searchValue}
        selectedSiteId={selectedSiteId}
        onSearchChange={setSearchValue}
        onSelectSite={selectSite}
      />
      {selectedSummary ? (
        <WorkspaceSurface className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
                Selected site
              </p>
              <p className="mt-2 font-[family-name:var(--vz-font-display)] text-lg font-semibold text-[var(--vz-text-primary)]">
                {selectedSummary.site_name}
              </p>
            </div>
            <Button variant="ghost" onClick={clearSite}>
              Clear selection
            </Button>
          </div>
        </WorkspaceSurface>
      ) : (
        <WorkspaceSurface className="p-5 text-sm text-[var(--vz-text-secondary)]">
          Choose a site to inspect link performance.
        </WorkspaceSurface>
      )}
    </main>
  );
}

export const LinksPage = Links;
