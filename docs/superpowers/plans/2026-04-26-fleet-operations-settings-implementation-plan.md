# Fleet Operations and Settings UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder Settings page with a real Fleet / Operations surface that exposes worker/bootstrap state, camera assignments, delivery diagnostics, and a UI-led production story for central and edge workers.

**Architecture:** Build a read-mostly operations API on top of the existing `EdgeNode`, camera, and worker-config services, then replace the current placeholder route with a structured operations page. Keep process supervision with infrastructure, but make the UI own bootstrap, desired assignment visibility, and operator-safe diagnostics.

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, TanStack Query, Vitest, React Testing Library, pytest.

---

## File Structure

- Create: `backend/src/argus/api/v1/operations.py`
  - Fleet and bootstrap endpoints.
- Modify: `backend/src/argus/api/contracts.py`
  - Add operations/fleet response models.
- Modify: `backend/src/argus/services/app.py`
  - Add an `OperationsService` that aggregates edge nodes, cameras, worker config, and delivery diagnostics.
- Test: `backend/tests/api/test_app.py`
- Test: `backend/tests/services/test_stream_service.py`
- Create: `frontend/src/hooks/use-operations.ts`
  - Query hooks for fleet status and bootstrap material.
- Modify: `frontend/src/pages/Settings.tsx`
  - Replace the placeholder with the Fleet / Operations page.
- Modify: `frontend/src/components/layout/TopNav.tsx`
  - Retitle the nav affordance if needed to `Operations` while keeping route compatibility.
- Test: `frontend/src/pages/Settings.test.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`

### Task 1: Add a backend operations aggregate service

**Files:**
- Create: `backend/src/argus/api/v1/operations.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/api/test_app.py`

- [ ] **Step 1: Write the failing backend tests for the operations summary**

```python
@pytest.mark.asyncio
async def test_operations_fleet_lists_nodes_cameras_and_health(client, admin_headers):
    response = await client.get("/api/v1/operations/fleet", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert "central_workers" in payload
    assert "edge_nodes" in payload
    assert "delivery_diagnostics" in payload
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `python3 -m uv run pytest backend/tests/api/test_app.py -q`

Expected: FAIL because the operations route does not exist.

- [ ] **Step 3: Add the operations response models and aggregate service**

```python
class FleetNodeSummary(BaseModel):
    id: UUID
    hostname: str
    runtime_profile: str | None = None
    status: Literal["healthy", "degraded", "offline"]
    last_seen_at: datetime | None = None
    assigned_camera_ids: list[UUID] = Field(default_factory=list)


class FleetOverviewResponse(BaseModel):
    central_workers: list[FleetNodeSummary]
    edge_nodes: list[FleetNodeSummary]
    delivery_diagnostics: list[dict[str, object]]
```

```python
@router.get("/fleet", response_model=FleetOverviewResponse)
async def get_fleet_overview(...):
    return await services.operations.get_fleet_overview(tenant_context)
```

- [ ] **Step 4: Re-run the backend tests**

Run: `python3 -m uv run pytest backend/tests/api/test_app.py -q`

Expected: PASS for the new operations route.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/api/v1/operations.py backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/tests/api/test_app.py
git commit -m "feat: add backend fleet operations overview"
```

### Task 2: Expose operator bootstrap material instead of shell-only flows

**Files:**
- Modify: `backend/src/argus/api/v1/operations.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/api/test_app.py`

- [ ] **Step 1: Write the failing backend tests for bootstrap creation**

