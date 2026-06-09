import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  AlertTriangle,
  Cpu,
  Download,
  Package,
  RefreshCw,
  Send,
  UploadCloud,
} from "lucide-react";

import {
  StatusToneBadge,
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { useCameras, type Camera } from "@/hooks/use-cameras";
import { useDeploymentNodes, type DeploymentNode } from "@/hooks/use-deployment";
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
  useAssignDeploymentModel,
  useCreateModelSyncJob,
  useCreateRuntimeArtifactBuildJob,
  useDeploymentModelAssignments,
  useDeploymentModelInventory,
  useDownloadCatalogModel,
  useEdgeConfiguration,
  useImportModelFromUrl,
  useModelImportJobs,
  useRegisterCatalogModel,
  useRuntimeArtifactBuildJobs,
} from "@/hooks/use-model-lifecycle";

type TabId =
  | "catalog"
  | "registered"
  | "imports"
  | "runtime-artifacts"
  | "edge-distribution";

const tabs = [
  { id: "catalog", label: "Catalog" },
  { id: "registered", label: "Registered" },
  { id: "imports", label: "Imports" },
  { id: "runtime-artifacts", label: "Runtime artifacts" },
  { id: "edge-distribution", label: "Edge distribution" },
] as const satisfies readonly { id: TabId; label: string }[];

const defaultTargetProfile = "linux-aarch64-nvidia-jetson";
const emptyModels: Model[] = [];
const emptyDeploymentNodes: DeploymentNode[] = [];
const emptyCameras: Camera[] = [];

