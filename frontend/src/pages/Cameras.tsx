import { useMemo, useState } from "react";

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
import { Button } from "@/components/ui/button";
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
import { useModels, type Model } from "@/hooks/use-models";
import { useFleetOverview } from "@/hooks/use-operations";
import { useSites } from "@/hooks/use-sites";
import {
  deriveSceneReadinessRows,
  healthToTone,
} from "@/lib/operational-health";

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
  const { data: cameras = [], isLoading: camerasLoading } = useCameras();
  const { data: sites = [] } = useSites();
  const {
    data: models = [],
    error: modelsError,
    isLoading: modelsLoading,
    isRefetching: modelsRefreshing,
    refetch: refetchModels,
  } = useModels();
  const createCamera = useCreateCamera();
  const updateCamera = useUpdateCamera();
  const deleteCamera = useDeleteCamera();
  const fleet = useFleetOverview();

  const siteNameById = useMemo(
    () => new Map(sites.map((site) => [site.id, site.name])),
    [sites],
  );
  const sceneHealthRows = useMemo(
    () => deriveSceneReadinessRows({ cameras, fleet: fleet.data }),
    [cameras, fleet.data],
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
      toWizardModelOptions(models, [
        selectedCamera?.primary_model_id,
        selectedCamera?.secondary_model_id,
      ]),
    [
      models,
      selectedCamera?.primary_model_id,
      selectedCamera?.secondary_model_id,
    ],
  );

  function openCreateWizard() {
    void refetchModels();
    setSelectedCamera(null);
    setSelectedRulesCameraId(null);
    setSelectedPolicyCameraId(null);
    setWizardMode("create");
  }

  function openEditWizard(camera: Camera) {
    void refetchModels();
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

    await deleteCamera.mutateAsync(camera.id);

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

      <section
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
      </section>

      <section
        data-testid="scene-inventory-table"
        className="overflow-hidden rounded-[0.9rem] border border-white/8 bg-[#0b1320]"
      >
        <Table>
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
            ) : (
              cameras.map((camera) => {
                const sceneHealth = sceneHealthByCamera.get(camera.id);
                const visionSummary = getCameraVisionSummary(camera);

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
                      {sceneHealth ? (
                        <StatusToneBadge
                          tone={healthToTone(sceneHealth.readiness.health)}
                        >
                          {sceneHealth.readiness.label}
                        </StatusToneBadge>
                      ) : (
                        <StatusToneBadge tone="muted">
                          Readiness pending
                        </StatusToneBadge>
                      )}
                    </TD>
                    <TD>
                      <div className="flex gap-2">
                        <button
                          className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                          type="button"
                          onClick={() => openRulesPanel(camera)}
                        >
                          Rules
                        </button>
                        <button
                          className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                          type="button"
                          onClick={() => openPolicyDraftPanel(camera)}
                        >
                          Policy
                        </button>
                        <button
                          className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                          type="button"
                          onClick={() => openEditWizard(camera)}
                        >
                          Edit
                        </button>
                        <button
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

function toWizardModelOptions(
  models: Model[],
  pinnedModelIds: Array<string | null | undefined>,
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
