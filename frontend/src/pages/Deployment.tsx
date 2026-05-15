import { useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Cpu,
  Download,
  KeyRound,
  Laptop,
  PackageCheck,
  RefreshCw,
  RotateCcw,
  Server,
  ShieldCheck,
  Wrench,
} from "lucide-react";

import {
  StatusToneBadge,
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useCreatePairingSession,
  useDeploymentNodes,
  useDeploymentSupportBundle,
  useRotateNodeCredential,
  type DeploymentNode,
  type DeploymentSupportBundle,
  type NodeCredentialRotateResponse,
  type NodePairingSessionResponse,
} from "@/hooks/use-deployment";
import { useCreateBootstrapMaterial } from "@/hooks/use-operations";
import { useSites, type Site } from "@/hooks/use-sites";

const installerTargets = [
  {
    title: "macOS master",
    platform: "Portable pilot master",
    command: "installer/macos/install-master.sh",
    detail: "Creates the local launchd service and opens first-run setup.",
    icon: Laptop,
  },
  {
    title: "Linux master",
    platform: "Production master",
    command: "installer/linux/install-master.sh",
    detail: "Installs the systemd-owned master appliance on the host.",
    icon: Server,
  },
  {
    title: "Jetson edge",
    platform: "Edge appliance",
    command: "installer/linux/install-edge.sh",
    detail: "Runs Jetson preflight, claims pairing, and starts edge service.",
    icon: Cpu,
  },
] as const;

