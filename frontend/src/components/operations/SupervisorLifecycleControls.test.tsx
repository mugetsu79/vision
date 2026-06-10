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
import type { FleetOverview } from "@/hooks/use-operations";

type Worker = FleetOverview["camera_workers"][number];

const edgeNodes = [
  { id: "00000000-0000-0000-0000-000000000201", hostname: "jetson-1" },
  { id: "00000000-0000-0000-0000-000000000202", hostname: "jetson-2" },
];

function supervisedWorker(overrides: Partial<Worker> = {}): Worker {
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
      selected_provider: "TensorrtExecutionProvider",
      media_pipeline_mode: "jetson_gstreamer_native",
      encoder_mode: "hardware",
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

  test("shows runtime report media and provider evidence", () => {
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker()}
        edgeNodes={edgeNodes}
      />,
    );

    expect(screen.getByText("TensorrtExecutionProvider")).toBeInTheDocument();
    expect(screen.getByText("Native Jetson GStreamer")).toBeInTheDocument();
    expect(screen.getByText("Hardware H.264")).toBeInTheDocument();
  });

  test("shows central supervised cameras as awaiting first heartbeat", () => {
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          node_id: null,
          node_hostname: null,
          processing_mode: "central",
          runtime_status: "not_reported",
          lifecycle_owner: "central_supervisor",
          detail:
            "Central supervisor owns this worker process; awaiting first per-camera heartbeat.",
          runtime_report: null,
          allowed_lifecycle_actions: ["start", "stop", "restart", "drain"],
        })}
        edgeNodes={edgeNodes}
      />,
    );

    expect(
      screen.getByText(/awaiting first per-camera heartbeat/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Awaiting first heartbeat")).toBeInTheDocument();
    expect(screen.getByText("not_reported")).toBeInTheDocument();
  });

  test("removes a configured worker assignment without deleting the scene", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker()}
        edgeNodes={edgeNodes}
      />,
    );

    await user.click(screen.getByRole("button", { name: /remove worker/i }));

    expect(confirm).toHaveBeenCalledWith(
      expect.stringContaining("Remove worker assignment for Driveway"),
    );
    expect(assignmentMutateAsync).toHaveBeenCalledWith({
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: null,
      desired_state: "not_desired",
    });
  });

  test("keeps removed workers stopped until an operator assigns them again", async () => {
    const user = userEvent.setup();
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          node_id: null,
          node_hostname: null,
          desired_state: "not_desired",
          runtime_status: "not_reported",
          lifecycle_owner: "none",
          detail:
            "Worker assignment removed. Assign a worker location to enable processing again.",
          allowed_lifecycle_actions: [],
          assignment: {
            ...supervisedWorker().assignment!,
            edge_node_id: null,
            desired_state: "not_desired",
          },
          runtime_report: null,
          latest_lifecycle_request: null,
        })}
        edgeNodes={edgeNodes}
      />,
    );

    expect(screen.getByRole("button", { name: /^start$/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /^restart$/i })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /worker removed/i }),
    ).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /assign worker/i }));

    expect(assignmentMutateAsync).toHaveBeenCalledWith({
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: null,
      desired_state: "manual",
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

    expect(
      screen.getByText(/manual mode requires operator-started worker processes/i),
    ).toBeInTheDocument();
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

    expect(screen.getByText(/supervisor mode is disabled/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^start$/i })).toBeDisabled();
  });

  test("renders backend lifecycle detail exactly and honors allowed actions", () => {
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          supervisor_mode: "disabled",
          allowed_lifecycle_actions: ["restart"],
          detail:
            "Operations profile is disabled until a production supervisor is paired.",
        })}
        edgeNodes={edgeNodes}
      />,
    );

    const panel = screen.getByTestId("supervisor-lifecycle-controls");
    expect(
      within(panel).getByText(
        "Operations profile is disabled until a production supervisor is paired.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^start$/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /^restart$/i })).not.toBeDisabled();
  });

  test("renders push mode and lifecycle dispatch state", () => {
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          supervisor_mode: "push",
          detail: "Edge supervisor owns this worker process via push mode.",
          latest_lifecycle_request: {
            ...supervisedWorker().latest_lifecycle_request!,
            status: "requested",
            action: "restart",
            error: "Timed out waiting for supervisor push acknowledgement.",
            request_payload: {
              source: "operations_ui",
              dispatch_mode: "push",
              dispatch_status: "ack_timeout",
            },
          },
        })}
        edgeNodes={edgeNodes}
      />,
    );

    const panel = screen.getByTestId("supervisor-lifecycle-controls");
    expect(within(panel).getByText("Push mode")).toBeInTheDocument();
    expect(within(panel).getByText(/ack timeout/i)).toBeInTheDocument();
  });

  test("directs missing installed supervisor state to Deployment pairing", () => {
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          node_id: null,
          node_hostname: null,
          lifecycle_owner: "edge_supervisor",
          supervisor_mode: "disabled",
          allowed_lifecycle_actions: [],
          dev_run_command:
            "ARGUS_API_BEARER_TOKEN=raw-token docker compose up worker",
          detail: "No installed supervisor has claimed this camera.",
        })}
        edgeNodes={edgeNodes}
      />,
    );

    const panel = screen.getByTestId("supervisor-lifecycle-controls");
    expect(
      within(panel).getByRole("link", { name: /open deployment/i }),
    ).toHaveAttribute("href", "/deployment");
    expect(within(panel).queryByText(/ARGUS_API_BEARER_TOKEN/i)).not.toBeInTheDocument();
    expect(within(panel).queryByText(/docker compose/i)).not.toBeInTheDocument();
  });

  test("blocks start and restart when model admission is unsupported", async () => {
    const user = userEvent.setup();
    render(
      <SupervisorLifecycleControls
        worker={supervisedWorker({
          latest_model_admission: {
            ...supervisedWorker().latest_model_admission!,
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
            ...supervisedWorker().latest_lifecycle_request!,
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

    await user.selectOptions(
      screen.getByLabelText(/desired worker location/i),
      ["00000000-0000-0000-0000-000000000202"],
    );
    await user.click(screen.getByRole("button", { name: /assign worker/i }));

    expect(assignmentMutateAsync).toHaveBeenCalledWith({
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000202",
      desired_state: "supervised",
    });
  });
});
