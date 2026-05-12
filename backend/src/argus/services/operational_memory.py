from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.models.enums import (
    EvidenceArtifactStatus,
    EvidenceStorageProvider,
    EvidenceStorageScope,
    IncidentRuleSeverity,
)
from argus.models.tables import OperationalMemoryPattern

EVENT_BURST_MIN_COUNT = 3
EVENT_BURST_WINDOW = timedelta(minutes=30)
STORAGE_FAILURE_MIN_COUNT = 2
ZONE_HOTSPOT_MIN_COUNT = 3


@dataclass(frozen=True, slots=True)
class IncidentMemoryInput:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    camera_id: UUID
    ts: datetime
    incident_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    scene_contract_hash: str | None = None
    edge_node_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ArtifactMemoryInput:
    id: UUID
    incident_id: UUID
    camera_id: UUID
    status: EvidenceArtifactStatus
    storage_provider: EvidenceStorageProvider
    storage_scope: EvidenceStorageScope
    created_at: datetime


@dataclass(frozen=True, slots=True)
class OperationalMemoryPatternCandidate:
    tenant_id: UUID
    site_id: UUID | None
    camera_id: UUID | None
    pattern_type: str
    severity: IncidentRuleSeverity
    summary: str
    window_started_at: datetime
    window_ended_at: datetime
    source_incident_ids: list[UUID]
    source_contract_hashes: list[str]
    dimensions: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def pattern_hash(self) -> str:
        payload = {
            "pattern_type": self.pattern_type,
            "tenant_id": str(self.tenant_id),
            "site_id": str(self.site_id) if self.site_id is not None else None,
            "camera_id": str(self.camera_id) if self.camera_id is not None else None,
            "window_started_at": self.window_started_at.isoformat(),
            "window_ended_at": self.window_ended_at.isoformat(),
            "source_incident_ids": [str(value) for value in self.source_incident_ids],
            "source_contract_hashes": self.source_contract_hashes,
            "dimensions": self.dimensions,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()


class OperationalMemoryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def list_patterns(
        self,
        *,
        tenant_id: UUID,
        incident_id: UUID | None = None,
        camera_id: UUID | None = None,
        site_id: UUID | None = None,
        limit: int = 20,
    ) -> list[OperationalMemoryPattern]:
        bounded_limit = max(1, min(limit, 100))
        async with self.session_factory() as session:
            statement = (
                select(OperationalMemoryPattern)
                .where(OperationalMemoryPattern.tenant_id == tenant_id)
                .order_by(OperationalMemoryPattern.created_at.desc())
                .limit(bounded_limit * 5 if incident_id is not None else bounded_limit)
            )
            if camera_id is not None:
                statement = statement.where(OperationalMemoryPattern.camera_id == camera_id)
            if site_id is not None:
                statement = statement.where(OperationalMemoryPattern.site_id == site_id)
            rows = list((await session.execute(statement)).scalars().all())
        if incident_id is not None:
            incident_key = str(incident_id)
            rows = [
                row
                for row in rows
                if incident_key in [str(value) for value in row.source_incident_ids]
            ]
        return rows[:bounded_limit]

    async def persist_patterns(
        self,
        patterns: list[OperationalMemoryPatternCandidate],
    ) -> list[OperationalMemoryPattern]:
        rows: list[OperationalMemoryPattern] = []
        async with self.session_factory() as session:
            for pattern in patterns:
                statement = select(OperationalMemoryPattern).where(
                    OperationalMemoryPattern.pattern_hash == pattern.pattern_hash
                )
                existing = (await session.execute(statement)).scalar_one_or_none()
                if existing is not None:
                    rows.append(existing)
                    continue
                row = _candidate_to_row(pattern)
                session.add(row)
                rows.append(row)
            await session.commit()
            for row in rows:
                await session.refresh(row)
        return rows


def detect_operational_memory_patterns(
    *,
    incidents: list[IncidentMemoryInput],
    artifacts: list[ArtifactMemoryInput],
) -> list[OperationalMemoryPatternCandidate]:
    ordered_incidents = sorted(incidents, key=lambda incident: incident.ts)
    by_incident_id = {incident.id: incident for incident in ordered_incidents}
    patterns: list[OperationalMemoryPatternCandidate] = []
    patterns.extend(_event_burst_patterns(ordered_incidents))
    patterns.extend(_storage_failure_patterns(artifacts, by_incident_id))
    patterns.extend(_zone_hotspot_patterns(ordered_incidents))
    return _dedupe_patterns(patterns)


def _event_burst_patterns(
    incidents: list[IncidentMemoryInput],
) -> list[OperationalMemoryPatternCandidate]:
    groups: dict[
        tuple[UUID, UUID, UUID, str, str, str],
        list[IncidentMemoryInput],
    ] = {}
    for incident in incidents:
        class_name, zone_id = _class_and_zone(incident.payload)
        if not class_name or not zone_id:
            continue
        key = (
            incident.tenant_id,
            incident.site_id,
            incident.camera_id,
            incident.incident_type,
            class_name,
            zone_id,
        )
        groups.setdefault(key, []).append(incident)

    patterns: list[OperationalMemoryPatternCandidate] = []
    for (
        tenant_id,
        site_id,
        camera_id,
        incident_type,
        class_name,
        zone_id,
    ), values in groups.items():
        if len(values) < EVENT_BURST_MIN_COUNT:
            continue
        window_started_at = values[0].ts
        window_ended_at = values[-1].ts
        if window_ended_at - window_started_at > EVENT_BURST_WINDOW:
            continue
        patterns.append(
            OperationalMemoryPatternCandidate(
                tenant_id=tenant_id,
                site_id=site_id,
                camera_id=camera_id,
                pattern_type="event_burst",
                severity=IncidentRuleSeverity.WARNING,
                summary=(
                    "Observed pattern: "
                    f"{len(values)} {incident_type} incidents for {class_name} "
                    f"in zone {zone_id} within "
                    f"{_format_duration(window_ended_at - window_started_at)}."
                ),
                window_started_at=window_started_at,
                window_ended_at=window_ended_at,
                source_incident_ids=[incident.id for incident in values],
                source_contract_hashes=_contract_hashes(values),
                dimensions={
                    "site_id": str(site_id),
                    "camera_id": str(camera_id),
                    "incident_type": incident_type,
                    "class_name": class_name,
                    "zone_id": zone_id,
                },
                evidence={"incident_count": len(values)},
            )
        )
    return patterns


def _storage_failure_patterns(
    artifacts: list[ArtifactMemoryInput],
    by_incident_id: dict[UUID, IncidentMemoryInput],
) -> list[OperationalMemoryPatternCandidate]:
    failure_statuses = {
        EvidenceArtifactStatus.CAPTURE_FAILED,
        EvidenceArtifactStatus.QUOTA_EXCEEDED,
    }
    groups: dict[
        tuple[
            UUID,
            UUID | None,
            UUID,
            UUID | None,
            EvidenceStorageProvider,
            EvidenceStorageScope,
        ],
        list[ArtifactMemoryInput],
    ] = {}
    for artifact in sorted(artifacts, key=lambda value: value.created_at):
        if artifact.status not in failure_statuses:
            continue
        incident = by_incident_id.get(artifact.incident_id)
        if incident is None:
            continue
        key = (
            incident.tenant_id,
            incident.site_id,
            artifact.camera_id,
            incident.edge_node_id,
            artifact.storage_provider,
            artifact.storage_scope,
        )
        groups.setdefault(key, []).append(artifact)

    patterns: list[OperationalMemoryPatternCandidate] = []
    for (
        tenant_id,
        site_id,
        camera_id,
        edge_node_id,
        provider,
        scope,
    ), values in groups.items():
        if len(values) < STORAGE_FAILURE_MIN_COUNT:
            continue
        incidents = [by_incident_id[value.incident_id] for value in values]
        patterns.append(
            OperationalMemoryPatternCandidate(
                tenant_id=tenant_id,
                site_id=site_id,
                camera_id=camera_id,
                pattern_type="storage_failure",
                severity=IncidentRuleSeverity.CRITICAL,
                summary=(
                    "Observed pattern: "
                    f"{len(values)} evidence storage failures for {provider.value} "
                    f"on {scope.value} storage."
                ),
                window_started_at=values[0].created_at,
                window_ended_at=values[-1].created_at,
                source_incident_ids=[incident.id for incident in incidents],
                source_contract_hashes=_contract_hashes(incidents),
                dimensions={
                    "site_id": str(site_id) if site_id is not None else None,
                    "camera_id": str(camera_id),
                    "edge_node_id": str(edge_node_id) if edge_node_id is not None else None,
                    "provider": provider.value,
                    "scope": scope.value,
                },
                evidence={
                    "artifact_count": len(values),
                    "statuses": sorted({value.status.value for value in values}),
                },
            )
        )
    return patterns


def _zone_hotspot_patterns(
    incidents: list[IncidentMemoryInput],
) -> list[OperationalMemoryPatternCandidate]:
    groups: dict[tuple[UUID, UUID, UUID, str], list[IncidentMemoryInput]] = {}
    for incident in incidents:
        _class_name, zone_id = _class_and_zone(incident.payload)
        if not zone_id:
            continue
        key = (incident.tenant_id, incident.site_id, incident.camera_id, zone_id)
        groups.setdefault(key, []).append(incident)

    patterns: list[OperationalMemoryPatternCandidate] = []
    for (tenant_id, site_id, camera_id, zone_id), values in groups.items():
        contract_hashes = _contract_hashes(values)
        if len(values) < ZONE_HOTSPOT_MIN_COUNT or len(contract_hashes) < 2:
            continue
        patterns.append(
            OperationalMemoryPatternCandidate(
                tenant_id=tenant_id,
                site_id=site_id,
                camera_id=camera_id,
                pattern_type="zone_hotspot",
                severity=IncidentRuleSeverity.WARNING,
                summary=(
                    "Observed pattern: "
                    f"{len(values)} incidents in zone {zone_id} across "
                    f"{len(contract_hashes)} scene contract hashes."
                ),
                window_started_at=values[0].ts,
                window_ended_at=values[-1].ts,
                source_incident_ids=[incident.id for incident in values],
                source_contract_hashes=contract_hashes,
                dimensions={
                    "site_id": str(site_id),
                    "camera_id": str(camera_id),
                    "zone_id": zone_id,
                    "contract_count": len(contract_hashes),
                },
                evidence={"incident_count": len(values)},
            )
        )
    return patterns


def _class_and_zone(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    detection = payload.get("detection")
    class_name: str | None = None
    zone_id: str | None = None
    if isinstance(detection, dict):
        class_name = _clean_string(detection.get("class_name"))
        zone_id = _clean_string(detection.get("zone_id"))

    trigger_rule = payload.get("trigger_rule")
    if isinstance(trigger_rule, dict):
        predicate = trigger_rule.get("predicate")
        if isinstance(predicate, dict):
            class_name = class_name or _first_clean_string(predicate.get("class_names"))
            zone_id = zone_id or _first_clean_string(predicate.get("zone_ids"))
    return class_name, zone_id


def _candidate_to_row(pattern: OperationalMemoryPatternCandidate) -> OperationalMemoryPattern:
    return OperationalMemoryPattern(
        tenant_id=pattern.tenant_id,
        site_id=pattern.site_id,
        camera_id=pattern.camera_id,
        pattern_type=pattern.pattern_type,
        severity=pattern.severity,
        summary=pattern.summary,
        window_started_at=pattern.window_started_at,
        window_ended_at=pattern.window_ended_at,
        source_incident_ids=[str(value) for value in pattern.source_incident_ids],
        source_contract_hashes=list(pattern.source_contract_hashes),
        dimensions=dict(pattern.dimensions),
        evidence=dict(pattern.evidence),
        pattern_hash=pattern.pattern_hash,
    )


def _contract_hashes(incidents: list[IncidentMemoryInput]) -> list[str]:
    hashes: list[str] = []
    for incident in incidents:
        if incident.scene_contract_hash and incident.scene_contract_hash not in hashes:
            hashes.append(incident.scene_contract_hash)
    return sorted(hashes)


def _dedupe_patterns(
    patterns: list[OperationalMemoryPatternCandidate],
) -> list[OperationalMemoryPatternCandidate]:
    by_hash: dict[str, OperationalMemoryPatternCandidate] = {}
    for pattern in patterns:
        by_hash.setdefault(pattern.pattern_hash, pattern)
    return list(by_hash.values())


def _first_clean_string(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    for item in value:
        cleaned = _clean_string(item)
        if cleaned:
            return cleaned
    return None


def _clean_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _format_duration(value: timedelta) -> str:
    total_minutes = max(0, int(value.total_seconds() // 60))
    if total_minutes == 1:
        return "1 minute"
    return f"{total_minutes} minutes"
