import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { LinkBudgetPolicyPanel } from "@/components/link/LinkBudgetPolicyPanel";
import { LinkConnectionsPanel } from "@/components/link/LinkConnectionsPanel";
import { LinkMasterTargetPanel } from "@/components/link/LinkMasterTargetPanel";
import { LinkPosturePanel } from "@/components/link/LinkPosturePanel";
import { LinkProbePanel } from "@/components/link/LinkProbePanel";
import { LinkQueuePanel } from "@/components/link/LinkQueuePanel";
import { LinkSiteSelector } from "@/components/link/LinkSiteSelector";
import {
  asRecord,
  controlPlaneTargetSites,
  linkSiteRole,
} from "@/components/link/types";
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
  useMasterLinkReflectorProfile,
  useDisableMasterLinkReflector,
  useEnableMasterLinkReflector,
  useRotateMasterLinkReflectorKey,
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
  const selectedRole = selectedSummary ? linkSiteRole(selectedSummary) : "edge";
  const selectedEdgeSiteId =
    selectedSummary && selectedRole === "edge" ? selectedSiteId : null;
  const targetSiteOptions = useMemo(
    () => controlPlaneTargetSites(summaryItems),
    [summaryItems],
  );
  const status = useLinkSiteStatus(selectedSiteId);
  const connections = useLinkConnections(selectedEdgeSiteId);
  const budget = useLinkSiteBudget(selectedEdgeSiteId);
  const policies = useLinkPolicies(selectedEdgeSiteId);
  const probes = useLinkProbes(selectedSiteId);
  const queue = useLinkSiteQueue(selectedEdgeSiteId);
  const reflectorProfile = useMasterLinkReflectorProfile();
  const enableReflector = useEnableMasterLinkReflector();
  const disableReflector = useDisableMasterLinkReflector();
  const rotateReflectorKey = useRotateMasterLinkReflectorKey();
  const connectionItems = connections.data ?? [];
  const statusBudget = asRecord(status.data).budget ?? null;
  const edgeSiteCount = summaryItems.filter(
    (summary) => linkSiteRole(summary) === "edge",
  ).length;
  const controlPlaneCount = summaryItems.length - edgeSiteCount;
  const degradedSiteCount = summaryItems.filter((summary) =>
    String(summary.link_state).toLowerCase().includes("degraded"),
  ).length;

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
      <WorkspaceSurface className="p-4">
        {summaries.isLoading ? (
          <p className="text-sm text-[var(--vz-text-secondary)]">
            Loading link sites...
          </p>
        ) : summaries.error ? (
          <p className="text-sm text-[var(--vz-state-risk)]">
            Link summaries could not be loaded.
          </p>
        ) : (
          <div className="grid gap-3 text-sm text-[var(--vz-text-secondary)] sm:grid-cols-4">
            <SummaryMetric label="Sites" value={summaryItems.length} />
            <SummaryMetric label="Edge sites" value={edgeSiteCount} />
            <SummaryMetric label="Control planes" value={controlPlaneCount} />
            <SummaryMetric label="Degraded" value={degradedSiteCount} />
          </div>
        )}
      </WorkspaceSurface>
      <LinkSiteSelector
        summaries={summaryItems}
        searchValue={searchValue}
        selectedSiteId={selectedSiteId}
        onSearchChange={setSearchValue}
        onSelectSite={selectSite}
      />
      {selectedSummary && selectedRole === "control_plane" ? (
        <LinkMasterTargetPanel
          summary={selectedSummary}
          status={status.data}
          probes={probes.data ?? []}
          reflectorProfile={reflectorProfile.data}
          reflectorIsLoading={reflectorProfile.isLoading}
          reflectorError={reflectorProfile.error}
          reflectorActionPending={
            enableReflector.isPending ||
            disableReflector.isPending ||
            rotateReflectorKey.isPending
          }
          isLoading={status.isLoading}
          error={status.error}
          onClearSelection={clearSite}
          onEnableReflector={(payload) =>
            enableReflector.mutateAsync(payload)
          }
          onDisableReflector={() => disableReflector.mutateAsync()}
          onRotateReflectorKey={() => rotateReflectorKey.mutateAsync()}
        />
      ) : selectedSummary ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <div className="grid gap-4">
            <LinkPosturePanel
              status={status.data}
              isLoading={status.isLoading}
              error={status.error}
              onClearSelection={clearSite}
            />
            <LinkConnectionsPanel
              siteId={selectedEdgeSiteId}
              connections={connectionItems}
              targetSiteOptions={targetSiteOptions}
            />
            <LinkBudgetPolicyPanel
              siteId={selectedEdgeSiteId}
              budget={budget.data ?? statusBudget}
              policies={policies.data ?? {}}
            />
          </div>
          <div className="grid gap-4">
            <LinkProbePanel
              siteId={selectedEdgeSiteId}
              connections={connectionItems}
              probes={probes.data ?? []}
            />
            <LinkQueuePanel siteId={selectedEdgeSiteId} queue={queue.data ?? []} />
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

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
        {label}
      </p>
      <p className="mt-1 text-base font-semibold text-[var(--vz-text-primary)]">
        {value}
      </p>
    </div>
  );
}
