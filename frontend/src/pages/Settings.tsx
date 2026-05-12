import { useMemo, useState, type ReactNode } from "react";
import {
  Copy,
  Cpu,
  RefreshCw,
  Server,
  ShieldAlert,
  TerminalSquare,
} from "lucide-react";

import {
  InstrumentRail,
  StatusToneBadge,
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { RuntimePassportPanel } from "@/components/evidence/RuntimePassportPanel";
import { OperationalMemoryPanel } from "@/components/evidence/OperationalMemoryPanel";
import { SceneIntelligenceMatrix } from "@/components/operations/SceneIntelligenceMatrix";
import { ConfigurationWorkspace } from "@/components/configuration/ConfigurationWorkspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { omniLabels, omniPlaceExamples } from "@/copy/omnisight";
import { useCameras, type Camera } from "@/hooks/use-cameras";
import {
  useModels,
  useRuntimeArtifactsByModelId,
  type RuntimeArtifact,
} from "@/hooks/use-models";
import {
  type FleetBootstrapResponse,
  type FleetOverview,
  useCreateBootstrapMaterial,
  useFleetOverview,
  useOperationalMemoryPatterns,
} from "@/hooks/use-operations";
import { useSites } from "@/hooks/use-sites";
import { deriveSceneReadinessRows } from "@/lib/operational-health";

type FleetSourceCapability = NonNullable<
  FleetOverview["delivery_diagnostics"][number]["source_capability"]
>;
type FleetRuleRuntime = NonNullable<
  FleetOverview["camera_workers"][number]["rule_runtime"]
>;

export function SettingsPage() {
  const fleet = useFleetOverview();
  const { data: cameras = [] } = useCameras();
  const { data: sites = [] } = useSites();
  const { data: models = [] } = useModels();
  const runtimeArtifacts = useRuntimeArtifactsByModelId(
    models.map((model) => model.id),
  );
  const bootstrap = useCreateBootstrapMaterial();
  const operationalMemory = useOperationalMemoryPatterns({ limit: 8 });
  const [hostname, setHostname] = useState("");
  const [version, setVersion] = useState("0.1.0");
  const [bootstrapResult, setBootstrapResult] =
    useState<FleetBootstrapResponse | null>(null);
  const firstSiteId = fleet.data?.camera_workers[0]?.site_id;
  const camerasById = useMemo(
    () => new Map(cameras.map((camera) => [camera.id, camera])),
    [cameras],
  );

  const modeCopy = useMemo(() => {
    if (fleet.data?.mode === "supervised") {
      return "Supervised production mode";
    }
    if (fleet.data?.mode === "mixed") {
      return "Mixed manual and supervised mode";
    }
    return "Manual dev mode";
  }, [fleet.data?.mode]);

  async function handleBootstrap() {
    if (
      !firstSiteId ||
      hostname.trim().length === 0 ||
      version.trim().length === 0
    ) {
      return;
    }
    const result = await bootstrap.mutateAsync({
      site_id: firstSiteId,
      hostname: hostname.trim(),
      version: version.trim(),
    });
    setBootstrapResult(result);
  }

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
  });
  const edgeNodes = fleet.data.nodes
    .filter((node) => node.id !== null)
    .map((node) => ({
      id: node.id as string,
      hostname: node.hostname,
    }));

  return (
    <div data-testid="operations-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Operations"
        title={omniLabels.operationsTitle}
        description="Monitor planned workers, runtime reports, bootstrap material, and stream diagnostics for the fleet."
        actions={
          <Button type="button" onClick={() => void fleet.refetch()}>
            <RefreshCw className="mr-2 size-4" />
            Refresh
          </Button>
        }
      />

      <SceneIntelligenceMatrix rows={sceneHealthRows} />

      <OperationalMemoryPanel
        patterns={operationalMemory.data ?? []}
        loading={operationalMemory.isLoading}
      />

      <ConfigurationWorkspace
        cameras={cameras}
        sites={sites}
        edgeNodes={edgeNodes}
      />

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

      <WorkspaceSurface className="px-5 py-4">
        <div className="flex items-center gap-3">
          <TerminalSquare className="size-5 text-[#8fd3ff]" />
          <div>
            <h2 className="text-base font-semibold text-[#f4f8ff]">
              {modeCopy}
            </h2>
            <p className="mt-1 text-sm text-[#93a7c5]">
              Start and stop are owned by the local terminal in dev, and by a
              supervisor in production. The UI changes planned state and shows
              diagnostics.
            </p>
          </div>
        </div>
      </WorkspaceSurface>

      <section className="grid gap-4 xl:grid-cols-2">
        <Panel title="Nodes" icon={<Server className="size-4" />}>
          <div className="flex flex-col gap-3">
            {fleet.data.nodes.map((node) => (
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
                      {node.kind} - {node.assigned_camera_ids?.length ?? 0}{" "}
                      assigned scenes
                    </p>
                  </div>
                  <StatusToneBadge tone={statusTone(node.status)}>
                    {node.status}
                  </StatusToneBadge>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          title="Bootstrap edge node"
          icon={<ShieldAlert className="size-4" />}
        >
          <div className="flex flex-col gap-3">
            <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
              Hostname
              <Input
                value={hostname}
                onChange={(event) => setHostname(event.target.value)}
                placeholder={omniPlaceExamples.edgeHostname}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
              Version
              <Input
                value={version}
                onChange={(event) => setVersion(event.target.value)}
                placeholder="0.1.0"
              />
            </label>
            <Button
              type="button"
              disabled={!firstSiteId || bootstrap.isPending}
              onClick={() => void handleBootstrap()}
            >
              <ShieldAlert className="mr-2 size-4" />
              Generate bootstrap
            </Button>
            {bootstrapResult ? (
              <div className="rounded-[1rem] border border-amber-300/30 bg-amber-950/30 p-3 text-sm text-amber-100">
                <p className="font-semibold">Secrets are shown once.</p>
                <CommandBlock text={bootstrapResult.api_key} />
                <CommandBlock text={bootstrapResult.dev_compose_command} />
              </div>
            ) : null}
          </div>
        </Panel>
      </section>

      <Panel
        title="Scene workers"
        icon={<TerminalSquare className="size-4" />}
        testId="worker-rail"
      >
        <div className="flex flex-col gap-3">
          {fleet.data.camera_workers.map((worker) => {
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
                      {worker.processing_mode} - {worker.lifecycle_owner}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <StatusToneBadge tone={statusTone(worker.desired_state)}>
                      {worker.desired_state}
                    </StatusToneBadge>
                    <StatusToneBadge tone={statusTone(worker.runtime_status)}>
                      {worker.runtime_status}
                    </StatusToneBadge>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[#93a7c5]">
                  <p>
                    <span className="font-semibold text-[#d8e2f2]">Source</span>{" "}
                    {formatCameraSource(camera)}
                  </p>
                  <p>
                    <span className="font-semibold text-[#d8e2f2]">
                      Recording
                    </span>{" "}
                    {formatRecordingPolicy(camera)}
                  </p>
                </div>
                <RuntimePassportPanel
                  summary={worker.runtime_passport}
                  compact
                />
                <RuleRuntimePanel summary={worker.rule_runtime} />
                {worker.detail ? (
                  <p className="mt-2 text-sm text-[#93a7c5]">{worker.detail}</p>
                ) : null}
                {worker.dev_run_command ? (
                  <CommandBlock text={worker.dev_run_command} />
                ) : null}
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel
        title={omniLabels.streamDiagnosticsTitle}
        icon={<Copy className="size-4" />}
        testId="stream-diagnostics-rail"
      >
        <div className="flex flex-col gap-3">
          {fleet.data.delivery_diagnostics.map((diagnostic) => (
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
        </div>
      </Panel>
    </div>
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

function CommandBlock({ text }: { text: string }) {
  return (
    <pre className="mt-3 overflow-auto rounded-[0.75rem] bg-black/40 p-3 text-xs text-[#d8e2f2]">
      {text}
    </pre>
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
