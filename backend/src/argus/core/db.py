from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from argus.core.config import Settings
from argus.core.metrics import TRACKING_EVENT_WRITE_FAILURES_TOTAL
from argus.models.tables import CountEvent, TrackingEvent
from argus.vision.types import Detection

if TYPE_CHECKING:
    from argus.vision.count_events import CountEventRecord


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
        *,
        vocabulary_version: int | None = None,
        vocabulary_hash: str | None = None,
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
                vocabulary_version=vocabulary_version,
                vocabulary_hash=vocabulary_hash,
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
            try:
                session.add_all(rows)
                await session.commit()
            except Exception:
                TRACKING_EVENT_WRITE_FAILURES_TOTAL.labels(store="tracking-events").inc()
                raise


class CountEventStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def record(
        self,
        camera_id: UUID,
        events: list[CountEventRecord],
        *,
        vocabulary_version: int | None = None,
        vocabulary_hash: str | None = None,
    ) -> None:
        if not events:
            return

        async with self.session_factory() as session:
            try:
                session.add_all(
                    [
                        CountEvent(
                            ts=event.ts,
                            camera_id=camera_id,
                            class_name=event.class_name,
                            track_id=event.track_id,
                            event_type=event.event_type,
                            boundary_id=event.boundary_id,
                            direction=event.direction,
                            from_zone_id=event.from_zone_id,
                            to_zone_id=event.to_zone_id,
                            speed_kph=event.speed_kph,
                            confidence=event.confidence,
                            attributes=dict(event.attributes) if event.attributes else None,
                            payload=dict(event.payload),
                            vocabulary_version=vocabulary_version,
                            vocabulary_hash=vocabulary_hash,
                        )
                        for event in events
                    ]
                )
                await session.commit()
            except Exception:
                TRACKING_EVENT_WRITE_FAILURES_TOTAL.labels(store="count-events").inc()
                raise


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database_manager: DatabaseManager = request.app.state.db
    async with database_manager.session_factory() as session:
        yield session
