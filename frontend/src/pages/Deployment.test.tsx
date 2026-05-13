import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { workspaceNavGroups } from "@/components/layout/workspace-nav";
import { DeploymentPage } from "@/pages/Deployment";

const deploymentMocks = vi.hoisted(() => ({
  createPairing: vi.fn(),
  refetchNodes: vi.fn(),
}));

const deploymentNodes = [
  {
    id: "00000000-0000-0000-0000-000000000101",
    tenant_id: "00000000-0000-0000-0000-000000000001",
    node_kind: "central",
    edge_node_id: null,
    supervisor_id: "central-imac-1",
    hostname: "central-imac",
    install_status: "healthy",
    credential_status: "active",
    service_manager: "launchd",
    service_status: "running",
    version: "0.21.0",
    os_name: "darwin",
    host_profile: "macos-arm64-apple",
    last_service_reported_at: "2026-05-13T08:30:00Z",
    diagnostics: {},
    created_at: "2026-05-13T08:00:00Z",
    updated_at: "2026-05-13T08:30:00Z",
  },
  {
    id: "00000000-0000-0000-0000-000000000102",
    tenant_id: "00000000-0000-0000-0000-000000000001",
    node_kind: "edge",
    edge_node_id: "00000000-0000-0000-0000-000000000201",
    supervisor_id: "edge-orin-1",
    hostname: "orin-nano-01",
    install_status: "degraded",
    credential_status: "active",
    service_manager: "systemd",
    service_status: "restarting",
    version: "0.21.0",
    os_name: "linux",
    host_profile: "linux-aarch64-nvidia-jetson",
    last_service_reported_at: "2026-05-13T08:31:00Z",
    diagnostics: {},
    created_at: "2026-05-13T08:00:00Z",
    updated_at: "2026-05-13T08:31:00Z",
  },
];

const supportBundle = {
  node: deploymentNodes[1],
  service_reports: [
    {
      id: "00000000-0000-0000-0000-000000000301",
      tenant_id: "00000000-0000-0000-0000-000000000001",
      deployment_node_id: "00000000-0000-0000-0000-000000000102",
      edge_node_id: "00000000-0000-0000-0000-000000000201",
      supervisor_id: "edge-orin-1",
      node_kind: "edge",
      hostname: "orin-nano-01",
      service_manager: "systemd",
      service_status: "restarting",
      install_status: "degraded",
      credential_status: "active",
      version: "0.21.0",
      os_name: "linux",
      host_profile: "linux-aarch64-nvidia-jetson",
      heartbeat_at: "2026-05-13T08:31:00Z",
      diagnostics: { authorization: "[redacted]" },
      created_at: "2026-05-13T08:31:00Z",
      node: deploymentNodes[1],
    },
  ],
  lifecycle_summary: { total: 1, by_status: { completed: 1 } },
  runtime_summary: { total: 1, by_state: { running: 1 } },
  hardware_summary: {
    total: 1,
    host_profile: "linux-aarch64-nvidia-jetson",
    accelerators: ["cuda"],
  },
  model_admission_summary: { total: 1, by_status: { recommended: 1 } },
  diagnostics: {
    node: {
      authorization: "[redacted]",
      nested: { credential: "[redacted]", status: "ok" },
    },
    service_reports: [{ bearer: "[redacted]", status: "recovered" }],
  },
  generated_at: "2026-05-13T08:32:00Z",
};

vi.mock("@/hooks/use-deployment", () => ({
  useDeploymentNodes: () => ({
    data: deploymentNodes,
    isLoading: false,
    isError: false,
    refetch: deploymentMocks.refetchNodes,
  }),
  useDeploymentSupportBundle: (nodeId: string | null) => ({
    data: nodeId ? supportBundle : null,
    isLoading: false,
    isFetching: false,
  }),
  useCreatePairingSession: () => ({
    mutateAsync: deploymentMocks.createPairing,
    isPending: false,
  }),
}));

