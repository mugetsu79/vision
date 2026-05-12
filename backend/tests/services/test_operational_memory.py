from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from argus.models.enums import (
    EvidenceArtifactStatus,
    EvidenceStorageProvider,
    EvidenceStorageScope,
    IncidentRuleSeverity,
)
from argus.services.operational_memory import (
    ArtifactMemoryInput,
    IncidentMemoryInput,
    OperationalMemoryPatternCandidate,
    OperationalMemoryService,
    detect_operational_memory_patterns,
)


def test_detects_repeated_event_bursts_by_scene_zone_class_and_window() -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    camera_id = uuid4()
    started_at = datetime(2026, 5, 12, 8, 0, tzinfo=UTC)
    incidents = [
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_id,
            ts=started_at + timedelta(minutes=offset),
            incident_type="restricted_person",
            class_name="person",
            zone_id="server-room",
            scene_contract_hash="a" * 64,
        )
        for offset in (0, 7, 13)
    ]

    patterns = detect_operational_memory_patterns(incidents=incidents, artifacts=[])

    event_burst = _single_pattern(patterns, "event_burst")
    assert event_burst.severity is IncidentRuleSeverity.WARNING
    assert event_burst.window_started_at == started_at
    assert event_burst.window_ended_at == started_at + timedelta(minutes=13)
    assert event_burst.dimensions["site_id"] == str(site_id)
    assert event_burst.dimensions["camera_id"] == str(camera_id)
    assert event_burst.dimensions["zone_id"] == "server-room"
    assert event_burst.dimensions["class_name"] == "person"
    assert event_burst.source_incident_ids == [incident.id for incident in incidents]
    assert event_burst.source_contract_hashes == ["a" * 64]
    assert "observed pattern" in event_burst.summary.lower()


def test_detects_repeated_clip_storage_failures_by_provider_edge_and_camera() -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    incidents = [
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            ts=datetime(2026, 5, 12, 10, minute, tzinfo=UTC),
            incident_type="rule.ppe_missing",
            class_name="hardhat",
            zone_id="dock",
            scene_contract_hash="b" * 64,
        )
        for minute in (3, 8)
    ]
    artifacts = [
        ArtifactMemoryInput(
            id=uuid4(),
            incident_id=incident.id,
            camera_id=camera_id,
            status=EvidenceArtifactStatus.CAPTURE_FAILED,
            storage_provider=EvidenceStorageProvider.S3_COMPATIBLE,
            storage_scope=EvidenceStorageScope.EDGE,
            created_at=incident.ts,
        )
        for incident in incidents
    ]

    patterns = detect_operational_memory_patterns(incidents=incidents, artifacts=artifacts)

    storage_failure = _single_pattern(patterns, "storage_failure")
    assert storage_failure.severity is IncidentRuleSeverity.CRITICAL
    assert storage_failure.dimensions["provider"] == "s3_compatible"
    assert storage_failure.dimensions["scope"] == "edge"
    assert storage_failure.dimensions["edge_node_id"] == str(edge_node_id)
    assert storage_failure.dimensions["camera_id"] == str(camera_id)
    assert storage_failure.source_incident_ids == [incident.id for incident in incidents]
    assert storage_failure.source_contract_hashes == ["b" * 64]


def test_detects_zone_hot_spots_after_scene_contract_changes() -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    camera_id = uuid4()
    incidents = [
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_id,
            ts=datetime(2026, 5, 12, 11, minute, tzinfo=UTC),
            incident_type="rule.forklift",
            class_name="forklift",
            zone_id="north-aisle",
            scene_contract_hash=contract_hash,
        )
        for minute, contract_hash in (
            (0, "c" * 64),
            (12, "d" * 64),
            (20, "d" * 64),
        )
    ]

    patterns = detect_operational_memory_patterns(incidents=incidents, artifacts=[])

    hotspot = _single_pattern(patterns, "zone_hotspot")
    assert hotspot.severity is IncidentRuleSeverity.WARNING
    assert hotspot.dimensions["zone_id"] == "north-aisle"
    assert hotspot.dimensions["contract_count"] == 2
    assert hotspot.source_contract_hashes == ["c" * 64, "d" * 64]
    assert "scene contract" in hotspot.summary.lower()


@pytest.mark.asyncio
async def test_operational_memory_service_persists_pattern_snapshots() -> None:
    tenant_id = uuid4()
    pattern = OperationalMemoryPatternCandidate(
        tenant_id=tenant_id,
        site_id=uuid4(),
        camera_id=uuid4(),
        pattern_type="event_burst",
        severity=IncidentRuleSeverity.WARNING,
        summary="Observed pattern: 3 incidents in one zone.",
        window_started_at=datetime(2026, 5, 12, 8, 0, tzinfo=UTC),
        window_ended_at=datetime(2026, 5, 12, 8, 15, tzinfo=UTC),
        source_incident_ids=[uuid4(), uuid4(), uuid4()],
        source_contract_hashes=["e" * 64],
        dimensions={"zone_id": "server-room"},
        evidence={"incident_count": 3},
    )
    session_factory = _MemorySessionFactory()
    service = OperationalMemoryService(session_factory)

    rows = await service.persist_patterns([pattern])

    assert len(rows) == 1
    assert rows[0].pattern_hash == pattern.pattern_hash
    assert rows[0].source_incident_ids == [str(value) for value in pattern.source_incident_ids]
    assert rows[0].source_contract_hashes == ["e" * 64]
    assert rows[0].summary == pattern.summary


def _single_pattern(
    patterns: list[OperationalMemoryPatternCandidate],
    pattern_type: str,
) -> OperationalMemoryPatternCandidate:
    matches = [pattern for pattern in patterns if pattern.pattern_type == pattern_type]
    assert len(matches) == 1
    return matches[0]


def _incident(
    *,
    tenant_id: UUID,
    site_id: UUID,
    camera_id: UUID,
    ts: datetime,
    incident_type: str,
    class_name: str,
    zone_id: str,
    scene_contract_hash: str,
    edge_node_id: UUID | None = None,
) -> IncidentMemoryInput:
    return IncidentMemoryInput(
        id=uuid4(),
        tenant_id=tenant_id,
        site_id=site_id,
        camera_id=camera_id,
        edge_node_id=edge_node_id,
        ts=ts,
        incident_type=incident_type,
        scene_contract_hash=scene_contract_hash,
        payload={
            "trigger_rule": {
                "incident_type": incident_type.removeprefix("rule."),
                "predicate": {
                    "class_names": [class_name],
                    "zone_ids": [zone_id],
                },
            },
            "detection": {
                "class_name": class_name,
                "zone_id": zone_id,
            },
        },
    )


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None


class _MemorySession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    async def __aenter__(self) -> _MemorySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _Result:  # noqa: ANN001
        pattern_hash = statement.compile().params.get("pattern_hash_1")
        return _Result(
            [
                row
                for row in self.rows
                if pattern_hash is None or getattr(row, "pattern_hash", None) == pattern_hash
            ]
        )

    def add(self, row: object) -> None:
        self.rows.append(row)

    async def commit(self) -> None:
        return None

    async def refresh(self, row: object) -> None:
        return None


class _MemorySessionFactory:
    def __init__(self) -> None:
        self.session = _MemorySession()

    def __call__(self) -> _MemorySession:
        return self.session
