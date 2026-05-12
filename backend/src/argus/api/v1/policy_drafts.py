from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from argus.api.contracts import PolicyDraftCreate, PolicyDraftResponse, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/policy-drafts", tags=["policy-drafts"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.post("", response_model=PolicyDraftResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_draft(
    payload: PolicyDraftCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> PolicyDraftResponse:
    return await services.policy_drafts.create_draft(tenant_context, payload)


@router.get("/{draft_id}", response_model=PolicyDraftResponse)
async def get_policy_draft(
    draft_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> PolicyDraftResponse:
    return await services.policy_drafts.get_draft(tenant_context, draft_id)


@router.post("/{draft_id}/approve", response_model=PolicyDraftResponse)
async def approve_policy_draft(
    draft_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> PolicyDraftResponse:
    return await services.policy_drafts.approve_draft(tenant_context, draft_id)


@router.post("/{draft_id}/reject", response_model=PolicyDraftResponse)
async def reject_policy_draft(
    draft_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> PolicyDraftResponse:
    return await services.policy_drafts.reject_draft(tenant_context, draft_id)


@router.post("/{draft_id}/apply", response_model=PolicyDraftResponse)
async def apply_policy_draft(
    draft_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> PolicyDraftResponse:
    return await services.policy_drafts.apply_draft(tenant_context, draft_id)
