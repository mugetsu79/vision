from __future__ import annotations

import inspect
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import CameraCommandPayload, QueryRequest, QueryResponse, TenantContext
from argus.compat import UTC
from argus.core.events import NatsJetStreamClient
from argus.models.enums import DetectorCapability, QueryResolutionMode, RuntimeVocabularySource
from argus.models.tables import AuditLog, Camera, CameraVocabularySnapshot, Model, Site, Tenant
from argus.vision.vocabulary import hash_vocabulary, normalize_vocabulary_terms


@dataclass(slots=True, frozen=True)
class QueryServiceResult:
    resolved_classes: list[str]
    provider: str
    model: str
    latency_ms: int


@dataclass(slots=True, frozen=True)
class QueryCameraDetectorContext:
    resolution_mode: QueryResolutionMode
    allowed_classes: list[str]
    runtime_vocabulary: list[str]
    runtime_vocabulary_version: int = 0
    max_runtime_terms: int | None = None


class QueryAuditLogger(Protocol):
    async def record_query(
        self,
        *,
        tenant_context: TenantContext,
        prompt: str,
        resolved_classes: list[str],
        provider: str,
        model: str,
        latency_ms: int,
    ) -> None: ...


class QueryQuotaEnforcer(Protocol):
    async def assert_query_allowed(self, *, tenant_context: TenantContext) -> None: ...


class CameraClassInventory(Protocol):
    async def allowed_classes_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> list[str]: ...

    async def detector_context_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> QueryCameraDetectorContext: ...

    async def record_runtime_vocabulary_snapshot(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
        terms: list[str],
        source: RuntimeVocabularySource,
        version: int,
        vocabulary_hash: str,
    ) -> None: ...


class QueryParser(Protocol):
    async def resolve_classes(
        self,
        *,
        prompt: str,
        allowed_classes: list[str],
    ) -> object: ...


class _ParserMetadata(Protocol):
    provider: str
    model: str
    latency_ms: int


class _ClassesResult(Protocol):
    classes: list[str]


class _ResolvedClassesResult(Protocol):
    resolved_classes: list[str]


class QueryService:
    def __init__(
        self,
        *,
        inventory: CameraClassInventory,
        parser: QueryParser,
        events: NatsJetStreamClient | None,
        audit_logger: QueryAuditLogger,
        quota_enforcer: QueryQuotaEnforcer | None = None,
    ) -> None:
        self.inventory = inventory
        self.parser = parser
        self.events = events
        self.audit_logger = audit_logger
        self.quota_enforcer = quota_enforcer or _AllowAllQuotaEnforcer()

    async def resolve_query(
        self,
        tenant_context: TenantContext,
        payload: QueryRequest,
    ) -> QueryResponse:
        await self.quota_enforcer.assert_query_allowed(tenant_context=tenant_context)
        detector_context = await _detector_context_for_inventory(
            self.inventory,
            tenant_context=tenant_context,
            camera_ids=payload.camera_ids,
        )
        terms_for_resolution = (
            detector_context.allowed_classes
            if detector_context.resolution_mode is QueryResolutionMode.FIXED_FILTER
            else detector_context.allowed_classes or detector_context.runtime_vocabulary
        )
        if not terms_for_resolution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching cameras or classes were found for this tenant.",
            )

        parser_result = await _resolve_classes_with_context(
            self.parser,
            prompt=payload.prompt,
            allowed_classes=terms_for_resolution,
            tenant_context=tenant_context,
            camera_ids=payload.camera_ids,
        )
        parser_metadata = cast(_ParserMetadata, parser_result)
        resolved_terms = _resolved_classes_from_parser_result(parser_result)
        if (
            detector_context.max_runtime_terms is not None
            and len(resolved_terms) > detector_context.max_runtime_terms
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "runtime_vocabulary exceeds "
                    f"max_runtime_terms={detector_context.max_runtime_terms}."
                ),
            )
        resolved_classes = (
            resolved_terms
            if detector_context.resolution_mode is QueryResolutionMode.FIXED_FILTER
            else []
        )
        resolved_vocabulary = (
            resolved_terms
            if detector_context.resolution_mode is QueryResolutionMode.OPEN_VOCAB
            else []
        )
        result = QueryServiceResult(
            resolved_classes=resolved_classes,
            provider=parser_metadata.provider,
            model=parser_metadata.model,
            latency_ms=parser_metadata.latency_ms,
        )

        if self.events is None:
            raise RuntimeError("Query events publisher is not configured.")
        for camera_id in payload.camera_ids:
            command = _camera_command_for_query(
                detector_context=detector_context,
                resolved_classes=result.resolved_classes,
                resolved_vocabulary=resolved_vocabulary,
            )
            await self.events.publish(f"cmd.camera.{camera_id}", command)
        await _record_runtime_vocabulary_snapshot_for_inventory(
            self.inventory,
            tenant_context=tenant_context,
            camera_ids=payload.camera_ids,
            detector_context=detector_context,
            resolved_vocabulary=resolved_vocabulary,
        )

        await self.audit_logger.record_query(
            tenant_context=tenant_context,
            prompt=payload.prompt,
            resolved_classes=result.resolved_classes,
            provider=result.provider,
            model=result.model,
            latency_ms=result.latency_ms,
        )

        return QueryResponse(
            resolution_mode=detector_context.resolution_mode,
            resolved_classes=result.resolved_classes,
            resolved_vocabulary=resolved_vocabulary,
            provider=result.provider,
            model=result.model,
            latency_ms=result.latency_ms,
            camera_ids=payload.camera_ids,
        )


