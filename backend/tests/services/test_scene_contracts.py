from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from argus.api.contracts import CameraSourceSettings, EvidenceRecordingPolicy
from argus.models.tables import SceneContractSnapshot
from argus.services.scene_contracts import (
    SceneContractService,
    build_scene_contract,
    hash_contract,
)


def test_camera_source_settings_support_usb_edge_source() -> None:
    source = CameraSourceSettings(kind="usb", uri="usb:///dev/video0", label="Dock Door USB")

    assert source.kind == "usb"
    assert source.uri == "usb:///dev/video0"
    assert source.label == "Dock Door USB"


def test_evidence_recording_policy_defaults_to_short_event_clip() -> None:
    policy = EvidenceRecordingPolicy()

    assert policy.enabled is True
    assert policy.mode == "event_clip"
    assert policy.pre_seconds == 4
    assert policy.post_seconds == 8
    assert policy.fps == 10
    assert policy.max_duration_seconds == 15
    assert policy.storage_profile == "central"


def test_scene_contract_hash_changes_when_runtime_vocabulary_changes() -> None:
    base = build_scene_contract(
        tenant_id="tenant-a",
        site_id="site-a",
        camera_id="camera-a",
        camera_name="Gate A",
        camera_source={"kind": "usb", "uri": "usb:///dev/video0", "redacted_uri": "usb://***"},
        deployment_mode="edge",
        model={"id": "model-a", "format": "onnx", "capability": "fixed_vocab"},
        runtime_vocabulary={"terms": ["person"], "version": 1, "hash": "a" * 64},
        runtime_selection={"backend": "onnxruntime", "fallback_reason": None},
        vision_profile={"preset": "industrial-yard"},
        detection_regions=[],
        candidate_quality={"min_confidence": 0.25},
        recording_policy=EvidenceRecordingPolicy(),
        privacy_manifest_hash="b" * 64,
    )
    changed = build_scene_contract(
        tenant_id="tenant-a",
        site_id="site-a",
        camera_id="camera-a",
        camera_name="Gate A",
        camera_source={"kind": "usb", "uri": "usb:///dev/video0", "redacted_uri": "usb://***"},
        deployment_mode="edge",
        model={"id": "model-a", "format": "onnx", "capability": "fixed_vocab"},
        runtime_vocabulary={"terms": ["person", "forklift"], "version": 2, "hash": "c" * 64},
        runtime_selection={"backend": "onnxruntime", "fallback_reason": None},
        vision_profile={"preset": "industrial-yard"},
        detection_regions=[],
        candidate_quality={"min_confidence": 0.25},
        recording_policy=EvidenceRecordingPolicy(),
        privacy_manifest_hash="b" * 64,
    )

    assert hash_contract(base) != hash_contract(changed)


class _Result:
    def __init__(self, values: list[SceneContractSnapshot]) -> None:
        self.values = values

    def scalar_one_or_none(self) -> SceneContractSnapshot | None:
        return self.values[0] if self.values else None


class _Session:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement):  # noqa: ANN001
        snapshots = self.state["snapshots"]
        assert isinstance(snapshots, list)
        contract_hash = _hash_param_from_statement(statement)
        return _Result(
            [
                snapshot
                for snapshot in snapshots
                if contract_hash is None or snapshot.contract_hash == contract_hash
            ]
        )

    def add(self, snapshot: SceneContractSnapshot) -> None:
        snapshot.id = snapshot.id or uuid4()
        snapshots = self.state["snapshots"]
        assert isinstance(snapshots, list)
        snapshots.append(snapshot)

    async def commit(self) -> None:
        self.state["commits"] = int(self.state.get("commits", 0)) + 1

    async def rollback(self) -> None:
        self.state["rollbacks"] = int(self.state.get("rollbacks", 0)) + 1

    async def refresh(self, snapshot: SceneContractSnapshot) -> None:
        snapshot.created_at = snapshot.created_at or datetime.now(tz=UTC)


class _SessionFactory:
    def __init__(self) -> None:
        self.state: dict[str, object] = {"snapshots": []}

    def __call__(self) -> _Session:
        return _Session(self.state)


@pytest.mark.asyncio
async def test_scene_contract_service_reuses_identical_contract_snapshot() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    contract = build_scene_contract(
        tenant_id=tenant_id,
        site_id=uuid4(),
        camera_id=camera_id,
        camera_name="Gate A",
        camera_source={"kind": "rtsp", "uri": "rtsp://camera.local/live"},
        deployment_mode="central",
        model={"id": "model-a", "format": "onnx", "capability": "fixed_vocab"},
        runtime_vocabulary={"terms": ["person"], "version": 1, "hash": "a" * 64},
        runtime_selection={"backend": "onnxruntime", "fallback_reason": None},
        vision_profile={"preset": "industrial-yard"},
        detection_regions=[],
        candidate_quality={"min_confidence": 0.25},
        recording_policy=EvidenceRecordingPolicy(),
        privacy_manifest_hash="b" * 64,
    )
    session_factory = _SessionFactory()
    service = SceneContractService(session_factory=session_factory)

    first = await service.get_or_create_snapshot(
        tenant_id=tenant_id,
        camera_id=camera_id,
        contract=contract,
    )
    second = await service.get_or_create_snapshot(
        tenant_id=tenant_id,
        camera_id=camera_id,
        contract=contract,
    )

    snapshots = session_factory.state["snapshots"]
    assert isinstance(snapshots, list)
    assert first.id == second.id
    assert first.contract_hash == hash_contract(contract)
    assert len(snapshots) == 1
    assert session_factory.state["commits"] == 1


def _hash_param_from_statement(statement) -> str | None:  # noqa: ANN001
    for key, value in statement.compile().params.items():
        if "hash" in key and isinstance(value, str):
            return value
    return None
