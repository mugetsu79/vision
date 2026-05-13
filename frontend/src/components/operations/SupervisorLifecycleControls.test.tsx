import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const lifecycleMutateAsync = vi.hoisted(() => vi.fn());
const assignmentMutateAsync = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/use-operations", () => ({
  useCreateLifecycleRequest: () => ({
    mutateAsync: lifecycleMutateAsync,
    isPending: false,
  }),
  useCreateWorkerAssignment: () => ({
    mutateAsync: assignmentMutateAsync,
    isPending: false,
  }),
}));

import { SupervisorLifecycleControls } from "@/components/operations/SupervisorLifecycleControls";

const edgeNodes = [
  { id: "00000000-0000-0000-0000-000000000201", hostname: "jetson-1" },
  { id: "00000000-0000-0000-0000-000000000202", hostname: "jetson-2" },
];

function supervisedWorker(overrides: Record<string, unknown> = {}) {
  return {
    camera_id: "00000000-0000-0000-0000-000000000101",
    camera_name: "Driveway",
    site_id: "00000000-0000-0000-0000-000000000301",
    node_id: "00000000-0000-0000-0000-000000000201",
    node_hostname: "jetson-1",
    processing_mode: "edge",
    desired_state: "supervised",
    runtime_status: "running",
    lifecycle_owner: "edge_supervisor",
    dev_run_command: null,
    detail: "Edge supervisor owns this worker process.",
    runtime_passport: null,
    rule_runtime: {
      configured_rule_count: 0,
      effective_rule_hash: null,
      latest_rule_event_at: null,
      load_status: "not_configured",
    },
    assignment: {
      id: "00000000-0000-0000-0000-000000000401",
      tenant_id: "tenant-1",
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      desired_state: "supervised",
      active: true,
      supersedes_assignment_id: null,
      assigned_by_subject: "operator-1",
      created_at: "2026-05-13T08:00:00Z",
      updated_at: "2026-05-13T08:00:00Z",
    },
    runtime_report: {
      id: "00000000-0000-0000-0000-000000000501",
      tenant_id: "tenant-1",
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      assignment_id: "00000000-0000-0000-0000-000000000401",
      heartbeat_at: "2026-05-13T08:01:00Z",
      runtime_state: "running",
      restart_count: 3,
      last_error: "previous restart recovered",
      runtime_artifact_id: "00000000-0000-0000-0000-000000000601",
      scene_contract_hash:
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      created_at: "2026-05-13T08:01:00Z",
    },
    latest_lifecycle_request: {
      id: "00000000-0000-0000-0000-000000000701",
      tenant_id: "tenant-1",
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      assignment_id: "00000000-0000-0000-0000-000000000401",
      action: "restart",
      status: "requested",
      requested_by_subject: "operator-1",
      requested_at: "2026-05-13T08:02:00Z",
      acknowledged_at: null,
      claimed_by_supervisor: null,
      claimed_at: null,
      completed_at: null,
      admission_report_id: null,
      error: null,
      request_payload: { reason: "operator_test" },
      created_at: "2026-05-13T08:02:00Z",
      updated_at: "2026-05-13T08:02:00Z",
    },
    latest_model_admission: {
      id: "00000000-0000-0000-0000-000000000801",
      tenant_id: "tenant-1",
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      assignment_id: "00000000-0000-0000-0000-000000000401",
      hardware_report_id: "00000000-0000-0000-0000-000000000802",
      model_id: "00000000-0000-0000-0000-000000000803",
      model_name: "YOLO26n COCO",
      model_capability: "fixed_vocab",
      runtime_artifact_id: null,
      runtime_selection_profile_id: null,
      stream_profile: { width: 1280, height: 720, fps: 10 },
      status: "recommended",
      selected_backend: "CoreMLExecutionProvider",
      recommended_model_id: null,
      recommended_model_name: null,
      recommended_runtime_profile_id: null,
      recommended_backend: "CoreMLExecutionProvider",
      rationale: "CoreML p95 total fits the frame budget.",
      constraints: { frame_budget_ms: 100 },
      evaluated_at: "2026-05-13T08:03:00Z",
      created_at: "2026-05-13T08:03:00Z",
    },
    supervisor_mode: "polling",
    restart_policy: "always",
    allowed_lifecycle_actions: ["start", "stop", "restart", "drain"],
    last_error: "previous restart recovered",
    ...overrides,
  };
}

