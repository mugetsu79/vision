import { useMemo, useState, type ReactNode } from "react";
import {
  Copy,
  RefreshCw,
  Server,
  ShieldAlert,
  TerminalSquare,
} from "lucide-react";

import { OmniSightField } from "@/components/brand/OmniSightField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { omniLabels, omniPlaceExamples } from "@/copy/omnisight";
import {
  type FleetBootstrapResponse,
  type FleetOverview,
  useCreateBootstrapMaterial,
  useFleetOverview,
} from "@/hooks/use-operations";

type FleetSourceCapability = NonNullable<
  FleetOverview["delivery_diagnostics"][number]["source_capability"]
>;

export function SettingsPage() {
  const fleet = useFleetOverview();
  const bootstrap = useCreateBootstrapMaterial();
  const [hostname, setHostname] = useState("");
  const [version, setVersion] = useState("0.1.0");
  const [bootstrapResult, setBootstrapResult] =
    useState<FleetBootstrapResponse | null>(null);
  const firstSiteId = fleet.data?.camera_workers[0]?.site_id;

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
      <section className="rounded-[1rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-sm text-[#9bb0d0]">
        Loading operations...
      </section>
    );
  }

  if (fleet.isError || !fleet.data) {
    return (
      <section className="rounded-[1rem] border border-[#5a2330] bg-[#241118] px-5 py-6 text-sm text-[#ffc2cd]">
        Failed to load fleet operations.
      </section>
    );
  }

  return (
    <div data-testid="operations-workspace" className="space-y-5 p-4 sm:p-6">
      <section className="relative overflow-hidden rounded-[1rem] border border-white/10 bg-[color:var(--vezor-surface-depth)] px-5 py-5">
        <OmniSightField variant="quiet" className="opacity-50" />
        <div className="relative z-10 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase text-[#9db3d3]">
              Operations
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-[#f4f8ff]">
              {omniLabels.operationsTitle}
            </h1>
            <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
              Monitor planned workers, runtime reports, bootstrap material, and
              stream diagnostics for the fleet.
            </p>
          </div>
          <Button type="button" onClick={() => void fleet.refetch()}>
            <RefreshCw className="mr-2 size-4" />
            Refresh
          </Button>
        </div>
      </section>

      <section
        data-testid="edge-fleet-grid"
        className="grid gap-3 rounded-[1rem] border border-white/10 bg-[#07101c] p-4 md:grid-cols-5"
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

      <section className="rounded-[1rem] border border-white/10 bg-[#0f172a] px-5 py-4">
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
      </section>

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
                  <Badge>{node.status}</Badge>
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
          {fleet.data.camera_workers.map((worker) => (
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
                  <Badge>{worker.desired_state}</Badge>
                  <Badge>{worker.runtime_status}</Badge>
                </div>
              </div>
              {worker.detail ? (
                <p className="mt-2 text-sm text-[#93a7c5]">{worker.detail}</p>
              ) : null}
              {worker.dev_run_command ? (
                <CommandBlock text={worker.dev_run_command} />
              ) : null}
            </div>
          ))}
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
                <Badge>{diagnostic.selected_stream_mode}</Badge>
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

function SummaryTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[0.85rem] border border-white/10 bg-[#101827] px-4 py-3">
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
  return (
    <section
      data-testid={testId}
      className="rounded-[1rem] border border-white/10 bg-[#0b1120] p-4"
    >
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#f4f8ff]">
        {icon}
        <h2>{title}</h2>
      </div>
      {children}
    </section>
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

function formatReason(reason: string | null | undefined) {
  return (reason ?? "not reported").replaceAll("_", " ");
}
