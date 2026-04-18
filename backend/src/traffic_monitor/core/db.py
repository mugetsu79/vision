from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from traffic_monitor.core.config import Settings
from traffic_monitor.models.tables import TrackingEvent
from traffic_monitor.vision.types import Detection


class DatabaseManager:
    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine = create_async_engine(
            settings.db_url,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def ping(self) -> bool:
        async with self.session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True


class TrackingEventStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def record(
        self,
        camera_id: UUID,
        ts: datetime,
        detections: list[Detection],
    ) -> None:
        if not detections:
            return

        rows = [
            TrackingEvent(
                ts=ts,
                camera_id=camera_id,
                class_name=detection.class_name,
                track_id=int(detection.track_id or 0),
                confidence=detection.confidence,
                speed_kph=detection.speed_kph,
                direction_deg=detection.direction_deg,
                zone_id=detection.zone_id,
                attributes=dict(detection.attributes) if detection.attributes else None,
                bbox={
                    "x1": detection.bbox[0],
                    "y1": detection.bbox[1],
                    "x2": detection.bbox[2],
                    "y2": detection.bbox[3],
                },
            )
            for detection in detections
        ]

        async with self.session_factory() as session:
            session.add_all(rows)
            await session.commit()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database_manager: DatabaseManager = request.app.state.db
    async with database_manager.session_factory() as session:
        yield session
