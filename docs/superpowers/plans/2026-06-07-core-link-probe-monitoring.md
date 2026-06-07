# Core Link Probe Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Core Link probe monitoring understandable by separating link paths, monitoring targets, probe sources, automated checks, manual samples, and sample deletion.

**Architecture:** Keep monitoring targets inside existing link path metadata, add structured fields to `link_health_probes`, and expose explicit APIs for manual samples, soft deletion, and backend synthetic run-now checks. Frontend copy changes from a flat "Record probe" history to a Monitoring panel with target cards and sample actions.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, SQLAlchemy/Alembic, httpx, asyncio, React 19, TypeScript, TanStack Query, Vitest, Testing Library, pnpm, uv.

---

## Constraints

- Preserve CC-1 through CC-10 constraints from the FleetOps/Core Link plans.
- Do not add maritime, traffic, camera, evidence, detection, carrier SDK, payment, or provider-specific SD-WAN semantics to Core Link.
- Do not run probes from the browser.
- Do not implement raw ICMP in the central backend.
- Keep existing `source` probe field for compatibility.
- Soft-delete probe samples instead of hard-deleting rows.
- Do not stage unrelated scratch files or directories.

## File Structure

Backend:

- Create `backend/src/argus/migrations/versions/0038_core_link_probe_monitoring.py`
  - Add structured probe source/target/delete columns to `link_health_probes`.
- Modify `backend/src/argus/link/tables.py`
  - Add mapped columns for probe target/source fields and `deleted_at`.
- Modify `backend/src/argus/link/contracts.py`
  - Extend `LinkHealthProbeRecord` fields and add source/sample literals.
- Modify `backend/src/argus/link/api.py`
  - Extend `LinkProbeCreate`.
  - Add delete probe route.
  - Add run target route.
  - Include structured fields in `_probe_payload`.
- Modify `backend/src/argus/link/service.py`
  - Extend probe record/create/list/latest behavior.
  - Add soft-delete methods.
  - Add helper to locate a target in link path metadata.
- Create `backend/src/argus/link/probe_runner.py`
  - Implement backend synthetic TCP/HTTP/HTTPS checks and result conversion.
- Modify `backend/tests/link/test_link_service.py`
  - Add service tests for structured samples and soft delete.
- Create `backend/tests/link/test_probe_runner.py`
  - Add runner tests for HTTP/TCP success/failure and unsupported ICMP.
- Modify `backend/tests/api/test_link_routes.py`
  - Add route tests for structured sample creation, soft delete, and run-now.

Frontend:

- Modify `frontend/src/hooks/use-link.ts`
  - Add `useDeleteLinkProbe`.
  - Add `useRunLinkProbeTarget`.
- Modify `frontend/src/components/link/types.ts`
  - Extend monitoring target metadata helpers with target IDs and monitoring config.
  - Add probe sample display/source helpers.
- Modify `frontend/src/components/link/LinkActionDialogs.tsx`
  - Rename probe dialog to manual sample dialog and add target/source fields.
- Modify `frontend/src/components/link/LinkProbePanel.tsx`
  - Rename panel to Monitoring.
  - Render target cards and sample rows.
  - Add run-now, add-manual-sample, and delete-sample actions.
- Modify `frontend/src/pages/Links.test.tsx`
  - Add/adjust tests for monitoring target cards, manual samples, run-now, and delete.

## Task 1: Backend Structured Probe Samples And Soft Delete

- [ ] **Step 1: Write failing service tests**

Add to `backend/tests/link/test_link_service.py`:

```python
def test_record_probe_stores_structured_source_and_target(link_service: LinkService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")

    probe = link_service.record_probe(
        tenant_id=tenant_id,
        site_id=site_id,
        latency_ms=42,
        throughput_mbps=180.0,
        packet_loss_percent=0.1,
        reachable=True,
        source="manual:operator-console",
        target_id="target-vezor-ingest",
        target_label="Vezor ingest",
        target_address="ingest.example.vezor",
        probe_type="https",
        source_type="manual",
        source_label="operator-console",
        sample_kind="manual",
    )

    assert probe.target_id == "target-vezor-ingest"
    assert probe.target_label == "Vezor ingest"
    assert probe.target_address == "ingest.example.vezor"
    assert probe.probe_type == "https"
    assert probe.source_type == "manual"
    assert probe.source_label == "operator-console"
    assert probe.sample_kind == "manual"
    assert probe.deleted_at is None


def test_delete_probe_hides_sample_from_history_and_latest(link_service: LinkService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")
    probe = link_service.record_probe(
        tenant_id=tenant_id,
        site_id=site_id,
        latency_ms=42,
        throughput_mbps=180.0,
        packet_loss_percent=0.1,
        reachable=True,
        source="manual:operator-console",
        source_type="manual",
        source_label="operator-console",
        sample_kind="manual",
    )

    deleted = link_service.delete_probe(
        tenant_id=tenant_id,
        site_id=site_id,
        probe_id=probe.id,
    )

    assert deleted is not None
    assert deleted.deleted_at is not None
    assert link_service.list_probes(tenant_id=tenant_id, site_id=site_id) == []
    assert link_service.latest_probe(tenant_id=tenant_id, site_id=site_id) is None
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_record_probe_stores_structured_source_and_target tests/link/test_link_service.py::test_delete_probe_hides_sample_from_history_and_latest -q
```

