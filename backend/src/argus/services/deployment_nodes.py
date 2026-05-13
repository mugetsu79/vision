from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    DeploymentNodeResponse,
    SupervisorServiceReportCreate,
    SupervisorServiceReportResponse,
)
from argus.compat import UTC
from argus.models.enums import DeploymentInstallStatus
from argus.models.tables import DeploymentNode, SupervisorServiceStatusReport

SERVICE_REPORT_STALE_AFTER = timedelta(minutes=5)
_SECRET_KEY_PARTS = (
    "api_key",
    "authorization",
    "bearer",
    "credential",
    "jwt",
    "key",
    "pairing",
    "password",
    "secret",
    "token",
)


class DeploymentNodeService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.now_factory = now_factory or (lambda: datetime.now(tz=UTC))

    async def list_nodes(self, *, tenant_id: UUID) -> list[DeploymentNodeResponse]:
        now = self.now_factory()
        async with self.session_factory() as session:
            statement = (
                select(DeploymentNode)
                .where(DeploymentNode.tenant_id == tenant_id)
                .order_by(DeploymentNode.node_kind.asc(), DeploymentNode.hostname.asc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        return [
            deployment_node_response(row, now=now)
            for row in rows
            if isinstance(row, DeploymentNode)
        ]

    async def record_service_report(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        payload: SupervisorServiceReportCreate,
    ) -> SupervisorServiceReportResponse:
        now = self.now_factory()
        diagnostics = redact_diagnostics(payload.diagnostics)
        install_status = _fresh_install_status(payload.install_status, payload.heartbeat_at, now)

        async with self.session_factory() as session:
            await self._validate_edge_node_scope(
                session=session,
                tenant_id=tenant_id,
                edge_node_id=payload.edge_node_id,
            )
            node = await self._load_node_by_supervisor(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
            )
            if node is None:
                node = DeploymentNode(
                    tenant_id=tenant_id,
                    edge_node_id=payload.edge_node_id,
                    supervisor_id=supervisor_id,
                    node_kind=payload.node_kind,
                    hostname=payload.hostname,
                    install_status=install_status,
                    credential_status=payload.credential_status,
                    service_manager=payload.service_manager,
                    service_status=payload.service_status,
                    version=payload.version,
                    os_name=payload.os_name,
                    host_profile=payload.host_profile,
                    last_service_reported_at=payload.heartbeat_at,
                    diagnostics=diagnostics,
                )
                _ensure_identity_and_timestamps(node, now=now)
                session.add(node)
                await _flush_if_available(session)
            else:
                node.edge_node_id = payload.edge_node_id
                node.node_kind = payload.node_kind
                node.hostname = payload.hostname
                node.install_status = install_status
                node.credential_status = payload.credential_status
                node.service_manager = payload.service_manager
                node.service_status = payload.service_status
                node.version = payload.version
                node.os_name = payload.os_name
                node.host_profile = payload.host_profile
                node.last_service_reported_at = payload.heartbeat_at
                node.diagnostics = diagnostics
                node.updated_at = now

            report = SupervisorServiceStatusReport(
                tenant_id=tenant_id,
                deployment_node_id=node.id,
                edge_node_id=payload.edge_node_id,
                supervisor_id=supervisor_id,
                node_kind=payload.node_kind,
                hostname=payload.hostname,
                service_manager=payload.service_manager,
                service_status=payload.service_status,
                install_status=install_status,
                credential_status=payload.credential_status,
                version=payload.version,
                os_name=payload.os_name,
                host_profile=payload.host_profile,
                heartbeat_at=payload.heartbeat_at,
                diagnostics=diagnostics,
            )
            _ensure_identity_and_timestamps(report, now=now)
            session.add(report)
            await session.commit()
            await session.refresh(node)
            await session.refresh(report)

        node_response = deployment_node_response(node, now=now)
        return supervisor_service_report_response(report, node=node_response)

    async def _load_node_by_supervisor(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        supervisor_id: str,
    ) -> DeploymentNode | None:
        statement = select(DeploymentNode).where(
            DeploymentNode.tenant_id == tenant_id,
            DeploymentNode.supervisor_id == supervisor_id,
        )
        row = (await session.execute(statement)).scalar_one_or_none()
        return row if isinstance(row, DeploymentNode) else None

    async def _validate_edge_node_scope(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        edge_node_id: UUID | None,
    ) -> None:
        if edge_node_id is None:
            return
        from argus.models.tables import EdgeNode, Site

        statement = (
            select(EdgeNode)
            .join(Site, Site.id == EdgeNode.site_id)
            .where(EdgeNode.id == edge_node_id, Site.tenant_id == tenant_id)
        )
        row = (await session.execute(statement)).scalar_one_or_none()
        if not isinstance(row, EdgeNode):
            msg = "Edge node is not in tenant scope."
            raise ValueError(msg)


def deployment_node_response(
    row: DeploymentNode,
    *,
    now: datetime,
) -> DeploymentNodeResponse:
    return DeploymentNodeResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        node_kind=row.node_kind,
        edge_node_id=row.edge_node_id,
        supervisor_id=row.supervisor_id,
        hostname=row.hostname,
        install_status=_fresh_install_status(
            row.install_status,
            row.last_service_reported_at,
            now,
        ),
        credential_status=row.credential_status,
        service_manager=row.service_manager,
        service_status=row.service_status,
        version=row.version,
        os_name=row.os_name,
        host_profile=row.host_profile,
        last_service_reported_at=row.last_service_reported_at,
        diagnostics=dict(row.diagnostics),
        created_at=_coerce_datetime(row.created_at, fallback=now),
        updated_at=_coerce_datetime(row.updated_at, fallback=now),
    )


def supervisor_service_report_response(
    row: SupervisorServiceStatusReport,
    *,
    node: DeploymentNodeResponse,
) -> SupervisorServiceReportResponse:
    return SupervisorServiceReportResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        deployment_node_id=row.deployment_node_id,
        edge_node_id=row.edge_node_id,
        supervisor_id=row.supervisor_id,
        node_kind=row.node_kind,
        hostname=row.hostname,
        service_manager=row.service_manager,
        service_status=row.service_status,
        install_status=row.install_status,
        credential_status=row.credential_status,
        version=row.version,
        os_name=row.os_name,
        host_profile=row.host_profile,
        heartbeat_at=row.heartbeat_at,
        diagnostics=dict(row.diagnostics),
        created_at=_coerce_datetime(row.created_at, fallback=node.updated_at),
        node=node,
    )


