from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from argus.api.contracts import CameraSetupPreviewResponse, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter()
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("/{camera_id}/setup-preview", response_model=CameraSetupPreviewResponse)
async def get_camera_setup_preview(
    camera_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    refresh: bool = Query(default=False),
) -> CameraSetupPreviewResponse:
    return await services.cameras.get_setup_preview(
        tenant_context,
        camera_id,
        force_refresh=refresh,
    )


@router.get("/{camera_id}/setup-preview/image")
async def get_camera_setup_preview_image(
    camera_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    snapshot = await services.cameras.get_setup_preview_image(tenant_context, camera_id)
    return Response(
        content=snapshot.image_bytes,
        media_type=snapshot.content_type,
        headers={"Cache-Control": "private, max-age=120"},
    )
