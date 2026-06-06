from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any, Protocol, cast
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.models.tables import DeploymentNode, EdgeNode, Site
from argus.support.contracts import (
    BreakGlassAccessRecord,
    JsonObject,
    OnboardingCheck,
    OnboardingCheckRunRecord,
    SupportBundleRecord,
    SupportSessionRecord,
    SupportTunnelRecord,
)
from argus.support.tables import (
    BreakGlassAccessRecord as BreakGlassAccessRecordRow,
)
from argus.support.tables import (
    OnboardingCheckRun,
    SupportBundle,
    SupportSession,
    SupportTunnel,
)
from argus.support.tunnel_transport import validate_support_tunnel_parameters

SENSITIVE_KEY_PARTS = ("password", "secret", "token", "api_key", "credential")
SUPPORTED_TRANSPORTS = {"ssh_reverse"}
DEFAULT_ONBOARDING_CHECKS: tuple[OnboardingCheck, ...] = (
    OnboardingCheck(key="identity", label="Identity", status="ready"),
    OnboardingCheck(key="master_readiness", label="Master readiness", status="ready"),
    OnboardingCheck(key="edge_pairing", label="Edge pairing", status="ready"),
    OnboardingCheck(key="camera_reachability", label="Camera reachability", status="ready"),
    OnboardingCheck(key="model_runtime", label="Model runtime", status="ready"),
    OnboardingCheck(key="link_state", label="Link state", status="ready"),
    OnboardingCheck(key="evidence_storage", label="Evidence storage", status="ready"),
    OnboardingCheck(key="billing_entitlement", label="Billing entitlement", status="ready"),
    OnboardingCheck(key="support_readiness", label="Support readiness", status="ready"),
)


class SupportError(ValueError):
    pass


class SupportNotFoundError(SupportError):
    pass


class SupportResourceValidator(Protocol):
    async def validate_site(self, *, tenant_id: UUID, site_id: UUID) -> None: ...

    async def validate_node(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        node_id: UUID,
    ) -> None: ...