export function ModelsPage() {
  const catalog = useModelCatalog();
  const modelsQuery = useModels();
  const deploymentNodes = useDeploymentNodes();
  const cameras = useCameras();
  const models = modelsQuery.data ?? emptyModels;
  const nodes = deploymentNodes.data ?? emptyDeploymentNodes;
  const cameraList = cameras.data ?? emptyCameras;
  const edgeNodes = useMemo(
    () => nodes.filter((node) => node.node_kind !== "central"),
    [nodes],
  );
  const modelIds = useMemo(() => models.map((model) => model.id), [models]);
  const runtimeArtifacts = useRuntimeArtifactsByModelId(modelIds);
  const [activeTab, setActiveTab] = useState<TabId>("catalog");
  const [selectedModelId, setSelectedModelId] = useState(
    () => models[0]?.id ?? "",
  );
  const [selectedNodeId, setSelectedNodeId] = useState(
    () => edgeNodes[0]?.id ?? nodes[0]?.id ?? "",
  );
  const [selectedCameraId, setSelectedCameraId] = useState(
    () => cameras.data?.[0]?.id ?? "",
  );
  const [importName, setImportName] = useState("Custom ONNX detector");
  const [importVersion, setImportVersion] = useState("2026.1");
  const [importUrl, setImportUrl] = useState("");
  const [importSha256, setImportSha256] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedModelId && models[0]) {
      setSelectedModelId(models[0].id);
    }
  }, [models, selectedModelId]);

  useEffect(() => {
    if (!selectedNodeId && (edgeNodes[0] || nodes[0])) {
      setSelectedNodeId((edgeNodes[0] ?? nodes[0]).id);
    }
  }, [edgeNodes, nodes, selectedNodeId]);

  useEffect(() => {
    if (!selectedCameraId && cameraList[0]) {
      setSelectedCameraId(cameraList[0].id);
    }
  }, [cameraList, selectedCameraId]);

  const selectedModel =
    models.find((model) => model.id === selectedModelId) ?? null;
  const selectedNode =
    nodes.find((node) => node.id === selectedNodeId) ??
    edgeNodes[0] ??
    nodes[0] ??
    null;
  const artifactMap = runtimeArtifacts.data ?? {};
  const selectedModelArtifacts = selectedModelId
    ? (artifactMap[selectedModelId] ?? [])
    : [];
  const assignmentQuery = useDeploymentModelAssignments(selectedNodeId || null);
  const inventoryQuery = useDeploymentModelInventory(selectedNodeId || null);
  const edgeConfiguration = useEdgeConfiguration(selectedNodeId || null);
  const buildJobs = useRuntimeArtifactBuildJobs(selectedModelId || null);
  const importJobs = useModelImportJobs();
  const registerCatalog = useRegisterCatalogModel();
  const downloadCatalog = useDownloadCatalogModel();
  const importModel = useImportModelFromUrl();
  const assignModel = useAssignDeploymentModel(selectedNodeId);
  const startSyncJob = useCreateModelSyncJob(selectedNodeId);
  const createBuildJob = useCreateRuntimeArtifactBuildJob(selectedModelId);

  async function runAction(successMessage: string, action: () => Promise<unknown>) {
    setActionMessage(null);
    setActionError(null);
    try {
      await action();
      setActionMessage(successMessage);
    } catch (error) {
      setActionError(errorMessage(error));
    }
  }

  function submitImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runAction("Model import job queued.", () =>
      importModel.mutateAsync({
        source: "url",
        source_uri: importUrl,
        expected_sha256: importSha256 || null,
        name: importName,
        version: importVersion,
        task: "detect",
        format: "onnx",
        capability: "fixed_vocab",
        input_shape: { width: 640, height: 640 },
        classes: [],
        license: "Custom",
      }),
    );
  }

  const buildInputShape = selectedModel?.input_shape ?? {
    width: 640,
    height: 640,
  };
  const targetProfile = selectedNode?.host_profile || defaultTargetProfile;

  return (
    <div data-testid="models-workspace" className="space-y-5">
      <WorkspaceBand
        eyebrow="Models"
        title="Model Management"
        description="Register bundled models, import trusted artifacts, distribute source models to edge nodes, and create runtime artifacts for target profiles."
        accent="cerulean"
        actions={
          <Button
            variant="ghost"
            onClick={() => setActiveTab("runtime-artifacts")}
          >
            <Cpu className="mr-2 h-4 w-4" aria-hidden="true" />
            Build runtime
          </Button>
        }
      >
        <div className="flex flex-wrap gap-2" role="group" aria-label="Model workspace tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              aria-pressed={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={[
                "rounded-full border px-3.5 py-2 text-sm font-medium transition",
                activeTab === tab.id
                  ? "border-[color:var(--vz-lens-cerulean)] bg-[rgba(118,224,255,0.16)] text-[var(--vz-text-primary)]"
                  : "border-[color:var(--vz-hair)] bg-white/[0.035] text-[var(--vz-text-secondary)] hover:border-[color:var(--vz-hair-strong)]",
              ].join(" ")}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </WorkspaceBand>

      {actionError ? (
        <WorkspaceSurface className="border-[#5a2330] bg-[#241118] px-5 py-4 text-sm text-[#ffc2cd]">
          {actionError}
        </WorkspaceSurface>
      ) : null}
      {actionMessage ? (
        <WorkspaceSurface className="border-[rgba(111,224,163,0.28)] bg-[rgba(10,36,24,0.72)] px-5 py-4 text-sm text-[var(--vz-state-healthy)]">
          {actionMessage}
        </WorkspaceSurface>
      ) : null}

      {activeTab === "catalog" ? (
        <CatalogTab
          entries={catalog.data ?? []}
          isLoading={catalog.isLoading}
          onDownload={(entry) => {
            void runAction(`Download queued for ${entry.name}.`, () =>
              downloadCatalog.mutateAsync(entry.id),
            );
          }}
          onRegister={(entry) => {
            void runAction(`${entry.name} registered.`, () =>
              registerCatalog.mutateAsync(entry.id),
            );
          }}
        />
      ) : null}

      {activeTab === "registered" ? (
        <RegisteredTab
          models={models}
          artifactsByModelId={artifactMap}
          isLoading={modelsQuery.isLoading}
        />
      ) : null}

      {activeTab === "imports" ? (
        <ImportsTab
          importName={importName}
          importSha256={importSha256}
          importUrl={importUrl}
          importVersion={importVersion}
          jobs={importJobs.data ?? []}
          onImportNameChange={setImportName}
          onImportSha256Change={setImportSha256}
          onImportUrlChange={setImportUrl}
          onImportVersionChange={setImportVersion}
          onSubmit={submitImport}
        />
      ) : null}

      {activeTab === "runtime-artifacts" ? (
        <RuntimeArtifactsTab
          artifacts={selectedModelArtifacts}
          buildJobs={buildJobs.data ?? []}
          cameras={cameraList}
          models={models}
          nodes={edgeNodes.length > 0 ? edgeNodes : nodes}
          selectedCameraId={selectedCameraId}
          selectedModel={selectedModel}
          selectedModelId={selectedModelId}
          selectedNodeId={selectedNodeId}
          targetProfile={targetProfile}
          onBuildOpenVocabulary={() => {
            void runAction("Open-vocabulary artifact build job queued.", () =>
              createBuildJob.mutateAsync({
                deployment_node_id: selectedNodeId,
                camera_id: selectedCameraId || null,
                build_format: "onnx_export",
                target_profile: targetProfile,
                precision: "fp16",
                input_shape: buildInputShape,
              }),
            );
          }}
          onBuildTensorRt={() => {
            void runAction("TensorRT artifact build job queued.", () =>
              createBuildJob.mutateAsync({
                deployment_node_id: selectedNodeId,
                build_format: "tensorrt_engine",
                target_profile: targetProfile,
                precision: "fp16",
                input_shape: buildInputShape,
              }),
            );
          }}
          onSelectCamera={setSelectedCameraId}
          onSelectModel={setSelectedModelId}
          onSelectNode={setSelectedNodeId}
        />
      ) : null}

      {activeTab === "edge-distribution" ? (
        <EdgeDistributionTab
          assignments={assignmentQuery.data ?? []}
          edgeConfiguration={edgeConfiguration.data ?? null}
          inventory={inventoryQuery.data?.items ?? []}
          models={models}
          nodes={edgeNodes.length > 0 ? edgeNodes : nodes}
          selectedModelId={selectedModelId}
          selectedNodeId={selectedNodeId}
          onAssign={() => {
            void runAction("Model assignment created.", () =>
              assignModel.mutateAsync({
                model_id: selectedModelId,
                desired_path: null,
              }),
            );
          }}
          onSelectModel={setSelectedModelId}
          onSelectNode={setSelectedNodeId}
          onSync={() => {
            void runAction("Model sync job started.", () =>
              startSyncJob.mutateAsync(),
            );
          }}
        />
      ) : null}
    </div>
  );
}

