# Core Link Edge Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a source-side Core Link edge agent path that records packet-loss samples from real site vantage points.

**Architecture:** Extend the existing `LinkHealthProbe` sample model with measurement metadata and a `udp` probe type, add an edge-agent sample ingestion endpoint that computes packet loss from counts, and add a small Python CLI that parses OS ping packet trains and posts samples. The frontend remains an operator control-plane surface: it configures edge-agent targets and renders edge-agent sample details.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy/Alembic, Python `argparse`/`subprocess`, `httpx`, React, TypeScript, Vitest, pytest, Ruff, mypy.

---

## File Structure

- Modify `backend/src/argus/link/contracts.py`: add `udp`, method literal, and `measurement_metadata`.
- Modify `backend/src/argus/link/tables.py`: add metadata JSON column and update probe type constraint.
- Create `backend/src/argus/migrations/versions/0039_core_link_edge_agent.py`: migrate metadata column and `udp` constraint.
- Modify `backend/src/argus/link/service.py`: persist metadata in memory and session-backed paths.
- Modify `backend/src/argus/link/api.py`: add edge-agent sample payload and route.
- Create `backend/src/argus/link/edge_agent.py`: source-side CLI, ping parser, and API poster.
- Modify `frontend/src/components/link/types.ts`: add `udp`, edge-agent target metadata, and metadata helpers.
- Modify `frontend/src/components/link/LinkActionDialogs.tsx`: preserve edge-agent method fields in link-path form.
- Modify `frontend/src/components/link/LinkProbePanel.tsx`: display edge-agent method/count metadata.
- Modify `frontend/src/hooks/use-link.ts`, `frontend/src/lib/openapi.json`, and `frontend/src/lib/api.generated.ts`: regenerate API client after backend route/schema changes.
- Test `backend/tests/link/test_link_service.py`, `backend/tests/api/test_link_routes.py`, `backend/tests/link/test_edge_agent.py`, and `frontend/src/pages/Links.test.tsx`.

## Task 1: Backend Service Metadata

**Files:**
- Modify: `backend/src/argus/link/contracts.py`
- Modify: `backend/src/argus/link/tables.py`
- Modify: `backend/src/argus/link/service.py`
- Create: `backend/src/argus/migrations/versions/0039_core_link_edge_agent.py`
- Test: `backend/tests/link/test_link_service.py`

- [ ] **Step 1: Write the failing service test**

Add:

```python
def test_record_probe_stores_measurement_metadata(link_service: LinkService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")

    probe = link_service.record_probe(
        tenant_id=tenant_id,
        site_id=site_id,
        latency_ms=24,
        throughput_mbps=0,
        packet_loss_percent=5.0,
        reachable=True,
        source="edge_agent:macbook-home",
        probe_type="udp",
        source_type="edge_agent",
        source_label="MacBook at home",
        sample_kind="automated",
        measurement_metadata={
            "agent_id": "macbook-home",
            "method": "icmp_sequence",
            "packet_count": 20,
            "packets_received": 19,
            "packets_lost": 1,
        },
    )

    assert probe.probe_type == "udp"
    assert probe.measurement_metadata["agent_id"] == "macbook-home"
    assert probe.measurement_metadata["packets_lost"] == 1
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_record_probe_stores_measurement_metadata -q
```

Expected: FAIL because `record_probe` does not accept `measurement_metadata` and `udp` is not in the contract.

- [ ] **Step 3: Implement service metadata**

Make these changes:

- `LinkProbeType = Literal["icmp", "tcp", "http", "https", "udp", "manual"]`
- `LinkHealthProbeRecord` gets `measurement_metadata: JsonObject = field(default_factory=dict)`.
- `LinkHealthProbe` gets `measurement_metadata = mapped_column(JSONB, nullable=True)`.
- Probe type check constraints include `udp`.
- `record_probe` and `arecord_probe` accept `measurement_metadata: Mapping[str, object] | None = None`.
- `_probe_record`, `_probe_payload`, and API payload helpers include metadata.

