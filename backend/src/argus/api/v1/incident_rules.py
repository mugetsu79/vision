from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from argus.api.contracts import (
    IncidentRuleCreate,
    IncidentRuleResponse,
    IncidentRuleUpdate,
    IncidentRuleValidationRequest,
    IncidentRuleValidationResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(
    prefix="/api/v1/cameras/{camera_id}/incident-rules",
    tags=["incident-rules"],
)
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=list[IncidentRuleResponse])
async def list_incident_rules(
    camera_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[IncidentRuleResponse]:
    return await services.incident_rules.list_rules(tenant_context, camera_id)


@router.post(
    "",
    response_model=IncidentRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident_rule(
    camera_id: UUID,
    payload: IncidentRuleCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> IncidentRuleResponse:
    return await services.incident_rules.create_rule(tenant_context, camera_id, payload)


@router.post("/validate", response_model=IncidentRuleValidationResponse)
async def validate_incident_rule(
    camera_id: UUID,
    payload: IncidentRuleValidationRequest,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> IncidentRuleValidationResponse:
    return await services.incident_rules.validate_rule(tenant_context, camera_id, payload)


@router.get("/{rule_id}", response_model=IncidentRuleResponse)
async def get_incident_rule(
    camera_id: UUID,
    rule_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> IncidentRuleResponse:
    return await services.incident_rules.get_rule(tenant_context, camera_id, rule_id)


@router.patch("/{rule_id}", response_model=IncidentRuleResponse)
async def update_incident_rule(
    camera_id: UUID,
    rule_id: UUID,
    payload: IncidentRuleUpdate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> IncidentRuleResponse:
    return await services.incident_rules.update_rule(
        tenant_context,
        camera_id,
        rule_id,
        payload,
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident_rule(
    camera_id: UUID,
    rule_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    await services.incident_rules.delete_rule(tenant_context, camera_id, rule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
