from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import CrossCameraThreadResponse
from argus.models.tables import CrossCameraThread

CROSS_CAMERA_WINDOW = timedelta(minutes=5)
BIOMETRIC_ATTRIBUTE_KEYS = {
    "biometric_id",
    "biometric_identity",
    "face_embedding",
    "face_id",
    "face_template",
    "person_id",
    "persistent_person_id",
}
DEFAULT_PRIVACY_LABELS = ["identity-light", "non-biometric"]


@dataclass(frozen=True, slots=True)
class CrossCameraIncidentInput:
    id: UUID
    tenant_id: UUID
    site_id: UUID | None
    camera_id: UUID
    ts: datetime
    incident_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    privacy_manifest_hash: str | None = None
    privacy_manifest: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CrossCameraThreadCandidate:
    tenant_id: UUID
    site_id: UUID | None
    camera_ids: list[UUID]
    source_incident_ids: list[UUID]
    privacy_manifest_hashes: list[str]
    confidence: float
    rationale: list[str]
    signals: dict[str, Any] = field(default_factory=dict)
    privacy_labels: list[str] = field(default_factory=lambda: list(DEFAULT_PRIVACY_LABELS))

    @property
    def thread_hash(self) -> str:
        payload = {
            "tenant_id": str(self.tenant_id),
            "site_id": str(self.site_id) if self.site_id is not None else None,
            "camera_ids": [str(value) for value in self.camera_ids],
            "source_incident_ids": [str(value) for value in self.source_incident_ids],
            "privacy_manifest_hashes": self.privacy_manifest_hashes,
            "signals": self.signals,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()


class CrossCameraThreadService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def list_threads_for_incident(
        self,
        *,
        tenant_id: UUID,
        incident_id: UUID,
        limit: int = 20,
    ) -> list[CrossCameraThread]:
        bounded_limit = max(1, min(limit, 100))
        async with self.session_factory() as session:
            statement = (
                select(CrossCameraThread)
                .where(CrossCameraThread.tenant_id == tenant_id)
                .order_by(CrossCameraThread.created_at.desc())
                .limit(bounded_limit * 5)
            )
            rows = list((await session.execute(statement)).scalars().all())
        incident_key = str(incident_id)
        return [
            row
            for row in rows
            if incident_key in [str(value) for value in row.source_incident_ids]
        ][:bounded_limit]

    async def persist_threads(
        self,
        threads: list[CrossCameraThreadCandidate],
    ) -> list[CrossCameraThread]:
        rows: list[CrossCameraThread] = []
        async with self.session_factory() as session:
            for thread in threads:
                statement = select(CrossCameraThread).where(
                    CrossCameraThread.thread_hash == thread.thread_hash
                )
                existing = (await session.execute(statement)).scalar_one_or_none()
                if existing is not None:
                    rows.append(existing)
                    continue
                row = _candidate_to_row(thread)
                session.add(row)
                rows.append(row)
            await session.commit()
            for row in rows:
                await session.refresh(row)
        return rows


def detect_cross_camera_threads(
    *,
    incidents: list[CrossCameraIncidentInput],
    topology_edges: list[tuple[UUID, UUID]] | None = None,
    window: timedelta = CROSS_CAMERA_WINDOW,
) -> list[CrossCameraThreadCandidate]:
    ordered_incidents = sorted(incidents, key=lambda incident: incident.ts)
    topology = _normalize_topology(topology_edges or [])
    candidates: list[CrossCameraThreadCandidate] = []

    for index, first in enumerate(ordered_incidents):
        for second in ordered_incidents[index + 1 :]:
            if first.tenant_id != second.tenant_id:
                continue
            if first.site_id != second.site_id:
                continue
            if first.camera_id == second.camera_id:
                continue
            time_delta = second.ts - first.ts
            if time_delta < timedelta(0) or time_delta > window:
                continue

            first_signal = _incident_signal(first)
            second_signal = _incident_signal(second)
            class_name = _matching_value(first_signal.class_name, second_signal.class_name)
            zone_id = _matching_value(first_signal.zone_id, second_signal.zone_id)
            direction = _matching_value(first_signal.direction, second_signal.direction)
            adjacent = _are_adjacent(first.camera_id, second.camera_id, topology)
            attributes = _matching_allowed_attributes(first, second)

            if class_name is None:
                continue
            if not (zone_id or direction or adjacent or attributes):
                continue

            rationale: list[str] = ["Same object class observed across cameras."]
            confidence = 0.2
            if zone_id:
                confidence += 0.15
                rationale.append(f"Matching scene zone: {zone_id}.")
            if direction:
                confidence += 0.15
                rationale.append(f"Matching motion direction: {direction}.")
            if adjacent:
                confidence += 0.15
                rationale.append("Camera topology marks the scenes as adjacent.")
            if attributes:
                confidence += 0.15
                rationale.append(
                    "Privacy manifests allowed matching non-biometric attributes."
                )
            confidence += 0.2
            rationale.append(
                f"Incidents occurred within {int(time_delta.total_seconds())} seconds."
            )

            signals: dict[str, Any] = {
                "class_name": class_name,
                "time_delta_seconds": int(time_delta.total_seconds()),
                "topology": {
                    "adjacent": adjacent,
                    "from_camera_id": str(first.camera_id),
                    "to_camera_id": str(second.camera_id),
                },
            }
            if zone_id:
                signals["zone_id"] = zone_id
            if direction:
                signals["direction"] = direction
            if attributes:
                signals["attributes"] = attributes

            candidates.append(
                CrossCameraThreadCandidate(
                    tenant_id=first.tenant_id,
                    site_id=first.site_id,
                    camera_ids=[first.camera_id, second.camera_id],
                    source_incident_ids=[first.id, second.id],
                    privacy_manifest_hashes=_privacy_hashes([first, second]),
                    confidence=round(min(confidence, 0.95), 2),
                    rationale=rationale,
                    signals=signals,
                )
            )

    return _dedupe_threads(candidates)


def cross_camera_thread_response(row: CrossCameraThread) -> CrossCameraThreadResponse:
    return CrossCameraThreadResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        site_id=row.site_id,
        camera_ids=[UUID(str(value)) for value in row.camera_ids],
        source_incident_ids=[UUID(str(value)) for value in row.source_incident_ids],
        privacy_manifest_hashes=list(row.privacy_manifest_hashes),
        confidence=row.confidence,
        rationale=list(row.rationale),
        signals=dict(row.signals),
        privacy_labels=list(row.privacy_labels),
        thread_hash=row.thread_hash,
        created_at=row.created_at,
    )


