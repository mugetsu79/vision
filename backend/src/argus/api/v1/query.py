from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from argus.api.contracts import QueryRequest, QueryResponse, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/query", tags=["query"])
OperatorUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.OPERATOR))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.post("", response_model=QueryResponse)
async def resolve_query(
    payload: QueryRequest,
    current_user: OperatorUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> QueryResponse:
    return await services.query.resolve_query(tenant_context, payload)