Expected: FAIL because `record_probe` does not accept structured fields and `delete_probe` does not exist.

- [ ] **Step 2: Add migration and table columns**

Create `backend/src/argus/migrations/versions/0038_core_link_probe_monitoring.py`:

```python
"""Add core link probe monitoring fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038_core_link_probe_monitoring"
down_revision = "0037_core_link_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("link_health_probes", sa.Column("target_id", sa.String(length=96), nullable=True))
    op.add_column("link_health_probes", sa.Column("target_label", sa.String(length=160), nullable=True))
    op.add_column("link_health_probes", sa.Column("target_address", sa.Text(), nullable=True))
    op.add_column("link_health_probes", sa.Column("probe_type", sa.String(length=16), nullable=True))
    op.add_column(
        "link_health_probes",
        sa.Column("source_type", sa.String(length=32), server_default="manual", nullable=False),
    )
    op.add_column("link_health_probes", sa.Column("source_label", sa.String(length=128), nullable=True))
    op.add_column(
        "link_health_probes",
        sa.Column("sample_kind", sa.String(length=32), server_default="manual", nullable=False),
    )
    op.add_column("link_health_probes", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_link_health_probes_target", "link_health_probes", ["target_id"])
    op.create_index("ix_link_health_probes_deleted", "link_health_probes", ["deleted_at"])
    op.create_check_constraint(
        "ck_link_health_probes_probe_type",
        "link_health_probes",
        "probe_type IS NULL OR probe_type IN ('icmp', 'tcp', 'http', 'https', 'manual')",
    )
    op.create_check_constraint(
        "ck_link_health_probes_source_type",
        "link_health_probes",
        "source_type IN ('manual', 'backend_synthetic', 'edge_agent', 'provider_api', 'import')",
    )
    op.create_check_constraint(
        "ck_link_health_probes_sample_kind",
        "link_health_probes",
        "sample_kind IN ('manual', 'automated', 'imported')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_link_health_probes_sample_kind", "link_health_probes", type_="check")
    op.drop_constraint("ck_link_health_probes_source_type", "link_health_probes", type_="check")
    op.drop_constraint("ck_link_health_probes_probe_type", "link_health_probes", type_="check")
    op.drop_index("ix_link_health_probes_deleted", table_name="link_health_probes")
    op.drop_index("ix_link_health_probes_target", table_name="link_health_probes")
    op.drop_column("link_health_probes", "deleted_at")
    op.drop_column("link_health_probes", "sample_kind")
    op.drop_column("link_health_probes", "source_label")
    op.drop_column("link_health_probes", "source_type")
    op.drop_column("link_health_probes", "probe_type")
    op.drop_column("link_health_probes", "target_address")
    op.drop_column("link_health_probes", "target_label")
    op.drop_column("link_health_probes", "target_id")
```

Modify `backend/src/argus/link/tables.py`:

```python
class LinkHealthProbe(UUIDPrimaryKeyMixin, Base):
    # existing columns remain
    target_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    target_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    probe_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sample_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 3: Extend contracts and service methods**

Modify `backend/src/argus/link/contracts.py`:

```python
LinkProbeType = Literal["icmp", "tcp", "http", "https", "manual"]
LinkProbeSourceType = Literal["manual", "backend_synthetic", "edge_agent", "provider_api", "import"]
LinkProbeSampleKind = Literal["manual", "automated", "imported"]


