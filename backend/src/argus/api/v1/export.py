from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from argus.api.contracts import ExportArtifact, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.api.v1.history import _normalize_camera_ids
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import HistoryMetric, RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/export", tags=["export"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
CameraIdQuery = Annotated[UUID | None, Query()]
CameraIdsQuery = Annotated[list[UUID] | None, Query()]
ClassNamesQuery = Annotated[list[str] | None, Query()]
GranularityQuery = Annotated[str, Query(pattern="^(1m|5m|1h|1d)$")]
FromQuery = Annotated[datetime, Query(alias="from")]
ToQuery = Annotated[datetime, Query(alias="to")]
FormatQuery = Annotated[str, Query(pattern="^(csv|parquet)$")]
MetricQuery = Annotated[HistoryMetric, Query()]


@router.get("")
async def export_history(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    from_: FromQuery,
    to: ToQuery,
    camera_id: CameraIdQuery = None,
    camera_ids: CameraIdsQuery = None,
    class_names: ClassNamesQuery = None,
    granularity: GranularityQuery = "1m",
    format: FormatQuery = "csv",
    metric: MetricQuery = HistoryMetric.OCCUPANCY,
) -> Response:
    artifact: ExportArtifact = await services.history.export_history(
        tenant_context,
        camera_ids=_normalize_camera_ids(camera_id=camera_id, camera_ids=camera_ids),
        class_names=class_names,
        granularity=granularity,
        starts_at=from_,
        ends_at=to,
        format_name=format,
        metric=metric,
    )
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
