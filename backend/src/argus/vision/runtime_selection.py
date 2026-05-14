from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from uuid import UUID

from argus.models.enums import DetectorCapability, RuntimeArtifactKind


class RuntimeArtifactCandidate(Protocol):
    id: UUID
    kind: RuntimeArtifactKind
    capability: DetectorCapability
    runtime_backend: str
    target_profile: str
    vocabulary_hash: str | None


class RuntimeModelCandidate(Protocol):
    capability: DetectorCapability
    capability_config: dict[str, Any]


RuntimeArtifactPreference = Literal["tensorrt_first", "onnx_first", "dynamic_first"]


class RuntimeSelectionPolicy(Protocol):
    @property
    def profile_id(self) -> UUID | None: ...

    @property
    def profile_name(self) -> str | None: ...

    @property
    def profile_hash(self) -> str | None: ...

    @property
    def preferred_backend(self) -> str | None: ...

    @property
    def artifact_preference(self) -> RuntimeArtifactPreference: ...

    @property
    def fallback_allowed(self) -> bool: ...


class RuntimeSelectionError(RuntimeError):
    def __init__(
        self,
        *,
        profile_id: UUID | None,
        profile_name: str | None,
        profile_hash: str | None,
        fallback_reason: str,
    ) -> None:
        label = profile_name or (str(profile_id) if profile_id is not None else "runtime profile")
        super().__init__(
            f"Runtime selection profile {label} disallows fallback: {fallback_reason}"
        )
        self.profile_id = profile_id
        self.profile_name = profile_name
        self.profile_hash = profile_hash
        self.fallback_reason = fallback_reason


@dataclass(frozen=True, slots=True)
class RuntimeSelection:
    selected_backend: str
    artifact: RuntimeArtifactCandidate | None
    fallback: bool
    fallback_reason: str | None
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_hash: str | None = None
    artifact_preference: RuntimeArtifactPreference = "tensorrt_first"
    fallback_allowed: bool = True