describe("DeploymentPage", () => {
  beforeEach(() => {
    deploymentMocks.createPairing.mockReset();
    deploymentMocks.refetchNodes.mockReset();
    deploymentMocks.createPairing.mockResolvedValue({
      id: "00000000-0000-0000-0000-000000000401",
      tenant_id: "00000000-0000-0000-0000-000000000001",
      deployment_node_id: null,
      edge_node_id: null,
      node_kind: "central",
      hostname: "central-supervisor",
      status: "pending",
      expires_at: "2026-05-13T08:37:00Z",
      consumed_at: null,
      claimed_by_supervisor: null,
      created_by_subject: "admin-1",
      pairing_code: "pair-once",
      created_at: "2026-05-13T08:32:00Z",
      updated_at: "2026-05-13T08:32:00Z",
    });
  });

  test("is available from the Control navigation group", () => {
    const controlItems = workspaceNavGroups.find(
      (group) => group.label === "Control",
    )?.items;

    expect(controlItems).toContainEqual(
      expect.objectContaining({
        label: "Deployment",
        to: "/deployment",
      }),
    );
  });

  test("renders installed nodes with service and credential status chips", () => {
    render(<DeploymentPage />);

    const workspace = screen.getByTestId("deployment-workspace");
    expect(
      within(workspace).getByRole("heading", {
        name: /install health and node pairing/i,
      }),
    ).toBeInTheDocument();
    expect(within(workspace).getByText("central-imac")).toBeInTheDocument();
    expect(within(workspace).getByText("orin-nano-01")).toBeInTheDocument();
    expect(within(workspace).getByText(/launchd/i)).toBeInTheDocument();
    expect(within(workspace).getByText(/systemd/i)).toBeInTheDocument();
    expect(
      within(workspace).getByText(/macos-arm64-apple/i),
    ).toBeInTheDocument();
    expect(
      within(workspace).getByText(/linux-aarch64-nvidia-jetson/i),
    ).toBeInTheDocument();
    expect(within(workspace).getAllByText(/active/i).length).toBeGreaterThan(1);
    expect(within(workspace).getByText(/degraded/i)).toBeInTheDocument();
    expect(
      within(workspace).getAllByText(/13 May 2026/i).length,
    ).toBeGreaterThan(0);
  });

  test("creates one-time central pairing material without a copied token flow", async () => {
    const user = userEvent.setup();
    render(<DeploymentPage />);

    await user.click(screen.getByRole("button", { name: /pair central/i }));

    expect(deploymentMocks.createPairing).toHaveBeenCalledWith({
      node_kind: "central",
      edge_node_id: undefined,
      hostname: "central-supervisor",
      requested_ttl_seconds: 300,
    });
    expect(
      await screen.findByText(/pairing material shown once/i),
    ).toBeInTheDocument();
    expect(screen.getByText("pair-once")).toBeInTheDocument();
    expect(screen.queryByText(/bearer/i)).not.toBeInTheDocument();
  });

  test("shows redacted support bundle summaries for the selected node", async () => {
    const user = userEvent.setup();
    render(<DeploymentPage />);

    await user.click(
      screen.getAllByRole("button", { name: /support bundle/i })[1],
    );

    const panel = screen.getByTestId("support-bundle-panel");
    expect(within(panel).getByText(/1 service report/i)).toBeInTheDocument();
    expect(within(panel).getByText(/completed: 1/i)).toBeInTheDocument();
    expect(within(panel).getByText(/running: 1/i)).toBeInTheDocument();
    expect(within(panel).getByText(/recommended: 1/i)).toBeInTheDocument();
    expect(
      within(panel).getByText(/linux-aarch64-nvidia-jetson/i),
    ).toBeInTheDocument();
    expect(within(panel).getAllByText(/\[redacted\]/i).length).toBeGreaterThan(
      0,
    );
    expect(within(panel).queryByText(/raw-token/i)).not.toBeInTheDocument();
    expect(within(panel).queryByText(/vzcred_/i)).not.toBeInTheDocument();
  });
});
