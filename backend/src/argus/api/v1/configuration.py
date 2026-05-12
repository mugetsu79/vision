from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from argus.api.contracts import (
    OperatorConfigBindingRequest,
    OperatorConfigBindingResponse,
    OperatorConfigProfileCreate,
    OperatorConfigProfileResponse,
    OperatorConfigProfileUpdate,
    OperatorConfigTestResponse,
    ResolvedOperatorConfigResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import OperatorConfigProfileKind, RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/configuration", tags=["configuration"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
ConfigKindQuery = Annotated[OperatorConfigProfileKind | None, Query()]
CameraIdQuery = Annotated[UUID | None, Query()]
SiteIdQuery = Annotated[UUID | None, Query()]
EdgeNodeIdQuery = Annotated[UUID | None, Query()]


@router.get("/catalog")
async def list_configuration_catalog(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> dict[str, object]:
    return await services.configuration.list_catalog()


@router.get("/profiles", response_model=list[OperatorConfigProfileResponse])
async def list_configuration_profiles(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    kind: ConfigKindQuery = None,
) -> list[OperatorConfigProfileResponse]:
    return await services.configuration.list_profiles(tenant_context, kind=kind)


@router.post(
    "/profiles",
    response_model=OperatorConfigProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_configuration_profile(
    payload: OperatorConfigProfileCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> OperatorConfigProfileResponse:
    return await services.configuration.create_profile(tenant_context, payload)


@router.patch("/profiles/{profile_id}", response_model=OperatorConfigProfileResponse)
async def update_configuration_profile(
    profile_id: UUID,
    payload: OperatorConfigProfileUpdate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> OperatorConfigProfileResponse:
    return await services.configuration.update_profile(tenant_context, profile_id, payload)


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration_profile(
    profile_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    await services.configuration.delete_profile(tenant_context, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/profiles/{profile_id}/test", response_model=OperatorConfigTestResponse)
async def test_configuration_profile(
    profile_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> OperatorConfigTestResponse:
    return await services.configuration.test_profile(tenant_context, profile_id)


@router.post("/bindings", response_model=OperatorConfigBindingResponse)
async def upsert_configuration_binding(
    payload: OperatorConfigBindingRequest,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> OperatorConfigBindingResponse:
    return await services.configuration.upsert_binding(tenant_context, payload)


@router.get("/resolved", response_model=ResolvedOperatorConfigResponse)
async def resolve_configuration(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    camera_id: CameraIdQuery = None,
    site_id: SiteIdQuery = None,
    edge_node_id: EdgeNodeIdQuery = None,
) -> ResolvedOperatorConfigResponse:
    return await services.configuration.resolve_all_for_camera(
        tenant_context,
        camera_id=camera_id,
        site_id=site_id,
        edge_node_id=edge_node_id,
    )
