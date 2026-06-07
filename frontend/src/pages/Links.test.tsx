import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { Links } from "@/pages/Links";

const linkPageMocks = vi.hoisted(() => ({
  summaries: [] as unknown[],
}));

vi.mock("@/hooks/use-link", () => ({
  useLinkSiteSummaries: () => ({
    data: linkPageMocks.summaries,
    isLoading: false,
    isError: false,
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

function mockLinkHooks({ summaries = [] }: { summaries?: unknown[] } = {}) {
  linkPageMocks.summaries = summaries;
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
});
