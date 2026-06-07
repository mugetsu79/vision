# Core Link Performance Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a domain-neutral Core Link Performance workspace that lets operators inspect and operate link health, connections, budgets, probes, policies, queues, and passports across generic sites without entering FleetOps.

**Architecture:** Keep selected-site detail on existing `/api/v1/link/sites/{site_id}/...` routes and add one packless `/api/v1/link/sites/summary` route for efficient list posture. Frontend work adds a `/links` page under the existing React workspace shell, reusing generated OpenAPI types, TanStack Query, shared pagination, `WorkspaceBand`, `WorkspaceSurface`, and current link mutation hooks.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async, pytest, httpx ASGI transport, React 19, TypeScript, TanStack Query, Vitest, Testing Library, pnpm, uv.

---

## Non-Negotiable Constraints

Preserve all constraints from `docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md`:

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

Stop and surface a conflict if implementation requires:

- adding maritime or traffic nouns to core link contracts, tables, routes, services, page copy, or tests
- implementing traffic/public-space runtime, demos, UI, or migrations
- creating home-lab pack status or UI
- integrating proprietary carrier SDKs
- integrating payment processors or accounting systems
- changing detector/runtime semantics
- changing evidence hash semantics or link passport hashing semantics outside the fields already modeled by `argus.link`

Do not stage unrelated scratch files, `.claude/`, `.codex/`, `.superpowers/`, `.vite/`, screenshots, or `taste-skill/`. Do not use `git add -A`.

## Atomic Commit Policy

Use focused commits and push `origin codex/sceneops-pack-registry` after these checkpoints:

1. Backend link summary route.
2. Link workspace navigation and selected-site shell.
3. Link detail controls and FleetOps deep links.
4. Full verification.

Suggested commit messages:

- `feat: add core link summary route`
- `feat: add link performance workspace`
- `feat: wire link workspace controls`
- `test: validate core link workspace`

## Current Baseline

Already present:

- Core link models and services:
  - `backend/src/argus/link/contracts.py`
  - `backend/src/argus/link/tables.py`
  - `backend/src/argus/link/service.py`
  - `backend/src/argus/link/api.py`
- Link routes for selected-site status, budget, connections, queue, probes, policies, passport, and queue actions.
- Frontend link hooks in `frontend/src/hooks/use-link.ts` for selected-site reads and mutations.
- Shared pagination utilities:
  - `frontend/src/components/ui/pagination.ts`
  - `frontend/src/components/ui/pagination-controls.tsx`
- Sites search/pagination/edit pattern in `frontend/src/pages/Sites.tsx`.
- FleetOps pages that can deep-link to core link by site ID.

Missing:

- Aggregate core link summary route for all generic sites.
- `/links` route and Control nav entry.
- Link page with explicit site selection, no default detail, search, and 10/25/50 pagination.
- Core link detail panels for connections, budget, policy, probes, queue, and passport.
- FleetOps "Open Link Performance" deep links.

## File Structure

Modify backend core link:

- `backend/src/argus/link/contracts.py`: add `LinkSiteSummaryRecord`.
- `backend/src/argus/link/service.py`: add sync and async summary methods.
- `backend/src/argus/link/api.py`: add named response models and `GET /api/v1/link/sites/summary`.
- `backend/tests/link/test_link_service.py`: add packless summary tests.
- `backend/tests/api/test_link_routes.py`: add summary route and tenant isolation tests.
- `backend/tests/core/test_packless_empty_registry.py`: add empty-registry summary coverage.

Modify frontend link:

- `frontend/src/hooks/use-link.ts`: add `useLinkSiteSummaries`.
- `frontend/src/hooks/use-link.test.ts`: create hook coverage for `useLinkSiteSummaries`.
- `frontend/src/pages/Links.tsx`: create the Link Performance page.
- `frontend/src/pages/Links.test.tsx`: cover page behavior.
- `frontend/src/components/link/LinkSiteSelector.tsx`: searchable paginated site selector.
- `frontend/src/components/link/LinkPosturePanel.tsx`: selected-site posture/passport panel.
- `frontend/src/components/link/LinkConnectionsPanel.tsx`: connection inventory and controls.
- `frontend/src/components/link/LinkBudgetPolicyPanel.tsx`: budget and policy controls.
- `frontend/src/components/link/LinkProbePanel.tsx`: probe history and record-probe dialog.
- `frontend/src/components/link/LinkQueuePanel.tsx`: queue list and pause/resume/retry.
- `frontend/src/components/link/LinkActionDialogs.tsx`: focused dialog helpers.
- `frontend/src/components/link/types.ts`: small view helpers only, not parallel API DTOs.
- `frontend/src/app/router.tsx`: add `/links`.
- `frontend/src/components/layout/workspace-nav.ts`: add Control nav item and prefetch.
- `frontend/src/components/layout/AppShell.test.tsx`: cover Link nav behavior.