@dataclass(frozen=True, slots=True)
class LinkHealthProbeRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    connection_id: UUID | None
    latency_ms: int
    throughput_mbps: float
    packet_loss_percent: float
    reachable: bool
    source: str
    recorded_at: datetime
    target_id: str | None = None
    target_label: str | None = None
    target_address: str | None = None
    probe_type: LinkProbeType | None = None
    source_type: LinkProbeSourceType = "manual"
    source_label: str | None = None
    sample_kind: LinkProbeSampleKind = "manual"
    deleted_at: datetime | None = None
```

Modify `backend/src/argus/link/service.py`:

- Extend `record_probe` and `arecord_probe` signatures with the structured fields from the tests.
- Set defaults: `source_type="manual"`, `sample_kind="manual"`, `source_label=None`.
- Add `delete_probe` and `adelete_probe`.
- Filter deleted probes in `list_probes`, `_list_probe_rows`, `latest_probe`, and `alatest_probe`.
- Extend `_probe_record`.

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_record_probe_stores_structured_source_and_target tests/link/test_link_service.py::test_delete_probe_hides_sample_from_history_and_latest -q
```

Expected: PASS.

- [ ] **Step 4: Commit backend service contract**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/migrations/versions/0038_core_link_probe_monitoring.py backend/src/argus/link/tables.py backend/src/argus/link/contracts.py backend/src/argus/link/service.py backend/tests/link/test_link_service.py
git commit -m "feat: structure core link probe samples"
```

## Task 2: Probe API Routes

- [ ] **Step 1: Write failing API route tests**

Add to `backend/tests/api/test_link_routes.py`:

```python
async def test_create_link_probe_accepts_structured_source_fields(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probes",
        json={
            "latency_ms": 42,
            "throughput_mbps": 180.0,
            "packet_loss_percent": 0.1,
            "reachable": True,
            "source": "manual:operator-console",
            "target_id": "target-vezor-ingest",
            "target_label": "Vezor ingest",
            "target_address": "ingest.example.vezor",
            "probe_type": "https",
            "source_type": "manual",
            "source_label": "operator-console",
            "sample_kind": "manual",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["target_id"] == "target-vezor-ingest"
    assert payload["source_type"] == "manual"
    assert payload["sample_kind"] == "manual"
    assert payload["deleted_at"] is None
```

Add:

```python
async def test_delete_link_probe_hides_sample(client: AsyncClient) -> None:
    created = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probes",
        json={
            "latency_ms": 42,
            "throughput_mbps": 180.0,
            "packet_loss_percent": 0.1,
            "reachable": True,
            "source": "manual:operator-console",
        },
    )
    probe_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/link/sites/{KNOWN_SITE_ID}/probes/{probe_id}")
    history = await client.get(f"/api/v1/link/sites/{KNOWN_SITE_ID}/probes")

    assert deleted.status_code == 204
    assert history.status_code == 200
    assert history.json() == []
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py -q
```

Expected: FAIL because route/schema fields and delete route do not exist.

- [ ] **Step 2: Extend API schema and payloads**

Modify `backend/src/argus/link/api.py`:

```python
class LinkProbeCreate(BaseModel):
    connection_id: UUID | None = None
    latency_ms: int = Field(ge=0)
    throughput_mbps: float = Field(ge=0)
    packet_loss_percent: float = Field(ge=0)
    reachable: bool
    source: str = Field(min_length=1, max_length=128)
    target_id: str | None = Field(default=None, max_length=96)
    target_label: str | None = Field(default=None, max_length=160)
    target_address: str | None = None
    probe_type: Literal["icmp", "tcp", "http", "https", "manual"] | None = None
    source_type: Literal["manual", "backend_synthetic", "edge_agent", "provider_api", "import"] = "manual"
    source_label: str | None = Field(default=None, max_length=128)
    sample_kind: Literal["manual", "automated", "imported"] = "manual"
```

Pass the new fields to `services.link.arecord_probe`.

Add route:

```python
@router.delete("/sites/{site_id}/probes/{probe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link_probe(
    site_id: UUID,
    probe_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    await _ensure_tenant_site(services, tenant_context, site_id)
    deleted = await services.link.adelete_probe(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        probe_id=probe_id,
    )
    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Probe sample not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Import `Response` from FastAPI.

Extend `_probe_payload` with every new field.

- [ ] **Step 3: Verify API task**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py tests/link/test_link_service.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit API routes**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/api.py backend/tests/api/test_link_routes.py
git commit -m "feat: expose core link probe sample controls"
```

## Task 3: Backend Synthetic Probe Runner

- [ ] **Step 1: Write failing runner tests**

Create `backend/tests/link/test_probe_runner.py`:

```python
import asyncio

import httpx
import pytest

from argus.link.probe_runner import ProbeTarget, run_backend_probe


@pytest.mark.asyncio
async def test_backend_probe_records_https_success() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(204))
    async with httpx.AsyncClient(transport=transport) as client:
        result = await run_backend_probe(
            ProbeTarget(
                target_id="target-1",
                label="Vezor ingest",
                address="https://ingest.example.vezor/health",
                probe_type="https",
                port=443,
            ),
            http_client=client,
        )

    assert result.reachable is True
    assert result.packet_loss_percent == 0.0
    assert result.probe_type == "https"
    assert result.source_type == "backend_synthetic"
    assert result.sample_kind == "automated"


@pytest.mark.asyncio
async def test_backend_probe_rejects_icmp() -> None:
    result = await run_backend_probe(
        ProbeTarget(
            target_id="target-1",
            label="Gateway",
            address="203.0.113.10",
            probe_type="icmp",
            port=None,
        ),
    )

    assert result.reachable is False
    assert result.failure_reason == "backend_synthetic_icmp_unsupported"
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_probe_runner.py -q
```

Expected: FAIL because `argus.link.probe_runner` does not exist.

- [ ] **Step 2: Implement runner**

Create `backend/src/argus/link/probe_runner.py`:

```python
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

from argus.link.contracts import LinkProbeSampleKind, LinkProbeSourceType


@dataclass(frozen=True, slots=True)
class ProbeTarget:
    target_id: str
    label: str
    address: str
    probe_type: str
    port: int | None = None


@dataclass(frozen=True, slots=True)
class ProbeResult:
    target_id: str
    target_label: str
    target_address: str
    probe_type: str
    latency_ms: int
    throughput_mbps: float
    packet_loss_percent: float
    reachable: bool
    source: str
    source_type: LinkProbeSourceType
    source_label: str
    sample_kind: LinkProbeSampleKind
    failure_reason: str | None = None


async def run_backend_probe(
    target: ProbeTarget,
    *,
    source_label: str = "backend:primary",
    timeout_seconds: float = 5.0,
    http_client: httpx.AsyncClient | None = None,
) -> ProbeResult:
    started = time.perf_counter()
    if target.probe_type == "icmp":
        return _result(target, 0, False, source_label, "backend_synthetic_icmp_unsupported")
    if target.probe_type in {"http", "https"}:
        return await _run_http_probe(target, started, source_label, timeout_seconds, http_client)
    if target.probe_type == "tcp":
        return await _run_tcp_probe(target, started, source_label, timeout_seconds)
    return _result(target, 0, False, source_label, "unsupported_probe_type")
```

Add the helper functions in the same file:

```python
async def _run_http_probe(
    target: ProbeTarget,
    started: float,
    source_label: str,
    timeout_seconds: float,
    http_client: httpx.AsyncClient | None,
) -> ProbeResult:
    client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
    owns_client = http_client is None
    try:
        url = target.address
        if not url.startswith(("http://", "https://")):
            url = f"{target.probe_type}://{target.address}"
        response = await client.get(url)
        return _result(
            target,
            _elapsed_ms(started),
            response.status_code < 500,
            source_label,
            None if response.status_code < 500 else f"http_status_{response.status_code}",
        )
    except httpx.HTTPError as exc:
        return _result(target, _elapsed_ms(started), False, source_label, exc.__class__.__name__)
    finally:
        if owns_client:
            await client.aclose()


async def _run_tcp_probe(
    target: ProbeTarget,
    started: float,
    source_label: str,
    timeout_seconds: float,
) -> ProbeResult:
    if target.port is None:
        return _result(target, 0, False, source_label, "tcp_port_required")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target.address, target.port),
            timeout=timeout_seconds,
        )
        writer.close()
        await writer.wait_closed()
        del reader
        return _result(target, _elapsed_ms(started), True, source_label, None)
    except (OSError, TimeoutError, asyncio.TimeoutError) as exc:
        return _result(target, _elapsed_ms(started), False, source_label, exc.__class__.__name__)


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _result(
    target: ProbeTarget,
    latency_ms: int,
    reachable: bool,
    source_label: str,
    failure_reason: str | None,
) -> ProbeResult:
    return ProbeResult(
        target_id=target.target_id,
        target_label=target.label,
        target_address=target.address,
        probe_type=target.probe_type,
        latency_ms=latency_ms,
        throughput_mbps=0.0,
        packet_loss_percent=0.0 if reachable else 100.0,
        reachable=reachable,
        source=f"backend_synthetic:{source_label}",
        source_type="backend_synthetic",
        source_label=source_label,
        sample_kind="automated",
        failure_reason=failure_reason,
    )
