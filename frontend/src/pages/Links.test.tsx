import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { Links } from "@/pages/Links";

const linkPageMocks = vi.hoisted(() => ({
  summaries: [] as unknown[],
  status: null as unknown,
  connections: [] as unknown[],
  budget: null as unknown,
  probes: [] as unknown[],
  queue: [] as unknown[],
  policies: {} as unknown,
  createConnection: vi.fn(),
  updateConnection: vi.fn(),
  deleteConnection: vi.fn(),
  updateBudget: vi.fn(),
  updatePolicies: vi.fn(),
  createProbe: vi.fn(),
  deleteProbe: vi.fn(),
  runProbeTarget: vi.fn(),
  measureProbeTargetThroughput: vi.fn(),
  retryQueueItem: vi.fn(),
  pauseQueueItem: vi.fn(),
  resumeQueueItem: vi.fn(),
}));

vi.mock("@/hooks/use-link", () => ({
  useLinkSiteSummaries: () => ({
    data: linkPageMocks.summaries,
    isLoading: false,
    isError: false,
  }),
  useLinkSiteStatus: () => ({
    data: linkPageMocks.status,
    isLoading: false,
    error: null,
  }),
  useLinkConnections: () => ({
    data: linkPageMocks.connections,
    isLoading: false,
    error: null,
  }),
  useLinkSiteBudget: () => ({
    data: linkPageMocks.budget,
    isLoading: false,
    error: null,
  }),
  useLinkPolicies: () => ({
    data: linkPageMocks.policies,
    isLoading: false,
    error: null,
  }),
  useLinkProbes: () => ({
    data: linkPageMocks.probes,
    isLoading: false,
    error: null,
  }),
  useLinkSiteQueue: () => ({
    data: linkPageMocks.queue,
    isLoading: false,
    error: null,
  }),
  useCreateLinkConnection: () => ({
    mutateAsync: linkPageMocks.createConnection,
    isPending: false,
  }),
  useUpdateLinkConnection: () => ({
    mutateAsync: linkPageMocks.updateConnection,
    isPending: false,
  }),
  useDeleteLinkConnection: () => ({
    mutateAsync: linkPageMocks.deleteConnection,
    isPending: false,
  }),
  useUpdateLinkBudget: () => ({
    mutateAsync: linkPageMocks.updateBudget,
    isPending: false,
  }),
  useUpdateLinkPolicies: () => ({
    mutateAsync: linkPageMocks.updatePolicies,
    isPending: false,
  }),
  useCreateLinkProbe: () => ({
    mutateAsync: linkPageMocks.createProbe,
    isPending: false,
  }),
  useDeleteLinkProbe: () => ({
    mutateAsync: linkPageMocks.deleteProbe,
    isPending: false,
  }),
  useRunLinkProbeTarget: () => ({
    mutateAsync: linkPageMocks.runProbeTarget,
    isPending: false,
  }),
  useMeasureLinkProbeTargetThroughput: () => ({
    mutateAsync: linkPageMocks.measureProbeTargetThroughput,
    isPending: false,
  }),
  useRetryLinkQueueItem: () => ({
    mutateAsync: linkPageMocks.retryQueueItem,
    isPending: false,
  }),
  usePauseLinkQueueItem: () => ({
    mutateAsync: linkPageMocks.pauseQueueItem,
    isPending: false,
  }),
  useResumeLinkQueueItem: () => ({
    mutateAsync: linkPageMocks.resumeQueueItem,
    isPending: false,
  }),
}));

function createSummary(overrides: Record<string, unknown> = {}) {
  return {
    site_id: "site-1",
    site_name: "North Gate",
    site_tz: "UTC",
    link_state: "healthy",
    active_connection: null,
    connection_count: 0,
    metered_connection_count: 0,
    latest_probe: null,
    queue_depth: {},
    queued_bytes: 0,
    budget: null,
    last_sync_at: null,
    passport_hash: "hash-1",
    ...overrides,
  };
}

