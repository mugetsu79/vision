# Remaining Live Smoke Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every remaining whole-product live smoke gap with repeatable fixtures, real Jetson validation, Jetson TensorRT build execution, real billing usage, authenticated UDP reflector probing, and fresh post-fix reset proof.

**Architecture:** Keep product code narrow and observable. Extend the existing smoke harness and add an explicit deterministic fixture script for history/incidents/evidence/billing; use the existing central model lifecycle job protocol for Jetson sync and TensorRT builds; add a real `trtexec` builder and supervisor-scoped reflector probe config only where live validation proves those pieces are missing.

**Tech Stack:** Python 3, FastAPI, Pydantic, SQLAlchemy async sessions, pytest, Ruff, React/Vitest for UI regressions when touched, Docker Compose installed product stack, Jetson Linux/TensorRT, Core Link UDP sequence reflector.

---

## Scope And Sequencing

This plan intentionally composes with:

- `docs/superpowers/specs/2026-06-09-remaining-live-smoke-closure-design.md`
- `docs/superpowers/specs/2026-06-08-central-model-edge-artifact-management-spec.md`
- `docs/superpowers/plans/2026-06-08-central-model-edge-artifact-management-plan.md`

The central model lifecycle tables, routes, and UI are already present on the
branch. Do not reimplement them unless live evidence shows a blocker. The
closure plan adds the missing proof mechanisms and hardens the final live run.

Execute in this order:

1. Upgrade the smoke harness and report contract.
2. Add the deterministic history/incident/evidence/billing fixture.
3. Wire a real TensorRT builder into the supervisor runner.
4. Add reflector probe secret distribution if the edge-agent cannot obtain a
   usable UDP secret through existing product paths.
5. Run the fresh destructive reset and installed master proof.
6. Pair the Jetson, sync models, build TensorRT, run Office RTSP live, seed the
   deterministic fixture, generate billing, run the UDP probe, and write the
   final closure report.

## File Structure

### Smoke Harness And Fixture

- Modify `scripts/validation/whole_product_live_smoke.py`: orchestrate closure
  checks, preserve status semantics, redact secrets, and write JSON reports.
- Modify `backend/tests/scripts/test_whole_product_live_smoke.py`: cover new
  statuses, required check names, redaction, and missing-lane behavior.
- Create `backend/src/argus/scripts/seed_whole_product_smoke_fixture.py`: seed
  deterministic tracking, incident, evidence artifact, evidence ledger, billing
  usage, and invoice data into an installed stack.
- Create `backend/tests/scripts/test_seed_whole_product_smoke_fixture.py`: prove
  fixture idempotency and API-visible records with a test database.

### Jetson Model And TensorRT

- Create `backend/src/argus/supervisor/tensorrt_builder.py`: `trtexec` builder
  used by `SupervisorModelJobExecutor`.
- Create `backend/tests/supervisor/test_tensorrt_builder.py`: mock subprocess
  execution and prove command construction, retry behavior, hashable output, and
  failure messages.
- Modify `backend/src/argus/supervisor/runner.py`: wire the builder, model store
  path, artifact store path, and runtime versions into
  `SupervisorModelJobExecutor`.
- Modify `backend/tests/supervisor/test_runner.py`: prove the runner builds a
  model job executor with a TensorRT builder when `trtexec` is available and a
  clear disabled reason when it is not.

### Core Link Reflector Probe Distribution

- Modify `backend/src/argus/link/api.py`: add a supervisor/admin-scoped edge
  agent config endpoint for the master reflector target.
- Modify `backend/tests/api/test_link_routes.py`: prove secret material is only
  returned by the new scoped endpoint, never by normal reflector profile/list
  endpoints.
- Modify `backend/src/argus/link/edge_agent.py`: allow loading UDP sequence
  config from the scoped endpoint and keep CLI/env overrides.
- Modify `backend/tests/link/test_edge_agent.py`: prove config loading, redacted
  errors, and one-shot UDP sample posting.
- Modify `docs/core-link-performance-guide.md` and `docs/runbook.md`: document
  the scoped config flow and redaction expectations.

### Docs And Report

- Modify `docs/superpowers/status/2026-06-09-next-chat-remaining-live-smoke-closure-handoff.md`: reference this spec and plan.
- Create `docs/superpowers/status/YYYY-MM-DD-whole-product-live-smoke-closure-report.md` after the live run.

## Task 1: Upgrade The Smoke Harness Contract

**Files:**
- Modify: `scripts/validation/whole_product_live_smoke.py`
- Modify: `backend/tests/scripts/test_whole_product_live_smoke.py`

- [ ] **Step 1: Add failing tests for required closure checks**

Append this test to `backend/tests/scripts/test_whole_product_live_smoke.py`:

```python
def test_closure_report_contains_all_required_lanes(tmp_path: Path) -> None:
    module = _load_module()
    report_path = tmp_path / "closure-smoke.json"

    result = module.main(
        [
            "--api-url",
            "http://api.local.test:8000",
            "--report",
            str(report_path),
            "--real-rtsp",
            "none",
        ]
    )

    assert result == 0
    report = _read_json(report_path)
    names = {check["name"] for check in report["checks"]}
    assert names >= {
        "Fresh destructive reset proof",
        "First-run auth and tenant claims",
        "Central supervisor credential binding",
        "Real Jetson supervisor API",
        "Jetson model sync inventory",
        "Jetson TensorRT artifact build",
        "Office RTSP live native annotated",
        "Deterministic history incident evidence",
        "Billing usage invoice FleetOps",
        "Master reflector secret distribution",
        "UDP edge-agent probe",
        "Core Link master target-only behavior",
    }
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/scripts/test_whole_product_live_smoke.py::test_closure_report_contains_all_required_lanes -q
```

Expected: FAIL because the current smoke script only emits the status taxonomy,
real RTSP, and API target checks.

- [ ] **Step 3: Add required lane names and default statuses**

In `scripts/validation/whole_product_live_smoke.py`, add this constant near
`SmokeCheck`:

