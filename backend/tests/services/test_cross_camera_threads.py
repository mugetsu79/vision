from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from argus.services.cross_camera_threads import (
    CrossCameraIncidentInput,
    CrossCameraThreadCandidate,
    CrossCameraThreadService,
    detect_cross_camera_threads,
)


def test_correlates_identity_light_signals_across_topology_adjacent_cameras() -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    camera_a = uuid4()
    camera_b = uuid4()
    started_at = datetime(2026, 5, 13, 8, 0, tzinfo=UTC)
    incidents = [
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_a,
            ts=started_at,
            class_name="person",
            zone_id="north-gate",
            direction="eastbound",
            privacy_manifest_hash="a" * 64,
            attributes={
                "vest_color": "red",
                "helmet_color": "white",
                "face_id": "face-123",
                "persistent_person_id": "person-123",
            },
            allowed_attributes=["vest_color", "helmet_color"],
        ),
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_b,
            ts=started_at + timedelta(seconds=75),
            class_name="person",
            zone_id="north-gate",
            direction="eastbound",
            privacy_manifest_hash="b" * 64,
            attributes={
                "vest_color": "red",
                "helmet_color": "white",
                "face_embedding": [0.1, 0.2],
            },
            allowed_attributes=["vest_color", "helmet_color"],
        ),
    ]

    threads = detect_cross_camera_threads(
        incidents=incidents,
        topology_edges=[(camera_a, camera_b)],
    )

    assert len(threads) == 1
    thread = threads[0]
    assert thread.tenant_id == tenant_id
    assert thread.site_id == site_id
    assert thread.source_incident_ids == [incident.id for incident in incidents]
    assert thread.camera_ids == [camera_a, camera_b]
    assert thread.privacy_manifest_hashes == ["a" * 64, "b" * 64]
    assert thread.confidence >= 0.75
    assert thread.signals["class_name"] == "person"
    assert thread.signals["zone_id"] == "north-gate"
    assert thread.signals["direction"] == "eastbound"
    assert thread.signals["time_delta_seconds"] == 75
    assert thread.signals["topology"] == {
        "adjacent": True,
        "from_camera_id": str(camera_a),
        "to_camera_id": str(camera_b),
    }
    assert thread.signals["attributes"] == {
        "helmet_color": "white",
        "vest_color": "red",
    }
    assert "same object class" in " ".join(thread.rationale).lower()
    assert "camera topology" in " ".join(thread.rationale).lower()
    assert len(thread.thread_hash) == 64


def test_privacy_manifest_blocks_disallowed_non_biometric_attributes() -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    camera_a = uuid4()
    camera_b = uuid4()
    incidents = [
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_a,
            ts=datetime(2026, 5, 13, 8, 0, tzinfo=UTC),
            class_name="person",
            zone_id="dock",
            direction="northbound",
            privacy_manifest_hash="c" * 64,
            attributes={"vest_color": "orange", "backpack": "black"},
            allowed_attributes=["vest_color"],
        ),
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_b,
            ts=datetime(2026, 5, 13, 8, 1, tzinfo=UTC),
            class_name="person",
            zone_id="dock",
            direction="northbound",
            privacy_manifest_hash="d" * 64,
            attributes={"vest_color": "orange", "backpack": "black"},
            allowed_attributes=["vest_color"],
        ),
    ]

    thread = detect_cross_camera_threads(
        incidents=incidents,
        topology_edges=[(camera_a, camera_b)],
    )[0]

    assert thread.signals["attributes"] == {"vest_color": "orange"}
    assert "backpack" not in json.dumps(thread.signals)