def select_runtime_artifact(
    *,
    model: RuntimeModelCandidate,
    host_profile: str,
    artifacts: Iterable[RuntimeArtifactCandidate],
    runtime_vocabulary_hash: str | None,
    runtime_profile: RuntimeSelectionPolicy | None = None,
) -> RuntimeSelection:
    candidates = list(artifacts)
    canonical_backend = _fallback_backend(model, runtime_profile)
    artifact_preference = _artifact_preference(runtime_profile)
    fallback_allowed = _fallback_allowed(runtime_profile)
    if not candidates:
        return _fallback_selection(
            selected_backend=canonical_backend,
            fallback_reason="no_runtime_artifacts",
            runtime_profile=runtime_profile,
            artifact_preference=artifact_preference,
            fallback_allowed=fallback_allowed,
        )

    matching_target = [
        artifact for artifact in candidates if artifact.target_profile == host_profile
    ]
    if not matching_target:
        return _fallback_selection(
            selected_backend=canonical_backend,
            fallback_reason="artifact_target_mismatch",
            runtime_profile=runtime_profile,
            artifact_preference=artifact_preference,
            fallback_allowed=fallback_allowed,
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
        return _fallback_selection(
            selected_backend=canonical_backend,
            fallback_reason="artifact_vocabulary_mismatch",
            runtime_profile=runtime_profile,
            artifact_preference=artifact_preference,
            fallback_allowed=fallback_allowed,
        )

    if artifact_preference == "dynamic_first":
        return _fallback_selection(
            selected_backend=canonical_backend,
            fallback_reason="dynamic_preferred",
            runtime_profile=runtime_profile,
            artifact_preference=artifact_preference,
            fallback_allowed=fallback_allowed,
        )

    for kind in _preferred_artifact_kinds(artifact_preference):
        artifact = _first_kind(matching_vocabulary, kind)
        if artifact is not None:
            return RuntimeSelection(
                selected_backend=artifact.runtime_backend,
                artifact=artifact,
                fallback=False,
                fallback_reason=None,
                profile_id=_profile_id(runtime_profile),
                profile_name=_profile_name(runtime_profile),
                profile_hash=_profile_hash(runtime_profile),
                artifact_preference=artifact_preference,
                fallback_allowed=fallback_allowed,
            )

    return _fallback_selection(
        selected_backend=canonical_backend,
        fallback_reason="no_supported_runtime_artifact",
        runtime_profile=runtime_profile,
        artifact_preference=artifact_preference,
        fallback_allowed=fallback_allowed,
    )


def _fallback_selection(
    *,
    selected_backend: str,
    fallback_reason: str,
    runtime_profile: RuntimeSelectionPolicy | None,
    artifact_preference: RuntimeArtifactPreference,
    fallback_allowed: bool,
) -> RuntimeSelection:
    profile_id = _profile_id(runtime_profile)
    profile_name = _profile_name(runtime_profile)
    profile_hash = _profile_hash(runtime_profile)
    if not fallback_allowed:
        raise RuntimeSelectionError(
            profile_id=profile_id,
            profile_name=profile_name,
            profile_hash=profile_hash,
            fallback_reason=fallback_reason,
        )
    return RuntimeSelection(
        selected_backend=selected_backend,
        artifact=None,
        fallback=True,
        fallback_reason=fallback_reason,
        profile_id=profile_id,
        profile_name=profile_name,
        profile_hash=profile_hash,
        artifact_preference=artifact_preference,
        fallback_allowed=fallback_allowed,
    )


def _preferred_artifact_kinds(
    artifact_preference: RuntimeArtifactPreference,
) -> tuple[RuntimeArtifactKind, RuntimeArtifactKind]:
    if artifact_preference == "onnx_first":
        return (RuntimeArtifactKind.ONNX_EXPORT, RuntimeArtifactKind.TENSORRT_ENGINE)
    return (RuntimeArtifactKind.TENSORRT_ENGINE, RuntimeArtifactKind.ONNX_EXPORT)


def _artifact_matches_vocabulary(
    *,
    model: RuntimeModelCandidate,
    artifact: RuntimeArtifactCandidate,
    runtime_vocabulary_hash: str | None,
) -> bool:
    if model.capability is not DetectorCapability.OPEN_VOCAB:
        return True
    return bool(artifact.vocabulary_hash) and artifact.vocabulary_hash == runtime_vocabulary_hash


def _first_kind(
    artifacts: list[RuntimeArtifactCandidate],
    kind: RuntimeArtifactKind,
) -> RuntimeArtifactCandidate | None:
    return next((artifact for artifact in artifacts if artifact.kind is kind), None)


def _fallback_backend(
    model: RuntimeModelCandidate,
    runtime_profile: RuntimeSelectionPolicy | None,
) -> str:
    preferred_backend = getattr(runtime_profile, "preferred_backend", None)
    if preferred_backend is not None:
        return str(preferred_backend)
    return _canonical_model_backend(model)


def _canonical_model_backend(model: RuntimeModelCandidate) -> str:
    backend = model.capability_config.get("runtime_backend")
    if backend is not None:
        return str(backend)
    return "onnxruntime"


def _artifact_preference(
    runtime_profile: RuntimeSelectionPolicy | None,
) -> RuntimeArtifactPreference:
    preference = getattr(runtime_profile, "artifact_preference", "tensorrt_first")
    if preference == "onnx_first":
        return "onnx_first"
    if preference == "dynamic_first":
        return "dynamic_first"
    return "tensorrt_first"


def _fallback_allowed(runtime_profile: RuntimeSelectionPolicy | None) -> bool:
    return bool(getattr(runtime_profile, "fallback_allowed", True))


def _profile_id(runtime_profile: RuntimeSelectionPolicy | None) -> UUID | None:
    value = getattr(runtime_profile, "profile_id", None)
    return value if isinstance(value, UUID) else None


def _profile_name(runtime_profile: RuntimeSelectionPolicy | None) -> str | None:
    value = getattr(runtime_profile, "profile_name", None)
    return str(value) if value else None


def _profile_hash(runtime_profile: RuntimeSelectionPolicy | None) -> str | None:
    value = getattr(runtime_profile, "profile_hash", None)
    return str(value) if value else None
