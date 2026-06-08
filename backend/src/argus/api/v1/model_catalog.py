from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from argus.api.contracts import ModelCatalogEntryResponse, ModelImportJobResponse, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/model-catalog", tags=["model-catalog"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=list[ModelCatalogEntryResponse])
async def list_model_catalog(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> list[ModelCatalogEntryResponse]:
    return await services.models.list_catalog_status()


@router.post(
    "/{catalog_id}/register",
    response_model=ModelImportJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_model_catalog_entry(
    catalog_id: str,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> ModelImportJobResponse:
    try:
        return await services.model_lifecycle.register_catalog_entry(
            tenant_id=tenant_context.tenant_id,
            actor_subject=current_user.subject,
            catalog_id=catalog_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{catalog_id}/download",
    response_model=ModelImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def download_model_catalog_entry(
    catalog_id: str,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> ModelImportJobResponse:
    try:
        return await services.model_lifecycle.queue_catalog_download(
            tenant_id=tenant_context.tenant_id,
            actor_subject=current_user.subject,
            catalog_id=catalog_id,
        )
    except ValueError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(exc).lower()
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
