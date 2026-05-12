from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from argus.inference.engine import (
    ModelSettings,
    RuntimeArtifactSettings,
    RuntimeVocabularySettings,
)
from argus.models.enums import (
    DetectorCapability,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
)
from argus.vision.runtime_selection import RuntimeSelectionError, select_runtime_artifact
from argus.vision.vocabulary import hash_vocabulary


def _model(
    *,
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB,
    backend: str = "onnxruntime",
    runtime_vocabulary: list[str] | None = None,
) -> ModelSettings:
    return ModelSettings(
        name="YOLO26n",
        path="/models/yolo26n.onnx",
        capability=capability,
        capability_config={"runtime_backend": backend},
        classes=[] if capability is DetectorCapability.OPEN_VOCAB else ["person", "car"],
        runtime_vocabulary=RuntimeVocabularySettings(terms=runtime_vocabulary or []),
        input_shape={"width": 640, "height": 640},
    )


def _artifact(
    *,
    kind: RuntimeArtifactKind = RuntimeArtifactKind.TENSORRT_ENGINE,
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB,
    target_profile: str = "linux-aarch64-nvidia-jetson",
    vocabulary_hash: str | None = None,
) -> RuntimeArtifactSettings:
    return RuntimeArtifactSettings(
        id=uuid4(),
        scope=RuntimeArtifactScope.MODEL,
        kind=kind,
        capability=capability,
        runtime_backend="tensorrt_engine"
        if kind is RuntimeArtifactKind.TENSORRT_ENGINE
        else "onnxruntime",
        path="/models/yolo26n.engine"
        if kind is RuntimeArtifactKind.TENSORRT_ENGINE
        else "/models/yolo26n.onnx",
        target_profile=target_profile,
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=[] if capability is DetectorCapability.OPEN_VOCAB else ["person", "car"],
        vocabulary_hash=vocabulary_hash,
        vocabulary_version=1 if vocabulary_hash is not None else None,
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=1234,
    )


def test_select_runtime_artifact_prefers_exact_valid_tensorrt_target() -> None:
    artifact = _artifact()

    selection = select_runtime_artifact(
        model=_model(),
        host_profile="linux-aarch64-nvidia-jetson",
        artifacts=[artifact],
        runtime_vocabulary_hash=None,
    )

    assert selection.selected_backend == "tensorrt_engine"
    assert selection.artifact == artifact
    assert selection.fallback is False
    assert selection.fallback_reason is None


def test_select_runtime_artifact_target_mismatch_falls_back_to_model_runtime() -> None:
    selection = select_runtime_artifact(
        model=_model(),
        host_profile="linux-aarch64-nvidia-jetson",
        artifacts=[_artifact(target_profile="linux-x86_64-nvidia")],
        runtime_vocabulary_hash=None,
    )

    assert selection.selected_backend == "onnxruntime"
    assert selection.artifact is None
    assert selection.fallback is True
    assert selection.fallback_reason == "artifact_target_mismatch"


def test_select_runtime_artifact_open_vocab_mismatch_falls_back_to_dynamic() -> None:
    selection = select_runtime_artifact(
        model=_model(
            capability=DetectorCapability.OPEN_VOCAB,
            backend="ultralytics_yoloe",
            runtime_vocabulary=["forklift"],
        ),
        host_profile="linux-aarch64-nvidia-jetson",
        artifacts=[
            _artifact(
                capability=DetectorCapability.OPEN_VOCAB,
                vocabulary_hash=hash_vocabulary(["person"]),
            )
        ],
        runtime_vocabulary_hash=hash_vocabulary(["forklift"]),
    )

    assert selection.selected_backend == "ultralytics_yoloe"
    assert selection.artifact is None
    assert selection.fallback is True
    assert selection.fallback_reason == "artifact_vocabulary_mismatch"


