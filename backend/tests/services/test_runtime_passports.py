from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from argus.models.enums import DetectorCapability, RuntimeArtifactKind, RuntimeArtifactPrecision
from argus.models.tables import RuntimePassportSnapshot
from argus.services.runtime_passports import (
    RuntimePassportService,
    build_runtime_passport,
    hash_runtime_passport,
)


def test_runtime_passport_hash_is_deterministic_for_fixed_vocab_onnx_selection() -> None:
    passport = build_runtime_passport(
        tenant_id="tenant-a",
        camera_id="camera-a",
        scene_contract_hash="a" * 64,
        model_metadata={
            "id": "model-a",
            "name": "YOLO fixed vocab",
            "sha256": "b" * 64,
            "capability": DetectorCapability.FIXED_VOCAB,
            "runtime_backend": "onnxruntime",
        },
        runtime_selection={
            "profile_id": "11111111-1111-1111-1111-111111111111",
            "profile_name": "Default runtime",
            "profile_hash": "c" * 64,
            "artifact_preference": "onnx_first",
            "fallback_allowed": True,
            "preferred_backend": "onnxruntime",
        },
        selection_report={
            "selected_backend": "onnxruntime",
            "fallback": False,
            "fallback_reason": None,
        },
        provider_versions={"onnxruntime": "1.20.0"},
    )

    same_passport = build_runtime_passport(
        tenant_id="tenant-a",
        camera_id="camera-a",
        scene_contract_hash="a" * 64,
        model_metadata={
            "runtime_backend": "onnxruntime",
            "capability": "fixed_vocab",
            "sha256": "b" * 64,
            "name": "YOLO fixed vocab",
            "id": "model-a",
        },
        runtime_selection={
            "preferred_backend": "onnxruntime",
            "fallback_allowed": True,
            "artifact_preference": "onnx_first",
            "profile_hash": "c" * 64,
            "profile_name": "Default runtime",
            "profile_id": "11111111-1111-1111-1111-111111111111",
        },
        selection_report={
            "fallback_reason": None,
            "fallback": False,
            "selected_backend": "onnxruntime",
        },
        provider_versions={"onnxruntime": "1.20.0"},
    )

    assert passport == same_passport
    assert hash_runtime_passport(passport) == hash_runtime_passport(same_passport)
    assert passport["selected_runtime"]["backend"] == "onnxruntime"
    assert passport["selected_runtime"]["fallback_reason"] is None
    assert passport["runtime_selection_profile"]["profile_hash"] == "c" * 64


def test_runtime_passport_hash_changes_when_provider_versions_change() -> None:
    passport = _artifact_passport(provider_versions={"tensorrt": "10.0.0"})
    upgraded = _artifact_passport(provider_versions={"tensorrt": "10.1.0"})

    assert hash_runtime_passport(passport) != hash_runtime_passport(upgraded)


def test_runtime_passport_represents_tensorrt_runtime_artifact_selection() -> None:
    artifact_id = str(uuid4())
    passport = _artifact_passport(
        runtime_artifact={
            "id": artifact_id,
            "kind": RuntimeArtifactKind.TENSORRT_ENGINE,
            "sha256": "d" * 64,
            "runtime_backend": "tensorrt_engine",
            "target_profile": "linux-aarch64-nvidia-jetson",
            "precision": RuntimeArtifactPrecision.FP16,
            "source_model_sha256": "b" * 64,
            "validated_at": datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            "runtime_versions": {"tensorrt": "10.0.0", "cuda": "12.6"},
        },
    )

    selected = passport["selected_runtime"]
    assert selected["backend"] == "tensorrt_engine"
    assert selected["runtime_artifact_id"] == artifact_id
    assert selected["runtime_artifact_hash"] == "d" * 64
    assert selected["target_profile"] == "linux-aarch64-nvidia-jetson"
    assert selected["precision"] == "fp16"
    assert selected["validated_at"] == "2026-05-12T10:00:00+00:00"


def test_runtime_passport_represents_compiled_open_vocab_scene_artifact() -> None:
    passport = _artifact_passport(
        model_metadata={
            "id": "model-open",
            "name": "Open vocab detector",
            "sha256": "f" * 64,
            "capability": DetectorCapability.OPEN_VOCAB,
            "runtime_backend": "tensorrt_engine",
        },
        runtime_artifact={
            "id": str(uuid4()),
            "kind": RuntimeArtifactKind.COMPILED_OPEN_VOCAB,
            "sha256": "e" * 64,
            "runtime_backend": "tensorrt_engine",
            "target_profile": "linux-aarch64-nvidia-jetson",
            "precision": RuntimeArtifactPrecision.FP16,
            "source_model_sha256": "f" * 64,
            "vocabulary_hash": "9" * 64,
            "validated_at": "2026-05-12T11:00:00+00:00",
        },
        scene_vocabulary_hash="9" * 64,
    )

    assert passport["model"]["capability"] == "open_vocab"
    assert passport["selected_runtime"]["runtime_artifact_kind"] == "compiled_open_vocab"
    assert passport["selected_runtime"]["scene_vocabulary_hash"] == "9" * 64