```python
REQUIRED_CLOSURE_LANES: tuple[str, ...] = (
    "Fresh destructive reset proof",
    "First-run auth and tenant claims",
    "Central supervisor credential binding",
    "Real Jetson supervisor API",
    "Jetson model sync inventory",
    "Jetson TensorRT artifact build",
    "Office RTSP live native annotated",
    "Deterministic history incident evidence",
    "Billing usage invoice FleetOps",
    "Master reflector secret distribution",
    "UDP edge-agent probe",
    "Core Link master target-only behavior",
)
```

Add this helper:

```python
def default_closure_checks() -> list[SmokeCheck]:
    return [
        SmokeCheck(
            name=name,
            status=SmokeStatus.NOT_RUN,
            evidence=["Live validation has not executed this lane in this harness run."],
        )
        for name in REQUIRED_CLOSURE_LANES
    ]
```

Update `build_checks` so it appends `default_closure_checks()` after the real
RTSP check.

- [ ] **Step 4: Verify the test passes**

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/scripts/test_whole_product_live_smoke.py::test_closure_report_contains_all_required_lanes -q
```

Expected: PASS.

- [ ] **Step 5: Protect missing infrastructure from accidental PASS**

Append this test:

```python
def test_missing_live_inputs_are_blocked_or_not_run_not_pass(tmp_path: Path) -> None:
    module = _load_module()
    report_path = tmp_path / "closure-smoke.json"

    module.main(["--report", str(report_path), "--real-rtsp", "720p"])

    report = _read_json(report_path)
    forbidden_pass_names = {
        "Real RTSP source",
        "Real Jetson supervisor API",
        "Jetson model sync inventory",
        "Jetson TensorRT artifact build",
        "Master reflector secret distribution",
        "UDP edge-agent probe",
    }
    for check in report["checks"]:
        if check["name"] in forbidden_pass_names:
            assert check["status"] in {"BLOCKED", "NOT RUN"}
```

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/scripts/test_whole_product_live_smoke.py::test_missing_live_inputs_are_blocked_or_not_run_not_pass -q
```

Expected: PASS after Step 3.

## Task 2: Add Fresh Install Credential Proof Checks

**Files:**
- Modify: `scripts/validation/whole_product_live_smoke.py`
- Modify: `backend/tests/scripts/test_whole_product_live_smoke.py`

- [ ] **Step 1: Add failing tests for credential proof parsing**

Append:

```python
def test_central_credential_proof_uses_hashes_not_secret_material() -> None:
    module = _load_module()

    check = module.build_central_credential_check(
        {
            "config_secret_sha256": "a" * 64,
            "runtime_credential_sha256": "a" * 64,
            "central_node_credential_status": "active",
            "manual_repair_used": False,
        }
    )

    assert check.status.value == "PASS"
    evidence = " ".join(check.evidence)
    assert "secret" not in evidence.lower()
    assert "a" * 64 in evidence
```

Append:

```python
def test_central_credential_proof_blocks_manual_repair() -> None:
    module = _load_module()

    check = module.build_central_credential_check(
        {
            "config_secret_sha256": "a" * 64,
            "runtime_credential_sha256": "a" * 64,
            "central_node_credential_status": "active",
            "manual_repair_used": True,
        }
    )

    assert check.status.value == "FAIL"
    assert "manual repair" in " ".join(check.evidence).lower()
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/scripts/test_whole_product_live_smoke.py::test_central_credential_proof_uses_hashes_not_secret_material \
  backend/tests/scripts/test_whole_product_live_smoke.py::test_central_credential_proof_blocks_manual_repair -q
```

Expected: FAIL because `build_central_credential_check` does not exist.

- [ ] **Step 3: Implement the proof helper**

Add to `scripts/validation/whole_product_live_smoke.py`:

```python
def build_central_credential_check(proof: Mapping[str, object]) -> SmokeCheck:
    config_hash = str(proof.get("config_secret_sha256") or "")
    runtime_hash = str(proof.get("runtime_credential_sha256") or "")
    status_value = str(proof.get("central_node_credential_status") or "")
    manual_repair_used = bool(proof.get("manual_repair_used"))
    evidence = [
        f"config credential sha256={config_hash or 'missing'}",
        f"runtime credential sha256={runtime_hash or 'missing'}",
        f"central node credential_status={status_value or 'missing'}",
    ]
    if manual_repair_used:
        return SmokeCheck(
            name="Central supervisor credential binding",
            status=SmokeStatus.FAIL,
            evidence=[*evidence, "Manual repair was required after first-run."],
        )
    if config_hash and runtime_hash and config_hash == runtime_hash and status_value == "active":
        return SmokeCheck(
            name="Central supervisor credential binding",
            status=SmokeStatus.PASS,
            evidence=evidence,
        )
    return SmokeCheck(
        name="Central supervisor credential binding",
        status=SmokeStatus.BLOCKED,
        evidence=evidence,
    )
```

- [ ] **Step 4: Verify**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/scripts/test_whole_product_live_smoke.py -q
```

Expected: all smoke script tests pass.

## Task 3: Build Deterministic Smoke Fixture Service

**Files:**
- Create: `backend/src/argus/scripts/seed_whole_product_smoke_fixture.py`
- Create: `backend/tests/scripts/test_seed_whole_product_smoke_fixture.py`

- [ ] **Step 1: Write failing idempotency and visibility tests**

Create `backend/tests/scripts/test_seed_whole_product_smoke_fixture.py`:

```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest

