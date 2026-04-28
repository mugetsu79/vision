"""API router package for v1 endpoints."""

from fastapi import APIRouter

from argus.api.v1 import (
    cameras,
    edge,
    export,
    history,
    incidents,
    models,
    operations,
    query,
    sites,
    streams,
    system,
    telemetry_ws,
)

router = APIRouter()
router.include_router(system.router)
router.include_router(sites.router)
router.include_router(cameras.router)
router.include_router(models.router)
router.include_router(edge.router)
router.include_router(operations.router)
router.include_router(history.router)
router.include_router(export.router)
router.include_router(incidents.router)
router.include_router(streams.router)
router.include_router(query.router)
router.include_router(telemetry_ws.router)

__all__ = ["router"]
