from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from traffic_monitor.core.security import AuthenticatedUser, require
from traffic_monitor.models.enums import RoleEnum

router = APIRouter(prefix="/api/v1", tags=["system"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]


@router.get("/debug/protected")
async def debug_protected(current_user: ViewerUser) -> dict[str, object]:
    return {
        "sub": current_user.subject,
        "email": current_user.email,
        "role": current_user.role.value,
        "realm": current_user.realm,
        "is_superadmin": current_user.is_superadmin,
    }


@router.post("/edge/ping")
async def edge_ping() -> dict[str, str]:
    return {"status": "ok"}
