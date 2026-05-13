import { useState } from "react";
import {
  KeyRound,
  PackageCheck,
  RefreshCw,
  ShieldCheck,
  Wrench,
} from "lucide-react";

import {
  StatusToneBadge,
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  useCreatePairingSession,
  useDeploymentNodes,
  useDeploymentSupportBundle,
  type DeploymentNode,
  type DeploymentSupportBundle,
  type NodePairingSessionResponse,
} from "@/hooks/use-deployment";

export function DeploymentPage() {
  const nodes = useDeploymentNodes();
  const createPairing = useCreatePairingSession();
  const [pairing, setPairing] = useState<NodePairingSessionResponse | null>(
    null,
  );
  const [bundleNodeId, setBundleNodeId] = useState<string | null>(null);
  const supportBundle = useDeploymentSupportBundle(bundleNodeId);

  async function handlePairNode(node?: DeploymentNode) {
    const result = await createPairing.mutateAsync({
      node_kind: node?.node_kind ?? "central",
      edge_node_id: node?.edge_node_id ?? undefined,
      hostname: node?.hostname ?? "central-supervisor",
      requested_ttl_seconds: 300,
    });
    setPairing(result);
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
          </>
        }
      />

      {pairing ? <PairingNotice pairing={pairing} /> : null}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <WorkspaceSurface className="p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#f4f8ff]">
            <PackageCheck className="size-4" />
            <h2>Deployment nodes</h2>
          </div>
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
        </WorkspaceSurface>

        <SupportBundlePanel
          bundle={supportBundle.data ?? null}
          loading={supportBundle.isLoading || supportBundle.isFetching}
        />
      </section>
    </div>
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
            This code expires shortly and will not be shown again after the
            session is claimed.
          </p>
        </div>
        <code className="rounded-[0.6rem] border border-amber-200/30 bg-black/35 px-3 py-2 text-sm font-semibold text-amber-50">
          {pairing.pairing_code ?? "claimed"}
        </code>
      </div>
    </WorkspaceSurface>
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
