from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from argus.api.contracts import (
    CameraCreate,
    CameraResponse,
    CameraSourceProbeRequest,
    CameraSourceProbeResponse,
    CameraUpdate,
    TenantContext,
    WorkerConfigResponse,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

from . import camera_setup

router = APIRouter(prefix="/api/v1/cameras", tags=["cameras"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
SiteIdQuery = Annotated[UUID | None, Query()]


@router.get("", response_model=list[CameraResponse])
async def list_cameras(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    site_id: SiteIdQuery = None,
) -> list[CameraResponse]:
    return await services.cameras.list_cameras(tenant_context, site_id=site_id)


@router.post("/source-probe", response_model=CameraSourceProbeResponse)
async def probe_camera_source(
    payload: CameraSourceProbeRequest,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> CameraSourceProbeResponse:
    return await services.cameras.probe_camera_source(tenant_context, payload)


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> CameraResponse:
    return await services.cameras.get_camera(tenant_context, camera_id)


@router.get("/{camera_id}/worker-config", response_model=WorkerConfigResponse)
async def get_camera_worker_config(
    camera_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> WorkerConfigResponse:
    return await services.cameras.get_worker_config(tenant_context, camera_id)


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    payload: CameraCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> CameraResponse:
    return await services.cameras.create_camera(tenant_context, payload)


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: UUID,
    payload: CameraUpdate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> CameraResponse:
    return await services.cameras.update_camera(tenant_context, camera_id, payload)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    await services.cameras.delete_camera(tenant_context, camera_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(camera_setup.router)
