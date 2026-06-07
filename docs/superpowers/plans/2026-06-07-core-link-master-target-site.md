# Core Link Master Target Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Vezor master visible as a target-only Link Performance site so every edge can probe it and operators can inspect edge-to-master health.

**Architecture:** Persist the master as a `control_plane` site, keep edge sites as the only configurable link sources, and store edge-originated samples with both source `site_id` and target `target_site_id`. The UI renders edge sites with the existing operational panels and renders the master with a target observability view.

**Tech Stack:** FastAPI/Pydantic, SQLAlchemy/Alembic, React/TypeScript, TanStack Query, pytest, Vitest, Ruff, mypy.

---

## File Structure

- Modify `backend/src/argus/models/tables.py`: add `Site.site_kind`.
- Modify `backend/src/argus/api/contracts.py`: add `site_kind` to site responses and add Link role/capability fields.
- Create `backend/src/argus/migrations/versions/0040_core_link_master_target_site.py`: add site kind and target site probe columns.
- Modify `backend/src/argus/services/app.py`: create/repair the control-plane site during master bootstrap, return site kind, and expose Link site capability helpers.
- Modify `backend/src/argus/link/contracts.py`: add `target_site_id` and summary role/capabilities.
- Modify `backend/src/argus/link/tables.py`: add `target_site_id` to `LinkHealthProbe`.
- Modify `backend/src/argus/link/service.py`: persist/query target site samples and aggregate master target status.
- Modify `backend/src/argus/link/api.py`: include master in summaries, allow read-only master view routes, reject local master config, and accept edge-to-master samples.
- Modify `frontend/src/components/link/types.ts`: add role/capability types and `target_site_id`.
- Modify `frontend/src/pages/Links.tsx`: branch edge vs control-plane selected views.
- Create `frontend/src/components/link/LinkMasterTargetPanel.tsx`: aggregate master target view.
- Modify `frontend/src/components/link/LinkSiteSelector.tsx`: show `Control plane target` role badge.
- Modify `frontend/src/components/link/LinkActionDialogs.tsx`: add `Vezor Master` target preset for edge sites.
- Test `backend/tests/api/test_link_routes.py`, `backend/tests/services/test_site_service.py`, `backend/tests/link/test_link_service.py`, and `frontend/src/pages/Links.test.tsx`.

## Task 1: Persist Site Role And Target Site Probe Fields

**Files:**
- Modify: `backend/src/argus/models/tables.py`
- Modify: `backend/src/argus/link/tables.py`
- Create: `backend/src/argus/migrations/versions/0040_core_link_master_target_site.py`
- Test: `backend/tests/link/test_link_service.py`

- [ ] **Step 1: Write failing schema contract tests**

Add to `backend/tests/link/test_link_service.py`:

```python
def test_core_link_master_target_migration_adds_site_kind_and_target_site_id() -> None:
    migration = Path("src/argus/migrations/versions/0040_core_link_master_target_site.py")
    text = migration.read_text()

    assert "site_kind" in text
    assert "target_site_id" in text
    assert "ix_link_health_probes_tenant_target_site_recorded" in text
    assert "control_plane" in text
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_core_link_master_target_migration_adds_site_kind_and_target_site_id -q
```

Expected: FAIL because migration `0040_core_link_master_target_site.py` does not exist.

- [ ] **Step 3: Add model fields and migration**

In `backend/src/argus/models/tables.py`, add:

```python
site_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="edge")
```

In `backend/src/argus/link/tables.py`, add to `LinkHealthProbe`:

```python
target_site_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("sites.id"),
    nullable=True,
)
```

Also add an index:

```python
Index(
    "ix_link_health_probes_tenant_target_site_recorded",
    "tenant_id",
    "target_site_id",
    "recorded_at",
)
```

Create `backend/src/argus/migrations/versions/0040_core_link_master_target_site.py`:

