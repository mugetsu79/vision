from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from argus.api.contracts import (
    RuntimeArtifactBuildJobCreate,
    RuntimeArtifactBuildJobResponse,
    RuntimeArtifactCreate,
    RuntimeArtifactResponse,
    RuntimeArtifactUpdate,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(
    prefix="/api/v1/models/{model_id}/runtime-artifacts",
    tags=["runtime-artifacts"],
)
build_jobs_router = APIRouter(
    prefix="/api/v1/models/{model_id}/runtime-artifact-build-jobs",
    tags=["runtime-artifacts"],
)
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]


@router.get("", response_model=list[RuntimeArtifactResponse])
async def list_runtime_artifacts(
    model_id: UUID,
    current_user: ViewerUser,
    services: ServicesDependency,
) -> list[RuntimeArtifactResponse]:
    return await services.runtime_artifacts.list_for_model(model_id)


@router.post("", response_model=RuntimeArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_runtime_artifact(
    model_id: UUID,
    payload: RuntimeArtifactCreate,
    current_user: AdminUser,
    services: ServicesDependency,
) -> RuntimeArtifactResponse:
    return await services.runtime_artifacts.create_for_model(model_id, payload)


@router.patch("/{artifact_id}", response_model=RuntimeArtifactResponse)
async def update_runtime_artifact(
    model_id: UUID,
    artifact_id: UUID,
    payload: RuntimeArtifactUpdate,
    current_user: AdminUser,
    services: ServicesDependency,
) -> RuntimeArtifactResponse:
    return await services.runtime_artifacts.update_artifact(model_id, artifact_id, payload)


@router.post("/{artifact_id}/validate", response_model=RuntimeArtifactResponse)
async def validate_runtime_artifact(
    model_id: UUID,
    artifact_id: UUID,
    current_user: AdminUser,
    services: ServicesDependency,
) -> RuntimeArtifactResponse:
    return await services.runtime_artifacts.validate_artifact(model_id, artifact_id)


@build_jobs_router.get("", response_model=list[RuntimeArtifactBuildJobResponse])
async def list_runtime_artifact_build_jobs(
    model_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[RuntimeArtifactBuildJobResponse]:
    return await services.model_lifecycle.list_runtime_artifact_build_jobs(
        tenant_id=tenant_context.tenant_id,
        model_id=model_id,
    )


@build_jobs_router.post(
    "",
    response_model=RuntimeArtifactBuildJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_runtime_artifact_build_job(
    model_id: UUID,
    payload: RuntimeArtifactBuildJobCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> RuntimeArtifactBuildJobResponse:
    try:
        return await services.model_lifecycle.create_runtime_artifact_build_job(
            tenant_id=tenant_context.tenant_id,
            model_id=model_id,
            payload=payload,
            actor_subject=current_user.subject,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