Modify FleetOps deep links:

- `frontend/src/pages/FleetOpsVesselDetail.tsx`: add generic link to `/links?site=<site_id>`.
- `frontend/src/pages/FleetOpsEvidence.tsx`: add selected-scope link when a vessel/site is selected.
- `frontend/src/pages/FleetOpsSupport.tsx`: add selected-scope link when a vessel/site is selected.
- `frontend/src/pages/FleetOpsOnboarding.tsx`: add selected-scope link when a vessel/site is selected.
- Existing `frontend/src/pages/FleetOps*.test.tsx`: assert deep links where page has selected site context.

Regenerate OpenAPI artifacts after backend route changes:

- `frontend/src/lib/openapi.json`
- `frontend/src/lib/api.generated.ts`

## Gate 1: Backend Summary

### Task 1: Link Site Summary Route

**Files:**

- Modify: `backend/src/argus/link/contracts.py`
- Modify: `backend/src/argus/link/service.py`
- Modify: `backend/src/argus/link/api.py`
- Test: `backend/tests/link/test_link_service.py`
- Test: `backend/tests/api/test_link_routes.py`
- Test: `backend/tests/core/test_packless_empty_registry.py`

- [ ] **Step 1: Write failing service tests**

Add tests to `backend/tests/link/test_link_service.py`:

```python
def test_packless_link_site_summaries_include_status_budget_queue_and_probe(
    link_service: LinkService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")

    connection = link_service.upsert_connection(
        tenant_id=tenant_id,
        site_id=site_id,
        label="Primary fiber",
        transport_kind="fiber",
        status="online",
        priority_rank=5,
        availability_scope="always",
        metered=False,
        expected_downlink_mbps=250.0,
        expected_uplink_mbps=100.0,
    )
    budget = link_service.upsert_budget(
        tenant_id=tenant_id,
        site_id=site_id,
        monthly_bytes=500_000_000_000,
        bulk_daily_bytes=25_000_000_000,
    )
    link_service.record_probe(
        tenant_id=tenant_id,
        site_id=site_id,
        connection_id=connection.id,
        latency_ms=42,
        throughput_mbps=180.0,
        packet_loss_percent=0.1,
        reachable=True,
        source="packless-lab",
    )
    link_service.enqueue_transfer(
        tenant_id=tenant_id,
        site_id=site_id,
        priority_lane="evidence",
        byte_size=8_000_000,
        source_object_type="evidence_artifact",
        source_object_id=UUID("00000000-0000-4000-8000-000000000030"),
    )

    summaries = link_service.list_site_summaries(
        tenant_id=tenant_id,
        sites=[{"id": site_id, "name": "North Gate", "tz": "UTC"}],
    )

    assert summaries[0].site_id == site_id
    assert summaries[0].site_name == "North Gate"
    assert summaries[0].site_tz == "UTC"
    assert summaries[0].link_state == "healthy"
    assert summaries[0].active_connection is not None
    assert summaries[0].active_connection.id == connection.id
    assert summaries[0].connection_count == 1
    assert summaries[0].metered_connection_count == 0
    assert summaries[0].latest_probe is not None
    assert summaries[0].latest_probe.latency_ms == 42
    assert summaries[0].queue_depth["evidence"] == 1
    assert summaries[0].queued_bytes == 8_000_000
    assert summaries[0].budget is not None
    assert summaries[0].budget.id == budget.id
    assert summaries[0].passport_hash
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_packless_link_site_summaries_include_status_budget_queue_and_probe -q
```

Expected: FAIL because `list_site_summaries` and `LinkSiteSummaryRecord` do not exist.

- [ ] **Step 2: Add summary contract**

Add to `backend/src/argus/link/contracts.py`:

```python
@dataclass(frozen=True, slots=True)
class LinkSiteSummaryRecord:
    site_id: UUID
    site_name: str
    site_tz: str
    link_state: LinkState
    active_connection: LinkConnectionRecord | None
    connection_count: int
    metered_connection_count: int
    latest_probe: LinkHealthProbeRecord | None
    queue_depth: dict[LinkPriorityLane, int]
    queued_bytes: int
    budget: LinkBudgetSnapshot | None
    last_sync_at: datetime | None
    passport_hash: str
```

Update `backend/src/argus/link/__init__.py` to import `LinkSiteSummaryRecord` and include it in `__all__`.

- [ ] **Step 3: Implement sync summary service**

In `backend/src/argus/link/service.py`, add:

