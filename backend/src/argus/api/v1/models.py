from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from argus.api.contracts import ModelCreate, ModelResponse, ModelUpdate
from argus.api.dependencies import get_app_services
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/models", tags=["models"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=list[ModelResponse])
async def list_models(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> list[ModelResponse]:
    return await services.models.list_models()


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    payload: ModelCreate,
    current_user: AdminUser,
    services: ServicesDependency,
) -> ModelResponse:
    return await services.models.create_model(payload)


@router.patch("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    payload: ModelUpdate,
    current_user: AdminUser,
    services: ServicesDependency,
) -> ModelResponse:
    return await services.models.update_model(model_id, payload)