```

HTTP success means status code below 500. TCP success means `asyncio.open_connection` completes.

- [ ] **Step 3: Add run-now API service**

In `backend/src/argus/link/service.py`, add:

```python
def target_for_connection_metadata(self, *, tenant_id: UUID, site_id: UUID, target_id: str) -> JsonObject | None:
    self._ensure_memory_mode()
    for connection in self.list_connections(tenant_id=tenant_id, site_id=site_id):
        for target in _metadata_targets(connection.metadata):
            if target.get("id") == target_id:
                return target
    return None
```

Add async equivalent for database-backed service by listing connections.

In `backend/src/argus/link/api.py`, add `POST /sites/{site_id}/probe-targets/{target_id}/run` that:

- finds the target
- runs `run_backend_probe`
- records the result with `source_type="backend_synthetic"` and `sample_kind="automated"`
- returns the probe payload

- [ ] **Step 4: Verify runner task**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_probe_runner.py tests/link/test_link_service.py tests/api/test_link_routes.py -q
python3 -m uv run ruff check src/argus/link tests/link tests/api/test_link_routes.py
python3 -m uv run mypy src/argus/link
```

Expected: PASS.

- [ ] **Step 5: Commit runner task**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/probe_runner.py backend/src/argus/link/service.py backend/src/argus/link/api.py backend/tests/link/test_probe_runner.py backend/tests/link/test_link_service.py backend/tests/api/test_link_routes.py
git commit -m "feat: add core link backend probe runner"
```

## Task 4: Frontend Monitoring Hooks And Metadata Helpers

- [ ] **Step 1: Write failing frontend hook/page tests**

In `frontend/src/pages/Links.test.tsx`, add:

```tsx
test("monitoring panel renders target cards instead of record probe", async () => {
  mockLinkHooks({
    summaries: [createSummary({ site_id: "site-1" })],
    connections: [
      {
        id: "connection-1",
        label: "ISP",
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

  expect(await screen.findByRole("heading", { name: /monitoring/i })).toBeInTheDocument();
  expect(screen.getByText(/Vezor ingest/i)).toBeInTheDocument();
  expect(screen.getByText(/ingest.example.vezor/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /record probe/i })).not.toBeInTheDocument();
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx --testNamePattern "monitoring panel"
```

Expected: FAIL because the panel still says Probe history and Record probe.

- [ ] **Step 2: Add hooks**

Modify `frontend/src/hooks/use-link.ts`:

```ts
export function useDeleteLinkProbe({ siteId, vesselId }: LinkMutationContext) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (probeId: string) => {
      if (!siteId) {
        throw new Error("A site is required to delete a probe sample.");
      }
      const { error } = await apiClient.DELETE(
        "/api/v1/link/sites/{site_id}/probes/{probe_id}",
        { params: { path: { site_id: siteId, probe_id: probeId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to delete probe sample.");
      }
      return probeId;
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
  });
}
```

Add `useRunLinkProbeTarget`:

```ts
export function useRunLinkProbeTarget({ siteId, vesselId }: LinkMutationContext) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (targetId: string) => {
      if (!siteId) {
        throw new Error("A site is required to run a probe target.");
      }
      const { data, error } = await apiClient.POST(
        "/api/v1/link/sites/{site_id}/probe-targets/{target_id}/run",
        { params: { path: { site_id: siteId, target_id: targetId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to run probe target.");
      }
      return data ?? null;
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
  });
}
```

- [ ] **Step 3: Extend metadata helpers**

Modify `frontend/src/components/link/types.ts`:

- Add `id` and `monitoring` to `MonitoringTarget`.
- Generate stable IDs for new targets in `LinkActionDialogs.tsx` using `crypto.randomUUID()` when available and `target-${Date.now()}` fallback.
- Add `monitoringSourceLabel(sourceType, intervalSeconds)` helper.
- Add `probeSourceDisplay(probe)` helper.

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx --testNamePattern "monitoring panel"
```

Expected: still FAIL until the panel is changed.

## Task 5: Frontend Monitoring Panel And Manual Samples

- [ ] **Step 1: Implement Monitoring panel**

Modify `frontend/src/components/link/LinkProbePanel.tsx`:

- Rename heading to `Monitoring`.
- Flatten targets from `connections` metadata.
- Render target cards before sample history.
- Replace button text `Record probe` with `Add manual sample`.
- Add `Run check now` on targets with `monitoring.source_type === "backend_synthetic"` and `probe_type !== "icmp"`.
- Add `Delete sample` button for each probe sample.

- [ ] **Step 2: Rename probe dialog to manual sample dialog**

Modify `frontend/src/components/link/LinkActionDialogs.tsx`:

- Keep the exported component name if that avoids broad churn, but change operator copy:
  - title: `Add manual sample`
  - description: `Record an observed link-health sample from a known vantage point.`
  - `Probe source` label becomes `Sample source label`.
- Add source type select defaulting to `manual`.
- Add target select from flattened targets. The dialog can still accept connection list for compatibility, but it should prefer target ID.

Submit payload includes:

```ts
{
  target_id: selectedTarget?.id ?? null,
  target_label: selectedTarget?.label ?? null,
  target_address: selectedTarget?.address ?? null,
  probe_type: selectedTarget?.probe_type ?? "manual",
  source_type: "manual",
  source_label: sourceLabel,
  sample_kind: "manual",
  source: `manual:${sourceLabel}`,
}
```

- [ ] **Step 3: Add delete and run-now tests**

In `frontend/src/pages/Links.test.tsx`, add:

```tsx
test("monitoring panel deletes a manual sample", async () => {
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
        source_type: "manual",
        source_label: "operator-console",
        sample_kind: "manual",
        recorded_at: "2026-06-07T10:00:00Z",
      },
    ],
    deleteProbe,
  });

  renderWithProviders(<Links />, { route: "/links?site=site-1" });

  await user.click(await screen.findByRole("button", { name: /delete sample/i }));

  expect(deleteProbe).toHaveBeenCalledWith("probe-1");
});
```

Extend the test harness mock with `deleteProbe` and `runProbeTarget` functions and hook mocks.

Add:

```tsx
test("monitoring panel runs a backend synthetic target now", async () => {
  const user = userEvent.setup();
  const runProbeTarget = vi.fn().mockResolvedValue({});
  mockLinkHooks({
    summaries: [createSummary({ site_id: "site-1" })],
    connections: [
      {
        id: "connection-1",
        label: "ISP",
        metadata: {
          monitoring_targets: [
            {
              id: "target-1",
              label: "Vezor ingest",
              address: "ingest.example.vezor",
              probe_type: "https",
              port: 443,
              purpose: "vezor_control",
              monitoring: { enabled: true, source_type: "backend_synthetic", interval_seconds: 300 },
            },
          ],
        },
      },
    ],
    runProbeTarget,
  });

  renderWithProviders(<Links />, { route: "/links?site=site-1" });

  await user.click(await screen.findByRole("button", { name: /run check now vezor ingest/i }));

  expect(runProbeTarget).toHaveBeenCalledWith("target-1");
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: PASS after implementation.

- [ ] **Step 4: Commit frontend monitoring UI**

```bash
cd /Users/yann.moren/vision
git add frontend/src/hooks/use-link.ts frontend/src/components/link/types.ts frontend/src/components/link/LinkActionDialogs.tsx frontend/src/components/link/LinkProbePanel.tsx frontend/src/pages/Links.test.tsx
git commit -m "feat: clarify core link monitoring workflow"
```

## Task 6: Final Verification And Push

- [ ] **Step 1: Full targeted verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py tests/link/test_probe_runner.py tests/api/test_link_routes.py -q
python3 -m uv run ruff check src/argus/link tests/link tests/api/test_link_routes.py
python3 -m uv run mypy src/argus/link

cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
corepack pnpm build

cd /Users/yann.moren/vision
git diff --check
```

Expected: PASS.

- [ ] **Step 2: Inspect staged scope**

Run:

```bash
cd /Users/yann.moren/vision
git status --short
```

Expected: only intended Core Link probe monitoring files are modified or staged. Pre-existing untracked scratch files remain unstaged.

- [ ] **Step 3: Push branch**

Run:

```bash
cd /Users/yann.moren/vision
git push origin codex/sceneops-pack-registry
```

Expected: push succeeds.

## Self-Review

- Spec coverage: each requirement in the probe monitoring spec maps to a backend, API, frontend, or verification task.
- Placeholder scan: the plan contains no placeholder tasks.
- Type consistency: target/source/sample field names match across migration, contracts, API, service, hooks, and tests.
- Scope check: edge-agent and provider SDK implementations remain outside this slice, while their source types are contract-ready.
