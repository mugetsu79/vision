import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { workspaceNavGroups } from "@/components/layout/workspace-nav";
import { DeploymentPage } from "@/pages/Deployment";

const deploymentMocks = vi.hoisted(() => ({
  createPairing: vi.fn(),
  createBootstrap: vi.fn(),
  rotateCredential: vi.fn(),
  revokeCredential: vi.fn(),
  refetchNodes: vi.fn(),
  nodes: [] as unknown[],
  sites: [] as unknown[],
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
    data: deploymentMocks.nodes,
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
  useRotateNodeCredential: () => ({
    mutateAsync: deploymentMocks.rotateCredential,
    isPending: false,
  }),
  useRevokeNodeCredential: () => ({
    mutateAsync: deploymentMocks.revokeCredential,
    isPending: false,
  }),
}));

vi.mock("@/hooks/use-operations", () => ({
  useCreateBootstrapMaterial: () => ({
    mutateAsync: deploymentMocks.createBootstrap,
    isPending: false,
  }),
}));

vi.mock("@/hooks/use-sites", () => ({
  useSites: () => ({
    data: deploymentMocks.sites,
    isLoading: false,
    isError: false,
  }),
}));

describe("DeploymentPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    deploymentMocks.nodes = deploymentNodes;
    deploymentMocks.sites = [
      {
        id: "00000000-0000-0000-0000-000000000301",
        name: "Portable Demo Site",
        description: "Demo floor",
        tz: "Europe/Zurich",
        geo_point: null,
        created_at: "2026-05-13T08:00:00Z",
        updated_at: "2026-05-13T08:00:00Z",
      },
    ];
    deploymentMocks.createPairing.mockReset();
    deploymentMocks.createBootstrap.mockReset();
    deploymentMocks.rotateCredential.mockReset();
    deploymentMocks.revokeCredential.mockReset();
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
    deploymentMocks.rotateCredential.mockResolvedValue({
      node_id: "00000000-0000-0000-0000-000000000102",
      credential_id: "00000000-0000-0000-0000-000000000402",
      credential_material: "vzcred_rotated_once",
      credential_hash:
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      credential_version: 2,
      revoked_credentials: 1,
      credential_status: "active",
      node: deploymentNodes[1],
    });
    deploymentMocks.revokeCredential.mockResolvedValue({
      node_id: "00000000-0000-0000-0000-000000000102",
      revoked_credentials: 1,
      credential_status: "revoked",
    });
    deploymentMocks.createBootstrap.mockResolvedValue({
      edge_node_id: "00000000-0000-0000-0000-000000000501",
      api_key: "edge_api_key_not_rendered",
      nats_nkey_seed: "nats_seed_not_rendered",
      subjects: ["edge.heartbeat.00000000-0000-0000-0000-000000000501"],
      mediamtx_url: "rtsp://media.example:8554",
      mediamtx_username: null,
      mediamtx_password: null,
      overlay_network_hints: {},
      dev_compose_command: "legacy lab command",
      supervisor_environment: {},
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
    expect(within(workspace).getAllByText(/launchd/i).length).toBeGreaterThan(
      0,
    );
    expect(within(workspace).getAllByText(/systemd/i).length).toBeGreaterThan(
      0,
    );
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

  test("shows installer package guidance for master and Jetson targets", () => {
    render(<DeploymentPage />);

    const workspace = screen.getByTestId("deployment-workspace");
    expect(within(workspace).getByText(/macOS master/i)).toBeInTheDocument();
    expect(within(workspace).getByText(/Linux master/i)).toBeInTheDocument();
    expect(within(workspace).getAllByText(/Jetson edge/i).length).toBeGreaterThan(
      0,
    );
    expect(
      within(workspace).getByText(/installer\/macos\/install-master\.sh/i),
    ).toBeInTheDocument();
    expect(
      within(workspace).getByText(/installer\/linux\/install-master\.sh/i),
    ).toBeInTheDocument();
    expect(
      within(workspace).getByText(/installer\/linux\/install-edge\.sh/i),
    ).toBeInTheDocument();
    expect(
      within(workspace).queryByText(/ARGUS_API_BEARER_TOKEN/i),
    ).not.toBeInTheDocument();
    expect(
      within(workspace).queryByText(/docker compose up/i),
    ).not.toBeInTheDocument();
  });

  test("shows a first deployment empty state instead of a load failure", () => {
    deploymentMocks.nodes = [];

    render(<DeploymentPage />);

    const workspace = screen.getByTestId("deployment-workspace");
    expect(
      within(workspace).getByRole("heading", { name: /no deployment yet/i }),
    ).toBeInTheDocument();
    expect(
      within(workspace).getByText(/pair the master supervisor/i),
    ).toBeInTheDocument();
    expect(
      within(workspace).getAllByRole("button", { name: /pair central/i })
        .length,
    ).toBeGreaterThan(0);
    expect(
      within(workspace).queryByText(/failed to load deployment/i),
    ).not.toBeInTheDocument();
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
    expect(
      screen.getByText("00000000-0000-0000-0000-000000000401"),
    ).toBeInTheDocument();
    expect(screen.getByText("pair-once")).toBeInTheDocument();
    expect(screen.queryByText(/bearer/i)).not.toBeInTheDocument();
  });

  test("creates a Jetson edge record and pairing session from Deployment", async () => {
    const user = userEvent.setup();
    deploymentMocks.createPairing.mockResolvedValueOnce({
      id: "00000000-0000-0000-0000-000000000601",
      tenant_id: "00000000-0000-0000-0000-000000000001",
      deployment_node_id: null,
      edge_node_id: "00000000-0000-0000-0000-000000000501",
      node_kind: "edge",
      hostname: "orin1",
      status: "pending",
      expires_at: "2026-05-13T08:37:00Z",
      consumed_at: null,
      claimed_by_supervisor: null,
      created_by_subject: "admin-1",
      pairing_code: "edge-once",
      created_at: "2026-05-13T08:32:00Z",
      updated_at: "2026-05-13T08:32:00Z",
    });
    render(<DeploymentPage />);

    await user.click(screen.getByRole("button", { name: /pair jetson edge/i }));
    await user.clear(screen.getByLabelText(/jetson edge name/i));
    await user.type(screen.getByLabelText(/jetson edge name/i), "orin1");
    await user.click(screen.getByRole("button", { name: /create edge pairing/i }));

    expect(deploymentMocks.createBootstrap).toHaveBeenCalledWith({
      site_id: "00000000-0000-0000-0000-000000000301",
      hostname: "orin1",
      version: "portable-demo",
    });
    expect(deploymentMocks.createPairing).toHaveBeenCalledWith({
      node_kind: "edge",
      edge_node_id: "00000000-0000-0000-0000-000000000501",
      hostname: "orin1",
      requested_ttl_seconds: 300,
    });
    expect(await screen.findByText("edge-once")).toBeInTheDocument();
    expect(screen.queryByText(/edge_api_key_not_rendered/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/nats_seed_not_rendered/i)).not.toBeInTheDocument();
  });

  test("rotates node credentials with a one-time pickup warning", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<DeploymentPage />);

    await user.click(
      screen.getAllByRole("button", { name: /rotate credential/i })[1],
    );

    expect(deploymentMocks.rotateCredential).toHaveBeenCalledWith(
      "00000000-0000-0000-0000-000000000102",
    );
    expect(
      await screen.findByText(/credential material shown once/i),
    ).toBeInTheDocument();
    expect(screen.getByText("vzcred_rotated_once")).toBeInTheDocument();
    expect(
      screen.getByText(/connected supervisors must pick up/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/bearer/i)).not.toBeInTheDocument();
  });

  test("unpairs a node by revoking its credential", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<DeploymentPage />);

    await user.click(screen.getAllByRole("button", { name: /unpair/i })[1]);

    expect(window.confirm).toHaveBeenCalledWith(
      expect.stringContaining("Unpair orin-nano-01?"),
    );
    expect(deploymentMocks.revokeCredential).toHaveBeenCalledWith(
      "00000000-0000-0000-0000-000000000102",
    );
    expect(await screen.findByText(/node unpaired/i)).toBeInTheDocument();
    expect(screen.getByText(/revoked 1 credential/i)).toBeInTheDocument();
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
