from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from argus.api.contracts import ExportArtifact, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/export", tags=["export"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
CameraIdQuery = Annotated[UUID | None, Query()]
GranularityQuery = Annotated[str, Query(pattern="^(1m|1h)$")]
FromQuery = Annotated[datetime, Query(alias="from")]
ToQuery = Annotated[datetime, Query(alias="to")]
FormatQuery = Annotated[str, Query(pattern="^(csv|parquet)$")]


@router.get("")
async def export_history(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    from_: FromQuery,
    to: ToQuery,
    camera_id: CameraIdQuery = None,
    granularity: GranularityQuery = "1m",
    format: FormatQuery = "csv",
) -> Response:
    artifact: ExportArtifact = await services.history.export_history(
        tenant_context,
        camera_id=camera_id,
        granularity=granularity,
        starts_at=from_,
        ends_at=to,
        format_name=format,
    )
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
