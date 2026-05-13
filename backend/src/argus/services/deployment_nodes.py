from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    DeploymentNodeResponse,
    NodeCredentialRevokeResponse,
    NodePairingClaim,
    NodePairingClaimResponse,
    NodePairingSessionCreate,
    NodePairingSessionResponse,
    SupervisorServiceReportCreate,
    SupervisorServiceReportResponse,
    TenantContext,
)
from argus.compat import UTC
from argus.core.security import AuthenticatedUser
from argus.models.enums import DeploymentCredentialStatus, DeploymentInstallStatus, RoleEnum
from argus.models.tables import (
    DeploymentCredentialEvent,
    DeploymentNode,
    NodePairingSession,
    SupervisorNodeCredential,
    SupervisorServiceStatusReport,
    Tenant,
)

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
        authenticated_node_id: UUID | None = None,
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
            node = await self._load_node_for_service_report(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
                payload=payload,
                authenticated_node_id=authenticated_node_id,
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

    async def create_pairing_session(
        self,
        *,
        tenant_id: UUID,
        payload: NodePairingSessionCreate,
        actor_subject: str | None,
    ) -> NodePairingSessionResponse:
        now = self.now_factory()
        code = _new_pairing_code()
        row = NodePairingSession(
            tenant_id=tenant_id,
            deployment_node_id=None,
            edge_node_id=payload.edge_node_id,
            node_kind=payload.node_kind,
            hostname=payload.hostname,
            pairing_code_hash=_hash_secret(code),
            status="pending",
            expires_at=now + timedelta(seconds=payload.requested_ttl_seconds),
            consumed_at=None,
            claimed_by_supervisor=None,
            created_by_subject=actor_subject,
        )
        _ensure_identity_and_timestamps(row, now=now)
        async with self.session_factory() as session:
            await self._validate_edge_node_scope(
                session=session,
                tenant_id=tenant_id,
                edge_node_id=payload.edge_node_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return pairing_session_response(row, now=now, pairing_code=code)

    async def get_pairing_session(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
    ) -> NodePairingSessionResponse:
        now = self.now_factory()
        async with self.session_factory() as session:
            row = await self._load_pairing_session(
                session=session,
                tenant_id=tenant_id,
                session_id=session_id,
            )
        return pairing_session_response(row, now=now, pairing_code=None)

    async def claim_pairing_session(
        self,
        *,
        tenant_id: UUID | None = None,
        session_id: UUID,
        payload: NodePairingClaim,
    ) -> NodePairingClaimResponse:
        now = self.now_factory()
        async with self.session_factory() as session:
            pairing = await self._load_pairing_session(
                session=session,
                tenant_id=tenant_id,
                session_id=session_id,
                for_update=True,
            )
            effective_tenant_id = pairing.tenant_id
            if pairing.status == "consumed":
                msg = "Pairing session is already consumed."
                raise ValueError(msg)
            if pairing.expires_at < now:
                pairing.status = "expired"
                await session.commit()
                msg = "Pairing session expired."
                raise ValueError(msg)
            if not secrets.compare_digest(
                pairing.pairing_code_hash,
                _hash_secret(payload.pairing_code),
            ):
                msg = "Invalid pairing code."
                raise ValueError(msg)

            node = await self._load_node_by_supervisor(
                session=session,
                tenant_id=effective_tenant_id,
                supervisor_id=payload.supervisor_id,
            )
            if node is None:
                node = DeploymentNode(
                    tenant_id=effective_tenant_id,
                    edge_node_id=pairing.edge_node_id,
                    supervisor_id=payload.supervisor_id,
                    node_kind=pairing.node_kind,
                    hostname=payload.hostname,
                    install_status=DeploymentInstallStatus.INSTALLED,
                    credential_status=DeploymentCredentialStatus.ACTIVE,
                    service_manager=None,
                    service_status=None,
                    version=None,
                    os_name=None,
                    host_profile=None,
                    last_service_reported_at=None,
                    diagnostics={},
                )
                _ensure_identity_and_timestamps(node, now=now)
                session.add(node)
                await _flush_if_available(session)
            else:
                node.edge_node_id = pairing.edge_node_id
                node.node_kind = pairing.node_kind
                node.hostname = payload.hostname
                node.install_status = DeploymentInstallStatus.INSTALLED
                node.credential_status = DeploymentCredentialStatus.ACTIVE
                node.updated_at = now

            credential_material = _new_credential_material()
            credential = SupervisorNodeCredential(
                tenant_id=effective_tenant_id,
                deployment_node_id=node.id,
                supervisor_id=payload.supervisor_id,
                credential_hash=_hash_secret(credential_material),
                encrypted_credential=None,
                status=DeploymentCredentialStatus.ACTIVE,
                issued_at=now,
                expires_at=None,
                revoked_at=None,
            )
            _ensure_identity_and_timestamps(credential, now=now)
            session.add(credential)
            pairing.deployment_node_id = node.id
            pairing.status = "consumed"
            pairing.consumed_at = now
            pairing.claimed_by_supervisor = payload.supervisor_id
            pairing.updated_at = now
            session.add(
                _credential_event(
                    tenant_id=effective_tenant_id,
                    deployment_node_id=node.id,
                    credential_id=credential.id,
                    event_type="credential.issued",
                    actor_subject=payload.supervisor_id,
                    occurred_at=now,
                )
            )
            await session.commit()
            await session.refresh(node)
            await session.refresh(credential)

        return NodePairingClaimResponse(
            session_id=session_id,
            credential_id=credential.id,
            credential_material=credential_material,
            credential_hash=credential.credential_hash,
            node=deployment_node_response(node, now=now),
        )

    async def revoke_node_credentials(
        self,
        *,
        tenant_id: UUID,
        node_id: UUID,
        actor_subject: str | None,
    ) -> NodeCredentialRevokeResponse:
        now = self.now_factory()
        async with self.session_factory() as session:
            node = await self._load_node_by_id(
                session=session,
                tenant_id=tenant_id,
                node_id=node_id,
            )
            statement = (
                select(SupervisorNodeCredential)
                .where(SupervisorNodeCredential.tenant_id == tenant_id)
                .where(SupervisorNodeCredential.deployment_node_id == node_id)
            )
            credentials = list((await session.execute(statement)).scalars().all())
            revoked = 0
            for credential in credentials:
                if not isinstance(credential, SupervisorNodeCredential):
                    continue
                if credential.status is DeploymentCredentialStatus.REVOKED:
                    continue
                credential.status = DeploymentCredentialStatus.REVOKED
                credential.revoked_at = now
                credential.updated_at = now
                revoked += 1
                session.add(
                    _credential_event(
                        tenant_id=tenant_id,
                        deployment_node_id=node_id,
                        credential_id=credential.id,
                        event_type="credential.revoked",
                        actor_subject=actor_subject,
                        occurred_at=now,
                    )
                )
            node.credential_status = DeploymentCredentialStatus.REVOKED
            node.install_status = DeploymentInstallStatus.REVOKED
            node.updated_at = now
            await session.commit()
            await session.refresh(node)
        return NodeCredentialRevokeResponse(
            node_id=node_id,
            revoked_credentials=revoked,
            credential_status=DeploymentCredentialStatus.REVOKED,
        )

    async def validate_supervisor_credential(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        credential_material: str,
    ) -> bool:
        credential_hash = _hash_secret(credential_material)
        async with self.session_factory() as session:
            statement = (
                select(SupervisorNodeCredential)
                .where(SupervisorNodeCredential.tenant_id == tenant_id)
                .where(SupervisorNodeCredential.supervisor_id == supervisor_id)
            )
            rows = list((await session.execute(statement)).scalars().all())
        return any(
            isinstance(row, SupervisorNodeCredential)
            and row.credential_hash == credential_hash
            and row.status is DeploymentCredentialStatus.ACTIVE
            for row in rows
        )

    async def authenticate_supervisor_credential(
        self,
        *,
        credential_material: str,
        supervisor_id: str | None = None,
    ) -> TenantContext:
        credential_hash = _hash_secret(credential_material)
        async with self.session_factory() as session:
            statement = (
                select(SupervisorNodeCredential)
                .where(SupervisorNodeCredential.credential_hash == credential_hash)
                .where(SupervisorNodeCredential.status == DeploymentCredentialStatus.ACTIVE)
            )
            if supervisor_id is not None:
                statement = statement.where(SupervisorNodeCredential.supervisor_id == supervisor_id)
            credentials = list((await session.execute(statement)).scalars().all())
            for credential in credentials:
                if not isinstance(credential, SupervisorNodeCredential):
                    continue
                if credential.status is not DeploymentCredentialStatus.ACTIVE:
                    continue
                if not secrets.compare_digest(credential.credential_hash, credential_hash):
                    continue
                node = await session.get(DeploymentNode, credential.deployment_node_id)
                if not isinstance(node, DeploymentNode):
                    continue
                if node.credential_status is not DeploymentCredentialStatus.ACTIVE:
                    continue
                tenant = await session.get(Tenant, credential.tenant_id)
                if not isinstance(tenant, Tenant):
                    continue
                return TenantContext(
                    tenant_id=tenant.id,
                    tenant_slug=tenant.slug,
                    user=AuthenticatedUser(
                        subject=f"supervisor:{credential.supervisor_id}",
                        email=None,
                        role=RoleEnum.OPERATOR,
                        issuer="vezor-node-credential",
                        realm=tenant.slug,
                        is_superadmin=False,
                        tenant_context=str(tenant.id),
                        claims={
                            "auth_type": "supervisor_node_credential",
                            "deployment_node_id": str(node.id),
                        },
                    ),
                )
        msg = "Invalid supervisor credential."
        raise ValueError(msg)

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

    async def _load_node_for_service_report(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        supervisor_id: str,
        payload: SupervisorServiceReportCreate,
        authenticated_node_id: UUID | None,
    ) -> DeploymentNode | None:
        if authenticated_node_id is None:
            return await self._load_node_by_supervisor(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
            )
        node = await self._load_node_by_id(
            session=session,
            tenant_id=tenant_id,
            node_id=authenticated_node_id,
        )
        if (
            node.supervisor_id != supervisor_id
            or node.node_kind is not payload.node_kind
            or node.edge_node_id != payload.edge_node_id
        ):
            msg = "Supervisor credential is not scoped to this service report."
            raise ValueError(msg)
        return node

    async def _load_node_by_id(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        node_id: UUID,
    ) -> DeploymentNode:
        statement = select(DeploymentNode).where(
            DeploymentNode.tenant_id == tenant_id,
            DeploymentNode.id == node_id,
        )
        row = (await session.execute(statement)).scalar_one_or_none()
        if isinstance(row, DeploymentNode):
            return row
        msg = "Deployment node not found."
        raise ValueError(msg)

    async def _load_pairing_session(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID | None,
        session_id: UUID,
        for_update: bool = False,
    ) -> NodePairingSession:
        statement = select(NodePairingSession).where(NodePairingSession.id == session_id)
        if tenant_id is not None:
            statement = statement.where(NodePairingSession.tenant_id == tenant_id)
        if for_update:
            statement = statement.with_for_update()
        row = (await session.execute(statement)).scalar_one_or_none()
        if isinstance(row, NodePairingSession):
            return row
        msg = "Pairing session not found."
        raise ValueError(msg)

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


def pairing_session_response(
    row: NodePairingSession,
    *,
    now: datetime,
    pairing_code: str | None,
) -> NodePairingSessionResponse:
    return NodePairingSessionResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        deployment_node_id=row.deployment_node_id,
        edge_node_id=row.edge_node_id,
        node_kind=row.node_kind,
        hostname=getattr(row, "hostname", None),
        status=_pairing_status(row, now),
        expires_at=row.expires_at,
        consumed_at=row.consumed_at,
        claimed_by_supervisor=row.claimed_by_supervisor,
        created_by_subject=row.created_by_subject,
        pairing_code=pairing_code,
        created_at=_coerce_datetime(row.created_at, fallback=now),
        updated_at=_coerce_datetime(row.updated_at, fallback=now),
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
    row: (
        DeploymentNode
        | SupervisorServiceStatusReport
        | NodePairingSession
        | SupervisorNodeCredential
        | DeploymentCredentialEvent
    ),
    *,
    now: datetime,
) -> None:
    if row.id is None:
        row.id = uuid4()
    if row.created_at is None:
        row.created_at = now
    if isinstance(row, (DeploymentNode, NodePairingSession, SupervisorNodeCredential)):
        if row.updated_at is None:
            row.updated_at = now


def _credential_event(
    *,
    tenant_id: UUID,
    deployment_node_id: UUID,
    credential_id: UUID | None,
    event_type: str,
    actor_subject: str | None,
    occurred_at: datetime,
) -> DeploymentCredentialEvent:
    row = DeploymentCredentialEvent(
        tenant_id=tenant_id,
        deployment_node_id=deployment_node_id,
        credential_id=credential_id,
        event_type=event_type,
        actor_subject=actor_subject,
        occurred_at=occurred_at,
        event_metadata={},
    )
    _ensure_identity_and_timestamps(row, now=occurred_at)
    return row


def _pairing_status(row: NodePairingSession, now: datetime) -> str:
    if row.status == "pending" and row.expires_at < now:
        return "expired"
    return row.status


def _new_pairing_code() -> str:
    return secrets.token_urlsafe(6)


def _new_credential_material() -> str:
    return f"vzcred_{secrets.token_urlsafe(32)}"


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _coerce_datetime(value: object, *, fallback: datetime) -> datetime:
    return value if isinstance(value, datetime) else fallback


async def _flush_if_available(session: object) -> None:
    flush = getattr(session, "flush", None)
    if callable(flush):
        await flush()
