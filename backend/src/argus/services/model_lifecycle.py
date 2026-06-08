from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import UUID, uuid4

import anyio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import ModelCapabilityConfig, ModelImportJobResponse, ModelImportRequest
from argus.models.enums import (
    DetectorCapability,
    ModelFormat,
    ModelImportSource,
    ModelLifecycleJobStatus,
    ModelTask,
)
from argus.models.tables import Model, ModelImportJob
from argus.services.model_catalog import ModelCatalogEntry, get_model_catalog_entry


class ModelLifecycleService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        model_store_path: Path | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.model_store_path = model_store_path

    async def import_model_from_request(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        payload: ModelImportRequest,
    ) -> ModelImportJobResponse:
        if payload.source is ModelImportSource.URL:
            return await self._queue_url_import(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                payload=payload,
                catalog_id=None,
            )
        if payload.source is ModelImportSource.MASTER_PATH:
            return await self._register_file_import(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=payload.source,
                source_uri=payload.source_uri or "",
                target_path=payload.source_uri or "",
                expected_sha256=payload.expected_sha256,
                name=payload.name,
                version=payload.version,
                task=payload.task,
                format=payload.format,
                capability=payload.capability,
                capability_config=payload.capability_config,
                input_shape=payload.input_shape,
                classes=payload.classes,
                license=payload.license,
                catalog_id=None,
            )
        return await self._failed_import_job(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            source=payload.source,
            source_uri=payload.source_uri,
            target_path=payload.source_uri or "",
            expected_sha256=payload.expected_sha256,
            error=f"Model import source {payload.source.value!r} is not supported yet.",
            catalog_id=None,
        )

    async def register_catalog_entry(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        catalog_id: str,
    ) -> ModelImportJobResponse:
        entry = _find_catalog_entry(catalog_id)
        capability_config = entry.capability_config.model_copy()
        return await self._register_file_import(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            source=ModelImportSource.CATALOG,
            source_uri=entry.path_hint,
            target_path=entry.path_hint,
            expected_sha256=None,
            name=entry.name,
            version=entry.version,
            task=entry.task,
            format=entry.format,
            capability=entry.capability,
            capability_config=capability_config,
            input_shape=entry.input_shape,
            classes=list(entry.classes),
            license=entry.license,
            catalog_id=entry.id,
        )

    async def queue_catalog_download(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        catalog_id: str,
    ) -> ModelImportJobResponse:
        entry = _find_catalog_entry(catalog_id)
        source_url = entry.capability_config.source_url
        expected_sha256 = entry.capability_config.source_sha256
        if source_url is None or expected_sha256 is None:
            raise ValueError(
                "Model artifact is expected to be bundled or mounted at "
                f"{entry.path_hint}; no trusted download source is configured."
            )
        payload = ModelImportRequest(
            source=ModelImportSource.URL,
            source_uri=source_url,
            expected_sha256=expected_sha256,
            name=entry.name,
            version=entry.version,
            task=entry.task,
            format=entry.format,
            capability=entry.capability,
            capability_config=entry.capability_config,
            input_shape=entry.input_shape,
            classes=list(entry.classes),
            license=entry.license,
        )
        return await self._queue_url_import(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            payload=payload,
            catalog_id=entry.id,
        )

    async def list_import_jobs(self, tenant_id: UUID) -> list[ModelImportJobResponse]:
        async with self.session_factory() as session:
            statement = (
                select(ModelImportJob)
                .where(ModelImportJob.tenant_id == tenant_id)
                .order_by(ModelImportJob.created_at.desc())
            )
            jobs = (await session.execute(statement)).scalars().all()
        return [_model_to_import_job_response(job) for job in jobs]

    async def _queue_url_import(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        payload: ModelImportRequest,
        catalog_id: str | None,
    ) -> ModelImportJobResponse:
        try:
            target_path = _target_path_for_url(payload.source_uri or "", self.model_store_path)
        except ValueError as exc:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=ModelImportSource.URL,
                source_uri=payload.source_uri,
                target_path=str(self.model_store_path or ""),
                expected_sha256=payload.expected_sha256,
                error=f"Unsafe model URL filename: {exc}",
                catalog_id=catalog_id,
            )

        async with self.session_factory() as session:
            job = ModelImportJob(
                tenant_id=tenant_id,
                catalog_id=catalog_id,
                source=ModelImportSource.URL,
                status=ModelLifecycleJobStatus.QUEUED,
                actor_subject=actor_subject,
                source_uri=payload.source_uri,
                target_path=target_path,
                expected_sha256=payload.expected_sha256,
                progress={},
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return _model_to_import_job_response(job)

    async def _register_file_import(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        source: ModelImportSource,
        source_uri: str,
        target_path: str,
        expected_sha256: str | None,
        name: str,
        version: str,
        task: ModelTask,
        format: ModelFormat,
        capability: DetectorCapability,
        capability_config: ModelCapabilityConfig,
        input_shape: dict[str, int],
        classes: list[str],
        license: str | None,
        catalog_id: str | None,
    ) -> ModelImportJobResponse:
        if catalog_id is not None:
            existing_response = await self._register_existing_catalog_model(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                expected_sha256=expected_sha256,
                catalog_id=catalog_id,
            )
            if existing_response is not None:
                return existing_response

        path = Path(source_uri)
        try:
            source_exists = await anyio.to_thread.run_sync(path.exists)
            source_is_file = await anyio.to_thread.run_sync(path.is_file)
        except OSError as exc:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                error=f"Could not inspect model artifact: {exc}",
                catalog_id=catalog_id,
            )
        if not source_exists:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                error=f"Model artifact does not exist: {source_uri}",
                catalog_id=catalog_id,
            )
        if not source_is_file:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                error=f"Model artifact must be a regular file: {source_uri}",
                catalog_id=catalog_id,
            )

        try:
            observed_sha256 = await anyio.to_thread.run_sync(_hash_file, path)
            size_bytes = (await anyio.to_thread.run_sync(path.stat)).st_size
        except OSError as exc:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                error=f"Could not read model artifact: {exc}",
                catalog_id=catalog_id,
            )
        if expected_sha256 is not None and observed_sha256 != expected_sha256:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                size_bytes=size_bytes,
                error=(
                    "Model artifact sha256 mismatch: "
                    f"expected {expected_sha256}, got {observed_sha256}."
                ),
                catalog_id=catalog_id,
            )

        model_id = uuid4()
        config_data = capability_config.model_dump(mode="python")
        if catalog_id is not None:
            config_data["catalog_id"] = catalog_id
        try:
            resolved_classes = _resolve_model_classes_for_import(
                capability=capability,
                path=target_path,
                format=format,
                classes=list(classes),
                capability_config=config_data,
            )
        except HTTPException as exc:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                size_bytes=size_bytes,
                error=str(exc.detail),
                catalog_id=catalog_id,
            )
        async with self.session_factory() as session:
            model = Model(
                id=model_id,
                name=name,
                version=version,
                task=task,
                path=target_path,
                format=format,
                capability=capability,
                capability_config=config_data,
                classes=resolved_classes,
                input_shape=dict(input_shape),
                sha256=observed_sha256,
                size_bytes=size_bytes,
                license=license,
            )
            job = ModelImportJob(
                tenant_id=tenant_id,
                catalog_id=catalog_id,
                source=source,
                status=ModelLifecycleJobStatus.SUCCEEDED,
                actor_subject=actor_subject,
                model_id=model_id,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                size_bytes=size_bytes,
                progress={},
            )
            session.add(model)
            session.add(job)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                if catalog_id is None:
                    raise
                existing_response = await self._register_existing_catalog_model(
                    tenant_id=tenant_id,
                    actor_subject=actor_subject,
                    source=source,
                    source_uri=source_uri,
                    expected_sha256=expected_sha256,
                    catalog_id=catalog_id,
                )
                if existing_response is None:
                    raise
                return existing_response
            await session.refresh(job)
        return _model_to_import_job_response(job)

    async def _register_existing_catalog_model(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        source: ModelImportSource,
        source_uri: str,
        expected_sha256: str | None,
        catalog_id: str,
    ) -> ModelImportJobResponse | None:
        async with self.session_factory() as session:
            existing_model = await _find_existing_catalog_model(session, catalog_id)
            if existing_model is None:
                return None
            job = ModelImportJob(
                tenant_id=tenant_id,
                catalog_id=catalog_id,
                source=source,
                status=ModelLifecycleJobStatus.SUCCEEDED,
                actor_subject=actor_subject,
                model_id=existing_model.id,
                source_uri=source_uri,
                target_path=existing_model.path,
                expected_sha256=expected_sha256,
                observed_sha256=existing_model.sha256,
                size_bytes=existing_model.size_bytes,
                progress={},
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return _model_to_import_job_response(job)

    async def _failed_import_job(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        source: ModelImportSource,
        source_uri: str | None,
        target_path: str,
        expected_sha256: str | None,
        error: str,
        catalog_id: str | None,
        observed_sha256: str | None = None,
        size_bytes: int | None = None,
    ) -> ModelImportJobResponse:
        async with self.session_factory() as session:
            job = ModelImportJob(
                tenant_id=tenant_id,
                catalog_id=catalog_id,
                source=source,
                status=ModelLifecycleJobStatus.FAILED,
                actor_subject=actor_subject,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                size_bytes=size_bytes,
                progress={},
                error=error,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return _model_to_import_job_response(job)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _model_to_import_job_response(job: ModelImportJob) -> ModelImportJobResponse:
    return ModelImportJobResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        catalog_id=job.catalog_id,
        source=job.source,
        status=job.status,
        actor_subject=job.actor_subject,
        model_id=job.model_id,
        source_uri=job.source_uri,
        target_path=job.target_path,
        expected_sha256=job.expected_sha256,
        observed_sha256=job.observed_sha256,
        size_bytes=job.size_bytes,
        progress=dict(job.progress or {}),
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _find_catalog_entry(catalog_id: str) -> ModelCatalogEntry:
    entry = get_model_catalog_entry(catalog_id)
    if entry is not None:
        return entry
    raise ValueError(f"Model catalog entry not found: {catalog_id}")


async def _find_existing_catalog_model(
    session: AsyncSession,
    catalog_id: str,
) -> Model | None:
    statement = select(Model).where(Model.capability_config["catalog_id"].astext == catalog_id)
    result = await session.execute(statement)
    return result.scalars().first()


def _resolve_model_classes_for_import(
    *,
    capability: DetectorCapability,
    path: str,
    format: ModelFormat,
    classes: list[str] | None,
    capability_config: dict[str, object],
) -> list[str]:
    from argus.services import app as app_services

    return app_services._resolve_model_classes_for_capability(
        capability=capability,
        path=path,
        format=format,
        classes=classes,
        capability_config=capability_config,
    )


def _target_path_for_url(source_uri: str, model_store_path: Path | None) -> str:
    filename = _safe_url_target_filename(source_uri)
    if model_store_path is None:
        return source_uri
    return str(model_store_path / filename)


def _safe_url_target_filename(source_uri: str) -> str:
    raw_path = urlsplit(source_uri).path
    raw_basename = raw_path.rsplit("/", 1)[-1]
    filename = unquote(raw_basename)
    if filename in {"", ".", ".."} or "/" in filename or "\\" in filename:
        raise ValueError(f"{filename!r} is not a safe filename.")
    return filename
