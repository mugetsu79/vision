from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from argus.api.contracts import (
    RuntimeArtifactSoakRunCreate,
    RuntimeArtifactSoakRunResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/runtime-artifacts/soak-runs", tags=["runtime-artifacts"])
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=list[RuntimeArtifactSoakRunResponse])
async def list_runtime_artifact_soak_runs(
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    runtime_artifact_id: UUID | None = None,
    edge_node_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RuntimeArtifactSoakRunResponse]:
    return await services.runtime_soak.list_soak_runs(
        tenant_id=tenant_context.tenant_id,
        runtime_artifact_id=runtime_artifact_id,
        edge_node_id=edge_node_id,
        limit=limit,
    )


@router.post(
    "",
    response_model=RuntimeArtifactSoakRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_runtime_artifact_soak_run(
    payload: RuntimeArtifactSoakRunCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> RuntimeArtifactSoakRunResponse:
    return await services.runtime_soak.record_soak_run(
        tenant_id=tenant_context.tenant_id,
        payload=payload,
    )
