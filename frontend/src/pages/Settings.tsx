import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Copy,
  Cpu,
  RefreshCw,
  Server,
  TerminalSquare,
} from "lucide-react";

import {
  InstrumentRail,
  OperationalSection,
  StatusToneBadge,
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { RuntimePassportPanel } from "@/components/evidence/RuntimePassportPanel";
import { OperationalMemoryPanel } from "@/components/evidence/OperationalMemoryPanel";
import { AttentionStack } from "@/components/operations/AttentionStack";
import { HardwareAdmissionPanel } from "@/components/operations/HardwareAdmissionPanel";
import { SceneIntelligenceMatrix } from "@/components/operations/SceneIntelligenceMatrix";
import { SupervisorLifecycleControls } from "@/components/operations/SupervisorLifecycleControls";
import { SceneFocusPicker } from "@/components/scenes/SceneFocusPicker";
import {
  filterSceneFocusItems,
  type SceneFocusItem,
} from "@/components/scenes/scene-focus";
import { ConfigurationWorkspace } from "@/components/configuration/ConfigurationWorkspace";
import { Button } from "@/components/ui/button";
import { PaginationControls } from "@/components/ui/pagination-controls";
import {
  paginateItems,
  type PaginationPageSize,
} from "@/components/ui/pagination";
import { omniLabels } from "@/copy/omnisight";
import { useCameras, type Camera } from "@/hooks/use-cameras";
import { useLiveTelemetry } from "@/hooks/use-live-telemetry";
import {
  useModels,
  useRuntimeArtifactsByModelId,
  type RuntimeArtifact,
} from "@/hooks/use-models";
import {
  type FleetOverview,
  useFleetOverview,
  useOperationalMemoryPatterns,
} from "@/hooks/use-operations";
import { useSites } from "@/hooks/use-sites";
import {
  deriveAttentionItems,
  deriveFleetHealth,
  deriveSceneReadinessRows,
} from "@/lib/operational-health";

type FleetSourceCapability = NonNullable<
  FleetOverview["delivery_diagnostics"][number]["source_capability"]
>;
type FleetRuleRuntime = NonNullable<
  FleetOverview["camera_workers"][number]["rule_runtime"]
>;

const configurationContentId = "configuration-content";

export function SettingsPage() {
  const fleet = useFleetOverview();
  const { data: cameras = [] } = useCameras();
  const { framesByCamera } = useLiveTelemetry(
    cameras.map((camera) => camera.id),
  );
  const { data: sites = [] } = useSites();
  const operationalMemory = useOperationalMemoryPatterns({ limit: 8 });
  const camerasById = useMemo(
    () => new Map(cameras.map((camera) => [camera.id, camera])),
    [cameras],
  );
  const [configurationOpen, setConfigurationOpen] = useState(false);
  const [configurationHasOpened, setConfigurationHasOpened] = useState(false);
  const [operationsSceneSearch, setOperationsSceneSearch] = useState("");
  const [selectedOperationsSceneIds, setSelectedOperationsSceneIds] = useState<
    Set<string>
  >(() => new Set());
  const [workerPageSize, setWorkerPageSize] =
    useState<PaginationPageSize>(10);
  const [workerPageIndex, setWorkerPageIndex] = useState(0);
  const [deliveryPageSize, setDeliveryPageSize] =
    useState<PaginationPageSize>(10);
  const [deliveryPageIndex, setDeliveryPageIndex] = useState(0);
  const [nodePageSize, setNodePageSize] = useState<PaginationPageSize>(10);
  const [nodePageIndex, setNodePageIndex] = useState(0);

  const siteNameById = useMemo(
    () => new Map(sites.map((site) => [site.id, site.name])),
    [sites],
  );
  const operationSceneItems = useMemo(() => {
    const itemsById = new Map<string, SceneFocusItem>();

    function addSceneItem(
      cameraId: string,
      name: string,
      siteId?: string | null,
    ) {
      if (itemsById.has(cameraId)) {
        return;
      }
      const resolvedSiteId =
        siteId ?? camerasById.get(cameraId)?.site_id ?? null;
      itemsById.set(cameraId, {
        id: cameraId,
        name,
        siteId: resolvedSiteId,
        siteName: resolvedSiteId
          ? (siteNameById.get(resolvedSiteId) ?? "Unknown site")
          : "Unknown site",
      });
    }

    cameras.forEach((camera) => {
      addSceneItem(camera.id, camera.name, camera.site_id);
    });
    fleet.data?.camera_workers.forEach((worker) => {
      addSceneItem(worker.camera_id, worker.camera_name, worker.site_id);
    });
    fleet.data?.delivery_diagnostics.forEach((diagnostic) => {
      addSceneItem(diagnostic.camera_id, diagnostic.camera_name);
    });

    return Array.from(itemsById.values());
  }, [cameras, camerasById, fleet.data, siteNameById]);
  const operationSceneIdSet = useMemo(
    () => new Set(operationSceneItems.map((item) => item.id)),
    [operationSceneItems],
  );
  const searchedOperationSceneItems = useMemo(
    () => filterSceneFocusItems(operationSceneItems, operationsSceneSearch),
    [operationSceneItems, operationsSceneSearch],
  );
  const focusedOperationSceneItems = useMemo(() => {
    if (selectedOperationsSceneIds.size > 0) {
      return operationSceneItems.filter((item) =>
        selectedOperationsSceneIds.has(item.id),
      );
    }

    if (operationsSceneSearch.trim().length > 0) {
      return searchedOperationSceneItems;
    }

    return [];
  }, [
    operationSceneItems,
    operationsSceneSearch,
    searchedOperationSceneItems,
    selectedOperationsSceneIds,
  ]);
  const hasOperationsSceneFocus =
    selectedOperationsSceneIds.size > 0 ||
    operationsSceneSearch.trim().length > 0;
  const focusedOperationSceneIds = useMemo(
    () => new Set(focusedOperationSceneItems.map((item) => item.id)),
    [focusedOperationSceneItems],
  );
  const focusedOperationSiteIds = useMemo(
    () =>
      new Set(
        focusedOperationSceneItems
          .map((item) => item.siteId)
          .filter((siteId): siteId is string => Boolean(siteId)),
      ),
    [focusedOperationSceneItems],
  );
  const operationsSceneFocusSummary =
    operationSceneItems.length === 0
      ? "0 of 0 scenes focused"
      : !hasOperationsSceneFocus
        ? "No scenes focused"
        : `${focusedOperationSceneItems.length} of ${operationSceneItems.length} scenes focused`;

  const modeCopy = useMemo(() => {
    if (fleet.data?.mode === "supervised") {
      return "Supervised production mode";
    }
    if (fleet.data?.mode === "mixed") {
      return "Mixed manual and supervised mode";
    }
    return "Manual dev mode";
  }, [fleet.data?.mode]);
  const fleetHealth = useMemo(
    () => deriveFleetHealth(fleet.data),
    [fleet.data],
  );
  const attentionItems = useMemo(
    () =>
      deriveAttentionItems({
        fleet: fleet.data,
        cameras,
        pendingIncidents: [],
      }),
    [cameras, fleet.data],
  );

  useEffect(() => {
    setSelectedOperationsSceneIds((current) => {
      const next = new Set(
        Array.from(current).filter((sceneId) =>
          operationSceneIdSet.has(sceneId),
        ),
      );
      return next.size === current.size ? current : next;
    });
  }, [operationSceneIdSet]);

  useEffect(() => {
    setWorkerPageIndex(0);
  }, [
    fleet.data?.camera_workers.length,
    focusedOperationSceneIds.size,
    workerPageSize,
  ]);

  useEffect(() => {
    setDeliveryPageIndex(0);
  }, [
    fleet.data?.delivery_diagnostics.length,
    focusedOperationSceneIds.size,
    deliveryPageSize,
  ]);

  useEffect(() => {
    setNodePageIndex(0);
  }, [fleet.data?.nodes.length, nodePageSize]);

  if (fleet.isLoading) {
    return (
      <WorkspaceSurface className="px-5 py-6 text-sm text-[#9bb0d0]">
        Loading operations...
      </WorkspaceSurface>
    );
  }

  if (fleet.isError || !fleet.data) {
    return (
      <WorkspaceSurface className="border-[#5a2330] bg-[#241118] px-5 py-6 text-sm text-[#ffc2cd]">
        Failed to load fleet operations.
      </WorkspaceSurface>
    );
  }

  const sceneHealthRows = deriveSceneReadinessRows({
    cameras,
    sites,
    fleet: fleet.data,
    framesByCamera,
  });
  const focusedSceneHealthRows = sceneHealthRows.filter((row) =>
    focusedOperationSceneIds.has(row.cameraId),
  );
  const focusedCameraWorkers = fleet.data.camera_workers.filter((worker) =>
    focusedOperationSceneIds.has(worker.camera_id),
  );
  const paginatedCameraWorkers = paginateItems(
    focusedCameraWorkers,
    workerPageSize,
    workerPageIndex,
  );
  const focusedDeliveryDiagnostics = fleet.data.delivery_diagnostics.filter(
    (diagnostic) => focusedOperationSceneIds.has(diagnostic.camera_id),
  );
  const paginatedDeliveryDiagnostics = paginateItems(
    focusedDeliveryDiagnostics,
    deliveryPageSize,
    deliveryPageIndex,
  );
  const focusedOperationalMemoryPatterns = (
    operationalMemory.data ?? []
  ).filter((pattern) => {
    if (pattern.camera_id) {
      return focusedOperationSceneIds.has(pattern.camera_id);
    }
    if (pattern.site_id) {
      return focusedOperationSiteIds.has(pattern.site_id);
    }
    return hasOperationsSceneFocus;
  });
  const edgeNodes = fleet.data.nodes
    .filter((node) => node.id !== null)
    .map((node) => ({
      id: node.id as string,
      hostname: node.hostname,
    }));
  const paginatedDeploymentNodes = paginateItems(
    fleet.data.nodes,
    nodePageSize,
    nodePageIndex,
  );
  const needsOperationsSetup =
    sites.length === 0 || cameras.length === 0 || fleet.data.nodes.length === 0;

  function toggleConfiguration() {
    if (!configurationOpen) {
      setConfigurationHasOpened(true);
    }
    setConfigurationOpen((current) => !current);
  }

  function toggleFocusedOperationsScene(sceneId: string) {
    setSelectedOperationsSceneIds((current) => {
      const next = new Set(current);
      if (next.has(sceneId)) {
        next.delete(sceneId);
      } else {
        next.add(sceneId);
      }
      return next;
    });
  }

  return (
    <div data-testid="operations-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Operations"
        title={omniLabels.operationsTitle}
        description="Monitor planned workers, runtime reports, lifecycle requests, and stream diagnostics for the fleet."
        actions={
          <Button type="button" onClick={() => void fleet.refetch()}>
            <RefreshCw className="mr-2 size-4" />
            Refresh
          </Button>
        }
      />

      {needsOperationsSetup ? <OperationsSetupEmptyState /> : null}

      <AttentionStack items={attentionItems} fleetHealth={fleetHealth} />

      <SceneFocusPicker
        defaultSummary={operationsSceneFocusSummary}
        items={operationSceneItems}
        onClearSelection={() => setSelectedOperationsSceneIds(new Set())}
        onSearchChange={setOperationsSceneSearch}
        onToggleScene={toggleFocusedOperationsScene}
        searchLabel="Search operations scenes"
        searchPlaceholder="Search by scene or site"
        searchValue={operationsSceneSearch}
        selectedSceneIds={selectedOperationsSceneIds}
        testId="operations-scene-focus"
        title="Focus scene view"
      />

      <SceneIntelligenceMatrix
        rows={focusedSceneHealthRows}
        emptyLabel={
          hasOperationsSceneFocus
            ? "No scenes match this focus."
            : "Select or search scenes to review readiness."
        }
      />

      <OperationsSectionNav />

      <OperationalSection
        id="workers"
        label="Workers"
        eyebrow="Command surface"
        className="scroll-mt-6"
      >
        <Panel
          title="Scene workers"
          icon={<TerminalSquare className="size-4" />}
          testId="worker-rail"
        >
          <div className="flex flex-col gap-3">
            {fleet.data.camera_workers.length === 0 ? (
              <p className="rounded-[1rem] border border-dashed border-white/15 p-3 text-sm text-[#93a7c5]">
                No scene workers yet.
              </p>
            ) : focusedCameraWorkers.length === 0 ? (
              <p className="rounded-[1rem] border border-dashed border-white/15 p-3 text-sm text-[#93a7c5]">
                {hasOperationsSceneFocus
                  ? "No workers match the focused scenes."
                  : "Select or search scenes to review workers."}
              </p>
            ) : (
              <>
                <PaginationControls
                  itemLabel="workers"
                  pageIndex={paginatedCameraWorkers.currentPageIndex}
                  pageSize={workerPageSize}
                  pageSizeLabel="Scene workers per page"
                  totalCount={focusedCameraWorkers.length}
                  onPageIndexChange={setWorkerPageIndex}
                  onPageSizeChange={setWorkerPageSize}
                />
                {paginatedCameraWorkers.items.map((worker) => {
                  const camera = camerasById.get(worker.camera_id);

                  return (
                    <div
                      key={worker.camera_id}
                      className="rounded-[1rem] border border-white/10 p-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-medium text-[#f4f8ff]">
                            {worker.camera_name}
                          </p>
                          <p className="mt-1 text-xs text-[#93a7c5]">
                            {worker.processing_mode} -{" "}
                            {worker.lifecycle_owner}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <StatusToneBadge
                            tone={statusTone(worker.desired_state)}
                          >
                            {worker.desired_state}
                          </StatusToneBadge>
                          <StatusToneBadge
                            tone={statusTone(worker.runtime_status)}
                          >
                            {worker.runtime_status}
                          </StatusToneBadge>
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[#93a7c5]">
                        <p>
                          <span className="font-semibold text-[#d8e2f2]">
                            Source
                          </span>{" "}
                          {formatCameraSource(camera)}
                        </p>
                        <p>
                          <span className="font-semibold text-[#d8e2f2]">
                            Recording
                          </span>{" "}
                          {formatRecordingPolicy(camera)}
                        </p>
                      </div>
                      <details className="mt-3 rounded-[0.85rem] border border-white/10 bg-black/15 p-3">
                        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-[#9fb7d8]">
                          Runtime diagnostics
                        </summary>
                        <RuntimePassportPanel
                          summary={worker.runtime_passport}
                          compact
                        />
                        <HardwareAdmissionPanel worker={worker} />
                        <RuleRuntimePanel summary={worker.rule_runtime} />
                        {worker.detail ? (
                          <p className="mt-2 text-sm text-[#93a7c5]">
                            {worker.detail}
                          </p>
                        ) : null}
                      </details>
                      <SupervisorLifecycleControls
                        worker={worker}
                        edgeNodes={edgeNodes}
                      />
                      {worker.dev_run_command ? (
                        <p className="mt-3 rounded-[0.75rem] border border-amber-300/25 bg-amber-950/20 p-3 text-xs text-amber-100">
                          Installable supervisors own production worker launch.
                          Manual terminal commands live in local lab and
                          break-glass documentation.
                        </p>
                      ) : null}
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </Panel>
      </OperationalSection>

      <OperationalMemoryPanel
        patterns={focusedOperationalMemoryPatterns}
        loading={operationalMemory.isLoading}
      />

      <OperationalSection
        id="stream-diagnostics"
        label="Stream Diagnostics"
        eyebrow="Delivery truth"
        className="scroll-mt-6"
      >
        <Panel
          title={omniLabels.streamDiagnosticsTitle}
          icon={<Copy className="size-4" />}
          testId="stream-diagnostics-rail"
        >
          <div className="flex flex-col gap-3">
            {fleet.data.delivery_diagnostics.length === 0 ? (
              <p className="rounded-[1rem] border border-dashed border-white/15 p-3 text-sm text-[#93a7c5]">
                No stream diagnostics yet.
              </p>
            ) : focusedDeliveryDiagnostics.length === 0 ? (
              <p className="rounded-[1rem] border border-dashed border-white/15 p-3 text-sm text-[#93a7c5]">
                {hasOperationsSceneFocus
                  ? "No stream diagnostics match the focused scenes."
                  : "Select or search scenes to review stream diagnostics."}
              </p>
            ) : (
              <>
                <PaginationControls
                  itemLabel="diagnostics"
                  pageIndex={paginatedDeliveryDiagnostics.currentPageIndex}
                  pageSize={deliveryPageSize}
                  pageSizeLabel="Stream diagnostics per page"
                  totalCount={focusedDeliveryDiagnostics.length}
                  onPageIndexChange={setDeliveryPageIndex}
                  onPageSizeChange={setDeliveryPageSize}
                />
                {paginatedDeliveryDiagnostics.items.map((diagnostic) => (
                  <div
                    key={diagnostic.camera_id}
                    className="rounded-[1rem] border border-white/10 p-3"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-[#f4f8ff]">
                          {diagnostic.camera_name} scene delivery
                        </p>
                        <p className="mt-1 text-xs text-[#93a7c5]">
                          {formatSource(diagnostic.source_capability)} -{" "}
                          {diagnostic.default_profile}
                        </p>
                      </div>
                      <StatusToneBadge tone="muted">
                        {diagnostic.selected_stream_mode}
                      </StatusToneBadge>
                    </div>
                    {diagnostic.native_status?.available === false ? (
                      <p className="mt-2 text-sm text-amber-100">
                        Direct stream unavailable:{" "}
                        {formatReason(diagnostic.native_status?.reason)}
                      </p>
                    ) : null}
                  </div>
                ))}
              </>
            )}
          </div>
        </Panel>
      </OperationalSection>

      <OperationalSection
        id="deployment-nodes"
        label="Deployment Nodes"
        eyebrow="Fleet topology"
        className="scroll-mt-6"
      >
        <section
          data-testid="edge-fleet-grid"
          className="grid gap-3 rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-neutral)] p-4 md:grid-cols-5"
        >
          <SummaryTile
            label="Planned workers"
            value={fleet.data.summary.desired_workers}
          />
          <SummaryTile
            label="Running workers"
            value={fleet.data.summary.running_workers}
          />
          <SummaryTile
            label="Stale nodes"
            value={fleet.data.summary.stale_nodes}
          />
          <SummaryTile
            label="Offline nodes"
            value={fleet.data.summary.offline_nodes}
          />
          <SummaryTile
            label="Direct streams unavailable"
            value={fleet.data.summary.native_unavailable_cameras}
          />
        </section>

        <section className="mt-4 grid gap-4 xl:grid-cols-2">
          <Panel title="Nodes" icon={<Server className="size-4" />}>
            <div className="flex flex-col gap-3">
              {fleet.data.nodes.length === 0 ? (
                <p className="rounded-[1rem] border border-dashed border-white/15 p-3 text-sm text-[#93a7c5]">
                  No deployment nodes yet.
                </p>
              ) : (
                <>
                  <PaginationControls
                    itemLabel="nodes"
                    pageIndex={paginatedDeploymentNodes.currentPageIndex}
                    pageSize={nodePageSize}
                    pageSizeLabel="Deployment nodes per page"
                    totalCount={fleet.data.nodes.length}
                    onPageIndexChange={setNodePageIndex}
                    onPageSizeChange={setNodePageSize}
                  />
                  {paginatedDeploymentNodes.items.map((node) => (
                    <div
                      key={node.id ?? "central"}
                      className="rounded-[1rem] border border-white/10 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-medium text-[#f4f8ff]">
                            {node.hostname}
                          </p>
                          <p className="mt-1 text-xs text-[#93a7c5]">
                            {node.kind} -{" "}
                            {node.assigned_camera_ids?.length ?? 0} assigned
                            scenes
                          </p>
                        </div>
                        <StatusToneBadge tone={statusTone(node.status)}>
                          {node.status}
                        </StatusToneBadge>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </Panel>

          <Panel title="Node pairing" icon={<Server className="size-4" />}>
            <div className="flex flex-col gap-3 text-sm text-[#a9b9d3]">
              <p>
                Pair Jetson edge nodes and inspect installable supervisor
                credentials from Deployment. Operations monitors runtime health
                after nodes are paired.
              </p>
              <Link
                to="/deployment"
                className="inline-flex w-fit items-center rounded-full border border-white/10 px-4 py-2 text-sm font-semibold text-[#d8e2f2] transition hover:border-[#6ec6ff]/60 hover:text-white"
              >
                Open Deployment
                <ArrowRight className="ml-2 size-4" />
              </Link>
            </div>
          </Panel>
        </section>
      </OperationalSection>

      <OperationalSection
        id="configuration"
        label="Configuration"
        eyebrow="Control plane"
        className="scroll-mt-6"
        data-testid="configuration-section"
      >
        <Button
          type="button"
          aria-expanded={configurationOpen}
          aria-controls={configurationContentId}
          className="mt-1"
          onClick={toggleConfiguration}
        >
          {configurationOpen ? "Hide configuration" : "Show configuration"}
        </Button>
        <div
          id={configurationContentId}
          hidden={!configurationOpen}
          className="mt-4 space-y-4"
        >
          {configurationHasOpened ? (
            <>
              <ConfigurationWorkspace
                cameras={cameras}
                sites={sites}
                edgeNodes={edgeNodes}
              />
              <ConfigurationRuntimeArtifacts />
            </>
          ) : null}
        </div>
        {!configurationOpen ? (
          <p className="mt-3 text-sm text-[var(--vz-text-secondary)]">
            Profiles, bindings, effective runtime hashes, and installer defaults
            are available when needed.
          </p>
        ) : null}
      </OperationalSection>

      <OperationalSection
        id="installer-guidance"
        label="Installer Guidance"
        eyebrow="Deployment handoff"
        className="scroll-mt-6"
      >
        <WorkspaceSurface className="px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Server className="size-5 text-[#8fd3ff]" />
              <div>
                <h2 className="text-base font-semibold text-[#f4f8ff]">
                  System setup
                </h2>
                <p className="mt-1 text-sm text-[#93a7c5]">
                  Installable supervisors, node pairing, credentials, service
                  health, and support bundles live in Deployment. Rotated
                  credentials must be picked up by connected supervisors before
                  polling resumes.
                </p>
              </div>
            </div>
            <Link
              className="inline-flex items-center justify-center rounded-full border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,#161c26,#0d121a)] px-4 py-2.5 text-sm font-medium text-[var(--vz-text-primary)] shadow-[var(--vz-elev-1)] transition duration-200 hover:border-[color:var(--vz-hair-focus)]"
              to="/deployment"
            >
              Open Deployment
              <ArrowRight className="ml-2 size-4" />
            </Link>
          </div>
        </WorkspaceSurface>

        <WorkspaceSurface className="mt-4 px-5 py-4">
          <div className="flex items-center gap-3">
            <TerminalSquare className="size-5 text-[#8fd3ff]" />
            <div>
              <h2 className="text-base font-semibold text-[#f4f8ff]">
                {modeCopy}
              </h2>
              <p className="mt-1 text-sm text-[#93a7c5]">
                Production worker launch is owned by installed supervisor
                services. Terminal commands are limited to local development,
                installer smoke tests, and break-glass support.
              </p>
            </div>
          </div>
        </WorkspaceSurface>
      </OperationalSection>
    </div>
  );
}

const operationsSections = [
  { id: "workers", label: "Workers" },
  { id: "stream-diagnostics", label: "Stream Diagnostics" },
  { id: "deployment-nodes", label: "Deployment Nodes" },
  { id: "configuration", label: "Configuration" },
  { id: "installer-guidance", label: "Installer Guidance" },
] as const;

function OperationsSectionNav() {
  return (
    <nav
      aria-label="Operations sections"
      className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]"
    >
      {operationsSections.map((section) => (
        <a
          key={section.id}
          href={`#${section.id}`}
          className="inline-flex items-center text-[var(--vz-text-secondary)] underline-offset-4 transition hover:text-[var(--vz-text-primary)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--vz-hair-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--vz-canvas-obsidian)]"
        >
          {section.label}
        </a>
      ))}
    </nav>
  );
}

function RuleRuntimePanel({ summary }: { summary?: FleetRuleRuntime | null }) {
  const configuredCount = summary?.configured_rule_count ?? 0;
  const status = summary?.load_status ?? "not_configured";

  return (
    <section aria-label="Rules" className="mt-3 border-t border-white/8 pt-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
            Rules
          </h4>
          <p className="mt-1 text-sm font-semibold text-[#eef4ff]">
            {configuredCount}{" "}
            {configuredCount === 1 ? "active rule" : "active rules"}
          </p>
        </div>
        <StatusToneBadge tone={ruleStatusTone(status)}>
          {status}
        </StatusToneBadge>
      </div>
      <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
        <RuntimeFact
          label="Rule hash"
          value={shortHash(summary?.effective_rule_hash)}
        />
        <RuntimeFact
          label="Latest event"
          value={formatRuleEventTime(summary?.latest_rule_event_at)}
        />
      </dl>
    </section>
  );
}

function RuntimeFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
        {label}
      </dt>
      <dd className="mt-1 truncate text-[#d8e2f2]" title={value}>
        {value}
      </dd>
    </div>
  );
}

function SummaryTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[0.75rem] border border-white/10 bg-black/25 px-4 py-3">
      <p className="text-xs text-[#93a7c5]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[#f4f8ff]">{value}</p>
    </div>
  );
}

function OperationsSetupEmptyState() {
  const actions = [
    { label: "Open Sites", to: "/sites" },
    { label: "Open Scenes", to: "/cameras" },
    { label: "Open Deployment", to: "/deployment" },
  ];

  return (
    <WorkspaceSurface className="p-5">
      <h2 className="text-base font-semibold text-[#f4f8ff]">
        Configure Sites, Scenes, and Deployment
      </h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[#93a7c5]">
        Add the location first, attach scene cameras, then pair the installed
        master or Jetson supervisors so Operations has live worker and service
        status to display.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {actions.map((action) => (
          <Link
            key={action.to}
            className="inline-flex items-center justify-center rounded-full border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,#161c26,#0d121a)] px-4 py-2.5 text-sm font-medium text-[var(--vz-text-primary)] shadow-[var(--vz-elev-1)] transition duration-200 hover:border-[color:var(--vz-hair-focus)]"
            to={action.to}
          >
            {action.label}
            <ArrowRight className="ml-2 size-4" />
          </Link>
        ))}
      </div>
    </WorkspaceSurface>
  );
}

function Panel({
  title,
  icon,
  children,
  testId,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  testId?: string;
}) {
  const Surface = testId?.endsWith("-rail") ? InstrumentRail : WorkspaceSurface;

  return (
    <Surface data-testid={testId} className="p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#f4f8ff]">
        {icon}
        <h2>{title}</h2>
      </div>
      {children}
    </Surface>
  );
}

function ConfigurationRuntimeArtifacts() {
  const { data: models = [] } = useModels();
  const runtimeArtifacts = useRuntimeArtifactsByModelId(
    models.map((model) => model.id),
  );

  return (
    <Panel
      title="Model runtimes"
      icon={<Cpu className="size-4" />}
      testId="runtime-artifact-rail"
    >
      <div className="flex flex-col gap-3">
        {models.length === 0 ? (
          <p className="text-sm text-[#93a7c5]">
            No registered models are available for runtime artifact checks.
          </p>
        ) : (
          models.map((model) => {
            const artifacts = runtimeArtifacts.data?.[model.id] ?? [];
            const summary = summarizeModelRuntimeArtifacts(artifacts);

            return (
              <div
                key={model.id}
                className="rounded-[1rem] border border-white/10 p-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-[#f4f8ff]">{model.name}</p>
                    <p className="mt-1 text-xs text-[#93a7c5]">
                      {model.version} - {model.capability ?? "fixed_vocab"}
                    </p>
                  </div>
                  <StatusToneBadge tone={summary.tone}>
                    {summary.label}
                  </StatusToneBadge>
                </div>
                <p className="mt-2 text-sm text-[#93a7c5]">
                  {artifacts.length}{" "}
                  {artifacts.length === 1 ? "artifact" : "artifacts"}
                  {summary.detail ? ` - ${summary.detail}` : ""}
                </p>
              </div>
            );
          })
        )}
      </div>
    </Panel>
  );
}

function formatSource(source: FleetSourceCapability | null | undefined) {
  if (!source?.width || !source.height) {
    return "source not reported";
  }
  return `${source.width} x ${source.height}${source.fps ? ` at ${source.fps} fps` : ""}`;
}

function formatCameraSource(camera: Camera | undefined) {
  const source = camera?.camera_source;
  if (source?.kind === "usb") {
    return `USB source ${source.uri}`;
  }
  if (source?.kind === "jetson_csi") {
    return `Jetson CSI source ${source.uri}`;
  }
  if (source?.kind === "rtsp" || camera?.rtsp_url_masked) {
    return "RTSP source";
  }
  return "source not configured";
}

function formatRecordingPolicy(camera: Camera | undefined) {
  const policy = camera?.recording_policy;
  if (!policy) {
    return "Event clips not configured";
  }
  if (!policy.enabled) {
    return "Event clips disabled";
  }
  return `Event clips: ${formatStorageProfile(policy.storage_profile)} storage`;
}

function formatStorageProfile(
  profile: NonNullable<Camera["recording_policy"]>["storage_profile"],
) {
  return profile.replaceAll("_", " ");
}

function formatReason(reason: string | null | undefined) {
  return (reason ?? "not reported").replaceAll("_", " ");
}

function statusTone(
  status: string,
): "healthy" | "attention" | "danger" | "muted" | "accent" {
  const normalized = status.toLowerCase();
  if (
    normalized === "running" ||
    normalized === "online" ||
    normalized === "healthy" ||
    normalized === "supervised"
  ) {
    return "healthy";
  }
  if (
    normalized === "stale" ||
    normalized === "manual" ||
    normalized === "not_reported" ||
    normalized === "unknown"
  ) {
    return "attention";
  }
  if (normalized === "offline" || normalized === "failed") {
    return "danger";
  }
  if (normalized === "edge_supervisor") {
    return "accent";
  }
  return "muted";
}

function ruleStatusTone(
  status: FleetRuleRuntime["load_status"] | "not_configured",
): "healthy" | "attention" | "danger" | "muted" {
  if (status === "loaded") {
    return "healthy";
  }
  if (status === "stale") {
    return "attention";
  }
  return "muted";
}

function shortHash(value: string | null | undefined) {
  return value ? value.slice(0, 12) : "Not available";
}

function formatRuleEventTime(timestamp: string | null | undefined) {
  if (!timestamp) {
    return "No event";
  }
  return new Date(timestamp).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function summarizeModelRuntimeArtifacts(artifacts: RuntimeArtifact[]): {
  label: string;
  detail: string;
  tone: "healthy" | "attention" | "danger" | "muted" | "accent";
} {
  const validArtifacts = artifacts.filter(
    (artifact) => artifact.validation_status === "valid",
  );
  const bestArtifact =
    validArtifacts.find((artifact) => artifact.kind === "tensorrt_engine") ??
    validArtifacts.find((artifact) => artifact.kind === "onnx_export");

  if (bestArtifact?.kind === "tensorrt_engine") {
    return {
      label: "TensorRT artifact: valid",
      detail: `${bestArtifact.target_profile} - ${bestArtifact.precision}`,
      tone: "healthy",
    };
  }

  if (bestArtifact?.kind === "onnx_export") {
    return {
      label: "ONNX artifact: valid",
      detail: `${bestArtifact.target_profile} - ${bestArtifact.precision}`,
      tone: "accent",
    };
  }

  if (artifacts.some((artifact) => artifact.validation_status === "stale")) {
    return {
      label: "Compiled stale",
      detail: "Rebuild before production selection.",
      tone: "attention",
    };
  }

  if (artifacts.some((artifact) => artifact.validation_status === "invalid")) {
    return {
      label: "Artifact invalid",
      detail: "Validation failed on the target host.",
      tone: "danger",
    };
  }

  return {
    label: "Dynamic/fallback runtime",
    detail: "No valid compiled artifact is ready.",
    tone: "muted",
  };
}