class SQLCameraClassInventory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def allowed_classes_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> list[str]:
        async with self.session_factory() as session:
            statement = (
                select(Camera.id, Model.classes)
                .join(Site, Site.id == Camera.site_id)
                .join(Model, Model.id == Camera.primary_model_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .where(Camera.id.in_(camera_ids))
            )
            rows = (await session.execute(statement)).all()

        if len(rows) != len(set(camera_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more cameras were not found for this tenant.",
            )

        allowed: list[str] = []
        for _, classes in rows:
            for class_name in classes:
                if class_name not in allowed:
                    allowed.append(class_name)
        return allowed

    async def detector_context_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> QueryCameraDetectorContext:
        async with self.session_factory() as session:
            statement = (
                select(
                    Camera.id,
                    Camera.runtime_vocabulary,
                    Camera.runtime_vocabulary_version,
                    Model.classes,
                    Model.capability,
                    Model.capability_config,
                )
                .join(Site, Site.id == Camera.site_id)
                .join(Model, Model.id == Camera.primary_model_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .where(Camera.id.in_(camera_ids))
            )
            rows = (await session.execute(statement)).all()

        if len(rows) != len(set(camera_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more cameras were not found for this tenant.",
            )

        capabilities = {_coerce_detector_capability(row.capability) for row in rows}
        if len(capabilities) > 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected cameras have incompatible detector query semantics.",
            )
        capability = next(iter(capabilities), DetectorCapability.FIXED_VOCAB)
        if capability is DetectorCapability.FIXED_VOCAB:
            return QueryCameraDetectorContext(
                resolution_mode=QueryResolutionMode.FIXED_FILTER,
                allowed_classes=_dedupe_terms(
                    class_name for row in rows for class_name in row.classes
                ),
                runtime_vocabulary=[],
            )

        capability_configs = [dict(row.capability_config or {}) for row in rows]
        max_terms_values = [
            int(config["max_runtime_terms"])
            for config in capability_configs
            if config.get("max_runtime_terms") is not None
        ]
        return QueryCameraDetectorContext(
            resolution_mode=QueryResolutionMode.OPEN_VOCAB,
            allowed_classes=_dedupe_terms(
                term
                for row in rows
                for term in ((row.runtime_vocabulary or []) or row.classes)
            ),
            runtime_vocabulary=_dedupe_terms(
                term for row in rows for term in (row.runtime_vocabulary or [])
            ),
            runtime_vocabulary_version=max(
                (int(row.runtime_vocabulary_version or 0) for row in rows),
                default=0,
            ),
            max_runtime_terms=min(max_terms_values) if max_terms_values else None,
        )

    async def record_runtime_vocabulary_snapshot(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
        terms: list[str],
        source: RuntimeVocabularySource,
        version: int,
        vocabulary_hash: str,
    ) -> None:
        normalized_terms = normalize_vocabulary_terms(terms)
        now = datetime.now(tz=UTC)
        async with self.session_factory() as session:
            statement = (
                select(Camera)
                .join(Site, Site.id == Camera.site_id)
                .join(Model, Model.id == Camera.primary_model_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .where(Camera.id.in_(camera_ids))
                .where(Model.capability == DetectorCapability.OPEN_VOCAB)
            )
            cameras = list((await session.execute(statement)).scalars().all())
            if len(cameras) != len(set(camera_ids)):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more cameras were not found for this tenant.",
                )
            for camera in cameras:
                camera.runtime_vocabulary = list(normalized_terms)
                camera.runtime_vocabulary_source = source
                camera.runtime_vocabulary_version = version
                camera.runtime_vocabulary_updated_at = now
                session.add(
                    CameraVocabularySnapshot(
                        camera_id=camera.id,
                        version=version,
                        vocabulary_hash=vocabulary_hash,
                        source=source,
                        terms=list(normalized_terms),
                    )
                )
            await session.commit()


async def _detector_context_for_inventory(
    inventory: CameraClassInventory,
    *,
    tenant_context: TenantContext,
    camera_ids: list[UUID],
) -> QueryCameraDetectorContext:
    detector_context = getattr(inventory, "detector_context_for_cameras", None)
    if callable(detector_context):
        return cast(
            QueryCameraDetectorContext,
            await detector_context(tenant_context=tenant_context, camera_ids=camera_ids),
        )
    allowed_classes = await inventory.allowed_classes_for_cameras(
        tenant_context=tenant_context,
        camera_ids=camera_ids,
    )
    return QueryCameraDetectorContext(
        resolution_mode=QueryResolutionMode.FIXED_FILTER,
        allowed_classes=allowed_classes,
        runtime_vocabulary=[],
    )


async def _record_runtime_vocabulary_snapshot_for_inventory(
    inventory: CameraClassInventory,
    *,
    tenant_context: TenantContext,
    camera_ids: list[UUID],
    detector_context: QueryCameraDetectorContext,
    resolved_vocabulary: list[str],
) -> None:
    if detector_context.resolution_mode is not QueryResolutionMode.OPEN_VOCAB:
        return
    recorder = getattr(inventory, "record_runtime_vocabulary_snapshot", None)
    if not callable(recorder):
        return
    version = detector_context.runtime_vocabulary_version + 1
    normalized_terms = normalize_vocabulary_terms(resolved_vocabulary)
    await recorder(
        tenant_context=tenant_context,
        camera_ids=camera_ids,
        terms=normalized_terms,
        source=RuntimeVocabularySource.QUERY,
        version=version,
        vocabulary_hash=hash_vocabulary(normalized_terms),
    )


def _camera_command_for_query(
    *,
    detector_context: QueryCameraDetectorContext,
    resolved_classes: list[str],
    resolved_vocabulary: list[str],
) -> CameraCommandPayload:
    if detector_context.resolution_mode is QueryResolutionMode.OPEN_VOCAB:
        return CameraCommandPayload(
            active_classes=None,
            runtime_vocabulary=list(resolved_vocabulary),
            runtime_vocabulary_source=RuntimeVocabularySource.QUERY,
            runtime_vocabulary_version=detector_context.runtime_vocabulary_version + 1,
        )
    return CameraCommandPayload(active_classes=list(resolved_classes))


def _coerce_detector_capability(value: object) -> DetectorCapability:
    if value is None:
        return DetectorCapability.FIXED_VOCAB
    if isinstance(value, DetectorCapability):
        return value
    return DetectorCapability(str(value))


def _dedupe_terms(terms: Iterable[object]) -> list[str]:
    deduped: list[str] = []
    for term in terms:
        value = str(term).strip()
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _resolved_classes_from_parser_result(parser_result: object) -> list[str]:
    if hasattr(parser_result, "classes"):
        classes_result = cast(_ClassesResult, parser_result)
        return list(classes_result.classes)
    if hasattr(parser_result, "resolved_classes"):
        resolved_result = cast(_ResolvedClassesResult, parser_result)
        return list(resolved_result.resolved_classes)
    raise AttributeError("Parser result must expose classes or resolved_classes.")


async def _resolve_classes_with_context(
    parser: QueryParser,
    *,
    prompt: str,
    allowed_classes: list[str],
    tenant_context: TenantContext,
    camera_ids: list[UUID],
) -> object:
    method = parser.resolve_classes
    parameters = inspect.signature(method).parameters
    supports_context = (
        "tenant_context" in parameters
        or any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values())
    )
    if supports_context:
        return await method(
            prompt=prompt,
            allowed_classes=allowed_classes,
            tenant_context=tenant_context,
            camera_ids=camera_ids,
        )
    return await method(prompt=prompt, allowed_classes=allowed_classes)


class _AllowAllQuotaEnforcer:
    async def assert_query_allowed(self, *, tenant_context: TenantContext) -> None:
        return None


class SQLQueryQuotaEnforcer:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def assert_query_allowed(self, *, tenant_context: TenantContext) -> None:
        window_start = datetime.now(tz=UTC) - timedelta(minutes=1)
        async with self.session_factory() as session:
            limit_statement = select(Tenant.query_requests_per_minute).where(
                Tenant.id == tenant_context.tenant_id
            )
            limit = (await session.execute(limit_statement)).scalar_one_or_none()
            if limit is None or int(limit) <= 0:
                return

            count_statement = select(func.count()).select_from(AuditLog).where(
                AuditLog.tenant_id == tenant_context.tenant_id,
                AuditLog.action == "query.resolve",
                AuditLog.ts >= window_start,
            )
            count = int((await session.execute(count_statement)).scalar_one())

        if count >= int(limit):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Tenant query rate limit exceeded.",
            )
