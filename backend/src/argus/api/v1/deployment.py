from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from argus.api.contracts import (
    DeploymentNodeResponse,
    SupervisorServiceReportCreate,
    SupervisorServiceReportResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
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
    "/supervisors/{supervisor_id}/service-reports",
    response_model=SupervisorServiceReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_supervisor_service_report(
    supervisor_id: str,
    payload: SupervisorServiceReportCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> SupervisorServiceReportResponse:
    return await services.deployment.record_service_report(
        tenant_id=tenant_context.tenant_id,
        supervisor_id=supervisor_id,
        payload=payload,
    )
