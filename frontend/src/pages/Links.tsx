import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { LinkBudgetPolicyPanel } from "@/components/link/LinkBudgetPolicyPanel";
import { LinkConnectionsPanel } from "@/components/link/LinkConnectionsPanel";
import { LinkPosturePanel } from "@/components/link/LinkPosturePanel";
import { LinkProbePanel } from "@/components/link/LinkProbePanel";
import { LinkQueuePanel } from "@/components/link/LinkQueuePanel";
import { LinkSiteSelector } from "@/components/link/LinkSiteSelector";
import { asRecord } from "@/components/link/types";
import {
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import {
  useLinkConnections,
  useLinkPolicies,
  useLinkProbes,
  useLinkSiteBudget,
  useLinkSiteQueue,
  useLinkSiteStatus,
  useLinkSiteSummaries,
} from "@/hooks/use-link";

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
  const status = useLinkSiteStatus(selectedSiteId);
  const connections = useLinkConnections(selectedSiteId);
  const budget = useLinkSiteBudget(selectedSiteId);
  const policies = useLinkPolicies(selectedSiteId);
  const probes = useLinkProbes(selectedSiteId);
  const queue = useLinkSiteQueue(selectedSiteId);
  const connectionItems = connections.data ?? [];
  const statusBudget = asRecord(status.data).budget ?? null;

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
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <div className="grid gap-4">
            <LinkPosturePanel
              status={status.data}
              isLoading={status.isLoading}
              error={status.error}
              onClearSelection={clearSite}
            />
            <LinkConnectionsPanel
              siteId={selectedSiteId}
              connections={connectionItems}
            />
            <LinkBudgetPolicyPanel
              siteId={selectedSiteId}
              budget={budget.data ?? statusBudget}
              policies={policies.data ?? {}}
            />
          </div>
          <div className="grid gap-4">
            <LinkProbePanel
              siteId={selectedSiteId}
              connections={connectionItems}
              probes={probes.data ?? []}
            />
            <LinkQueuePanel siteId={selectedSiteId} queue={queue.data ?? []} />
          </div>
        </div>
      ) : (
        <WorkspaceSurface className="p-5 text-sm text-[var(--vz-text-secondary)]">
          Choose a site to inspect link performance.
        </WorkspaceSurface>
      )}
    </main>
  );
}

export const LinksPage = Links;