Migration:

```python
"""Add core link edge agent metadata."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039_core_link_edge_agent"
down_revision = "0038_core_link_probe_monitoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "link_health_probes",
        sa.Column("measurement_metadata", sa.JSON(), nullable=True),
    )
    op.drop_constraint("ck_link_health_probes_probe_type", "link_health_probes", type_="check")
    op.create_check_constraint(
        "ck_link_health_probes_probe_type",
        "link_health_probes",
        "probe_type IS NULL OR probe_type IN ('icmp', 'tcp', 'http', 'https', 'udp', 'manual')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_link_health_probes_probe_type", "link_health_probes", type_="check")
    op.create_check_constraint(
        "ck_link_health_probes_probe_type",
        "link_health_probes",
        "probe_type IS NULL OR probe_type IN ('icmp', 'tcp', 'http', 'https', 'manual')",
    )
    op.drop_column("link_health_probes", "measurement_metadata")
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_record_probe_stores_measurement_metadata tests/link/test_link_service.py::test_link_tables_keep_expected_indexes_and_constraints -q
```

Expected: PASS.

## Task 2: Edge-Agent Ingestion API

**Files:**
- Modify: `backend/src/argus/link/api.py`
- Test: `backend/tests/api/test_link_routes.py`

- [ ] **Step 1: Write failing API tests**

Add:

```python
@pytest.mark.asyncio
async def test_edge_agent_sample_computes_loss_from_packet_counts(client: AsyncClient) -> None:
    await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/connections",
        json={
            "label": "Home",
            "transport_kind": "ethernet",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "always",
            "metered": False,
            "metadata": {
                "monitoring_targets": [
                    {
                        "id": "target-google-dns",
                        "label": "Google DNS",
                        "address": "8.8.8.8",
                        "probe_type": "icmp",
                        "purpose": "custom",
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
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/target-google-dns/edge-samples",
        json={
            "agent_id": "macbook-home",
            "agent_label": "MacBook at home",
            "method": "icmp_sequence",
            "packet_count": 20,
            "packets_received": 19,
            "latency_ms": 24,
            "jitter_ms": 1.8,
            "duration_ms": 19024,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source_type"] == "edge_agent"
    assert payload["sample_kind"] == "automated"
    assert payload["source"] == "edge_agent:macbook-home"
    assert payload["source_label"] == "MacBook at home"
    assert payload["target_id"] == "target-google-dns"
    assert payload["packet_loss_percent"] == 5.0
    assert payload["measurement_metadata"]["packet_count"] == 20
    assert payload["measurement_metadata"]["packets_received"] == 19
    assert payload["measurement_metadata"]["packets_lost"] == 1
```

Add:

```python
@pytest.mark.asyncio
async def test_edge_agent_sample_rejects_received_count_above_sent(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/missing/edge-samples",
        json={
            "agent_id": "macbook-home",
            "method": "icmp_sequence",
            "packet_count": 20,
            "packets_received": 21,
            "latency_ms": 24,
        },
    )

    assert response.status_code == 422
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py::test_edge_agent_sample_computes_loss_from_packet_counts tests/api/test_link_routes.py::test_edge_agent_sample_rejects_received_count_above_sent -q
```

Expected: FAIL because the route and validation model do not exist.

- [ ] **Step 3: Implement API route**

Add:

- `LinkEdgeProbeMethod = Literal["icmp_sequence", "stamp", "twamp", "udp_sequence"]`
- `LinkEdgeProbeSampleCreate` with a `model_validator` that rejects `packets_received > packet_count`.
- `POST /sites/{site_id}/probe-targets/{target_id}/edge-samples`.
- Metadata helper that stores agent id/label, method, packet counts, lost packets, jitter, duration, DSCP, and measured time.
- Computed loss percent rounded to four decimals.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py::test_edge_agent_sample_computes_loss_from_packet_counts tests/api/test_link_routes.py::test_edge_agent_sample_rejects_received_count_above_sent -q
```

Expected: PASS.

## Task 3: Edge-Agent CLI

**Files:**
- Create: `backend/src/argus/link/edge_agent.py`
- Test: `backend/tests/link/test_edge_agent.py`

- [ ] **Step 1: Write failing agent tests**

Add tests for:

- macOS ping parsing.
- Linux ping parsing.
- payload building.
- API posting path and authorization header.

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_edge_agent.py -q
```

