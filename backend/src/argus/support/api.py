from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from argus.api.contracts import TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices
from argus.support.contracts import (
    BreakGlassAccessRecord,
    JsonObject,
    OnboardingCheck,
    OnboardingCheckRunRecord,
    SupportBundleRecord,
    SupportSessionRecord,
    SupportTunnelRecord,
)
from argus.support.service import SupportError, SupportNotFoundError

router = APIRouter(prefix="/api/v1/support", tags=["support"])
HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
OperatorUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.OPERATOR))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]


class SupportBundleCreate(BaseModel):
    site_id: UUID
    node_id: UUID | None = None
    include_logs: bool = False
    pack_id: str | None = Field(default=None, max_length=128)
    diagnostics: dict[str, object] = Field(default_factory=dict)


class SupportSessionCreate(BaseModel):
    site_id: UUID
    node_id: UUID | None = None
    operator_id: str | None = Field(default=None, min_length=1, max_length=160)
    metadata: dict[str, object] = Field(default_factory=dict)


class SupportSessionClose(BaseModel):
    ended_at: datetime | None = None


class SupportTunnelCreate(BaseModel):
    site_id: UUID
    node_id: UUID
    transport: Literal["ssh_reverse"] = "ssh_reverse"
    credential_ref: str = Field(min_length=1, max_length=256)
    relay_host: str = Field(min_length=1, max_length=255)
    allowed_ports: list[int] = Field(min_length=1)
    expires_at: datetime | None = None
    dispatch_method: str = Field(default="supervisor_poll", max_length=64)
    metadata: dict[str, object] = Field(default_factory=dict)


class SupportTunnelRevoke(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class BreakGlassOpen(BaseModel):
    reason: str = Field(min_length=1, max_length=255)
    scope: dict[str, object] = Field(default_factory=dict)
    actor_id: str = Field(min_length=1, max_length=160)
    approver_id: str = Field(min_length=1, max_length=160)
    audit_payload: dict[str, object] = Field(default_factory=dict)


class BreakGlassClose(BaseModel):
    closure_notes: str = Field(min_length=1, max_length=500)


class OnboardingCheckRunCreate(BaseModel):
    site_id: UUID
    pack_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, object] = Field(default_factory=dict)


class SupportBundleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID
    node_id: UUID | None = None
    pack_id: str | None = None
    include_logs: bool
    payload: JsonObject
    created_at: str


class SupportBundleListResponse(BaseModel):
    items: list[SupportBundleResponse] = Field(default_factory=list)