@dataclass(frozen=True, slots=True)
class _IncidentSignal:
    class_name: str | None
    zone_id: str | None
    direction: str | None


def _incident_signal(incident: CrossCameraIncidentInput) -> _IncidentSignal:
    detection = incident.payload.get("detection")
    class_name: str | None = None
    zone_id: str | None = None
    direction: str | None = None
    if isinstance(detection, dict):
        class_name = _clean_string(detection.get("class_name"))
        zone_id = _clean_string(detection.get("zone_id"))
        direction = _clean_string(detection.get("direction"))

    trigger_rule = incident.payload.get("trigger_rule")
    if isinstance(trigger_rule, dict):
        predicate = trigger_rule.get("predicate")
        if isinstance(predicate, dict):
            class_name = class_name or _first_clean_string(predicate.get("class_names"))
            zone_id = zone_id or _first_clean_string(predicate.get("zone_ids"))
            direction = direction or _clean_string(predicate.get("direction"))
    return _IncidentSignal(
        class_name=class_name,
        zone_id=zone_id,
        direction=direction,
    )


def _matching_allowed_attributes(
    first: CrossCameraIncidentInput,
    second: CrossCameraIncidentInput,
) -> dict[str, object]:
    first_allowed = _allowed_attribute_names(first.privacy_manifest)
    second_allowed = _allowed_attribute_names(second.privacy_manifest)
    allowed = first_allowed & second_allowed
    if not allowed:
        return {}

    first_attributes = _incident_attributes(first.payload)
    second_attributes = _incident_attributes(second.payload)
    matches: dict[str, object] = {}
    for key in sorted(allowed):
        if _is_biometric_attribute_key(key):
            continue
        first_value = first_attributes.get(key)
        if first_value is None:
            continue
        if first_value == second_attributes.get(key):
            matches[key] = first_value
    return matches


