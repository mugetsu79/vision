import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { HardwareAdmissionPanel } from "@/components/operations/HardwareAdmissionPanel";
import type { FleetOverview } from "@/hooks/use-operations";

type Worker = FleetOverview["camera_workers"][number];

function worker(overrides: Partial<Worker> = {}): Worker {
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
    latest_hardware_report: {
      id: "00000000-0000-0000-0000-000000000801",
      tenant_id: "tenant-1",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      supervisor_id: "edge-supervisor-1",
      reported_at: "2026-05-13T08:03:00Z",
      host_profile: "macos-x86_64-intel",
      os_name: "darwin",
      machine_arch: "x86_64",
      cpu_model: "Intel Core i7",
      cpu_cores: 8,
      memory_total_mb: 32768,
      accelerators: ["coreml"],
      provider_capabilities: { CoreMLExecutionProvider: true },
      observed_performance: [
        {
          model_id: "00000000-0000-0000-0000-000000000803",
          model_name: "YOLO26n COCO",
          runtime_backend: "CoreMLExecutionProvider",
          input_width: 1280,
          input_height: 720,
          target_fps: 10,
          observed_fps: 10,
          stage_p95_ms: { total: 92 },
          stage_p99_ms: { total: 118 },
          captured_at: "2026-05-13T08:03:00Z",
        },
      ],
      thermal_state: "nominal",
      report_hash: "b".repeat(64),
      created_at: "2026-05-13T08:03:00Z",
    },
    latest_model_admission: {
      id: "00000000-0000-0000-0000-000000000811",
      tenant_id: "tenant-1",
      camera_id: "00000000-0000-0000-0000-000000000101",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      assignment_id: null,
      hardware_report_id: "00000000-0000-0000-0000-000000000801",
      model_id: "00000000-0000-0000-0000-000000000803",
      model_name: "YOLO26n COCO",
      model_capability: "fixed_vocab",
      runtime_artifact_id: null,
      runtime_selection_profile_id: null,
      stream_profile: { width: 1280, height: 720, fps: 10 },
      status: "degraded",
      selected_backend: "CoreMLExecutionProvider",
      recommended_model_id: null,
      recommended_model_name: "YOLO26n COCO",
      recommended_runtime_profile_id: null,
      recommended_backend: "CoreMLExecutionProvider",
      rationale: "CoreML p95 total exceeds the frame budget.",
      constraints: { frame_budget_ms: 100, observed_p95_total_ms: 148 },
      evaluated_at: "2026-05-13T08:04:00Z",
      created_at: "2026-05-13T08:04:00Z",
    },
    supervisor_mode: "polling",
    restart_policy: "always",
    allowed_lifecycle_actions: ["start", "stop", "restart", "drain"],
    last_error: null,
    ...overrides,
  };
}

describe("HardwareAdmissionPanel", () => {
  test("renders hardware capability, performance, and admission recommendation", () => {
    render(<HardwareAdmissionPanel worker={worker()} />);

    const panel = screen.getByTestId("hardware-admission-panel");
    expect(within(panel).getByText(/hardware admission/i)).toBeInTheDocument();
    expect(within(panel).getByText(/degraded/i)).toBeInTheDocument();
    expect(within(panel).getByText(/macos-x86_64-intel/i)).toBeInTheDocument();
    expect(within(panel).getByText(/32768 mb/i)).toBeInTheDocument();
    expect(within(panel).getAllByText(/coreml/i).length).toBeGreaterThan(0);
    expect(within(panel).getAllByText(/YOLO26n COCO/i).length).toBeGreaterThan(
      0,
    );
    expect(within(panel).getByText(/p95 92.0 ms/i)).toBeInTheDocument();
    expect(within(panel).getByText(/p99 118.0 ms/i)).toBeInTheDocument();
    expect(within(panel).getByText(/frame budget/i)).toBeInTheDocument();
  });

  test("labels manual workers as production admission bypass", () => {
    render(
      <HardwareAdmissionPanel
        worker={worker({
          lifecycle_owner: "manual_dev",
          latest_hardware_report: null,
          latest_model_admission: null,
        })}
      />,
    );

    expect(
      screen.getByText(/production admission bypass/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/not reported/i).length).toBeGreaterThan(0);
  });
});