function mockLinkHooks({
  summaries = [],
  status = null,
  connections = [],
  budget = null,
  probes = [],
  queue = [],
  policies = {},
  createConnection = vi.fn().mockResolvedValue({}),
  updateConnection = vi.fn().mockResolvedValue({}),
  deleteConnection = vi.fn().mockResolvedValue({}),
  updateBudget = vi.fn().mockResolvedValue({}),
  updatePolicies = vi.fn().mockResolvedValue({}),
  createProbe = vi.fn().mockResolvedValue({}),
  deleteProbe = vi.fn().mockResolvedValue({}),
  runProbeTarget = vi.fn().mockResolvedValue({}),
  measureProbeTargetThroughput = vi.fn().mockResolvedValue({}),
  retryQueueItem = vi.fn().mockResolvedValue({}),
  pauseQueueItem = vi.fn().mockResolvedValue({}),
  resumeQueueItem = vi.fn().mockResolvedValue({}),
}: {
  summaries?: unknown[];
  status?: unknown;
  connections?: unknown[];
  budget?: unknown;
  probes?: unknown[];
  queue?: unknown[];
  policies?: unknown;
  createConnection?: ReturnType<typeof vi.fn>;
  updateConnection?: ReturnType<typeof vi.fn>;
  deleteConnection?: ReturnType<typeof vi.fn>;
  updateBudget?: ReturnType<typeof vi.fn>;
  updatePolicies?: ReturnType<typeof vi.fn>;
  createProbe?: ReturnType<typeof vi.fn>;
  deleteProbe?: ReturnType<typeof vi.fn>;
  runProbeTarget?: ReturnType<typeof vi.fn>;
  measureProbeTargetThroughput?: ReturnType<typeof vi.fn>;
  retryQueueItem?: ReturnType<typeof vi.fn>;
  pauseQueueItem?: ReturnType<typeof vi.fn>;
  resumeQueueItem?: ReturnType<typeof vi.fn>;
} = {}) {
  linkPageMocks.summaries = summaries;
  linkPageMocks.status = status;
  linkPageMocks.connections = connections;
  linkPageMocks.budget = budget;
  linkPageMocks.probes = probes;
  linkPageMocks.queue = queue;
  linkPageMocks.policies = policies;
  linkPageMocks.createConnection = createConnection;
  linkPageMocks.updateConnection = updateConnection;
  linkPageMocks.deleteConnection = deleteConnection;
  linkPageMocks.updateBudget = updateBudget;
  linkPageMocks.updatePolicies = updatePolicies;
  linkPageMocks.createProbe = createProbe;
  linkPageMocks.deleteProbe = deleteProbe;
  linkPageMocks.runProbeTarget = runProbeTarget;
  linkPageMocks.measureProbeTargetThroughput = measureProbeTargetThroughput;
  linkPageMocks.retryQueueItem = retryQueueItem;
  linkPageMocks.pauseQueueItem = pauseQueueItem;
  linkPageMocks.resumeQueueItem = resumeQueueItem;
}

function renderWithProviders(
  ui: ReactElement,
  { route = "/links" }: { route?: string } = {},
) {
  return render(
    <MemoryRouter
      initialEntries={[route]}
      future={{
        v7_relativeSplatPath: true,
        v7_startTransition: true,
      }}
    >
      {ui}
    </MemoryRouter>,
  );
}