def redact_diagnostics(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_secret_key(key_text):
                redacted[key_text] = "[redacted]"
            else:
                redacted[key_text] = redact_diagnostics(item)
        return redacted
    if isinstance(value, list):
        return [redact_diagnostics(item) for item in value]
    return value


def _fresh_install_status(
    install_status: DeploymentInstallStatus,
    heartbeat_at: datetime | None,
    now: datetime,
) -> DeploymentInstallStatus:
    if install_status is DeploymentInstallStatus.REVOKED:
        return DeploymentInstallStatus.REVOKED
    if heartbeat_at is None:
        return install_status
    if now - heartbeat_at > SERVICE_REPORT_STALE_AFTER:
        return DeploymentInstallStatus.OFFLINE
    return install_status


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SECRET_KEY_PARTS)


def _ensure_identity_and_timestamps(
    row: DeploymentNode | SupervisorServiceStatusReport,
    *,
    now: datetime,
) -> None:
    if row.id is None:
        row.id = uuid4()
    if row.created_at is None:
        row.created_at = now
    if isinstance(row, DeploymentNode) and row.updated_at is None:
        row.updated_at = now


def _coerce_datetime(value: object, *, fallback: datetime) -> datetime:
    return value if isinstance(value, datetime) else fallback


async def _flush_if_available(session: object) -> None:
    flush = getattr(session, "flush", None)
    if callable(flush):
        await flush()
