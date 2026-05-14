from __future__ import annotations

import hashlib
import re
import secrets
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from typing import Any, TypeVar, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    DeploymentNodeResponse,
    DeploymentSupportBundleResponse,
    MasterBootstrapComplete,
    MasterBootstrapCompleteResponse,
    MasterBootstrapRotateResponse,
    MasterBootstrapStatusResponse,
    NodeCredentialRevokeResponse,
    NodeCredentialRotateResponse,
    NodePairingClaim,
    NodePairingClaimResponse,
    NodePairingSessionCreate,
    NodePairingSessionResponse,
    OperationsLifecycleRequestResponse,
    SupervisorRuntimeReportResponse,
    SupervisorServiceReportCreate,
    SupervisorServiceReportResponse,
    TenantContext,
    WorkerModelAdmissionResponse,
)
from argus.compat import UTC
from argus.core.security import AuthenticatedUser
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    RoleEnum,
)
from argus.models.tables import (
    DeploymentCredentialEvent,
    DeploymentNode,
    EdgeNodeHardwareReport,
    MasterBootstrapSession,
    NodePairingSession,
    OperationsLifecycleRequest,
    SupervisorNodeCredential,
    SupervisorServiceStatusReport,
    Tenant,
    User,
    WorkerModelAdmissionReport,
    WorkerRuntimeReport,
)
from argus.services.supervisor_operations import (
    edge_node_hardware_report_response,
    operations_lifecycle_request_response,
    supervisor_runtime_report_response,
    worker_model_admission_response,
)