Expected: FAIL because `argus.link.edge_agent` does not exist.

- [ ] **Step 3: Implement agent**

Implement:

- `PingStatistics` dataclass.
- `parse_ping_output(output: str) -> PingStatistics`.
- `build_edge_sample_payload(...) -> dict[str, object]`.
- `post_edge_sample(...)` with `httpx.AsyncClient`.
- `parse_args(argv)` with env fallbacks for `ARGUS_API_BASE_URL`, `ARGUS_API_BEARER_TOKEN`, and `ARGUS_LINK_EDGE_AGENT_ID`.
- `async_main(argv)` and `main()`.

The CLI supports `--once`; without `--once`, it loops on `--interval-seconds`.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_edge_agent.py -q
```

Expected: PASS.

## Task 4: Frontend Edge-Agent Display

**Files:**
- Modify: `frontend/src/components/link/types.ts`
- Modify: `frontend/src/components/link/LinkActionDialogs.tsx`
- Modify: `frontend/src/components/link/LinkProbePanel.tsx`
- Test: `frontend/src/pages/Links.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Add tests that:

- Save an edge-agent monitoring target with method, packet count, and DSCP.
- Render an edge-agent target card and sample metadata.

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: FAIL because `udp` and metadata rendering are not wired.

- [ ] **Step 3: Implement frontend**

Update:

- `MonitoringProbeType` and `monitoringProbeTypes` include `udp`.
- `MonitoringTarget` includes `loss_method`, `loss_packet_count`, and `loss_dscp`.
- `LinkConnectionDialog` preserves those fields.
- `LinkProbePanel` displays method/count metadata for edge-agent targets and samples.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: PASS.

## Task 5: Generated API and Verification

**Files:**
- Modify: `frontend/src/lib/openapi.json`
- Modify: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Export OpenAPI**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.export_openapi_schema ../frontend/src/lib/openapi.json
```

- [ ] **Step 2: Generate frontend API types**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm generate:api
```

- [ ] **Step 3: Full scoped verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py tests/link/test_probe_runner.py tests/link/test_edge_agent.py tests/api/test_link_routes.py -q
python3 -m uv run ruff check src/argus/link tests/link/test_link_service.py tests/link/test_probe_runner.py tests/link/test_edge_agent.py tests/api/test_link_routes.py
python3 -m uv run mypy src/argus/link

cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
corepack pnpm build

cd /Users/yann.moren/vision
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit and push scoped changes**

Run:

```bash
cd /Users/yann.moren/vision
git status --short
git add docs/superpowers/specs/2026-06-07-core-link-edge-agent-design.md docs/superpowers/plans/2026-06-07-core-link-edge-agent.md backend/src/argus/link/contracts.py backend/src/argus/link/tables.py backend/src/argus/link/service.py backend/src/argus/link/api.py backend/src/argus/link/edge_agent.py backend/src/argus/migrations/versions/0039_core_link_edge_agent.py backend/tests/link/test_link_service.py backend/tests/api/test_link_routes.py backend/tests/link/test_edge_agent.py frontend/src/components/link/types.ts frontend/src/components/link/LinkActionDialogs.tsx frontend/src/components/link/LinkProbePanel.tsx frontend/src/hooks/use-link.ts frontend/src/lib/openapi.json frontend/src/lib/api.generated.ts frontend/src/pages/Links.test.tsx
git commit -m "feat: add core link edge agent probes"
git push origin codex/sceneops-pack-registry
```

Do not stage unrelated untracked files.