def _allowed_attribute_names(manifest: dict[str, Any] | None) -> set[str]:
    if not isinstance(manifest, dict):
        return set()
    candidates: list[object] = []
    cross_camera = manifest.get("cross_camera")
    if isinstance(cross_camera, dict):
        candidates.extend(
            [
                cross_camera.get("allowed_non_biometric_attributes"),
                cross_camera.get("allowed_attributes"),
            ]
        )
    privacy = manifest.get("privacy")
    if isinstance(privacy, dict):
        privacy_cross_camera = privacy.get("cross_camera")
        if isinstance(privacy_cross_camera, dict):
            candidates.extend(
                [
                    privacy_cross_camera.get("allowed_non_biometric_attributes"),
                    privacy_cross_camera.get("allowed_attributes"),
                ]
            )

    allowed: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, list):
            continue
        for item in candidate:
            cleaned = _clean_string(item)
            if cleaned and not _is_biometric_attribute_key(cleaned):
                allowed.add(cleaned)
    return allowed


def _incident_attributes(payload: dict[str, Any]) -> dict[str, object]:
    attributes: dict[str, object] = {}
    detection = payload.get("detection")
    if isinstance(detection, dict):
        detection_attributes = detection.get("attributes")
        if isinstance(detection_attributes, dict):
            attributes.update(detection_attributes)
    trigger_rule = payload.get("trigger_rule")
    if isinstance(trigger_rule, dict):
        predicate = trigger_rule.get("predicate")
        if isinstance(predicate, dict):
            rule_attributes = predicate.get("attributes")
            if isinstance(rule_attributes, dict):
                attributes.update(rule_attributes)
    return {
        str(key): value
        for key, value in attributes.items()
        if not _is_biometric_attribute_key(str(key))
    }


def _candidate_to_row(thread: CrossCameraThreadCandidate) -> CrossCameraThread:
    return CrossCameraThread(
        tenant_id=thread.tenant_id,
        site_id=thread.site_id,
        camera_ids=[str(value) for value in thread.camera_ids],
        source_incident_ids=[str(value) for value in thread.source_incident_ids],
        privacy_manifest_hashes=list(thread.privacy_manifest_hashes),
        confidence=thread.confidence,
        rationale=list(thread.rationale),
        signals=dict(thread.signals),
        privacy_labels=list(thread.privacy_labels),
        thread_hash=thread.thread_hash,
    )


def _privacy_hashes(incidents: list[CrossCameraIncidentInput]) -> list[str]:
    hashes: list[str] = []
    for incident in incidents:
        if incident.privacy_manifest_hash and incident.privacy_manifest_hash not in hashes:
            hashes.append(incident.privacy_manifest_hash)
    return hashes


def _dedupe_threads(
    threads: list[CrossCameraThreadCandidate],
) -> list[CrossCameraThreadCandidate]:
    by_hash: dict[str, CrossCameraThreadCandidate] = {}
    for thread in threads:
        by_hash.setdefault(thread.thread_hash, thread)
    return list(by_hash.values())


def _normalize_topology(edges: list[tuple[UUID, UUID]]) -> set[tuple[str, str]]:
    normalized: set[tuple[str, str]] = set()
    for first, second in edges:
        normalized.add((str(first), str(second)))
        normalized.add((str(second), str(first)))
    return normalized


def _are_adjacent(first: UUID, second: UUID, topology: set[tuple[str, str]]) -> bool:
    return (str(first), str(second)) in topology


def _matching_value(first: str | None, second: str | None) -> str | None:
    if first and second and first == second:
        return first
    return None


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


def _is_biometric_attribute_key(value: str) -> bool:
    normalized = value.lower()
    return normalized in BIOMETRIC_ATTRIBUTE_KEYS or any(
        token in normalized
        for token in ("face_", "biometric", "embedding", "person_id")
    )