def test_runtime_passport_represents_dynamic_pt_fallback_reason() -> None:
    passport = build_runtime_passport(
        tenant_id="tenant-a",
        camera_id="camera-a",
        scene_contract_hash="a" * 64,
        model_metadata={
            "id": "model-pt",
            "name": "Dynamic PT",
            "sha256": "8" * 64,
            "capability": DetectorCapability.OPEN_VOCAB,
            "runtime_backend": "ultralytics_pt",
        },
        runtime_selection={
            "profile_id": None,
            "profile_name": None,
            "profile_hash": None,
            "artifact_preference": "tensorrt_first",
            "fallback_allowed": True,
            "preferred_backend": "ultralytics_pt",
        },
        selection_report={
            "selected_backend": "ultralytics_pt",
            "fallback": True,
            "fallback_reason": "no_validated_runtime_artifact",
        },
        scene_vocabulary_hash="7" * 64,
    )

    assert passport["selected_runtime"]["backend"] == "ultralytics_pt"
    assert passport["selected_runtime"]["fallback"] is True
    assert passport["selected_runtime"]["fallback_reason"] == "no_validated_runtime_artifact"
    assert passport["selected_runtime"]["runtime_artifact_id"] is None


@pytest.mark.asyncio
async def test_runtime_passport_service_dedupes_by_hash() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    passport = _artifact_passport(tenant_id=tenant_id, camera_id=camera_id)
    session_factory = _PassportSessionFactory()
    service = RuntimePassportService(session_factory)

    first = await service.get_or_create_snapshot(
        tenant_id=tenant_id,
        camera_id=camera_id,
        passport=passport,
    )
    second = await service.get_or_create_snapshot(
        tenant_id=tenant_id,
        camera_id=camera_id,
        passport=dict(passport),
    )

    assert first.id == second.id
    assert len(session_factory.rows) == 1
    assert session_factory.rows[0].passport_hash == hash_runtime_passport(passport)


class _Result:
    def __init__(self, values: list[RuntimePassportSnapshot]) -> None:
        self.values = values

    def scalar_one_or_none(self) -> RuntimePassportSnapshot | None:
        return self.values[0] if self.values else None


class _PassportSession:
    def __init__(self, rows: list[RuntimePassportSnapshot]) -> None:
        self.rows = rows

    async def __aenter__(self) -> _PassportSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _Result:  # noqa: ANN001
        passport_hash = _hash_param_from_statement(statement)
        return _Result(
            [
                row
                for row in self.rows
                if passport_hash is None or row.passport_hash == passport_hash
            ]
        )

    def add(self, value: RuntimePassportSnapshot) -> None:
        value.id = value.id or uuid4()
        self.rows.append(value)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def refresh(self, value: RuntimePassportSnapshot) -> None:
        value.created_at = value.created_at or datetime.now(tz=UTC)


class _PassportSessionFactory:
    def __init__(self) -> None:
        self.rows: list[RuntimePassportSnapshot] = []

    def __call__(self) -> _PassportSession:
        return _PassportSession(self.rows)


def _hash_param_from_statement(statement) -> str | None:  # noqa: ANN001
    for key, value in statement.compile().params.items():
        if "hash" in key and isinstance(value, str):
            return value
    return None


def _artifact_passport(
    *,
    tenant_id: object = "tenant-a",
    camera_id: object = "camera-a",
    model_metadata: dict[str, object] | None = None,
    runtime_artifact: dict[str, object] | None = None,
    provider_versions: dict[str, object] | None = None,
    scene_vocabulary_hash: str | None = None,
) -> dict[str, object]:
    artifact = runtime_artifact or {
        "id": str(uuid4()),
        "kind": RuntimeArtifactKind.TENSORRT_ENGINE,
        "sha256": "d" * 64,
        "runtime_backend": "tensorrt_engine",
        "target_profile": "linux-aarch64-nvidia-jetson",
        "precision": RuntimeArtifactPrecision.FP16,
        "source_model_sha256": "b" * 64,
        "validated_at": "2026-05-12T10:00:00+00:00",
    }
    return build_runtime_passport(
        tenant_id=tenant_id,
        camera_id=camera_id,
        scene_contract_hash="a" * 64,
        model_metadata=model_metadata
        or {
            "id": "model-a",
            "name": "YOLO fixed vocab",
            "sha256": "b" * 64,
            "capability": DetectorCapability.FIXED_VOCAB,
            "runtime_backend": "tensorrt_engine",
        },
        runtime_selection={
            "profile_id": "11111111-1111-1111-1111-111111111111",
            "profile_name": "Jetson runtime",
            "profile_hash": "c" * 64,
            "artifact_preference": "tensorrt_first",
            "fallback_allowed": True,
            "preferred_backend": "tensorrt_engine",
        },
        runtime_artifact=artifact,
        selection_report={
            "selected_backend": "tensorrt_engine",
            "fallback": False,
            "fallback_reason": None,
        },
        provider_versions=provider_versions,
        scene_vocabulary_hash=scene_vocabulary_hash,
    )
