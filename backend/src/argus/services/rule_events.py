from __future__ import annotations

from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.models.tables import RuleEvent


class _EventWithTimestamp(Protocol):
    ts: object


class SQLRuleEventStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def record(self, event: BaseModel) -> None:
        payload = event.model_dump(mode="json")
        async with self.session_factory() as session:
            session.add(
                RuleEvent(
                    ts=_event_ts(event),
                    camera_id=_event_uuid(event, "camera_id"),
                    rule_id=_event_uuid(event, "rule_id"),
                    event_payload=payload,
                    snapshot_url=None,
                )
            )
            await session.commit()


def _event_uuid(event: BaseModel, field_name: str) -> UUID:
    value = getattr(event, field_name)
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _event_ts(event: BaseModel) -> datetime:
    value = cast(_EventWithTimestamp, event).ts
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
