from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest

from argus.api.contracts import EvidenceRecordingPolicy
from argus.billing.service import BillingService
from argus.compat import UTC
from argus.scripts.seed_whole_product_smoke_fixture import (
    SmokeFixtureRequest,
    parse_args,
    seed_smoke_fixture,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")
CAMERA_ID = UUID("00000000-0000-4000-8000-000000000003")


@pytest.fixture
def db_session_factory() -> _SmokeFixtureSessionFactory:
    return _SmokeFixtureSessionFactory()


def test_parse_args_defaults_evidence_root_to_backend_storage_root() -> None:
    args = parse_args(
        [
            "--tenant-id",
            str(TENANT_ID),
            "--site-id",
            str(SITE_ID),
            "--camera-id",
            str(CAMERA_ID),
            "--smoke-run-id",
            "closure-2026-06-09",
            "--occurred-at",
            "2026-06-09T12:00:00Z",
        ]
    )

    assert args.evidence_root == Path("/var/lib/vezor/evidence")


class _SmokeFixtureSessionFactory:
    def __init__(self) -> None:
        self.rows: list[object] = []
        self.add_events: list[tuple[str, object | None]] = []

    def __call__(self) -> _SmokeFixtureSession:
        return _SmokeFixtureSession(self)


class _SmokeFixtureSession:
    def __init__(self, factory: _SmokeFixtureSessionFactory) -> None:
        self.factory = factory

    async def __aenter__(self) -> _SmokeFixtureSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def add(self, row: object) -> None:
        self.factory.rows.append(row)
        self.factory.add_events.append((row.__class__.__name__, getattr(row, "incident_id", None)))

    async def get(self, entity: type[object], row_id: object) -> object | None:
        for row in self.factory.rows:
            if isinstance(row, entity) and getattr(row, "id", None) == row_id:
                return row
        return None

    async def execute(self, statement):  # noqa: ANN001
        return _SmokeFixtureResultSet(self.factory.rows)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


class _SmokeFixtureResultSet:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalars(self) -> _SmokeFixtureResultSet:
        return self

    def first(self) -> object | None:
        for row in self.rows:
            if row.__class__.__name__ == "TrackingEvent":
                return row
        return None

    def all(self) -> list[object]:
        return list(self.rows)


@pytest.mark.asyncio
async def test_seed_smoke_fixture_is_idempotent(
    db_session_factory: _SmokeFixtureSessionFactory,
    tmp_path: Path,
) -> None:
    request = SmokeFixtureRequest(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        camera_id=CAMERA_ID,
        smoke_run_id="closure-2026-06-09",
        occurred_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        evidence_root=tmp_path,
    )
    billing = BillingService()

    first = await seed_smoke_fixture(db_session_factory, request, billing_service=billing)
    second = await seed_smoke_fixture(db_session_factory, request, billing_service=billing)

    assert second.incident_id == first.incident_id
    assert second.artifact_id == first.artifact_id
    assert second.billing_node_id == first.billing_node_id
    assert second.billing_account_id == first.billing_account_id
    assert second.invoice_run_id == first.invoice_run_id
    assert second.tracking_event_count == 1
    assert second.usage_record_count == 2


@pytest.mark.asyncio
async def test_seed_smoke_fixture_creates_reviewable_artifact(
    db_session_factory: _SmokeFixtureSessionFactory,
    tmp_path: Path,
) -> None:
    request = SmokeFixtureRequest(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        camera_id=CAMERA_ID,
        smoke_run_id="closure-2026-06-09",
        occurred_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        evidence_root=tmp_path,
    )

    result = await seed_smoke_fixture(
        db_session_factory,
        request,
        billing_service=BillingService(),
    )

    assert result.incident_id is not None
    assert result.artifact_id is not None
    assert result.artifact_path.exists()
    assert result.artifact_sha256
    assert result.history_class_name == "person"
    assert result.billing_node_id is not None
    assert result.billing_account_id is not None
    assert result.invoice_run_id is not None


@pytest.mark.asyncio
async def test_seed_smoke_fixture_breaks_runtime_passport_incident_fk_cycle(
    db_session_factory: _SmokeFixtureSessionFactory,
    tmp_path: Path,
) -> None:
    request = SmokeFixtureRequest(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        camera_id=CAMERA_ID,
        smoke_run_id="closure-2026-06-09",
        occurred_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        evidence_root=tmp_path,
    )

    result = await seed_smoke_fixture(
        db_session_factory,
        request,
        billing_service=BillingService(),
    )

    assert ("RuntimePassportSnapshot", None) in db_session_factory.add_events
    passport = next(
        row
        for row in db_session_factory.rows
        if row.__class__.__name__ == "RuntimePassportSnapshot"
    )
    assert passport.incident_id == result.incident_id


@pytest.mark.asyncio
async def test_seed_smoke_fixture_creates_api_valid_incident_recording_policy(
    db_session_factory: _SmokeFixtureSessionFactory,
    tmp_path: Path,
) -> None:
    request = SmokeFixtureRequest(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        camera_id=CAMERA_ID,
        smoke_run_id="closure-2026-06-09",
        occurred_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        evidence_root=tmp_path,
    )

    await seed_smoke_fixture(
        db_session_factory,
        request,
        billing_service=BillingService(),
    )

    incident = next(row for row in db_session_factory.rows if row.__class__.__name__ == "Incident")
    policy = EvidenceRecordingPolicy.model_validate(incident.recording_policy)
    assert policy.mode == "event_clip"
