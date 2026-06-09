import { useEffect, useMemo, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import {
  CameraWizard,
  type ModelOption,
} from "@/components/cameras/CameraWizard";
import { IncidentRulesPanel } from "@/components/cameras/IncidentRulesPanel";
import {
  StatusToneBadge,
  WorkspaceBand,
} from "@/components/layout/workspace-surfaces";
import { PolicyDraftReview } from "@/components/policy/PolicyDraftReview";
import { SceneFocusPicker } from "@/components/scenes/SceneFocusPicker";
import { filterSceneFocusItems } from "@/components/scenes/scene-focus";
import { Button } from "@/components/ui/button";
import { PaginationControls } from "@/components/ui/pagination-controls";
import {
  paginateItems,
  type PaginationPageSize,
} from "@/components/ui/pagination";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { productBrand } from "@/brand/product";
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
import {
  useCameras,
  useCreateCamera,
  useDeleteCamera,
  useUpdateCamera,
  type Camera,
  type CreateCameraInput,
  type UpdateCameraInput,
} from "@/hooks/use-cameras";
import {
  useModelCatalog,
  type ModelCatalogEntry,
} from "@/hooks/use-model-catalog";
import {
  useModels,
  useRuntimeArtifactsByModelId,
  type Model,
  type RuntimeArtifact,
} from "@/hooks/use-models";
import {
  useCreateRuntimeArtifactBuildJob,
  useDeploymentModelInventory,
} from "@/hooks/use-model-lifecycle";
import { useFleetOverview } from "@/hooks/use-operations";
import { useSites } from "@/hooks/use-sites";
import {
  deriveSceneReadinessRows,
  healthToTone,
} from "@/lib/operational-health";

const jetsonTargetProfile = "linux-aarch64-nvidia-jetson";

export function CamerasPage() {
  return (
    <RequireRole role="admin">
      <CamerasContent />
    </RequireRole>
  );
}

function CamerasContent() {
  const brandName = productBrand.name;
  const [wizardMode, setWizardMode] = useState<"create" | "edit" | null>(null);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [selectedRulesCameraId, setSelectedRulesCameraId] = useState<
    string | null
  >(null);
  const [selectedPolicyCameraId, setSelectedPolicyCameraId] = useState<
    string | null
  >(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [sceneSearch, setSceneSearch] = useState("");
  const [selectedSceneIds, setSelectedSceneIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [inventoryPageSize, setInventoryPageSize] =
    useState<PaginationPageSize>(10);
  const [inventoryPageIndex, setInventoryPageIndex] = useState(0);
  const { data: cameras = [], isLoading: camerasLoading } = useCameras();
  const { data: sites = [] } = useSites();
  const {
    data: models = [],
    error: modelsError,
    isLoading: modelsLoading,
    isRefetching: modelsRefreshing,
    refetch: refetchModels,
  } = useModels();
  const modelRuntimeArtifacts = useRuntimeArtifactsByModelId(
    models.map((model) => model.id),
  );
  const createCamera = useCreateCamera();
  const updateCamera = useUpdateCamera();
  const deleteCamera = useDeleteCamera();
  const fleet = useFleetOverview();

  const siteNameById = useMemo(
    () => new Map(sites.map((site) => [site.id, site.name])),
    [sites],
  );
  const cameraIdSet = useMemo(
    () => new Set(cameras.map((camera) => camera.id)),
    [cameras],
  );
  const sceneFocusItems = useMemo(
    () =>
      cameras.map((camera) => ({
        id: camera.id,
        name: camera.name,
        siteName: siteNameById.get(camera.site_id) ?? "Unknown site",
      })),
    [cameras, siteNameById],
  );
  const searchedSceneFocusItems = useMemo(
    () => filterSceneFocusItems(sceneFocusItems, sceneSearch),
    [sceneFocusItems, sceneSearch],
  );
  const focusedSceneIds = useMemo(() => {
    if (selectedSceneIds.size > 0) {
      return new Set(
        Array.from(selectedSceneIds).filter((sceneId) =>
          cameraIdSet.has(sceneId),
        ),
      );
    }

    if (sceneSearch.trim().length > 0) {
      return new Set(searchedSceneFocusItems.map((item) => item.id));
    }

    return new Set<string>();
  }, [cameraIdSet, sceneSearch, searchedSceneFocusItems, selectedSceneIds]);
  const focusedInventoryCameras = useMemo(
    () => cameras.filter((camera) => focusedSceneIds.has(camera.id)),
    [cameras, focusedSceneIds],
  );
  const paginatedInventoryCameras = paginateItems(
    focusedInventoryCameras,
    inventoryPageSize,
    inventoryPageIndex,
  );
  const sceneInventorySummary =
    cameras.length === 0
      ? "0 of 0 scenes shown"
      : selectedSceneIds.size === 0 && sceneSearch.trim().length === 0
        ? "No scenes selected"
        : `${focusedInventoryCameras.length} of ${cameras.length} scenes shown`;
  const sceneHealthRows = useMemo(
    () => deriveSceneReadinessRows({ cameras, fleet: fleet.data }),
    [cameras, fleet.data],
  );
  const modelById = useMemo(
    () => new Map(models.map((model) => [model.id, model])),
    [models],
  );
  const assignedDeploymentNodeByCamera = useMemo(
    () =>
      new Map(
        (fleet.data?.delivery_diagnostics ?? [])
          .filter((diagnostic) => diagnostic.assigned_node_id)
          .map((diagnostic) => [
            diagnostic.camera_id,
            diagnostic.assigned_node_id as string,
          ]),
      ),
    [fleet.data],
  );
  const edgeNodeOptions = useMemo(
    () =>
      (fleet.data?.nodes ?? [])
        .filter((node) => node.kind === "edge" && node.id)
        .map((node) => ({
          id: node.id as string,
          hostname: node.hostname,
          status: node.status,
          siteId: node.site_id ?? null,
        })),
    [fleet.data],
  );
  const sceneHealthByCamera = useMemo(
    () => new Map(sceneHealthRows.map((row) => [row.cameraId, row])),
    [sceneHealthRows],
  );
  const rulesCamera = useMemo(
    () => cameras.find((camera) => camera.id === selectedRulesCameraId) ?? null,
    [cameras, selectedRulesCameraId],
  );
  const policyCamera = useMemo(
    () =>
      cameras.find((camera) => camera.id === selectedPolicyCameraId) ?? null,
    [cameras, selectedPolicyCameraId],
  );
  const modelQueryEmpty = models.length === 0;
  const wizardModels = useMemo(
    () =>
      toWizardModelOptions(
        models,
        [selectedCamera?.primary_model_id, selectedCamera?.secondary_model_id],
        modelRuntimeArtifacts.data ?? {},
      ),
    [
      models,
      modelRuntimeArtifacts.data,
      selectedCamera?.primary_model_id,
      selectedCamera?.secondary_model_id,
    ],
  );

  useEffect(() => {
    setSelectedSceneIds((current) => {
      const next = new Set(
        Array.from(current).filter((sceneId) => cameraIdSet.has(sceneId)),
      );
      return next.size === current.size ? current : next;
    });
  }, [cameraIdSet]);

  useEffect(() => {
    setInventoryPageIndex(0);
  }, [focusedInventoryCameras.length, inventoryPageSize, sceneSearch]);

  function toggleFocusedScene(sceneId: string) {
    setSelectedSceneIds((current) => {
      const next = new Set(current);
      if (next.has(sceneId)) {
        next.delete(sceneId);
      } else {
        next.add(sceneId);
      }
      return next;
    });
  }

  function openCreateWizard() {
    void refetchModels();
    void modelRuntimeArtifacts.refetch();
    setSelectedCamera(null);
    setSelectedRulesCameraId(null);
    setSelectedPolicyCameraId(null);
    setWizardMode("create");
  }

  function openEditWizard(camera: Camera) {
    void refetchModels();
    void modelRuntimeArtifacts.refetch();
    setSelectedCamera(camera);
    setSelectedRulesCameraId(null);
    setSelectedPolicyCameraId(null);
    setWizardMode("edit");
  }

  function openRulesPanel(camera: Camera) {
    setWizardMode(null);
    setSelectedCamera(null);
    setSelectedPolicyCameraId(null);
    setSelectedRulesCameraId(camera.id);
  }

  function openPolicyDraftPanel(camera: Camera) {
    setWizardMode(null);
    setSelectedCamera(null);
    setSelectedRulesCameraId(null);
    setSelectedPolicyCameraId(camera.id);
  }

  function closeWizard() {
    setSelectedCamera(null);
    setWizardMode(null);
  }

  async function handleDeleteCamera(camera: Camera) {
    if (!window.confirm(`Delete ${camera.name}? This cannot be undone.`)) {
      return;
    }

    setDeleteError(null);
    try {
      await deleteCamera.mutateAsync(camera.id);
    } catch (error) {
      setDeleteError(
        error instanceof Error ? error.message : "Failed to delete scene.",
      );
      return;
    }

    if (selectedCamera?.id === camera.id) {
      closeWizard();
    }
    if (selectedRulesCameraId === camera.id) {
      setSelectedRulesCameraId(null);
    }
    if (selectedPolicyCameraId === camera.id) {
      setSelectedPolicyCameraId(null);
    }
  }

  return (
    <div data-testid="scene-setup-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Scenes"
        title={omniLabels.sceneSetupTitle}
        description={`Scene setup connects source streams, models, privacy rules, event boundaries, and calibration so ${brandName} can understand each environment.`}
        actions={<Button onClick={openCreateWizard}>Add scene</Button>}
      />

      {deleteError ? (
        <div
          role="alert"
          className="rounded-[0.75rem] border border-[#5a2330] bg-[#241118] px-4 py-3 text-sm text-[#ffc2cd]"
        >
          {deleteError}
        </div>
      ) : null}

      <section className="space-y-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea4c7]">
            Setup flow
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[#f4f8ff]">
            Guided setup flow
          </h2>
        </div>
        <div
          data-testid="scene-setup-sequence"
          className="grid gap-3 rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-rail)] p-4 sm:grid-cols-5"
        >
          {["Source", "Model", "Privacy", "Boundaries", "Calibration"].map(
            (step, index) => (
              <div
                key={step}
                className="rounded-[0.75rem] border border-white/8 bg-black/20 px-3 py-3"
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7f96b8]">
                  Step {index + 1}
                </p>
                <p className="mt-2 text-sm font-semibold text-[#f4f8ff]">
                  {step}
                </p>
              </div>
            ),
          )}
        </div>
      </section>

      <section className="space-y-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea4c7]">
            Inventory
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[#f4f8ff]">
            Scene inventory
          </h2>
        </div>
        <SceneFocusPicker
          defaultSummary={sceneInventorySummary}
          items={sceneFocusItems}
          onClearSelection={() => setSelectedSceneIds(new Set())}
          onSearchChange={setSceneSearch}
          onToggleScene={toggleFocusedScene}
          searchLabel="Search scene inventory"
          searchPlaceholder="Search by scene or site"
          searchValue={sceneSearch}
          selectedSceneIds={selectedSceneIds}
          title="Choose scene inventory"
        />
        <div
          data-testid="scene-inventory-table"
          className="overflow-x-auto rounded-[0.9rem] border border-white/8 bg-[#0b1320]"
        >
          <PaginationControls
            className="px-4 pt-4"
            itemLabel="scenes"
            pageIndex={paginatedInventoryCameras.currentPageIndex}
            pageSize={inventoryPageSize}
            pageSizeLabel="Scene inventory per page"
            totalCount={focusedInventoryCameras.length}
            onPageIndexChange={setInventoryPageIndex}
            onPageSizeChange={setInventoryPageSize}
          />
          <Table className="min-w-[76rem]">
            <THead>
              <TR>
                <TH>Scene</TH>
                <TH>Site</TH>
                <TH>Mode</TH>
                <TH>Vision</TH>
                <TH>Stream</TH>
                <TH>Tracker</TH>
                <TH>Readiness</TH>
                <TH>Actions</TH>
              </TR>
            </THead>
            <TBody>
              {camerasLoading ? (
                <TR>
                  <TD colSpan={8} className="text-[#9eb2cf]">
                    Loading scenes...
                  </TD>
                </TR>
              ) : cameras.length === 0 ? (
                <TR>
                  <TD colSpan={8} className="text-[#9eb2cf]">
                    {omniEmptyStates.noScenes}
                  </TD>
                </TR>
              ) : focusedInventoryCameras.length === 0 ? (
                <TR>
                  <TD colSpan={8} className="text-[#9eb2cf]">
                    {selectedSceneIds.size === 0 &&
                    sceneSearch.trim().length === 0
                      ? "Select or search scenes to inspect inventory."
                      : "No scenes match this selection."}
                  </TD>
                </TR>
              ) : (
                paginatedInventoryCameras.items.map((camera) => {
                  const sceneHealth = sceneHealthByCamera.get(camera.id);
                  const visionSummary = getCameraVisionSummary(camera);
                  const primaryModel = modelById.get(camera.primary_model_id);
                  const deploymentNodeId =
                    assignedDeploymentNodeByCamera.get(camera.id) ??
                    camera.edge_node_id ??
                    null;
                  const runtimeArtifacts =
                    camera.primary_model_id
                      ? (modelRuntimeArtifacts.data?.[
                          camera.primary_model_id
                        ] ?? [])
                      : [];

                  return (
                    <TR key={camera.id}>
                      <TD className="font-medium text-[#eef4ff]">
                        {camera.name}
                      </TD>
                      <TD>
                        {siteNameById.get(camera.site_id) ?? "Unknown site"}
                      </TD>
                      <TD>{camera.processing_mode}</TD>
                      <TD>
                        <div className="min-w-[8rem] leading-tight">
                          <div className="font-medium text-[#eef4ff]">
                            {visionSummary.accuracy}
                          </div>
                          <div className="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-xs text-[#93a7c5]">
                            <span>{visionSummary.compute}</span>
                            <span
                              className={
                                visionSummary.speedEnabled
                                  ? "text-[#a9dfc0]"
                                  : "text-[#93a7c5]"
                              }
                            >
                              {visionSummary.speed}
                            </span>
                          </div>
                        </div>
                      </TD>
                      <TD>
                        <div className="font-medium text-[#eef4ff]">
                          {camera.browser_delivery?.default_profile ?? "720p10"}
                        </div>
                        {camera.source_capability ? (
                          <div className="mt-1 text-xs text-[#93a7c5]">
                            source{" "}
                            {`${camera.source_capability.width}×${camera.source_capability.height}`}
                          </div>
                        ) : null}
                      </TD>
                      <TD>{camera.tracker_type}</TD>
                      <TD>
                        <SceneReadinessCell
                          camera={camera}
                          deploymentNodeId={deploymentNodeId}
                          model={primaryModel ?? null}
                          runtimeArtifacts={runtimeArtifacts}
                          sceneHealth={sceneHealth}
                        />
                      </TD>
                      <TD>
                        <div className="flex gap-2">
                          <button
                            aria-label={`Open rules for ${camera.name}`}
                            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                            type="button"
                            onClick={() => openRulesPanel(camera)}
                          >
                            Rules
                          </button>
                          <button
                            aria-label={`Open policy for ${camera.name}`}
                            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                            type="button"
                            onClick={() => openPolicyDraftPanel(camera)}
                          >
                            Policy
                          </button>
                          <button
                            aria-label={`Edit ${camera.name}`}
                            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                            type="button"
                            onClick={() => openEditWizard(camera)}
                          >
                            Edit
                          </button>
                          <button
                            aria-label={`Delete ${camera.name}`}
                            className="rounded-full border border-[#5a2330] bg-[#241118] px-3 py-1.5 text-xs font-medium text-[#ffc2cd] transition hover:bg-[#311722]"
                            type="button"
                            onClick={() => void handleDeleteCamera(camera)}
                          >
                            Delete
                          </button>
                        </div>
                      </TD>
                    </TR>
                  );
                })
              )}
            </TBody>
          </Table>
        </div>
      </section>

      {rulesCamera ? (
        <IncidentRulesPanel
          camera={rulesCamera}
          onClose={() => setSelectedRulesCameraId(null)}
        />
      ) : null}

      {policyCamera ? (
        <PolicyDraftReview
          camera={policyCamera}
          onClose={() => setSelectedPolicyCameraId(null)}
        />
      ) : null}

      {wizardMode ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#8ea4c7]">
                {wizardMode === "create" ? "Create scene" : "Edit scene"}
              </p>
              <h3 className="mt-2 text-2xl font-semibold text-[#f4f8ff]">
                {wizardMode === "create"
                  ? "Complete the guided setup for a new scene."
                  : `Update ${selectedCamera?.name ?? "scene"} without exposing the stored RTSP URL.`}
              </h3>
            </div>
            <Button
              className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
              onClick={closeWizard}
            >
              Close setup
            </Button>
          </div>

          <CameraWizard
            initialCamera={selectedCamera}
            edgeNodes={edgeNodeOptions}
            models={wizardModels}
            modelsError={
              modelQueryEmpty && modelsError instanceof Error
                ? modelsError.message
                : null
            }
            modelsLoading={
              modelQueryEmpty && (modelsLoading || modelsRefreshing)
            }
            onRetryModels={() => void refetchModels()}
            sites={sites.map((site) => ({ id: site.id, name: site.name }))}
            onSubmit={async (payload) => {
              if (wizardMode === "edit" && selectedCamera) {
                await updateCamera.mutateAsync({
                  cameraId: selectedCamera.id,
                  payload: payload as UpdateCameraInput,
                });
              } else {
                await createCamera.mutateAsync(payload as CreateCameraInput);
              }

              closeWizard();
            }}
          />
          <ModelCatalogHints modelInventoryCount={wizardModels.length} />
        </section>
      ) : null}
    </div>
  );
}

function SceneReadinessCell({
  camera,
  deploymentNodeId,
  model,
  runtimeArtifacts,
  sceneHealth,
}: {
  camera: Camera;
  deploymentNodeId: string | null;
  model: Model | null;
  runtimeArtifacts: RuntimeArtifact[];
  sceneHealth: ReturnType<typeof deriveSceneReadinessRows>[number] | undefined;
}) {
  const isEdgeRuntime =
    camera.processing_mode === "edge" || camera.processing_mode === "hybrid";
  const inventory = useDeploymentModelInventory(
    isEdgeRuntime ? deploymentNodeId : null,
  );
  const createArtifactBuildJob = useCreateRuntimeArtifactBuildJob(
    camera.primary_model_id ?? "",
  );
  const runtimeReadiness = deriveRuntimeReadiness({
    camera,
    deploymentNodeId,
    inventoryItems: inventory.data?.items ?? [],
    inventoryLoading: inventory.isLoading,
    isEdgeRuntime,
    model,
    runtimeArtifacts,
  });
  const canBuildArtifact = Boolean(
    runtimeReadiness.canBuildArtifact && model && deploymentNodeId,
  );

  return (
    <div className="min-w-[13rem] space-y-2">
      {sceneHealth ? (
        <StatusToneBadge tone={healthToTone(sceneHealth.readiness.health)}>
          {sceneHealth.readiness.label}
        </StatusToneBadge>
      ) : (
        <StatusToneBadge tone="muted">Readiness pending</StatusToneBadge>
      )}
      <div className="space-y-1">
        <StatusToneBadge tone={runtimeReadiness.tone}>
          {runtimeReadiness.label}
        </StatusToneBadge>
        {runtimeReadiness.detail ? (
          <p className="text-xs leading-5 text-[#93a7c5]">
            {runtimeReadiness.detail}
          </p>
        ) : null}
      </div>
      {canBuildArtifact ? (
        <button
          aria-label={`Build artifact for ${camera.name}`}
          className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
          disabled={createArtifactBuildJob.isPending}
          type="button"
          onClick={() => {
            if (!model || !deploymentNodeId) {
              return;
            }
            void createArtifactBuildJob.mutateAsync({
              camera_id: camera.id,
              deployment_node_id: deploymentNodeId,
              build_format: "tensorrt_engine",
              target_profile: jetsonTargetProfile,
              precision: "fp16",
              input_shape: model.input_shape,
              builder_options:
                model.capability === "open_vocab"
                  ? {
                      vocabulary_terms: camera.runtime_vocabulary?.terms ?? [],
                      vocabulary_version:
                        camera.runtime_vocabulary?.version ?? null,
                    }
                  : undefined,
            });
          }}
        >
          Build artifact
        </button>
      ) : null}
    </div>
  );
}

type RuntimeReadiness = {
  canBuildArtifact: boolean;
  detail?: string;
  label: string;
  tone: "healthy" | "attention" | "danger" | "muted";
};

function deriveRuntimeReadiness({
  camera,
  deploymentNodeId,
  inventoryItems,
  inventoryLoading,
  isEdgeRuntime,
  model,
  runtimeArtifacts,
}: {
  camera: Camera;
  deploymentNodeId: string | null;
  inventoryItems: NonNullable<
    ReturnType<typeof useDeploymentModelInventory>["data"]
  >["items"];
  inventoryLoading: boolean;
  isEdgeRuntime: boolean;
  model: Model | null;
  runtimeArtifacts: RuntimeArtifact[];
}): RuntimeReadiness {
  if (!camera.primary_model_id) {
    return {
      canBuildArtifact: false,
      label: "Model not selected",
      tone: "attention",
    };
  }

  if (!model) {
    return {
      canBuildArtifact: false,
      label: "Model not registered",
      tone: "danger",
    };
  }

  if (!isEdgeRuntime) {
    return {
      canBuildArtifact: false,
      label: "Model registered",
      tone: "healthy",
    };
  }

  if (!deploymentNodeId) {
    return {
      canBuildArtifact: false,
      label: "No edge node assigned",
      tone: "attention",
    };
  }

  if (inventoryLoading) {
    return {
      canBuildArtifact: false,
      label: "Checking edge inventory",
      tone: "muted",
    };
  }

  if (!hasSyncedModelInventory(model, inventoryItems ?? [])) {
    return {
      canBuildArtifact: false,
      label: "Model not synced to edge node",
      tone: "attention",
    };
  }

  const artifact = findTargetRuntimeArtifact({
    camera,
    model,
    runtimeArtifacts,
  });

  if (!artifact) {
    return {
      canBuildArtifact: true,
      label: `No TensorRT artifact for ${jetsonTargetProfile}`,
      tone: "attention",
    };
  }

  if (model.capability === "open_vocab" && isVocabularyStale(camera, artifact)) {
    return {
      canBuildArtifact: true,
      detail: `Artifact vocabulary v${artifact.vocabulary_version ?? "unknown"} does not match scene vocabulary v${camera.runtime_vocabulary?.version ?? "unknown"}.`,
      label: "Open-vocab artifact stale: vocabulary changed",
      tone: "attention",
    };
  }

  if (artifact.validation_status !== "valid") {
    return {
      canBuildArtifact: true,
      label: `Runtime artifact ${artifact.validation_status}`,
      tone:
        artifact.validation_status === "invalid" ||
        artifact.validation_status === "missing_artifact"
          ? "danger"
          : "attention",
    };
  }

  return {
    canBuildArtifact: false,
    detail: artifact.path,
    label: "Runtime artifact ready",
    tone: "healthy",
  };
}

function hasSyncedModelInventory(
  model: Model,
  inventoryItems: NonNullable<
    ReturnType<typeof useDeploymentModelInventory>["data"]
  >["items"],
) {
  return (inventoryItems ?? []).some(
    (item) =>
      item.asset_kind === "model" &&
      item.asset_id === model.id &&
      (!model.sha256 || item.sha256 === model.sha256),
  );
}

function findTargetRuntimeArtifact({
  camera,
  model,
  runtimeArtifacts,
}: {
  camera: Camera;
  model: Model;
  runtimeArtifacts: RuntimeArtifact[];
}) {
  const requiredKind =
    model.capability === "open_vocab"
      ? "compiled_open_vocab"
      : "tensorrt_engine";
  const candidates = runtimeArtifacts.filter(
    (artifact) =>
      artifact.kind === requiredKind &&
      artifact.target_profile === jetsonTargetProfile,
  );

  if (model.capability === "open_vocab") {
    return (
      candidates.find(
        (artifact) =>
          artifact.scope === "scene" && artifact.camera_id === camera.id,
      ) ?? candidates[0]
    );
  }

  return (
    candidates.find((artifact) => artifact.validation_status === "valid") ??
    candidates[0] ??
    null
  );
}

function isVocabularyStale(camera: Camera, artifact: RuntimeArtifact) {
  const sceneVocabularyVersion = camera.runtime_vocabulary?.version;
  if (
    typeof sceneVocabularyVersion === "number" &&
    typeof artifact.vocabulary_version === "number"
  ) {
    return artifact.vocabulary_version !== sceneVocabularyVersion;
  }

  return artifact.validation_status === "stale";
}

function toWizardModelOptions(
  models: Model[],
  pinnedModelIds: Array<string | null | undefined>,
  runtimeArtifactsByModelId: Record<string, ModelOption["runtime_artifacts"]>,
): ModelOption[] {
  const pinnedIds = new Set(
    pinnedModelIds.filter((id): id is string => Boolean(id)),
  );
  const optionsByKey = new Map<string, ModelOption>();

  for (const model of models) {
    const option: ModelOption = {
      id: model.id,
      name: model.name,
      version: model.version,
      classes: model.classes,
      capability: model.capability,
      capability_config: model.capability_config,
      runtime_artifacts: runtimeArtifactsByModelId[model.id] ?? [],
    };
    const key = modelOptionKey(option);
    const current = optionsByKey.get(key);
    if (!current || (pinnedIds.has(option.id) && !pinnedIds.has(current.id))) {
      optionsByKey.set(key, option);
    }
  }

  return Array.from(optionsByKey.values());
}

function modelOptionKey(model: ModelOption) {
  return [
    model.name.trim().toLowerCase(),
    model.version.trim().toLowerCase(),
    model.capability ?? "fixed_vocab",
    model.capability_config?.runtime_backend ?? "onnxruntime",
    model.capability_config?.readiness ?? "ready",
  ].join("\u0000");
}

type CameraVisionProfile = NonNullable<Camera["vision_profile"]>;

const accuracyModeLabels: Record<CameraVisionProfile["accuracy_mode"], string> =
  {
    fast: "Fast",
    balanced: "Balanced",
    maximum_accuracy: "Max accuracy",
    open_vocabulary: "Open vocab",
  };

const computeTierLabels: Record<CameraVisionProfile["compute_tier"], string> = {
  cpu_low: "Low CPU",
  edge_standard: "Standard edge",
  edge_advanced_jetson: "Advanced edge",
  central_gpu: "Central GPU",
};

function getCameraVisionSummary(camera: Camera) {
  const accuracyMode = camera.vision_profile?.accuracy_mode ?? "balanced";
  const computeTier = camera.vision_profile?.compute_tier ?? "edge_standard";
  const speedEnabled =
    camera.vision_profile?.motion_metrics?.speed_enabled ?? false;

  return {
    accuracy: accuracyModeLabels[accuracyMode],
    compute: computeTierLabels[computeTier],
    speed: speedEnabled ? "Speed on" : "Speed off",
    speedEnabled,
  };
}

function ModelCatalogHints({
  modelInventoryCount,
}: {
  modelInventoryCount: number;
}) {
  const { data: catalog = [] } = useModelCatalog();
  if (modelInventoryCount > 0) {
    return null;
  }

  const visibleEntries = catalog
    .filter((entry) => entry.registration_state === "unregistered")
    .filter((entry) => entry.artifact_exists)
    .filter(
      (entry) => (entry.capability_config.readiness ?? "ready") === "ready",
    )
    .slice(0, 4);

  if (visibleEntries.length === 0) {
    return null;
  }

  return (
    <section
      data-testid="model-catalog-hints"
      className="rounded-[0.9rem] border border-white/8 bg-[#0b1320] px-4 py-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
          Model catalog
        </p>
        <p className="text-xs text-[#93a7c5]">
          {visibleEntries.length} available presets
        </p>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {visibleEntries.map((entry) => (
          <CatalogHintEntry key={entry.id} entry={entry} />
        ))}
      </div>
    </section>
  );
}

function CatalogHintEntry({ entry }: { entry: ModelCatalogEntry }) {
  const backend = entry.capability_config.runtime_backend ?? "onnxruntime";
  const readiness = entry.capability_config.readiness ?? "ready";

  return (
    <div className="rounded-[0.75rem] border border-white/8 bg-white/[0.03] px-3 py-3">
      <p className="text-sm font-semibold text-[#eef4ff]">{entry.name}</p>
      <p className="mt-1 text-xs text-[#9eb2cf]">
        {entry.registration_state} - {entry.capability} - {backend} -{" "}
        {readiness}
      </p>
    </div>
  );
}