@router.get("/bundles", response_model=SupportBundleListResponse)
async def get_support_bundles(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> SupportBundleListResponse:
    bundles = await services.support.alist_bundles(tenant_id=tenant_context.tenant_id)
    return SupportBundleListResponse(
        items=[SupportBundleResponse.model_validate(_bundle_payload(bundle)) for bundle in bundles]
    )


@router.post("/bundles", status_code=status.HTTP_201_CREATED)
async def post_support_bundle(
    payload: SupportBundleCreate,
    current_user: OperatorUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        bundle = await services.support.agenerate_bundle(
            tenant_id=tenant_context.tenant_id,
            site_id=payload.site_id,
            node_id=payload.node_id,
            include_logs=payload.include_logs,
            pack_id=payload.pack_id,
            diagnostics=payload.diagnostics,
        )
    except SupportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _bundle_payload(bundle)


@router.get("/bundles/{bundle_id}")
async def get_support_bundle(
    bundle_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    bundle = await services.support.aget_bundle(
        tenant_id=tenant_context.tenant_id,
        bundle_id=bundle_id,
    )
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support bundle not found.",
        )
    return _bundle_payload(bundle)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def post_support_session(
    payload: SupportSessionCreate,
    current_user: OperatorUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        session = await services.support.acreate_session(
            tenant_id=tenant_context.tenant_id,
            site_id=payload.site_id,
            node_id=payload.node_id,
            operator_id=payload.operator_id or current_user.subject,
            metadata=payload.metadata,
        )
    except SupportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _session_payload(session)


@router.patch("/sessions/{session_id}")
async def patch_support_session(
    session_id: UUID,
    payload: SupportSessionClose,
    current_user: OperatorUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        session = await services.support.aclose_session(
            tenant_id=tenant_context.tenant_id,
            session_id=session_id,
            ended_at=payload.ended_at,
        )
    except SupportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _session_payload(session)


@router.post("/tunnels", status_code=status.HTTP_201_CREATED)
async def post_support_tunnel(
    payload: SupportTunnelCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        tunnel = await services.support.arequest_tunnel(
            tenant_id=tenant_context.tenant_id,
            site_id=payload.site_id,
            node_id=payload.node_id,
            transport=payload.transport,
            credential_ref=payload.credential_ref,
            relay_host=payload.relay_host,
            allowed_ports=payload.allowed_ports,
            expires_at=payload.expires_at,
            dispatch_method=payload.dispatch_method,
            metadata=payload.metadata,
        )
    except SupportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (SupportError, ValueError) as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=str(exc),
        ) from exc
    return _tunnel_payload(tunnel)


@router.post("/tunnels/{tunnel_id}/revoke")
async def revoke_support_tunnel(
    tunnel_id: UUID,
    payload: SupportTunnelRevoke,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        tunnel = await services.support.arevoke_tunnel(
            tenant_id=tenant_context.tenant_id,
            tunnel_id=tunnel_id,
            reason=payload.reason,
        )
    except SupportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _tunnel_payload(tunnel)


@router.post("/break-glass", status_code=status.HTTP_201_CREATED)
async def open_break_glass(
    payload: BreakGlassOpen,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    record = await services.support.aopen_break_glass(
        tenant_id=tenant_context.tenant_id,
        reason=payload.reason,
        scope=payload.scope,
        actor_id=payload.actor_id,
        approver_id=payload.approver_id,
        audit_payload=payload.audit_payload,
    )
    return _break_glass_payload(record)


@router.post("/break-glass/{record_id}/close")
async def close_break_glass(
    record_id: UUID,
    payload: BreakGlassClose,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        record = await services.support.aclose_break_glass(
            tenant_id=tenant_context.tenant_id,
            record_id=record_id,
            closure_notes=payload.closure_notes,
        )
    except SupportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _break_glass_payload(record)


@router.get("/onboarding-checks")
async def get_onboarding_checks(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    site_id: Annotated[UUID, Query()],
) -> JsonObject:
    run = await services.support.alist_onboarding_checks(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
    )
    return _onboarding_run_payload(run)


@router.post("/onboarding-checks/run", status_code=status.HTTP_201_CREATED)
async def run_onboarding_checks(
    payload: OnboardingCheckRunCreate,
    current_user: OperatorUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        run = await services.support.arun_onboarding_checks(
            tenant_id=tenant_context.tenant_id,
            site_id=payload.site_id,
            pack_id=payload.pack_id,
            metadata=payload.metadata,
        )
    except SupportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _onboarding_run_payload(run)


def _bundle_payload(bundle: SupportBundleRecord) -> JsonObject:
    return {
        "id": str(bundle.id),
        "tenant_id": str(bundle.tenant_id),
        "site_id": str(bundle.site_id),
        "node_id": str(bundle.node_id) if bundle.node_id is not None else None,
        "pack_id": bundle.pack_id,
        "include_logs": bundle.include_logs,
        "payload": bundle.payload,
        "created_at": bundle.created_at.isoformat(),
    }


def _session_payload(session: SupportSessionRecord) -> JsonObject:
    return {
        "id": str(session.id),
        "tenant_id": str(session.tenant_id),
        "site_id": str(session.site_id),
        "node_id": str(session.node_id) if session.node_id is not None else None,
        "operator_id": session.operator_id,
        "status": session.status,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at is not None else None,
        "billable_duration_minutes": session.billable_duration_minutes,
        "usage_meter_key": session.usage_meter_key,
        "metadata": session.metadata,
        "updated_at": session.updated_at.isoformat(),
    }


def _tunnel_payload(tunnel: SupportTunnelRecord) -> JsonObject:
    return {
        "id": str(tunnel.id),
        "tenant_id": str(tunnel.tenant_id),
        "site_id": str(tunnel.site_id),
        "node_id": str(tunnel.node_id),
        "transport": tunnel.transport,
        "status": tunnel.status,
        "credential_ref": tunnel.credential_ref,
        "credential_ref_hash": tunnel.credential_ref_hash,
        "relay_host": tunnel.relay_host,
        "allowed_ports": tunnel.allowed_ports,
        "dispatch_method": tunnel.dispatch_method,
        "requested_at": tunnel.requested_at.isoformat(),
        "expires_at": tunnel.expires_at.isoformat() if tunnel.expires_at is not None else None,
        "revoked_at": tunnel.revoked_at.isoformat() if tunnel.revoked_at is not None else None,
        "revocation_reason": tunnel.revocation_reason,
        "metadata": tunnel.metadata,
        "updated_at": tunnel.updated_at.isoformat(),
        "private_key": None,
    }


def _break_glass_payload(record: BreakGlassAccessRecord) -> JsonObject:
    return {
        "id": str(record.id),
        "tenant_id": str(record.tenant_id) if record.tenant_id is not None else None,
        "reason": record.reason,
        "scope": record.scope,
        "actor_id": record.actor_id,
        "approver_id": record.approver_id,
        "started_at": record.started_at.isoformat(),
        "ended_at": record.ended_at.isoformat() if record.ended_at is not None else None,
        "closure_notes": record.closure_notes,
        "audit_payload": record.audit_payload,
        "updated_at": record.updated_at.isoformat(),
    }


def _onboarding_run_payload(run: OnboardingCheckRunRecord) -> JsonObject:
    return {
        "id": str(run.id),
        "tenant_id": str(run.tenant_id),
        "site_id": str(run.site_id),
        "pack_id": run.pack_id,
        "checks": [_check_payload(check) for check in run.checks],
        "metadata": run.metadata,
        "created_at": run.created_at.isoformat(),
    }


def _check_payload(check: OnboardingCheck) -> JsonObject:
    return {
        "key": check.key,
        "label": check.label,
        "status": check.status,
        "details": check.details,
    }
