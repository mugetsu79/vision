import { useMemo, useState } from "react";
import { Play, RefreshCw, RotateCcw, Square, Unplug } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  type FleetOverview,
  useCreateLifecycleRequest,
  useCreateWorkerAssignment,
} from "@/hooks/use-operations";

type Worker = FleetOverview["camera_workers"][number];
type EdgeNodeOption = {
  id: string;
  hostname: string;
};

const lifecycleButtons = [
  { action: "start", label: "Start", icon: Play },
  { action: "stop", label: "Stop", icon: Square },
  { action: "restart", label: "Restart", icon: RotateCcw },
  { action: "drain", label: "Drain", icon: Unplug },
] as const;

export function SupervisorLifecycleControls({
  worker,
  edgeNodes,
}: {
  worker: Worker;
  edgeNodes: EdgeNodeOption[];
}) {
  const lifecycle = useCreateLifecycleRequest();
  const assignment = useCreateWorkerAssignment();
  const [targetNodeId, setTargetNodeId] = useState(worker.node_id ?? "");
  const allowedActions = new Set(worker.allowed_lifecycle_actions ?? []);
  const assignmentId = worker.assignment?.id ?? null;
  const runtimeReport = worker.runtime_report ?? null;
  const latestRequest = worker.latest_lifecycle_request ?? null;
  const lifecycleDisabledReason = lifecycleReason(worker);
  const selectedDesiredState = targetNodeId ? "supervised" : "manual";

  const targetChanged = targetNodeId !== (worker.node_id ?? "");
  const availableNodes = useMemo(
    () =>
      worker.node_id && !edgeNodes.some((node) => node.id === worker.node_id)
        ? [
            ...edgeNodes,
            {
              id: worker.node_id,
              hostname: worker.node_hostname ?? worker.node_id,
            },
          ]
        : edgeNodes,
    [edgeNodes, worker.node_hostname, worker.node_id],
  );

  async function createRequest(action: (typeof lifecycleButtons)[number]["action"]) {
    await lifecycle.mutateAsync({
      camera_id: worker.camera_id,
      edge_node_id: worker.node_id ?? undefined,
      assignment_id: assignmentId ?? undefined,
      action,
      request_payload: { source: "operations_ui" },
    });
  }

  async function updateAssignment() {
    await assignment.mutateAsync({
      camera_id: worker.camera_id,
      edge_node_id: targetNodeId || null,
      desired_state: selectedDesiredState,
    });
  }

  return (
    <section
      data-testid="supervisor-lifecycle-controls"
      className="mt-3 rounded-[0.85rem] border border-white/8 bg-white/[0.025] p-3"
      aria-label={`Supervisor controls for ${worker.camera_name}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8ea8cf]">
            Supervisor controls
          </h4>
          <p className="mt-1 text-sm text-[#d8e2f2]">
            {lifecycleDisabledReason}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {lifecycleButtons.map(({ action, label, icon: Icon }) => (
            <Button
              key={action}
              type="button"
              onClick={() => void createRequest(action)}
              disabled={
                !allowedActions.has(action) ||
                !admissionAllowsAction(worker, action) ||
                lifecycle.isPending
              }
              variant="secondary"
              className="h-9 px-3 text-xs"
            >
              <Icon className="mr-2 size-3.5" />
              {label}
            </Button>
          ))}
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <label className="space-y-2 text-sm text-[#d8e2f2]">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
            Desired worker location
          </span>
          <Select
            aria-label="Desired worker location"
            value={targetNodeId}
            onChange={(event) => setTargetNodeId(event.target.value)}
          >
            <option value="">Central/manual</option>
            {availableNodes.map((node) => (
              <option key={node.id} value={node.id}>
                {node.hostname}
              </option>
            ))}
          </Select>
        </label>
        <Button
          type="button"
          onClick={() => void updateAssignment()}
          disabled={!targetChanged || assignment.isPending}
          className="self-end"
        >
          <RefreshCw className="mr-2 size-4" />
          Assign worker
        </Button>
      </div>

      <dl className="mt-3 grid gap-2 text-xs md:grid-cols-2">
        <LifecycleFact
          label="Heartbeat"
          value={
            runtimeReport?.heartbeat_at
              ? formatDate(runtimeReport.heartbeat_at)
              : "Not reported"
          }
        />
        <LifecycleFact
          label="Runtime"
          value={runtimeReport?.runtime_state ?? worker.runtime_status}
        />
        <LifecycleFact
          label="Restarts"
          value={`${runtimeReport?.restart_count ?? 0} restarts`}
        />
        <LifecycleFact
          label="Runtime artifact"
          value={shortUuid(runtimeReport?.runtime_artifact_id)}
        />
        <LifecycleFact
          label="Scene contract"
          value={hashPrefix(runtimeReport?.scene_contract_hash)}
        />
        <LifecycleFact
          label="Last request"
          value={
            latestRequest
              ? `${latestRequest.status} ${latestRequest.action}`
              : "No request"
          }
        />
      </dl>

      {worker.last_error ? (
        <p className="mt-3 rounded-md border border-amber-300/20 bg-amber-950/20 px-3 py-2 text-xs text-amber-100">
          {worker.last_error}
        </p>
      ) : null}
    </section>
  );
}

function LifecycleFact({ label, value }: { label: string; value: string }) {
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

function lifecycleReason(worker: Worker): string {
  if (worker.lifecycle_owner === "manual_dev") {
    return "Manual-mode guidance only. Lifecycle requests stay disabled.";
  }
  if (worker.supervisor_mode === "disabled") {
    return "Lifecycle requests disabled by the operations profile.";
  }
  if ((worker.allowed_lifecycle_actions ?? []).length === 0) {
    return worker.detail ?? "Supervisor has not reported healthy runtime state.";
  }
  return worker.detail ?? "Supervisor lifecycle requests are available.";
}

function admissionAllowsAction(
  worker: Worker,
  action: (typeof lifecycleButtons)[number]["action"],
): boolean {
  if (action !== "start" && action !== "restart") {
    return true;
  }
  const status = worker.latest_model_admission?.status;
  return status === "recommended" || status === "supported" || status === "degraded";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function hashPrefix(value: string | null | undefined): string {
  return value ? value.slice(0, 12) : "Not recorded";
}

function shortUuid(value: string | null | undefined): string {
  return value ? value.split("-").at(-1) ?? value : "Not recorded";
}