```python
"""core link master target site

Revision ID: 0040_core_link_master_target_site
Revises: 0039_core_link_edge_agent
Create Date: 2026-06-07 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040_core_link_master_target_site"
down_revision: str | Sequence[str] | None = "0039_core_link_edge_agent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sites",
        sa.Column("site_kind", sa.String(length=32), nullable=False, server_default="edge"),
    )
    op.create_check_constraint(
        "ck_sites_site_kind",
        "sites",
        "site_kind in ('edge', 'control_plane')",
    )
    op.add_column(
        "link_health_probes",
        sa.Column("target_site_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_link_health_probes_target_site_id_sites",
        "link_health_probes",
        "sites",
        ["target_site_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_link_health_probes_tenant_target_site_recorded",
        "link_health_probes",
        ["tenant_id", "target_site_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_link_health_probes_tenant_target_site_recorded", table_name="link_health_probes")
    op.drop_constraint(
        "fk_link_health_probes_target_site_id_sites",
        "link_health_probes",
        type_="foreignkey",
    )
    op.drop_column("link_health_probes", "target_site_id")
    op.drop_constraint("ck_sites_site_kind", "sites", type_="check")
    op.drop_column("sites", "site_kind")
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_core_link_master_target_migration_adds_site_kind_and_target_site_id -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/models/tables.py backend/src/argus/link/tables.py backend/src/argus/migrations/versions/0040_core_link_master_target_site.py backend/tests/link/test_link_service.py
git commit -m "feat: add core link site roles"
```

## Task 2: Site Service Control-Plane Site Support

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_site_service.py`

- [ ] **Step 1: Write failing service tests**

Add to `backend/tests/services/test_site_service.py`:

```python
@pytest.mark.asyncio
async def test_site_response_exposes_site_kind() -> None:
    site = Site(
        id=uuid4(),
        tenant_id=uuid4(),
        name="Vezor Master",
        description=None,
        tz="UTC",
        geo_point=None,
        site_kind="control_plane",
        created_at=datetime(2026, 6, 7, tzinfo=UTC),
    )

    response = app_services._site_to_response(site)

    assert response.site_kind == "control_plane"
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_site_service.py::test_site_response_exposes_site_kind -q
```

Expected: FAIL because `SiteResponse` has no `site_kind`.

- [ ] **Step 3: Add site kind contracts and service helpers**

In `backend/src/argus/api/contracts.py`, add:

```python
SiteKind = Literal["edge", "control_plane"]
```

Add to `SiteResponse`:

```python
site_kind: SiteKind = "edge"
```

Do not add `site_kind` to public `SiteCreate` or `SiteUpdate`; normal operator-created sites remain edge sites. In `backend/src/argus/services/app.py`, update site creation to set `site_kind="edge"` explicitly and update `_site_to_response` to include `site_kind`.

Add helper constants:

```python
CONTROL_PLANE_SITE_NAME = "Vezor Master"
CONTROL_PLANE_SITE_KIND = "control_plane"
EDGE_SITE_KIND = "edge"
```

Add helper:

```python
async def _ensure_control_plane_site(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    now: datetime,
) -> Site:
    statement = (
        select(Site)
        .where(Site.tenant_id == tenant_id, Site.site_kind == CONTROL_PLANE_SITE_KIND)
        .order_by(Site.created_at.asc())
        .limit(1)
    )
    existing = (await session.execute(statement)).scalar_one_or_none()
    if isinstance(existing, Site):
        return existing
    site = Site(
        tenant_id=tenant_id,
        name=CONTROL_PLANE_SITE_NAME,
        description="Vezor control-plane probe target",
        tz="UTC",
        geo_point=None,
        site_kind=CONTROL_PLANE_SITE_KIND,
    )
    _ensure_identity_and_timestamps(site, now=now)
    session.add(site)
    await _flush_if_available(session)
    return site
