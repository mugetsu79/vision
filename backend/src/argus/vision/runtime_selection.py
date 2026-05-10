from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from argus.inference.engine import ModelSettings, RuntimeArtifactSettings
from argus.models.enums import DetectorCapability, RuntimeArtifactKind


@dataclass(frozen=True, slots=True)
class RuntimeSelection:
    selected_backend: str
    artifact: RuntimeArtifactSettings | None
    fallback: bool
    fallback_reason: str | None


def select_runtime_artifact(
    *,
    model: ModelSettings,
    host_profile: str,
    artifacts: Iterable[RuntimeArtifactSettings],
    runtime_vocabulary_hash: str | None,
) -> RuntimeSelection:
    candidates = list(artifacts)
    canonical_backend = _canonical_model_backend(model)
    if not candidates:
        return RuntimeSelection(
            selected_backend=canonical_backend,
            artifact=None,
            fallback=True,
            fallback_reason="no_runtime_artifacts",
        )

    matching_target = [
        artifact for artifact in candidates if artifact.target_profile == host_profile
    ]
    if not matching_target:
        return RuntimeSelection(
            selected_backend=canonical_backend,
            artifact=None,
            fallback=True,
            fallback_reason="artifact_target_mismatch",
        )

    matching_vocabulary = [
        artifact
        for artifact in matching_target
        if _artifact_matches_vocabulary(
            model=model,
            artifact=artifact,
            runtime_vocabulary_hash=runtime_vocabulary_hash,
        )
    ]
    if not matching_vocabulary:
        return RuntimeSelection(
            selected_backend=canonical_backend,
            artifact=None,
            fallback=True,
            fallback_reason="artifact_vocabulary_mismatch",
        )

    tensorrt = _first_kind(matching_vocabulary, RuntimeArtifactKind.TENSORRT_ENGINE)
    if tensorrt is not None:
        return RuntimeSelection(
            selected_backend=tensorrt.runtime_backend,
            artifact=tensorrt,
            fallback=False,
            fallback_reason=None,
        )

    onnx_export = _first_kind(matching_vocabulary, RuntimeArtifactKind.ONNX_EXPORT)
    if onnx_export is not None:
        return RuntimeSelection(
            selected_backend=onnx_export.runtime_backend,
            artifact=onnx_export,
            fallback=False,
            fallback_reason=None,
        )

    return RuntimeSelection(
        selected_backend=canonical_backend,
        artifact=None,
        fallback=True,
        fallback_reason="no_supported_runtime_artifact",
    )


def _artifact_matches_vocabulary(
    *,
    model: ModelSettings,
    artifact: RuntimeArtifactSettings,
    runtime_vocabulary_hash: str | None,
) -> bool:
    if model.capability is not DetectorCapability.OPEN_VOCAB:
        return True
    return bool(artifact.vocabulary_hash) and artifact.vocabulary_hash == runtime_vocabulary_hash


def _first_kind(
    artifacts: list[RuntimeArtifactSettings],
    kind: RuntimeArtifactKind,
) -> RuntimeArtifactSettings | None:
    return next((artifact for artifact in artifacts if artifact.kind is kind), None)


def _canonical_model_backend(model: ModelSettings) -> str:
    backend = model.capability_config.get("runtime_backend")
    if backend is not None:
        return str(backend)
    return "onnxruntime"