def test_select_runtime_artifact_prefers_open_vocab_tensorrt_when_hash_matches() -> None:
    expected_hash = hash_vocabulary(["forklift"])
    artifact = _artifact(
        capability=DetectorCapability.OPEN_VOCAB,
        vocabulary_hash=expected_hash,
    )

    selection = select_runtime_artifact(
        model=_model(
            capability=DetectorCapability.OPEN_VOCAB,
            backend="ultralytics_yoloe",
            runtime_vocabulary=["forklift"],
        ),
        host_profile="linux-aarch64-nvidia-jetson",
        artifacts=[artifact],
        runtime_vocabulary_hash=expected_hash,
    )

    assert selection.selected_backend == "tensorrt_engine"
    assert selection.artifact == artifact
    assert selection.fallback is False
    assert selection.fallback_reason is None


def test_select_runtime_artifact_onnx_export_wins_when_open_vocab_hash_matches() -> None:
    expected_hash = hash_vocabulary(["forklift"])
    artifact = _artifact(
        kind=RuntimeArtifactKind.ONNX_EXPORT,
        capability=DetectorCapability.OPEN_VOCAB,
        vocabulary_hash=expected_hash,
    )

    selection = select_runtime_artifact(
        model=_model(
            capability=DetectorCapability.OPEN_VOCAB,
            backend="ultralytics_yoloe",
            runtime_vocabulary=["forklift"],
        ),
        host_profile="linux-aarch64-nvidia-jetson",
        artifacts=[artifact],
        runtime_vocabulary_hash=expected_hash,
    )

    assert selection.selected_backend == "onnxruntime"
    assert selection.artifact == artifact
    assert selection.fallback is False
    assert selection.fallback_reason is None


def test_select_runtime_artifact_onnx_first_profile_overrides_tensorrt() -> None:
    tensorrt = _artifact(kind=RuntimeArtifactKind.TENSORRT_ENGINE)
    onnx_export = _artifact(kind=RuntimeArtifactKind.ONNX_EXPORT)

    selection = select_runtime_artifact(
        model=_model(),
        host_profile="linux-aarch64-nvidia-jetson",
        artifacts=[tensorrt, onnx_export],
        runtime_vocabulary_hash=None,
        runtime_profile=SimpleNamespace(
            profile_id=uuid4(),
            profile_name="ONNX first",
            profile_hash="f" * 64,
            preferred_backend=None,
            artifact_preference="onnx_first",
            fallback_allowed=True,
        ),
    )

    assert selection.selected_backend == "onnxruntime"
    assert selection.artifact == onnx_export
    assert selection.profile_name == "ONNX first"
    assert selection.artifact_preference == "onnx_first"
    assert selection.fallback_allowed is True


def test_select_runtime_artifact_disallows_fallback_when_profile_requires_artifact() -> None:
    profile_id = uuid4()

    try:
        select_runtime_artifact(
            model=_model(),
            host_profile="linux-aarch64-nvidia-jetson",
            artifacts=[],
            runtime_vocabulary_hash=None,
            runtime_profile=SimpleNamespace(
                profile_id=profile_id,
                profile_name="TensorRT required",
                profile_hash="a" * 64,
                preferred_backend="tensorrt_engine",
                artifact_preference="tensorrt_first",
                fallback_allowed=False,
            ),
        )
    except RuntimeSelectionError as exc:
        assert "TensorRT required" in str(exc)
        assert "no_runtime_artifacts" in str(exc)
        assert exc.profile_id == profile_id
        assert exc.fallback_reason == "no_runtime_artifacts"
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected runtime selection to fail closed.")


def test_select_runtime_artifact_fallback_reason_is_explicit_without_candidates() -> None:
    selection = select_runtime_artifact(
        model=_model(),
        host_profile="linux-aarch64-nvidia-jetson",
        artifacts=[],
        runtime_vocabulary_hash=None,
    )

    assert selection.selected_backend == "onnxruntime"
    assert selection.artifact is None
    assert selection.fallback is True
    assert selection.fallback_reason == "no_runtime_artifacts"