class SupportService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        resource_validator: SupportResourceValidator | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.resource_validator = resource_validator
        self._bundles: dict[UUID, SupportBundleRecord] = {}
        self._sessions: dict[UUID, SupportSessionRecord] = {}
        self._tunnels: dict[UUID, SupportTunnelRecord] = {}
        self._break_glass_records: dict[UUID, BreakGlassAccessRecord] = {}
        self._onboarding_runs: dict[UUID, OnboardingCheckRunRecord] = {}

    def generate_bundle(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        diagnostics: Mapping[str, object] | None = None,
        node_id: UUID | None = None,
        include_logs: bool = False,
        pack_id: str | None = None,
    ) -> SupportBundleRecord:
        now = _now()
        bundle = SupportBundleRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            node_id=node_id,
            pack_id=pack_id,
            include_logs=include_logs,
            payload=_support_bundle_payload(
                site_id=site_id,
                node_id=node_id,
                diagnostics=diagnostics,
                include_logs=include_logs,
            ),
            created_at=now,
        )
        self._bundles[bundle.id] = bundle
        return bundle

    async def agenerate_bundle(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        diagnostics: Mapping[str, object] | None = None,
        node_id: UUID | None = None,
        include_logs: bool = False,
        pack_id: str | None = None,
    ) -> SupportBundleRecord:
        if self.session_factory is None:
            await self._avalidate_resources(
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=node_id,
            )
            return self.generate_bundle(
                tenant_id=tenant_id,
                site_id=site_id,
                diagnostics=diagnostics,
                node_id=node_id,
                include_logs=include_logs,
                pack_id=pack_id,
            )
        row = SupportBundle(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            node_id=node_id,
            pack_id=pack_id,
            include_logs=include_logs,
            payload=_support_bundle_payload(
                site_id=site_id,
                node_id=node_id,
                diagnostics=diagnostics,
                include_logs=include_logs,
            ),
            created_at=_now(),
        )
        async with self.session_factory() as session:
            await _db_validate_site_and_node(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=node_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _bundle_record(row)

    def get_bundle(self, *, tenant_id: UUID, bundle_id: UUID) -> SupportBundleRecord | None:
        bundle = self._bundles.get(bundle_id)
        if bundle is None or bundle.tenant_id != tenant_id:
            return None
        return bundle

    async def aget_bundle(
        self,
        *,
        tenant_id: UUID,
        bundle_id: UUID,
    ) -> SupportBundleRecord | None:
        if self.session_factory is None:
            return self.get_bundle(tenant_id=tenant_id, bundle_id=bundle_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(SupportBundle).where(
                    SupportBundle.id == bundle_id,
                    SupportBundle.tenant_id == tenant_id,
                )
            )
        row = result.scalar_one_or_none()
        return _bundle_record(row) if row is not None else None

    def list_bundles(self, *, tenant_id: UUID) -> list[SupportBundleRecord]:
        return sorted(
            (bundle for bundle in self._bundles.values() if bundle.tenant_id == tenant_id),
            key=lambda bundle: bundle.created_at,
            reverse=True,
        )

    async def alist_bundles(self, *, tenant_id: UUID) -> list[SupportBundleRecord]:
        if self.session_factory is None:
            return self.list_bundles(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(SupportBundle)
                .where(SupportBundle.tenant_id == tenant_id)
                .order_by(SupportBundle.created_at.desc())
            )
        return [_bundle_record(row) for row in result.scalars().all()]

    def create_session(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        operator_id: str,
        node_id: UUID | None = None,
        started_at: datetime | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> SupportSessionRecord:
        now = started_at or _now()
        session = SupportSessionRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            node_id=node_id,
            operator_id=operator_id,
            status="open",
            started_at=now,
            updated_at=now,
            metadata=_json_object(metadata),
        )
        self._sessions[session.id] = session
        return session

    async def acreate_session(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        operator_id: str,
        node_id: UUID | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> SupportSessionRecord:
        if self.session_factory is None:
            await self._avalidate_resources(
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=node_id,
            )
            return self.create_session(
                tenant_id=tenant_id,
                site_id=site_id,
                operator_id=operator_id,
                node_id=node_id,
                metadata=metadata,
            )
        now = _now()
        row = SupportSession(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            node_id=node_id,
            operator_id=operator_id,
            status="open",
            started_at=now,
            updated_at=now,
            attributes=_json_object(metadata),
        )
        async with self.session_factory() as db_session:
            await _db_validate_site_and_node(
                db_session,
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=node_id,
            )
            db_session.add(row)
            await db_session.commit()
            await db_session.refresh(row)
        return _session_record(row)

    def close_session(
        self,
        session_id: UUID,
        *,
        ended_at: datetime | None = None,
    ) -> SupportSessionRecord:
        session = self._sessions.get(session_id)
        if session is None:
            raise SupportNotFoundError("Support session not found.")
        ended = ended_at or _now()
        closed = replace(
            session,
            status="closed",
            ended_at=ended,
            updated_at=ended,
            billable_duration_minutes=_duration_minutes(session.started_at, ended),
        )
        self._sessions[session_id] = closed
        return closed

    async def aclose_session(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
        ended_at: datetime | None = None,
    ) -> SupportSessionRecord:
        if self.session_factory is None:
            session = self._sessions.get(session_id)
            if session is None or session.tenant_id != tenant_id:
                raise SupportNotFoundError("Support session not found.")
            return self.close_session(session_id, ended_at=ended_at)
        async with self.session_factory() as db_session:
            row = await _db_get(
                db_session,
                SupportSession,
                tenant_id=tenant_id,
                object_id=session_id,
                not_found="Support session not found.",
            )
            ended = ended_at or _now()
            row.status = "closed"
            row.ended_at = ended
            row.updated_at = ended
            row.billable_duration_minutes = _duration_minutes(row.started_at, ended)
            await db_session.commit()
            await db_session.refresh(row)
        return _session_record(row)

    def request_tunnel(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        node_id: UUID,
        transport: str,
        credential_ref: str,
        relay_host: str,
        allowed_ports: Sequence[int],
        expires_at: datetime | None = None,
        dispatch_method: str = "supervisor_poll",
        metadata: Mapping[str, object] | None = None,
    ) -> SupportTunnelRecord:
        _ensure_transport(transport)
        validate_support_tunnel_parameters(relay_host=relay_host, allowed_ports=allowed_ports)
        now = _now()
        tunnel = SupportTunnelRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            node_id=node_id,
            transport=transport,
            status="requested",
            credential_ref=credential_ref,
            credential_ref_hash=_sha256(credential_ref),
            relay_host=relay_host,
            allowed_ports=[int(port) for port in allowed_ports],
            dispatch_method=dispatch_method,
            requested_at=now,
            updated_at=now,
            expires_at=expires_at or now + timedelta(hours=1),
            metadata=_json_object(metadata),
        )
        self._tunnels[tunnel.id] = tunnel
        return tunnel

    async def arequest_tunnel(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        node_id: UUID,
        transport: str,
        credential_ref: str,
        relay_host: str,
        allowed_ports: Sequence[int],
        expires_at: datetime | None = None,
        dispatch_method: str = "supervisor_poll",
        metadata: Mapping[str, object] | None = None,
    ) -> SupportTunnelRecord:
        _ensure_transport(transport)
        validate_support_tunnel_parameters(relay_host=relay_host, allowed_ports=allowed_ports)
        if self.session_factory is None:
            await self._avalidate_resources(
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=node_id,
            )
            return self.request_tunnel(
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=node_id,
                transport=transport,
                credential_ref=credential_ref,
                relay_host=relay_host,
                allowed_ports=allowed_ports,
                expires_at=expires_at,
                dispatch_method=dispatch_method,
                metadata=metadata,
            )
        now = _now()
        row = SupportTunnel(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            node_id=node_id,
            transport=transport,
            status="requested",
            credential_ref=credential_ref,
            credential_ref_hash=_sha256(credential_ref),
            relay_host=relay_host,
            allowed_ports=[int(port) for port in allowed_ports],
            dispatch_method=dispatch_method,
            requested_at=now,
            updated_at=now,
            expires_at=expires_at or now + timedelta(hours=1),
            attributes=_json_object(metadata),
        )
        async with self.session_factory() as db_session:
            await _db_validate_site_and_node(
                db_session,
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=node_id,
            )
            db_session.add(row)
            await db_session.commit()
            await db_session.refresh(row)
        return _tunnel_record(row)

    def revoke_tunnel(
        self,
        tunnel_id: UUID,
        *,
        reason: str | None = None,
    ) -> SupportTunnelRecord:
        tunnel = self._tunnels.get(tunnel_id)
        if tunnel is None:
            raise SupportNotFoundError("Support tunnel not found.")
        now = _now()
        revoked = replace(
            tunnel,
            status="revoked",
            revoked_at=now,
            updated_at=now,
            revocation_reason=reason,
        )
        self._tunnels[tunnel_id] = revoked
        return revoked

    async def arevoke_tunnel(
        self,
        *,
        tenant_id: UUID,
        tunnel_id: UUID,
        reason: str | None = None,
    ) -> SupportTunnelRecord:
        if self.session_factory is None:
            tunnel = self._tunnels.get(tunnel_id)
            if tunnel is None or tunnel.tenant_id != tenant_id:
                raise SupportNotFoundError("Support tunnel not found.")
            return self.revoke_tunnel(tunnel_id, reason=reason)
        async with self.session_factory() as db_session:
            row = await _db_get(
                db_session,
                SupportTunnel,
                tenant_id=tenant_id,
                object_id=tunnel_id,
                not_found="Support tunnel not found.",
            )
            now = _now()
            row.status = "revoked"
            row.revoked_at = now
            row.updated_at = now
            row.revocation_reason = reason
            await db_session.commit()
            await db_session.refresh(row)
        return _tunnel_record(row)

    def open_break_glass(
        self,
        *,
        reason: str,
        scope: Mapping[str, object],
        actor_id: str,
        approver_id: str,
        tenant_id: UUID | None = None,
        audit_payload: Mapping[str, object] | None = None,
    ) -> BreakGlassAccessRecord:
        now = _now()
        record = BreakGlassAccessRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            reason=reason,
            scope=_json_object(scope),
            actor_id=actor_id,
            approver_id=approver_id,
            started_at=now,
            updated_at=now,
            audit_payload=_json_object(audit_payload),
        )
        self._break_glass_records[record.id] = record
        return record

    async def aopen_break_glass(
        self,
        *,
        tenant_id: UUID,
        reason: str,
        scope: Mapping[str, object],
        actor_id: str,
        approver_id: str,
        audit_payload: Mapping[str, object] | None = None,
    ) -> BreakGlassAccessRecord:
        if self.session_factory is None:
            return self.open_break_glass(
                tenant_id=tenant_id,
                reason=reason,
                scope=scope,
                actor_id=actor_id,
                approver_id=approver_id,
                audit_payload=audit_payload,
            )
        now = _now()
        row = BreakGlassAccessRecordRow(
            id=uuid4(),
            tenant_id=tenant_id,
            reason=reason,
            scope=_json_object(scope),
            actor_id=actor_id,
            approver_id=approver_id,
            started_at=now,
            updated_at=now,
            audit_payload=_json_object(audit_payload),
        )
        async with self.session_factory() as db_session:
            db_session.add(row)
            await db_session.commit()
            await db_session.refresh(row)
        return _break_glass_record(row)

    def close_break_glass(
        self,
        record_id: UUID,
        *,
        closure_notes: str,
    ) -> BreakGlassAccessRecord:
        record = self._break_glass_records.get(record_id)
        if record is None:
            raise SupportNotFoundError("Break-glass record not found.")
        now = _now()
        closed = replace(
            record,
            ended_at=now,
            updated_at=now,
            closure_notes=closure_notes,
        )
        self._break_glass_records[record_id] = closed
        return closed

    async def aclose_break_glass(
        self,
        *,
        tenant_id: UUID,
        record_id: UUID,
        closure_notes: str,
    ) -> BreakGlassAccessRecord:
        if self.session_factory is None:
            record = self._break_glass_records.get(record_id)
            if record is None or record.tenant_id != tenant_id:
                raise SupportNotFoundError("Break-glass record not found.")
            return self.close_break_glass(record_id, closure_notes=closure_notes)
        async with self.session_factory() as db_session:
            row = await _db_get(
                db_session,
                BreakGlassAccessRecordRow,
                tenant_id=tenant_id,
                object_id=record_id,
                not_found="Break-glass record not found.",
            )
            now = _now()
            row.ended_at = now
            row.updated_at = now
            row.closure_notes = closure_notes
            await db_session.commit()
            await db_session.refresh(row)
        return _break_glass_record(row)

    def run_onboarding_checks(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        pack_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> OnboardingCheckRunRecord:
        run = OnboardingCheckRunRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            pack_id=pack_id,
            checks=[replace(check) for check in DEFAULT_ONBOARDING_CHECKS],
            metadata=_json_object(metadata),
            created_at=_now(),
        )
        self._onboarding_runs[run.id] = run
        return run

    async def arun_onboarding_checks(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        pack_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> OnboardingCheckRunRecord:
        if self.session_factory is None:
            await self._avalidate_resources(
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=None,
            )
            return self.run_onboarding_checks(
                tenant_id=tenant_id,
                site_id=site_id,
                pack_id=pack_id,
                metadata=metadata,
            )
        run = OnboardingCheckRun(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            pack_id=pack_id,
            checks=[_check_payload(check) for check in DEFAULT_ONBOARDING_CHECKS],
            attributes=_json_object(metadata),
            created_at=_now(),
        )
        async with self.session_factory() as db_session:
            await _db_validate_site_and_node(
                db_session,
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=None,
            )
            db_session.add(run)
            await db_session.commit()
            await db_session.refresh(run)
        return _onboarding_run_record(run)

    def list_onboarding_checks(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> OnboardingCheckRunRecord:
        runs = [
            run
            for run in self._onboarding_runs.values()
            if run.tenant_id == tenant_id and run.site_id == site_id
        ]
        if not runs:
            return self.run_onboarding_checks(tenant_id=tenant_id, site_id=site_id)
        return max(runs, key=lambda run: run.created_at)

    async def alist_onboarding_checks(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> OnboardingCheckRunRecord:
        if self.session_factory is None:
            await self._avalidate_resources(
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=None,
            )
            return self.list_onboarding_checks(tenant_id=tenant_id, site_id=site_id)
        async with self.session_factory() as db_session:
            result = await db_session.execute(
                select(OnboardingCheckRun)
                .where(
                    OnboardingCheckRun.tenant_id == tenant_id,
                    OnboardingCheckRun.site_id == site_id,
                )
                .order_by(OnboardingCheckRun.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
        if row is not None:
            return _onboarding_run_record(row)
        return await self.arun_onboarding_checks(tenant_id=tenant_id, site_id=site_id)

    async def _avalidate_resources(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        node_id: UUID | None,
    ) -> None:
        if self.resource_validator is None:
            return
        await self.resource_validator.validate_site(tenant_id=tenant_id, site_id=site_id)
        if node_id is not None:
            await self.resource_validator.validate_node(
                tenant_id=tenant_id,
                site_id=site_id,
                node_id=node_id,
            )


async def _db_get[TableRow](
    session: AsyncSession,
    model: type[TableRow],
    *,
    tenant_id: UUID,
    object_id: UUID,
    not_found: str,
) -> TableRow:
    model_any = cast(Any, model)
    result = await session.execute(
        select(model).where(
            model_any.id == object_id,
            model_any.tenant_id == tenant_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise SupportNotFoundError(not_found)
    return row


async def _db_validate_site_and_node(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    site_id: UUID,
    node_id: UUID | None,
) -> None:
    result = await session.execute(
        select(Site).where(Site.id == site_id, Site.tenant_id == tenant_id)
    )
    if result.scalar_one_or_none() is None:
        raise SupportNotFoundError("Site not found.")
    if node_id is not None:
        await _db_validate_node(session, tenant_id=tenant_id, site_id=site_id, node_id=node_id)


async def _db_validate_node(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    site_id: UUID,
    node_id: UUID,
) -> None:
    deployment_result = await session.execute(
        select(DeploymentNode).where(
            DeploymentNode.id == node_id,
            DeploymentNode.tenant_id == tenant_id,
        )
    )
    deployment_node = deployment_result.scalar_one_or_none()
    if isinstance(deployment_node, DeploymentNode):
        if deployment_node.edge_node_id is None:
            return
        edge_result = await session.execute(
            select(EdgeNode).where(
                EdgeNode.id == deployment_node.edge_node_id,
                EdgeNode.site_id == site_id,
            )
        )
        if isinstance(edge_result.scalar_one_or_none(), EdgeNode):
            return
        raise SupportNotFoundError("Node not found.")

    edge_result = await session.execute(
        select(EdgeNode).where(EdgeNode.id == node_id, EdgeNode.site_id == site_id)
    )
    if not isinstance(edge_result.scalar_one_or_none(), EdgeNode):
        raise SupportNotFoundError("Node not found.")


def _support_bundle_payload(
    *,
    site_id: UUID,
    node_id: UUID | None,
    diagnostics: Mapping[str, object] | None,
    include_logs: bool,
) -> JsonObject:
    return {
        "site_id": str(site_id),
        "node_id": str(node_id) if node_id is not None else None,
        "include_logs": include_logs,
        "summaries": {
            "master": {"status": "unknown"},
            "edge": {"status": "unknown"},
            "camera": {"status": "unknown"},
            "runtime": {"status": "unknown"},
            "link": {"status": "unknown"},
            "evidence": {"status": "unknown"},
            "configuration": {"status": "unknown"},
        },
        "diagnostics": _redact_json(_json_object(diagnostics)),
        "logs": {"included": include_logs, "entries": []},
    }


def _redact_json(value: object) -> object:
    if isinstance(value, Mapping):
        redacted: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if _is_sensitive_key(key):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_json(raw_value)
        return redacted
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return _redact_url_secret(value)
    return value


def _redact_url_secret(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc and parsed.password is not None:
        username = parsed.username or ""
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port is not None else ""
        userinfo = f"{username}:****@" if username else "****@"
        return urlunsplit(
            (
                parsed.scheme,
                f"{userinfo}{host}{port}",
                parsed.path,
                parsed.query,
                parsed.fragment,
            )
        )
    return re.sub(r"(Bearer|Token)\s+[A-Za-z0-9_.:-]+", r"\1 [redacted]", value)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def _ensure_transport(transport: str) -> None:
    if transport not in SUPPORTED_TRANSPORTS:
        raise SupportError(f"Unsupported support tunnel transport: {transport}")


def _duration_minutes(started_at: datetime, ended_at: datetime) -> int:
    return max(0, int((ended_at - started_at).total_seconds() // 60))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_object(value: Mapping[str, object] | None) -> JsonObject:
    return {str(key): item for key, item in (value or {}).items()}


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _bundle_record(row: SupportBundle) -> SupportBundleRecord:
    return SupportBundleRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        site_id=row.site_id,
        node_id=row.node_id,
        pack_id=row.pack_id,
        include_logs=row.include_logs,
        payload=dict(row.payload),
        created_at=row.created_at,
    )


def _session_record(row: SupportSession) -> SupportSessionRecord:
    return SupportSessionRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        site_id=row.site_id,
        node_id=row.node_id,
        operator_id=row.operator_id,
        status=row.status,
        started_at=row.started_at,
        ended_at=row.ended_at,
        billable_duration_minutes=row.billable_duration_minutes,
        usage_meter_key=row.usage_meter_key,
        metadata=dict(row.attributes),
        updated_at=row.updated_at,
    )


def _tunnel_record(row: SupportTunnel) -> SupportTunnelRecord:
    return SupportTunnelRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        site_id=row.site_id,
        node_id=row.node_id,
        transport=row.transport,
        status=row.status,
        credential_ref=row.credential_ref,
        credential_ref_hash=row.credential_ref_hash,
        relay_host=row.relay_host,
        allowed_ports=[int(port) for port in row.allowed_ports],
        dispatch_method=row.dispatch_method,
        requested_at=row.requested_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        revocation_reason=row.revocation_reason,
        metadata=dict(row.attributes),
        updated_at=row.updated_at,
    )


def _break_glass_record(row: BreakGlassAccessRecordRow) -> BreakGlassAccessRecord:
    return BreakGlassAccessRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        reason=row.reason,
        scope=dict(row.scope),
        actor_id=row.actor_id,
        approver_id=row.approver_id,
        started_at=row.started_at,
        ended_at=row.ended_at,
        closure_notes=row.closure_notes,
        audit_payload=dict(row.audit_payload),
        updated_at=row.updated_at,
    )


def _onboarding_run_record(row: OnboardingCheckRun) -> OnboardingCheckRunRecord:
    return OnboardingCheckRunRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        site_id=row.site_id,
        pack_id=row.pack_id,
        checks=[_check_record(check) for check in row.checks],
        metadata=dict(row.attributes),
        created_at=row.created_at,
    )


def _check_record(payload: Mapping[str, object]) -> OnboardingCheck:
    details_value = payload.get("details")
    details = _json_object(details_value) if isinstance(details_value, Mapping) else {}
    return OnboardingCheck(
        key=str(payload["key"]),
        label=str(payload["label"]),
        status=str(payload["status"]),
        details=details,
    )


def _check_payload(check: OnboardingCheck) -> JsonObject:
    return {
        "key": check.key,
        "label": check.label,
        "status": check.status,
        "details": check.details,
    }