```

Call `_ensure_control_plane_site(...)` from `DeploymentNodeService.complete_master_bootstrap` after the tenant is known.

Add a Link-specific site listing method:

```python
async def list_link_performance_sites(
    self,
    tenant_context: TenantContext,
) -> list[SiteResponse]:
    async with self.session_factory() as session:
        statement = (
            select(Site)
            .outerjoin(EdgeNode, EdgeNode.site_id == Site.id)
            .where(Site.tenant_id == tenant_context.tenant_id)
            .where(
                or_(
                    Site.site_kind == CONTROL_PLANE_SITE_KIND,
                    EdgeNode.id.is_not(None),
                )
            )
            .distinct()
            .order_by(Site.site_kind.desc(), Site.name)
        )
        sites = (await session.execute(statement)).scalars().all()
    return [_site_to_response(site) for site in sites]
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_site_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/tests/services/test_site_service.py
git commit -m "feat: add control plane site support"
```

## Task 3: Link Service Source And Target Probe Semantics

**Files:**
- Modify: `backend/src/argus/link/contracts.py`
- Modify: `backend/src/argus/link/service.py`
- Test: `backend/tests/link/test_link_service.py`

- [ ] **Step 1: Write failing service tests**

Add to `backend/tests/link/test_link_service.py`:

```python
def test_record_probe_keeps_source_site_and_target_site() -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    edge_site_id = UUID("00000000-0000-4000-8000-000000000002")
    master_site_id = UUID("00000000-0000-4000-8000-000000000010")
    service = LinkService()

    probe = service.record_probe(
        tenant_id=tenant_id,
        site_id=edge_site_id,
        target_site_id=master_site_id,
        latency_ms=31,
        throughput_mbps=0,
        packet_loss_percent=0,
        reachable=True,
        source="edge_agent:edge-a",
        target_id="vezor-master-https",
        target_label="Vezor Master API",
        target_address="https://vezor.example.com/api/v1/health",
        probe_type="https",
        source_type="edge_agent",
        sample_kind="automated",
    )

    assert probe.site_id == edge_site_id
    assert probe.target_site_id == master_site_id
```

Add:

```python
def test_list_target_site_probes_returns_inverse_master_view() -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    edge_site_id = UUID("00000000-0000-4000-8000-000000000002")
    other_edge_site_id = UUID("00000000-0000-4000-8000-000000000003")
    master_site_id = UUID("00000000-0000-4000-8000-000000000010")
    service = LinkService()
    service.record_probe(
        tenant_id=tenant_id,
        site_id=edge_site_id,
        target_site_id=master_site_id,
        latency_ms=31,
        throughput_mbps=0,
        packet_loss_percent=0,
        reachable=True,
        source="edge_agent:edge-a",
    )
    service.record_probe(
        tenant_id=tenant_id,
        site_id=other_edge_site_id,
        target_site_id=None,
        latency_ms=99,
        throughput_mbps=0,
        packet_loss_percent=0,
        reachable=True,
        source="edge_agent:edge-b",
    )

    probes = service.list_target_site_probes(
        tenant_id=tenant_id,
        target_site_id=master_site_id,
    )

    assert len(probes) == 1
    assert probes[0].site_id == edge_site_id
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_record_probe_keeps_source_site_and_target_site tests/link/test_link_service.py::test_list_target_site_probes_returns_inverse_master_view -q
```

Expected: FAIL because probe records do not have `target_site_id`.

- [ ] **Step 3: Implement source and target fields**

In `backend/src/argus/link/contracts.py`, add to `LinkHealthProbeRecord`:

```python
target_site_id: UUID | None = None
```

In `LinkService.record_probe` and `LinkService.arecord_probe`, add parameter:

```python
target_site_id: UUID | None = None
```

Store it in memory records and SQL rows.

Add memory method:

```python
def list_target_site_probes(
    self,
    *,
    tenant_id: UUID,
    target_site_id: UUID,
) -> list[LinkHealthProbeRecord]:
    self._ensure_memory_mode()
    return [
        probe
        for probe in self._probes
        if probe.tenant_id == tenant_id
        and probe.target_site_id == target_site_id
        and probe.deleted_at is None
    ]
