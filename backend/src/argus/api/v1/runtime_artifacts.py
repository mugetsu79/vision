from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from argus.api.contracts import (
    RuntimeArtifactCreate,
    RuntimeArtifactResponse,
    RuntimeArtifactUpdate,
)
from argus.api.dependencies import get_app_services
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(
    prefix="/api/v1/models/{model_id}/runtime-artifacts",
    tags=["runtime-artifacts"],
)
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


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
