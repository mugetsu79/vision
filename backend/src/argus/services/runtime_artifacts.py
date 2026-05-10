from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    RuntimeArtifactCreate,
    RuntimeArtifactResponse,
    RuntimeArtifactUpdate,
)
from argus.models.enums import (
    DetectorCapability,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
)
from argus.models.tables import Camera, Model, ModelRuntimeArtifact

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class RuntimeArtifactService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def list_for_model(self, model_id: UUID) -> list[RuntimeArtifactResponse]:
        async with self.session_factory() as session:
            model = await _load_model(session, model_id)
            statement = (
                select(ModelRuntimeArtifact)
                .where(ModelRuntimeArtifact.model_id == model_id)
                .order_by(
                    ModelRuntimeArtifact.target_profile,
                    ModelRuntimeArtifact.created_at.desc(),
                )
            )
            artifacts = (await session.execute(statement)).scalars().all()
        return [
            _artifact_to_response(artifact, model=model)
            for artifact in artifacts
            if artifact.model_id == model_id
        ]

    async def create_for_model(
        self,
        model_id: UUID,
        payload: RuntimeArtifactCreate,
    ) -> RuntimeArtifactResponse:
        async with self.session_factory() as session:
            model = await _load_model(session, model_id)
            _validate_artifact_matches_model(model, payload)
            if payload.scope is RuntimeArtifactScope.SCENE:
                camera = await _load_camera(session, payload.camera_id)
                _validate_camera_uses_model(camera, model_id)

            artifact = ModelRuntimeArtifact(
                model_id=model_id,
                camera_id=payload.camera_id,
                scope=payload.scope,
                kind=payload.kind,
                capability=payload.capability,
                runtime_backend=payload.runtime_backend,
                path=payload.path,
                target_profile=payload.target_profile,
                precision=payload.precision,
                input_shape=payload.input_shape,
                classes=payload.classes,
                vocabulary_hash=payload.vocabulary_hash,
                vocabulary_version=payload.vocabulary_version,
                source_model_sha256=payload.source_model_sha256,
                sha256=payload.sha256,
                size_bytes=payload.size_bytes,
                builder=payload.builder,
                runtime_versions=payload.runtime_versions,
                validation_status=payload.validation_status,
                validation_error=payload.validation_error,
                build_duration_seconds=payload.build_duration_seconds,
                validation_duration_seconds=payload.validation_duration_seconds,
                validated_at=payload.validated_at,
            )
            session.add(artifact)
            await session.commit()
            await session.refresh(artifact)
        return _artifact_to_response(artifact, model=model)

    async def update_artifact(
        self,
        model_id: UUID,
        artifact_id: UUID,
        payload: RuntimeArtifactUpdate,
    ) -> RuntimeArtifactResponse:
        async with self.session_factory() as session:
            model = await _load_model(session, model_id)
            artifact = await _load_artifact(session, model_id, artifact_id)
            for field_name, value in payload.model_dump(
                exclude_unset=True,
                mode="python",
            ).items():
                if value is None and field_name in {"validation_status", "sha256", "size_bytes"}:
                    continue
                setattr(artifact, field_name, value)
            await session.commit()
            await session.refresh(artifact)
        return _artifact_to_response(artifact, model=model)

    async def validate_artifact(self, model_id: UUID, artifact_id: UUID) -> RuntimeArtifactResponse:
        async with self.session_factory() as session:
            model = await _load_model(session, model_id)
            artifact = await _load_artifact(session, model_id, artifact_id)
            file_is_valid = await asyncio.to_thread(
                _artifact_file_matches_hash,
                artifact.path,
                artifact.sha256,
            )
            if file_is_valid:
                artifact.validation_status = RuntimeArtifactValidationStatus.VALID
                artifact.validation_error = None
            else:
                artifact.validation_status = RuntimeArtifactValidationStatus.UNVALIDATED
                artifact.validation_error = "Artifact file is not locally validated."
            await session.commit()
            await session.refresh(artifact)
        return _artifact_to_response(artifact, model=model)

    async def validation_candidates_for_camera(
        self,
        *,
        camera: Camera,
        model: Model,
    ) -> list[RuntimeArtifactResponse]:
        async with self.session_factory() as session:
            statement = select(ModelRuntimeArtifact).where(
                ModelRuntimeArtifact.model_id == model.id
            )
            artifacts = (await session.execute(statement)).scalars().all()

        responses: list[RuntimeArtifactResponse] = []
        for artifact in artifacts:
            if artifact.model_id != model.id:
                continue
            if artifact.validation_status is not RuntimeArtifactValidationStatus.VALID:
                continue
            if _artifact_is_stale(model, artifact):
                continue
            if artifact.scope is RuntimeArtifactScope.SCENE and artifact.camera_id != camera.id:
                continue
            responses.append(_artifact_to_response(artifact, model=model))
        return responses


