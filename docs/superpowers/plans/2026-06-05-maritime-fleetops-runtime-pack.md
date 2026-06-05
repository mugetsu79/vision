# Maritime FleetOps Runtime Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full working Maritime FleetOps product: global link/fleet/billing/support baselines, the `argus.maritime` runtime pack, FleetOps UI, evidence export, billing exports, support diagnostics, onboarding, and end-to-end smoke coverage.

**Architecture:** Core baselines live in domain-neutral modules under `argus.link`, `argus.fleet`, `argus.billing`, and `argus.support`; the maritime pack lives under `argus.maritime` and references core IDs without moving vessel/voyage/port-call nouns into core contracts. APIs are routed through `/api/v1/link`, `/api/v1/fleet`, `/api/v1/billing`, `/api/v1/support`, and `/api/v1/maritime`, with generated OpenAPI types consumed by the existing React/TanStack Query frontend.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async, Alembic, PostgreSQL, NATS JetStream, pytest, pytest-asyncio, httpx ASGI transport, React 19, TypeScript, TanStack Query, Vitest, Playwright, uv, pnpm.

---

## Non-Negotiable Constraints

Every task must preserve the spec's cross-cutting constraints. The stable IDs
below point to the appendix in
`docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md#cross-cutting-constraints`.

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

Execution rules:

- Run each task with TDD: write the test, run it red, implement the smallest
  product code that satisfies the expected behavior, run it green, then commit.
- If executing a task requires relaxing a `CC-*` constraint, changing a
  cross-cutting decision, or moving a vertical noun into core to make the task
  pass, stop and surface the conflict. Do not silently work around the
  constraint.
- Keep core tests packless unless the task is explicitly a maritime task.
- Do not stage unrelated scratch files, `.claude/`, `.codex/`, `.superpowers/`,
  `.vite/`, screenshots, or `taste-skill/`.
- Do not create `backend/src/argus/traffic_public_space`, traffic routes,
  traffic migrations, traffic UI, or home-lab pack code.
- Use focused modules; keep `backend/src/argus/services/app.py` to service
  construction and avoid placing domain logic there.
- Frontend verification uses the existing package scripts:
  `corepack pnpm test --run`, `corepack pnpm build`, and
  `corepack pnpm lint`.

Atomic commit policy:

- Small tasks can use the single commit command shown at the end of the task.
- Large tasks must split into atomic commits even when the task header stays
  intact. Use these checkpoints unless the implementation naturally produces an
  even smaller reviewable commit:
  - Task 1: `test: define core link baseline`, `feat: add link schema`,
    `feat: add link service`, `feat: add link api`.
  - Task 4: `test: define maritime entity behavior`,
    `feat: add maritime entity schema`, `feat: add maritime entity api`.
  - Task 6: `test: define maritime telemetry adapters`,
    `feat: add maritime telemetry schema`, `feat: add maritime telemetry ingest`,
    `feat: add carrier-aware link selection`.
  - Task 7: `test: define maritime evidence context`,
    `feat: add maritime evidence context`, `feat: add maritime evidence export`.
  - Task 8: `test: define billing baseline`, `feat: add billing schema`,
    `feat: add billing service api`, `feat: add maritime billing rollups`.
  - Task 9: `test: define support baseline`, `feat: add support schema`,
    `feat: add support service api`, `feat: add supervisor tunnel handoff`,
    `feat: add maritime support diagnostics`.
  - Task 11: `test: define fleetops ui states`, `feat: add fleetops routes`,
    `feat: add fleetops operations surfaces`,
    `feat: add fleetops billing support surfaces`.

Migration numbering:

- Migration filenames in this plan use `0030` through `0034` as examples because
  the branch currently has migrations through `0029`. Before writing Task 1
  implementation code, read the highest existing migration number and allocate
  the next five free numbers for `core_link`, `core_fleet`, `core_billing`,
  `core_support`, and `maritime_pack`.
- Use this command from the repository root:

```bash
ls backend/src/argus/migrations/versions/*.py | sed -E 's#.*/([0-9]+).*#\1#' | sort -n | tail -1
```

- If the result is not `0029`, replace every migration filename in the task with
  the computed free number before committing. Do not overwrite or reuse an
  existing migration number.

## File Structure

Create backend core modules:

- `backend/src/argus/link/contracts.py`: domain-neutral link API models.
- `backend/src/argus/link/tables.py`: link SQLAlchemy tables.
- `backend/src/argus/link/service.py`: budgets, queues, probes, transfer attempts, passports, selection policy.
- `backend/src/argus/link/api.py`: `/api/v1/link` routes.
- `backend/src/argus/fleet/contracts.py`: domain-neutral fleet/site API models.
- `backend/src/argus/fleet/tables.py`: site groups, hierarchy, state, assignments, rotations.
- `backend/src/argus/fleet/service.py`: site grouping, exceptions, state aggregation.
- `backend/src/argus/fleet/api.py`: `/api/v1/fleet` routes.
- `backend/src/argus/billing/contracts.py`: billing API models.
- `backend/src/argus/billing/tables.py`: billing nodes, accounts, entitlements, meters, price books, usage, invoice lines, exports.
- `backend/src/argus/billing/service.py`: entitlements, usage recording, invoice generation, exports.
- `backend/src/argus/billing/api.py`: `/api/v1/billing` routes.
- `backend/src/argus/support/contracts.py`: support API models.
- `backend/src/argus/support/tables.py`: bundles, sessions, tunnels, break-glass, onboarding checks.
- `backend/src/argus/support/service.py`: support bundles, tunnel lifecycle, onboarding, break-glass, redaction.
- `backend/src/argus/support/tunnel_transport.py`: supervisor-managed `ssh_reverse` transport command contracts.
- `backend/src/argus/support/api.py`: `/api/v1/support` routes.

Create maritime pack modules:

- `backend/src/argus/maritime/contracts.py`: maritime API models.
- `backend/src/argus/maritime/tables.py`: vessels, voyages, port calls, telemetry, roles, evidence context.
- `backend/src/argus/maritime/service.py`: vessel/voyage/port-call CRUD and overview.
- `backend/src/argus/maritime/templates.py`: manifest template mapping into core camera config.
- `backend/src/argus/maritime/telemetry.py`: AIS/NMEA/carrier adapters and ingest.
- `backend/src/argus/maritime/evidence.py`: context resolution and evidence export metadata.
- `backend/src/argus/maritime/billing.py`: maritime labels, meters, rollups, charter handover.
- `backend/src/argus/maritime/support.py`: shipboard checklist and diagnostics grouping.
- `backend/src/argus/maritime/api.py`: `/api/v1/maritime` routes.

Modify backend integration points:

- `backend/src/argus/models/__init__.py`: import new table classes for metadata.
- `backend/src/argus/api/v1/__init__.py`: include new routers.
- `backend/src/argus/services/app.py`: construct services without embedding domain logic.
- `backend/src/argus/core/events.py`: add support tunnel and link transfer streams if needed.
- `backend/src/argus/models/enums.py`: add only domain-neutral core enums; maritime enums stay in `argus.maritime.contracts` unless SQL enum reuse is required.
- `backend/src/argus/scripts/export_openapi_schema.py`: export OpenAPI to a
  file without requiring a running backend server.
- `backend/src/argus/migrations/versions/0030_core_link.py`
- `backend/src/argus/migrations/versions/0031_core_fleet.py`
- `backend/src/argus/migrations/versions/0032_core_billing.py`
- `backend/src/argus/migrations/versions/0033_core_support.py`
- `backend/src/argus/migrations/versions/0034_maritime_pack.py`

Create backend tests:

- `backend/tests/link/test_link_service.py`
- `backend/tests/api/test_link_routes.py`
- `backend/tests/fleet/test_fleet_service.py`
- `backend/tests/api/test_fleet_routes.py`
- `backend/tests/billing/test_billing_service.py`
- `backend/tests/api/test_billing_routes.py`
- `backend/tests/support/test_support_service.py`
- `backend/tests/api/test_support_routes.py`
- `backend/tests/maritime/test_runtime.py`
- `backend/tests/maritime/test_entities.py`
- `backend/tests/maritime/test_templates.py`
- `backend/tests/maritime/test_telemetry.py`
- `backend/tests/maritime/test_evidence.py`
- `backend/tests/maritime/test_billing_support.py`
- `backend/tests/api/test_maritime_routes.py`
- `backend/tests/api/test_openapi_export.py`
- `backend/tests/core/test_full_product_boundaries.py`
- `backend/tests/core/test_packless_empty_registry.py`
- `backend/tests/e2e/test_maritime_fleetops_smoke.py`

Create frontend files:

- `frontend/src/hooks/use-link.ts`
- `frontend/src/hooks/use-fleet.ts`
- `frontend/src/hooks/use-billing.ts`
- `frontend/src/hooks/use-support.ts`
- `frontend/src/hooks/use-maritime.ts`
- `frontend/src/pages/FleetOps.tsx`
- `frontend/src/pages/FleetOpsVessels.tsx`
- `frontend/src/pages/FleetOpsVesselDetail.tsx`
- `frontend/src/pages/FleetOpsEvidence.tsx`
- `frontend/src/pages/FleetOpsBilling.tsx`
- `frontend/src/pages/FleetOpsSupport.tsx`
- `frontend/src/pages/FleetOpsOnboarding.tsx`
- `frontend/src/components/fleetops/FleetOverviewPanel.tsx`
- `frontend/src/components/fleetops/VesselSummaryTable.tsx`
- `frontend/src/components/fleetops/VoyageTimeline.tsx`
- `frontend/src/components/fleetops/LinkOperationsPanel.tsx`
- `frontend/src/components/fleetops/EvidenceExportBuilder.tsx`
- `frontend/src/components/fleetops/BillingRollupPanel.tsx`
- `frontend/src/components/fleetops/SupportDiagnosticsPanel.tsx`

Modify frontend integration points:

- `frontend/src/app/router.tsx`: add FleetOps routes.
- `frontend/src/components/layout/workspace-nav.ts`: add FleetOps nav while keeping traffic hidden.
- `frontend/src/lib/api.generated.ts`: regenerate after backend OpenAPI is complete.
- `frontend/src/lib/openapi.json`: generated OpenAPI file artifact consumed by
  `openapi-typescript`.
- `frontend/package.json`: change `generate:api` to read
  `src/lib/openapi.json` rather than `http://127.0.0.1:8000/openapi.json`.

## Gate 1: Core Generality

### Task 1: Core Link Baseline

**Constraints:** `CC-1`, `CC-4`, `CC-8`

**Files:**
- Create: `backend/src/argus/link/contracts.py`
- Create: `backend/src/argus/link/tables.py`
- Create: `backend/src/argus/link/service.py`
- Create: `backend/src/argus/link/api.py`
- Create: `backend/src/argus/migrations/versions/0030_core_link.py`
- Modify: `backend/src/argus/models/__init__.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/link/test_link_service.py`
- Test: `backend/tests/api/test_link_routes.py`
- Test: `backend/tests/core/test_packless_empty_registry.py`

- [ ] **Step 0: Reserve migration filenames**

Run:

```bash
cd /Users/yann.moren/vision
ls backend/src/argus/migrations/versions/*.py | sed -E 's#.*/([0-9]+).*#\1#' | sort -n | tail -1
```

Expected today: `0029`. If the command prints a larger number, reserve the next
five free numbers and update the migration filenames in Tasks 1, 2, 8, 9, and
4 before writing migrations.

- [ ] **Step 1: Write failing link service tests**

Create `backend/tests/link/test_link_service.py` with concrete tests covering
these assertions:

```python
def test_packless_site_budget_queue_and_passport_flow(link_service: LinkService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")

    budget = link_service.upsert_budget(
        tenant_id=tenant_id,
        site_id=site_id,
        monthly_bytes=50_000_000_000,
        bulk_daily_bytes=5_000_000_000,
    )
    link_service.record_probe(
        tenant_id=tenant_id,
        site_id=site_id,
        latency_ms=620,
        throughput_mbps=8.5,
        packet_loss_percent=0.8,
        reachable=True,
        source="packless-lab",
    )
    item = link_service.enqueue_transfer(
        tenant_id=tenant_id,
        site_id=site_id,
        priority_lane="evidence",
        byte_size=2048,
        source_object_type="evidence_artifact",
        source_object_id=UUID("00000000-0000-4000-8000-000000000003"),
    )
    passport = link_service.build_passport(tenant_id=tenant_id, site_id=site_id)

    assert budget.site_id == site_id
    assert item.priority_lane == "evidence"
    assert passport.site_id == site_id
    assert passport.pack_id is None
    assert passport.link_state in {"healthy", "degraded", "recovering", "port_wifi"}


def test_priority_order_is_safety_evidence_telemetry_bulk(link_service: LinkService) -> None:
    items = [
        link_service.make_queue_item_for_test(priority_lane="bulk", byte_size=100),
        link_service.make_queue_item_for_test(priority_lane="telemetry", byte_size=100),
        link_service.make_queue_item_for_test(priority_lane="safety", byte_size=100),
        link_service.make_queue_item_for_test(priority_lane="evidence", byte_size=100),
    ]
    assert [item.priority_lane for item in link_service.sort_queue(items)] == [
        "safety",
        "evidence",
        "telemetry",
        "bulk",
    ]


def test_degraded_budget_backpressures_lower_priority_lanes(link_service: LinkService) -> None:
    decision = link_service.apply_backpressure(
        link_state="degraded",
        remaining_daily_bulk_bytes=0,
        queue_depth_by_lane={"safety": 1, "evidence": 3, "telemetry": 10, "bulk": 20},
    )
    assert decision.paused_lanes == {"telemetry", "bulk"}
    assert decision.allowed_lanes == {"safety", "evidence"}
    assert decision.reason == "degraded_link_or_budget_exhausted"


def test_resume_records_offsets_and_last_successful_transfer(link_service: LinkService) -> None:
    queue_item = link_service.make_queue_item_for_test(priority_lane="evidence", byte_size=4096)
    attempt = link_service.record_transfer_attempt(
        queue_item_id=queue_item.id,
        status="interrupted",
        bytes_transferred=2048,
        resume_token="object-part-2",
        interruption_reason="link_dark",
    )
    resumed = link_service.record_transfer_attempt(
        queue_item_id=queue_item.id,
        status="succeeded",
        bytes_transferred=4096,
        resume_token=attempt.resume_token,
    )
    assert resumed.bytes_transferred == 4096
    assert resumed.resume_token == "object-part-2"
    assert link_service.get_queue_item(queue_item.id).last_successful_transfer_at is not None


def test_link_passport_hash_is_stable_for_canonical_payload(link_service: LinkService) -> None:
    first = link_service.hash_passport_payload({"b": 2, "a": {"z": 1, "y": 2}})
    second = link_service.hash_passport_payload({"a": {"y": 2, "z": 1}, "b": 2})
    assert first == second
```

Assertions:

- A generic `site_id` with no pack can create a budget, queue items, probes, and passport.
- Lane ordering is `safety`, `evidence`, `telemetry`, `bulk`.
- Degraded probes pause `bulk` and `telemetry` before `evidence`.
- Resume state stores `resume_token`, `bytes_transferred`, and `last_successful_transfer_at`.
- Passport hash is deterministic and independent of dict key order.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py -q
```

Expected: import failure for `argus.link.service`.

- [ ] **Step 3: Implement link contracts, tables, migration, and service**

Implement:

- `LinkState = Literal["unknown", "healthy", "degraded", "dark", "recovering", "port_wifi"]`
- `LinkPriorityLane = Literal["safety", "evidence", "telemetry", "bulk"]`
- `LINK_PRIORITY_ORDER = {"safety": 0, "evidence": 1, "telemetry": 2, "bulk": 3}`
- `LinkBudget`, `LinkQueueItem`, `LinkTransferAttempt`, `LinkHealthProbe`, `LinkPassportSnapshot` tables.
- `LinkService.upsert_budget()`
- `LinkService.enqueue_transfer()`
- `LinkService.record_probe()`
- `LinkService.list_queue()`
- `LinkService.apply_backpressure()`
- `LinkService.record_transfer_attempt()`
- `LinkService.build_passport()`

Use `tenant_id`, `site_id`, optional `camera_id`, optional `incident_id`, and optional `evidence_artifact_id`; do not add maritime columns.

- [ ] **Step 4: Add link routes and route tests**

Create `backend/tests/api/test_link_routes.py` with tests covering:

```python
async def test_packless_link_status_route_returns_budget_queue_probe_and_state(client: AsyncClient) -> None:
    response = await client.get("/api/v1/link/sites/00000000-0000-4000-8000-000000000002/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["site_id"] == "00000000-0000-4000-8000-000000000002"
    assert payload["pack_id"] is None
    assert set(payload) >= {"budget", "queue_depth", "latest_probe", "link_state", "last_sync_at"}


async def test_link_budget_update_requires_admin(viewer_client: AsyncClient) -> None:
    response = await viewer_client.put(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/budget",
        json={"monthly_bytes": 50_000_000_000, "bulk_daily_bytes": 5_000_000_000},
    )
    assert response.status_code == 403


async def test_queue_pause_resume_retry_routes_are_tenant_scoped(client: AsyncClient) -> None:
    foreign_item_id = "00000000-0000-4000-8000-000000000099"
    for action in ("pause", "resume", "retry"):
        response = await client.post(f"/api/v1/link/queue/{foreign_item_id}/{action}")
        assert response.status_code == 404
```

Add the first empty-registry integration test in
`backend/tests/core/test_packless_empty_registry.py`:

```python
async def test_link_routes_work_with_empty_pack_registry(empty_pack_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=empty_pack_app), base_url="http://test") as client:
        response = await client.get("/api/v1/link/sites/00000000-0000-4000-8000-000000000002/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["site_id"] == "00000000-0000-4000-8000-000000000002"
    assert payload.get("pack_id") is None
```

The `empty_pack_app` fixture must construct the full FastAPI app with a
`PackRegistry` pointed at an empty temporary `packs/` directory. This proves
`CC-1` at the API/app-composition layer, not only inside the service.

Implement routes:

- `GET /api/v1/link/sites/{site_id}/status`
- `GET /api/v1/link/sites/{site_id}/budget`
- `PUT /api/v1/link/sites/{site_id}/budget`
- `GET /api/v1/link/sites/{site_id}/queue`
- `GET /api/v1/link/sites/{site_id}/probes`
- `POST /api/v1/link/sites/{site_id}/probes`
- `GET /api/v1/link/sites/{site_id}/policies`
- `PUT /api/v1/link/sites/{site_id}/policies`
- `GET /api/v1/link/evidence/{incident_id}/passport`
- `POST /api/v1/link/queue/{queue_item_id}/retry`
- `POST /api/v1/link/queue/{queue_item_id}/pause`
- `POST /api/v1/link/queue/{queue_item_id}/resume`

- [ ] **Step 5: Verify link task**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py::test_link_routes_work_with_empty_pack_registry -q
python3 -m uv run ruff check src/argus/link tests/link tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py
python3 -m uv run mypy src/argus/link
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link backend/src/argus/migrations/versions/0030_core_link.py backend/src/argus/models/__init__.py backend/src/argus/api/v1/__init__.py backend/src/argus/services/app.py backend/tests/link backend/tests/api/test_link_routes.py backend/tests/core/test_packless_empty_registry.py
git commit -m "feat: add core link baseline"
```

### Task 2: Core Fleet Baseline

**Constraints:** `CC-1`, `CC-5`

**Files:**
- Create: `backend/src/argus/fleet/contracts.py`
- Create: `backend/src/argus/fleet/tables.py`
- Create: `backend/src/argus/fleet/service.py`
- Create: `backend/src/argus/fleet/api.py`
- Create: `backend/src/argus/migrations/versions/0031_core_fleet.py`
- Modify: `backend/src/argus/models/__init__.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/fleet/test_fleet_service.py`
- Test: `backend/tests/api/test_fleet_routes.py`
- Test: `backend/tests/core/test_packless_empty_registry.py`

- [ ] **Step 1: Write failing fleet tests**

Create tests with concrete assertions:

```python
def test_packless_site_group_hierarchy_and_assignment_flow(fleet_service: FleetService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")

    group = fleet_service.create_site_group(
        tenant_id=tenant_id,
        label="Remote sites",
        kind="operator_group",
    )
    fleet_service.replace_hierarchy(
        tenant_id=tenant_id,
        nodes=[
            {"id": "region-eu", "parent_id": None, "label": "Europe", "kind": "region"},
            {"id": "site-node", "parent_id": "region-eu", "site_id": str(site_id), "kind": "site"},
        ],
    )
    assignment = fleet_service.create_site_assignment(
        tenant_id=tenant_id,
        site_id=site_id,
        assignee_type="support_queue",
        assignee_id="noc-day",
    )

    assert group.pack_id is None
    assert assignment.site_id == site_id
    assert fleet_service.get_hierarchy(tenant_id=tenant_id).nodes[1].kind == "site"


def test_fleet_exceptions_order_by_attention_without_maritime_context(fleet_service: FleetService) -> None:
    exceptions = fleet_service.compute_exceptions(
        stale_heartbeat=True,
        degraded_link=True,
        evidence_backlog_count=12,
        stopped_worker=True,
        privacy_mismatch=True,
        model_artifact_mismatch=True,
        active_incident_count=1,
    )
    assert [item.kind for item in exceptions] == [
        "active_incident",
        "stopped_worker",
        "privacy_mismatch",
        "model_artifact_mismatch",
        "degraded_link",
        "evidence_backlog",
        "stale_heartbeat",
    ]
    assert all(item.pack_id is None for item in exceptions)


def test_rotation_groups_are_generic_and_pack_label_free(fleet_service: FleetService) -> None:
    rotation = fleet_service.create_rotation_group(
        tenant_id=UUID("00000000-0000-4000-8000-000000000001"),
        label="NOC day watch",
        member_user_ids=["operator-a", "operator-b"],
    )
    assert rotation.label == "NOC day watch"
    assert rotation.pack_labels == {}


async def test_fleet_exceptions_route_is_packless_and_tenant_scoped(client: AsyncClient) -> None:
    response = await client.get("/api/v1/fleet/exceptions")
    assert response.status_code == 200
    payload = response.json()
    assert all("vessel" not in json.dumps(item).lower() for item in payload["items"])
    assert all(item["tenant_id"] == "00000000-0000-4000-8000-000000000001" for item in payload["items"])
```

Append this empty-registry API test to
`backend/tests/core/test_packless_empty_registry.py`:

```python
async def test_fleet_routes_work_with_empty_pack_registry(empty_pack_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=empty_pack_app), base_url="http://test") as client:
        response = await client.get("/api/v1/fleet/exceptions")

    assert response.status_code == 200
    serialized = json.dumps(response.json()).lower()
    assert "vessel" not in serialized
    assert "voyage" not in serialized
```

Assertions:

- Generic sites can belong to generic groups and hierarchy nodes.
- Exceptions are computed for stale heartbeat, degraded link, evidence backlog, stopped worker, privacy mismatch, model/artifact mismatch, and active incident.
- No response field is named vessel, voyage, owner, manager, charterer, AIS, NMEA, or port call.

- [ ] **Step 2: Run tests and verify failure**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/fleet/test_fleet_service.py tests/api/test_fleet_routes.py -q
```

Expected: import failure for `argus.fleet`.

- [ ] **Step 3: Implement fleet contracts, tables, migration, and service**

Implement:

- `SiteGroup`
- `SiteHierarchyNode`
- `SiteState`
- `SiteAssignment`
- `RotationGroup`
- computed `FleetException`

Service methods:

- `create_site_group()`
- `list_site_groups()`
- `replace_hierarchy()`
- `get_hierarchy()`
- `upsert_site_state()`
- `get_site_state()`
- `create_rotation_group()`
- `create_site_assignment()`
- `list_exceptions()`

- [ ] **Step 4: Add fleet API routes**

Routes:

- `GET /api/v1/fleet/site-groups`
- `POST /api/v1/fleet/site-groups`
- `GET /api/v1/fleet/hierarchy`
- `PUT /api/v1/fleet/hierarchy`
- `GET /api/v1/fleet/sites/{site_id}/state`
- `GET /api/v1/fleet/exceptions`
- `GET /api/v1/fleet/rotation-groups`
- `POST /api/v1/fleet/rotation-groups`
- `GET /api/v1/fleet/site-assignments`
- `POST /api/v1/fleet/site-assignments`

- [ ] **Step 5: Verify fleet task**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/fleet/test_fleet_service.py tests/api/test_fleet_routes.py tests/core/test_packless_empty_registry.py::test_fleet_routes_work_with_empty_pack_registry -q
python3 -m uv run ruff check src/argus/fleet tests/fleet tests/api/test_fleet_routes.py tests/core/test_packless_empty_registry.py
python3 -m uv run mypy src/argus/fleet
```

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/fleet backend/src/argus/migrations/versions/0031_core_fleet.py backend/src/argus/models/__init__.py backend/src/argus/api/v1/__init__.py backend/src/argus/services/app.py backend/tests/fleet backend/tests/api/test_fleet_routes.py backend/tests/core/test_packless_empty_registry.py
git commit -m "feat: add core fleet baseline"
```

## Gate 2: Maritime Runtime

### Task 3: Maritime Runtime Skeleton

**Constraints:** `CC-2`, `CC-3`

**Files:**
- Create: `backend/src/argus/maritime/__init__.py`
- Create: `backend/src/argus/maritime/contracts.py`
- Create: `backend/src/argus/maritime/tables.py`
- Create: `backend/src/argus/maritime/service.py`
- Create: `backend/src/argus/maritime/api.py`
- Modify: `backend/src/argus/models/__init__.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/maritime/test_runtime.py`
- Test: `backend/tests/core/test_full_product_boundaries.py`

- [ ] **Step 1: Write failing runtime and boundary tests**

Tests:

```python
def test_maritime_runtime_requires_manifest_enabled_pack(pack_registry: PackRegistry) -> None:
    runtime = MaritimeRuntimeService(pack_registry=pack_registry).runtime()
    assert runtime.pack_id == "maritime-fleet"
    assert runtime.enabled is True
    assert runtime.implementation_commitment is True
    assert {"argus.link", "argus.fleet", "argus.billing", "argus.support"} <= set(runtime.required_core_capabilities)


def test_traffic_has_no_runtime_module_or_route(app: FastAPI) -> None:
    assert importlib.util.find_spec("argus.traffic_public_space") is None
    route_paths = {route.path for route in app.routes}
    assert "/api/v1/traffic-public-space/runtime" not in route_paths
    assert "/api/v1/packs/traffic-public-space/runtime" not in route_paths


def test_core_contracts_do_not_contain_maritime_nouns() -> None:
    forbidden_identifier_patterns = [
        r"\bVessel\b",
        r"\bVoyage\b",
        r"\bPortCall\b",
        r"\bAIS\b",
        r"\bNMEA\b",
        r"\bMMSI\b",
        r"\bIMO\b",
        r"\bvessel_id\b",
        r"\bvoyage_id\b",
        r"\bport_call_id\b",
        r"\bmmsi\b",
        r"\bimo_number\b",
    ]
    scanned_paths = [
        Path("backend/src/argus/link"),
        Path("backend/src/argus/fleet"),
        Path("backend/src/argus/billing"),
        Path("backend/src/argus/support"),
        Path("backend/src/argus/api/contracts.py"),
    ]
    text = "\n".join(path.read_text() for root in scanned_paths for path in ([root] if root.is_file() else root.rglob("*.py")))
    hits = [pattern for pattern in forbidden_identifier_patterns if re.search(pattern, text)]
    assert hits == []
```

Core noun scan must inspect:

- `backend/src/argus/link`
- `backend/src/argus/fleet`
- `backend/src/argus/billing`
- `backend/src/argus/support`
- `backend/src/argus/api/contracts.py`

Allowed exceptions: opaque `pack_id`, `pack_metadata`, tests, and the `argus.maritime` package. Use word-boundary or identifier-pattern matching, not broad lowercase substring matching; broad matching can falsely fail on unrelated words.

- [ ] **Step 2: Implement runtime contribution**

`MaritimeRuntimeService.runtime()` returns:

- pack id and manifest version
- runtime enabled flag
- scene templates
- model presets
- evidence fields
- integration descriptors
- UI labels
- billing labels and meters

Routes:

- `GET /api/v1/maritime/runtime`
- `GET /api/v1/packs/maritime-fleet/runtime`

- [ ] **Step 3: Verify and commit**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/maritime/test_runtime.py tests/core/test_full_product_boundaries.py -q
python3 -m uv run ruff check src/argus/maritime tests/maritime tests/core/test_full_product_boundaries.py
python3 -m uv run mypy src/argus/maritime
cd /Users/yann.moren/vision
git add backend/src/argus/maritime backend/src/argus/models/__init__.py backend/src/argus/api/v1/__init__.py backend/src/argus/services/app.py backend/tests/maritime/test_runtime.py backend/tests/core/test_full_product_boundaries.py
git commit -m "feat: add maritime runtime skeleton"
```

### Task 4: Maritime Entities

**Constraints:** `CC-2`, `CC-5`

**Files:**
- Modify: `backend/src/argus/maritime/contracts.py`
- Modify: `backend/src/argus/maritime/tables.py`
- Modify: `backend/src/argus/maritime/service.py`
- Modify: `backend/src/argus/maritime/api.py`
- Create: `backend/src/argus/migrations/versions/0034_maritime_pack.py`
- Test: `backend/tests/maritime/test_entities.py`
- Test: `backend/tests/api/test_maritime_routes.py`

- [ ] **Step 1: Write failing entity tests**

Tests:

```python
async def test_create_vessel_with_linked_site(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/maritime/vessels",
        json={"name": "MV Resolute", "mmsi": "235012345", "create_site": {"name": "MV Resolute"}},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "MV Resolute"
    assert payload["site"]["name"] == "MV Resolute"
    assert payload["site_id"] == payload["site"]["id"]


async def test_create_vessel_attaches_existing_site(client: AsyncClient, site_id: UUID) -> None:
    response = await client.post(
        "/api/v1/maritime/vessels",
        json={"name": "MV Existing", "site_id": str(site_id), "imo_number": "9876543"},
    )
    assert response.status_code == 201
    assert response.json()["site_id"] == str(site_id)


async def test_vessel_identifiers_are_unique_per_tenant(client: AsyncClient) -> None:
    payload = {"name": "MV Duplicate", "mmsi": "235012345", "create_site": {"name": "MV Duplicate"}}
    assert (await client.post("/api/v1/maritime/vessels", json=payload)).status_code == 201
    duplicate = await client.post("/api/v1/maritime/vessels", json={**payload, "name": "MV Duplicate 2"})
    assert duplicate.status_code == 409


async def test_only_one_active_voyage_per_vessel(client: AsyncClient, vessel_id: UUID) -> None:
    first = await client.post(f"/api/v1/maritime/vessels/{vessel_id}/voyages", json={"name": "Leg 1"})
    second = await client.post(f"/api/v1/maritime/vessels/{vessel_id}/voyages", json={"name": "Leg 2"})
    assert (await client.post(f"/api/v1/maritime/voyages/{first.json()['id']}/activate")).status_code == 200
    conflict = await client.post(f"/api/v1/maritime/voyages/{second.json()['id']}/activate")
    assert conflict.status_code == 409


async def test_port_call_state_transitions_are_validated(client: AsyncClient, voyage_id: UUID) -> None:
    port_call = await client.post(
        f"/api/v1/maritime/voyages/{voyage_id}/port-calls",
        json={"port_name": "Rotterdam", "un_locode": "NLRTM", "eta": "2026-06-10T08:00:00Z"},
    )
    port_call_id = port_call.json()["id"]
    assert (await client.post(f"/api/v1/maritime/port-calls/{port_call_id}/depart")).status_code == 409
    assert (await client.post(f"/api/v1/maritime/port-calls/{port_call_id}/arrive")).status_code == 200
    assert (await client.post(f"/api/v1/maritime/port-calls/{port_call_id}/depart")).status_code == 200


async def test_cross_tenant_vessel_access_returns_404(foreign_tenant_client: AsyncClient, vessel_id: UUID) -> None:
    response = await foreign_tenant_client.get(f"/api/v1/maritime/vessels/{vessel_id}")
    assert response.status_code == 404
```

- [ ] **Step 2: Implement tables and state transitions**

Tables:

- `MaritimeVessel`
- `MaritimeVoyage`
- `MaritimePortCall`
- `MaritimeRole`
- `MaritimeWatchRotation`

State rules:

- Voyage statuses: `planned`, `active`, `completed`, `cancelled`.
- Port-call statuses: `scheduled`, `arrived`, `alongside`, `departed`, `cancelled`.
- Activating a voyage rejects another active voyage for the same vessel.
- Departing a port call requires `arrived` or `alongside`.

- [ ] **Step 3: Implement entity routes**

Routes:

- `GET|POST /api/v1/maritime/vessels`
- `GET|PATCH|DELETE /api/v1/maritime/vessels/{vessel_id}`
- `GET|POST /api/v1/maritime/vessels/{vessel_id}/voyages`
- `GET|PATCH /api/v1/maritime/voyages/{voyage_id}`
- `POST /api/v1/maritime/voyages/{voyage_id}/activate`
- `POST /api/v1/maritime/voyages/{voyage_id}/complete`
- `GET|POST /api/v1/maritime/voyages/{voyage_id}/port-calls`
- `PATCH /api/v1/maritime/port-calls/{port_call_id}`
- `POST /api/v1/maritime/port-calls/{port_call_id}/arrive`
- `POST /api/v1/maritime/port-calls/{port_call_id}/depart`

- [ ] **Step 4: Verify and commit**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/maritime/test_entities.py tests/api/test_maritime_routes.py -q
python3 -m uv run ruff check src/argus/maritime tests/maritime tests/api/test_maritime_routes.py
python3 -m uv run mypy src/argus/maritime
cd /Users/yann.moren/vision
git add backend/src/argus/maritime backend/src/argus/migrations/versions/0034_maritime_pack.py backend/tests/maritime/test_entities.py backend/tests/api/test_maritime_routes.py
git commit -m "feat: add maritime vessel voyage port call entities"
```

### Task 5: Maritime Scene Templates

**Constraints:** `CC-2`, `CC-8`

**Files:**
- Create: `backend/src/argus/maritime/templates.py`
- Modify: `backend/src/argus/maritime/api.py`
- Test: `backend/tests/maritime/test_templates.py`

- [ ] **Step 1: Write failing template tests**

Tests:

```python
def test_manifest_templates_map_to_core_camera_payloads(template_service: MaritimeTemplateService) -> None:
    template = template_service.get_template("gangway-access")
    payload = template_service.to_core_camera_payload(template)
    assert set(payload) <= {
        "active_classes",
        "runtime_vocabulary",
        "detection_regions",
        "zones",
        "incident_rules",
        "evidence_recording_policy",
        "privacy_defaults",
    }
    assert "vessel" not in payload


async def test_apply_gangway_template_updates_core_camera_primitives(client: AsyncClient, camera_id: UUID) -> None:
    response = await client.post(
        f"/api/v1/maritime/cameras/{camera_id}/apply-template",
        json={"template_id": "gangway-access"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["template_id"] == "gangway-access"
    assert payload["scene_contract_snapshot_id"] is not None


def test_templates_do_not_create_second_scene_engine(template_service: MaritimeTemplateService) -> None:
    template = template_service.get_template("deck-presence")
    assert template.execution_engine == "core_scene_contract"
    assert template.detector_override is None
```

Assert templates map only to existing core fields: active classes, runtime vocabulary, detection regions, zones, incident rules, recording policy, privacy defaults.

- [ ] **Step 2: Implement template mapping and routes**

Routes:

- `GET /api/v1/maritime/scene-templates`
- `POST /api/v1/maritime/cameras/{camera_id}/apply-template`

Templates:

- `gangway-access`
- `deck-presence`
- `engine-room-safety`
- `cargo-work-area`
- `port-call-evidence`

- [ ] **Step 3: Verify and commit**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/maritime/test_templates.py -q
python3 -m uv run ruff check src/argus/maritime/templates.py tests/maritime/test_templates.py
python3 -m uv run mypy src/argus/maritime/templates.py
cd /Users/yann.moren/vision
git add backend/src/argus/maritime/templates.py backend/src/argus/maritime/api.py backend/tests/maritime/test_templates.py
git commit -m "feat: add maritime scene templates"
```

### Task 6: Maritime Telemetry And Carrier Selection

**Constraints:** `CC-2`, `CC-4`, `CC-7`

**Files:**
- Create: `backend/src/argus/maritime/telemetry.py`
- Modify: `backend/src/argus/maritime/contracts.py`
- Modify: `backend/src/argus/maritime/tables.py`
- Modify: `backend/src/argus/maritime/service.py`
- Modify: `backend/src/argus/maritime/api.py`
- Test: `backend/tests/maritime/test_telemetry.py`

- [ ] **Step 1: Write failing telemetry tests**

Tests:

```python
def test_ais_json_adapter_normalizes_position() -> None:
    result = AISJsonAdapter().parse(
        {"mmsi": "235012345", "lat": 51.95, "lon": 4.14, "sog": 12.4, "cog": 84.2, "reported_at": "2026-06-05T09:15:00Z"}
    )
    assert result.mmsi == "235012345"
    assert result.latitude == 51.95
    assert result.longitude == 4.14
    assert result.raw_payload["sog"] == 12.4


def test_ais_csv_adapter_imports_common_export() -> None:
    csv_payload = "mmsi,lat,lon,sog,cog,heading,reported_at\n235012345,51.95,4.14,12.4,84.2,90,2026-06-05T09:15:00Z\n"
    result = AisCsvFileAdapter().parse(csv_payload)
    assert len(result.positions) == 1
    assert result.failures == []
    assert result.positions[0].heading == 90


def test_nmea_0183_adapter_parses_position_heading_and_speed() -> None:
    readings = Nmea0183Adapter().parse_lines([
        "$GPRMC,091500,A,5157.000,N,00408.400,E,012.4,084.2,050626,,,A*68",
        "$HEHDT,090.0,T*1B",
    ])
    assert readings.position.latitude_decimal == pytest.approx(51.95, rel=0.01)
    assert readings.speed_over_ground == pytest.approx(12.4)
    assert readings.heading == pytest.approx(90.0)


def test_carrier_webhook_adapter_preserves_raw_payload() -> None:
    payload = {"terminal_id": "starlink-a", "status": "online", "downlink_mbps": 120, "vendor_extra": {"beam": "eu-west"}}
    result = CarrierWebhookAdapter().parse(payload)
    assert result.terminal_id == "starlink-a"
    assert result.provider == "generic"
    assert result.raw_payload["vendor_extra"]["beam"] == "eu-west"


async def test_carrier_http_polling_uses_secret_profile_not_plain_table_secret(httpx_mock: HTTPXMock) -> None:
    adapter = CarrierHttpPollingAdapter(secret_profile_id="carrier-profile-1", endpoint_url="https://carrier.example/state")
    assert adapter.plaintext_secret is None
    httpx_mock.add_response(json={"terminal_id": "sat-1", "status": "online"})
    result = await adapter.poll(secret_resolver=lambda profile_id: {"authorization": "Bearer redacted"})
    assert result.terminal_id == "sat-1"


def test_carrier_file_import_reports_parse_failures() -> None:
    result = CarrierFileImportAdapter().parse_json_lines('{"terminal_id":"sat-1","status":"online"}\nnot-json\n')
    assert len(result.terminals) == 1
    assert result.failures[0].line_number == 2


def test_carrier_aware_selection_chooses_port_wifi_when_available() -> None:
    decision = select_transfer_lane(
        link_state="port_wifi",
        terminal_status="online",
        priority_lane="bulk",
        remaining_budget_bytes=100_000_000,
    )
    assert decision.transport == "port_wifi"
    assert decision.defer is False


def test_carrier_aware_selection_defers_bulk_on_degraded_satellite() -> None:
    decision = select_transfer_lane(
        link_state="satellite_degraded",
        terminal_status="degraded",
        priority_lane="bulk",
        remaining_budget_bytes=10_000,
    )
    assert decision.transport == "deferred"
    assert decision.defer is True
```

- [ ] **Step 2: Implement telemetry tables and adapters**

Tables:

- `MaritimeAISPosition`
- `MaritimeNMEAReading`
- `MaritimeCarrierTerminal`
- `MaritimeTelemetryIngestEvent`

Adapters:

- `AISJsonAdapter`
- `AisCsvFileAdapter`
- `Nmea0183Adapter`
- `CarrierWebhookAdapter`
- `CarrierHttpPollingAdapter`
- `CarrierFileImportAdapter`

- [ ] **Step 3: Implement ingest and selection routes**

Routes:

- `POST /api/v1/maritime/ingest/ais`
- `POST /api/v1/maritime/ingest/nmea`
- `POST /api/v1/maritime/ingest/carrier-terminal`
- `POST /api/v1/maritime/import/ais-file`
- `POST /api/v1/maritime/import/nmea-file`
- `GET /api/v1/maritime/vessels/{vessel_id}/telemetry`
- `GET /api/v1/maritime/vessels/{vessel_id}/carrier-selection`

- [ ] **Step 4: Verify and commit**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/maritime/test_telemetry.py -q
python3 -m uv run ruff check src/argus/maritime/telemetry.py tests/maritime/test_telemetry.py
python3 -m uv run mypy src/argus/maritime/telemetry.py
cd /Users/yann.moren/vision
git add backend/src/argus/maritime backend/tests/maritime/test_telemetry.py
git commit -m "feat: add maritime telemetry ingest"
```

### Task 7: Maritime Evidence Context And Export

**Constraints:** `CC-2`, `CC-4`, `CC-8`

**Files:**
- Create: `backend/src/argus/maritime/evidence.py`
- Modify: `backend/src/argus/maritime/contracts.py`
- Modify: `backend/src/argus/maritime/tables.py`
- Modify: `backend/src/argus/maritime/api.py`
- Test: `backend/tests/maritime/test_evidence.py`

- [ ] **Step 1: Write failing evidence tests**

Tests:

```python
async def test_resolves_context_from_explicit_context_row(evidence_service: MaritimeEvidenceService, incident_id: UUID) -> None:
    context = await evidence_service.create_context(
        incident_id=incident_id,
        vessel_id=UUID("00000000-0000-4000-8000-000000000010"),
        voyage_id=UUID("00000000-0000-4000-8000-000000000011"),
        resolution_source="manual",
    )
    resolved = await evidence_service.resolve_context(incident_id=incident_id)
    assert resolved.vessel_id == context.vessel_id
    assert resolved.resolution_source == "manual"


async def test_resolves_context_from_camera_site_active_voyage_and_port_call(evidence_service: MaritimeEvidenceService, camera_id: UUID) -> None:
    resolved = await evidence_service.resolve_context(camera_id=camera_id, incident_time=datetime(2026, 6, 5, 9, 15, tzinfo=UTC))
    assert resolved.resolution_source == "camera_site_active_voyage"
    assert resolved.vessel_name == "MV Resolute"
    assert resolved.port_name == "Rotterdam"


async def test_missing_telemetry_returns_partial_context_with_freshness(evidence_service: MaritimeEvidenceService, incident_id: UUID) -> None:
    resolved = await evidence_service.resolve_context(incident_id=incident_id)
    assert resolved.ais_position is None
    assert resolved.telemetry_freshness == {"ais": "missing", "carrier": "missing"}
    assert resolved.partial is True


async def test_export_adds_maritime_and_link_metadata_without_rehashing_artifacts(evidence_service: MaritimeEvidenceService, incident_id: UUID) -> None:
    before = await evidence_service.core_artifact_hashes(incident_id)
    export = await evidence_service.create_export(incident_id=incident_id, include_maritime_context=True, include_link_passport=True)
    after = await evidence_service.core_artifact_hashes(incident_id)
    assert before == after
    assert export.metadata["maritime_context"]["vessel_name"] == "MV Resolute"
    assert export.metadata["link_passport_hash"].startswith("sha256:")


async def test_export_includes_scene_runtime_link_passports_and_ledger_summary(evidence_service: MaritimeEvidenceService, incident_id: UUID) -> None:
    export = await evidence_service.create_export(incident_id=incident_id, include_maritime_context=True, include_link_passport=True)
    assert set(export.metadata) >= {
        "scene_contract_hash",
        "privacy_manifest_hash",
        "runtime_passport_hash",
        "link_passport_hash",
        "ledger_summary",
        "retention_policy",
        "time_source",
    }
```

- [ ] **Step 2: Implement context resolution**

Resolution order:

1. Explicit maritime context row.
2. Camera site to vessel.
3. Active voyage at incident time.
4. Overlapping or nearest port call.
5. Latest AIS and terminal state before incident within freshness windows.

- [ ] **Step 3: Implement evidence export**

Routes:

- `GET /api/v1/maritime/evidence-context`
- `GET /api/v1/maritime/evidence-exports`
- `POST /api/v1/maritime/evidence-exports`

Export metadata must include incident/artifact IDs, scene contract hash, privacy manifest hash, runtime passport hash, link passport hash, ledger summary, maritime context, time-source fields, and retention policy fields.

- [ ] **Step 4: Verify and commit**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/maritime/test_evidence.py -q
python3 -m uv run ruff check src/argus/maritime/evidence.py tests/maritime/test_evidence.py
python3 -m uv run mypy src/argus/maritime/evidence.py
cd /Users/yann.moren/vision
git add backend/src/argus/maritime backend/tests/maritime/test_evidence.py
git commit -m "feat: add maritime evidence context export"
```

## Gate 3: Commercial Operations

### Task 8: Core Billing And Maritime Rollups

**Constraints:** `CC-1`, `CC-2`, `CC-6`

**Files:**
- Create: `backend/src/argus/billing/contracts.py`
- Create: `backend/src/argus/billing/tables.py`
- Create: `backend/src/argus/billing/service.py`
- Create: `backend/src/argus/billing/api.py`
- Create: `backend/src/argus/migrations/versions/0032_core_billing.py`
- Create: `backend/src/argus/maritime/billing.py`
- Modify: `backend/src/argus/models/__init__.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/billing/test_billing_service.py`
- Test: `backend/tests/api/test_billing_routes.py`
- Test: `backend/tests/maritime/test_billing_support.py`
- Test: `backend/tests/core/test_packless_empty_registry.py`

- [ ] **Step 1: Write failing billing tests**

Tests:

```python
def test_packless_billing_node_account_entitlement_usage_invoice_flow(billing_service: BillingService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    node = billing_service.create_node(tenant_id=tenant_id, label="Generic deployment", kind="deployment", pack_id=None)
    account = billing_service.create_account(tenant_id=tenant_id, name="Mugetsu Ops", node_ids=[node.id])
    entitlement = billing_service.grant_entitlement(
        tenant_id=tenant_id,
        account_id=account.id,
        pack_id=None,
        feature_key="core_support",
        effective_from=date(2026, 6, 1),
    )
    usage = billing_service.record_usage(
        tenant_id=tenant_id,
        meter_key="support_session_hour",
        quantity=Decimal("1.5"),
        source_object_type="support_session",
        source_object_id=UUID("00000000-0000-4000-8000-000000000020"),
    )
    invoice = billing_service.run_invoice(tenant_id=tenant_id, account_id=account.id, period_start=date(2026, 6, 1), period_end=date(2026, 7, 1))
    assert entitlement.pack_id is None
    assert usage.pack_id is None
    assert invoice.line_items[0].meter_key == "support_session_hour"


def test_price_book_prices_invoice_line_items(billing_service: BillingService) -> None:
    billing_service.create_price_book(
        currency="USD",
        effective_from=date(2026, 6, 1),
        meter_prices={"vessel_month": Decimal("299.00"), "evidence_pack_export": Decimal("9.00")},
    )
    line = billing_service.price_line_item(meter_key="evidence_pack_export", quantity=Decimal("3"))
    assert line.unit_price == Decimal("9.00")
    assert line.total == Decimal("27.00")


def test_meter_positioning_labels_capacity_base_and_value_meters() -> None:
    catalog = maritime_billing_meter_catalog()
    assert catalog["capacity_guardrails"] == ["camera_capacity_tier", "managed_edge_node", "retained_evidence_gb", "managed_link_gb"]
    assert catalog["base_commercial_unit"] == "vessel_month"
    assert {"evidence_pack_export", "support_session_hour", "operational_incident_resolved"} <= set(catalog["value_meters"])


async def test_billing_routes_are_tenant_scoped(client: AsyncClient) -> None:
    response = await client.get("/api/v1/billing/accounts?tenant_id=00000000-0000-4000-8000-000000000099")
    assert response.status_code in {403, 404}


async def test_maritime_rollups_label_reseller_owner_charterer_and_vessel(client: AsyncClient) -> None:
    response = await client.get("/api/v1/maritime/billing/rollups")
    assert response.status_code == 200
    labels = response.json()["labels"]
    assert {"reseller", "fleet_manager", "owner", "charterer", "vessel"} <= set(labels)
    assert response.json()["meters"]["base_commercial_unit"] == "vessel_month"
```

Append this empty-registry API test to
`backend/tests/core/test_packless_empty_registry.py`:

```python
async def test_billing_routes_work_with_empty_pack_registry(empty_pack_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=empty_pack_app), base_url="http://test") as client:
        account_response = await client.post(
            "/api/v1/billing/accounts",
            json={"name": "Packless account", "node_ids": []},
        )
        meter_response = await client.get("/api/v1/billing/meters")

    assert account_response.status_code == 201
    assert meter_response.status_code == 200
    assert all(meter.get("pack_id") is None or meter["pack_id"] != "maritime-fleet" for meter in meter_response.json()["items"])
```

- [ ] **Step 2: Implement billing core**

Tables:

- `BillingNode`
- `BillingAccount`
- `Entitlement`
- `UsageMeter`
- `PriceBook`
- `UsageRecord`
- `InvoiceRun`
- `InvoiceLineItem`
- `BillingExport`

Service methods:

- `create_node()`
- `create_account()`
- `grant_entitlement()`
- `record_usage()`
- `create_price_book()`
- `run_invoice()`
- `export_billing()`

- [ ] **Step 3: Implement billing routes and maritime rollups**

Routes:

- `GET|POST /api/v1/billing/nodes`
- `GET|POST /api/v1/billing/accounts`
- `GET|POST /api/v1/billing/entitlements`
- `GET /api/v1/billing/meters`
- `GET|POST /api/v1/billing/price-books`
- `GET|POST /api/v1/billing/usage`
- `POST /api/v1/billing/invoice-runs`
- `GET /api/v1/billing/invoice-runs/{invoice_run_id}`
- `GET /api/v1/billing/exports/{export_id}`
- `GET /api/v1/maritime/billing/usage`
- `GET /api/v1/maritime/billing/rollups`

- [ ] **Step 4: Verify and commit**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/billing/test_billing_service.py tests/api/test_billing_routes.py tests/maritime/test_billing_support.py tests/core/test_packless_empty_registry.py::test_billing_routes_work_with_empty_pack_registry -q
python3 -m uv run ruff check src/argus/billing src/argus/maritime/billing.py tests/billing tests/api/test_billing_routes.py tests/maritime/test_billing_support.py tests/core/test_packless_empty_registry.py
python3 -m uv run mypy src/argus/billing src/argus/maritime/billing.py
cd /Users/yann.moren/vision
git add backend/src/argus/billing backend/src/argus/maritime/billing.py backend/src/argus/migrations/versions/0032_core_billing.py backend/src/argus/models/__init__.py backend/src/argus/api/v1/__init__.py backend/src/argus/services/app.py backend/tests/billing backend/tests/api/test_billing_routes.py backend/tests/maritime/test_billing_support.py backend/tests/core/test_packless_empty_registry.py
git commit -m "feat: add billing baseline and maritime rollups"
```

### Task 9: Core Support And Maritime Diagnostics

**Constraints:** `CC-1`, `CC-2`, `CC-7`

**Files:**
- Create: `backend/src/argus/support/contracts.py`
- Create: `backend/src/argus/support/tables.py`
- Create: `backend/src/argus/support/service.py`
- Create: `backend/src/argus/support/tunnel_transport.py`
- Create: `backend/src/argus/support/api.py`
- Create: `backend/src/argus/supervisor/support_tunnel.py`
- Create: `backend/src/argus/migrations/versions/0033_core_support.py`
- Create: `backend/src/argus/maritime/support.py`
- Modify: `backend/src/argus/core/events.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/support/test_support_service.py`
- Test: `backend/tests/api/test_support_routes.py`
- Test: `backend/tests/supervisor/test_support_tunnel_handoff.py`
- Test: `backend/tests/core/test_packless_empty_registry.py`

- [ ] **Step 1: Write failing support tests**

Tests:

```python
def test_packless_support_bundle_redacts_secrets(support_service: SupportService) -> None:
    bundle = support_service.generate_bundle(
        tenant_id=UUID("00000000-0000-4000-8000-000000000001"),
        site_id=UUID("00000000-0000-4000-8000-000000000002"),
        diagnostics={"rtsp_url": "rtsp://user:password@camera.local/stream", "api_key": "secret-token"},
    )
    serialized = json.dumps(bundle.payload)
    assert "password" not in serialized
    assert "secret-token" not in serialized
    assert "rtsp://user:****@camera.local/stream" in serialized


def test_support_session_records_billable_duration(support_service: SupportService) -> None:
    session = support_service.create_session(tenant_id=TENANT_ID, site_id=SITE_ID, operator_id="noc-1")
    closed = support_service.close_session(session.id, ended_at=session.started_at + timedelta(minutes=90))
    assert closed.billable_duration_minutes == 90
    assert closed.usage_meter_key == "support_session_hour"


def test_ssh_reverse_tunnel_transport_uses_node_local_credential_references() -> None:
    request = SshReverseTunnelTransport().build_request(
        node_id=UUID("00000000-0000-4000-8000-000000000030"),
        relay_host="noc-relay.mugetsu.tech",
        allowed_ports=[22, 8000],
        credential_ref="node-local:ssh/support-tunnel",
        expires_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )
    assert request.transport == "ssh_reverse"
    assert request.credential_ref == "node-local:ssh/support-tunnel"
    assert request.private_key is None
    assert "IdentityFile" not in json.dumps(request.model_dump())


def test_backend_does_not_invoke_ssh_directly(support_service: SupportService, monkeypatch: pytest.MonkeyPatch) -> None:
    invoked = False

    def fake_run(*args: object, **kwargs: object) -> None:
        nonlocal invoked
        invoked = True

    monkeypatch.setattr(subprocess, "run", fake_run)
    tunnel = support_service.request_tunnel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        node_id=NODE_ID,
        transport="ssh_reverse",
        credential_ref="node-local:ssh/support-tunnel",
        relay_host="noc-relay.mugetsu.tech",
        allowed_ports=[22, 8000],
    )

    assert tunnel.status == "requested"
    assert tunnel.dispatch_method in {"supervisor_poll", "nats_push"}
    assert invoked is False


def test_break_glass_records_reason_scope_actor_and_closure(support_service: SupportService) -> None:
    record = support_service.open_break_glass(reason="restore camera access", scope={"site_id": str(SITE_ID)}, actor_id="captain", approver_id="fleet-admin")
    closed = support_service.close_break_glass(record.id, closure_notes="rotated temporary credential")
    assert closed.reason == "restore camera access"
    assert closed.ended_at is not None
    assert closed.closure_notes == "rotated temporary credential"


def test_onboarding_checks_cover_identity_master_edge_camera_model_link_evidence_billing_support(support_service: SupportService) -> None:
    run = support_service.run_onboarding_checks(tenant_id=TENANT_ID, site_id=SITE_ID)
    assert {check.key for check in run.checks} >= {
        "identity",
        "master_readiness",
        "edge_pairing",
        "camera_reachability",
        "model_runtime",
        "link_state",
        "evidence_storage",
        "billing_entitlement",
        "support_readiness",
    }


async def test_support_routes_are_tenant_scoped(client: AsyncClient, foreign_bundle_id: UUID) -> None:
    response = await client.get(f"/api/v1/support/bundles/{foreign_bundle_id}")
    assert response.status_code == 404
```

Create `backend/tests/supervisor/test_support_tunnel_handoff.py` with the
supervisor-side counterpart:

```python
def test_supervisor_resolves_node_local_credential_and_invokes_ssh_reverse_transport(
    credential_store: NodeCredentialStore,
    process_adapter: FakeProcessAdapter,
) -> None:
    credential_store.put_reference("node-local:ssh/support-tunnel", private_key_path="/var/lib/vezor/ssh/support_tunnel")
    request = SupportTunnelRequest(
        tunnel_id=UUID("00000000-0000-4000-8000-000000000031"),
        node_id=NODE_ID,
        transport="ssh_reverse",
        relay_host="noc-relay.mugetsu.tech",
        allowed_ports=[22, 8000],
        credential_ref="node-local:ssh/support-tunnel",
        expires_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    result = SupervisorSupportTunnelRunner(credential_store=credential_store, process_adapter=process_adapter).open(request)

    assert result.status == "active"
    assert process_adapter.commands[0][:3] == ["ssh", "-N", "-R"]
    assert "/var/lib/vezor/ssh/support_tunnel" in process_adapter.commands[0]
    assert "PRIVATE KEY" not in " ".join(process_adapter.commands[0])
```

Append this empty-registry API test to
`backend/tests/core/test_packless_empty_registry.py`:

```python
async def test_support_routes_work_with_empty_pack_registry(empty_pack_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=empty_pack_app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/support/bundles",
            json={"site_id": "00000000-0000-4000-8000-000000000002", "include_logs": True},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload.get("pack_id") is None
    assert "vessel" not in json.dumps(payload).lower()
```

- [ ] **Step 2: Implement support core**

Tables:

- `SupportBundle`
- `SupportSession`
- `SupportTunnel`
- `BreakGlassAccessRecord`
- `OnboardingCheckRun`

Transport:

- `SupportTunnelTransport`
- `SshReverseTunnelTransport`
- no stored private keys or plaintext secrets in DB rows

- [ ] **Step 3: Implement support routes and maritime diagnostics**

Routes:

- `POST /api/v1/support/bundles`
- `GET /api/v1/support/bundles/{bundle_id}`
- `POST /api/v1/support/sessions`
- `PATCH /api/v1/support/sessions/{session_id}`
- `POST /api/v1/support/tunnels`
- `POST /api/v1/support/tunnels/{tunnel_id}/revoke`
- `POST /api/v1/support/break-glass`
- `POST /api/v1/support/break-glass/{record_id}/close`
- `GET /api/v1/support/onboarding-checks`
- `POST /api/v1/support/onboarding-checks/run`
- `GET /api/v1/maritime/support/checklist`
- `GET /api/v1/maritime/support/diagnostics`

- [ ] **Step 4: Verify and commit**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/support/test_support_service.py tests/api/test_support_routes.py tests/supervisor/test_support_tunnel_handoff.py tests/core/test_packless_empty_registry.py::test_support_routes_work_with_empty_pack_registry -q
python3 -m uv run ruff check src/argus/support src/argus/supervisor/support_tunnel.py src/argus/maritime/support.py tests/support tests/api/test_support_routes.py tests/supervisor/test_support_tunnel_handoff.py tests/core/test_packless_empty_registry.py
python3 -m uv run mypy src/argus/support src/argus/supervisor/support_tunnel.py src/argus/maritime/support.py
cd /Users/yann.moren/vision
git add backend/src/argus/support backend/src/argus/supervisor/support_tunnel.py backend/src/argus/maritime/support.py backend/src/argus/migrations/versions/0033_core_support.py backend/src/argus/core/events.py backend/src/argus/api/v1/__init__.py backend/src/argus/services/app.py backend/tests/support backend/tests/api/test_support_routes.py backend/tests/supervisor/test_support_tunnel_handoff.py backend/tests/core/test_packless_empty_registry.py
git commit -m "feat: add support baseline and maritime diagnostics"
```

## Gate 4: Full Working Product

### Task 10: OpenAPI And Frontend Hooks

**Constraints:** `CC-9`

**Files:**
- Create: `backend/src/argus/scripts/export_openapi_schema.py`
- Test: `backend/tests/api/test_openapi_export.py`
- Create: `frontend/src/lib/openapi.json`
- Modify: `frontend/src/lib/api.generated.ts`
- Modify: `frontend/package.json`
- Create: `frontend/src/hooks/use-link.ts`
- Create: `frontend/src/hooks/use-fleet.ts`
- Create: `frontend/src/hooks/use-billing.ts`
- Create: `frontend/src/hooks/use-support.ts`
- Create: `frontend/src/hooks/use-maritime.ts`
- Test: `frontend/src/hooks/use-maritime.test.ts`
- Test: `frontend/src/hooks/use-billing.test.ts`
- Test: `frontend/src/hooks/use-support.test.ts`

- [ ] **Step 1: Export OpenAPI as a file artifact**

Create `backend/tests/api/test_openapi_export.py`:

```python
def test_openapi_export_writes_fleetops_schema(tmp_path: Path) -> None:
    output_path = tmp_path / "openapi.json"

    export_openapi_schema(output_path)

    schema = json.loads(output_path.read_text())
    paths = schema["paths"]
    assert "/api/v1/maritime/runtime" in paths
    assert "/api/v1/link/sites/{site_id}/status" in paths
    assert "/api/v1/billing/invoice-runs" in paths
    assert "/api/v1/support/bundles" in paths
```

Implement `backend/src/argus/scripts/export_openapi_schema.py` so it imports
the FastAPI app factory, builds the app without starting a server, and writes a
deterministic sorted JSON schema.

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_openapi_export.py -q
python3 -m uv run python -m argus.scripts.export_openapi_schema ../frontend/src/lib/openapi.json
```

Expected:

- `frontend/src/lib/openapi.json` exists.
- The file includes `/api/v1/link`, `/api/v1/fleet`, `/api/v1/billing`,
  `/api/v1/support`, and `/api/v1/maritime` paths.

- [ ] **Step 2: Regenerate API types from the file artifact**

Modify `frontend/package.json`:

```json
"generate:api": "openapi-typescript src/lib/openapi.json -o src/lib/api.generated.ts"
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm generate:api
```

- [ ] **Step 3: Write hook tests and implement hooks**

Write hook tests that mock `apiClient` and assert exact endpoint families:

```typescript
test("useMaritimeRuntime queries the maritime runtime endpoint", async () => {
  apiClient.GET.mockResolvedValue({ data: { pack_id: "maritime-fleet", enabled: true } });
  renderHookWithQueryClient(() => useMaritimeRuntime());
  await waitFor(() => expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/maritime/runtime"));
});

test("useVesselDetail composes vessel, telemetry, link, evidence, billing, and support queries", async () => {
  const vesselId = "00000000-0000-4000-8000-000000000010";
  renderHookWithQueryClient(() => useFleetOpsVesselDetail(vesselId));
  await waitFor(() => {
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/maritime/vessels/{vessel_id}", { params: { path: { vessel_id: vesselId } } });
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/maritime/vessels/{vessel_id}/telemetry", { params: { path: { vessel_id: vesselId } } });
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/maritime/vessels/{vessel_id}/link-status", { params: { path: { vessel_id: vesselId } } });
  });
});

test("billing and support hooks keep core routes generic", async () => {
  renderHookWithQueryClient(() => useBillingInvoiceRuns());
  renderHookWithQueryClient(() => useSupportBundles());
  await waitFor(() => {
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/billing/invoice-runs");
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/support/bundles");
  });
});
```

- [ ] **Step 4: Verify and commit**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_openapi_export.py -q
cd /Users/yann.moren/vision/frontend
corepack pnpm test -- use-maritime use-billing use-support --run
corepack pnpm build
cd /Users/yann.moren/vision
git add backend/src/argus/scripts/export_openapi_schema.py backend/tests/api/test_openapi_export.py frontend/package.json frontend/src/lib/openapi.json frontend/src/lib/api.generated.ts frontend/src/hooks/use-link.ts frontend/src/hooks/use-fleet.ts frontend/src/hooks/use-billing.ts frontend/src/hooks/use-support.ts frontend/src/hooks/use-maritime.ts frontend/src/hooks/*.test.ts
git commit -m "feat: add fleetops frontend hooks"
```

### Task 11: FleetOps UI

**Constraints:** `CC-3`, `CC-6`, `CC-9`, `CC-10`

**Files:**
- Create: `frontend/src/pages/FleetOps.tsx`
- Create: `frontend/src/pages/FleetOpsVessels.tsx`
- Create: `frontend/src/pages/FleetOpsVesselDetail.tsx`
- Create: `frontend/src/pages/FleetOpsEvidence.tsx`
- Create: `frontend/src/pages/FleetOpsBilling.tsx`
- Create: `frontend/src/pages/FleetOpsSupport.tsx`
- Create: `frontend/src/pages/FleetOpsOnboarding.tsx`
- Create: `frontend/src/components/fleetops/FleetOverviewPanel.tsx`
- Create: `frontend/src/components/fleetops/VesselSummaryTable.tsx`
- Create: `frontend/src/components/fleetops/VoyageTimeline.tsx`
- Create: `frontend/src/components/fleetops/LinkOperationsPanel.tsx`
- Create: `frontend/src/components/fleetops/EvidenceExportBuilder.tsx`
- Create: `frontend/src/components/fleetops/BillingRollupPanel.tsx`
- Create: `frontend/src/components/fleetops/SupportDiagnosticsPanel.tsx`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/components/layout/workspace-nav.ts`
- Test: `frontend/src/pages/FleetOps.test.tsx`
- Test: `frontend/src/pages/FleetOpsVesselDetail.test.tsx`
- Test: `frontend/src/pages/FleetOpsBilling.test.tsx`
- Test: `frontend/src/pages/FleetOpsSupport.test.tsx`

- [ ] **Step 1: Write failing page tests**

Tests:

```typescript
test("FleetOps overview renders vessels, link state, evidence queue, billing, and support status", async () => {
  renderWithProviders(<FleetOps />);
  expect(await screen.findByRole("heading", { name: /FleetOps/i })).toBeInTheDocument();
  expect(screen.getByText(/MV Resolute/i)).toBeInTheDocument();
  expect(screen.getByText(/port wifi|satellite degraded|dark|recovering/i)).toBeInTheDocument();
  expect(screen.getByText(/Evidence queue/i)).toBeInTheDocument();
  expect(screen.getByText(/Current billable usage/i)).toBeInTheDocument();
  expect(screen.getByText(/Open support sessions/i)).toBeInTheDocument();
});

test("Vessel detail renders voyage timeline, templates, telemetry, and evidence context", async () => {
  renderWithProviders(<FleetOpsVesselDetail />);
  expect(await screen.findByText(/Voyage timeline/i)).toBeInTheDocument();
  expect(screen.getByText(/Gangway access/i)).toBeInTheDocument();
  expect(screen.getByText(/Latest AIS/i)).toBeInTheDocument();
  expect(screen.getByText(/Evidence context/i)).toBeInTheDocument();
});

test("Billing page separates capacity guardrails, vessel month, and value meters", async () => {
  renderWithProviders(<FleetOpsBilling />);
  expect(await screen.findByText(/Value meters/i)).toBeInTheDocument();
  expect(screen.getByText(/vessel month/i)).toBeInTheDocument();
  expect(screen.getByText(/camera capacity tier/i)).toBeInTheDocument();
  expect(screen.getByText(/evidence pack export/i)).toBeInTheDocument();
});

test("Support page renders bundles, tunnel lifecycle, break-glass, and onboarding checks", async () => {
  renderWithProviders(<FleetOpsSupport />);
  expect(await screen.findByText(/Support bundles/i)).toBeInTheDocument();
  expect(screen.getByText(/Tunnel lifecycle/i)).toBeInTheDocument();
  expect(screen.getByText(/Break-glass/i)).toBeInTheDocument();
  expect(screen.getByText(/Onboarding checks/i)).toBeInTheDocument();
});

test("traffic public space route is not present in workspace navigation", () => {
  const labels = workspaceNavItems.map((item) => item.label.toLowerCase());
  expect(labels.join(" ")).not.toContain("traffic");
  expect(labels.join(" ")).not.toContain("public space");
});
```

- [ ] **Step 2: Implement FleetOps routes and components**

Reuse:

- `AppShell`
- `WorkspaceBand`
- `WorkspaceSurface`
- `Button`
- generated OpenAPI types
- TanStack Query hooks

Do not create a new component system or landing page.

- [ ] **Step 3: Verify and commit**

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test -- FleetOps --run
corepack pnpm build
cd /Users/yann.moren/vision
git add frontend/src/pages/FleetOps*.tsx frontend/src/pages/FleetOps*.test.tsx frontend/src/components/fleetops frontend/src/app/router.tsx frontend/src/components/layout/workspace-nav.ts
git commit -m "feat: add fleetops workspace"
```

### Task 12: End-To-End Smoke, Installer, Docs

**Constraints:** `CC-1` through `CC-10`

**Files:**
- Create: `backend/tests/e2e/test_maritime_fleetops_smoke.py`
- Create: `frontend/e2e/fleetops.spec.ts`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/product-installer-and-first-run-guide.md`
- Modify: `installer/tests/test_macos_master_artifacts.py`
- Modify: `installer/tests/test_linux_master_artifacts.py`

- [ ] **Step 1: Write backend end-to-end smoke**

Test flow:

1. Create generic site.
2. Create vessel linked to site.
3. Create fleet hierarchy and exception.
4. Create billing account, entitlement, price book.
5. Set link budget and queue items.
6. Apply gangway template to camera.
7. Create voyage and port call.
8. Ingest AIS and carrier state.
9. Create incident fixture.
10. Resolve maritime context.
11. Export evidence pack.
12. Generate usage and invoice run.
13. Create support bundle, onboarding check, tunnel, break-glass record.

- [ ] **Step 2: Write frontend Playwright smoke**

Use the real development stack, not mocked API fixtures. The smoke should catch
frontend/backend/OpenAPI/auth wiring issues, so it must run against
`infra/docker-compose.dev.yml`.

Start the stack:

```bash
cd /Users/yann.moren/vision
docker compose -f infra/docker-compose.dev.yml up -d postgres redis nats minio keycloak backend frontend
```

Wait for health:

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:3000
```

Create `frontend/e2e/fleetops.spec.ts` so it logs in through the dev realm or
loads an existing authenticated storage state, then tests route `/fleetops`
against the real backend:

```typescript
test("FleetOps product smoke covers overview detail evidence billing and support", async ({ page }) => {
  await page.goto("/fleetops");
  await expect(page.getByRole("heading", { name: /FleetOps/i })).toBeVisible();
  await page.getByRole("link", { name: /MV Resolute/i }).click();
  await expect(page.getByText(/Voyage timeline/i)).toBeVisible();
  await page.getByRole("link", { name: /Evidence/i }).click();
  await expect(page.getByText(/scene contract/i)).toBeVisible();
  await expect(page.getByText(/link passport/i)).toBeVisible();
  await page.getByRole("link", { name: /Billing/i }).click();
  await expect(page.getByText(/vessel month/i)).toBeVisible();
  await expect(page.getByText(/evidence pack export/i)).toBeVisible();
  await page.getByRole("link", { name: /Support/i }).click();
  await expect(page.getByText(/Onboarding checks/i)).toBeVisible();
  await expect(page.getByText(/Tunnel lifecycle/i)).toBeVisible();
});
```

Do not switch this smoke to route-level mocking. Mocked UI tests belong in Task
11; Task 12 is the real product integration check.

- [ ] **Step 3: Update docs and installer checks**

Docs must explain:

- MacBook/Linux master plus edge path.
- FleetOps entitlement and billing export.
- Support bundle and tunnel transport.
- Packless home/lab validation remains non-product.
- Traffic remains manifest-only.

Installer tests must ensure `packs/` and FleetOps routes/API assets remain packaged.

- [ ] **Step 4: Run full verification**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link tests/fleet tests/billing tests/support tests/maritime tests/api/test_link_routes.py tests/api/test_fleet_routes.py tests/api/test_billing_routes.py tests/api/test_support_routes.py tests/api/test_maritime_routes.py tests/e2e/test_maritime_fleetops_smoke.py -q
python3 -m uv run ruff check src/argus/link src/argus/fleet src/argus/billing src/argus/support src/argus/maritime tests/link tests/fleet tests/billing tests/support tests/maritime tests/e2e
python3 -m uv run mypy src/argus/link src/argus/fleet src/argus/billing src/argus/support src/argus/maritime
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run
corepack pnpm build
corepack pnpm exec playwright test e2e/fleetops.spec.ts
cd /Users/yann.moren/vision/installer
python3 -m uv run pytest tests -q
```

- [ ] **Step 5: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/tests/e2e/test_maritime_fleetops_smoke.py frontend/e2e/fleetops.spec.ts docs/operator-deployment-playbook.md docs/product-installer-and-first-run-guide.md installer/tests/test_macos_master_artifacts.py installer/tests/test_linux_master_artifacts.py
git commit -m "test: add fleetops product smoke coverage"
```

## Final Verification Before Merge

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link tests/fleet tests/billing tests/support tests/maritime tests/core/test_full_product_boundaries.py -q
python3 -m uv run pytest tests/core/test_packless_empty_registry.py -q
python3 -m uv run ruff check src/argus/link src/argus/fleet src/argus/billing src/argus/support src/argus/maritime tests/link tests/fleet tests/billing tests/support tests/maritime
python3 -m uv run mypy src/argus/link src/argus/fleet src/argus/billing src/argus/support src/argus/maritime
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run
corepack pnpm build
cd /Users/yann.moren/vision
git status --short
```

Expected:

- Backend tests pass.
- Frontend tests and build pass.
- No traffic runtime files exist.
- No home-lab pack exists.
- Core link/fleet/billing/support tests include packless variants.
- Empty-registry app tests prove core link/fleet/billing/support APIs run with
  no runtime-enabled packs.
- Only intended files are staged or committed.

## Spec Traceability

- Product goal and full scope: Tasks 1-12, with final smoke in Task 12.
- Core `argus.link`: Task 1 plus FleetOps composition in Tasks 6, 7, 10, 11.
- Core `argus.fleet`: Task 2 plus FleetOps overview in Tasks 4, 10, 11.
- Maritime runtime boundary: Task 3.
- Vessels, voyages, port calls, roles, rotations: Task 4.
- Scene template application over core camera primitives: Task 5.
- AIS, NMEA, generic carrier adapters, carrier-aware link selection: Task 6.
- Maritime evidence context and evidence pack export: Task 7.
- Billing accounts, entitlements, meters, price books, invoice lines, exports,
  and maritime rollups: Task 8.
- Support bundles, sessions, `ssh_reverse` tunnel lifecycle, break-glass, and
  onboarding checks: Task 9.
- FleetOps frontend hooks and generated OpenAPI types: Task 10.
- FleetOps workspace UI, including link, evidence, billing, support, and
  onboarding surfaces: Task 11.
- Installer, docs, product runbooks, and end-to-end smoke: Task 12.

## Constraint Traceability

| Constraint | Enforced by |
|---|---|
| `CC-1 Packless Core Compatibility` | Task 1 link service/API no-pack tests; Task 2 fleet no-pack tests; Task 8 billing no-pack tests; Task 9 support no-pack tests; `tests/core/test_packless_empty_registry.py`; final verification empty-registry run. |
| `CC-2 Pack Boundary` | Task 3 runtime/boundary scanner; Task 4 maritime-only entity tables; Task 5 template mapping; Task 7 evidence metadata; Task 8 maritime billing rollups; Task 9 maritime diagnostics. |
| `CC-3 Traffic Boundary` | Task 3 route/module absence test; Task 11 navigation absence test; Task 12 docs and smoke checks. |
| `CC-4 Link Is Core` | Task 1 `argus.link` service/API; Task 6 carrier selection composes link state without owning link queue semantics; Task 7 link passport integration. |
| `CC-5 Fleet Is Core` | Task 2 `argus.fleet` service/API; Task 4 vessel-to-site projection; Task 11 FleetOps labels over generic site/fleet primitives. |
| `CC-6 Billing Positioning` | Task 8 meter catalog tests and invoice/export behavior; Task 11 FleetOps billing UI tests. |
| `CC-7 Support Tunnel` | Task 9 backend-does-not-ssh test, supervisor handoff test, node-local credential reference test, and support route tests. |
| `CC-8 Evidence Integrity` | Task 1 link passport hash tests; Task 5 scene template/core primitive tests; Task 7 no-rehash evidence export tests. |
| `CC-9 Frontend Reuse` | Task 10 OpenAPI file generation and hooks; Task 11 AppShell/workspace/TanStack Query reuse tests. |
| `CC-10 Full Product Scope` | Task 12 backend e2e, frontend Playwright smoke, installer checks, and docs updates. |

## Self-Review

Spec coverage:

- Covered: packless compatibility, pack boundary, traffic boundary, link core,
  fleet core, billing positioning, support tunnel transport, evidence integrity,
  frontend reuse, full-product smoke.
- Covered: generic HTTP/webhook/file carrier adapters; no proprietary carrier
  SDK dependency.
- Covered: MacBook/Linux master and edge installer checks in Task 12.
- Covered: no home-lab pack; home/lab behavior is validated through packless
  core tests in Tasks 1, 2, 8, and 9.

Placeholder scan:

- Search the plan for the red-flag phrases listed in the Writing Plans skill.
  Expected: no matches except quoted references from that skill if an engineer
  intentionally copies the checklist elsewhere.

Type and command consistency:

- Backend commands use `python3 -m uv run pytest`, `ruff`, and `mypy`, matching
  existing backend workflow.
- Frontend commands use existing package scripts: `corepack pnpm test --run`,
  `corepack pnpm build`, `corepack pnpm lint`, and
  `corepack pnpm generate:api`.
- Playwright smoke path is `frontend/e2e/fleetops.spec.ts`; run it from
  `frontend/` as `corepack pnpm exec playwright test e2e/fleetops.spec.ts`.

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.