```python
def list_site_summaries(
    self,
    *,
    tenant_id: UUID,
    sites: Sequence[Mapping[str, object]],
) -> list[LinkSiteSummaryRecord]:
    self._ensure_memory_mode()
    summaries: list[LinkSiteSummaryRecord] = []
    for site in sites:
        site_id = cast(UUID, site["id"])
        connections = self.list_connections(tenant_id=tenant_id, site_id=site_id)
        budget = self.get_budget(tenant_id=tenant_id, site_id=site_id)
        active_connection = _select_connection(
            connections,
            priority_lane="bulk",
            remaining_budget_bytes=budget.bulk_daily_bytes if budget is not None else 0,
        )
        latest_probe = self.latest_probe(tenant_id=tenant_id, site_id=site_id)
        queue = self.list_queue(tenant_id=tenant_id, site_id=site_id)
        last_sync_at = self.last_successful_transfer_at(
            tenant_id=tenant_id,
            site_id=site_id,
        )
        passport = self.build_passport(tenant_id=tenant_id, site_id=site_id)
        summaries.append(
            LinkSiteSummaryRecord(
                site_id=site_id,
                site_name=str(site["name"]),
                site_tz=str(site.get("tz", "UTC")),
                link_state=self.derive_link_state(latest_probe),
                active_connection=active_connection,
                connection_count=len(connections),
                metered_connection_count=sum(1 for connection in connections if connection.metered),
                latest_probe=latest_probe,
                queue_depth=self.queue_depth_by_lane(queue),
                queued_bytes=sum(item.byte_size for item in queue if item.status not in {"paused", "succeeded"}),
                budget=budget,
                last_sync_at=last_sync_at,
                passport_hash=passport.passport_hash,
            )
        )
    return summaries
```

Add imports for `Mapping`, `Sequence`, `cast`, and `LinkSiteSummaryRecord`. Keep this method generic; do not import maritime.

- [ ] **Step 4: Implement async summary service**

Add an async equivalent in `backend/src/argus/link/service.py`:

```python
async def alist_site_summaries(
    self,
    *,
    tenant_id: UUID,
    sites: Sequence[Mapping[str, object]],
) -> list[LinkSiteSummaryRecord]:
    if self.session_factory is None:
        return self.list_site_summaries(tenant_id=tenant_id, sites=sites)
    summaries: list[LinkSiteSummaryRecord] = []
    for site in sites:
        site_id = cast(UUID, site["id"])
        connections = await self.alist_connections(tenant_id=tenant_id, site_id=site_id)
        budget = await self.aget_budget(tenant_id=tenant_id, site_id=site_id)
        active_connection = _select_connection(
            connections,
            priority_lane="bulk",
            remaining_budget_bytes=budget.bulk_daily_bytes if budget is not None else 0,
        )
        latest_probe = await self.alatest_probe(tenant_id=tenant_id, site_id=site_id)
        queue = await self.alist_queue(tenant_id=tenant_id, site_id=site_id)
        last_sync_at = await self.alast_successful_transfer_at(
            tenant_id=tenant_id,
            site_id=site_id,
        )
        passport = await self.abuild_passport(tenant_id=tenant_id, site_id=site_id)
        summaries.append(
            LinkSiteSummaryRecord(
                site_id=site_id,
                site_name=str(site["name"]),
                site_tz=str(site.get("tz", "UTC")),
                link_state=self.derive_link_state(latest_probe),
                active_connection=active_connection,
                connection_count=len(connections),
                metered_connection_count=sum(1 for connection in connections if connection.metered),
                latest_probe=latest_probe,
                queue_depth=self.queue_depth_by_lane(queue),
                queued_bytes=sum(item.byte_size for item in queue if item.status not in {"paused", "succeeded"}),
                budget=budget,
                last_sync_at=last_sync_at,
                passport_hash=passport.passport_hash,
            )
        )
    return summaries
```

This intentionally uses existing per-site methods for the MVP. Batched SQL optimization belongs behind the same service contract in a later performance pass.

- [ ] **Step 5: Write failing API route test**

Add to `backend/tests/api/test_link_routes.py`:

```python
@pytest.mark.asyncio
async def test_link_site_summary_route_is_packless_and_domain_neutral(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/link/sites/summary")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload
    assert {
        "site_id",
        "site_name",
        "site_tz",
        "link_state",
        "connection_count",
        "metered_connection_count",
        "queue_depth",
        "queued_bytes",
        "passport_hash",
    } <= set(payload[0])
    assert "vessel" not in payload[0]
    assert "voyage" not in payload[0]
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py::test_link_site_summary_route_is_packless_and_domain_neutral -q
```

Expected: FAIL because `/api/v1/link/sites/summary` is not routed.

- [ ] **Step 6: Add named summary API response and route**

In `backend/src/argus/link/api.py`, add route before `/sites/{site_id}/status` so the literal path is not captured as a UUID:

```python
class LinkSiteSummaryResponse(BaseModel):
    site_id: UUID
    site_name: str
    site_tz: str
    link_state: str
    active_connection: dict[str, object] | None = None
    connection_count: int
    metered_connection_count: int
    latest_probe: dict[str, object] | None = None
    queue_depth: dict[str, int] = Field(default_factory=dict)
    queued_bytes: int
    budget: dict[str, object] | None = None
    last_sync_at: datetime | None = None
    passport_hash: str


@router.get("/sites/summary", response_model=list[LinkSiteSummaryResponse])
async def get_link_site_summaries(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[LinkSiteSummaryResponse]:
    sites = await services.sites.list_sites(tenant_context)
    summary_records = await services.link.alist_site_summaries(
        tenant_id=tenant_context.tenant_id,
        sites=[
            {"id": site.id, "name": site.name, "tz": site.tz}
            for site in sites
        ],
    )
    return [_site_summary_payload(summary) for summary in summary_records]
```

Add payload helper:

```python
def _site_summary_payload(summary: LinkSiteSummaryRecord) -> LinkSiteSummaryResponse:
    return LinkSiteSummaryResponse(
        site_id=summary.site_id,
        site_name=summary.site_name,
        site_tz=summary.site_tz,
        link_state=summary.link_state,
        active_connection=(
            _connection_payload(summary.active_connection)
            if summary.active_connection is not None
            else None
        ),
        connection_count=summary.connection_count,
        metered_connection_count=summary.metered_connection_count,
        latest_probe=(
            _probe_payload(summary.latest_probe)
            if summary.latest_probe is not None
            else None
        ),
        queue_depth=summary.queue_depth,
        queued_bytes=summary.queued_bytes,
        budget=(
            _budget_payload(summary.budget)
            if summary.budget is not None
            else None
        ),
        last_sync_at=summary.last_sync_at,
        passport_hash=summary.passport_hash,
    )
```

Import `LinkSiteSummaryRecord`.

- [ ] **Step 7: Extend empty-registry test coverage**

In `backend/tests/core/test_packless_empty_registry.py`, add `list_sites` to `_FakeSiteService`:

```python
async def list_sites(self, tenant_context: TenantContext) -> list[SiteResponse]:
    return [
        SiteResponse(
            id=SITE_ID,
            tenant_id=tenant_context.tenant_id,
            name="Packless Site",
            description=None,
            tz="UTC",
            geo_point=None,
            created_at=datetime.now(tz=UTC),
        )
    ]
```

Add:

```python
@pytest.mark.asyncio
async def test_link_summary_route_works_with_empty_pack_registry(
    empty_pack_app: FastAPI,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=empty_pack_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/link/sites/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["site_id"] == "00000000-0000-4000-8000-000000000002"
    assert payload[0]["site_name"] == "Packless Site"
    assert "vessel" not in json.dumps(payload).lower()
```

- [ ] **Step 8: Verify backend summary**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py -q
python3 -m uv run ruff check src/argus/link tests/link tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py
python3 -m uv run mypy src/argus/link
```

Expected: PASS.

- [ ] **Step 9: Commit backend summary**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/contracts.py backend/src/argus/link/__init__.py backend/src/argus/link/service.py backend/src/argus/link/api.py backend/tests/link/test_link_service.py backend/tests/api/test_link_routes.py backend/tests/core/test_packless_empty_registry.py
git commit -m "feat: add core link summary route"
git push origin codex/sceneops-pack-registry
```

## Gate 2: Navigation And Page Shell

### Task 2: Link Workspace Route And Explicit Site Selector

**Files:**

- Modify: `frontend/src/hooks/use-link.ts`
- Create: `frontend/src/hooks/use-link.test.ts`
- Create: `frontend/src/pages/Links.tsx`
- Create: `frontend/src/pages/Links.test.tsx`
- Create: `frontend/src/components/link/types.ts`
- Create: `frontend/src/components/link/LinkSiteSelector.tsx`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/components/layout/workspace-nav.ts`
- Modify: `frontend/src/components/layout/AppShell.test.tsx`
- Modify: `frontend/src/lib/openapi.json`
- Modify: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Regenerate OpenAPI**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.export_openapi_schema ../frontend/src/lib/openapi.json
cd /Users/yann.moren/vision/frontend
corepack pnpm generate:api
```

Expected: `frontend/src/lib/openapi.json` includes `/api/v1/link/sites/summary`, and `frontend/src/lib/api.generated.ts` includes the response schema.

- [ ] **Step 2: Create failing hook test**

Create `frontend/src/hooks/use-link.test.ts`:

```ts
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) => new Error(fallbackMessage),
}));

import { useLinkSiteSummaries } from "@/hooks/use-link";
import { apiClient } from "@/lib/api";
import { createTestQueryWrapper } from "@/test/query-test-utils";

describe("link hooks", () => {
  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: [],
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);
  });

  test("useLinkSiteSummaries reads the core link summary route", async () => {
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: [
        {
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
        },
      ],
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);

    const { result } = renderHook(() => useLinkSiteSummaries(), {
      wrapper: createTestQueryWrapper(),
    });

    await waitFor(() => expect(result.current.data).toHaveLength(1));
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/link/sites/summary");
  });
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/hooks/use-link.test.ts
```

Expected: FAIL because `useLinkSiteSummaries` does not exist.

- [ ] **Step 3: Add summary hook**

Add to `frontend/src/hooks/use-link.ts`:

```ts
export type LinkSiteSummary = components["schemas"]["LinkSiteSummaryResponse"];

export function useLinkSiteSummaries() {
  return useQuery({
    queryKey: ["link", "sites", "summary"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/link/sites/summary");
      if (error) {
        throw toApiError(error, "Failed to load link summaries.");
      }
      return data ?? [];
    },
  });
}
```

Verify `components["schemas"]["LinkSiteSummaryResponse"]` exists before moving on. A missing generated schema means Task 1 is incomplete and the backend response model must be fixed before frontend work continues.

- [ ] **Step 4: Write failing navigation test**

In `frontend/src/components/layout/AppShell.test.tsx`, add or update assertions:

```tsx
test("exposes core link performance in the control rail", () => {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={["/links"]}>
        <AppShell>
          <div>Links page</div>
        </AppShell>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  const controlNav = screen.getByRole("navigation", { name: /control/i });
  expect(within(controlNav).getByRole("link", { name: "Links" })).toHaveAttribute(
    "href",
    "/links",
  );
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/components/layout/AppShell.test.tsx
```

Expected: FAIL because the Control nav has no Links item.

- [ ] **Step 5: Add nav and route**

In `frontend/src/components/layout/workspace-nav.ts`, map or add a Control item:

```ts
{ label: "Links", to: "/links", icon: Network }
```

Import a fitting Lucide icon such as `Network` or `Cable`. Extend `prefetchWorkspaceRoute`:

```ts
if (route === "/links") {
  void import("@/pages/Links");
}
```

In `frontend/src/app/router.tsx`, add:

```tsx
{
  path: "links",
  lazy: async () => ({
    Component: (await import("@/pages/Links")).LinksPage,
  }),
},
```

- [ ] **Step 6: Write failing page selector tests**

Create `frontend/src/pages/Links.test.tsx`:

```tsx
test("Link Performance starts without selecting the first site", async () => {
  mockLinkHooks({
    summaries: [
      createSummary({ site_id: "site-1", site_name: "North Gate" }),
      createSummary({ site_id: "site-2", site_name: "South Gate" }),
    ],
  });

  renderWithProviders(<Links />);

  expect(await screen.findByRole("heading", { name: /Link Performance/i })).toBeInTheDocument();
  expect(screen.getByText(/choose a site to inspect link performance/i)).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: /Current posture/i })).not.toBeInTheDocument();
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
  expect(within(selector).getAllByRole("button", { name: /select remote site/i })).toHaveLength(10);
  expect(within(selector).queryByText("Remote Site 11")).not.toBeInTheDocument();

  await user.selectOptions(screen.getByLabelText(/link sites per page/i), "25");
  expect(within(selector).getAllByRole("button", { name: /select remote site/i })).toHaveLength(12);

  await user.type(screen.getByLabelText(/search link sites/i), "12");
  expect(within(selector).getByText("Remote Site 12")).toBeInTheDocument();
  expect(within(selector).queryByText("Remote Site 1")).not.toBeInTheDocument();
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: FAIL because `Links` does not exist.

- [ ] **Step 7: Implement link selector component**

Create `frontend/src/components/link/types.ts` with helpers:

```ts
import type { LinkSiteSummary } from "@/hooks/use-link";

export type LinkSiteSummaryItem = LinkSiteSummary;

