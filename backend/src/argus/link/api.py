from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from argus.api.contracts import TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.link.contracts import (
    JsonObject,
    LinkBudgetSnapshot,
    LinkHealthProbeRecord,
    LinkPassportSnapshotRecord,
    LinkQueueItemRecord,
)
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/link", tags=["link"])

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]


class LinkBudgetUpdate(BaseModel):
    monthly_bytes: int = Field(ge=0)
    bulk_daily_bytes: int = Field(ge=0)


class LinkProbeCreate(BaseModel):
    latency_ms: int = Field(ge=0)
    throughput_mbps: float = Field(ge=0)
    packet_loss_percent: float = Field(ge=0)
    reachable: bool
    source: str = Field(min_length=1, max_length=128)


class LinkPolicyUpdate(BaseModel):
    policy: dict[str, object] = Field(default_factory=dict)


@router.get("/sites/{site_id}/status")
async def get_link_status(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, site_id)
    passport = await services.link.abuild_passport(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
    )
    return _status_payload(passport)


@router.get("/sites/{site_id}/budget")
async def get_link_budget(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject | None:
    await _ensure_tenant_site(services, tenant_context, site_id)
    budget = await services.link.aget_budget(tenant_id=tenant_context.tenant_id, site_id=site_id)
    if budget is None:
        return None
    return _budget_payload(budget)


@router.put("/sites/{site_id}/budget")
async def put_link_budget(
    site_id: UUID,
    payload: LinkBudgetUpdate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, site_id)
    budget = await services.link.aupsert_budget(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        monthly_bytes=payload.monthly_bytes,
        bulk_daily_bytes=payload.bulk_daily_bytes,
    )
    return _budget_payload(budget)


@router.get("/sites/{site_id}/queue")
async def get_link_queue(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[JsonObject]:
    await _ensure_tenant_site(services, tenant_context, site_id)
    return [
        _queue_item_payload(item)
        for item in await services.link.alist_queue(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
        )
    ]


@router.get("/sites/{site_id}/probes")
async def get_link_probes(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[JsonObject]:
    await _ensure_tenant_site(services, tenant_context, site_id)
    return [
        _probe_payload(probe)
        for probe in await services.link.alist_probes(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
        )
    ]


@router.post("/sites/{site_id}/probes", status_code=status.HTTP_201_CREATED)
async def post_link_probe(
    site_id: UUID,
    payload: LinkProbeCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, site_id)
    probe = await services.link.arecord_probe(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        latency_ms=payload.latency_ms,
        throughput_mbps=payload.throughput_mbps,
        packet_loss_percent=payload.packet_loss_percent,
        reachable=payload.reachable,
        source=payload.source,
    )
    return _probe_payload(probe)


@router.get("/sites/{site_id}/policies")
async def get_link_policies(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, site_id)
    return await services.link.aget_policy(tenant_id=tenant_context.tenant_id, site_id=site_id)


@router.put("/sites/{site_id}/policies")
async def put_link_policies(
    site_id: UUID,
    payload: LinkPolicyUpdate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, site_id)
    try:
        return await services.link.aput_policy(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
            policy=payload.policy,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link budget not found.",
        ) from exc


@router.get("/evidence/{incident_id}/passport")
async def get_incident_link_passport(
    incident_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    passport = await services.link.abuild_incident_passport(
        tenant_id=tenant_context.tenant_id,
        incident_id=incident_id,
    )
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    return passport.payload


@router.post("/queue/{queue_item_id}/retry")
async def retry_link_queue_item(
    queue_item_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    item = await services.link.aretry_queue_item(
        tenant_id=tenant_context.tenant_id,
        queue_item_id=queue_item_id,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found.")
    return _queue_item_payload(item)


@router.post("/queue/{queue_item_id}/pause")
async def pause_link_queue_item(
    queue_item_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    item = await services.link.apause_queue_item(
        tenant_id=tenant_context.tenant_id,
        queue_item_id=queue_item_id,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found.")
    return _queue_item_payload(item)


@router.post("/queue/{queue_item_id}/resume")
async def resume_link_queue_item(
    queue_item_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    item = await services.link.aresume_queue_item(
        tenant_id=tenant_context.tenant_id,
        queue_item_id=queue_item_id,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found.")
    return _queue_item_payload(item)


def _status_payload(passport: LinkPassportSnapshotRecord) -> JsonObject:
    payload = passport.payload.copy()
    payload["passport_hash"] = passport.passport_hash
    return payload


async def _ensure_tenant_site(
    services: AppServices,
    tenant_context: TenantContext,
    site_id: UUID,
) -> None:
    try:
        await services.sites.get_site(tenant_context, site_id)
    except HTTPException:
        raise


def _budget_payload(budget: LinkBudgetSnapshot) -> JsonObject:
    return {
        "id": str(budget.id),
        "tenant_id": str(budget.tenant_id),
        "site_id": str(budget.site_id),
        "monthly_bytes": budget.monthly_bytes,
        "bulk_daily_bytes": budget.bulk_daily_bytes,
        "created_at": budget.created_at.isoformat(),
        "updated_at": budget.updated_at.isoformat(),
    }


def _queue_item_payload(item: LinkQueueItemRecord) -> JsonObject:
    return {
        "id": str(item.id),
        "tenant_id": str(item.tenant_id),
        "site_id": str(item.site_id),
        "camera_id": str(item.camera_id) if item.camera_id is not None else None,
        "incident_id": str(item.incident_id) if item.incident_id is not None else None,
        "evidence_artifact_id": (
            str(item.evidence_artifact_id) if item.evidence_artifact_id is not None else None
        ),
        "priority_lane": item.priority_lane,
        "byte_size": item.byte_size,
        "source_object_type": item.source_object_type,
        "source_object_id": str(item.source_object_id),
        "status": item.status,
        "last_successful_transfer_at": (
            item.last_successful_transfer_at.isoformat()
            if item.last_successful_transfer_at is not None
            else None
        ),
    }


def _probe_payload(probe: LinkHealthProbeRecord) -> JsonObject:
    return {
        "id": str(probe.id),
        "tenant_id": str(probe.tenant_id),
        "site_id": str(probe.site_id),
        "latency_ms": probe.latency_ms,
        "throughput_mbps": probe.throughput_mbps,
        "packet_loss_percent": probe.packet_loss_percent,
        "reachable": probe.reachable,
        "source": probe.source,
        "recorded_at": probe.recorded_at.isoformat(),
    }
