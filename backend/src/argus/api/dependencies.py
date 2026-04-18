from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request, WebSocket

from argus.api.contracts import TenantContext
from argus.core.security import (
    AuthenticatedUser,
    CurrentUserDependency,
    get_current_websocket_user,
)
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


async def get_websocket_tenant_context(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_websocket_user)],
    services: Annotated[AppServices, Depends(get_websocket_services)],
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
) -> TenantContext:
    return await services.tenancy.resolve_context(
        user=current_user,
        explicit_tenant_id=_parse_explicit_tenant_id(x_tenant_id),
    )