function CatalogTab({
  entries,
  isLoading,
  onDownload,
  onRegister,
}: {
  entries: ModelCatalogEntry[];
  isLoading: boolean;
  onDownload: (entry: ModelCatalogEntry) => void;
  onRegister: (entry: ModelCatalogEntry) => void;
}) {
  return (
    <WorkspaceSurface className="overflow-hidden">
      <SectionHeader
        eyebrow="Catalog"
        title="Bundled and trusted sources"
        description="Register artifacts that already exist on the master or queue trusted downloads when a source is configured."
      />
      {isLoading ? <LoadingRow label="Loading model catalog..." /> : null}
      <div className="overflow-x-auto">
        <Table>
          <THead>
            <TR>
              <TH>Model</TH>
              <TH>Status</TH>
              <TH>Artifact</TH>
              <TH>Path</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {entries.map((entry) => (
              <TR key={entry.id}>
                <TD>
                  <div className="font-semibold text-[var(--vz-text-primary)]">
                    {entry.name}
                  </div>
                  <div className="mt-1 text-xs text-[var(--vz-text-muted)]">
                    {entry.version} · {entry.format} · {entry.capability}
                  </div>
                </TD>
                <TD>
                  <StatusToneBadge tone={catalogTone(entry)}>
                    {catalogLabel(entry)}
                  </StatusToneBadge>
                </TD>
                <TD>
                  {entry.artifact_exists ? (
                    <span className="text-[var(--vz-state-healthy)]">
                      Present
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2 text-[var(--vz-state-attention)]">
                      <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                      Missing artifact
                    </span>
                  )}
                </TD>
                <TD className="min-w-[14rem] text-xs text-[var(--vz-text-muted)]">
                  {catalogPathLabel(entry)}
                </TD>
                <TD>
                  <div className="flex justify-end gap-2">
                    <Button
                      className="whitespace-nowrap"
                      disabled={!entry.artifact_exists}
                      onClick={() => onRegister(entry)}
                      variant="secondary"
                    >
                      <Package className="mr-2 h-4 w-4" aria-hidden="true" />
                      Register {entry.name}
                    </Button>
                    <Button
                      className="whitespace-nowrap"
                      onClick={() => onDownload(entry)}
                      variant="ghost"
                    >
                      <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                      Download
                    </Button>
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </div>
    </WorkspaceSurface>
  );
}

function RegisteredTab({
  artifactsByModelId,
  isLoading,
  models,
}: {
  artifactsByModelId: Record<string, RuntimeArtifact[]>;
  isLoading: boolean;
  models: Model[];
}) {
  return (
    <WorkspaceSurface className="overflow-hidden">
      <SectionHeader
        eyebrow="Registered"
        title="Source models"
        description="Registered source models remain portable; TensorRT engines and scene exports are runtime artifacts."
      />
      {isLoading ? <LoadingRow label="Loading models..." /> : null}
      <div className="overflow-x-auto">
        <Table>
          <THead>
            <TR>
              <TH>Model</TH>
              <TH>Format</TH>
              <TH>Hash</TH>
              <TH>Runtime artifacts</TH>
            </TR>
          </THead>
          <TBody>
            {models.map((model) => {
              const artifacts = artifactsByModelId[model.id] ?? [];
              return (
                <TR key={model.id}>
                  <TD>
                    <div className="font-semibold text-[var(--vz-text-primary)]">
                      {model.name}
                    </div>
                    <div className="mt-1 text-xs text-[var(--vz-text-muted)]">
                      {model.path}
                    </div>
                  </TD>
                  <TD>{model.format}</TD>
                  <TD className="font-mono text-xs">{shortHash(model.sha256)}</TD>
                  <TD>
                    {artifacts.length > 0 ? (
                      <StatusToneBadge tone="healthy">
                        {artifacts.length} artifact{artifacts.length === 1 ? "" : "s"}
                      </StatusToneBadge>
                    ) : (
                      <StatusToneBadge tone="attention">
                        No runtime artifact registered
                      </StatusToneBadge>
                    )}
                  </TD>
                </TR>
              );
            })}
          </TBody>
        </Table>
      </div>
    </WorkspaceSurface>
  );
}

function ImportsTab({
  importName,
  importSha256,
  importUrl,
  importVersion,
  jobs,
  onImportNameChange,
  onImportSha256Change,
  onImportUrlChange,
  onImportVersionChange,
  onSubmit,
}: {
  importName: string;
  importSha256: string;
  importUrl: string;
  importVersion: string;
  jobs: ReturnType<typeof useModelImportJobs>["data"];
  onImportNameChange: (value: string) => void;
  onImportSha256Change: (value: string) => void;
  onImportUrlChange: (value: string) => void;
  onImportVersionChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(20rem,28rem)_minmax(0,1fr)]">
      <WorkspaceSurface className="px-5 py-5">
        <SectionTitle eyebrow="Import" title="URL model import" />
        <form className="mt-5 space-y-4" onSubmit={onSubmit}>
          <LabelledInput
            label="Name"
            value={importName}
            onChange={onImportNameChange}
          />
          <LabelledInput
            label="Version"
            value={importVersion}
            onChange={onImportVersionChange}
          />
          <LabelledInput
            label="Source URL"
            value={importUrl}
            onChange={onImportUrlChange}
            placeholder="https://models.example/yolo26n.onnx"
          />
          <LabelledInput
            label="Expected SHA-256"
            value={importSha256}
            onChange={onImportSha256Change}
            placeholder="64 character checksum"
          />
          <Button type="submit" variant="primary" disabled={!importUrl}>
            <UploadCloud className="mr-2 h-4 w-4" aria-hidden="true" />
            Import model URL
          </Button>
        </form>
      </WorkspaceSurface>

      <WorkspaceSurface className="overflow-hidden" data-testid="model-import-jobs">
        <SectionHeader
          eyebrow="Imports"
          title="Import jobs"
          description="Queued URL imports show hash and source failures here before they become registered models."
        />
        <JobTable jobs={jobs ?? []} emptyLabel="No model import jobs yet." />
      </WorkspaceSurface>
    </div>
  );
}

function RuntimeArtifactsTab({
  artifacts,
  buildJobs,
  cameras,
  models,
  nodes,
  onBuildOpenVocabulary,
  onBuildTensorRt,
  onSelectCamera,
  onSelectModel,
  onSelectNode,
  selectedCameraId,
  selectedModel,
  selectedModelId,
  selectedNodeId,
  targetProfile,
}: {
  artifacts: RuntimeArtifact[];
  buildJobs: ReturnType<typeof useRuntimeArtifactBuildJobs>["data"];
  cameras: ReturnType<typeof useCameras>["data"];
  models: Model[];
  nodes: ReturnType<typeof useDeploymentNodes>["data"];
  onBuildOpenVocabulary: () => void;
  onBuildTensorRt: () => void;
  onSelectCamera: (value: string) => void;
  onSelectModel: (value: string) => void;
  onSelectNode: (value: string) => void;
  selectedCameraId: string;
  selectedModel: Model | null;
  selectedModelId: string;
  selectedNodeId: string;
  targetProfile: string;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(22rem,30rem)_minmax(0,1fr)]">
      <WorkspaceSurface className="px-5 py-5">
        <SectionTitle eyebrow="Builder" title="Create runtime artifact" />
        <div className="mt-5 space-y-4">
          <LabelledSelect
            label="Source model"
            value={selectedModelId}
            onChange={onSelectModel}
            options={models.map((model) => ({ label: model.name, value: model.id }))}
          />
          <LabelledSelect
            label="Target node"
            value={selectedNodeId}
            onChange={onSelectNode}
            options={(nodes ?? []).map((node) => ({
              label: node.hostname,
              value: node.id,
            }))}
          />
          <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.035] px-4 py-3 text-sm text-[var(--vz-text-secondary)]">
            Target profile:{" "}
            <span className="font-mono text-[var(--vz-text-primary)]">
              {targetProfile}
            </span>
          </div>
          <Button
            disabled={!selectedModel || !selectedNodeId}
            onClick={onBuildTensorRt}
            variant="primary"
          >
            <Cpu className="mr-2 h-4 w-4" aria-hidden="true" />
            Build TensorRT artifact
          </Button>
          <div className="border-t border-[color:var(--vz-hair)] pt-4">
            <LabelledSelect
              label="Scene for open-vocab export"
              value={selectedCameraId}
              onChange={onSelectCamera}
              options={(cameras ?? []).map((camera) => ({
                label: camera.name,
                value: camera.id,
              }))}
              placeholder="No scene selected"
            />
            <Button
              className="mt-3"
              disabled={!selectedModel || !selectedNodeId || !selectedCameraId}
              onClick={onBuildOpenVocabulary}
              variant="secondary"
            >
              <Package className="mr-2 h-4 w-4" aria-hidden="true" />
              Build open-vocab artifact
            </Button>
          </div>
        </div>
      </WorkspaceSurface>

      <WorkspaceSurface className="overflow-hidden">
        <SectionHeader
          eyebrow="Artifacts"
          title="Runtime artifacts"
          description="Artifacts are target-specific outputs such as TensorRT engines or scene vocabulary exports."
        />
        <div className="border-t border-[color:var(--vz-hair)] px-5 py-4">
          {artifacts.length === 0 ? (
            <StatusToneBadge tone="attention">
              No runtime artifact registered for{" "}
              {selectedModel?.name ?? "selected model"}
            </StatusToneBadge>
          ) : (
            <div className="space-y-3">
              {artifacts.map((artifact) => (
                <div
                  key={artifact.id}
                  className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.035] px-4 py-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
                        {artifact.kind} · {artifact.target_profile}
                      </p>
                      <p className="mt-2 break-all font-mono text-xs text-[var(--vz-text-muted)]">
                        {artifact.path}
                      </p>
                    </div>
                    <StatusToneBadge
                      tone={runtimeArtifactValidationTone(
                        artifact.validation_status,
                      )}
                    >
                      {runtimeArtifactValidationLabel(artifact)}
                    </StatusToneBadge>
                  </div>
                  {artifact.validation_error ? (
                    <p className="mt-3 break-words text-xs text-[var(--vz-state-risk)]">
                      {artifact.validation_error}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
        <div data-testid="runtime-artifact-build-jobs">
          <JobTable
            jobs={buildJobs ?? []}
            emptyLabel="No runtime artifact build jobs yet."
          />
        </div>
      </WorkspaceSurface>
    </div>
  );
}

function EdgeDistributionTab({
  assignments,
  edgeConfiguration,
  inventory,
  models,
  nodes,
  onAssign,
  onSelectModel,
  onSelectNode,
  onSync,
  selectedModelId,
  selectedNodeId,
}: {
  assignments: ReturnType<typeof useDeploymentModelAssignments>["data"];
  edgeConfiguration: ReturnType<typeof useEdgeConfiguration>["data"] | null;
  inventory: NonNullable<ReturnType<typeof useDeploymentModelInventory>["data"]>["items"];
  models: Model[];
  nodes: ReturnType<typeof useDeploymentNodes>["data"];
  onAssign: () => void;
  onSelectModel: (value: string) => void;
  onSelectNode: (value: string) => void;
  onSync: () => void;
  selectedModelId: string;
  selectedNodeId: string;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(22rem,30rem)_minmax(0,1fr)]">
      <WorkspaceSurface className="px-5 py-5">
        <SectionTitle eyebrow="Distribution" title="Assign and sync" />
        <div className="mt-5 space-y-4">
          <LabelledSelect
            label="Deployment node"
            value={selectedNodeId}
            onChange={onSelectNode}
            options={(nodes ?? []).map((node) => ({
              label: `${node.hostname} · ${node.host_profile}`,
              value: node.id,
            }))}
          />
          <LabelledSelect
            label="Model"
            value={selectedModelId}
            onChange={onSelectModel}
            options={models.map((model) => ({ label: model.name, value: model.id }))}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={!selectedModelId || !selectedNodeId}
              onClick={onAssign}
              variant="primary"
            >
              <Send className="mr-2 h-4 w-4" aria-hidden="true" />
              Assign model to node
            </Button>
            <Button disabled={!selectedNodeId} onClick={onSync} variant="secondary">
              <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
              Start model sync
            </Button>
          </div>
          <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.035] px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--vz-text-muted)]">
              Edge configuration
            </p>
            <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
              Revision {edgeConfiguration?.revision ?? "not assigned"} ·{" "}
              {edgeConfiguration?.apply_status ?? "pending"}
            </p>
          </div>
        </div>
      </WorkspaceSurface>

      <WorkspaceSurface className="overflow-hidden">
        <SectionHeader
          eyebrow="State"
          title="Assignments and inventory"
          description="Assignments express desired state; inventory proves what the edge actually has on disk."
        />
        <div className="grid border-t border-[color:var(--vz-hair)] md:grid-cols-2">
          <StateList
            title="Assignments"
            rows={(assignments ?? []).map((assignment) => ({
              key: assignment.id,
              label: modelName(models, assignment.model_id),
              detail: assignment.error ?? assignment.status,
              tone: assignment.status === "synced" ? "healthy" : "attention",
            }))}
            emptyLabel="No assignments yet."
          />
          <StateList
            title="Inventory"
            rows={(inventory ?? []).map((item) => ({
              key: `${item.asset_id}-${item.sha256}`,
              label: item.local_path,
              detail: `${item.asset_kind} · ${shortHash(item.sha256)}`,
              tone: "healthy",
            }))}
            emptyLabel="No inventory reported yet."
          />
        </div>
      </WorkspaceSurface>
    </div>
  );
}

function JobTable({
  emptyLabel,
  jobs,
}: {
  emptyLabel: string;
  jobs: {
    id: string;
    status: string;
    error?: string | null;
    source?: string;
    build_format?: string;
    target_path?: string;
    target_profile?: string;
    created_at?: string | null;
  }[];
}) {
  if (jobs.length === 0) {
    return <LoadingRow label={emptyLabel} />;
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <THead>
          <TR>
            <TH>Job</TH>
            <TH>Status</TH>
            <TH>Target</TH>
            <TH>Details</TH>
          </TR>
        </THead>
        <TBody>
          {jobs.map((job) => (
            <TR key={job.id}>
              <TD className="font-mono text-xs">{job.id}</TD>
              <TD>
                <StatusToneBadge tone={jobTone(job.status)}>
                  {job.status}
                </StatusToneBadge>
              </TD>
              <TD className="text-xs text-[var(--vz-text-muted)]">
                {job.target_path ?? job.target_profile ?? job.source ?? "Queued"}
              </TD>
              <TD>
                {job.error ? (
                  <span className="text-[var(--vz-state-risk)]">{job.error}</span>
                ) : (
                  <span className="text-[var(--vz-text-muted)]">
                    {job.build_format ?? "Waiting for worker"}
                  </span>
                )}
              </TD>
            </TR>
          ))}
        </TBody>
      </Table>
    </div>
  );
}

function StateList({
  emptyLabel,
  rows,
  title,
}: {
  emptyLabel: string;
  rows: { detail: string; key: string; label: string; tone: "healthy" | "attention" }[];
  title: string;
}) {
  return (
    <div className="min-h-[14rem] border-b border-[color:var(--vz-hair)] px-5 py-5 md:border-b-0 md:border-r md:last:border-r-0">
      <h3 className="font-[family-name:var(--vz-font-display)] text-lg font-semibold text-[var(--vz-text-primary)]">
        {title}
      </h3>
      <div className="mt-4 space-y-3">
        {rows.length === 0 ? (
          <p className="text-sm text-[var(--vz-text-muted)]">{emptyLabel}</p>
        ) : (
          rows.map((row) => (
            <div
              key={row.key}
              className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.035] px-4 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="min-w-0 break-words text-sm font-semibold text-[var(--vz-text-primary)]">
                  {row.label}
                </p>
                <StatusToneBadge tone={row.tone}>{row.tone}</StatusToneBadge>
              </div>
              <p className="mt-2 break-words text-xs text-[var(--vz-text-muted)]">
                {row.detail}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function SectionHeader({
  description,
  eyebrow,
  title,
}: {
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <div className="px-5 py-5">
      <SectionTitle eyebrow={eyebrow} title={title} />
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--vz-text-secondary)]">
        {description}
      </p>
    </div>
  );
}

function SectionTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
        {eyebrow}
      </p>
      <h2 className="mt-2 font-[family-name:var(--vz-font-display)] text-xl font-semibold tracking-normal text-[var(--vz-text-primary)]">
        {title}
      </h2>
    </div>
  );
}

function LoadingRow({ label }: { label: string }) {
  return (
    <div className="border-t border-[color:var(--vz-hair)] px-5 py-5 text-sm text-[var(--vz-text-muted)]">
      {label}
    </div>
  );
}

function LabelledInput({
  label,
  onChange,
  placeholder,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  placeholder?: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
        {label}
      </span>
      <Input
        className="mt-2"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function LabelledSelect({
  label,
  onChange,
  options,
  placeholder = "Select",
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  options: { label: string; value: string }[];
  placeholder?: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
        {label}
      </span>
      <Select
        className="mt-2"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </label>
  );
}

function catalogTone(entry: ModelCatalogEntry) {
  if (!entry.artifact_exists || entry.registration_state === "missing_artifact") {
    return "attention" as const;
  }
  if (entry.registration_state === "registered") {
    return "healthy" as const;
  }
  return "muted" as const;
}

function catalogLabel(entry: ModelCatalogEntry) {
  if (!entry.artifact_exists || entry.registration_state === "missing_artifact") {
    return "Missing artifact";
  }
  if (entry.registration_state === "registered") {
    return "Registered";
  }
  if (entry.registration_state === "planned") {
    return "Download planned";
  }
  return "Unregistered";
}

function catalogPathLabel(entry: ModelCatalogEntry) {
  if (
    entry.format === "engine" &&
    (!entry.artifact_exists || entry.registration_state === "missing_artifact")
  ) {
    return "Managed by runtime artifacts";
  }
  return entry.path_hint;
}

function jobTone(status: string) {
  if (status === "succeeded") {
    return "healthy" as const;
  }
  if (status === "failed" || status === "cancelled") {
    return "danger" as const;
  }
  if (status === "running" || status === "accepted") {
    return "accent" as const;
  }
  return "attention" as const;
}

function runtimeArtifactValidationLabel(artifact: RuntimeArtifact) {
  switch (artifact.validation_status) {
    case "valid":
      return "Runtime artifact ready";
    case "unvalidated":
      return "Built on edge, awaiting validation";
    case "invalid":
      return "Runtime artifact invalid";
    case "stale":
      return "Runtime artifact stale";
    case "missing_artifact":
      return "Runtime artifact missing";
    case "target_mismatch":
      return "Target mismatch";
    default:
      return "Runtime artifact status unknown";
  }
}

function runtimeArtifactValidationTone(
  status: RuntimeArtifact["validation_status"],
) {
  if (status === "valid") {
    return "healthy" as const;
  }
  if (status === "invalid" || status === "missing_artifact") {
    return "danger" as const;
  }
  if (status === "target_mismatch") {
    return "accent" as const;
  }
  return "attention" as const;
}

function shortHash(value: string | null | undefined) {
  if (!value) {
    return "unknown";
  }
  return `${value.slice(0, 10)}...${value.slice(-6)}`;
}

function modelName(models: Model[], modelId: string) {
  return models.find((model) => model.id === modelId)?.name ?? modelId;
}

function errorMessage(error: unknown) {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return "The model lifecycle action failed.";
}
