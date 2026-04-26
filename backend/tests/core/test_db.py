from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from argus.core.config import Settings
from argus.core.db import CountEventStore, DatabaseManager
from argus.models.enums import CountEventType
from argus.vision.count_events import CountEventRecord


class _CaptureSession:
    def __init__(self) -> None:
        self.rows: list[object] = []
        self.committed = False

    def add_all(self, rows: list[object]) -> None:
        self.rows.extend(rows)

    async def commit(self) -> None:
        self.committed = True


class _CaptureSessionFactory:
    def __init__(self, session: _CaptureSession) -> None:
        self.session = session

    def __call__(self) -> "_CaptureSessionContext":
        return _CaptureSessionContext(self.session)


class _CaptureSessionContext:
    def __init__(self, session: _CaptureSession) -> None:
        self.session = session

    async def __aenter__(self) -> _CaptureSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


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
    assert getattr(row, "camera_id") == camera_id
    assert getattr(row, "event_type") == CountEventType.LINE_CROSS
    assert getattr(row, "boundary_id") == "driveway"
    assert getattr(row, "speed_kph") == 37.5
    assert getattr(row, "payload") == {"source": "test", "count": 1}
    assert getattr(row, "attributes") == {"direction": "north", "lane": 2}


def test_count_events_migration_exists() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    migration_path = repo_root / "src/argus/migrations/versions/0004_prompt12_count_events.py"
    migration_text = migration_path.read_text(encoding="utf-8")

    assert migration_path.exists()
    assert 'revision = "0004_prompt12_count_events"' in migration_text
    assert "create_hypertable('count_events'" in migration_text
    assert "count_events_1m" in migration_text
    assert "count_events_1h" in migration_text
