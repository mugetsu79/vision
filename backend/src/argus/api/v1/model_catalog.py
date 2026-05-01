from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from argus.api.contracts import ModelCatalogEntryResponse
from argus.api.dependencies import get_app_services
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/model-catalog", tags=["model-catalog"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=list[ModelCatalogEntryResponse])
async def list_model_catalog(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> list[ModelCatalogEntryResponse]:
    return await services.models.list_catalog_status()
