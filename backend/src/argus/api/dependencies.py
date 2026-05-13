from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query, Request, WebSocket, status

from argus.api.contracts import TenantContext
from argus.core.security import (
    AuthenticatedUser,
    CurrentUserDependency,
    enforce_role,
    get_current_media_user,
    get_current_websocket_user,
)
from argus.models.enums import RoleEnum
from argus.services.app import AppServices


def get_app_services(request: Request) -> AppServices:
    return request.app.state.services  # type: ignore[no-any-return]


def get_websocket_services(websocket: WebSocket) -> AppServices:
    return websocket.app.state.services  # type: ignore[no-any-return]


def _parse_explicit_tenant_id(raw_tenant_id: str | None) -> UUID | None:
    if raw_tenant_id is None:
        return None
    return UUID(raw_tenant_id)


async def get_tenant_context(
    current_user: CurrentUserDependency,
    services: Annotated[AppServices, Depends(get_app_services)],
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
) -> TenantContext:
    return await services.tenancy.resolve_context(
        user=current_user,
        explicit_tenant_id=_parse_explicit_tenant_id(x_tenant_id),
    )


async def get_media_tenant_context(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_media_user)],
    services: Annotated[AppServices, Depends(get_app_services)],
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    tenant_id: Annotated[str | None, Query()] = None,
) -> TenantContext:
    return await services.tenancy.resolve_context(
        user=current_user,
        explicit_tenant_id=_parse_explicit_tenant_id(x_tenant_id or tenant_id),
    )


async def get_websocket_tenant_context(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_websocket_user)],
    services: Annotated[AppServices, Depends(get_websocket_services)],
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
) -> TenantContext:
    return await services.tenancy.resolve_context(
        user=current_user,
        explicit_tenant_id=_parse_explicit_tenant_id(x_tenant_id),
    )


async def get_supervisor_or_admin_tenant_context(
    request: Request,
    services: Annotated[AppServices, Depends(get_app_services)],
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    supervisor_id: str | None = None,
) -> TenantContext:
    token = _bearer_token(request.headers.get("Authorization"))
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    try:
        user = await request.app.state.security.authenticate_request(request)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
    else:
        enforce_role(user, RoleEnum.ADMIN)
        return await services.tenancy.resolve_context(
            user=user,
            explicit_tenant_id=_parse_explicit_tenant_id(x_tenant_id),
        )

    try:
        return await services.deployment.authenticate_supervisor_credential(
            credential_material=token,
            supervisor_id=supervisor_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid supervisor credential.",
        ) from exc


SupervisorOrAdminTenantDependency = Annotated[
    TenantContext,
    Depends(get_supervisor_or_admin_tenant_context),
]


def _bearer_token(authorization_header: str | None) -> str | None:
    if authorization_header is None:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()