describe("Links", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    linkPageMocks.summaries = [];
    linkPageMocks.status = null;
    linkPageMocks.connections = [];
    linkPageMocks.budget = null;
    linkPageMocks.probes = [];
    linkPageMocks.queue = [];
    linkPageMocks.policies = {};
    linkPageMocks.createConnection = vi.fn().mockResolvedValue({});
    linkPageMocks.updateConnection = vi.fn().mockResolvedValue({});
    linkPageMocks.deleteConnection = vi.fn().mockResolvedValue({});
    linkPageMocks.updateBudget = vi.fn().mockResolvedValue({});
    linkPageMocks.updatePolicies = vi.fn().mockResolvedValue({});
    linkPageMocks.createProbe = vi.fn().mockResolvedValue({});
    linkPageMocks.deleteProbe = vi.fn().mockResolvedValue({});
    linkPageMocks.runProbeTarget = vi.fn().mockResolvedValue({});
    linkPageMocks.measureProbeTargetThroughput = vi.fn().mockResolvedValue({});
    linkPageMocks.retryQueueItem = vi.fn().mockResolvedValue({});
    linkPageMocks.pauseQueueItem = vi.fn().mockResolvedValue({});
    linkPageMocks.resumeQueueItem = vi.fn().mockResolvedValue({});
  });

  test("Link Performance starts without selecting the first site", async () => {
    mockLinkHooks({
      summaries: [
        createSummary({ site_id: "site-1", site_name: "North Gate" }),
        createSummary({ site_id: "site-2", site_name: "South Gate" }),
      ],
    });

    renderWithProviders(<Links />);

    expect(
      await screen.findByRole("heading", { name: /Link Performance/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/choose a site to inspect link performance/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /Current posture/i }),
    ).not.toBeInTheDocument();
  });

  test("Link Performance filters and paginates site summaries", async () => {
    const user = userEvent.setup();
    mockLinkHooks({
      summaries: Array.from({ length: 12 }, (_, index) =>
        createSummary({
          site_id: `site-${index + 1}`,
          site_name: `Remote Site ${index + 1}`,
        }),
      ),
    });

    renderWithProviders(<Links />);

    const selector = await screen.findByTestId("link-site-selector");
    expect(
      within(selector).getAllByRole("button", { name: /select remote site/i }),
    ).toHaveLength(10);
    expect(
      within(selector).queryByText("Remote Site 11"),
    ).not.toBeInTheDocument();

    await user.selectOptions(
      screen.getByLabelText(/link sites per page/i),
      "25",
    );
    expect(
      within(selector).getAllByRole("button", { name: /select remote site/i }),
    ).toHaveLength(12);

    await user.type(screen.getByLabelText(/search link sites/i), "12");
    expect(within(selector).getByText("Remote Site 12")).toBeInTheDocument();
    expect(
      within(selector).queryByText("Remote Site 1"),
    ).not.toBeInTheDocument();
  });

  test("selected Link Performance scope hides the unfiltered site list", async () => {
    const user = userEvent.setup();
    mockLinkHooks({
      summaries: Array.from({ length: 12 }, (_, index) =>
        createSummary({
          site_id: `site-${index + 1}`,
          site_name: `Remote Site ${index + 1}`,
        }),
      ),
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    const selector = await screen.findByTestId("link-site-selector");
    expect(within(selector).getByText("Remote Site 1")).toBeInTheDocument();
    expect(
      within(selector).queryByText("Remote Site 2"),
    ).not.toBeInTheDocument();
    expect(
      within(selector).queryByLabelText(/link sites per page/i),
    ).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/search link sites/i), "12");

    expect(within(selector).getByText("Remote Site 12")).toBeInTheDocument();
  });

  test("selected site renders link posture link paths budget probes queue and passport", async () => {
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1", site_name: "North Gate" })],
      status: {
        link_state: "healthy",
        passport_hash: "abcdef123456",
        active_connection: {
          id: "connection-1",
          label: "Primary fiber",
          transport_kind: "fiber",
          status: "online",
        },
        queue_depth: { safety: 0, evidence: 1, telemetry: 0, bulk: 2 },
        latest_probe: {
          latency_ms: 42,
          throughput_mbps: 180,
          packet_loss_percent: 0.1,
          reachable: true,
          source: "packless-lab",
          recorded_at: "2026-06-07T10:00:00Z",
        },
        budget: { monthly_bytes: 500000000000, bulk_daily_bytes: 25000000000 },
      },
      connections: [
        {
          id: "connection-1",
          label: "Primary fiber",
          transport_kind: "fiber",
          status: "online",
          metered: false,
          provider: "Acme Fiber",
          metadata: {
            link_model: "direct",
            visibility: "full",
            external_reference: "Circuit CH-ZRH-01",
            monitoring_targets: [
              {
                label: "Provider edge",
                address: "203.0.113.10",
                probe_type: "icmp",
                purpose: "provider_edge",
              },
            ],
          },
        },
      ],
      probes: [
        {
          id: "probe-1",
          latency_ms: 42,
          throughput_mbps: 180,
          packet_loss_percent: 0.1,
          reachable: true,
          source: "packless-lab",
          recorded_at: "2026-06-07T10:00:00Z",
        },
      ],
      queue: [
        {
          id: "queue-1",
          priority_lane: "evidence",
          byte_size: 8000000,
          status: "queued",
          source_object_type: "evidence_artifact",
        },
      ],
      policies: { policy: { bulk_requires_unmetered: true } },
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    expect(
      await screen.findByRole("heading", { name: /Current posture/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Primary fiber/i).length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", { name: /Link paths/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Direct/i)).toBeInTheDocument();
    expect(screen.getByText(/Full visibility/i)).toBeInTheDocument();
    expect(screen.getByText(/1 monitoring target/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Budget and policy/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/180 Mbps/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/evidence 1 \/ bulk 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Queued transfers/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Monitoring/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Transfer queue/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/abcdef12/i)).toBeInTheDocument();
  });

  test("link path form saves a provider-managed path with a monitoring target", async () => {
    const user = userEvent.setup();
    const createConnection = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      createConnection,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(
      await screen.findByRole("button", { name: /add link path/i }),
    );
    await user.type(
      screen.getByLabelText(/link path label/i),
      "Managed SD-WAN overlay",
    );
    await user.selectOptions(
      screen.getByLabelText(/link model/i),
      "provider_managed",
    );
    await user.type(screen.getByLabelText(/provider/i), "Acme MSP");
    await user.type(
      screen.getByLabelText(/external reference/i),
      "CH-ZRH-01 edge pair",
    );
    await user.selectOptions(screen.getByLabelText(/visibility/i), "handoff_only");
    await user.click(screen.getByRole("button", { name: /add monitoring target/i }));
    await user.type(screen.getByLabelText(/target label/i), "Vezor ingest");
    await user.type(
      screen.getByLabelText(/target address/i),
      "ingest.example.vezor",
    );
    await user.selectOptions(screen.getByLabelText(/probe type/i), "https");
    await user.clear(screen.getByLabelText(/target port/i));
    await user.type(screen.getByLabelText(/target port/i), "443");
    await user.click(screen.getByRole("button", { name: /save link path/i }));

    const createCall = createConnection.mock.calls[0]?.[0] as
      | {
          label?: string;
          transport_kind?: string;
          provider?: string | null;
          metadata?: {
            external_reference?: string | null;
            link_model?: string;
            monitoring_targets?: Array<{
              address?: string;
              label?: string;
              port?: number | null;
              probe_type?: string;
            }>;
            visibility?: string;
          };
        }
      | undefined;
    expect(createCall?.label).toBe("Managed SD-WAN overlay");
    expect(createCall?.transport_kind).toBe("other");
    expect(createCall?.provider).toBe("Acme MSP");
    expect(createCall?.metadata?.external_reference).toBe(
      "CH-ZRH-01 edge pair",
    );
    expect(createCall?.metadata?.link_model).toBe("provider_managed");
    expect(createCall?.metadata?.visibility).toBe("handoff_only");
    expect(createCall?.metadata?.monitoring_targets?.[0]).toMatchObject({
      address: "ingest.example.vezor",
      label: "Vezor ingest",
      port: 443,
      probe_type: "https",
    });
  });

  test("link path form can save inventory-only paths without targets", async () => {
    const user = userEvent.setup();
    const createConnection = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      createConnection,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(
      await screen.findByRole("button", { name: /add link path/i }),
    );
    await user.type(
      screen.getByLabelText(/link path label/i),
      "Inventory only SD-WAN",
    );
    await user.selectOptions(
      screen.getByLabelText(/link model/i),
      "inventory_only",
    );
    await user.selectOptions(screen.getByLabelText(/visibility/i), "none");
    await user.click(screen.getByRole("button", { name: /save link path/i }));

    const createCall = createConnection.mock.calls[0]?.[0] as
      | {
          label?: string;
          transport_kind?: string;
          metadata?: {
            link_model?: string;
            monitoring_targets?: unknown[];
            visibility?: string;
          };
        }
      | undefined;
    expect(createCall?.label).toBe("Inventory only SD-WAN");
    expect(createCall?.transport_kind).toBe("other");
    expect(createCall?.metadata?.link_model).toBe("inventory_only");
    expect(createCall?.metadata?.monitoring_targets).toEqual([]);
    expect(createCall?.metadata?.visibility).toBe("none");
  });

  test("link path controls edit and delete the selected path", async () => {
    const user = userEvent.setup();
    const updateConnection = vi.fn().mockResolvedValue({});
    const deleteConnection = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      connections: [
        {
          id: "connection-1",
          label: "Primary fiber",
          transport_kind: "fiber",
          status: "online",
          metered: false,
        },
      ],
      updateConnection,
      deleteConnection,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(
      await screen.findByRole("button", { name: /edit primary fiber/i }),
    );
    await user.clear(screen.getByLabelText(/link path label/i));
    await user.type(screen.getByLabelText(/link path label/i), "Backup fiber");
    await user.click(screen.getByRole("button", { name: /save link path/i }));
    await user.click(
      screen.getByRole("button", { name: /delete primary fiber/i }),
    );

    const updateCall = updateConnection.mock.calls[0]?.[0] as
      | { connectionId: string; payload: { label?: string } }
      | undefined;
    expect(updateCall?.connectionId).toBe("connection-1");
    expect(updateCall?.payload.label).toBe("Backup fiber");
    expect(deleteConnection).toHaveBeenCalledWith("connection-1");
  });

  test("budget save updates monthly and bulk byte limits", async () => {
    const user = userEvent.setup();
    const updateBudget = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      budget: { monthly_bytes: 1000, bulk_daily_bytes: 100 },
      updateBudget,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.clear(await screen.findByLabelText(/monthly bytes/i));
    await user.type(screen.getByLabelText(/monthly bytes/i), "5000");
    await user.clear(screen.getByLabelText(/bulk daily bytes/i));
    await user.type(screen.getByLabelText(/bulk daily bytes/i), "250");
    await user.click(screen.getByRole("button", { name: /save budget/i }));

    expect(updateBudget).toHaveBeenCalledWith({
      monthly_bytes: 5000,
      bulk_daily_bytes: 250,
    });
  });

  test("policy controls save generated policy without exposing JSON", async () => {
    const user = userEvent.setup();
    const updatePolicies = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      policies: {
        policy: {
          priority_order: ["safety", "evidence", "telemetry", "bulk"],
          backpressure: {
            degraded_pauses: ["telemetry", "bulk"],
            dark_allows: ["safety"],
          },
        },
      },
      updatePolicies,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    expect(screen.queryByLabelText(/policy json/i)).not.toBeInTheDocument();

    await user.click(
      await screen.findByRole("button", { name: /move evidence down/i }),
    );
    await user.click(
      screen.getByRole("checkbox", { name: /pause evidence when degraded/i }),
    );
    await user.click(screen.getByRole("button", { name: /save policy/i }));

    const policyCall = updatePolicies.mock.calls[0]?.[0] as
      | {
          policy?: {
            backpressure?: { degraded_pauses?: string[] };
            priority_order?: string[];
          };
        }
      | undefined;
    expect(policyCall?.policy?.priority_order).toEqual([
      "safety",
      "telemetry",
      "evidence",
      "bulk",
    ]);
    expect(policyCall?.policy?.backpressure?.degraded_pauses).toEqual([
      "telemetry",
      "bulk",
      "evidence",
    ]);
  });

  test("monitoring panel renders target cards instead of a flat record probe action", async () => {
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      connections: [
        {
          id: "connection-1",
          label: "ISP",
          transport_kind: "ethernet",
          status: "online",
          metadata: {
            monitoring_targets: [
              {
                id: "target-1",
                label: "Vezor ingest",
                address: "ingest.example.vezor",
                probe_type: "https",
                port: 443,
                purpose: "vezor_control",
                monitoring: {
                  enabled: true,
                  source_type: "backend_synthetic",
                  interval_seconds: 300,
                },
              },
            ],
          },
        },
      ],
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    expect(
      await screen.findByRole("heading", { name: /Monitoring/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Vezor ingest/i)).toBeInTheDocument();
    expect(screen.getByText(/ingest.example.vezor/i)).toBeInTheDocument();
    expect(screen.getByText(/Backend synthetic every 5 min/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /record probe/i }),
    ).not.toBeInTheDocument();
  });

  test("backend synthetic samples show throughput as unmeasured", async () => {
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      status: {
        link_state: "healthy",
        passport_hash: "abcdef123456",
        queue_depth: {},
        latest_probe: {
          latency_ms: 73,
          throughput_mbps: 0,
          packet_loss_percent: 0,
          reachable: true,
          source: "backend_synthetic:backend:primary",
          source_type: "backend_synthetic",
          source_label: "backend:primary",
          sample_kind: "automated",
          recorded_at: "2026-06-07T10:00:00Z",
        },
      },
      probes: [
        {
          id: "probe-1",
          latency_ms: 73,
          throughput_mbps: 0,
          packet_loss_percent: 0,
          reachable: true,
          source: "backend_synthetic:backend:primary",
          source_type: "backend_synthetic",
          source_label: "backend:primary",
          sample_kind: "automated",
          target_label: "Wisp",
          target_address: "https://openwisp.mugetsu.tech",
          recorded_at: "2026-06-07T10:00:00Z",
        },
      ],
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    expect(
      await screen.findAllByText(/throughput not measured/i),
    ).toHaveLength(2);
    expect(screen.queryByText(/0 Mbps/i)).not.toBeInTheDocument();
  });

  test("monitoring panel runs a backend synthetic target now", async () => {
    const user = userEvent.setup();
    const runProbeTarget = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      connections: [
        {
          id: "connection-1",
          label: "ISP",
          transport_kind: "ethernet",
          status: "online",
          metadata: {
            monitoring_targets: [
              {
                id: "target-1",
                label: "Vezor ingest",
                address: "ingest.example.vezor",
                probe_type: "https",
                port: 443,
                purpose: "vezor_control",
                monitoring: {
                  enabled: true,
                  source_type: "backend_synthetic",
                  interval_seconds: 300,
                },
              },
            ],
          },
        },
      ],
      runProbeTarget,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(
      await screen.findByRole("button", {
        name: /run check now vezor ingest/i,
      }),
    );

    expect(runProbeTarget).toHaveBeenCalledWith("target-1");
  });

  test("monitoring panel measures throughput only from an operator action", async () => {
    const user = userEvent.setup();
    const measureProbeTargetThroughput = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      connections: [
        {
          id: "connection-1",
          label: "Home",
          transport_kind: "ethernet",
          status: "online",
          metadata: {
            monitoring_targets: [
              {
                id: "target-openwisp",
                label: "Wisp",
                address: "https://openwisp.mugetsu.tech",
                probe_type: "https",
                port: 443,
                purpose: "custom",
                throughput_test_url:
                  "https://openwisp.mugetsu.tech/speed.bin",
                throughput_test_max_bytes: 1048576,
                monitoring: {
                  enabled: true,
                  source_type: "backend_synthetic",
                  interval_seconds: 300,
                },
              },
            ],
          },
        },
      ],
      measureProbeTargetThroughput,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    expect(
      await screen.findByRole("button", {
        name: /measure throughput wisp/i,
      }),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /measure throughput wisp/i }),
    );

    expect(measureProbeTargetThroughput).toHaveBeenCalledWith("target-openwisp");
  });

  test("monitoring panel deletes a sample from history", async () => {
    const user = userEvent.setup();
    const deleteProbe = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      probes: [
        {
          id: "probe-1",
          latency_ms: 42,
          throughput_mbps: 180,
          packet_loss_percent: 0.1,
          reachable: true,
          source: "manual:operator-console",
          source_type: "manual",
          source_label: "operator-console",
          sample_kind: "manual",
          recorded_at: "2026-06-07T10:00:00Z",
        },
      ],
      deleteProbe,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(
      await screen.findByRole("button", { name: /delete sample/i }),
    );

    expect(deleteProbe).toHaveBeenCalledWith("probe-1");
  });

  test("manual sample dialog sends structured probe metrics for the selected target", async () => {
    const user = userEvent.setup();
    const createProbe = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      connections: [
        {
          id: "connection-1",
          label: "Primary fiber",
          transport_kind: "fiber",
          status: "online",
          metadata: {
            monitoring_targets: [
              {
                id: "target-1",
                label: "Vezor ingest",
                address: "ingest.example.vezor",
                probe_type: "https",
                port: 443,
                purpose: "vezor_control",
              },
            ],
          },
        },
      ],
      createProbe,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(
      await screen.findByRole("button", { name: /add manual sample/i }),
    );
    await user.selectOptions(screen.getByLabelText(/sample target/i), "target-1");
    await user.clear(screen.getByLabelText(/latency ms/i));
    await user.type(screen.getByLabelText(/latency ms/i), "42");
    await user.clear(screen.getByLabelText(/throughput mbps/i));
    await user.type(screen.getByLabelText(/throughput mbps/i), "180");
    await user.clear(screen.getByLabelText(/packet loss percent/i));
    await user.type(screen.getByLabelText(/packet loss percent/i), "0.1");
    await user.type(
      screen.getByLabelText(/sample source label/i),
      "operator-console",
    );
    await user.click(screen.getByRole("button", { name: /save sample/i }));

    expect(createProbe).toHaveBeenCalledWith({
      connection_id: "connection-1",
      latency_ms: 42,
      throughput_mbps: 180,
      packet_loss_percent: 0.1,
      reachable: true,
      source: "manual:operator-console",
      source_type: "manual",
      source_label: "operator-console",
      sample_kind: "manual",
      target_id: "target-1",
      target_label: "Vezor ingest",
      target_address: "ingest.example.vezor",
      probe_type: "https",
    });
  });

  test("queue controls retry pause and resume selected items", async () => {
    const user = userEvent.setup();
    const retryQueueItem = vi.fn().mockResolvedValue({});
    const pauseQueueItem = vi.fn().mockResolvedValue({});
    const resumeQueueItem = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      queue: [
        {
          id: "queue-1",
          priority_lane: "evidence",
          status: "queued",
          byte_size: 8000000,
          source_object_type: "evidence_artifact",
        },
        {
          id: "queue-2",
          priority_lane: "bulk",
          status: "paused",
          byte_size: 16000000,
          source_object_type: "bulk_artifact",
        },
      ],
      retryQueueItem,
      pauseQueueItem,
      resumeQueueItem,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(
      await screen.findByRole("button", { name: /retry evidence/i }),
    );
    await user.click(screen.getByRole("button", { name: /pause evidence/i }));
    await user.click(screen.getByRole("button", { name: /resume bulk/i }));

    expect(retryQueueItem).toHaveBeenCalledWith("queue-1");
    expect(pauseQueueItem).toHaveBeenCalledWith("queue-1");
    expect(resumeQueueItem).toHaveBeenCalledWith("queue-2");
  });
});
