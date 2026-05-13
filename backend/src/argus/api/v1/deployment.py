from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from argus.api.contracts import (
    DeploymentNodeResponse,
    DeploymentSupportBundleResponse,
    NodeCredentialRevokeResponse,
    NodePairingClaim,
    NodePairingClaimResponse,
    NodePairingSessionCreate,
    NodePairingSessionResponse,
    SupervisorServiceReportCreate,
    SupervisorServiceReportResponse,
    TenantContext,
)
from argus.api.dependencies import (
    SupervisorOrAdminTenantDependency,
    get_app_services,
    get_tenant_context,
)
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/deployment", tags=["deployment"])
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("/nodes", response_model=list[DeploymentNodeResponse])
async def list_deployment_nodes(
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[DeploymentNodeResponse]:
    return await services.deployment.list_nodes(tenant_id=tenant_context.tenant_id)


@router.post(
    "/pairing-sessions",
    response_model=NodePairingSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pairing_session(
    payload: NodePairingSessionCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> NodePairingSessionResponse:
    try:
        return await services.deployment.create_pairing_session(
            tenant_id=tenant_context.tenant_id,
            payload=payload,
            actor_subject=current_user.subject,
        )
    except ValueError as exc:
        raise _deployment_http_error(exc) from exc


@router.get(
    "/pairing-sessions/{session_id}",
    response_model=NodePairingSessionResponse,
)
async def get_pairing_session(
    session_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> NodePairingSessionResponse:
    try:
        return await services.deployment.get_pairing_session(
            tenant_id=tenant_context.tenant_id,
            session_id=session_id,
        )
    except ValueError as exc:
        raise _deployment_http_error(exc) from exc


@router.post(
    "/pairing-sessions/{session_id}/claim",
    response_model=NodePairingClaimResponse,
)
async def claim_pairing_session(
    session_id: UUID,
    payload: NodePairingClaim,
    services: ServicesDependency,
) -> NodePairingClaimResponse:
    try:
        return await services.deployment.claim_pairing_session(
            session_id=session_id,
            payload=payload,
        )
    except ValueError as exc:
        raise _deployment_http_error(exc) from exc


@router.post(
    "/nodes/{node_id}/credentials/revoke",
    response_model=NodeCredentialRevokeResponse,
)
async def revoke_node_credentials(
    node_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> NodeCredentialRevokeResponse:
    try:
        return await services.deployment.revoke_node_credentials(
            tenant_id=tenant_context.tenant_id,
            node_id=node_id,
            actor_subject=current_user.subject,
        )
    except ValueError as exc:
        raise _deployment_http_error(exc) from exc


@router.get(
    "/nodes/{node_id}/support-bundle",
    response_model=DeploymentSupportBundleResponse,
)
async def get_node_support_bundle(
    node_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> DeploymentSupportBundleResponse:
    try:
        return await services.deployment.get_support_bundle(
            tenant_id=tenant_context.tenant_id,
            node_id=node_id,
        )
    except ValueError as exc:
        raise _deployment_http_error(exc) from exc


@router.post(
    "/supervisors/{supervisor_id}/service-reports",
    response_model=SupervisorServiceReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_supervisor_service_report(
    supervisor_id: str,
    payload: SupervisorServiceReportCreate,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> SupervisorServiceReportResponse:
    try:
        return await services.deployment.record_service_report(
            tenant_id=tenant_context.tenant_id,
            supervisor_id=supervisor_id,
            payload=payload,
            authenticated_node_id=_authenticated_deployment_node_id(tenant_context),
        )
    except ValueError as exc:
        raise _deployment_http_error(exc) from exc


def _deployment_http_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    normalized = detail.lower()
    if "not found" in normalized:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    if "already consumed" in normalized or "expired" in normalized:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _authenticated_deployment_node_id(tenant_context: TenantContext) -> UUID | None:
    if tenant_context.user.claims.get("auth_type") != "supervisor_node_credential":
        return None
    raw_node_id = tenant_context.user.claims.get("deployment_node_id")
    if not isinstance(raw_node_id, str):
        return None
    try:
        return UUID(raw_node_id)
    except ValueError:
        return None
