from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from argus.api.contracts import (
    ModelCreate,
    ModelImportJobResponse,
    ModelImportRequest,
    ModelResponse,
    ModelUpdate,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import ModelImportSource, RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1", tags=["models"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("/models", response_model=list[ModelResponse])
async def list_models(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> list[ModelResponse]:
    return await services.models.list_models()


@router.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    payload: ModelCreate,
    current_user: AdminUser,
    services: ServicesDependency,
) -> ModelResponse:
    return await services.models.create_model(payload)


@router.post(
    "/models/import-url",
    response_model=ModelImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_model_url(
    payload: ModelImportRequest,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> ModelImportJobResponse:
    if payload.source is not ModelImportSource.URL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="source must be url for this endpoint.",
        )
    return await services.model_lifecycle.import_model_from_request(
        tenant_id=tenant_context.tenant_id,
        actor_subject=current_user.subject,
        payload=payload,
    )


@router.get("/model-import-jobs", response_model=list[ModelImportJobResponse])
async def list_model_import_jobs(
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[ModelImportJobResponse]:
    return await services.model_lifecycle.list_import_jobs(tenant_context.tenant_id)


@router.patch("/models/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    payload: ModelUpdate,
    current_user: AdminUser,
    services: ServicesDependency,
) -> ModelResponse:
    return await services.models.update_model(model_id, payload)
