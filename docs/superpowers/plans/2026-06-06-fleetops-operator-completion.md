# FleetOps Operator Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make FleetOps a fully navigable, fully plumbed operations workspace with vessel creation, core multi-transport link connections, distinct Support and Onboarding workflows, and real backend-backed controls on every current FleetOps page.

**Architecture:** FleetOps UI remains in the existing React workspace shell and uses generated OpenAPI types through TanStack Query hooks. Vessel, voyage, port-call, AIS, NMEA, and carrier terminal concepts remain in `argus.maritime`; link transport and connection state are added to domain-neutral `argus.link` and referenced by maritime through site IDs. Existing core billing, support, fleet, evidence, and site APIs are reused rather than duplicated by the pack.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async, Alembic, PostgreSQL, pytest, httpx ASGI transport, React 19, TypeScript, TanStack Query, Vitest, Testing Library, Playwright, pnpm, uv.

---

## Non-Negotiable Constraints

Preserve all constraints from
`docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md`:

- `CC-1 Packless Core Compatibility`
- `CC-2 Pack Boundary`
- `CC-3 Traffic Boundary`
- `CC-4 Link Is Core`
- `CC-5 Fleet Is Core`
- `CC-6 Billing Positioning`
- `CC-7 Support Tunnel`
- `CC-8 Evidence Integrity`
- `CC-9 Frontend Reuse`
- `CC-10 Full Product Scope`

Stop and surface a conflict if implementation requires any of these:

- adding maritime nouns to a core API, table, service, or contract
- implementing traffic/public-space runtime, demos, routes, UI, or migrations
- creating home-lab pack status or UI
- integrating proprietary carrier SDKs
- integrating payment processors or accounting systems
- bypassing support credential references or supervisor tunnel dispatch

Do not stage unrelated scratch files, `.claude/`, `.codex/`, `.superpowers/`,
`.vite/`, screenshots, or `taste-skill/`. Do not use `git add -A`.

## Atomic Commit Policy

Use focused commits and push `origin codex/sceneops-pack-registry` after these
checkpoints:

1. Navigation and vessel create UI.
2. Core link connections and maritime carrier mapping.
3. FleetOps page plumbing and support/onboarding split.
4. Real-stack validation and installer artifact verification.

Suggested commit messages:

- `feat: expose fleetops section navigation`
- `feat: add fleetops vessel create flow`
- `feat: add core link connections`
- `feat: map fleetops carrier links to core connections`
- `feat: plumb fleetops operations pages`
- `test: validate fleetops operator workflows`

## Current Baseline

Already present:

- FleetOps routes:
  - `/fleetops`
  - `/fleetops/vessels`
  - `/fleetops/vessels/:vesselId`
  - `/fleetops/evidence`
  - `/fleetops/billing`
  - `/fleetops/support`
  - `/fleetops/onboarding`
- Backend vessel create/update/delete:
  - `POST /api/v1/maritime/vessels`
  - `PATCH /api/v1/maritime/vessels/{vessel_id}`
  - `DELETE /api/v1/maritime/vessels/{vessel_id}`
- Core site list/create:
  - `GET /api/v1/sites`
  - `POST /api/v1/sites`
- Core link budget, queue, probes, policies, passport endpoints.
- Core support bundle, session, tunnel, break-glass, and onboarding-check routes.
- Core billing meters, usage, invoice runs, and exports.

Missing:

- FleetOps child links in the primary rail.
- Frontend vessel mutations and create/edit UI.
- Core link connection profiles for satellite, LTE, 5G, Wi-Fi, fiber,
  ethernet, and other.
- Maritime carrier ingest mapping into core link connections.
- Support and onboarding page separation.
- Real controls and mutation hooks for visible FleetOps support, onboarding,
  evidence, billing, and link queue actions.

## File Structure

Modify frontend navigation:

- `frontend/src/components/layout/workspace-nav.ts`: add child nav metadata and
  FleetOps route prefetching.
- `frontend/src/components/layout/AppContextRail.tsx`: render active FleetOps
  child links.
- `frontend/src/components/layout/AppIconRail.tsx`: keep one active FleetOps
  icon for all `/fleetops/*` routes.
- `frontend/src/components/layout/AppShell.test.tsx`: cover child nav behavior.

Modify frontend FleetOps:

- `frontend/src/hooks/use-maritime.ts`: add vessel create/update/delete
  mutations and carrier selection invalidation. Add voyage/port-call mutations
  only for controls that are rendered in this plan.
- `frontend/src/hooks/use-link.ts`: add link connection, probe, queue, policy,
  pause/resume/retry mutations.
- `frontend/src/hooks/use-support.ts`: add bundle/session/tunnel/break-glass
  and onboarding run mutations.
- `frontend/src/hooks/use-billing.ts`: add typed list hooks for core billing
  meters, usage, invoice runs, and exports.
- `frontend/src/components/fleetops/VesselFormDialog.tsx`: new accessible
  vessel create/edit dialog.
- `frontend/src/components/fleetops/LinkConnectionPanel.tsx`: new
  multi-transport connection display and editor.
- `frontend/src/components/fleetops/SupportReadinessPanel.tsx`: new support page
  panel.
- `frontend/src/components/fleetops/OnboardingChecklistPanel.tsx`: new
  onboarding page panel.
- `frontend/src/pages/FleetOps*.tsx`: wire pages to the new hooks and panels.
- `frontend/src/pages/FleetOps*.test.tsx`: update and add page behavior tests.

Modify backend core link:

- `backend/src/argus/link/contracts.py`: add transport, connection, status, and
  response contracts.
- `backend/src/argus/link/tables.py`: add `LinkConnection` table and optional
  `connection_id` on probes.
- `backend/src/argus/link/service.py`: add connection CRUD, selection, passport
  payload, and connection-aware probes.
- `backend/src/argus/link/api.py`: add `/sites/{site_id}/connections` routes.
- `backend/src/argus/migrations/versions/0037_core_link_connections.py`: add
  migration after current highest migration `0036_core_support.py`.
- `backend/tests/link/test_link_service.py`: add packless connection tests.
- `backend/tests/api/test_link_routes.py`: add connection route tests.
- `backend/tests/core/test_packless_empty_registry.py`: confirm core link
  connections work without packs.

Modify maritime carrier mapping:

- `backend/src/argus/maritime/contracts.py`: add optional generic carrier
  transport fields while keeping maritime-owned carrier records.
- `backend/src/argus/maritime/telemetry.py`: parse `transport_kind` and map
  legacy link states.
- `backend/src/argus/maritime/api.py`: after carrier terminal ingest, upsert
  the corresponding core link connection for the vessel site.
- `backend/tests/maritime/test_telemetry.py`: cover satellite, LTE, 5G, Wi-Fi,
  fiber, ethernet, and other mapping.
- `backend/tests/e2e/test_maritime_fleetops_smoke.py`: include multi-link
  FleetOps path.

Regenerate API artifacts:

- `frontend/src/lib/openapi.json`
- `frontend/src/lib/api.generated.ts`

## Gate 1: Navigation And Vessel Creation

### Task 1: FleetOps Rail Navigation

**Files:**

