"""API router package for v1 endpoints."""

from fastapi import APIRouter

from argus.api.v1 import (
    cameras,
    configuration,
    deployment,
    edge,
    export,
    history,
    incident_rules,
    incidents,
    model_catalog,
    models,
    operations,
    packs,
    policy_drafts,
    query,
    runtime_artifacts,
    runtime_soak,
    sites,
    streams,
    system,
    telemetry_ws,
)
from argus.fleet import api as fleet
from argus.link import api as link

router = APIRouter()
router.include_router(system.router)
router.include_router(sites.router)
router.include_router(cameras.router)
router.include_router(configuration.router)
router.include_router(deployment.router)
router.include_router(models.router)
router.include_router(runtime_artifacts.router)
router.include_router(runtime_soak.router)
router.include_router(model_catalog.router)
router.include_router(packs.router)
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
router.include_router(link.router)
router.include_router(fleet.router)

__all__ = ["router"]
