from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from argus.api.contracts import (
    HistoryClassesResponse,
    HistoryPoint,
    HistorySeriesResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import HistoryMetric, RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/history", tags=["history"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
CameraIdQuery = Annotated[UUID | None, Query()]
CameraIdsQuery = Annotated[list[UUID] | None, Query()]
ClassNamesQuery = Annotated[list[str] | None, Query()]
GranularityQuery = Annotated[str, Query(pattern="^(1m|5m|1h|1d)$")]
FromQuery = Annotated[datetime, Query(alias="from")]
ToQuery = Annotated[datetime, Query(alias="to")]
IncludeSpeedQuery = Annotated[bool, Query()]
SpeedThresholdQuery = Annotated[float | None, Query(ge=0)]
HistoryMetricQuery = Annotated[HistoryMetric, Query()]


def _normalize_camera_ids(
    *,
    camera_id: UUID | None,
    camera_ids: list[UUID] | None,
) -> list[UUID] | None:
    combined: list[UUID] = []
    if camera_ids:
        combined.extend(camera_ids)
    if camera_id is not None:
        combined.append(camera_id)
    if not combined:
        return None
    unique: list[UUID] = []
    seen: set[UUID] = set()
    for value in combined:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


@router.get("", response_model=list[HistoryPoint])
async def get_history(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    from_: FromQuery,
    to: ToQuery,
    camera_id: CameraIdQuery = None,
    camera_ids: CameraIdsQuery = None,
    class_names: ClassNamesQuery = None,
    granularity: GranularityQuery = "1m",
    metric: HistoryMetricQuery = HistoryMetric.OCCUPANCY,
) -> list[HistoryPoint]:
    return await services.history.query_history(
        tenant_context,
        camera_ids=_normalize_camera_ids(camera_id=camera_id, camera_ids=camera_ids),
        class_names=class_names,
        granularity=granularity,
        starts_at=from_,
        ends_at=to,
        metric=metric,
    )


@router.get("/series", response_model=HistorySeriesResponse)
async def get_history_series(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    from_: FromQuery,
    to: ToQuery,
    camera_id: CameraIdQuery = None,
    camera_ids: CameraIdsQuery = None,
    class_names: ClassNamesQuery = None,
    granularity: GranularityQuery = "1h",
    metric: HistoryMetricQuery = HistoryMetric.OCCUPANCY,
    include_speed: IncludeSpeedQuery = False,
    speed_threshold: SpeedThresholdQuery = None,
) -> HistorySeriesResponse:
    return await services.history.query_series(
        tenant_context,
        camera_ids=_normalize_camera_ids(camera_id=camera_id, camera_ids=camera_ids),
        class_names=class_names,
        granularity=granularity,
        starts_at=from_,
        ends_at=to,
        metric=metric,
        include_speed=include_speed,
        speed_threshold=speed_threshold,
    )


@router.get("/classes", response_model=HistoryClassesResponse)
async def get_history_classes(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    from_: FromQuery,
    to: ToQuery,
    camera_id: CameraIdQuery = None,
    camera_ids: CameraIdsQuery = None,
    metric: HistoryMetricQuery = HistoryMetric.OCCUPANCY,
) -> HistoryClassesResponse:
    return await services.history.list_classes(
        tenant_context,
        camera_ids=_normalize_camera_ids(camera_id=camera_id, camera_ids=camera_ids),
        starts_at=from_,
        ends_at=to,
        metric=metric,
    )