async def _load_model(session: AsyncSession, model_id: UUID) -> Model:
    model = await session.get(Model, model_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found.")
    return model


async def _load_camera(session: AsyncSession, camera_id: UUID | None) -> Camera:
    if camera_id is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="camera_id is required for scene-scoped artifacts.",
        )
    camera = await session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    return camera


async def _load_artifact(
    session: AsyncSession,
    model_id: UUID,
    artifact_id: UUID,
) -> ModelRuntimeArtifact:
    artifact = await session.get(ModelRuntimeArtifact, artifact_id)
    if artifact is None or artifact.model_id != model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Runtime artifact not found.",
        )
    return artifact


def _artifact_to_response(
    artifact: ModelRuntimeArtifact,
    *,
    model: Model | None = None,
) -> RuntimeArtifactResponse:
    validation_status = artifact.validation_status
    if model is not None and _artifact_is_stale(model, artifact):
        validation_status = RuntimeArtifactValidationStatus.STALE
    return RuntimeArtifactResponse(
        id=artifact.id,
        model_id=artifact.model_id,
        camera_id=artifact.camera_id,
        scope=artifact.scope,
        kind=artifact.kind,
        capability=artifact.capability,
        runtime_backend=artifact.runtime_backend,
        path=artifact.path,
        target_profile=artifact.target_profile,
        precision=artifact.precision,
        input_shape=dict(artifact.input_shape),
        classes=list(artifact.classes),
        vocabulary_hash=artifact.vocabulary_hash,
        vocabulary_version=artifact.vocabulary_version,
        source_model_sha256=artifact.source_model_sha256,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
        builder=dict(artifact.builder),
        runtime_versions=dict(artifact.runtime_versions),
        validation_status=validation_status,
        validation_error=artifact.validation_error,
        build_duration_seconds=artifact.build_duration_seconds,
        validation_duration_seconds=artifact.validation_duration_seconds,
        validated_at=artifact.validated_at,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


def _validate_artifact_matches_model(model: Model, payload: RuntimeArtifactCreate) -> None:
    if payload.capability is not _model_capability(model):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Runtime artifact capability must match the model capability.",
        )
    if payload.source_model_sha256 != model.sha256:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Runtime artifact source_model_sha256 must match the model sha256.",
        )
    if (
        payload.capability is DetectorCapability.FIXED_VOCAB
        and model.classes
        and payload.classes != list(model.classes)
    ):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Runtime artifact classes must match the fixed-vocab model classes.",
        )


def _validate_camera_uses_model(camera: Camera, model_id: UUID) -> None:
    if camera.primary_model_id == model_id or camera.secondary_model_id == model_id:
        return
    raise HTTPException(
        status_code=HTTP_422_UNPROCESSABLE,
        detail="Scene-scoped runtime artifact camera does not use model.",
    )


def _artifact_is_stale(model: Model, artifact: ModelRuntimeArtifact) -> bool:
    return artifact.source_model_sha256 != model.sha256


def _model_capability(model: Model) -> DetectorCapability:
    capability = getattr(model, "capability", None)
    if isinstance(capability, DetectorCapability):
        return capability
    if capability is None:
        return DetectorCapability.FIXED_VOCAB
    return DetectorCapability(str(capability))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact_file:
        for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_file_matches_hash(path: str, expected_sha256: str) -> bool:
    artifact_path = Path(path)
    return artifact_path.exists() and _sha256_file(artifact_path) == expected_sha256
