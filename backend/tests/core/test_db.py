from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from argus.core.config import Settings
from argus.core.db import (
    CountEventStore,
    DatabaseManager,
    TrackingEventBatchRecord,
    TrackingEventStore,
)
from argus.models.enums import CountEventType
from argus.vision.count_events import CountEventRecord
from argus.vision.types import Detection


class _CaptureSession:
    def __init__(self) -> None:
        self.rows: list[object] = []
        self.committed = False
        self.commit_count = 0

    def add_all(self, rows: list[object]) -> None:
        self.rows.extend(rows)

    async def commit(self) -> None:
        self.committed = True
        self.commit_count += 1


class _CaptureSessionFactory:
    def __init__(self, session: _CaptureSession) -> None:
        self.session = session

    def __call__(self) -> _CaptureSessionContext:
        return _CaptureSessionContext(self.session)


class _CaptureSessionContext:
    def __init__(self, session: _CaptureSession) -> None:
        self.session = session

    async def __aenter__(self) -> _CaptureSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _expected_vocabulary_hash(terms: list[str]) -> str:
    payload = json.dumps([term.strip() for term in terms if term.strip()], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_database_manager_exposes_async_sessions() -> None:
    settings = Settings(
        _env_file=None,
        db_url="postgresql+asyncpg://argus:argus@localhost:5432/argus",
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    database_manager = DatabaseManager(settings)
    session = database_manager.session_factory()

    assert isinstance(session, AsyncSession)

    await session.close()
    await database_manager.dispose()


@pytest.mark.asyncio
async def test_count_event_store_preserves_core_fields() -> None:
    session = _CaptureSession()
    store = CountEventStore(_CaptureSessionFactory(session))
    camera_id = uuid4()
    ts = datetime(2026, 4, 25, 12, 30, tzinfo=UTC)
    attributes = {"direction": "north", "lane": 2}
    payload = {"source": "test", "count": 1}

    await store.record(
        camera_id,
        [
            CountEventRecord(
                ts=ts,
                class_name="car",
                track_id=42,
                event_type=CountEventType.LINE_CROSS,
                boundary_id="driveway",
                speed_kph=37.5,
                attributes=attributes,
                payload=payload,
            )
        ],
    )

    attributes["direction"] = "south"
    payload["count"] = 2

    assert session.committed is True
    assert len(session.rows) == 1
    row = session.rows[0]
    assert row.camera_id == camera_id
    assert row.event_type == CountEventType.LINE_CROSS
    assert row.boundary_id == "driveway"
    assert row.speed_kph == 37.5
    assert row.payload == {"source": "test", "count": 1}
    assert row.attributes == {"direction": "north", "lane": 2}


@pytest.mark.asyncio
async def test_tracking_event_store_records_vocabulary_attribution() -> None:
    session = _CaptureSession()
    store = TrackingEventStore(_CaptureSessionFactory(session))
    camera_id = uuid4()
    expected_hash = _expected_vocabulary_hash(["forklift", "pallet jack"])

    await store.record(
        camera_id,
        datetime(2026, 4, 25, 12, 30, tzinfo=UTC),
        [
            Detection(
                class_name="forklift",
                confidence=0.93,
                bbox=(1.0, 2.0, 3.0, 4.0),
                track_id=7,
            )
        ],
        vocabulary_version=2,
        vocabulary_hash=expected_hash,
    )

    assert session.committed is True
    row = session.rows[0]
    assert row.vocabulary_version == 2
    assert row.vocabulary_hash == expected_hash


@pytest.mark.asyncio
async def test_tracking_event_store_batches_frames_in_one_commit() -> None:
    session = _CaptureSession()
    store = TrackingEventStore(_CaptureSessionFactory(session))
    camera_id = uuid4()

    await store.record_many(
        [
            TrackingEventBatchRecord(
                camera_id=camera_id,
                ts=datetime(2026, 4, 25, 12, 30, tzinfo=UTC),
                detections=[
                    Detection(
                        class_name="car",
                        confidence=0.93,
                        bbox=(1.0, 2.0, 3.0, 4.0),
                        track_id=7,
                    )
                ],
                vocabulary_version=2,
                vocabulary_hash="hash-a",
            ),
            TrackingEventBatchRecord(
                camera_id=camera_id,
                ts=datetime(2026, 4, 25, 12, 30, 1, tzinfo=UTC),
                detections=[
                    Detection(
                        class_name="bus",
                        confidence=0.88,
                        bbox=(5.0, 6.0, 7.0, 8.0),
                        track_id=8,
                    )
                ],
                vocabulary_version=3,
                vocabulary_hash="hash-b",
            ),
        ]
    )

    assert session.commit_count == 1
    assert len(session.rows) == 2
    assert [row.class_name for row in session.rows] == ["car", "bus"]
    assert [row.vocabulary_version for row in session.rows] == [2, 3]


@pytest.mark.asyncio
async def test_count_event_store_records_vocabulary_attribution() -> None:
    session = _CaptureSession()
    store = CountEventStore(_CaptureSessionFactory(session))
    camera_id = uuid4()
    expected_hash = _expected_vocabulary_hash(["forklift", "pallet jack"])

    await store.record(
        camera_id,
        [
            CountEventRecord(
                ts=datetime(2026, 4, 25, 12, 30, tzinfo=UTC),
                class_name="forklift",
                track_id=7,
                event_type=CountEventType.LINE_CROSS,
                boundary_id="dock-door",
            )
        ],
        vocabulary_version=2,
        vocabulary_hash=expected_hash,
    )

    assert session.committed is True
    row = session.rows[0]
    assert row.vocabulary_version == 2
    assert row.vocabulary_hash == expected_hash


def test_count_events_migration_exists() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    migration_path = repo_root / "src/argus/migrations/versions/0004_prompt12_count_events.py"
    migration_text = migration_path.read_text(encoding="utf-8")

    assert migration_path.exists()
    assert 'revision = "0004_prompt12_count_events"' in migration_text
    assert "create_hypertable('count_events'" in migration_text
    assert "count_events_1m" in migration_text
    assert "count_events_1h" in migration_text


def test_accountable_scene_evidence_migration_keeps_source_kind_string_backed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    migration_path = (
        repo_root
        / "src/argus/migrations/versions/0011_accountable_scene_evidence.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert migration_path.exists()
    assert 'revision = "0011_accountable_scene_evidence"' in migration_text
    assert 'down_revision = "0010_model_runtime_artifacts"' in migration_text
    assert '"scene_contract_snapshots"' in migration_text
    assert '"privacy_manifest_snapshots"' in migration_text
    assert '"evidence_artifacts"' in migration_text
    assert '"evidence_ledger_entries"' in migration_text
    assert 'sa.Column("source_kind", sa.String(length=32), nullable=True)' in migration_text
    assert "camera_source_kind_enum" not in migration_text


def test_accountable_scene_evidence_migration_constraint_names_fit_postgres() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    migration_path = (
        repo_root
        / "src/argus/migrations/versions/0011_accountable_scene_evidence.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    legacy_constraint_names = [
        "fk_incidents_scene_contract_snapshot_id_scene_contract_snapshots",
        "fk_incidents_privacy_manifest_snapshot_id_privacy_manifest_snapshots",
    ]
    constraint_names = [
        "fk_incidents_scene_contract_snapshot",
        "fk_incidents_privacy_manifest_snapshot",
    ]

    for constraint_name in legacy_constraint_names:
        assert constraint_name not in migration_text
        assert len(constraint_name) > 63

    for constraint_name in constraint_names:
        assert constraint_name in migration_text
        assert len(constraint_name) <= 63
