from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from argus.api.contracts import (
    PlatformBootstrapComplete,
    PlatformBootstrapCompleteResponse,
    PlatformBootstrapStatusResponse,
)
from argus.api.dependencies import get_app_services
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/platform/bootstrap", tags=["platform-bootstrap"])
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("/status", response_model=PlatformBootstrapStatusResponse)
async def get_platform_bootstrap_status(
    services: ServicesDependency,
) -> PlatformBootstrapStatusResponse:
    return await services.platform_bootstrap.status()


@router.post("/complete", response_model=PlatformBootstrapCompleteResponse)
async def complete_platform_bootstrap(
    payload: PlatformBootstrapComplete,
    request: Request,
    services: ServicesDependency,
) -> PlatformBootstrapCompleteResponse:
    _require_local_platform_bootstrap_request(request)
    try:
        return await services.platform_bootstrap.complete(payload)
    except ValueError as exc:
        raise _platform_bootstrap_http_error(exc) from exc


def _platform_bootstrap_http_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    normalized = detail.lower()
    if "already exists" in normalized or "already consumed" in normalized:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _require_local_platform_bootstrap_request(request: Request) -> None:
    host = request.client.host if request.client is not None else ""
    settings = getattr(request.app.state, "settings", None)
    allowed_hosts = (
        settings.local_bootstrap_allowed_client_hosts
        if settings is not None
        else ("127.0.0.1", "::1", "localhost", "testclient", "test")
    )
    if host in allowed_hosts:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Platform bootstrap is only available from the local host.",
    )
