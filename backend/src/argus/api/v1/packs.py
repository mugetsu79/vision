from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from argus.api.contracts import PackListResponse, PackManifestResponse
from argus.api.dependencies import get_app_services
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices
from argus.services.pack_registry import PackManifest

router = APIRouter(prefix="/api/v1/packs", tags=["packs"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=PackListResponse)
async def list_packs(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> PackListResponse:
    return PackListResponse(
        packs=[_manifest_response(manifest) for manifest in services.packs.list_packs()]
    )


@router.get("/{pack_id}", response_model=PackManifestResponse)
async def get_pack(
    pack_id: str,
    current_user: ViewerUser,
    services: ServicesDependency,
) -> PackManifestResponse:
    try:
        manifest = services.packs.get_pack(pack_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pack not found.",
        ) from exc
    return _manifest_response(manifest)


def _manifest_response(manifest: PackManifest) -> PackManifestResponse:
    data = manifest.model_dump(mode="python")
    data["is_runtime_enabled"] = manifest.is_runtime_enabled
    return PackManifestResponse.model_validate(data)
