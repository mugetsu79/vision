"""API router package for v1 endpoints."""

from fastapi import APIRouter

from argus.api.v1 import (
    cameras,
    configuration,
    edge,
    export,
    history,
    incident_rules,
    incidents,
    model_catalog,
    models,
    operations,
    policy_drafts,
    query,
    runtime_artifacts,
    sites,
    streams,
    system,
    telemetry_ws,
)

router = APIRouter()
router.include_router(system.router)
router.include_router(sites.router)
router.include_router(cameras.router)
router.include_router(configuration.router)
router.include_router(models.router)
router.include_router(runtime_artifacts.router)
router.include_router(model_catalog.router)
router.include_router(edge.router)
router.include_router(operations.router)
router.include_router(policy_drafts.router)
router.include_router(history.router)
router.include_router(export.router)
router.include_router(incidents.router)
router.include_router(incident_rules.router)
router.include_router(streams.router)
router.include_router(query.router)
router.include_router(telemetry_ws.router)

__all__ = ["router"]