export function textValue(value: unknown, fallback = "Not recorded") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function numberValue(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}
```

Create `frontend/src/components/link/LinkSiteSelector.tsx` using `PaginationControls`, `paginateItems`, and explicit selection:

```tsx
export function LinkSiteSelector({
  summaries,
  searchValue,
  selectedSiteId,
  onSearchChange,
  onSelectSite,
}: LinkSiteSelectorProps) {
  const [pageSize, setPageSize] = useState<PaginationPageSize>(10);
  const [pageIndex, setPageIndex] = useState(0);
  const filtered = filterSummaries(summaries, searchValue);
  const paginated = paginateItems(filtered, pageSize, pageIndex);

  useEffect(() => {
    setPageIndex(0);
  }, [pageSize, searchValue, filtered.length]);

  return (
    <WorkspaceSurface data-testid="link-site-selector" className="p-4">
      <Input
        aria-label="Search link sites"
        placeholder="Search site, transport, provider, or link state"
        value={searchValue}
        onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
          onSearchChange(event.currentTarget.value)
        }
      />
      <div className="mt-4 grid gap-2">
        {paginated.items.map((summary) => (
          <button
            key={summary.site_id}
            aria-pressed={summary.site_id === selectedSiteId}
            aria-label={`Select ${summary.site_name}`}
            type="button"
            onClick={() => onSelectSite(summary.site_id)}
          >
            <span>{summary.site_name}</span>
            <span>{summary.link_state}</span>
          </button>
        ))}
      </div>
      <PaginationControls
        className="mt-3"
        itemLabel="sites"
        pageIndex={paginated.currentPageIndex}
        pageSize={pageSize}
        pageSizeLabel="Link sites per page"
        totalCount={filtered.length}
        onPageIndexChange={setPageIndex}
        onPageSizeChange={setPageSize}
      />
    </WorkspaceSurface>
  );
}
```

Use existing Vezor classes from Sites/FleetOps selectors when filling the button markup.

- [ ] **Step 8: Implement Links page shell**

Create `frontend/src/pages/Links.tsx`:

```tsx
export function Links() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchValue, setSearchValue] = useState("");
  const selectedSiteId = searchParams.get("site");
  const summaries = useLinkSiteSummaries();
  const selectedSummary = useMemo(
    () => (summaries.data ?? []).find((summary) => summary.site_id === selectedSiteId) ?? null,
    [selectedSiteId, summaries.data],
  );

  function selectSite(siteId: string) {
    setSearchParams({ site: siteId });
  }

  function clearSite() {
    setSearchParams({});
  }

  return (
    <main data-testid="link-performance-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Core Link"
        title="Link Performance"
        description="Monitor site connectivity, transfer posture, budgets, probes, and link passports across Vezor."
      />
      <LinkSiteSelector
        summaries={summaries.data ?? []}
        searchValue={searchValue}
        selectedSiteId={selectedSiteId}
        onSearchChange={setSearchValue}
        onSelectSite={selectSite}
      />
      {selectedSummary ? (
        <button type="button" onClick={clearSite}>Clear selection</button>
      ) : (
        <WorkspaceSurface className="p-5 text-sm text-[var(--vz-text-secondary)]">
          Choose a site to inspect link performance.
        </WorkspaceSurface>
      )}
    </main>
  );
}

export const LinksPage = Links;
```

Polish classes to match current pages.

- [ ] **Step 9: Verify and commit page shell**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/hooks/use-link.test.ts src/pages/Links.test.tsx src/components/layout/AppShell.test.tsx
corepack pnpm lint
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add frontend/src/hooks/use-link.ts frontend/src/hooks/use-link.test.ts frontend/src/pages/Links.tsx frontend/src/pages/Links.test.tsx frontend/src/components/link frontend/src/app/router.tsx frontend/src/components/layout/workspace-nav.ts frontend/src/components/layout/AppShell.test.tsx frontend/src/lib/openapi.json frontend/src/lib/api.generated.ts
git commit -m "feat: add link performance workspace"
git push origin codex/sceneops-pack-registry
```

## Gate 3: Detail Panels And Controls

### Task 3: Selected-Site Link Detail Controls

**Files:**

- Modify: `frontend/src/pages/Links.tsx`
- Create/Modify: `frontend/src/components/link/LinkPosturePanel.tsx`
- Create/Modify: `frontend/src/components/link/LinkConnectionsPanel.tsx`
- Create/Modify: `frontend/src/components/link/LinkBudgetPolicyPanel.tsx`
- Create/Modify: `frontend/src/components/link/LinkProbePanel.tsx`
- Create/Modify: `frontend/src/components/link/LinkQueuePanel.tsx`
- Create/Modify: `frontend/src/components/link/LinkActionDialogs.tsx`
- Modify: `frontend/src/pages/Links.test.tsx`

- [ ] **Step 1: Write failing detail panel test**

Add to `frontend/src/pages/Links.test.tsx`:

```tsx
test("selected site renders link posture connections budget probes queue and passport", async () => {
  mockLinkHooks({
    summaries: [createSummary({ site_id: "site-1", site_name: "North Gate" })],
    status: {
      link_state: "healthy",
      passport_hash: "abcdef123456",
      active_connection: { id: "connection-1", label: "Primary fiber", transport_kind: "fiber", status: "online" },
      queue_depth: { safety: 0, evidence: 1, telemetry: 0, bulk: 2 },
      latest_probe: { latency_ms: 42, throughput_mbps: 180, packet_loss_percent: 0.1, reachable: true, source: "packless-lab", recorded_at: "2026-06-07T10:00:00Z" },
      budget: { monthly_bytes: 500000000000, bulk_daily_bytes: 25000000000 },
    },
    connections: [{ id: "connection-1", label: "Primary fiber", transport_kind: "fiber", status: "online", metered: false }],
    probes: [{ id: "probe-1", latency_ms: 42, throughput_mbps: 180, packet_loss_percent: 0.1, reachable: true, source: "packless-lab", recorded_at: "2026-06-07T10:00:00Z" }],
    queue: [{ id: "queue-1", priority_lane: "evidence", byte_size: 8000000, status: "queued", source_object_type: "evidence_artifact" }],
    policies: { policy: { bulk_requires_unmetered: true } },
  });

  renderWithProviders(<Links />, { route: "/links?site=site-1" });

  expect(await screen.findByRole("heading", { name: /Current posture/i })).toBeInTheDocument();
  expect(screen.getByText(/Primary fiber/i)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Connections/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Budget and policy/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Probe history/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Transfer queue/i })).toBeInTheDocument();
  expect(screen.getByText(/abcdef12/i)).toBeInTheDocument();
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: FAIL because detail panels do not exist.

- [ ] **Step 2: Wire selected-site queries**

In `frontend/src/pages/Links.tsx`, call existing hooks with `selectedSiteId`:

```tsx
const status = useLinkSiteStatus(selectedSiteId);
const connections = useLinkConnections(selectedSiteId);
const budget = useLinkSiteBudget(selectedSiteId);
const policies = useLinkPolicies(selectedSiteId);
const probes = useLinkProbes(selectedSiteId);
const queue = useLinkSiteQueue(selectedSiteId);
```

Do not enable these hooks when no site is selected; existing hooks already use `enabled: Boolean(siteId)`.

- [ ] **Step 3: Implement posture panel**

Create `LinkPosturePanel.tsx` with:

- heading `Current posture`
- status badge from `link_state`
- active connection label
- latest probe latency, throughput, packet loss, reachable
- queue lane chips
- passport hash short form
- copy hash button using `navigator.clipboard.writeText` when available

Pass `isLoading={status.isLoading}` and `error={status.error}` into the panel. Render a compact skeleton while loading and a panel-local recoverable error when `error` is present.

- [ ] **Step 4: Implement connections panel and dialogs**

`LinkConnectionsPanel.tsx` should render connection rows and call:

- `useCreateLinkConnection`
- `useUpdateLinkConnection`
- `useDeleteLinkConnection`

`LinkActionDialogs.tsx` should expose a connection form with:

- label
- transport kind select: satellite, LTE, 5G, Wi-Fi, fiber, ethernet, other
- provider
- status
- priority rank
- availability scope
- metered checkbox
- monthly bytes
- bulk daily bytes
- expected downlink/uplink
- expected latency
- packet loss

Tests should assert create/edit/delete call the correct hook payloads.

- [ ] **Step 5: Implement budget and policy panel**

`LinkBudgetPolicyPanel.tsx` should call:

- `useUpdateLinkBudget`
- `useUpdateLinkPolicies`

The budget form has numeric monthly bytes and bulk daily bytes. The policy editor may use a textarea containing formatted JSON. On submit, parse JSON and send `{ policy: parsed }`. Invalid JSON shows inline error and does not call the mutation.

- [ ] **Step 6: Implement probe panel**

`LinkProbePanel.tsx` should list probes newest first and expose a record-probe dialog:

- connection selector, optional
- latency ms
- throughput Mbps
- packet loss percent
- reachable checkbox
- source

Call `useCreateLinkProbe`.

- [ ] **Step 7: Implement queue panel**

`LinkQueuePanel.tsx` should render queue items with:

- priority lane
- status
- byte size
- source object type
- pause reason
- last successful transfer

Actions:

- queued or failed item: Retry
- queued item: Pause
- paused item: Resume

Call `useRetryLinkQueueItem`, `usePauseLinkQueueItem`, and `useResumeLinkQueueItem`.

- [ ] **Step 8: Add mutation tests**

In `frontend/src/pages/Links.test.tsx`, add tests:

```tsx
test("connection form creates a core link connection for the selected site", async () => {
  const user = userEvent.setup();
  const createConnection = vi.fn().mockResolvedValue({});
  mockLinkHooks({ summaries: [createSummary({ site_id: "site-1" })], createConnection });

  renderWithProviders(<Links />, { route: "/links?site=site-1" });

  await user.click(await screen.findByRole("button", { name: /add connection/i }));
  await user.type(screen.getByLabelText(/connection label/i), "Primary fiber");
  await user.selectOptions(screen.getByLabelText(/transport kind/i), "fiber");
  await user.click(screen.getByRole("button", { name: /save connection/i }));

  expect(createConnection).toHaveBeenCalledWith(
    expect.objectContaining({ label: "Primary fiber", transport_kind: "fiber" }),
  );
});
```

Add equivalent tests for budget save, invalid policy JSON, record probe, and queue retry/pause/resume.

- [ ] **Step 9: Verify and commit controls**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
```