export function DeploymentPage() {
  const nodes = useDeploymentNodes();
  const sites = useSites();
  const createEdgeNode = useCreateBootstrapMaterial();
  const createPairing = useCreatePairingSession();
  const rotateCredential = useRotateNodeCredential();
  const [edgePairingOpen, setEdgePairingOpen] = useState(false);
  const [edgeSiteId, setEdgeSiteId] = useState("");
  const [edgeHostname, setEdgeHostname] = useState("jetson-portable-1");
  const [edgeVersion, setEdgeVersion] = useState("portable-demo");
  const [pairing, setPairing] = useState<NodePairingSessionResponse | null>(
    null,
  );
  const [rotation, setRotation] = useState<NodeCredentialRotateResponse | null>(
    null,
  );
  const [bundleNodeId, setBundleNodeId] = useState<string | null>(null);
  const supportBundle = useDeploymentSupportBundle(bundleNodeId);
  const availableSites = sites.data ?? [];
  const selectedEdgeSiteId = edgeSiteId || availableSites[0]?.id || "";

  async function handlePairNode(node?: DeploymentNode) {
    const result = await createPairing.mutateAsync({
      node_kind: node?.node_kind ?? "central",
      edge_node_id: node?.edge_node_id ?? undefined,
      hostname: node?.hostname ?? "central-supervisor",
      requested_ttl_seconds: 300,
    });
    setPairing(result);
  }

  async function handleRotateNode(node: DeploymentNode) {
    const confirmed = window.confirm(
      `Rotate credentials for ${node.hostname}? Connected supervisors must pick up the new credential before they can poll or report again.`,
    );
    if (!confirmed) {
      return;
    }
    const result = await rotateCredential.mutateAsync(node.id);
    setRotation(result);
  }

  async function handleCreateEdgePairing() {
    if (!selectedEdgeSiteId) {
      return;
    }
    const hostname = edgeHostname.trim() || "jetson-portable-1";
    const version = edgeVersion.trim() || "portable-demo";
    const edge = await createEdgeNode.mutateAsync({
      site_id: selectedEdgeSiteId,
      hostname,
      version,
    });
    const result = await createPairing.mutateAsync({
      node_kind: "edge",
      edge_node_id: edge.edge_node_id,
      hostname,
      requested_ttl_seconds: 300,
    });
    setPairing(result);
    setEdgePairingOpen(false);
  }

  if (nodes.isLoading) {
    return (
      <WorkspaceSurface className="px-5 py-6 text-sm text-[#9bb0d0]">
        Loading deployment...
      </WorkspaceSurface>
    );
  }

  if (nodes.isError || !nodes.data) {
    return (
      <WorkspaceSurface className="border-[#5a2330] bg-[#241118] px-5 py-6 text-sm text-[#ffc2cd]">
        Failed to load deployment.
      </WorkspaceSurface>
    );
  }

  return (
    <div data-testid="deployment-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Deployment"
        title="Install health and node pairing"
        description="Pair installed supervisors, verify service ownership, and inspect redacted diagnostics without copied terminal secrets."
        actions={
          <>
            <Button type="button" onClick={() => void nodes.refetch()}>
              <RefreshCw className="mr-2 size-4" />
              Refresh
            </Button>
            <Button type="button" onClick={() => void handlePairNode()}>
              <KeyRound className="mr-2 size-4" />
              Pair central
            </Button>
            <Button type="button" onClick={() => setEdgePairingOpen(true)}>
              <Cpu className="mr-2 size-4" />
              Pair Jetson edge
            </Button>
          </>
        }
      />

      {edgePairingOpen ? (
        <EdgePairingPanel
          sites={availableSites}
          selectedSiteId={selectedEdgeSiteId}
          hostname={edgeHostname}
          version={edgeVersion}
          busy={createEdgeNode.isPending || createPairing.isPending}
          onSiteChange={setEdgeSiteId}
          onHostnameChange={setEdgeHostname}
          onVersionChange={setEdgeVersion}
          onCancel={() => setEdgePairingOpen(false)}
          onCreate={() => void handleCreateEdgePairing()}
        />
      ) : null}

      {pairing ? <PairingNotice pairing={pairing} /> : null}
      {rotation ? <CredentialRotationNotice rotation={rotation} /> : null}

      <InstallerTargets />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <WorkspaceSurface className="p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#f4f8ff]">
            <PackageCheck className="size-4" />
            <h2>Deployment nodes</h2>
          </div>
          {nodes.data.length === 0 ? (
            <DeploymentEmptyState onPairCentral={() => void handlePairNode()} />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-y-2 text-sm">
                <thead className="text-left text-[11px] uppercase tracking-[0.14em] text-[#7894bd]">
                  <tr>
                    <th className="px-3 py-2">Node</th>
                    <th className="px-3 py-2">Service</th>
                    <th className="px-3 py-2">Install</th>
                    <th className="px-3 py-2">Credential</th>
                    <th className="px-3 py-2">Heartbeat</th>
                    <th className="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {nodes.data.map((node) => (
                    <tr key={node.id} className="bg-white/[0.025]">
                      <td className="rounded-l-[0.75rem] border-y border-l border-white/10 px-3 py-3">
                        <p className="font-medium text-[#f4f8ff]">
                          {node.hostname}
                        </p>
                        <p className="mt-1 text-xs text-[#93a7c5]">
                          {node.node_kind} - {node.supervisor_id}
                        </p>
                        <p className="mt-1 text-xs text-[#93a7c5]">
                          {node.host_profile ??
                            node.os_name ??
                            "host profile not reported"}
                        </p>
                      </td>
                      <td className="border-y border-white/10 px-3 py-3 text-[#d8e2f2]">
                        {node.service_manager ?? "not reported"}
                        <p className="mt-1 text-xs text-[#93a7c5]">
                          {node.service_status ?? "service unknown"}
                        </p>
                      </td>
                      <td className="border-y border-white/10 px-3 py-3">
                        <StatusToneBadge tone={statusTone(node.install_status)}>
                          {node.install_status}
                        </StatusToneBadge>
                      </td>
                      <td className="border-y border-white/10 px-3 py-3">
                        <StatusToneBadge
                          tone={statusTone(node.credential_status)}
                        >
                          {node.credential_status}
                        </StatusToneBadge>
                      </td>
                      <td className="border-y border-white/10 px-3 py-3 text-[#d8e2f2]">
                        {formatDate(node.last_service_reported_at)}
                      </td>
                      <td className="rounded-r-[0.75rem] border-y border-r border-white/10 px-3 py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            onClick={() => void handlePairNode(node)}
                          >
                            <KeyRound className="mr-2 size-4" />
                            Pair
                          </Button>
                          <Button
                            type="button"
                            disabled={rotateCredential.isPending}
                            onClick={() => void handleRotateNode(node)}
                          >
                            <RotateCcw className="mr-2 size-4" />
                            Rotate credential
                          </Button>
                          <Button
                            type="button"
                            onClick={() => setBundleNodeId(node.id)}
                          >
                            <Wrench className="mr-2 size-4" />
                            Support bundle
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </WorkspaceSurface>

        <SupportBundlePanel
          bundle={supportBundle.data ?? null}
          loading={supportBundle.isLoading || supportBundle.isFetching}
        />
      </section>
    </div>
  );
}

function EdgePairingPanel({
  sites,
  selectedSiteId,
  hostname,
  version,
  busy,
  onSiteChange,
  onHostnameChange,
  onVersionChange,
  onCancel,
  onCreate,
}: {
  sites: Site[];
  selectedSiteId: string;
  hostname: string;
  version: string;
  busy: boolean;
  onSiteChange: (siteId: string) => void;
  onHostnameChange: (hostname: string) => void;
  onVersionChange: (version: string) => void;
  onCancel: () => void;
  onCreate: () => void;
}) {
  return (
    <WorkspaceSurface className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-[#f4f8ff]">
            <Cpu className="size-4 text-[#79d6ff]" />
            <h2>Create Jetson edge pairing</h2>
          </div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#93a7c5]">
            Choose the physical site for this Jetson, then create the one-time
            pairing material used by the edge installer.
          </p>
        </div>
        <Button type="button" onClick={onCancel}>
          Cancel
        </Button>
      </div>

      {sites.length === 0 ? (
        <div className="mt-4 rounded-[0.75rem] border border-dashed border-white/15 bg-white/[0.025] p-4">
          <p className="text-sm font-medium text-[#f4f8ff]">
            Create a Site before pairing the Jetson.
          </p>
          <p className="mt-2 text-sm text-[#93a7c5]">
            Sites are the physical locations that own scenes, cameras, time
            zone, and edge node assignment.
          </p>
          <Link
            to="/sites"
            className="mt-3 inline-flex items-center justify-center rounded-full border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,#161c26,#0d121a)] px-4 py-2.5 text-sm font-medium text-[var(--vz-text-primary)] shadow-[var(--vz-elev-1)] transition hover:border-[color:var(--vz-hair-focus)]"
          >
            Open Sites
          </Link>
        </div>
      ) : (
        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_12rem_auto]">
          <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
            Site
            <select
              className="min-h-11 rounded-[0.75rem] border border-white/10 bg-black/35 px-3 text-sm text-[#f4f8ff] outline-none transition focus:border-[#79d6ff]"
              value={selectedSiteId}
              onChange={(event) => onSiteChange(event.target.value)}
            >
              {sites.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
            Jetson edge name
            <Input
              value={hostname}
              onChange={(event) => onHostnameChange(event.target.value)}
              placeholder="jetson-portable-1"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
            Version
            <Input
              value={version}
              onChange={(event) => onVersionChange(event.target.value)}
              placeholder="portable-demo"
            />
          </label>
          <div className="flex items-end">
            <Button
              type="button"
              disabled={busy || !selectedSiteId || hostname.trim().length === 0}
              onClick={onCreate}
            >
              <KeyRound className="mr-2 size-4" />
              Create edge pairing
            </Button>
          </div>
        </div>
      )}
    </WorkspaceSurface>
  );
}

function DeploymentEmptyState({
  onPairCentral,
}: {
  onPairCentral: () => void;
}) {
  return (
    <div className="rounded-[0.75rem] border border-dashed border-white/15 bg-white/[0.025] p-5">
      <h3 className="text-base font-semibold text-[#f4f8ff]">
        No deployment yet
      </h3>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-[#93a7c5]">
        Pair the master supervisor first, then add Jetson edge supervisors when
        the camera locations are ready.
      </p>
      <Button type="button" className="mt-4" onClick={onPairCentral}>
        <KeyRound className="mr-2 size-4" />
        Pair central
      </Button>
    </div>
  );
}

function InstallerTargets() {
  return (
    <WorkspaceSurface className="p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#f4f8ff]">
        <Download className="size-4" />
        <h2>Installer packages</h2>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        {installerTargets.map(
          ({ title, platform, command, detail, icon: Icon }) => (
            <article
              key={title}
              className="rounded-[0.75rem] border border-white/10 bg-white/[0.025] p-3"
            >
              <div className="flex items-start gap-3">
                <Icon className="mt-0.5 size-4 text-[#79d6ff]" />
                <div>
                  <h3 className="text-sm font-semibold text-[#f4f8ff]">
                    {title}
                  </h3>
                  <p className="mt-1 text-xs text-[#93a7c5]">{platform}</p>
                </div>
              </div>
              <code className="mt-3 block overflow-auto rounded-[0.5rem] bg-black/35 px-2 py-2 text-xs text-[#d8e2f2]">
                {command}
              </code>
              <p className="mt-2 text-xs leading-5 text-[#93a7c5]">{detail}</p>
            </article>
          ),
        )}
      </div>
    </WorkspaceSurface>
  );
}

function CredentialRotationNotice({
  rotation,
}: {
  rotation: NodeCredentialRotateResponse;
}) {
  return (
    <WorkspaceSurface className="border-[rgba(245,196,106,0.28)] bg-[rgba(42,31,10,0.72)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-100">
            <AlertTriangle className="size-4" />
            <h2>Credential material shown once</h2>
          </div>
          <p className="mt-2 text-sm text-amber-100/80">
            Connected supervisors must pick up this rotated credential before
            they can poll lifecycle requests or report service health again.
          </p>
          <p className="mt-1 text-xs text-amber-100/70">
            Version {rotation.credential_version}; revoked{" "}
            {rotation.revoked_credentials} old{" "}
            {rotation.revoked_credentials === 1 ? "credential" : "credentials"}.
          </p>
        </div>
        <code className="max-w-full overflow-auto rounded-[0.6rem] border border-amber-200/30 bg-black/35 px-3 py-2 text-sm font-semibold text-amber-50">
          {rotation.credential_material}
        </code>
      </div>
    </WorkspaceSurface>
  );
}

function PairingNotice({ pairing }: { pairing: NodePairingSessionResponse }) {
  return (
    <WorkspaceSurface className="border-[rgba(245,196,106,0.28)] bg-[rgba(42,31,10,0.72)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-100">
            <ShieldCheck className="size-4" />
            <h2>Pairing material shown once</h2>
          </div>
          <p className="mt-2 text-sm text-amber-100/80">
            Use both values when pairing the supervisor. They expire shortly and
            will not be shown again after the session is claimed.
          </p>
        </div>
        <div className="grid min-w-0 gap-2 sm:min-w-[24rem]">
          <OneTimePairingValue label="Session ID" value={pairing.id} />
          <OneTimePairingValue
            label="Pairing code"
            value={pairing.pairing_code ?? "claimed"}
          />
        </div>
      </div>
    </WorkspaceSurface>
  );
}

function OneTimePairingValue({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0">
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-100/70">
        {label}
      </p>
      <code className="block max-w-full overflow-auto rounded-[0.6rem] border border-amber-200/30 bg-black/35 px-3 py-2 text-sm font-semibold text-amber-50">
        {value}
      </code>
    </div>
  );
}

function SupportBundlePanel({
  bundle,
  loading,
}: {
  bundle: DeploymentSupportBundle | null;
  loading: boolean;
}) {
  return (
    <WorkspaceSurface data-testid="support-bundle-panel" className="p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#f4f8ff]">
        <Wrench className="size-4" />
        <h2>Support bundle</h2>
      </div>
      {loading ? (
        <p className="text-sm text-[#93a7c5]">Loading bundle...</p>
      ) : null}
      {!loading && !bundle ? (
        <p className="text-sm text-[#93a7c5]">
          Select a node to inspect diagnostics.
        </p>
      ) : null}
      {bundle ? (
        <div className="space-y-4 text-sm">
          <section>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
              Reports
            </h3>
            <p className="mt-1 text-[#d8e2f2]">
              {formatCount(
                bundle.service_reports?.length ?? 0,
                "service report",
              )}
            </p>
          </section>
          <SummaryBlock
            title="Lifecycle"
            summary={bundle.lifecycle_summary ?? {}}
          />
          <SummaryBlock
            title="Runtime"
            summary={bundle.runtime_summary ?? {}}
          />
          <SummaryBlock
            title="Hardware"
            summary={bundle.hardware_summary ?? {}}
          />
          <SummaryBlock
            title="Model admission"
            summary={bundle.model_admission_summary ?? {}}
          />
          <SummaryBlock
            title="Config references"
            summary={bundle.config_references ?? {}}
          />
          <section>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
              Log excerpts
            </h3>
            <p className="mt-1 text-[#d8e2f2]">
              {formatCount(
                bundle.selected_log_excerpts?.length ?? 0,
                "excerpt",
              )}
            </p>
          </section>
          <pre className="max-h-52 overflow-auto rounded-[0.75rem] bg-black/35 p-3 text-xs text-[#d8e2f2]">
            {JSON.stringify(bundle.diagnostics, null, 2)}
          </pre>
        </div>
      ) : null}
    </WorkspaceSurface>
  );
}

function SummaryBlock({
  title,
  summary,
}: {
  title: string;
  summary: Record<string, unknown>;
}) {
  return (
    <section>
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
        {title}
      </h3>
      <p className="mt-1 text-[#d8e2f2]">{formatSummary(summary)}</p>
    </section>
  );
}

function formatSummary(summary: Record<string, unknown>) {
  const byStatus = summary.by_status ?? summary.by_state;
  if (byStatus && typeof byStatus === "object") {
    return Object.entries(byStatus)
      .map(([key, value]) => `${key}: ${value}`)
      .join(", ");
  }
  if (typeof summary.host_profile === "string") {
    return summary.host_profile;
  }
  if (Array.isArray(summary.scene_contract_hashes)) {
    return summary.scene_contract_hashes.length > 0
      ? `${summary.scene_contract_hashes.length} scene contract hash`
      : "No config references";
  }
  return "No recent records";
}

function formatCount(count: number, label: string) {
  return `${count} ${label}${count === 1 ? "" : "s"}`;
}

function statusTone(
  status: string,
): "healthy" | "attention" | "danger" | "muted" | "accent" {
  const normalized = status.toLowerCase();
  if (["healthy", "active", "running", "installed"].includes(normalized)) {
    return "healthy";
  }
  if (
    ["degraded", "pairing_pending", "pending", "offline"].includes(normalized)
  ) {
    return "attention";
  }
  if (["revoked", "expired", "missing", "failed"].includes(normalized)) {
    return "danger";
  }
  return "muted";
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "not reported";
  }
  return new Date(value).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
