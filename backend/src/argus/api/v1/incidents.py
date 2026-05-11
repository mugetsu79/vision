from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, RedirectResponse, Response

from argus.api.contracts import (
    EvidenceLedgerEntryResponse,
    IncidentResponse,
    IncidentReviewUpdate,
    PrivacyManifestSnapshotResponse,
    SceneContractSnapshotResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import IncidentReviewStatus, RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
OperatorUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.OPERATOR))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
CameraIdQuery = Annotated[UUID | None, Query()]
IncidentTypeQuery = Annotated[str | None, Query(alias="type")]
ReviewStatusQuery = Annotated[IncidentReviewStatus | None, Query()]
LimitQuery = Annotated[int, Query(ge=1, le=200)]


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    camera_id: CameraIdQuery = None,
    incident_type: IncidentTypeQuery = None,
    review_status: ReviewStatusQuery = None,
    limit: LimitQuery = 50,
) -> list[IncidentResponse]:
    return await services.incidents.list_incidents(
        tenant_context,
        camera_id=camera_id,
        incident_type=incident_type,
        review_status=review_status,
        limit=limit,
    )


@router.get("/{incident_id}/scene-contract", response_model=SceneContractSnapshotResponse)
async def get_incident_scene_contract(
    incident_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> SceneContractSnapshotResponse:
    return await services.incidents.get_scene_contract(
        tenant_context,
        incident_id=incident_id,
    )


@router.get("/{incident_id}/privacy-manifest", response_model=PrivacyManifestSnapshotResponse)
async def get_incident_privacy_manifest(
    incident_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> PrivacyManifestSnapshotResponse:
    return await services.incidents.get_privacy_manifest(
        tenant_context,
        incident_id=incident_id,
    )


@router.get("/{incident_id}/ledger", response_model=list[EvidenceLedgerEntryResponse])
async def list_incident_ledger(
    incident_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[EvidenceLedgerEntryResponse]:
    return await services.incidents.list_ledger_entries(
        tenant_context,
        incident_id=incident_id,
    )


@router.get("/{incident_id}/artifacts/{artifact_id}/content", response_model=None)
async def get_incident_artifact_content(
    incident_id: UUID,
    artifact_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    content = await services.incidents.get_artifact_content(
        tenant_context,
        incident_id=incident_id,
        artifact_id=artifact_id,
    )
    if content.redirect_url is not None:
        return RedirectResponse(content.redirect_url)
    if content.file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence artifact content not available.",
        )
    return FileResponse(content.file_path, media_type=content.content_type)


@router.patch("/{incident_id}/review", response_model=IncidentResponse)
async def update_incident_review(
    incident_id: UUID,
    payload: IncidentReviewUpdate,
    current_user: OperatorUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> IncidentResponse:
    return await services.incidents.update_review_state(
        tenant_context,
        incident_id=incident_id,
        review_status=payload.review_status,
    )
