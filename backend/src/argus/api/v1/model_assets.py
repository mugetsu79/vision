from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from argus.api.contracts import TenantContext
from argus.api.dependencies import (
    SupervisorOrAdminTenantDependency,
    get_app_services,
)
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/model-assets", tags=["model-assets"])
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("/{asset_id}/download")
async def download_model_asset(
    asset_id: UUID,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> FileResponse:
    try:
        asset = await services.model_lifecycle.get_model_asset_download(
            tenant_id=tenant_context.tenant_id,
            asset_id=asset_id,
            authenticated_node_id=_authenticated_deployment_node_id(tenant_context),
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise _model_asset_http_error(exc) from exc
    return FileResponse(
        asset.path,
        filename=asset.filename,
        media_type="application/octet-stream",
    )


def _model_asset_http_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if "not found" in detail.lower():
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _authenticated_deployment_node_id(tenant_context: TenantContext) -> UUID | None:
    if tenant_context.user.claims.get("auth_type") != "supervisor_node_credential":
        return None
    raw_node_id = tenant_context.user.claims.get("deployment_node_id")
    if not isinstance(raw_node_id, str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor credential is missing deployment node scope.",
        )
    try:
        return UUID(raw_node_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor credential has invalid deployment node scope.",
        ) from None