from argus.compat import UTC
from argus.scripts.seed_whole_product_smoke_fixture import (
    SmokeFixtureRequest,
    seed_smoke_fixture,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")
CAMERA_ID = UUID("00000000-0000-4000-8000-000000000003")


@pytest.fixture
def db_session_factory() -> "_SmokeFixtureSessionFactory":
    return _SmokeFixtureSessionFactory()


class _SmokeFixtureSessionFactory:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def __call__(self) -> "_SmokeFixtureSession":
        return _SmokeFixtureSession(self)


class _SmokeFixtureSession:
    def __init__(self, factory: _SmokeFixtureSessionFactory) -> None:
        self.factory = factory

    async def __aenter__(self) -> "_SmokeFixtureSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def add(self, row: object) -> None:
        self.factory.rows.append(row)

    async def get(self, entity: type[object], row_id: object) -> object | None:
        for row in self.factory.rows:
            if isinstance(row, entity) and getattr(row, "id", None) == row_id:
                return row
        return None

    async def execute(self, statement):  # noqa: ANN001
        return _SmokeFixtureResultSet(self.factory.rows, statement)

    async def commit(self) -> None:
        return None


class _SmokeFixtureResultSet:
    def __init__(self, rows: list[object], statement: object) -> None:
        self.rows = rows
        self.statement = statement

    def scalars(self) -> "_SmokeFixtureResultSet":
        return self

    def first(self) -> object | None:
        for row in self.rows:
            if row.__class__.__name__ == "TrackingEvent":
                return row
        return None

    def all(self) -> list[object]:
        return list(self.rows)


@pytest.mark.asyncio
async def test_seed_smoke_fixture_is_idempotent(db_session_factory, tmp_path: Path) -> None:
    request = SmokeFixtureRequest(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        camera_id=CAMERA_ID,
        smoke_run_id="closure-2026-06-09",
        occurred_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        evidence_root=tmp_path,
    )

    first = await seed_smoke_fixture(db_session_factory, request)
    second = await seed_smoke_fixture(db_session_factory, request)

    assert second.incident_id == first.incident_id
    assert second.artifact_id == first.artifact_id
    assert second.tracking_event_count == 1
    assert second.usage_record_count >= 2
```

Add a second test:

```python
@pytest.mark.asyncio
async def test_seed_smoke_fixture_creates_reviewable_artifact(db_session_factory, tmp_path: Path) -> None:
    request = SmokeFixtureRequest(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        camera_id=CAMERA_ID,
        smoke_run_id="closure-2026-06-09",
        occurred_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        evidence_root=tmp_path,
    )

    result = await seed_smoke_fixture(db_session_factory, request)

    assert result.incident_id is not None
    assert result.artifact_path.exists()
    assert result.artifact_sha256
    assert result.history_class_name == "person"
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/scripts/test_seed_whole_product_smoke_fixture.py -q
```

Expected: FAIL because the script module does not exist.

- [ ] **Step 3: Implement request and result models**

Create `backend/src/argus/scripts/seed_whole_product_smoke_fixture.py` with:

```python
from __future__ import annotations

import argparse
import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.core.db import create_session_factory
from argus.models.enums import (
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
    IncidentReviewStatus,
)
from argus.models.tables import (
    EvidenceArtifact,
    EvidenceLedgerEntry,
    Incident,
    PrivacyManifestSnapshot,
    RuntimePassportSnapshot,
    SceneContractSnapshot,
    TrackingEvent,
)


@dataclass(frozen=True, slots=True)
class SmokeFixtureRequest:
    tenant_id: UUID
    site_id: UUID
    camera_id: UUID
    smoke_run_id: str
    occurred_at: datetime
    evidence_root: Path


@dataclass(frozen=True, slots=True)
class SmokeFixtureResult:
    incident_id: UUID
    artifact_id: UUID
    artifact_path: Path
    artifact_sha256: str
    history_class_name: str
    tracking_event_count: int
    usage_record_count: int
```

- [ ] **Step 4: Implement deterministic IDs and artifact content**

Add:

```python
def _fixture_uuid(request: SmokeFixtureRequest, suffix: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"vezor:whole-product-smoke:{request.tenant_id}:{request.camera_id}:{request.smoke_run_id}:{suffix}",
    )


def _hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _entry_hash(*, previous: str | None, payload: str) -> str:
    base = f"{previous or ''}:{payload}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()
```

- [ ] **Step 5: Implement `seed_smoke_fixture`**

Use existing tables and upsert by deterministic IDs:

```python
async def seed_smoke_fixture(
    session_factory: async_sessionmaker[AsyncSession],
    request: SmokeFixtureRequest,
) -> SmokeFixtureResult:
    incident_id = _fixture_uuid(request, "incident")
    artifact_id = _fixture_uuid(request, "artifact")
    scene_snapshot_id = _fixture_uuid(request, "scene-contract")
    privacy_snapshot_id = _fixture_uuid(request, "privacy-manifest")
    passport_snapshot_id = _fixture_uuid(request, "runtime-passport")
    ledger_entry_id = _fixture_uuid(request, "ledger-entry-1")
    artifact_dir = request.evidence_root / request.smoke_run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{artifact_id}.txt"
    artifact_payload = (
        f"Vezor whole-product smoke evidence\n"
        f"smoke_run_id={request.smoke_run_id}\n"
        f"camera_id={request.camera_id}\n"
    ).encode("utf-8")
    artifact_path.write_bytes(artifact_payload)
    artifact_sha256 = _hash_payload(artifact_payload)

    async with session_factory() as session:
        await _upsert_tracking_event(session, request)
        scene_hash = _hash_payload(f"scene:{request.smoke_run_id}".encode("utf-8"))
        privacy_hash = _hash_payload(f"privacy:{request.smoke_run_id}".encode("utf-8"))
        passport_hash = _hash_payload(f"runtime:{request.smoke_run_id}".encode("utf-8"))
        await _upsert_scene_contract(session, request, scene_snapshot_id, scene_hash)
        await _upsert_privacy_manifest(session, request, privacy_snapshot_id, privacy_hash)
        await _upsert_runtime_passport(
            session,
            request,
            passport_snapshot_id,
            passport_hash,
            privacy_hash,
            incident_id,
        )
        await _upsert_incident(
            session,
            request,
            incident_id,
            scene_snapshot_id,
            scene_hash,
            privacy_snapshot_id,
            privacy_hash,
            passport_snapshot_id,
            passport_hash,
            artifact_path,
            len(artifact_payload),
        )
        await _upsert_artifact(
            session,
            request,
            artifact_id,
            incident_id,
            artifact_path,
            artifact_sha256,
            len(artifact_payload),
        )
        await _upsert_ledger(session, request, ledger_entry_id, incident_id, artifact_id)
        await session.commit()

    return SmokeFixtureResult(
        incident_id=incident_id,
        artifact_id=artifact_id,
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        history_class_name="person",
        tracking_event_count=1,
        usage_record_count=0,
    )
```

Implement the helper functions using `await session.get(ModelClass, id)` and
insert if missing; update the smoke metadata when present. For the tracking
event, select by `camera_id`, `ts`, and `track_id` because `TrackingEvent` has
both `id` and `ts` keys:

```python
async def _upsert_tracking_event(session: AsyncSession, request: SmokeFixtureRequest) -> None:
    existing = await session.execute(
        select(TrackingEvent)
        .where(TrackingEvent.camera_id == request.camera_id)
        .where(TrackingEvent.ts == request.occurred_at)
        .where(TrackingEvent.track_id == 2609)
    )
    row = existing.scalars().first()
    attrs = {"smoke_run_id": request.smoke_run_id, "source": "whole_product_smoke_fixture"}
    if row is None:
        session.add(
            TrackingEvent(
                id=_fixture_uuid(request, "tracking-event"),
                ts=request.occurred_at,
                camera_id=request.camera_id,
                class_name="person",
                track_id=2609,
                confidence=0.93,
                speed_kph=None,
                direction_deg=None,
                zone_id="office-entry",
                attributes=attrs,
                bbox={"x": 0.42, "y": 0.22, "width": 0.16, "height": 0.48},
            )
        )
    else:
        row.attributes = attrs
```

- [ ] **Step 6: Add CLI argument parsing**

Add:

```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed deterministic whole-product smoke data.")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--smoke-run-id", required=True)
    parser.add_argument("--occurred-at", required=True)
    parser.add_argument("--evidence-root", type=Path, default=Path("/var/lib/vezor/evidence/smoke"))
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    session_factory = create_session_factory()
    result = await seed_smoke_fixture(
        session_factory,
        SmokeFixtureRequest(
            tenant_id=UUID(args.tenant_id),
            site_id=UUID(args.site_id),
            camera_id=UUID(args.camera_id),
            smoke_run_id=args.smoke_run_id,
            occurred_at=datetime.fromisoformat(args.occurred_at.replace("Z", "+00:00")),
            evidence_root=args.evidence_root,
        ),
    )
    print(
        {
            "incident_id": str(result.incident_id),
            "artifact_id": str(result.artifact_id),
            "artifact_sha256": result.artifact_sha256,
        }
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Verify fixture tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/scripts/test_seed_whole_product_smoke_fixture.py -q
python3 -m uv run --project backend ruff check backend/src/argus/scripts/seed_whole_product_smoke_fixture.py backend/tests/scripts/test_seed_whole_product_smoke_fixture.py
```

Expected: tests pass and Ruff passes.

## Task 4: Add Billing Usage To The Deterministic Fixture

**Files:**
- Modify: `backend/src/argus/scripts/seed_whole_product_smoke_fixture.py`
- Modify: `backend/tests/scripts/test_seed_whole_product_smoke_fixture.py`

- [ ] **Step 1: Add failing billing assertions**

Import `BillingService` in
`backend/tests/scripts/test_seed_whole_product_smoke_fixture.py`:

```python
from argus.billing.service import BillingService
```

Replace the two existing `seed_smoke_fixture` calls in
`test_seed_smoke_fixture_is_idempotent` with:

```python
billing = BillingService()
first = await seed_smoke_fixture(db_session_factory, request, billing_service=billing)
second = await seed_smoke_fixture(db_session_factory, request, billing_service=billing)

assert second.billing_account_id == first.billing_account_id
assert second.invoice_run_id == first.invoice_run_id
assert second.usage_record_count == 2
```

Extend `SmokeFixtureResult` assertions with:

```python
assert result.billing_node_id is not None
assert result.billing_account_id is not None
assert result.invoice_run_id is not None
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/scripts/test_seed_whole_product_smoke_fixture.py -q
```

Expected: FAIL because the result does not expose billing IDs and usage count is
still zero.

- [ ] **Step 3: Add billing result fields**

Extend `SmokeFixtureResult`:

```python
billing_node_id: UUID
billing_account_id: UUID
invoice_run_id: UUID
```

- [ ] **Step 4: Seed billing through `BillingService`**

In `seed_whole_product_smoke_fixture.py`, import `BillingService` and add:

```python
from decimal import Decimal

from argus.billing.service import BillingService
```

Change the `seed_smoke_fixture` signature so tests can pass an in-memory
`BillingService()` while live execution uses the DB-backed service:

```python
async def seed_smoke_fixture(
    session_factory: async_sessionmaker[AsyncSession],
    request: SmokeFixtureRequest,
    *,
    billing_service: BillingService | None = None,
) -> SmokeFixtureResult:
```

After the incident/artifact transaction commits, create billing records through
the service so live behavior matches the API layer:

```python
billing = billing_service or BillingService(session_factory)
billing_node = await billing.acreate_node(
    tenant_id=request.tenant_id,
    label=f"Smoke Office Node {request.smoke_run_id}",
    kind="site",
    attributes={"smoke_run_id": request.smoke_run_id, "site_id": str(request.site_id)},
)
billing_account = await billing.acreate_account(
    tenant_id=request.tenant_id,
    name=f"Smoke Account {request.smoke_run_id}",
    node_ids=[billing_node.id],
    attributes={"smoke_run_id": request.smoke_run_id},
)
await billing.agrant_entitlement(
    tenant_id=request.tenant_id,
    account_id=billing_account.id,
    feature_key="whole_product_smoke",
    effective_from=request.occurred_at.date(),
    attributes={"smoke_run_id": request.smoke_run_id},
)
await billing.acreate_price_book(
    tenant_id=request.tenant_id,
    currency="USD",
    effective_from=request.occurred_at.date(),
    meter_prices={"evidence_pack_export": Decimal("5.00"), "managed_edge_node": Decimal("25.00")},
)
await billing.arecord_usage(
    tenant_id=request.tenant_id,
    meter_key="evidence_pack_export",
    quantity=Decimal("1"),
    account_id=billing_account.id,
    node_id=billing_node.id,
    source_object_type="smoke_evidence_artifact",
    source_object_id=artifact_id,
    occurred_on=request.occurred_at.date(),
    metadata={"smoke_run_id": request.smoke_run_id, "incident_id": str(incident_id)},
)
await billing.arecord_usage(
    tenant_id=request.tenant_id,
    meter_key="managed_edge_node",
    quantity=Decimal("1"),
    account_id=billing_account.id,
    node_id=billing_node.id,
    source_object_type="smoke_site",
    source_object_id=request.site_id,
    occurred_on=request.occurred_at.date(),
    metadata={"smoke_run_id": request.smoke_run_id},
)
invoice = await billing.arun_invoice(
    tenant_id=request.tenant_id,
    account_id=billing_account.id,
    period_start=request.occurred_at.date(),
    period_end=request.occurred_at.date(),
)
```

Set `usage_record_count=2` and include the three billing IDs in
`SmokeFixtureResult`.

- [ ] **Step 5: Make billing idempotent**

Before creating a billing node, query `BillingService.alist_nodes` for a record
with matching `attributes.smoke_run_id`. Reuse matching node/account/invoice
records instead of creating duplicates. Add a helper:

```python
def _matching_smoke_record(records: list[object], smoke_run_id: str) -> object | None:
    for record in records:
        attributes = getattr(record, "attributes", {})
        if isinstance(attributes, dict) and attributes.get("smoke_run_id") == smoke_run_id:
            return record
    return None
```

- [ ] **Step 6: Verify**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/scripts/test_seed_whole_product_smoke_fixture.py backend/tests/api/test_billing_routes.py -q
```

Expected: PASS.

## Task 5: Wire A Real TensorRT Builder Into Supervisor Jobs

**Files:**
- Create: `backend/src/argus/supervisor/tensorrt_builder.py`
- Create: `backend/tests/supervisor/test_tensorrt_builder.py`
- Modify: `backend/src/argus/supervisor/runner.py`
- Modify: `backend/tests/supervisor/test_runner.py`

- [ ] **Step 1: Write failing builder tests**

Create `backend/tests/supervisor/test_tensorrt_builder.py`:

```python
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from argus.supervisor.tensorrt_builder import TrtExecTensorRTEngineBuilder


def test_trtexec_builder_writes_engine_with_fp16(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "yolo26n.onnx"
    source.write_bytes(b"onnx")
    output = tmp_path / "yolo26n.engine"
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check):  # noqa: ANN001
        calls.append(list(command))
        output.write_bytes(b"engine")
        return subprocess.CompletedProcess(command, 0, stdout="&&&& PASSED TensorRT.trtexec", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    builder = TrtExecTensorRTEngineBuilder(executable="trtexec")

    result = builder.build(source, output, {"batch": 1, "channels": 3, "height": 640, "width": 640}, "fp16")

    assert result == output
    assert output.read_bytes() == b"engine"
    assert "--onnx" in calls[0]
    assert "--saveEngine" in calls[0]
    assert "--fp16" in calls[0]
```

Add the failure test:

```python
def test_trtexec_builder_raises_clear_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "bad.onnx"
    source.write_bytes(b"onnx")
    output = tmp_path / "bad.engine"

    def fake_run(command, capture_output, text, check):  # noqa: ANN001
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="parser failed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    builder = TrtExecTensorRTEngineBuilder(executable="trtexec")

    with pytest.raises(RuntimeError, match="parser failed"):
        builder.build(source, output, {"batch": 1, "channels": 3, "height": 640, "width": 640}, "fp16")
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/supervisor/test_tensorrt_builder.py -q
```

Expected: FAIL because the builder module does not exist.

- [ ] **Step 3: Implement the builder**

Create `backend/src/argus/supervisor/tensorrt_builder.py`:

```python
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class TrtExecTensorRTEngineBuilder:
    def __init__(self, executable: str | None = None, workspace_mib: int = 2048) -> None:
        self.executable = executable or shutil.which("trtexec") or "/usr/src/tensorrt/bin/trtexec"
        self.workspace_mib = workspace_mib

    def available(self) -> bool:
        return Path(self.executable).exists() or shutil.which(self.executable) is not None

    def build(
        self,
        source_path: Path,
        output_path: Path,
        input_shape: dict[str, int],
        precision: str,
    ) -> Path:
        if not source_path.is_file():
            raise FileNotFoundError(f"TensorRT source model does not exist: {source_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.executable,
            "--onnx",
            str(source_path),
            "--saveEngine",
            str(output_path),
            f"--memPoolSize=workspace:{self.workspace_mib}",
        ]
        if precision.lower() == "fp16":
            command.append("--fp16")
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        if completed.returncode != 0:
            raise RuntimeError(f"TensorRT trtexec failed: {combined.strip()}")
        if not output_path.is_file() or output_path.stat().st_size <= 0:
            raise RuntimeError("TensorRT trtexec succeeded but did not write an engine file.")
        return output_path
```

- [ ] **Step 4: Wire the builder into runner construction**

In `backend/src/argus/supervisor/runner.py`, import:

```python
from argus.supervisor.tensorrt_builder import TrtExecTensorRTEngineBuilder
```

Replace:

```python
model_job_executor=SupervisorModelJobExecutor(operations_client=operations),
```

with:

```python
tensorrt_builder = TrtExecTensorRTEngineBuilder()
model_job_executor = SupervisorModelJobExecutor(
    operations_client=operations,
    tensorrt_engine_builder=tensorrt_builder if tensorrt_builder.available() else None,
    runtime_versions={"tensorrt_builder": "trtexec"},
    model_store_path=config.model_store_path,
    artifact_store_path=config.artifact_store_path,
)
```

Pass `model_job_executor=model_job_executor` into `SupervisorRunner`.

- [ ] **Step 5: Add a runner wiring regression test**

In `backend/tests/supervisor/test_runner.py`, add a test that monkeypatches
`TrtExecTensorRTEngineBuilder.available` to return `True`, calls `build_runner`,
and asserts `runner.model_job_executor.tensorrt_engine_builder is not None`.

- [ ] **Step 6: Verify**

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/supervisor/test_tensorrt_builder.py \
  backend/tests/supervisor/test_artifact_build_jobs.py \
  backend/tests/supervisor/test_runner.py -q
python3 -m uv run --project backend ruff check \
  backend/src/argus/supervisor/tensorrt_builder.py \
  backend/src/argus/supervisor/runner.py \
  backend/tests/supervisor/test_tensorrt_builder.py \
  backend/tests/supervisor/test_runner.py
```

Expected: PASS.

## Task 6: Add Supervisor-Scoped Master Reflector Edge-Agent Config

**Files:**
- Modify: `backend/src/argus/link/api.py`
- Modify: `backend/tests/api/test_link_routes.py`
- Modify: `backend/src/argus/link/edge_agent.py`
- Modify: `backend/tests/link/test_edge_agent.py`
- Modify: `docs/core-link-performance-guide.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add failing API tests**

In `backend/tests/api/test_link_routes.py`, add:

```python
async def test_master_reflector_profile_never_returns_secret(client, admin_headers):  # noqa: ANN001
    response = await client.post("/api/v1/link/reflectors/master/rotate-key", headers=admin_headers)
    assert response.status_code == 200

    profile = await client.get("/api/v1/link/reflectors/master", headers=admin_headers)

    assert profile.status_code == 200
    payload = profile.json()
    assert payload["secret_state"] == "present"
    assert "reflector_secret" not in payload
    assert "encrypted_secret" not in payload
```

Add:

```python
async def test_supervisor_can_fetch_master_reflector_edge_agent_config(
    client,
    admin_headers,
    supervisor_headers,
    edge_site_id,
):  # noqa: ANN001
    await client.post("/api/v1/link/reflectors/master/rotate-key", headers=admin_headers)
    await client.post(
        "/api/v1/link/reflectors/master/enable",
        headers=admin_headers,
        json={"public_address": "192.168.1.166", "udp_port": 8622},
    )
    target_response = await client.post(
        f"/api/v1/link/sites/{edge_site_id}/control-targets/master",
        headers=admin_headers,
        json={"mode": "udp_reflector", "address": "192.168.1.166"},
    )
    assert target_response.status_code == 201

    config = await client.get(
        f"/api/v1/link/sites/{edge_site_id}/control-targets/master/edge-agent-config",
        headers=supervisor_headers,
    )

    assert config.status_code == 200
    payload = config.json()
    assert payload["method"] == "udp_sequence"
    assert payload["reflector_address"] == "192.168.1.166"
    assert payload["reflector_port"] == 8622
    assert payload["reflector_key_id"].startswith("master-reflector-")
    assert payload["reflector_secret"].startswith("vzref_")
    assert payload["target_id"] == "vezor-master-udp-reflector"
```

- [ ] **Step 2: Run the failing API tests**

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/api/test_link_routes.py::test_master_reflector_profile_never_returns_secret \
  backend/tests/api/test_link_routes.py::test_supervisor_can_fetch_master_reflector_edge_agent_config -q
```

Expected: the profile redaction test passes or continues passing; the config
test fails because the endpoint does not exist.

- [ ] **Step 3: Add response model and endpoint**

In `backend/src/argus/link/api.py`, add:

```python
class LinkMasterReflectorEdgeAgentConfigResponse(BaseModel):
    site_id: UUID
    target_id: str
    target_site_id: UUID
    method: Literal["udp_sequence"]
    reflector_address: str
    reflector_port: int
    reflector_key_id: str
    reflector_secret: str
    packet_count: int
    packet_spacing_ms: int
    loss_timeout_ms: int
```

Add route after `post_master_control_target`:

```python
@router.get(
    "/sites/{site_id}/control-targets/master/edge-agent-config",
    response_model=LinkMasterReflectorEdgeAgentConfigResponse,
)
async def get_master_reflector_edge_agent_config(
    site_id: UUID,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> LinkMasterReflectorEdgeAgentConfigResponse:
    site = await _ensure_link_edge_site(services, tenant_context, site_id)
    await services.operations.assert_supervisor_edge_site_scope(tenant_context, site_id)
    master_site = await _master_control_plane_site(services, tenant_context)
    profile = await services.link.aget_master_reflector_profile(
        tenant_id=tenant_context.tenant_id,
        site_id=master_site.id,
    )
    if profile is None or not profile.enabled or profile.encrypted_secret is None:
        raise HTTPException(status_code=409, detail="Master reflector secret is not ready.")
    secret = decrypt_reflector_secret(profile.encrypted_secret, settings=services.settings)
    connection = await services.link.afirst_connection_with_target(
        tenant_id=tenant_context.tenant_id,
        site_id=site.id,
        target_id="vezor-master-udp-reflector",
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="Master UDP reflector target not found.")
    return LinkMasterReflectorEdgeAgentConfigResponse(
        site_id=site.id,
        target_id="vezor-master-udp-reflector",
        target_site_id=master_site.id,
        method="udp_sequence",
        reflector_address=profile.public_address or profile.bind_address,
        reflector_port=profile.udp_port,
        reflector_key_id=profile.key_id,
        reflector_secret=secret,
        packet_count=20,
        packet_spacing_ms=100,
        loss_timeout_ms=1000,
    )
```

If `LinkService` does not yet expose `afirst_connection_with_target`, add a
small service helper that scans the site's connection metadata for the requested
monitoring target id. Test it in `backend/tests/link/test_link_service.py`.

- [ ] **Step 4: Add edge-agent config loading**

In `backend/src/argus/link/edge_agent.py`, add CLI argument:

```python
parser.add_argument("--config-url", default=os.getenv("ARGUS_LINK_EDGE_AGENT_CONFIG_URL"))
```

Add async loader:

```python
async def fetch_edge_agent_config(
    *,
    config_url: str,
    bearer_token: str,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, object]:
    client = http_client or httpx.AsyncClient()
    owns_client = http_client is None
    try:
        response = await client.get(config_url, headers={"Authorization": f"Bearer {bearer_token}"})
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(f"Edge-agent config fetch failed with HTTP {response.status_code}")
        body = response.json()
        return dict(body) if isinstance(body, Mapping) else {}
    finally:
        if owns_client:
            await client.aclose()
```

In `async_main`, when `args.config_url` is set, fetch config before validation
and assign missing `site_id`, `target_id`, `target`, `method`, reflector fields,
packet count, spacing, and timeout from the response.

- [ ] **Step 5: Verify API and edge-agent tests**

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/api/test_link_routes.py \
  backend/tests/link/test_edge_agent.py \
  backend/tests/link/test_reflector.py -q
python3 -m uv run --project backend ruff check \
  backend/src/argus/link/api.py \
  backend/src/argus/link/edge_agent.py \
  backend/tests/api/test_link_routes.py \
  backend/tests/link/test_edge_agent.py
```

Expected: PASS, and normal reflector profile responses still omit secret
material.

## Task 7: Add Jetson And Closure Live Validation Procedure To Harness

**Files:**
- Modify: `scripts/validation/whole_product_live_smoke.py`
- Modify: `backend/tests/scripts/test_whole_product_live_smoke.py`
- Modify: `docs/superpowers/status/2026-06-09-next-chat-remaining-live-smoke-closure-handoff.md`

- [ ] **Step 1: Add CLI options for closure artifacts**

Add arguments:

```python
parser.add_argument("--token-env", default="VEZOR_SMOKE_TOKEN")
parser.add_argument("--jetson-node-id")
parser.add_argument("--office-site-id")
parser.add_argument("--office-camera-id")
parser.add_argument("--smoke-run-id")
parser.add_argument("--reflector-config-url")
```

- [ ] **Step 2: Add test for report metadata redaction**

Append:

```python
def test_report_metadata_redacts_token_env_not_token_value(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    module = _load_module()
    report_path = tmp_path / "closure.json"
    monkeypatch.setenv("VEZOR_SMOKE_TOKEN", "secret-token-value")

    module.main(["--report", str(report_path), "--token-env", "VEZOR_SMOKE_TOKEN"])

    text = report_path.read_text(encoding="utf-8")
    assert "VEZOR_SMOKE_TOKEN" in text
    assert "secret-token-value" not in text
```

- [ ] **Step 3: Implement token-env metadata**

Add `token_env` to report metadata and never serialize the token value:

```python
metadata={
    "api_url": _redact_url_credentials(args.api_url),
    "real_rtsp": args.real_rtsp,
    "token_env": args.token_env,
}
```

- [ ] **Step 4: Keep live checks evidence-driven**

Add helper functions for API GET/POST with timeout and redaction. Each helper
must catch connection failures and return `SmokeCheck(..., status=SmokeStatus.BLOCKED, ...)`
instead of raising after partial report setup. Do not mark a lane `PASS` unless
the expected JSON fields are present.

- [ ] **Step 5: Verify**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/scripts/test_whole_product_live_smoke.py -q
```

Expected: PASS.

## Task 8: Run The Fresh Installed Stack Smoke

**Files:**
- Create after live run: `docs/superpowers/status/YYYY-MM-DD-whole-product-live-smoke-closure-report.md`

- [ ] **Step 1: Confirm branch and working tree**

Run:

```bash
cd /Users/yann.moren/vision
git fetch origin codex/sceneops-pack-registry
git status --short --branch
git rev-list --left-right --count origin/codex/sceneops-pack-registry...HEAD
```

Expected: not behind origin. Unrelated untracked files may exist; leave them
unstaged.

- [ ] **Step 2: Perform the targeted destructive reset**

Follow the reset commands in
`docs/superpowers/status/2026-06-09-next-chat-remaining-live-smoke-closure-handoff.md`.
Record evidence:

- before/after container list;
- before/after volume list;
- preserved `/var/lib/vezor/models/yolo26n.onnx`;
- preserved `/var/lib/vezor/models/yolo26s.onnx`;
- deleted `/etc/vezor/secrets/central_supervisor_credential` before reinstall.

- [ ] **Step 3: Reinstall and complete first-run**

Run:

```bash
MASTER_IP="$(ipconfig getifaddr en0 || ipconfig getifaddr en1)"
sudo ./bin/vezor install master --public-url "http://${MASTER_IP}:3000"
curl -fsS "http://${MASTER_IP}:8000/healthz"
./bin/vezor ctl bootstrap-master \
  --api-url "http://${MASTER_IP}:8000" \
  --rotate-local-token \
  --json
```

Complete first-run in the UI. Record only redacted evidence.

- [ ] **Step 4: Prove central supervisor credential binding**

Run:

```bash
sudo shasum -a 256 /etc/vezor/secrets/central_supervisor_credential
sudo shasum -a 256 /var/lib/vezor/credentials/supervisor.credential
sudo cmp -s /etc/vezor/secrets/central_supervisor_credential \
  /var/lib/vezor/credentials/supervisor.credential
sudo docker logs --tail 200 vezor-master-supervisor 2>/dev/null || true
```

Acceptance: hashes match, `cmp` exits `0`, logs show supervisor polling/reporting,
and no manual repair command was used.

- [ ] **Step 5: Pair the real Jetson**

Create a pairing session from UI/API, run the edge installer on the Jetson, and
verify:

```bash
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/deployment/nodes"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/deployment/nodes/${JETSON_NODE_ID}/support-bundle"
```

Acceptance: real Jetson node has active credentials, recent service report, and
hardware/runtime data.

- [ ] **Step 6: Sync YOLO26n and YOLO26s to Jetson**

Assign models and start sync through UI/API. Verify:

```bash
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/deployment/nodes/${JETSON_NODE_ID}/model-assignments"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/deployment/nodes/${JETSON_NODE_ID}/model-inventory"
```

Acceptance: both models appear with matching hash and size.

- [ ] **Step 7: Build TensorRT on Jetson**

Create the artifact build job from Models -> Runtime artifacts or API. On the
Jetson, capture:

```bash
which trtexec || true
trtexec --version || true
ls -lh /var/lib/vezor/models/yolo26n.onnx
```

Acceptance: runtime artifact record is valid for
`linux-aarch64-nvidia-jetson`, and worker admission can select it.

- [ ] **Step 8: Validate Office RTSP live**

Configure the Office physical site and camera with the redacted RTSP source.
Verify Live native and annotated playback. Confirm no 1080p/900p options appear
for the 720p source.

- [ ] **Step 9: Seed deterministic fixture**

Run the fixture inside the backend container or equivalent backend environment:

```bash
python3 -m argus.scripts.seed_whole_product_smoke_fixture \
  --tenant-id "${TENANT_ID}" \
  --site-id "${OFFICE_SITE_ID}" \
  --camera-id "${OFFICE_CAMERA_ID}" \
  --smoke-run-id "closure-$(date +%Y%m%d%H%M%S)" \
  --occurred-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --evidence-root /var/lib/vezor/evidence/smoke
```

Verify:

```bash
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/history?camera_id=${OFFICE_CAMERA_ID}"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/incidents?camera_id=${OFFICE_CAMERA_ID}"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/billing/usage"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/billing/invoice-runs"
```

Acceptance: History, Incidents, Evidence artifact content, Billing, and FleetOps
Billing are non-empty.

- [ ] **Step 10: Enable reflector and run UDP edge-agent probe**

Enable reflector, create the Office-to-master UDP control target, fetch scoped
edge-agent config, and run:

```bash
python3 -m argus.link.edge_agent \
  --config-url "${VEZOR_API_URL}/api/v1/link/sites/${OFFICE_SITE_ID}/control-targets/master/edge-agent-config" \
  --bearer-token "${EDGE_OR_ADMIN_TOKEN}" \
  --once
```

Acceptance: Link Performance shows a `udp_sequence` edge-agent sample with
packet counts and RTT metadata. The report records key id and redacted target
details, not the secret.

## Task 9: Final Verification And Report

**Files:**
- Create: `docs/superpowers/status/YYYY-MM-DD-whole-product-live-smoke-closure-report.md`
- Modify docs only if live behavior diverges from current docs.

- [ ] **Step 1: Run focused automated verification**

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/scripts/test_whole_product_live_smoke.py \
  backend/tests/scripts/test_seed_whole_product_smoke_fixture.py \
  backend/tests/supervisor/test_tensorrt_builder.py \
  backend/tests/supervisor/test_model_jobs.py \
  backend/tests/supervisor/test_artifact_build_jobs.py \
  backend/tests/api/test_link_routes.py \
  backend/tests/link/test_edge_agent.py \
  backend/tests/link/test_reflector.py \
  backend/tests/api/test_billing_routes.py -q

python3 -m uv run --project backend ruff check \
  backend/src/argus/scripts/seed_whole_product_smoke_fixture.py \
  backend/src/argus/supervisor/tensorrt_builder.py \
  backend/src/argus/supervisor/runner.py \
  backend/src/argus/link/api.py \
  backend/src/argus/link/edge_agent.py \
  scripts/validation/whole_product_live_smoke.py \
  backend/tests/scripts/test_whole_product_live_smoke.py \
  backend/tests/scripts/test_seed_whole_product_smoke_fixture.py \
  backend/tests/supervisor/test_tensorrt_builder.py \
  backend/tests/api/test_link_routes.py \
  backend/tests/link/test_edge_agent.py

installer/.venv/bin/python -m pytest \
  installer/tests/test_macos_master_artifacts.py \
  installer/tests/test_linux_master_artifacts.py \
  installer/tests/test_edge_installer_artifacts.py -q

npm --prefix frontend run test -- \
  Live.test.tsx Models.test.tsx Deployment.test.tsx Cameras.test.tsx \
  Links.test.tsx FleetOps.test.tsx FleetOpsBilling.test.tsx Incidents.test.tsx

git diff --check
```

Expected: all commands exit `0`.

- [ ] **Step 2: Run product installer verification when installer/deployment changed**

Run:

```bash
make verify-installers
```

Expected: installer validation passes.

- [ ] **Step 3: Write the closure report**

Create:

```text
docs/superpowers/status/YYYY-MM-DD-whole-product-live-smoke-closure-report.md
```

Use the template in
`docs/superpowers/status/2026-06-09-next-chat-remaining-live-smoke-closure-handoff.md`.
Every row must be one of `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`.

- [ ] **Step 4: Secret scan before any commit**

Run:

```bash
rg -n "E[d]m39Lek|m[a]rina1987|7[4]1:190|rtsp://7[4]1|vzboot_[A-Za-z0-9._~+/=-]+|vzcred_[A-Za-z0-9._~+/=-]+|vzref_[A-Za-z0-9._~+/=-]+" \
  backend docs infra installer scripts frontend || true
```

Expected: no real secrets. Test fixtures may contain fake values such as
`reflector-secret`; final reports must not contain raw live material.

- [ ] **Step 5: Commit only with user approval**

If the user asks to commit:

```bash
git status --short --branch
git add -- <explicit changed paths>
git diff --cached --stat
git commit -m "fix: close whole-product live smoke gaps"
git push origin codex/sceneops-pack-registry
```

Never use `git add -A` in this workspace.

## Self-Review Checklist

- The plan covers all six closure lanes from the spec.
- The reset preserves `/var/lib/vezor/models` and removes old config/secrets.
- Deterministic fixture creates History, Incident, Evidence, Ledger, Billing,
  and Invoice data.
- TensorRT build runs on Jetson through supervisor jobs.
- Reflector secret material is available only through the scoped edge-agent
  config path.
- Final report cannot mark missing external inputs as pass.
- Commands and tests are concrete and reproducible.