```

Add async SQL method:

```python
async def alist_target_site_probes(
    self,
    *,
    tenant_id: UUID,
    target_site_id: UUID,
) -> list[LinkHealthProbeRecord]:
    if self.session_factory is None:
        return self.list_target_site_probes(
            tenant_id=tenant_id,
            target_site_id=target_site_id,
        )
    async with self.session_factory() as session:
        statement = (
            select(LinkHealthProbe)
            .where(
                LinkHealthProbe.tenant_id == tenant_id,
                LinkHealthProbe.target_site_id == target_site_id,
                LinkHealthProbe.deleted_at.is_(None),
            )
            .order_by(LinkHealthProbe.recorded_at.desc())
        )
        rows = (await session.execute(statement)).scalars().all()
    return [_probe_record(row) for row in rows if isinstance(row, LinkHealthProbe)]
```

Update `_probe_record` to include `target_site_id`.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/contracts.py backend/src/argus/link/service.py backend/tests/link/test_link_service.py
git commit -m "feat: track link probe target sites"
```

## Task 4: Link API Role-Aware Summaries And Guards

**Files:**
- Modify: `backend/src/argus/link/api.py`
- Test: `backend/tests/api/test_link_routes.py`

- [ ] **Step 1: Write failing API tests**

Update the fake site service in `backend/tests/api/test_link_routes.py` so it returns:

```python
SiteResponse(
    id=MASTER_SITE_ID,
    tenant_id=tenant_context.tenant_id,
    name="Vezor Master",
    description=None,
    tz="UTC",
    geo_point=None,
    site_kind="control_plane",
    created_at=datetime.now(tz=UTC),
)
```

Add:

```python
@pytest.mark.asyncio
async def test_link_summary_includes_master_as_control_plane_target(client: AsyncClient) -> None:
    response = await client.get("/api/v1/link/sites/summary")

    assert response.status_code == 200
    master = next(item for item in response.json() if item["site_id"] == str(MASTER_SITE_ID))
    assert master["site_role"] == "control_plane"
    assert master["capabilities"]["can_configure_links"] is False
    assert master["capabilities"]["can_receive_edge_samples"] is True
```

Add:

```python
@pytest.mark.asyncio
async def test_edge_sample_can_target_master_site(client: AsyncClient) -> None:
    created = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/connections",
        json={
            "label": "Primary ISP",
            "transport_kind": "ethernet",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "always",
            "metered": False,
            "metadata": {
                "monitoring_targets": [
                    {
                        "id": "vezor-master-https",
                        "label": "Vezor Master API",
                        "address": "https://vezor.example.com/api/v1/health",
                        "target_site_id": str(MASTER_SITE_ID),
                        "probe_type": "https",
                        "purpose": "vezor_control",
                        "monitoring": {
                            "enabled": True,
                            "source_type": "edge_agent",
                            "interval_seconds": 300,
                        },
                    }
                ]
            },
        },
    )
    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/vezor-master-https/edge-samples",
        json={
            "agent_id": "edge-a",
            "agent_label": "Edge A",
            "method": "icmp_sequence",
            "packet_count": 20,
            "packets_received": 20,
            "latency_ms": 31,
        },
    )
    master_history = await client.get(f"/api/v1/link/sites/{MASTER_SITE_ID}/probes")

    assert created.status_code == 201
    assert response.status_code == 201
    assert response.json()["target_site_id"] == str(MASTER_SITE_ID)
    assert master_history.status_code == 200
    assert master_history.json()[0]["site_id"] == str(KNOWN_SITE_ID)
```

