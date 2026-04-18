from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from argus.api.contracts import StreamOfferRequest, StreamOfferResponse, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/streams", tags=["streams"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.post("/{camera_id}/offer", response_model=StreamOfferResponse)
async def create_stream_offer(
    camera_id: UUID,
    payload: StreamOfferRequest,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> StreamOfferResponse:
    return await services.streams.create_offer(
        tenant_context,
        camera_id=camera_id,
        offer=payload,
    )