def test_never_emits_biometric_identity_or_persistent_person_ids() -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    camera_a = uuid4()
    camera_b = uuid4()
    incidents = [
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_a,
            ts=datetime(2026, 5, 13, 8, 0, tzinfo=UTC),
            class_name="person",
            zone_id="lobby",
            direction="southbound",
            privacy_manifest_hash="e" * 64,
            attributes={
                "face_id": "face-abc",
                "biometric_identity": "bio-abc",
                "persistent_person_id": "person-abc",
                "person_id": "person-short",
                "face_embedding": [0.1, 0.2],
                "vest_color": "blue",
            },
            allowed_attributes=[
                "face_id",
                "biometric_identity",
                "persistent_person_id",
                "person_id",
                "face_embedding",
                "vest_color",
            ],
        ),
        _incident(
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_b,
            ts=datetime(2026, 5, 13, 8, 2, tzinfo=UTC),
            class_name="person",
            zone_id="lobby",
            direction="southbound",
            privacy_manifest_hash="f" * 64,
            attributes={
                "face_id": "face-abc",
                "biometric_identity": "bio-abc",
                "persistent_person_id": "person-abc",
                "person_id": "person-short",
                "face_embedding": [0.1, 0.2],
                "vest_color": "blue",
            },
            allowed_attributes=[
                "face_id",
                "biometric_identity",
                "persistent_person_id",
                "person_id",
                "face_embedding",
                "vest_color",
            ],
        ),
    ]

    thread = detect_cross_camera_threads(
        incidents=incidents,
        topology_edges=[(camera_a, camera_b)],
    )[0]

    serialized = json.dumps(thread.signals, sort_keys=True)
    assert "face_id" not in serialized
    assert "biometric_identity" not in serialized
    assert "persistent_person_id" not in serialized
    assert "person_id" not in serialized
    assert "face_embedding" not in serialized
    assert not hasattr(thread, "face_id")
    assert not hasattr(thread, "biometric_identity")
    assert not hasattr(thread, "persistent_person_id")
    assert not hasattr(thread, "person_id")


@pytest.mark.asyncio
async def test_cross_camera_thread_service_persists_and_lists_snapshots() -> None:
    incident_a = uuid4()
    incident_b = uuid4()
    candidate = CrossCameraThreadCandidate(
        tenant_id=uuid4(),
        site_id=uuid4(),
        camera_ids=[uuid4(), uuid4()],
        source_incident_ids=[incident_a, incident_b],
        privacy_manifest_hashes=["a" * 64, "b" * 64],
        confidence=0.82,
        rationale=[
            "Same object class observed across adjacent cameras.",
            "Privacy manifests allowed only non-biometric attributes.",
        ],
        signals={
            "class_name": "person",
            "attributes": {"vest_color": "red"},
        },
        privacy_labels=["identity-light", "non-biometric"],
    )
    service = CrossCameraThreadService(_MemorySessionFactory())

    rows = await service.persist_threads([candidate])
    listed = await service.list_threads_for_incident(
        tenant_id=candidate.tenant_id,
        incident_id=incident_b,
    )

    assert len(rows) == 1
    assert rows[0].thread_hash == candidate.thread_hash
    assert rows[0].source_incident_ids == [str(incident_a), str(incident_b)]
    assert rows[0].privacy_manifest_hashes == ["a" * 64, "b" * 64]
    assert listed == rows


def _incident(
    *,
    tenant_id: UUID,
    site_id: UUID,
    camera_id: UUID,
    ts: datetime,
    class_name: str,
    zone_id: str,
    direction: str,
    privacy_manifest_hash: str,
    attributes: dict[str, object],
    allowed_attributes: list[str],
) -> CrossCameraIncidentInput:
    return CrossCameraIncidentInput(
        id=uuid4(),
        tenant_id=tenant_id,
        site_id=site_id,
        camera_id=camera_id,
        ts=ts,
        incident_type="rule.restricted_person",
        privacy_manifest_hash=privacy_manifest_hash,
        privacy_manifest={
            "identity": {
                "face_identification": "disabled",
                "biometric_identification": "disabled",
            },
            "cross_camera": {
                "allowed_non_biometric_attributes": allowed_attributes,
            },
        },
        payload={
            "trigger_rule": {
                "incident_type": "restricted_person",
                "predicate": {
                    "class_names": [class_name],
                    "zone_ids": [zone_id],
                    "attributes": attributes,
                },
            },
            "detection": {
                "class_name": class_name,
                "zone_id": zone_id,
                "direction": direction,
                "attributes": attributes,
            },
        },
    )


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[object]:
        return self.rows


class _MemorySession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    async def __aenter__(self) -> _MemorySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _Result:  # noqa: ANN001
        params = statement.compile().params
        thread_hash = params.get("thread_hash_1")
        tenant_id = params.get("tenant_id_1")
        rows = [
            row
            for row in self.rows
            if thread_hash is None or getattr(row, "thread_hash", None) == thread_hash
        ]
        if tenant_id is not None:
            rows = [row for row in rows if getattr(row, "tenant_id", None) == tenant_id]
        return _Result(rows)

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