Expected: PASS.

Commit:

```bash
cd /Users/yann.moren/vision
git add frontend/src/pages/Links.tsx frontend/src/pages/Links.test.tsx frontend/src/components/link
git commit -m "feat: wire link workspace controls"
git push origin codex/sceneops-pack-registry
```

## Gate 4: FleetOps Deep Links And Full Verification

### Task 4: FleetOps Link Performance Deep Links

**Files:**

- Modify: `frontend/src/pages/FleetOpsVesselDetail.tsx`
- Modify: `frontend/src/pages/FleetOpsEvidence.tsx`
- Modify: `frontend/src/pages/FleetOpsSupport.tsx`
- Modify: `frontend/src/pages/FleetOpsOnboarding.tsx`
- Modify: `frontend/src/pages/FleetOpsVesselDetail.test.tsx`
- Modify: `frontend/src/pages/FleetOpsEvidence.test.tsx`
- Modify: `frontend/src/pages/FleetOpsSupport.test.tsx`
- Modify: `frontend/src/pages/FleetOpsOnboarding.test.tsx`

- [ ] **Step 1: Write failing FleetOps deep-link tests**

In each selected-scope FleetOps page test, assert:

```tsx
expect(
  screen.getByRole("link", { name: /open link performance/i }),
).toHaveAttribute("href", "/links?site=site-1");
```

For pages that start with no selected vessel/site, assert the link is absent or disabled until explicit selection.

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsVesselDetail.test.tsx src/pages/FleetOpsEvidence.test.tsx src/pages/FleetOpsSupport.test.tsx src/pages/FleetOpsOnboarding.test.tsx
```

Expected: FAIL because the deep links do not exist.

- [ ] **Step 2: Add deep links**

Add a small helper near FleetOps pages or inline:

```tsx
function linkPerformancePath(siteId?: string | null) {
  return siteId ? `/links?site=${encodeURIComponent(siteId)}` : "/links";
}
```

Render `Open Link Performance` only when the page has an explicit selected site or detail vessel site. Do not auto-select a FleetOps vessel just to show this link.

- [ ] **Step 3: Verify FleetOps deep links**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/FleetOpsVesselDetail.test.tsx src/pages/FleetOpsEvidence.test.tsx src/pages/FleetOpsSupport.test.tsx src/pages/FleetOpsOnboarding.test.tsx
```

Expected: PASS.

- [ ] **Step 4: Full verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py -q
python3 -m uv run ruff check src/argus/link tests/link tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py
python3 -m uv run mypy src/argus/link

cd /Users/yann.moren/vision/frontend
corepack pnpm lint
corepack pnpm build
corepack pnpm test --run
```

Expected: PASS.

- [ ] **Step 5: Browser smoke**

Start the frontend if no server is running:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm dev --host 127.0.0.1
```

Open `/links` in the in-app browser. Verify:

- unauthenticated users are redirected to sign-in
- authenticated session shows Link Performance
- no site is selected by default
- search filters site summaries
- page size changes between 10, 25, and 50
- selecting a site opens detail panels
- dialogs open and close without layout overlap

If the browser session is not authenticated, report that browser verification is auth-blocked and rely on tests for protected states.

- [ ] **Step 6: Commit and push final checkpoint**

```bash
cd /Users/yann.moren/vision
git add frontend/src/pages/FleetOpsVesselDetail.tsx frontend/src/pages/FleetOpsEvidence.tsx frontend/src/pages/FleetOpsSupport.tsx frontend/src/pages/FleetOpsOnboarding.tsx frontend/src/pages/FleetOpsVesselDetail.test.tsx frontend/src/pages/FleetOpsEvidence.test.tsx frontend/src/pages/FleetOpsSupport.test.tsx frontend/src/pages/FleetOpsOnboarding.test.tsx
git commit -m "test: validate core link workspace"
git push origin codex/sceneops-pack-registry
```

## Plan Self-Review

- Spec coverage: backend summary, frontend route/nav, explicit site focus, 10/25/50 pagination, selected-site panels, mutations, FleetOps deep links, and packless constraints are covered.
- Completeness scan: every step names concrete paths, commands, code snippets, and expected outcomes.
- Type consistency: route names, hook names, and component names are consistent across tasks.
- Scope check: this plan only adds core link performance UI and one core summary route; it does not implement traffic/public-space, home-lab packs, proprietary SDKs, payment/accounting integrations, or runtime semantic changes.
