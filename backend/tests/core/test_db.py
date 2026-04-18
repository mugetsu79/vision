from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from traffic_monitor.core.config import Settings
from traffic_monitor.core.db import DatabaseManager


@pytest.mark.asyncio
async def test_database_manager_exposes_async_sessions() -> None:
    settings = Settings(
        _env_file=None,
        db_url="postgresql+asyncpg://traffic_monitor:traffic_monitor@localhost:5432/traffic_monitor",
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    database_manager = DatabaseManager(settings)
    session = database_manager.session_factory()

    assert isinstance(session, AsyncSession)

    await session.close()
    await database_manager.dispose()
