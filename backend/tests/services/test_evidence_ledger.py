from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from argus.models.enums import (
    CameraSourceKind,
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)
from argus.models.tables import EvidenceLedgerEntry
from argus.services.evidence_ledger import EvidenceLedgerService, compute_entry_hash


def test_evidence_enums_expose_accountability_values() -> None:
    assert CameraSourceKind.USB.value == "usb"
    assert EvidenceArtifactKind.EVENT_CLIP.value == "event_clip"
    assert EvidenceArtifactStatus.LOCAL_ONLY.value == "local_only"
    assert EvidenceStorageProvider.LOCAL_FILESYSTEM.value == "local_filesystem"
    assert EvidenceStorageScope.EDGE.value == "edge"
    assert EvidenceLedgerAction.INCIDENT_TRIGGERED.value == "incident.triggered"
    assert EvidenceLedgerAction.INCIDENT_RULE_ATTACHED.value == "incident_rule.attached"


@pytest.mark.asyncio
async def test_evidence_ledger_appends_sequence_and_chains_hashes() -> None:
    session_factory = _LedgerSessionFactory()
    service = EvidenceLedgerService(session_factory)
    tenant_id = uuid4()
    incident_id = uuid4()
    camera_id = uuid4()
    occurred_at = datetime(2026, 5, 11, 10, 0, tzinfo=UTC)

    first = await service.append_entry(
        tenant_id=tenant_id,
        incident_id=incident_id,
        camera_id=camera_id,
        action=EvidenceLedgerAction.INCIDENT_TRIGGERED,
        actor_type="system",
        actor_subject=None,
        occurred_at=occurred_at,
        payload={"type": "rule.record_clip"},
    )
    second = await service.append_entry(
        tenant_id=tenant_id,
        incident_id=incident_id,
        camera_id=camera_id,
        action=EvidenceLedgerAction.CLIP_AVAILABLE,
        actor_type="system",
        actor_subject=None,
        occurred_at=occurred_at + timedelta(seconds=3),
        payload={"artifact": "clip"},
    )

    assert first.sequence == 1
    assert first.previous_entry_hash is None
    assert len(first.entry_hash) == 64
    assert second.sequence == 2
    assert second.previous_entry_hash == first.entry_hash
    assert second.entry_hash != first.entry_hash
    assert session_factory.state["commits"] == 2


def test_evidence_ledger_hash_changes_when_payload_changes() -> None:
    incident_id = uuid4()
    occurred_at = datetime(2026, 5, 11, 10, 0, tzinfo=UTC)

    first = compute_entry_hash(
        incident_id=incident_id,
        sequence=1,
        action=EvidenceLedgerAction.INCIDENT_TRIGGERED,
        occurred_at=occurred_at,
        actor_type="system",
        actor_subject=None,
        payload={"count": 1},
        previous_entry_hash=None,
    )
    second = compute_entry_hash(
        incident_id=incident_id,
        sequence=1,
        action=EvidenceLedgerAction.INCIDENT_TRIGGERED,
        occurred_at=occurred_at,
        actor_type="system",
        actor_subject=None,
        payload={"count": 2},
        previous_entry_hash=None,
    )

    assert first != second


@pytest.mark.asyncio
async def test_evidence_ledger_lists_entries_in_sequence_order() -> None:
    session_factory = _LedgerSessionFactory()
    service = EvidenceLedgerService(session_factory)
    tenant_id = uuid4()
    incident_id = uuid4()
    camera_id = uuid4()
    occurred_at = datetime(2026, 5, 11, 10, 0, tzinfo=UTC)
    await service.append_entry(
        tenant_id=tenant_id,
        incident_id=incident_id,
        camera_id=camera_id,
        action=EvidenceLedgerAction.INCIDENT_TRIGGERED,
        actor_type="system",
        actor_subject=None,
        occurred_at=occurred_at,
        payload={},
    )
    await service.append_entry(
        tenant_id=tenant_id,
        incident_id=incident_id,
        camera_id=camera_id,
        action=EvidenceLedgerAction.INCIDENT_REVIEWED,
        actor_type="user",
        actor_subject="operator-1",
        occurred_at=occurred_at + timedelta(minutes=5),
        payload={},
    )

    entries = await service.list_for_incident(incident_id=incident_id)
    summary = await service.summary_for_incident(incident_id=incident_id)

    assert [entry.sequence for entry in entries] == [1, 2]
    assert summary.entry_count == 2
    assert summary.latest_action is EvidenceLedgerAction.INCIDENT_REVIEWED
    assert summary.latest_at == occurred_at + timedelta(minutes=5)


class _Result:
    def __init__(self, values: list[EvidenceLedgerEntry]) -> None:
        self.values = values

    def scalar_one_or_none(self) -> EvidenceLedgerEntry | None:
        return self.values[0] if self.values else None

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[EvidenceLedgerEntry]:
        return self.values


class _LedgerSession:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    async def __aenter__(self) -> _LedgerSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement):  # noqa: ANN001
        entries = self.state["entries"]
        assert isinstance(entries, list)
        ordered = sorted(entries, key=lambda entry: entry.sequence)
        sql = str(statement)
        if "DESC" in sql or "LIMIT" in sql:
            return _Result(list(reversed(ordered[:]))[:1])
        return _Result(ordered)

    def add(self, entry: EvidenceLedgerEntry) -> None:
        entry.id = entry.id or uuid4()
        entries = self.state["entries"]
        assert isinstance(entries, list)
        entries.append(entry)

    async def commit(self) -> None:
        self.state["commits"] = int(self.state.get("commits", 0)) + 1

    async def refresh(self, entry: EvidenceLedgerEntry) -> None:
        entry.created_at = entry.created_at or datetime.now(tz=UTC)


class _LedgerSessionFactory:
    def __init__(self) -> None:
        self.state: dict[str, object] = {"entries": [], "commits": 0}

    def __call__(self) -> _LedgerSession:
        return _LedgerSession(self.state)