- Modify: `frontend/src/components/layout/workspace-nav.ts`
- Modify: `frontend/src/components/layout/AppContextRail.tsx`
- Modify: `frontend/src/components/layout/AppIconRail.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: Write failing navigation tests**

Add tests that expect FleetOps child links in the expanded section rail and a
single active FleetOps icon for nested routes:

```tsx
test("exposes FleetOps child pages in the expanded section rail", () => {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={["/fleetops/vessels"]}>
        <AppShell>
          <div>FleetOps page</div>
        </AppShell>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  const packsNav = screen.getByRole("navigation", { name: /packs/i });
  expect(within(packsNav).getByRole("link", { name: "FleetOps" })).toBeInTheDocument();
  expect(within(packsNav).getByRole("link", { name: "Vessels" })).toHaveAttribute(
    "href",
    "/fleetops/vessels",
  );
  expect(within(packsNav).getByRole("link", { name: "Evidence" })).toHaveAttribute(
    "href",
    "/fleetops/evidence",
  );
  expect(within(packsNav).getByRole("link", { name: "Billing" })).toHaveAttribute(
    "href",
    "/fleetops/billing",
  );
  expect(within(packsNav).getByRole("link", { name: "Support" })).toHaveAttribute(
    "href",
    "/fleetops/support",
  );
  expect(within(packsNav).getByRole("link", { name: "Onboarding" })).toHaveAttribute(
    "href",
    "/fleetops/onboarding",
  );
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/components/layout/AppShell.test.tsx
```

Expected: the new test fails because only the parent FleetOps link exists.

- [ ] **Step 2: Add child nav metadata**

Update `WorkspaceNavItem` in `workspace-nav.ts`:

```ts
export type WorkspaceNavChildItem = {
  label: string;
  to: string;
};

export type WorkspaceNavItem = {
  label: string;
  to: string;
  icon: LucideIcon;
  children?: readonly WorkspaceNavChildItem[];
};
```

Add:

```ts
const fleetOpsChildren = [
  { label: "Vessels", to: "/fleetops/vessels" },
  { label: "Evidence", to: "/fleetops/evidence" },
  { label: "Billing", to: "/fleetops/billing" },
  { label: "Support", to: "/fleetops/support" },
  { label: "Onboarding", to: "/fleetops/onboarding" },
] as const;
```

Attach `children: fleetOpsChildren` to the FleetOps item.

- [ ] **Step 3: Render active child links**

In `AppContextRail.tsx`, render `item.children` under the parent link when the
current route starts with the parent route:

```tsx
const isFleetOpsSection = location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
```

Render child `NavLink`s with smaller text, visible active state, and the same
prefetch calls used by parent links. Use native `NavLink` and real `href`
values; do not use `div` click handlers.

- [ ] **Step 4: Warm FleetOps child routes**

Extend `prefetchWorkspaceRoute` so each FleetOps child imports its page module:

```ts
if (route === "/fleetops/vessels") {
  void import("@/pages/FleetOpsVessels");
}
```

Repeat for evidence, billing, support, and onboarding.

- [ ] **Step 5: Verify and commit**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/components/layout/AppShell.test.tsx
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add frontend/src/components/layout/workspace-nav.ts frontend/src/components/layout/AppContextRail.tsx frontend/src/components/layout/AppIconRail.tsx frontend/src/components/layout/AppShell.test.tsx
git commit -m "feat: expose fleetops section navigation"
```

### Task 2: Vessel Create And Edit Flow

**Files:**

- Modify: `frontend/src/hooks/use-maritime.ts`
- Create: `frontend/src/components/fleetops/VesselFormDialog.tsx`
- Modify: `frontend/src/components/fleetops/VesselSummaryTable.tsx`
- Modify: `frontend/src/pages/FleetOpsVessels.tsx`
- Modify: `frontend/src/pages/FleetOpsVesselDetail.tsx`
- Test: `frontend/src/hooks/use-maritime.test.ts`
- Test: `frontend/src/pages/FleetOpsVessels.test.tsx`
- Test: `frontend/src/pages/FleetOpsVesselDetail.test.tsx`

- [ ] **Step 1: Write failing hook tests**

Add a hook test that verifies the create mutation calls the existing typed API
route and invalidates vessel/site queries:

```ts
test("useCreateMaritimeVessel posts create_site payload and refreshes vessel data", async () => {
  const wrapper = createHookWrapper();
  const { result } = renderHook(() => useCreateMaritimeVessel(), { wrapper });

  await act(async () => {
    await result.current.mutateAsync({
      name: "MV Resolute",
      create_site: {
        name: "MV Resolute",
        description: "FleetOps vessel site for MV Resolute",
        tz: "UTC",
      },
      imo_number: "9876543",
      metadata: { home_port: "Rotterdam" },
    });
  });

  expect(apiClient.POST).toHaveBeenCalledWith("/api/v1/maritime/vessels", {
    body: expect.objectContaining({
      name: "MV Resolute",
      create_site: expect.objectContaining({ tz: "UTC" }),
    }),
  });
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/hooks/use-maritime.test.ts
```

Expected: FAIL because the mutation does not exist.

- [ ] **Step 2: Add maritime vessel mutations**

Add these exports to `use-maritime.ts`:

```ts
export type MaritimeVesselCreateInput =
  components["schemas"]["VesselCreate"];
export type MaritimeVesselUpdateInput =
  components["schemas"]["VesselUpdate"];

export function useCreateMaritimeVessel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: MaritimeVesselCreateInput) => {
      const { data, error } = await apiClient.POST("/api/v1/maritime/vessels", {
        body: payload,
      });
      if (error) {
        throw toApiError(error, "Failed to create vessel.");
      }
      return data ?? null;
    },
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ["maritime", "vessels"] });
      await queryClient.invalidateQueries({ queryKey: ["sites"] });
      await queryClient.invalidateQueries({ queryKey: ["fleet"] });
      const vesselId = typeof created?.id === "string" ? created.id : null;
      if (vesselId) {
        await queryClient.invalidateQueries({
          queryKey: ["maritime", "vessels", vesselId],
        });
      }
    },
  });
}

export function useUpdateMaritimeVessel(vesselId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: MaritimeVesselUpdateInput) => {
      const { data, error } = await apiClient.PATCH(
        "/api/v1/maritime/vessels/{vessel_id}",
        { params: { path: { vessel_id: vesselId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to update vessel.");
      }
      return data ?? null;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["maritime", "vessels"] });
      await queryClient.invalidateQueries({
        queryKey: ["maritime", "vessels", vesselId],
      });
    },
  });
}

export function useDeactivateMaritimeVessel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (vesselId: string) => {
      const { error } = await apiClient.DELETE(
        "/api/v1/maritime/vessels/{vessel_id}",
        { params: { path: { vessel_id: vesselId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to deactivate vessel.");
      }
      return vesselId;
    },
    onSuccess: async (vesselId) => {
      await queryClient.invalidateQueries({ queryKey: ["maritime", "vessels"] });
      await queryClient.invalidateQueries({
        queryKey: ["maritime", "vessels", vesselId],
      });
      await queryClient.invalidateQueries({ queryKey: ["fleet"] });
    },
  });
}
```

Each success handler must invalidate:

- `["maritime", "vessels"]`
- `["sites"]`
- `["fleet"]`
- the relevant vessel detail key when a vessel ID is known

- [ ] **Step 3: Write failing page tests**

Add tests to `FleetOpsVessels.test.tsx`:

```tsx
test("empty vessels state opens a labelled add vessel dialog", async () => {
  const user = userEvent.setup();
  renderWithProviders(<FleetOpsVessels />);

  await user.click(screen.getByRole("button", { name: /add vessel/i }));

  expect(screen.getByRole("dialog", { name: /add vessel/i })).toBeInTheDocument();
  expect(screen.getByLabelText(/vessel name/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/imo number/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /create vessel/i })).toBeInTheDocument();
});
```

Add a submit test with `create_site` as the default path.

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsVessels.test.tsx
```

Expected: FAIL because no add button or dialog exists.

- [ ] **Step 4: Implement `VesselFormDialog`**

Use `frontend/src/components/ui/dialog.tsx` and controlled inputs. Required
inputs must have visible labels. Default state:

```ts
const defaultForm = {
  name: "",
  siteMode: "create",
  siteId: "",
  siteName: "",
  siteTimezone: "UTC",
  imoNumber: "",
  mmsi: "",
  callSign: "",
  flagState: "",
  vesselType: "",
  ownerLabel: "",
  managerLabel: "",
  chartererLabel: "",
  homePort: "",
  notes: "",
};
```

Submit payload rules:

- if `siteMode === "create"`, send `create_site`
- if `siteMode === "existing"`, send `site_id`
- never send both
- omit empty optional strings
- put `home_port` and `notes` under `metadata`

- [ ] **Step 5: Wire Vessels page actions**

Add an Add Vessel button to the page band and the empty state. On successful
create, navigate to `/fleetops/vessels/${created.id}`.

- [ ] **Step 6: Add edit/deactivate controls on detail page**

Expose Edit Vessel and Deactivate Vessel actions when a vessel is loaded. Edit
uses `PATCH`; deactivate uses `DELETE` and then navigates back to
`/fleetops/vessels`.

- [ ] **Step 7: Verify and commit**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/hooks/use-maritime.test.ts src/pages/FleetOpsVessels.test.tsx src/pages/FleetOpsVesselDetail.test.tsx
corepack pnpm build
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add frontend/src/hooks/use-maritime.ts frontend/src/hooks/use-maritime.test.ts frontend/src/components/fleetops/VesselFormDialog.tsx frontend/src/components/fleetops/VesselSummaryTable.tsx frontend/src/pages/FleetOpsVessels.tsx frontend/src/pages/FleetOpsVessels.test.tsx frontend/src/pages/FleetOpsVesselDetail.tsx frontend/src/pages/FleetOpsVesselDetail.test.tsx
git commit -m "feat: add fleetops vessel create flow"
git push origin codex/sceneops-pack-registry
```

### Task 2A: Vessel List Search Filters And Pagination

**Files:**

- Modify: `frontend/src/pages/FleetOpsVessels.tsx`
- Modify: `frontend/src/components/fleetops/VesselSummaryTable.tsx`
- Test: `frontend/src/pages/FleetOpsVessels.test.tsx`

- [ ] **Step 1: Write failing list-control tests**

Extend `frontend/src/pages/FleetOpsVessels.test.tsx` with this helper near the
mock setup:

```tsx
function makeVessel(
  index: number,
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  const suffix = String(index).padStart(2, "0");
  return {
    id: `vessel-${suffix}`,
    name: `MV ${suffix}`,
    site_id: `site-${suffix}`,
    site: { name: `FleetOps Site ${suffix}` },
    imo_number: `imo-${suffix}`,
    mmsi: `mmsi-${suffix}`,
    call_sign: `CALL${suffix}`,
    active: true,
    metadata: {
      evidence_queue: "No pending exports",
      link_state:
        index % 3 === 0
          ? "dark"
          : index % 2 === 0
            ? "satellite_degraded"
            : "port_wifi",
    },
    ...overrides,
  };
}
```

Add the search and filter test:

```tsx
test("vessel list filters by search, link state, and status", async () => {
  vesselPageMocks.vessels = [
    makeVessel(1, {
      name: "MV Resolute",
      active: true,
      metadata: { link_state: "port_wifi", evidence_queue: "Ready" },
    }),
    makeVessel(2, {
      name: "MV Horizon",
      active: false,
      metadata: { link_state: "dark", evidence_queue: "Queued" },
    }),
    makeVessel(3, {
      name: "MV Endurance",
      active: true,
      metadata: { link_state: "satellite_degraded", evidence_queue: "Queued" },
    }),
  ];
  const user = userEvent.setup();
  renderWithProviders(<FleetOpsVessels />);

  await user.type(
    screen.getByRole("searchbox", { name: /search vessels/i }),
    "horizon",
  );

  expect(screen.getByRole("link", { name: /mv horizon/i })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /mv resolute/i })).not.toBeInTheDocument();

  await user.selectOptions(
    screen.getByRole("combobox", { name: /link state/i }),
    "dark",
  );

  expect(screen.getByRole("link", { name: /mv horizon/i })).toBeInTheDocument();

  await user.selectOptions(
    screen.getByRole("combobox", { name: /^status$/i }),
    "active",
  );

  expect(screen.getByText(/no vessels match these filters/i)).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /clear filters/i }));

  expect(screen.getByRole("link", { name: /mv resolute/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /mv horizon/i })).toBeInTheDocument();
});
```

Add the pagination test:

```tsx
test("vessel list paginates 10 rows by default and supports 25 or 50 rows", async () => {
  vesselPageMocks.vessels = Array.from({ length: 12 }, (_, index) =>
    makeVessel(index + 1),
  );
  const user = userEvent.setup();
  renderWithProviders(<FleetOpsVessels />);

  expect(screen.getByRole("link", { name: /mv 01/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /mv 10/i })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /mv 11/i })).not.toBeInTheDocument();
  expect(screen.getByText(/1-10 of 12 vessels/i)).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /next page/i }));

  expect(screen.queryByRole("link", { name: /mv 01/i })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /mv 11/i })).toBeInTheDocument();
  expect(screen.getByText(/11-12 of 12 vessels/i)).toBeInTheDocument();

  await user.selectOptions(
    screen.getByRole("combobox", { name: /rows per page/i }),
    "25",
  );

  expect(screen.getByRole("link", { name: /mv 01/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /mv 12/i })).toBeInTheDocument();
  expect(screen.getByText(/1-12 of 12 vessels/i)).toBeInTheDocument();
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsVessels.test.tsx
```

Expected: FAIL because the Vessels page has no search box, link-state filter,
status filter, page-size selector, or pagination controls.

- [ ] **Step 2: Add URL-backed list state to `FleetOpsVessels.tsx`**

Change the imports at the top of `frontend/src/pages/FleetOpsVessels.tsx`:

```tsx
import { useDeferredValue, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
```

Add these constants and helpers above `FleetOpsVessels`:

```tsx
const PAGE_SIZE_OPTIONS = [10, 25, 50] as const;
const DEFAULT_PAGE_SIZE = 10;
type PageSizeOption = (typeof PAGE_SIZE_OPTIONS)[number];
type VesselStatusFilter = "all" | "active" | "inactive";

function normalize(value: unknown): string {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}

function vesselLinkState(vessel: FleetOpsVessel): string {
  const metadata = asRecord(vessel.metadata);
  const value = metadata.link_state;
  return typeof value === "string" && value.trim().length > 0
    ? value
    : "unknown";
}

function vesselStatus(vessel: FleetOpsVessel): Exclude<VesselStatusFilter, "all"> {
  return vessel.active === false ? "inactive" : "active";
}

function vesselSearchText(vessel: FleetOpsVessel): string {
  const metadata = asRecord(vessel.metadata);
  const site = asRecord(vessel.site);
  return [
    vessel.name,
    vessel.id,
    vessel.site_id,
    site.name,
    vessel.imo_number,
    vessel.mmsi,
    vessel.call_sign,
    metadata.home_port,
    metadata.link_state,
    vesselStatus(vessel),
  ]
    .map((value) => (typeof value === "string" ? value : ""))
    .join(" ")
    .toLowerCase();
}

function parsePageSize(value: string | null): PageSizeOption {
  const parsed = Number(value);
  return PAGE_SIZE_OPTIONS.includes(parsed as PageSizeOption)
    ? (parsed as PageSizeOption)
    : DEFAULT_PAGE_SIZE;
}

function parsePage(value: string | null): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}
```

Also add `asRecord` to the existing type import:

```tsx
import { asRecord, type FleetOpsVessel } from "@/components/fleetops/types";
```

- [ ] **Step 3: Derive filtered and paged vessels in `FleetOpsVessels.tsx`**

Inside `FleetOpsVessels`, after `const vesselRows = ...`, add:

```tsx
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get("q") ?? "";
  const deferredSearchTerm = useDeferredValue(searchTerm);
  const linkStateFilter = searchParams.get("link") ?? "all";
  const rawStatusFilter = searchParams.get("status");
  const statusFilter: VesselStatusFilter =
    rawStatusFilter === "active" || rawStatusFilter === "inactive"
      ? rawStatusFilter
      : "all";
  const pageSize = parsePageSize(searchParams.get("pageSize"));
  const requestedPage = parsePage(searchParams.get("page"));

  const linkStateOptions = useMemo(
    () =>
      Array.from(new Set(vesselRows.map(vesselLinkState))).sort((left, right) =>
        left.localeCompare(right),
      ),
    [vesselRows],
  );

  const filteredVessels = useMemo(() => {
    const normalizedSearch = normalize(deferredSearchTerm);
    return vesselRows.filter((vessel) => {
      const matchesSearch =
        normalizedSearch.length === 0 ||
        vesselSearchText(vessel).includes(normalizedSearch);
      const matchesLinkState =
        linkStateFilter === "all" || vesselLinkState(vessel) === linkStateFilter;
      const matchesStatus =
        statusFilter === "all" || vesselStatus(vessel) === statusFilter;
      return matchesSearch && matchesLinkState && matchesStatus;
    });
  }, [deferredSearchTerm, linkStateFilter, statusFilter, vesselRows]);

  const totalPages = Math.max(1, Math.ceil(filteredVessels.length / pageSize));
  const currentPage = Math.min(requestedPage, totalPages);
  const pageStart = (currentPage - 1) * pageSize;
  const pagedVessels = filteredVessels.slice(pageStart, pageStart + pageSize);
  const hasActiveListFilters =
    searchTerm.trim().length > 0 ||
    linkStateFilter !== "all" ||
    statusFilter !== "all";
```

Add this query updater below `handleCreateVessel`:

```tsx
  function updateListQuery(updates: Record<string, string | number | null>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === "" || value === "all") {
        next.delete(key);
      } else {
        next.set(key, String(value));
      }
    }
    setSearchParams(next, { replace: true });
  }
```

Update the `VesselSummaryTable` call:

```tsx
      <VesselSummaryTable
        vessels={pagedVessels}
        totalVessels={vesselRows.length}
        totalMatches={filteredVessels.length}
        page={currentPage}
        pageSize={pageSize}
        pageStart={pageStart}
        totalPages={totalPages}
        searchTerm={searchTerm}
        linkStateFilter={linkStateFilter}
        statusFilter={statusFilter}
        linkStateOptions={linkStateOptions}
        hasActiveFilters={hasActiveListFilters}
        onSearchTermChange={(value) =>
          updateListQuery({ q: value, page: 1 })
        }
        onLinkStateFilterChange={(value) =>
          updateListQuery({ link: value, page: 1 })
        }
        onStatusFilterChange={(value) =>
          updateListQuery({ status: value, page: 1 })
        }
        onPageSizeChange={(value) =>
          updateListQuery({ pageSize: value, page: 1 })
        }
        onPageChange={(value) => updateListQuery({ page: value })}
        onClearFilters={() =>
          updateListQuery({ q: null, link: null, status: null, page: 1 })
        }
        onAddVessel={() => setDialogOpen(true)}
      />
```

- [ ] **Step 4: Render the Vessels list control surface**

Change `frontend/src/components/fleetops/VesselSummaryTable.tsx` imports:

```tsx
import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";
import { Link } from "react-router-dom";
```

Add UI imports:

```tsx
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
```

Replace `VesselSummaryTableProps` with:

```tsx
type VesselSummaryTableProps = {
  vessels: FleetOpsVessel[];
  totalVessels: number;
  totalMatches: number;
  page: number;
  pageSize: number;
  pageStart: number;
  totalPages: number;
  searchTerm: string;
  linkStateFilter: string;
  statusFilter: "all" | "active" | "inactive";
  linkStateOptions: string[];
  hasActiveFilters: boolean;
  onSearchTermChange: (value: string) => void;
  onLinkStateFilterChange: (value: string) => void;
  onStatusFilterChange: (value: "all" | "active" | "inactive") => void;
  onPageSizeChange: (value: number) => void;
  onPageChange: (value: number) => void;
  onClearFilters: () => void;
  onAddVessel?: () => void;
};
```

Change the component signature to destructure all props. Keep the existing true
empty state when `totalVessels === 0`.

Before the table markup, render this control surface:

```tsx
      <div className="border-b border-[color:var(--vz-hair)] px-4 py-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="grid flex-1 gap-3 md:grid-cols-[minmax(18rem,1fr)_12rem_10rem_10rem]">
            <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
              Search vessels
              <span className="relative mt-2 block">
                <Search
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[var(--vz-text-muted)]"
                  aria-hidden="true"
                />
                <Input
                  type="search"
                  value={searchTerm}
                  onChange={(event) => onSearchTermChange(event.target.value)}
                  className="pl-10"
                  placeholder="Name, IMO, MMSI, call sign, site, or state"
                />
              </span>
            </label>
            <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
              Link state
              <Select
                className="mt-2"
                value={linkStateFilter}
                onChange={(event) => onLinkStateFilterChange(event.target.value)}
              >
                <option value="all">All link states</option>
                {linkStateOptions.map((option) => (
                  <option key={option} value={option}>
                    {formatLinkState(option)}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
              Status
              <Select
                className="mt-2"
                value={statusFilter}
                onChange={(event) =>
                  onStatusFilterChange(event.target.value as "all" | "active" | "inactive")
                }
              >
                <option value="all">All statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </Select>
            </label>
            <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
              Rows per page
              <Select
                className="mt-2"
                value={String(pageSize)}
                onChange={(event) => onPageSizeChange(Number(event.target.value))}
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
              </Select>
            </label>
          </div>
          {hasActiveFilters ? (
            <Button variant="ghost" onClick={onClearFilters}>
              <X className="mr-2 size-4" aria-hidden="true" />
              Clear filters
            </Button>
          ) : null}
        </div>
        <p className="mt-3 text-sm text-[var(--vz-text-secondary)]" aria-live="polite">
          {totalMatches === 0
            ? `0 of ${totalVessels} vessels shown`
            : `${pageStart + 1}-${pageStart + vessels.length} of ${totalMatches} vessels shown`}
        </p>
      </div>
```

When `totalVessels > 0 && vessels.length === 0`, render this filtered empty
state after the control surface:

```tsx
      <div className="px-4 py-12 text-center">
        <p className="font-[family-name:var(--vz-font-display)] text-lg font-semibold text-[var(--vz-text-primary)]">
          No vessels match these filters.
        </p>
        <p className="mx-auto mt-2 max-w-md text-sm text-[var(--vz-text-secondary)]">
          Clear filters or search for another vessel, site, IMO, MMSI, call sign,
          link state, or status.
        </p>
      </div>
```

After the table, render pagination controls:

```tsx
      <div className="flex flex-col gap-3 border-t border-[color:var(--vz-hair)] px-4 py-3 text-sm text-[var(--vz-text-secondary)] sm:flex-row sm:items-center sm:justify-between">
        <span>
          Page {page} of {totalPages}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft className="size-4" aria-hidden="true" />
          </Button>
          <Button
            variant="ghost"
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            aria-label="Next page"
          >
            <ChevronRight className="size-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
```

- [ ] **Step 5: Verify and commit**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsVessels.test.tsx
corepack pnpm build
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add frontend/src/pages/FleetOpsVessels.tsx frontend/src/components/fleetops/VesselSummaryTable.tsx frontend/src/pages/FleetOpsVessels.test.tsx
git commit -m "feat: add fleetops vessel list controls"
git push origin codex/sceneops-pack-registry
```

## Gate 2: Core Multi-Transport Link Connections

### Task 3: Core Link Connections

**Files:**

- Modify: `backend/src/argus/link/contracts.py`
- Modify: `backend/src/argus/link/tables.py`
- Modify: `backend/src/argus/link/service.py`
- Modify: `backend/src/argus/link/api.py`
- Modify: `backend/src/argus/models/__init__.py`
- Create: `backend/src/argus/migrations/versions/0037_core_link_connections.py`
- Test: `backend/tests/link/test_link_service.py`
- Test: `backend/tests/api/test_link_routes.py`
- Test: `backend/tests/core/test_packless_empty_registry.py`

- [ ] **Step 1: Write failing service tests**

Append packless tests:

```python
def test_packless_link_connections_select_best_available_path(link_service: LinkService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")

    satellite = link_service.upsert_connection(
        tenant_id=tenant_id,
        site_id=site_id,
        label="VSAT primary",
        transport_kind="satellite",
        status="degraded",
        priority_rank=20,
        metered=True,
        availability_scope="at_sea",
    )
    fiber = link_service.upsert_connection(
        tenant_id=tenant_id,
        site_id=site_id,
        label="Port fiber",
        transport_kind="fiber",
        status="online",
        priority_rank=5,
        metered=False,
        availability_scope="in_port",
    )

    selected = link_service.select_connection(
        tenant_id=tenant_id,
        site_id=site_id,
        priority_lane="bulk",
        remaining_budget_bytes=0,
    )

    assert selected is not None
    assert selected.id == fiber.id
    assert satellite.transport_kind == "satellite"
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py -q
```

Expected: FAIL because `upsert_connection` does not exist.

- [ ] **Step 2: Add contracts and table**

Add literals in `contracts.py`:

```python
LinkTransportKind = Literal["satellite", "lte", "5g", "wifi", "fiber", "ethernet", "other"]
LinkConnectionStatus = Literal["unknown", "online", "degraded", "offline", "blocked", "recovering"]
LinkAvailabilityScope = Literal["always", "at_sea", "near_shore", "in_port", "maintenance"]
```

Add `LinkConnectionRecord` dataclass with the fields from the spec.

Add a `LinkConnection` SQLAlchemy table with tenant/site foreign keys, check
constraints for the literals above, and an index on `(tenant_id, site_id,
priority_rank)`.

Add nullable `connection_id` to `LinkHealthProbe`.

- [ ] **Step 3: Add service methods**

Implement:

- `upsert_connection`
- `list_connections`
- `get_connection`
- `delete_connection`
- `select_connection`
- async wrappers matching existing `a*` service patterns

Selection rules:

- ignore `offline`, `blocked`, and `unknown` connections for active selection
- prefer `online` over `recovering` over `degraded`
- then prefer lower `priority_rank`
- for `bulk`, prefer unmetered connections when present
- return `None` only when no usable connection exists

- [ ] **Step 4: Add route tests**

Add API tests:

```python
async def test_link_connection_routes_are_packless(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections",
        json={
            "label": "Port fiber",
            "transport_kind": "fiber",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "in_port",
            "metered": False,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["transport_kind"] == "fiber"

    listed = await client.get(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections"
    )
    assert listed.status_code == 200
    assert listed.json()[0]["label"] == "Port fiber"
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py -q
```

Expected: FAIL until routes are implemented.

- [ ] **Step 5: Add API routes**

Add:

- `GET /api/v1/link/sites/{site_id}/connections`
- `POST /api/v1/link/sites/{site_id}/connections`
- `PATCH /api/v1/link/sites/{site_id}/connections/{connection_id}`
- `DELETE /api/v1/link/sites/{site_id}/connections/{connection_id}`
- `GET /api/v1/link/sites/{site_id}/connections/selection`

All routes must call `_ensure_tenant_site` before service access.

- [ ] **Step 6: Extend passports**

`abuild_passport` payload should include:

```python
"active_connection": _connection_payload(selected) if selected else None,
"connections": [_connection_payload(connection) for connection in connections],
```

Existing payload fields and hashes must remain stable except for the explicit
new fields.

- [ ] **Step 7: Add migration and metadata import**

Create `0037_core_link_connections.py` with:

- `link_connections` table
- nullable `connection_id` on `link_health_probes`
- downgrade that removes the column and table

Import `LinkConnection` in `backend/src/argus/models/__init__.py`.

- [ ] **Step 8: Verify and commit**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py -q
python3 -m uv run ruff check src/argus/link tests/link tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py
python3 -m uv run mypy src/argus/link
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/contracts.py backend/src/argus/link/tables.py backend/src/argus/link/service.py backend/src/argus/link/api.py backend/src/argus/models/__init__.py backend/src/argus/migrations/versions/0037_core_link_connections.py backend/tests/link/test_link_service.py backend/tests/api/test_link_routes.py backend/tests/core/test_packless_empty_registry.py
git commit -m "feat: add core link connections"
```

### Task 4: Maritime Carrier Mapping To Core Connections

**Files:**

- Modify: `backend/src/argus/maritime/contracts.py`
- Modify: `backend/src/argus/maritime/telemetry.py`
- Modify: `backend/src/argus/maritime/api.py`
- Test: `backend/tests/maritime/test_telemetry.py`
- Test: `backend/tests/api/test_maritime_routes.py`
- Test: `backend/tests/e2e/test_maritime_fleetops_smoke.py`

- [ ] **Step 1: Write failing mapping tests**

Add tests that parse generic transport kinds:

```python
@pytest.mark.parametrize(
    ("payload_transport", "expected_transport"),
    [
        ("satellite", "satellite"),
        ("lte", "lte"),
        ("5g", "5g"),
        ("wifi", "wifi"),
        ("fiber", "fiber"),
        ("ethernet", "ethernet"),
        ("other", "other"),
    ],
)
def test_carrier_webhook_adapter_accepts_transport_kind(payload_transport: str, expected_transport: str) -> None:
    reading = CarrierWebhookAdapter().parse(
        {
            "terminal_id": f"{payload_transport}-terminal",
            "provider": "generic",
            "transport_kind": payload_transport,
            "status": "online",
            "last_seen_at": "2026-06-06T10:00:00Z",
        }
    )

    assert reading.transport_kind == expected_transport
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/maritime/test_telemetry.py -q
```

Expected: FAIL because `transport_kind` is not parsed.

- [ ] **Step 2: Add transport parsing**

Add `transport_kind: LinkTransportKind | None` to `CarrierTerminalReading`.
Map invalid values to `other` only if the payload key exists. Preserve existing
legacy `link_state` behavior.

Legacy inference:

```python
def _transport_kind_for_link_state(link_state: CarrierLinkState) -> LinkTransportKind:
    if link_state in {"satellite_good", "satellite_degraded"}:
        return "satellite"
    if link_state == "port_wifi":
        return "wifi"
    return "other"
```

- [ ] **Step 3: Write failing API route test**

Ingest a carrier payload with `transport_kind: "lte"` and assert the vessel site
has a core link connection:

```python
response = await client.post(
    "/api/v1/maritime/ingest/carrier-terminal",
    json={
        "vessel_id": str(vessel_id),
        "payload": {
            "terminal_id": "lte-a",
            "provider": "generic-lte",
            "transport_kind": "lte",
            "status": "online",
            "downlink_mbps": 45,
            "uplink_mbps": 12,
        },
    },
)
assert response.status_code == 201

connections = await client.get(f"/api/v1/link/sites/{site_id}/connections")
assert any(item["transport_kind"] == "lte" for item in connections.json())
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_maritime_routes.py -q
```

Expected: FAIL until carrier ingest upserts core link connections.

- [ ] **Step 4: Upsert core connection after carrier ingest**

In `ingest_maritime_carrier_terminal`, after the maritime terminal is saved,
load the vessel and call `services.link.aupsert_connection` with:

- `site_id = vessel.site_id`
- `label = f"{reading.provider} {reading.terminal_id}"`
- `transport_kind = reading.transport_kind or inferred transport`
- `status` mapped from carrier status
- `priority_rank = 20` for satellite, `10` for LTE/5G/Wi-Fi, `5` for
  fiber/ethernet
- `metered = True` for satellite, LTE, and 5G; `False` for fiber and ethernet
- expected throughput/latency/loss from reading fields
- `metadata = {"maritime_terminal_id": reading.terminal_id, "provider": reading.provider}`

Do not add vessel or carrier fields to core link contracts.

- [ ] **Step 5: Update carrier selection**

`GET /api/v1/maritime/vessels/{vessel_id}/carrier-selection` should return a
decision based on `services.link.aselect_connection` when core connections are
present. Preserve legacy terminal-only behavior when no core connection exists.

- [ ] **Step 6: Verify and commit**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/maritime/test_telemetry.py tests/api/test_maritime_routes.py tests/e2e/test_maritime_fleetops_smoke.py -q
python3 -m uv run ruff check src/argus/maritime tests/maritime tests/api/test_maritime_routes.py tests/e2e/test_maritime_fleetops_smoke.py
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/maritime/contracts.py backend/src/argus/maritime/telemetry.py backend/src/argus/maritime/api.py backend/tests/maritime/test_telemetry.py backend/tests/api/test_maritime_routes.py backend/tests/e2e/test_maritime_fleetops_smoke.py
git commit -m "feat: map fleetops carrier links to core connections"
git push origin codex/sceneops-pack-registry
```

## Gate 3: Fully Plumb FleetOps Pages

### Task 5: Link, Evidence, And Billing UI Plumbing

**Files:**

- Modify: `frontend/src/hooks/use-link.ts`
- Modify: `frontend/src/hooks/use-maritime.ts`
- Modify: `frontend/src/hooks/use-billing.ts`
- Create: `frontend/src/components/fleetops/LinkConnectionPanel.tsx`
- Modify: `frontend/src/components/fleetops/LinkOperationsPanel.tsx`
- Modify: `frontend/src/components/fleetops/EvidenceExportBuilder.tsx`
- Modify: `frontend/src/components/fleetops/BillingRollupPanel.tsx`
- Modify: `frontend/src/pages/FleetOpsEvidence.tsx`
- Modify: `frontend/src/pages/FleetOpsBilling.tsx`
- Test: `frontend/src/pages/FleetOpsEvidence.test.tsx`
- Test: `frontend/src/pages/FleetOpsBilling.test.tsx`
- Test: `frontend/src/pages/FleetOpsVesselDetail.test.tsx`

- [ ] **Step 1: Regenerate OpenAPI types**

Run after backend Task 4 passes:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.export_openapi_schema --output ../frontend/src/lib/openapi.json
cd /Users/yann.moren/vision/frontend
corepack pnpm generate:api
```

Expected: `frontend/src/lib/api.generated.ts` includes link connection routes.

- [ ] **Step 2: Write failing page tests**

Evidence page should show queue items and export actions:

```tsx
test("FleetOps evidence shows pending queue work and export history", async () => {
  renderWithProviders(<FleetOpsEvidence />);

  expect(await screen.findByRole("heading", { name: /Evidence/i })).toBeInTheDocument();
  expect(screen.getByText(/pending/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  expect(screen.getByText(/link posture/i)).toBeInTheDocument();
});
```

Billing page should show maritime meters and usage from core billing:

```tsx
test("FleetOps billing combines maritime rollups with core meters", async () => {
  renderWithProviders(<FleetOpsBilling />);

  expect(await screen.findByText(/vessel month/i)).toBeInTheDocument();
  expect(screen.getByText(/managed link GB/i)).toBeInTheDocument();
  expect(screen.getByText(/invoice runs/i)).toBeInTheDocument();
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsEvidence.test.tsx src/pages/FleetOpsBilling.test.tsx src/pages/FleetOpsVesselDetail.test.tsx
```

Expected: FAIL where hooks or UI are missing.

- [ ] **Step 3: Add link hooks**

Add typed hooks for:

- list/create/update/delete link connections
- list/create probes
- queue pause/resume/retry
- get/update policies
- get/update budget

Each mutation invalidates `["link", "sites", siteId]` and vessel link-status
queries when a vessel ID is known.

- [ ] **Step 4: Add billing hooks**

Add or extend hooks for:

- `GET /api/v1/billing/meters`
- `GET /api/v1/billing/usage`
- `GET /api/v1/billing/invoice-runs`
- `GET /api/v1/billing/exports/{export_id}` when linked from UI

Filter FleetOps data with `pack_id=maritime-fleet`.

- [ ] **Step 5: Render working panels**

Add `LinkConnectionPanel` to vessel detail. It should show transport kind
swatches for satellite, LTE, 5G, Wi-Fi, fiber, ethernet, and other, plus active
connection, budget, latest probe, and queue depth.

Update evidence and billing pages so visible buttons are either backed by
mutations or removed. Do not leave decorative actions.

- [ ] **Step 6: Verify and commit**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsEvidence.test.tsx src/pages/FleetOpsBilling.test.tsx src/pages/FleetOpsVesselDetail.test.tsx
corepack pnpm build
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add frontend/src/hooks/use-link.ts frontend/src/hooks/use-maritime.ts frontend/src/hooks/use-billing.ts frontend/src/components/fleetops/LinkConnectionPanel.tsx frontend/src/components/fleetops/LinkOperationsPanel.tsx frontend/src/components/fleetops/EvidenceExportBuilder.tsx frontend/src/components/fleetops/BillingRollupPanel.tsx frontend/src/pages/FleetOpsEvidence.tsx frontend/src/pages/FleetOpsEvidence.test.tsx frontend/src/pages/FleetOpsBilling.tsx frontend/src/pages/FleetOpsBilling.test.tsx frontend/src/pages/FleetOpsVesselDetail.test.tsx frontend/src/lib/openapi.json frontend/src/lib/api.generated.ts
git commit -m "feat: plumb fleetops link evidence billing pages"
```

### Task 6: Support And Onboarding Split

**Files:**

- Modify: `backend/src/argus/maritime/support.py`
- Modify: `backend/src/argus/maritime/api.py`
- Modify: `backend/tests/api/test_support_routes.py`
- Modify: `frontend/src/hooks/use-support.ts`
- Create: `frontend/src/components/fleetops/SupportReadinessPanel.tsx`
- Create: `frontend/src/components/fleetops/OnboardingChecklistPanel.tsx`
- Modify: `frontend/src/components/fleetops/SupportDiagnosticsPanel.tsx`
- Modify: `frontend/src/pages/FleetOpsSupport.tsx`
- Modify: `frontend/src/pages/FleetOpsOnboarding.tsx`
- Test: `frontend/src/pages/FleetOpsSupport.test.tsx`
- Test: `frontend/src/pages/FleetOpsOnboarding.test.tsx`

- [ ] **Step 1: Write failing backend diagnostics test**

Change support route tests to expect operator-ready group payloads:

```python
async def test_maritime_support_diagnostics_expose_readiness_groups(client: AsyncClient) -> None:
    response = await client.get("/api/v1/maritime/support/diagnostics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "Support readiness"
    first_group = payload["groups"][0]
    assert set(first_group) >= {"id", "label", "status", "checks", "next_action"}
    assert first_group["label"] != "Satellite link"
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_support_routes.py -q
```

Expected: FAIL because diagnostics are a dict keyed by internal names.

- [ ] **Step 2: Enrich maritime diagnostics payload**

Return:

```python
{
    "pack_id": "maritime-fleet",
    "label": "Support readiness",
    "groups": [
        {
            "id": "connectivity",
            "label": "Connectivity readiness",
            "status": "attention",
            "checks": [
                {"key": "link_state", "label": "Link state", "status": "attention"},
            ],
            "next_action": "Review active connection and queued evidence work.",
        },
    ],
}
```

Use IDs: `connectivity`, `shipboard_network`, `evidence_path`,
`access_and_roles`. Avoid the phrase "diagnostic groups" in user-facing
payload labels.

- [ ] **Step 3: Write failing frontend tests**

Support page expectations:

```tsx
test("FleetOps support renders support readiness and support actions", async () => {
  renderWithProviders(<FleetOpsSupport />);

  expect(await screen.findByRole("heading", { name: /Support/i })).toBeInTheDocument();
  expect(screen.getByText(/Support readiness/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /generate bundle/i })).toBeInTheDocument();
  expect(screen.queryByText(/setup checks/i)).not.toBeInTheDocument();
});
```

Onboarding page expectations:

```tsx
test("FleetOps onboarding renders setup checks separately from support readiness", async () => {
  renderWithProviders(<FleetOpsOnboarding />);

  expect(await screen.findByRole("heading", { name: /Onboarding/i })).toBeInTheDocument();
  expect(screen.getByText(/setup checks/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /run checks/i })).toBeInTheDocument();
  expect(screen.queryByText(/Generate bundle/i)).not.toBeInTheDocument();
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsSupport.test.tsx src/pages/FleetOpsOnboarding.test.tsx
```

Expected: FAIL because both pages use the same panel.

- [ ] **Step 4: Add support mutations**

In `use-support.ts`, add:

- `useCreateSupportBundle`
- `useCreateSupportSession`
- `useCloseSupportSession`
- `useRequestSupportTunnel`
- `useRevokeSupportTunnel`
- `useOpenBreakGlass`
- `useCloseBreakGlass`
- `useRunSupportOnboardingChecks`

Invalidate relevant `["support"]` and `["support", "onboarding-checks", siteId]`
queries on success.

- [ ] **Step 5: Split UI panels**

`FleetOpsSupport.tsx` should render `SupportReadinessPanel` with readiness
groups and support actions.

`FleetOpsOnboarding.tsx` should render `OnboardingChecklistPanel` with setup
checks and the Run Checks action.

Keep `SupportDiagnosticsPanel` only as a thin compatibility wrapper or remove
it if no tests import it directly.

- [ ] **Step 6: Verify and commit**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_support_routes.py -q
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsSupport.test.tsx src/pages/FleetOpsOnboarding.test.tsx
corepack pnpm build
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/maritime/support.py backend/src/argus/maritime/api.py backend/tests/api/test_support_routes.py frontend/src/hooks/use-support.ts frontend/src/components/fleetops/SupportReadinessPanel.tsx frontend/src/components/fleetops/OnboardingChecklistPanel.tsx frontend/src/components/fleetops/SupportDiagnosticsPanel.tsx frontend/src/pages/FleetOpsSupport.tsx frontend/src/pages/FleetOpsSupport.test.tsx frontend/src/pages/FleetOpsOnboarding.tsx frontend/src/pages/FleetOpsOnboarding.test.tsx
git commit -m "feat: split fleetops support onboarding workflows"
git push origin codex/sceneops-pack-registry
```

### Task 7: Product Completeness Sweep

**Files:**

- Modify: `frontend/src/pages/FleetOps.tsx`
- Modify: `frontend/src/components/fleetops/FleetOverviewPanel.tsx`
- Modify: `frontend/src/components/fleetops/VoyageTimeline.tsx`
- Modify: `frontend/src/components/fleetops/types.ts`
- Modify: `frontend/src/pages/FleetOps.test.tsx`
- Modify: `frontend/src/pages/FleetOpsVesselDetail.test.tsx`
- Modify: `backend/tests/e2e/test_maritime_fleetops_smoke.py`

- [ ] **Step 1: Write failing overview test**

The overview should show actionable summary data and no dead buttons:

```tsx
test("FleetOps overview links to each fully plumbed workflow", async () => {
  renderWithProviders(<FleetOps />);

  expect(await screen.findByRole("heading", { name: "FleetOps" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /add vessel/i })).toHaveAttribute(
    "href",
    "/fleetops/vessels",
  );
  expect(screen.getByRole("link", { name: /review evidence/i })).toHaveAttribute(
    "href",
    "/fleetops/evidence",
  );
  expect(screen.getByRole("link", { name: /open billing/i })).toHaveAttribute(
    "href",
    "/fleetops/billing",
  );
  expect(screen.getByRole("link", { name: /open support/i })).toHaveAttribute(
    "href",
    "/fleetops/support",
  );
  expect(screen.getByRole("link", { name: /open onboarding/i })).toHaveAttribute(
    "href",
    "/fleetops/onboarding",
  );
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOps.test.tsx
```

Expected: FAIL until overview links are complete.

- [ ] **Step 2: Remove decorative controls**

Scan FleetOps components for visible buttons without handlers or links:

```bash
cd /Users/yann.moren/vision
rg -n "<button|role=\\\"button\\\"|Button" frontend/src/components/fleetops frontend/src/pages/FleetOps*.tsx
```

For each visible command:

- wire it to a route or mutation
- or remove it
- or render it disabled with a backend-derived reason

- [ ] **Step 3: Update copy for transport neutrality**

Replace satellite-only UI copy with neutral link wording unless the specific
data item is truly satellite:

- "satellite link" -> "active connection" or "metered link"
- "moves over satellite" -> "moves over the selected connection"
- "port WiFi" -> "in-port link" when transport kind is not known

Do not remove satellite as a supported transport kind.

- [ ] **Step 4: Extend e2e smoke**

Update backend e2e smoke to:

- create a vessel
- ingest a satellite carrier record
- ingest an LTE carrier record
- create a fiber connection through core link API
- verify carrier selection picks fiber for bulk when online
- verify evidence export still includes link passport hash

- [ ] **Step 5: Verify and commit**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/e2e/test_maritime_fleetops_smoke.py -q
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOps.test.tsx src/pages/FleetOpsVesselDetail.test.tsx
corepack pnpm build
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add frontend/src/pages/FleetOps.tsx frontend/src/components/fleetops/FleetOverviewPanel.tsx frontend/src/components/fleetops/VoyageTimeline.tsx frontend/src/components/fleetops/types.ts frontend/src/pages/FleetOps.test.tsx frontend/src/pages/FleetOpsVesselDetail.test.tsx backend/tests/e2e/test_maritime_fleetops_smoke.py
git commit -m "feat: complete fleetops operator surfaces"
```

## Gate 4: Validation

### Task 8: Full Verification, Real Stack, And Installer Artifacts

**Files:**

- Validation may modify these installer artifacts when a verification failure
  identifies a defect in installer output:
  - `installer/macos/install-master.sh`
  - `installer/linux/install-master.sh`
  - `installer/edge/install-edge.sh`
  - `installer/manifests/dev-example.json`
  - installer artifact tests under `installer/tests/`
- Test: `e2e/fleetops.spec.ts`

- [ ] **Step 1: Run backend verification**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link tests/maritime tests/api/test_link_routes.py tests/api/test_maritime_routes.py tests/api/test_support_routes.py tests/api/test_openapi_export.py tests/core/test_packless_empty_registry.py tests/e2e/test_maritime_fleetops_smoke.py -q
python3 -m uv run ruff check src tests
python3 -m uv run mypy src/argus
```

Expected: PASS.

- [ ] **Step 2: Run frontend verification**

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run
corepack pnpm build
corepack pnpm lint
```

Expected: PASS.

- [ ] **Step 3: Run installer artifact tests**

```bash
cd /Users/yann.moren/vision/installer
python3 -m uv run pytest tests/test_macos_master_artifacts.py tests/test_linux_master_artifacts.py tests/test_edge_installer_artifacts.py -q
python3 -m uv run pytest -q
```

Expected: PASS. If tests fail because new migrations, generated frontend
assets, or config files are excluded from an installer package, patch only the
relevant installer and artifact test.

- [ ] **Step 4: Run a real-stack Playwright smoke**

Use the same appliance/dev stack pattern from the FleetOps runtime branch.
Start from a clean stack, apply Alembic migrations, run the FleetOps Playwright
smoke, then restore the appliance stack if it was running before validation.

```bash
cd /Users/yann.moren/vision
CI=true corepack pnpm exec playwright test e2e/fleetops.spec.ts
```

Expected: PASS. The smoke must prove:

- the FleetOps icon exposes child navigation
- Vessels page can add a vessel
- the created vessel detail page shows connectivity
- Evidence, Billing, Support, and Onboarding routes load from rail links
- Support and Onboarding are visibly distinct

- [ ] **Step 5: Boundary scans**

Run:

```bash
cd /Users/yann.moren/vision
rg -n "traffic-public-space|home-lab|lab_only|Intersection|CurbZone|SignalPhase" backend/src frontend/src packs docs/superpowers/specs/2026-06-06-fleetops-operator-completion-design.md docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md
rg -n "Vessel|Voyage|PortCall|AIS|NMEA|CarrierTerminal|owner|charterer" backend/src/argus/link backend/src/argus/fleet backend/src/argus/billing backend/src/argus/support
```

Expected:

- no new traffic/public-space runtime or home-lab product references
- no maritime nouns in core link/fleet/billing/support contracts or services
- docs may mention forbidden words only as constraints or examples

- [ ] **Step 6: Commit validation fixes and push**

If installer or smoke fixes were required:

```bash
cd /Users/yann.moren/vision
git status --short
git add installer/macos/install-master.sh installer/linux/install-master.sh installer/edge/install-edge.sh installer/tests/test_macos_master_artifacts.py installer/tests/test_linux_master_artifacts.py installer/tests/test_edge_installer_artifacts.py e2e/fleetops.spec.ts
git commit -m "test: validate fleetops operator workflows"
```

Push:

```bash
git push origin codex/sceneops-pack-registry
```

Do not merge to `main`.

## Final Handoff Checklist

- [ ] Branch is still `codex/sceneops-pack-registry`.
- [ ] All focused commits are pushed.
- [ ] No unrelated scratch files are staged.
- [ ] Backend tests pass.
- [ ] Frontend tests/build/lint pass.
- [ ] Installer artifact tests pass.
- [ ] Real-stack Playwright FleetOps smoke passes.
- [ ] Support and onboarding pages are distinct.
- [ ] Vessel creation works from the UI.
- [ ] Vessels page search, link-state filter, status filter, and 10/25/50
  pagination work without auto-opening a vessel detail.
- [ ] Link transport supports satellite, LTE, 5G, Wi-Fi, fiber, ethernet, and
  other through core link connections.
- [ ] No traffic/public-space runtime, home-lab pack/status/UI, proprietary
  carrier SDK, payment processor, or accounting integration was added.
