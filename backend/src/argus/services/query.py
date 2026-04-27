from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import CameraCommandPayload, QueryRequest, QueryResponse, TenantContext
from argus.core.events import NatsJetStreamClient
from argus.models.tables import AuditLog, Camera, Model, Site, Tenant


@dataclass(slots=True, frozen=True)
class QueryServiceResult:
    resolved_classes: list[str]
    provider: str
    model: str
    latency_ms: int


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
        allowed_classes = await self.inventory.allowed_classes_for_cameras(
            tenant_context=tenant_context,
            camera_ids=payload.camera_ids,
        )
        if not allowed_classes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching cameras or classes were found for this tenant.",
            )

        parser_result = await self.parser.resolve_classes(
            prompt=payload.prompt,
            allowed_classes=allowed_classes,
        )
        parser_metadata = cast(_ParserMetadata, parser_result)
        resolved_classes = _resolved_classes_from_parser_result(parser_result)
        result = QueryServiceResult(
            resolved_classes=resolved_classes,
            provider=parser_metadata.provider,
            model=parser_metadata.model,
            latency_ms=parser_metadata.latency_ms,
        )

        command = CameraCommandPayload(active_classes=result.resolved_classes)
        if self.events is None:
            raise RuntimeError("Query events publisher is not configured.")
        for camera_id in payload.camera_ids:
            await self.events.publish(f"cmd.camera.{camera_id}", command)

        await self.audit_logger.record_query(
            tenant_context=tenant_context,
            prompt=payload.prompt,
            resolved_classes=result.resolved_classes,
            provider=result.provider,
            model=result.model,
            latency_ms=result.latency_ms,
        )

        return QueryResponse(
            resolved_classes=result.resolved_classes,
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


def _resolved_classes_from_parser_result(parser_result: object) -> list[str]:
    if hasattr(parser_result, "classes"):
        classes_result = cast(_ClassesResult, parser_result)
        return list(classes_result.classes)
    if hasattr(parser_result, "resolved_classes"):
        resolved_result = cast(_ResolvedClassesResult, parser_result)
        return list(resolved_result.resolved_classes)
    raise AttributeError("Parser result must expose classes or resolved_classes.")


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