```python
@pytest.mark.asyncio
async def test_operations_bootstrap_returns_short_lived_install_material(client, admin_headers, site_id):
    response = await client.post(
        "/api/v1/operations/bootstrap",
        headers=admin_headers,
        json={"site_id": str(site_id), "hostname": "edge-kit-01", "version": "0.1.0"},
    )

    assert response.status_code == 201
    assert "install_command" in response.json()
    assert "api_key" in response.json()
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `python3 -m uv run pytest backend/tests/api/test_app.py -q`

Expected: FAIL because the bootstrap route does not exist.

- [ ] **Step 3: Add a bootstrap endpoint that wraps the existing edge registration flow**

```python
@router.post("/bootstrap", response_model=EdgeRegisterResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap_edge_node(payload: EdgeRegisterRequest, ...):
    return await services.edge.register_edge_node(tenant_context, payload)
```

```python
class FleetBootstrapResponse(BaseModel):
    edge_node_id: UUID
    api_key: str
    install_command: str
    overlay_network_hints: dict[str, object] = Field(default_factory=dict)
```

- [ ] **Step 4: Re-run the backend tests**

Run: `python3 -m uv run pytest backend/tests/api/test_app.py -q`

Expected: PASS with bootstrap/install material exposed via the API.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/api/v1/operations.py backend/src/argus/services/app.py backend/tests/api/test_app.py
git commit -m "feat: expose ui bootstrap flow for edge workers"
```

### Task 3: Replace the placeholder Settings page with Fleet / Operations

**Files:**
- Create: `frontend/src/hooks/use-operations.ts`
- Modify: `frontend/src/pages/Settings.tsx`
- Test: `frontend/src/pages/Settings.test.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: Write the failing frontend tests for the operations page**

```tsx
test("renders fleet sections instead of placeholder copy", async () => {
  renderSettingsPage();

  expect(await screen.findByRole("heading", { name: /fleet and operations/i })).toBeInTheDocument();
  expect(screen.getByText(/bootstrap an edge node/i)).toBeInTheDocument();
  expect(screen.queryByText(/prompt 7 uses this route as a stable anchor/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx src/components/layout/AppShell.test.tsx`

Expected: FAIL because the route still renders placeholder text.

- [ ] **Step 3: Add operations hooks and render real sections**

```ts
export function useFleetOverview() {
  return useQuery({
    queryKey: ["operations", "fleet"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/operations/fleet");
      if (error || !data) throw toApiError(error, "Failed to load fleet overview.");
      return data;
    },
  });
}
```

```tsx
<section>
  <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">Fleet</p>
  <h2 className="mt-3 text-3xl font-semibold text-[#f4f8ff]">Fleet and operations.</h2>
  <p className="mt-3 text-sm text-[#93a7c5]">Bootstrap nodes, verify worker health, and inspect delivery truth from one place.</p>
</section>
```

- [ ] **Step 4: Re-run the frontend tests**

Run: `corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx src/components/layout/AppShell.test.tsx`

Expected: PASS with the placeholder removed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/use-operations.ts frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx frontend/src/components/layout/AppShell.test.tsx
git commit -m "feat: replace placeholder settings page with fleet operations ui"
```

### Task 4: Add worker assignment and delivery diagnostics panels

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `frontend/src/pages/Settings.test.tsx`

- [ ] **Step 1: Write the failing tests for diagnostics panels**

```tsx
test("shows native availability and assigned cameras in operations panels", async () => {
  mockFleetOverview({
    delivery_diagnostics: [{ camera_name: "CAMERA1", native_status: "unavailable", reason: "processed_stream_only" }],
    edge_nodes: [{ hostname: "jetson-1", assigned_camera_ids: ["cam-1"], status: "healthy" }],
  });

  renderSettingsPage();

  expect(await screen.findByText(/camera1/i)).toBeInTheDocument();
  expect(screen.getByText(/processed stream only/i)).toBeInTheDocument();
  expect(screen.getByText(/jetson-1/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the failing tests**

Run: `corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx`

Expected: FAIL because the operations page does not yet show diagnostics and assignments.

- [ ] **Step 3: Add the diagnostics and assignment panels**

```tsx
<section className="grid gap-4 xl:grid-cols-2">
  <FleetAssignmentsPanel nodes={data.edge_nodes} />
  <DeliveryDiagnosticsPanel diagnostics={data.delivery_diagnostics} />
</section>
```

- [ ] **Step 4: Re-run the settings tests**

Run: `corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx`

Expected: PASS with worker assignment and delivery diagnostics panels.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx backend/src/argus/api/contracts.py backend/src/argus/services/app.py
git commit -m "feat: add worker assignment and delivery diagnostics panels"
```

### Task 5: Verification

**Files:**
- Test: `backend/tests/api/test_app.py`
- Test: `frontend/src/pages/Settings.test.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: Run focused verification**

Run:

```bash
python3 -m uv run pytest backend/tests/api/test_app.py -q
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx src/components/layout/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Build the frontend**

Run: `corepack pnpm --dir frontend build`

Expected: PASS.

- [ ] **Step 3: Commit final polish**

```bash
git add docs/superpowers/specs/2026-04-26-operator-setup-history-delivery-hardening-design.md
git commit -m "docs: record fleet operations implementation completion"
```
