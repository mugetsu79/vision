import { useMemo, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { CameraWizard } from "@/components/cameras/CameraWizard";
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
import { useModels } from "@/hooks/use-models";
import { useSites } from "@/hooks/use-sites";

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

  const siteNameById = useMemo(
    () => new Map(sites.map((site) => [site.id, site.name])),
    [sites],
  );
  const modelQueryEmpty = models.length === 0;

  function openCreateWizard() {
    void refetchModels();
    setSelectedCamera(null);
    setWizardMode("create");
  }

  function openEditWizard(camera: Camera) {
    void refetchModels();
    setSelectedCamera(camera);
    setWizardMode("edit");
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
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.95),rgba(8,11,18,0.92))] shadow-[0_24px_72px_-54px_rgba(0,0,0,0.9)]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
                Scenes
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
                {omniLabels.sceneSetupTitle}
              </h2>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                Scene setup connects source streams, models, privacy rules, event boundaries, and calibration so {brandName} can understand each environment.
              </p>
            </div>
            <Button onClick={openCreateWizard}>Add camera</Button>
          </div>
        </div>

        <div className="px-6 py-6">
          <div className="overflow-hidden rounded-[1.5rem] border border-white/8 bg-[#0b1320]">
            <Table>
              <THead>
                <TR>
                  <TH>Name</TH>
                  <TH>Site</TH>
                  <TH>Mode</TH>
                  <TH>Delivery</TH>
                  <TH>Tracker</TH>
                  <TH>Actions</TH>
                </TR>
              </THead>
              <TBody>
                {camerasLoading ? (
                  <TR>
                    <TD colSpan={6} className="text-[#9eb2cf]">
                      Loading cameras...
                    </TD>
                  </TR>
                ) : cameras.length === 0 ? (
                  <TR>
                    <TD colSpan={6} className="text-[#9eb2cf]">
                      {omniEmptyStates.noScenes}
                    </TD>
                  </TR>
                ) : (
                  cameras.map((camera) => (
                    <TR key={camera.id}>
                      <TD className="font-medium text-[#eef4ff]">{camera.name}</TD>
                      <TD>{siteNameById.get(camera.site_id) ?? "Unknown site"}</TD>
                      <TD>{camera.processing_mode}</TD>
                      <TD>
                        <div className="font-medium text-[#eef4ff]">
                          {camera.browser_delivery?.default_profile ?? "720p10"}
                        </div>
                        {camera.source_capability ? (
                          <div className="mt-1 text-xs text-[#93a7c5]">
                            source {`${camera.source_capability.width}×${camera.source_capability.height}`}
                          </div>
                        ) : null}
                      </TD>
                      <TD>{camera.tracker_type}</TD>
                      <TD>
                        <div className="flex gap-2">
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
                  ))
                )}
              </TBody>
            </Table>
          </div>
        </div>
      </section>

      {wizardMode ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#8ea4c7]">
                {wizardMode === "create" ? "Create camera" : "Edit camera"}
              </p>
              <h3 className="mt-2 text-2xl font-semibold text-[#f4f8ff]">
                {wizardMode === "create"
                  ? "Complete the guided setup for a new camera."
                  : `Update ${selectedCamera?.name ?? "camera"} without exposing the stored RTSP URL.`}
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
            models={models.map((model) => ({
              id: model.id,
              name: model.name,
              version: model.version,
              classes: model.classes,
            }))}
            modelsError={
              modelQueryEmpty && modelsError instanceof Error ? modelsError.message : null
            }
            modelsLoading={modelQueryEmpty && (modelsLoading || modelsRefreshing)}
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
        </section>
      ) : null}
    </div>
  );
}
