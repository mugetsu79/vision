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

  test("selected site renders link posture connections budget probes queue and passport", async () => {
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
    expect(screen.getByText(/Primary fiber/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Connections/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Budget and policy/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Probe history/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Transfer queue/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/abcdef12/i)).toBeInTheDocument();
  });

  test("connection form creates a core link connection for the selected site", async () => {
    const user = userEvent.setup();
    const createConnection = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      createConnection,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(
      await screen.findByRole("button", { name: /add connection/i }),
    );
    await user.type(screen.getByLabelText(/connection label/i), "Primary fiber");
    await user.selectOptions(screen.getByLabelText(/transport kind/i), "fiber");
    await user.click(screen.getByRole("button", { name: /save connection/i }));

    expect(createConnection).toHaveBeenCalledWith(
      expect.objectContaining({
        label: "Primary fiber",
        transport_kind: "fiber",
      }),
    );
  });

  test("connection controls edit and delete the selected connection", async () => {
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
    await user.clear(screen.getByLabelText(/connection label/i));
    await user.type(screen.getByLabelText(/connection label/i), "Backup fiber");
    await user.click(screen.getByRole("button", { name: /save connection/i }));
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

  test("invalid policy JSON shows an inline error without saving", async () => {
    const user = userEvent.setup();
    const updatePolicies = vi.fn().mockResolvedValue({});
    mockLinkHooks({
      summaries: [createSummary({ site_id: "site-1" })],
      policies: { policy: { bulk_requires_unmetered: true } },
      updatePolicies,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.clear(await screen.findByLabelText(/policy json/i));
    await user.type(screen.getByLabelText(/policy json/i), "not json");
    await user.click(screen.getByRole("button", { name: /save policy/i }));

    expect(
      screen.getByText(/policy must be valid json/i),
    ).toBeInTheDocument();
    expect(updatePolicies).not.toHaveBeenCalled();
  });

  test("record probe dialog sends probe metrics for the selected site", async () => {
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
        },
      ],
      createProbe,
    });

    renderWithProviders(<Links />, { route: "/links?site=site-1" });

    await user.click(await screen.findByRole("button", { name: /record probe/i }));
    await user.selectOptions(screen.getByLabelText(/probe connection/i), "connection-1");
    await user.clear(screen.getByLabelText(/latency ms/i));
    await user.type(screen.getByLabelText(/latency ms/i), "42");
    await user.clear(screen.getByLabelText(/throughput mbps/i));
    await user.type(screen.getByLabelText(/throughput mbps/i), "180");
    await user.clear(screen.getByLabelText(/packet loss percent/i));
    await user.type(screen.getByLabelText(/packet loss percent/i), "0.1");
    await user.type(screen.getByLabelText(/probe source/i), "packless-lab");
    await user.click(screen.getByRole("button", { name: /save probe/i }));

    expect(createProbe).toHaveBeenCalledWith({
      connection_id: "connection-1",
      latency_ms: 42,
      throughput_mbps: 180,
      packet_loss_percent: 0.1,
      reachable: true,
      source: "packless-lab",
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
