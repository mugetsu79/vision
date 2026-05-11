from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import EvidenceLedgerSummary
from argus.compat import UTC
from argus.models.enums import EvidenceLedgerAction
from argus.models.tables import EvidenceLedgerEntry


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_json_default,
    )


def compute_entry_hash(
    *,
    incident_id: UUID,
    sequence: int,
    action: EvidenceLedgerAction,
    occurred_at: datetime,
    actor_type: str,
    actor_subject: str | None,
    payload: Mapping[str, object],
    previous_entry_hash: str | None,
) -> str:
    hash_input = {
        "incident_id": str(incident_id),
        "sequence": sequence,
        "action": action.value,
        "occurred_at": occurred_at.isoformat(),
        "actor_type": actor_type,
        "actor_subject": actor_subject,
        "payload": payload,
        "previous_entry_hash": previous_entry_hash,
    }
    return hashlib.sha256(canonical_json(hash_input).encode("utf-8")).hexdigest()


class EvidenceLedgerService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def append_entry(
        self,
        *,
        tenant_id: UUID,
        incident_id: UUID,
        camera_id: UUID,
        action: EvidenceLedgerAction,
        actor_type: str,
        actor_subject: str | None = None,
        occurred_at: datetime | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> EvidenceLedgerEntry:
        occurred = occurred_at or datetime.now(tz=UTC)
        payload_dict = _json_safe_payload(payload or {})
        async with self.session_factory() as session:
            previous_entry = await _load_latest_entry(session, incident_id)
            sequence = 1 if previous_entry is None else previous_entry.sequence + 1
            previous_hash = (
                previous_entry.entry_hash if previous_entry is not None else None
            )
            entry_hash = compute_entry_hash(
                incident_id=incident_id,
                sequence=sequence,
                action=action,
                occurred_at=occurred,
                actor_type=actor_type,
                actor_subject=actor_subject,
                payload=payload_dict,
                previous_entry_hash=previous_hash,
            )
            entry = EvidenceLedgerEntry(
                tenant_id=tenant_id,
                incident_id=incident_id,
                camera_id=camera_id,
                sequence=sequence,
                action=action,
                actor_type=actor_type,
                actor_subject=actor_subject,
                occurred_at=occurred,
                payload=payload_dict,
                previous_entry_hash=previous_hash,
                entry_hash=entry_hash,
            )
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            return entry

    async def list_for_incident(self, *, incident_id: UUID) -> list[EvidenceLedgerEntry]:
        async with self.session_factory() as session:
            statement = (
                select(EvidenceLedgerEntry)
                .where(EvidenceLedgerEntry.incident_id == incident_id)
                .order_by(EvidenceLedgerEntry.sequence.asc())
            )
            return list((await session.execute(statement)).scalars().all())

    async def summary_for_incident(self, *, incident_id: UUID) -> EvidenceLedgerSummary:
        entries = await self.list_for_incident(incident_id=incident_id)
        if not entries:
            return EvidenceLedgerSummary()
        latest_entry = entries[-1]
        return EvidenceLedgerSummary(
            entry_count=len(entries),
            latest_action=latest_entry.action,
            latest_at=latest_entry.occurred_at,
        )


async def _load_latest_entry(
    session: AsyncSession,
    incident_id: UUID,
) -> EvidenceLedgerEntry | None:
    statement = (
        select(EvidenceLedgerEntry)
        .where(EvidenceLedgerEntry.incident_id == incident_id)
        .order_by(EvidenceLedgerEntry.sequence.desc())
        .limit(1)
    )
    return (await session.execute(statement)).scalar_one_or_none()


def _json_safe_payload(payload: Mapping[str, object]) -> dict[str, Any]:
    return json.loads(canonical_json(payload))


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
