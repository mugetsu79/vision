from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from argus.api.contracts import (
    EdgeHeartbeatRequest,
    EdgeHeartbeatResponse,
    EdgeRegisterRequest,
    EdgeRegisterResponse,
    TelemetryEnvelope,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/edge", tags=["edge"])
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.post("/register", response_model=EdgeRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_edge_node(
    payload: EdgeRegisterRequest,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> EdgeRegisterResponse:
    return await services.edge.register_edge_node(tenant_context, payload)


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def ingest_edge_telemetry(
    payload: TelemetryEnvelope,
    services: ServicesDependency,
) -> dict[str, int]:
    return await services.edge.ingest_telemetry(payload)


@router.post(
    "/heartbeat",
    response_model=EdgeHeartbeatResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def edge_heartbeat(
    payload: EdgeHeartbeatRequest,
    services: ServicesDependency,
) -> EdgeHeartbeatResponse:
    return await services.edge.record_heartbeat(payload)
