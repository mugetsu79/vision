from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from argus.api.contracts import IncidentResponse, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[IncidentResponse]:
    return await services.incidents.list_incidents(tenant_context)
