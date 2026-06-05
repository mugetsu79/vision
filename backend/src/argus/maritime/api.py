from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from argus.api.dependencies import get_app_services
from argus.core.security import AuthenticatedUser, require
from argus.maritime.contracts import JsonObject
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(tags=["maritime"])

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("/api/v1/maritime/runtime")
async def get_maritime_runtime(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> JsonObject:
    return _runtime_payload(services)


@router.get("/api/v1/packs/maritime-fleet/runtime")
async def get_maritime_pack_runtime(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> JsonObject:
    return _runtime_payload(services)


def _runtime_payload(services: AppServices) -> JsonObject:
    try:
        return services.maritime.runtime_payload()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