describe("SupervisorLifecycleControls", () => {
  beforeEach(() => {
    lifecycleMutateAsync.mockReset();
    assignmentMutateAsync.mockReset();
    lifecycleMutateAsync.mockResolvedValue({});
    assignmentMutateAsync.mockResolvedValue({});
  });

  test("creates lifecycle requests for supervisor-owned workers", async () => {
    const user = userEvent.setup();
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker()}
        edgeNodes={edgeNodes}
      />,
    );

    await user.click(screen.getByRole("button", { name: /^start$/i }));
    await user.click(screen.getByRole("button", { name: /^stop$/i }));
    await user.click(screen.getByRole("button", { name: /^restart$/i }));
    await user.click(screen.getByRole("button", { name: /^drain$/i }));

    expect(lifecycleMutateAsync).toHaveBeenCalledTimes(4);
    expect(lifecycleMutateAsync).toHaveBeenNthCalledWith(3, {
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      assignment_id: "00000000-0000-0000-0000-000000000401",
      action: "restart",
      request_payload: { source: "operations_ui" },
    });
  });

  test("disables lifecycle requests in manual or disabled supervisor modes", () => {
    const { rerender } = render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          lifecycle_owner: "manual_dev",
          supervisor_mode: "disabled",
          allowed_lifecycle_actions: [],
          detail: "Manual mode requires operator-started worker processes.",
        })}
        edgeNodes={edgeNodes}
      />,
    );

    expect(screen.getByText(/manual-mode guidance/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^restart$/i })).toBeDisabled();

    rerender(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          supervisor_mode: "disabled",
          allowed_lifecycle_actions: [],
          detail: "Supervisor mode is disabled.",
        })}
        edgeNodes={edgeNodes}
      />,
    );

    expect(screen.getByText(/lifecycle requests disabled/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^start$/i })).toBeDisabled();
  });

  test("blocks start and restart when model admission is unsupported", async () => {
    const user = userEvent.setup();
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          latest_model_admission: {
            ...supervisedWorker().latest_model_admission,
            status: "unsupported",
            rationale: "Open-world model unsupported on CPU-only hardware.",
          },
        })}
        edgeNodes={edgeNodes}
      />,
    );

    expect(screen.getByRole("button", { name: /^start$/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /^restart$/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /^stop$/i })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: /^drain$/i })).not.toBeDisabled();

    await user.click(screen.getByRole("button", { name: /^stop$/i }));
    expect(lifecycleMutateAsync).toHaveBeenCalledTimes(1);
    expect(lifecycleMutateAsync).toHaveBeenCalledWith({
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      assignment_id: "00000000-0000-0000-0000-000000000401",
      action: "stop",
      request_payload: { source: "operations_ui" },
    });
  });

  test("allows first start when model admission has not been evaluated yet", async () => {
    const user = userEvent.setup();
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          runtime_status: "not_reported",
          runtime_report: null,
          latest_model_admission: null,
          latest_lifecycle_request: {
            ...supervisedWorker().latest_lifecycle_request,
            action: "stop",
            status: "completed",
          },
        })}
        edgeNodes={edgeNodes}
      />,
    );

    expect(screen.getByRole("button", { name: /^start$/i })).not.toBeDisabled();

    await user.click(screen.getByRole("button", { name: /^start$/i }));

    expect(lifecycleMutateAsync).toHaveBeenCalledWith({
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      assignment_id: "00000000-0000-0000-0000-000000000401",
      action: "start",
      request_payload: { source: "operations_ui" },
    });
  });

  test("updates assignment and renders runtime report truth", async () => {
    const user = userEvent.setup();
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker()}
        edgeNodes={edgeNodes}
      />,
    );

    const panel = screen.getByTestId("supervisor-lifecycle-controls");
    expect(within(panel).getByText(/heartbeat/i)).toBeInTheDocument();
    expect(within(panel).getByText(/may 13/i)).toBeInTheDocument();
    expect(within(panel).getByText(/3 restarts/i)).toBeInTheDocument();
    expect(
      within(panel).getByText(/previous restart recovered/i),
    ).toBeInTheDocument();
    expect(within(panel).getByText(/000000000601/i)).toBeInTheDocument();
    expect(within(panel).getByText(/aaaaaaaaaaaa/i)).toBeInTheDocument();
    expect(within(panel).getByText(/requested restart/i)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/desired worker location/i), [
      "00000000-0000-0000-0000-000000000202",
    ]);
    await user.click(screen.getByRole("button", { name: /assign worker/i }));

    expect(assignmentMutateAsync).toHaveBeenCalledWith({
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000202",
      desired_state: "supervised",
    });
  });
});