Keep the existing rejection test for master connection creation.

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py::test_link_summary_includes_master_as_control_plane_target tests/api/test_link_routes.py::test_edge_sample_can_target_master_site -q
```

Expected: FAIL because summaries do not expose roles and edge samples do not store `target_site_id`.

- [ ] **Step 3: Implement role-aware API**

In `LinkSiteSummaryResponse`, add:

```python
site_role: Literal["edge", "control_plane"] = "edge"
capabilities: dict[str, bool] = Field(default_factory=dict)
```

Add helper:

```python
def _link_site_capabilities(site_role: str) -> dict[str, bool]:
    is_edge = site_role == "edge"
    return {
        "can_configure_links": is_edge,
        "can_configure_targets": is_edge,
        "can_record_manual_samples": is_edge,
        "can_receive_edge_samples": True,
        "can_show_queue": is_edge,
        "can_show_budget": is_edge,
        "can_show_policy": is_edge,
    }
```

Change summary loading to include edge sites and control-plane sites. A simple implementation is:

```python
sites = await services.sites.list_link_performance_sites(tenant_context)
```

where `list_link_performance_sites` returns edge sites plus control-plane sites.

Update `_ensure_link_edge_site` into two helpers:

```python
async def _ensure_observable_link_site(...) -> SiteResponse:
    site = await services.sites.get_site(tenant_context, site_id)
    if site.site_kind not in {"edge", "control_plane"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Core Link can only inspect link performance sites.")
    return site
```

```python
async def _ensure_configurable_edge_site(...) -> SiteResponse:
    site = await _ensure_observable_link_site(...)
    if site.site_kind != "edge" or not await services.sites.is_edge_site(tenant_context, site_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Core Link can only be configured for edge sites.")
    return site
```

For `GET /sites/{site_id}/probes`, if `site.site_kind == "control_plane"`, return `services.link.alist_target_site_probes(...)`.

In edge sample handling, read `target_site_id` from target metadata and pass it to `arecord_probe`.

Update `_probe_payload`:

```python
"target_site_id": str(probe.target_site_id) if probe.target_site_id is not None else None,
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/api.py backend/tests/api/test_link_routes.py
git commit -m "feat: expose master as link target site"
```

## Task 5: Frontend Role-Aware Link Performance UI

**Files:**
- Modify: `frontend/src/components/link/types.ts`
- Modify: `frontend/src/components/link/LinkSiteSelector.tsx`
- Modify: `frontend/src/pages/Links.tsx`
- Create: `frontend/src/components/link/LinkMasterTargetPanel.tsx`
- Test: `frontend/src/pages/Links.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Add a summary mock in `frontend/src/pages/Links.test.tsx`:

```ts
const masterSummary = {
  site_id: "00000000-0000-4000-8000-000000000010",
  site_name: "Vezor Master",
  site_tz: "UTC",
  site_role: "control_plane",
  capabilities: {
    can_configure_links: false,
    can_configure_targets: false,
    can_record_manual_samples: false,
    can_receive_edge_samples: true,
    can_show_queue: false,
    can_show_budget: false,
    can_show_policy: false,
  },
  link_state: "healthy",
  active_connection: null,
  connection_count: 0,
  metered_connection_count: 0,
  latest_probe: null,
  queue_depth: {},
  queued_bytes: 0,
  budget: null,
  last_sync_at: null,
  passport_hash: "master-passport",
};
```

Add test:

```ts
it("renders the master as a target-only control plane view", async () => {
  server.use(
    http.get("*/api/v1/link/sites/summary", () =>
      HttpResponse.json([masterSummary]),
    ),
    http.get("*/api/v1/link/sites/:siteId/status", () =>
      HttpResponse.json({ link_state: "healthy", passport_hash: "master-passport" }),
    ),
    http.get("*/api/v1/link/sites/:siteId/probes", () =>
      HttpResponse.json([
        {
          id: "probe-1",
          tenant_id: "tenant",
          site_id: "00000000-0000-4000-8000-000000000002",
          target_site_id: masterSummary.site_id,
          latency_ms: 31,
          throughput_mbps: 0,
          packet_loss_percent: 0,
          reachable: true,
          source: "edge_agent:edge-a",
          source_type: "edge_agent",
          sample_kind: "automated",
          target_id: "vezor-master-https",
          target_label: "Vezor Master API",
          target_address: "https://vezor.example.com/api/v1/health",
          probe_type: "https",
          recorded_at: "2026-06-07T10:00:00Z",
          deleted_at: null,
          measurement_metadata: {},
        },
      ]),
    ),
  );

  render(<Links />);
  await userEvent.click(await screen.findByRole("button", { name: /select vezor master/i }));

  expect(screen.getByText("Control plane target")).toBeInTheDocument();
  expect(screen.getByText("Edge-to-master reachability")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /add link path/i })).not.toBeInTheDocument();
  expect(screen.queryByText("Budget and policy")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: FAIL because the UI has no master target branch.

- [ ] **Step 3: Add role types and selector labels**

In `frontend/src/components/link/types.ts`, add:

```ts
export type LinkSiteRole = "edge" | "control_plane";
export type LinkSiteCapabilities = {
  can_configure_links: boolean;
  can_configure_targets: boolean;
  can_record_manual_samples: boolean;
  can_receive_edge_samples: boolean;
  can_show_queue: boolean;
  can_show_budget: boolean;
  can_show_policy: boolean;
};
```

Add helpers:

```ts
export function linkSiteRole(value: unknown): LinkSiteRole {
  return value === "control_plane" ? "control_plane" : "edge";
}

export function linkSiteRoleLabel(value: LinkSiteRole) {
  return value === "control_plane" ? "Control plane target" : "Edge site";
}
```

In `LinkSiteSelector.tsx`, show `linkSiteRoleLabel(linkSiteRole(summary.site_role))` alongside the state.

- [ ] **Step 4: Add master target panel**

Create `frontend/src/components/link/LinkMasterTargetPanel.tsx`:

```tsx
import { Activity, RadioTower } from "lucide-react";

import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { probeSampleSourceLabel, textValue } from "@/components/link/types";

type LinkMasterTargetPanelProps = {
  probes: unknown[];
};

export function LinkMasterTargetPanel({ probes }: LinkMasterTargetPanelProps) {
  return (
    <WorkspaceSurface className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Control plane target
          </p>
          <h2 className="mt-2 font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
            Edge-to-master reachability
          </h2>
        </div>
        <RadioTower className="size-5 text-[var(--vz-text-secondary)]" aria-hidden="true" />
      </div>
      <div className="mt-4 grid gap-3">
        {probes.length > 0 ? (
          probes.map((probe, index) => (
            <div
              key={String((probe as { id?: unknown }).id ?? index)}
              className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] p-4"
            >
              <p className="font-semibold text-[var(--vz-text-primary)]">
                {textValue((probe as { target_label?: unknown }).target_label, "Vezor Master")}
              </p>
              <p className="mt-1 text-sm text-[var(--vz-text-secondary)]">
                {probeSampleSourceLabel(probe)}
              </p>
              <p className="mt-3 flex items-center gap-2 text-sm text-[var(--vz-text-primary)]">
                <Activity className="size-4" aria-hidden="true" />
                {String((probe as { latency_ms?: unknown }).latency_ms ?? 0)} ms /
                {" "}
                {String((probe as { packet_loss_percent?: unknown }).packet_loss_percent ?? 0)}% loss
              </p>
            </div>
          ))
        ) : (
          <p className="text-sm text-[var(--vz-text-secondary)]">
            No edge-to-master samples recorded yet.
          </p>
        )}
      </div>
    </WorkspaceSurface>
  );
}
```

- [ ] **Step 5: Branch the Links page by role**

In `frontend/src/pages/Links.tsx`, import `linkSiteRole` and `LinkMasterTargetPanel`. When `selectedSummary` is control plane, render:

```tsx
<div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
  <LinkPosturePanel
    status={status.data}
    isLoading={status.isLoading}
    error={status.error}
    onClearSelection={clearSite}
  />
  <LinkMasterTargetPanel probes={probes.data ?? []} />
</div>
```

When role is edge, render the existing panels.

- [ ] **Step 6: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/components/link/types.ts frontend/src/components/link/LinkSiteSelector.tsx frontend/src/components/link/LinkMasterTargetPanel.tsx frontend/src/pages/Links.tsx frontend/src/pages/Links.test.tsx
git commit -m "feat: add master link target view"
```

## Task 6: Edge-Site Vezor Master Target Preset

**Files:**
- Modify: `frontend/src/components/link/LinkActionDialogs.tsx`
- Modify: `frontend/src/components/link/types.ts`
- Test: `frontend/src/pages/Links.test.tsx`

- [ ] **Step 1: Write failing preset test**

Add to `frontend/src/pages/Links.test.tsx`:

```ts
it("adds a Vezor Master monitoring target from a preset", async () => {
  render(<Links />);
  await userEvent.click(await screen.findByRole("button", { name: /add link path/i }));
  await userEvent.click(screen.getByRole("button", { name: /add monitoring target/i }));
  await userEvent.selectOptions(screen.getByLabelText(/target preset/i), "vezor_master");

  expect(screen.getByLabelText(/target label/i)).toHaveValue("Vezor Master API");
  expect(screen.getByLabelText(/purpose/i)).toHaveValue("vezor_control");
  expect(screen.getByLabelText(/monitoring source/i)).toHaveValue("edge_agent");
});
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx -t "Vezor Master monitoring target"
```

Expected: FAIL because no preset selector exists.

- [ ] **Step 3: Implement preset**

In `types.ts`, add:

```ts
export type MonitoringTargetPreset = "custom" | "vezor_master";
```

In `LinkActionDialogs.tsx`, add a preset select labelled `Target preset`. When `vezor_master` is selected, update the current target draft:

```ts
{
  id: "vezor-master-https",
  label: "Vezor Master API",
  address: "/api/v1/health",
  probe_type: "https",
  purpose: "vezor_control",
  monitoring: {
    enabled: true,
    source_type: "edge_agent",
    interval_seconds: 300,
  },
  loss_method: "icmp_sequence",
  loss_packet_count: 20,
}
```

The backend should replace the relative address with the configured public master URL when it generates an edge-agent command.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/components/link/LinkActionDialogs.tsx frontend/src/components/link/types.ts frontend/src/pages/Links.test.tsx
git commit -m "feat: add vezor master target preset"
```

## Task 7: Final Verification

**Files:**
- No code changes unless verification finds an issue.

- [ ] **Step 1: Run backend verification**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py tests/link/test_link_service.py tests/services/test_site_service.py -q
python3 -m uv run ruff check src/argus/link src/argus/services/app.py tests/api/test_link_routes.py tests/link/test_link_service.py tests/services/test_site_service.py
python3 -m uv run mypy src/argus/link
```

Expected: all commands exit 0.

- [ ] **Step 2: Run frontend verification**

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
corepack pnpm build
```

Expected: all commands exit 0.

- [ ] **Step 3: Run whitespace and status checks**

```bash
cd /Users/yann.moren/vision
git diff --check
git status --short
```

Expected: no whitespace errors. Only intended files should be staged or modified.

- [ ] **Step 4: Commit verification fixes if needed**

If verification required fixes:

```bash
cd /Users/yann.moren/vision
git add <fixed-files>
git commit -m "fix: stabilize master link target site"
```

If no fixes were needed, do not create an empty commit.

## Self-Review

- Spec coverage: site role, master target visibility, edge-originated samples, API guards, UI branching, and Vezor Master preset are covered by Tasks 1 through 6.
- Placeholder scan: no task uses placeholder language.
- Type consistency: `site_kind`, `site_role`, `capabilities`, and `target_site_id` are consistently named across backend and frontend tasks.
