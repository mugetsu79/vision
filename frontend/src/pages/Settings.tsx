import { useMemo, useState, type ReactNode } from "react";
import { Copy, RefreshCw, Server, ShieldAlert, TerminalSquare } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  const [bootstrapResult, setBootstrapResult] = useState<FleetBootstrapResponse | null>(null);
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
    if (!firstSiteId || hostname.trim().length === 0 || version.trim().length === 0) {
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
      <section className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-sm text-[#9bb0d0]">
        Loading operations...
      </section>
    );
  }

  if (fleet.isError || !fleet.data) {
    return (
      <section className="rounded-[1.5rem] border border-[#5a2330] bg-[#241118] px-5 py-6 text-sm text-[#ffc2cd]">
        Failed to load fleet operations.
      </section>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <section className="overflow-hidden rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.95),rgba(8,11,18,0.92))] shadow-[0_24px_72px_-54px_rgba(0,0,0,0.9)]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase text-[#9db3d3]">
                Operations
              </p>
              <h1 className="mt-3 text-3xl font-semibold text-[#f4f8ff]">
                Fleet and operations
              </h1>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                Workers are started by manual dev commands or production supervisors.
                This page shows desired state, runtime reports, bootstrap material, and
                delivery truth.
              </p>
            </div>
            <Button type="button" onClick={() => void fleet.refetch()}>
              <RefreshCw className="mr-2 size-4" />
              Refresh
            </Button>
          </div>
        </div>

        <div className="grid gap-3 px-6 py-5 md:grid-cols-5">
          <SummaryTile label="Desired workers" value={fleet.data.summary.desired_workers} />
          <SummaryTile label="Running workers" value={fleet.data.summary.running_workers} />
          <SummaryTile label="Stale nodes" value={fleet.data.summary.stale_nodes} />
          <SummaryTile label="Offline nodes" value={fleet.data.summary.offline_nodes} />
          <SummaryTile
            label="Native unavailable"
            value={fleet.data.summary.native_unavailable_cameras}
          />
        </div>
      </section>

      <section className="rounded-[1.25rem] border border-white/10 bg-[#0f172a] px-5 py-4">
        <div className="flex items-center gap-3">
          <TerminalSquare className="size-5 text-[#8fd3ff]" />
          <div>
            <h2 className="text-base font-semibold text-[#f4f8ff]">{modeCopy}</h2>
            <p className="mt-1 text-sm text-[#93a7c5]">
              Start and stop are owned by the local terminal in dev, and by a supervisor
              in production. The UI changes desired state and shows diagnostics.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Panel title="Nodes" icon={<Server className="size-4" />}>
          <div className="flex flex-col gap-3">
            {fleet.data.nodes.map((node) => (
              <div key={node.id ?? "central"} className="rounded-[1rem] border border-white/10 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-[#f4f8ff]">{node.hostname}</p>
                    <p className="mt-1 text-xs text-[#93a7c5]">
                      {node.kind} - {node.assigned_camera_ids.length} assigned cameras
                    </p>
                  </div>
                  <Badge>{node.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Bootstrap edge node" icon={<ShieldAlert className="size-4" />}>
          <div className="flex flex-col gap-3">
            <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
              Hostname
              <Input
                value={hostname}
                onChange={(event) => setHostname(event.target.value)}
                placeholder="edge-kit-01"
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

      <Panel title="Camera workers" icon={<TerminalSquare className="size-4" />}>
        <div className="flex flex-col gap-3">
          {fleet.data.camera_workers.map((worker) => (
            <div key={worker.camera_id} className="rounded-[1rem] border border-white/10 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-[#f4f8ff]">{worker.camera_name}</p>
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
              {worker.dev_run_command ? <CommandBlock text={worker.dev_run_command} /> : null}
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Delivery diagnostics" icon={<Copy className="size-4" />}>
        <div className="flex flex-col gap-3">
          {fleet.data.delivery_diagnostics.map((diagnostic) => (
            <div key={diagnostic.camera_id} className="rounded-[1rem] border border-white/10 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-[#f4f8ff]">
                    {diagnostic.camera_name} delivery
                  </p>
                  <p className="mt-1 text-xs text-[#93a7c5]">
                    {formatSource(diagnostic.source_capability)} - {diagnostic.default_profile}
                  </p>
                </div>
                <Badge>{diagnostic.selected_stream_mode}</Badge>
              </div>
              {diagnostic.native_status.available === false ? (
                <p className="mt-2 text-sm text-amber-100">
                  Native unavailable: {formatReason(diagnostic.native_status.reason)}
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
    <div className="rounded-[1rem] border border-white/10 bg-[#101827] px-4 py-3">
      <p className="text-xs text-[#93a7c5]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[#f4f8ff]">{value}</p>
    </div>
  );
}

function Panel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[1.25rem] border border-white/10 bg-[#0b1120] p-4">
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
    return "source unknown";
  }
  return `${source.width} x ${source.height}${source.fps ? ` at ${source.fps} fps` : ""}`;
}

function formatReason(reason: string | null | undefined) {
  return (reason ?? "unknown").replaceAll("_", " ");
}