SERVICE_REPORT_STALE_AFTER = timedelta(minutes=5)
ModelT = TypeVar("ModelT")
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
_BEARER_TOKEN_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_CREDENTIAL_RE = re.compile(r"\bvzcred_[A-Za-z0-9._~+/=-]+")
_KEY_VALUE_SECRET_RE = re.compile(
    r"\b(token|secret|password|credential|authorization|bearer)=\S+",
    re.IGNORECASE,
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

    async def get_master_bootstrap_status(self) -> MasterBootstrapStatusResponse:
        now = self.now_factory()
        async with self.session_factory() as session:
            tenants = await self._list_rows(session=session, model=Tenant)
            users = await self._list_rows(session=session, model=User)
            sessions = await self._list_rows(session=session, model=MasterBootstrapSession)

        first_run_required = not tenants or not users
        active_session = _latest_active_bootstrap_session(sessions, now=now)
        completed_session = _latest_consumed_bootstrap_session(sessions)
        tenant = next((row for row in tenants if isinstance(row, Tenant)), None)
        return MasterBootstrapStatusResponse(
            first_run_required=first_run_required,
            has_active_local_token=active_session is not None,
            active_token_expires_at=(
                active_session.expires_at if active_session is not None else None
            ),
            completed_at=(
                completed_session.consumed_at if completed_session is not None else None
            ),
            tenant_slug=tenant.slug if tenant is not None else None,
        )

    async def rotate_local_bootstrap_token(
        self,
        *,
        actor_subject: str | None,
    ) -> MasterBootstrapRotateResponse:
        now = self.now_factory()
        bootstrap_token = _new_bootstrap_token()
        expires_at = now + timedelta(minutes=15)
        async with self.session_factory() as session:
            sessions = await self._list_rows(session=session, model=MasterBootstrapSession)
            for row in sessions:
                if not isinstance(row, MasterBootstrapSession):
                    continue
                if row.status == "pending" and row.expires_at >= now:
                    row.status = "revoked"
                    row.updated_at = now
            session_row = MasterBootstrapSession(
                tenant_id=None,
                token_hash=_hash_secret(bootstrap_token),
                status="pending",
                expires_at=expires_at,
                consumed_at=None,
                created_by_subject=actor_subject,
                consumed_by_subject=None,
            )
            _ensure_identity_and_timestamps(session_row, now=now)
            session.add(session_row)
            await session.commit()
            await session.refresh(session_row)
        return MasterBootstrapRotateResponse(
            bootstrap_token=bootstrap_token,
            expires_at=session_row.expires_at,
        )

    async def complete_master_bootstrap(
        self,
        payload: MasterBootstrapComplete,
    ) -> MasterBootstrapCompleteResponse:
        now = self.now_factory()
        token_hash = _hash_secret(payload.bootstrap_token)
        async with self.session_factory() as session:
            sessions = await self._list_rows(session=session, model=MasterBootstrapSession)
            matching_sessions = [
                row
                for row in sessions
                if isinstance(row, MasterBootstrapSession) and row.token_hash == token_hash
            ]
            if any(row.status == "consumed" for row in matching_sessions):
                msg = "Bootstrap token is already consumed."
                raise ValueError(msg)
            session_row = next(
                (row for row in matching_sessions if row.status == "pending"),
                None,
            )
            if session_row is None:
                msg = "Invalid bootstrap token."
                raise ValueError(msg)
            if session_row.expires_at < now:
                session_row.status = "expired"
                session_row.updated_at = now
                await session.commit()
                msg = "Bootstrap token expired."
                raise ValueError(msg)

            tenant_slug = payload.tenant_slug or _slugify(payload.tenant_name)
            tenant = Tenant(name=payload.tenant_name, slug=tenant_slug)
            _ensure_identity_and_timestamps(tenant, now=now)
            session.add(tenant)
            await _flush_if_available(session)

            admin_subject = f"bootstrap:{payload.admin_email}"
            user = User(
                tenant_id=tenant.id,
                email=payload.admin_email,
                oidc_sub=admin_subject,
                role=RoleEnum.ADMIN,
            )
            _ensure_identity_and_timestamps(user, now=now)
            session.add(user)

            supervisor_id = payload.central_supervisor_id or _slugify(
                payload.central_node_name
            )
            node = DeploymentNode(
                tenant_id=tenant.id,
                edge_node_id=None,
                supervisor_id=supervisor_id,
                node_kind=DeploymentNodeKind.CENTRAL,
                hostname=payload.central_node_name,
                install_status=DeploymentInstallStatus.INSTALLED,
                credential_status=DeploymentCredentialStatus.MISSING,
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

            session_row.tenant_id = tenant.id
            session_row.status = "consumed"
            session_row.consumed_at = now
            session_row.consumed_by_subject = admin_subject
            session_row.updated_at = now
            await session.commit()
            await session.refresh(tenant)
            await session.refresh(node)

        return MasterBootstrapCompleteResponse(
            first_run_required=False,
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            admin_subject=admin_subject,
            completed_at=now,
            central_node=deployment_node_response(node, now=now),
        )

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

    async def get_support_bundle(
        self,
        *,
        tenant_id: UUID,
        node_id: UUID,
    ) -> DeploymentSupportBundleResponse:
        now = self.now_factory()
        async with self.session_factory() as session:
            node = await self._load_node_by_id(
                session=session,
                tenant_id=tenant_id,
                node_id=node_id,
            )
            service_reports = await _query_rows(
                session=session,
                model=SupervisorServiceStatusReport,
                tenant_id=tenant_id,
                deployment_node_id=node.id,
            )
            lifecycle_requests = await _query_rows(
                session=session,
                model=OperationsLifecycleRequest,
                tenant_id=tenant_id,
                edge_node_id=node.edge_node_id,
            )
            runtime_reports = await _query_rows(
                session=session,
                model=WorkerRuntimeReport,
                tenant_id=tenant_id,
                edge_node_id=node.edge_node_id,
            )
            hardware_reports = await _query_rows(
                session=session,
                model=EdgeNodeHardwareReport,
                tenant_id=tenant_id,
                edge_node_id=node.edge_node_id,
                supervisor_id=node.supervisor_id,
            )
            model_admissions = await _query_rows(
                session=session,
                model=WorkerModelAdmissionReport,
                tenant_id=tenant_id,
                edge_node_id=node.edge_node_id,
            )

        node_response = deployment_node_response(node, now=now).model_copy(
            update={"diagnostics": redact_diagnostics(dict(node.diagnostics))}
        )
        return DeploymentSupportBundleResponse(
            node=node_response,
            service_reports=[
                _redacted_service_report_response(report, node=node_response)
                for report in service_reports
                if isinstance(report, SupervisorServiceStatusReport)
            ],
            recent_lifecycle_requests=[
                _redacted_lifecycle_response(row)
                for row in _recent_rows(
                    lifecycle_requests,
                    model=OperationsLifecycleRequest,
                    timestamp_attr="requested_at",
                )
            ],
            recent_runtime_reports=[
                _redacted_runtime_response(row)
                for row in _recent_rows(
                    runtime_reports,
                    model=WorkerRuntimeReport,
                    timestamp_attr="heartbeat_at",
                )
            ],
            hardware_reports=[
                edge_node_hardware_report_response(row)
                for row in _recent_rows(
                    hardware_reports,
                    model=EdgeNodeHardwareReport,
                    timestamp_attr="reported_at",
                )
            ],
            model_admission_reports=[
                _redacted_model_admission_response(row)
                for row in _recent_rows(
                    model_admissions,
                    model=WorkerModelAdmissionReport,
                    timestamp_attr="evaluated_at",
                )
            ],
            lifecycle_summary=_lifecycle_summary(lifecycle_requests),
            runtime_summary=_runtime_summary(runtime_reports),
            hardware_summary=_hardware_summary(hardware_reports),
            model_admission_summary=_model_admission_summary(model_admissions),
            config_references=_config_references(
                runtime_reports=runtime_reports,
                hardware_reports=hardware_reports,
                model_admissions=model_admissions,
            ),
            selected_log_excerpts=_selected_log_excerpts(
                node=node,
                service_reports=service_reports,
            ),
            diagnostics={
                "node": redact_diagnostics(dict(node.diagnostics)),
                "service_reports": [
                    redact_diagnostics(dict(report.diagnostics))
                    for report in service_reports
                    if isinstance(report, SupervisorServiceStatusReport)
                ],
            },
            generated_at=now,
        )

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
                credential_version=1,
                status=DeploymentCredentialStatus.ACTIVE,
                issued_at=now,
                expires_at=None,
                revoked_at=None,
            )
            _ensure_identity_and_timestamps(credential, now=now)
            session.add(credential)
            await _flush_if_available(session)
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
            credential_version=credential.credential_version,
            node=deployment_node_response(node, now=now),
        )

    async def rotate_edge_node_credentials(
        self,
        *,
        tenant_id: UUID,
        edge_node_id: UUID,
        actor_subject: str | None,
    ) -> NodeCredentialRotateResponse:
        now = self.now_factory()
        async with self.session_factory() as session:
            node = await self._load_node_by_edge_node(
                session=session,
                tenant_id=tenant_id,
                edge_node_id=edge_node_id,
            )
        return await self.rotate_node_credentials(
            tenant_id=tenant_id,
            node_id=node.id,
            actor_subject=actor_subject,
            now=now,
        )

    async def rotate_node_credentials(
        self,
        *,
        tenant_id: UUID,
        node_id: UUID,
        actor_subject: str | None,
        now: datetime | None = None,
    ) -> NodeCredentialRotateResponse:
        rotation_time = now or self.now_factory()
        async with self.session_factory() as session:
            node = await self._load_node_by_id(
                session=session,
                tenant_id=tenant_id,
                node_id=node_id,
            )
            credentials = await self._load_credentials_for_node(
                session=session,
                tenant_id=tenant_id,
                node_id=node.id,
            )
            revoked = 0
            next_version = _next_credential_version(credentials)
            for credential in credentials:
                if credential.status is DeploymentCredentialStatus.REVOKED:
                    continue
                credential.status = DeploymentCredentialStatus.REVOKED
                credential.revoked_at = rotation_time
                credential.updated_at = rotation_time
                revoked += 1
                session.add(
                    _credential_event(
                        tenant_id=tenant_id,
                        deployment_node_id=node.id,
                        credential_id=credential.id,
                        event_type="credential.revoked",
                        actor_subject=actor_subject,
                        occurred_at=rotation_time,
                        metadata={
                            "reason": "rotation",
                            "replaced_by_credential_version": next_version,
                        },
                    )
                )

            credential_material = _new_credential_material()
            credential = SupervisorNodeCredential(
                tenant_id=tenant_id,
                deployment_node_id=node.id,
                supervisor_id=node.supervisor_id,
                credential_hash=_hash_secret(credential_material),
                encrypted_credential=None,
                credential_version=next_version,
                status=DeploymentCredentialStatus.ACTIVE,
                issued_at=rotation_time,
                expires_at=None,
                revoked_at=None,
            )
            _ensure_identity_and_timestamps(credential, now=rotation_time)
            session.add(credential)
            await _flush_if_available(session)
            node.credential_status = DeploymentCredentialStatus.ACTIVE
            if node.install_status is DeploymentInstallStatus.REVOKED:
                node.install_status = DeploymentInstallStatus.INSTALLED
            node.updated_at = rotation_time
            session.add(
                _credential_event(
                    tenant_id=tenant_id,
                    deployment_node_id=node.id,
                    credential_id=credential.id,
                    event_type="credential.issued",
                    actor_subject=actor_subject,
                    occurred_at=rotation_time,
                    metadata={
                        "reason": "rotation",
                        "credential_version": next_version,
                    },
                )
            )
            session.add(
                _credential_event(
                    tenant_id=tenant_id,
                    deployment_node_id=node.id,
                    credential_id=credential.id,
                    event_type="credential.rotated",
                    actor_subject=actor_subject,
                    occurred_at=rotation_time,
                    metadata={
                        "credential_version": next_version,
                        "revoked_credentials": revoked,
                    },
                )
            )
            await session.commit()
            await session.refresh(node)
            await session.refresh(credential)

        return NodeCredentialRotateResponse(
            node_id=node.id,
            credential_id=credential.id,
            credential_material=credential_material,
            credential_hash=credential.credential_hash,
            credential_version=credential.credential_version,
            revoked_credentials=revoked,
            credential_status=DeploymentCredentialStatus.ACTIVE,
            node=deployment_node_response(node, now=rotation_time),
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

    async def _list_rows(
        self,
        *,
        session: AsyncSession,
        model: type[object],
    ) -> list[object]:
        statement = select(model)
        rows = list((await session.execute(statement)).scalars().all())
        return [row for row in rows if isinstance(row, model)]

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

    async def _load_node_by_edge_node(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        edge_node_id: UUID,
    ) -> DeploymentNode:
        statement = (
            select(DeploymentNode)
            .where(DeploymentNode.tenant_id == tenant_id)
            .where(DeploymentNode.edge_node_id == edge_node_id)
        )
        row = (await session.execute(statement)).scalar_one_or_none()
        if isinstance(row, DeploymentNode):
            return row
        msg = "Deployment node not found."
        raise ValueError(msg)

    async def _load_credentials_for_node(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        node_id: UUID,
    ) -> list[SupervisorNodeCredential]:
        statement = (
            select(SupervisorNodeCredential)
            .where(SupervisorNodeCredential.tenant_id == tenant_id)
            .where(SupervisorNodeCredential.deployment_node_id == node_id)
        )
        return [
            row
            for row in (await session.execute(statement)).scalars().all()
            if isinstance(row, SupervisorNodeCredential)
        ]

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
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redacted_service_report_response(
    row: SupervisorServiceStatusReport,
    *,
    node: DeploymentNodeResponse,
) -> SupervisorServiceReportResponse:
    response = supervisor_service_report_response(row, node=node)
    return response.model_copy(
        update={"diagnostics": redact_diagnostics(response.diagnostics)}
    )


def _redacted_lifecycle_response(
    row: OperationsLifecycleRequest,
) -> OperationsLifecycleRequestResponse:
    response = operations_lifecycle_request_response(row)
    return response.model_copy(
        update={"request_payload": redact_diagnostics(response.request_payload)}
    )


def _redacted_runtime_response(row: WorkerRuntimeReport) -> SupervisorRuntimeReportResponse:
    response = supervisor_runtime_report_response(row)
    return response.model_copy(update={"last_error": redact_diagnostics(response.last_error)})


def _redacted_model_admission_response(
    row: WorkerModelAdmissionReport,
) -> WorkerModelAdmissionResponse:
    response = worker_model_admission_response(row)
    return response.model_copy(
        update={
            "constraints": redact_diagnostics(response.constraints),
            "stream_profile": redact_diagnostics(response.stream_profile),
        }
    )


def _lifecycle_summary(rows: Iterable[object]) -> dict[str, object]:
    lifecycle_rows = [row for row in rows if isinstance(row, OperationsLifecycleRequest)]
    latest = max(
        (row.requested_at for row in lifecycle_rows),
        default=None,
    )
    return {
        "total": len(lifecycle_rows),
        "by_status": _count_by(lifecycle_rows, "status"),
        "latest_requested_at": latest,
    }


def _runtime_summary(rows: Iterable[object]) -> dict[str, object]:
    runtime_rows = [row for row in rows if isinstance(row, WorkerRuntimeReport)]
    latest = max((row.heartbeat_at for row in runtime_rows), default=None)
    return {
        "total": len(runtime_rows),
        "by_state": _count_by(runtime_rows, "runtime_state"),
        "latest_heartbeat_at": latest,
    }


def _hardware_summary(rows: Iterable[object]) -> dict[str, object]:
    hardware_rows = [row for row in rows if isinstance(row, EdgeNodeHardwareReport)]
    latest = max(hardware_rows, key=lambda row: row.reported_at, default=None)
    return {
        "total": len(hardware_rows),
        "latest_reported_at": latest.reported_at if latest is not None else None,
        "host_profile": latest.host_profile if latest is not None else None,
        "accelerators": list(latest.accelerators) if latest is not None else [],
    }


def _model_admission_summary(rows: Iterable[object]) -> dict[str, object]:
    admission_rows = [row for row in rows if isinstance(row, WorkerModelAdmissionReport)]
    latest = max((row.evaluated_at for row in admission_rows), default=None)
    return {
        "total": len(admission_rows),
        "by_status": _count_by(admission_rows, "status"),
        "latest_evaluated_at": latest,
    }


def _config_references(
    *,
    runtime_reports: Iterable[object],
    hardware_reports: Iterable[object],
    model_admissions: Iterable[object],
) -> dict[str, object]:
    runtime_rows = [row for row in runtime_reports if isinstance(row, WorkerRuntimeReport)]
    hardware_rows = [
        row for row in hardware_reports if isinstance(row, EdgeNodeHardwareReport)
    ]
    admission_rows = [
        row for row in model_admissions if isinstance(row, WorkerModelAdmissionReport)
    ]
    return {
        "scene_contract_hashes": _sorted_values(
            row.scene_contract_hash for row in runtime_rows
        ),
        "runtime_artifact_ids": _sorted_values(
            [
                *(row.runtime_artifact_id for row in runtime_rows),
                *(row.runtime_artifact_id for row in admission_rows),
            ]
        ),
        "runtime_selection_profile_ids": _sorted_values(
            row.runtime_selection_profile_id for row in admission_rows
        ),
        "hardware_report_hashes": _sorted_values(row.report_hash for row in hardware_rows),
        "hardware_report_ids": _sorted_values(
            row.hardware_report_id for row in admission_rows
        ),
    }


def _selected_log_excerpts(
    *,
    node: DeploymentNode,
    service_reports: Iterable[object],
) -> list[dict[str, Any]]:
    excerpts: list[dict[str, Any]] = []
    for source, diagnostics in [
        ("node", dict(node.diagnostics)),
        *[
            (f"service_report:{report.supervisor_id}", dict(report.diagnostics))
            for report in service_reports
            if isinstance(report, SupervisorServiceStatusReport)
        ],
    ]:
        for key in ("log_excerpt", "log_excerpts", "logs", "service_logs"):
            if key not in diagnostics:
                continue
            for excerpt in _coerce_log_excerpts(diagnostics[key]):
                excerpts.append(
                    {
                        "source": source,
                        "excerpt": redact_diagnostics(excerpt),
                    }
                )
    return excerpts[:10]


def _coerce_log_excerpts(value: object) -> list[object]:
    if isinstance(value, list):
        return value[:10]
    if isinstance(value, (str, dict)):
        return [value]
    return []


def _count_by(rows: Iterable[object], attribute: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = getattr(row, attribute, "unknown")
        key = getattr(value, "value", str(value))
        counts[key] = counts.get(key, 0) + 1
    return counts


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


def _redact_text(value: str) -> str:
    redacted = _BEARER_TOKEN_RE.sub("Bearer [redacted]", value)
    redacted = _CREDENTIAL_RE.sub("[redacted]", redacted)
    return _KEY_VALUE_SECRET_RE.sub(lambda match: f"{match.group(1)}=[redacted]", redacted)


def _recent_rows(  # noqa: UP047
    rows: Iterable[object],
    *,
    model: type[ModelT],
    timestamp_attr: str,
    limit: int = 5,
) -> list[ModelT]:
    matching_rows = [row for row in rows if isinstance(row, model)]
    return sorted(
        matching_rows,
        key=lambda row: _coerce_datetime(
            getattr(row, timestamp_attr, None),
            fallback=datetime.min.replace(tzinfo=UTC),
        ),
        reverse=True,
    )[:limit]


def _sorted_values(values: Iterable[object]) -> list[str]:
    return sorted({str(value) for value in values if value is not None})


def _ensure_identity_and_timestamps(
    row: object,
    *,
    now: datetime,
) -> None:
    row_any = cast(Any, row)
    if getattr(row_any, "id", None) is None:
        row_any.id = uuid4()
    if hasattr(row_any, "created_at") and getattr(row_any, "created_at", None) is None:
        row_any.created_at = now
    if hasattr(row_any, "updated_at") and getattr(row_any, "updated_at", None) is None:
        row_any.updated_at = now


def _credential_event(
    *,
    tenant_id: UUID,
    deployment_node_id: UUID,
    credential_id: UUID | None,
    event_type: str,
    actor_subject: str | None,
    occurred_at: datetime,
    metadata: dict[str, object] | None = None,
) -> DeploymentCredentialEvent:
    row = DeploymentCredentialEvent(
        tenant_id=tenant_id,
        deployment_node_id=deployment_node_id,
        credential_id=credential_id,
        event_type=event_type,
        actor_subject=actor_subject,
        occurred_at=occurred_at,
        event_metadata=metadata or {},
    )
    _ensure_identity_and_timestamps(row, now=occurred_at)
    return row


def _next_credential_version(credentials: list[SupervisorNodeCredential]) -> int:
    return (
        max((credential.credential_version or 1 for credential in credentials), default=0)
        + 1
    )


def _pairing_status(row: NodePairingSession, now: datetime) -> str:
    if row.status == "pending" and row.expires_at < now:
        return "expired"
    return row.status


def _new_pairing_code() -> str:
    return secrets.token_urlsafe(6)


def _new_bootstrap_token() -> str:
    return f"vzboot_{secrets.token_urlsafe(24)}"


def _new_credential_material() -> str:
    return f"vzcred_{secrets.token_urlsafe(32)}"


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "vezor"


def _latest_active_bootstrap_session(
    rows: list[object],
    *,
    now: datetime,
) -> MasterBootstrapSession | None:
    pending = [
        row
        for row in rows
        if isinstance(row, MasterBootstrapSession)
        and row.status == "pending"
        and row.expires_at >= now
    ]
    return max(
        pending,
        key=lambda row: _coerce_datetime(row.created_at, fallback=datetime.min.replace(tzinfo=UTC)),
        default=None,
    )


def _latest_consumed_bootstrap_session(rows: list[object]) -> MasterBootstrapSession | None:
    consumed = [
        row
        for row in rows
        if isinstance(row, MasterBootstrapSession) and row.status == "consumed"
    ]
    return max(
        consumed,
        key=lambda row: _coerce_datetime(
            row.consumed_at,
            fallback=datetime.min.replace(tzinfo=UTC),
        ),
        default=None,
    )


def _coerce_datetime(value: object, *, fallback: datetime) -> datetime:
    return value if isinstance(value, datetime) else fallback


async def _query_rows(  # noqa: UP047
    *,
    session: AsyncSession,
    model: type[ModelT],
    tenant_id: UUID,
    deployment_node_id: UUID | None = None,
    edge_node_id: UUID | None = None,
    supervisor_id: str | None = None,
) -> list[ModelT]:
    model_columns = cast(Any, model)
    statement = select(model).where(model_columns.tenant_id == tenant_id)
    if deployment_node_id is not None:
        statement = statement.where(model_columns.deployment_node_id == deployment_node_id)
    if hasattr(model, "edge_node_id"):
        if edge_node_id is None:
            statement = statement.where(model_columns.edge_node_id.is_(None))
        else:
            statement = statement.where(model_columns.edge_node_id == edge_node_id)
    if supervisor_id is not None and hasattr(model, "supervisor_id"):
        statement = statement.where(model_columns.supervisor_id == supervisor_id)
    return cast(list[ModelT], list((await session.execute(statement)).scalars().all()))


async def _flush_if_available(session: object) -> None:
    flush = getattr(session, "flush", None)
    if callable(flush):
        await flush()
