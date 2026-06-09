from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from argus.api.contracts import (
    ManagedTenantCreate,
    ManagedTenantResponse,
    ManagedUserCreate,
    ManagedUserPatch,
    ManagedUserResetPassword,
    ManagedUserResponse,
)
from argus.api.dependencies import get_app_services
from argus.core.security import AuthenticatedUser, CurrentUserDependency, enforce_role
from argus.models.enums import RoleEnum
from argus.models.tables import Tenant, User
from argus.services.app import AppServices

router = APIRouter(tags=["users"])

ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantQuery = Annotated[UUID | None, Query(alias="tenant_id")]


@router.get("/api/v1/tenants", response_model=list[ManagedTenantResponse])
async def list_managed_tenants(
    current_user: CurrentUserDependency,
    services: ServicesDependency,
) -> list[ManagedTenantResponse]:
    _require_superadmin(current_user)
    rows = await services.users.list_tenants()
    return [_tenant_response(row) for row in rows]


@router.post(
    "/api/v1/tenants",
    response_model=ManagedTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_managed_tenant(
    payload: ManagedTenantCreate,
    current_user: CurrentUserDependency,
    services: ServicesDependency,
) -> ManagedTenantResponse:
    _require_superadmin(current_user)
    row = await services.users.create_tenant(
        name=payload.name,
        slug=payload.slug,
        actor_subject=current_user.subject,
    )
    return _tenant_response(row)


@router.get("/api/v1/users", response_model=list[ManagedUserResponse])
async def list_managed_users(
    current_user: CurrentUserDependency,
    services: ServicesDependency,
    tenant_id: TenantQuery = None,
) -> list[ManagedUserResponse]:
    target_tenant_id = await _target_tenant_id(
        current_user=current_user,
        services=services,
        requested_tenant_id=tenant_id,
        allow_all_for_superadmin=True,
    )
    rows = await services.users.list_users(tenant_id=target_tenant_id)
    return [_user_response(row) for row in rows]


@router.post(
    "/api/v1/users",
    response_model=ManagedUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_managed_user(
    payload: ManagedUserCreate,
    current_user: CurrentUserDependency,
    services: ServicesDependency,
) -> ManagedUserResponse:
    target_tenant_id = await _target_tenant_id(
        current_user=current_user,
        services=services,
        requested_tenant_id=payload.tenant_id,
        allow_all_for_superadmin=False,
    )
    if target_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="tenant_id is required for superadmin user creation.",
        )
    row = await services.users.create_user(
        tenant_id=target_tenant_id,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        temporary_password=payload.temporary_password,
        actor_subject=current_user.subject,
    )
    return _user_response(row)


@router.patch("/api/v1/users/{user_id}", response_model=ManagedUserResponse)
async def update_managed_user(
    user_id: UUID,
    payload: ManagedUserPatch,
    current_user: CurrentUserDependency,
    services: ServicesDependency,
) -> ManagedUserResponse:
    target_tenant_id = await _target_tenant_id(
        current_user=current_user,
        services=services,
        requested_tenant_id=None,
        allow_all_for_superadmin=True,
    )
    row = await services.users.update_user(
        tenant_id=target_tenant_id,
        user_id=user_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        enabled=payload.enabled,
        actor_subject=current_user.subject,
    )
    return _user_response(row)


@router.post("/api/v1/users/{user_id}/reset-password", response_model=ManagedUserResponse)
async def reset_managed_user_password(
    user_id: UUID,
    payload: ManagedUserResetPassword,
    current_user: CurrentUserDependency,
    services: ServicesDependency,
) -> ManagedUserResponse:
    target_tenant_id = await _target_tenant_id(
        current_user=current_user,
        services=services,
        requested_tenant_id=None,
        allow_all_for_superadmin=True,
    )
    row = await services.users.reset_user_password(
        tenant_id=target_tenant_id,
        user_id=user_id,
        temporary_password=payload.temporary_password,
        actor_subject=current_user.subject,
    )
    return _user_response(row)


async def _target_tenant_id(
    *,
    current_user: AuthenticatedUser,
    services: AppServices,
    requested_tenant_id: UUID | None,
    allow_all_for_superadmin: bool,
) -> UUID | None:
    if current_user.is_superadmin:
        return requested_tenant_id if requested_tenant_id is not None else (
            None if allow_all_for_superadmin else requested_tenant_id
        )
    enforce_role(current_user, RoleEnum.ADMIN)
    tenant_context = await services.tenancy.resolve_context(user=current_user)
    if requested_tenant_id is not None and requested_tenant_id != tenant_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admins cannot manage users in another tenant.",
        )
    return tenant_context.tenant_id


def _require_superadmin(current_user: AuthenticatedUser) -> None:
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform superadmin role is required.",
        )


def _tenant_response(row: Tenant) -> ManagedTenantResponse:
    return ManagedTenantResponse(
        id=row.id,
        name=row.name,
        slug=row.slug,
        created_at=row.created_at,
    )


def _user_response(row: User) -> ManagedUserResponse:
    return ManagedUserResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        email=row.email,
        first_name=getattr(row, "first_name", None),
        last_name=getattr(row, "last_name", None),
        oidc_sub=row.oidc_sub,
        role=row.role,
        enabled=getattr(row, "enabled", True),
        created_at=row.created_at,
    )
