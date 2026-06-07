from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from argus.api.contracts import TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.link.contracts import (
    JsonObject,
    LinkAvailabilityScope,
    LinkBudgetSnapshot,
    LinkConnectionRecord,
    LinkConnectionStatus,
    LinkHealthProbeRecord,
    LinkPassportSnapshotRecord,
    LinkPriorityLane,
    LinkProbeSampleKind,
    LinkProbeSourceType,
    LinkProbeType,
    LinkQueueItemRecord,
    LinkSiteSummaryRecord,
    LinkTransportKind,
)
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/link", tags=["link"])

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
PriorityLaneQuery = Annotated[LinkPriorityLane, Query()]
RemainingBudgetBytesQuery = Annotated[int, Query(ge=0)]
REQUIRED_CONNECTION_PATCH_FIELDS = {
    "label",
    "transport_kind",
    "status",
    "priority_rank",
    "availability_scope",
    "metered",
}


class LinkBudgetUpdate(BaseModel):
    monthly_bytes: int = Field(ge=0)
    bulk_daily_bytes: int = Field(ge=0)


class LinkProbeCreate(BaseModel):
    connection_id: UUID | None = None
    latency_ms: int = Field(ge=0)
    throughput_mbps: float = Field(ge=0)
    packet_loss_percent: float = Field(ge=0)
    reachable: bool
    source: str = Field(min_length=1, max_length=128)
    target_id: str | None = Field(default=None, max_length=96)
    target_label: str | None = Field(default=None, max_length=160)
    target_address: str | None = None
    probe_type: LinkProbeType | None = None
    source_type: LinkProbeSourceType = "manual"
    source_label: str | None = Field(default=None, max_length=128)
    sample_kind: LinkProbeSampleKind = "manual"


class LinkPolicyUpdate(BaseModel):
    policy: dict[str, object] = Field(default_factory=dict)


class LinkConnectionCreate(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    transport_kind: LinkTransportKind
    provider: str | None = Field(default=None, max_length=160)
    status: LinkConnectionStatus = "unknown"
    priority_rank: int = Field(default=100, ge=0)
    availability_scope: LinkAvailabilityScope = "always"
    metered: bool = False
    monthly_bytes: int | None = Field(default=None, ge=0)
    bulk_daily_bytes: int | None = Field(default=None, ge=0)
    expected_downlink_mbps: float | None = Field(default=None, ge=0)
    expected_uplink_mbps: float | None = Field(default=None, ge=0)
    expected_latency_ms: int | None = Field(default=None, ge=0)
    packet_loss_percent: float | None = Field(default=None, ge=0)
    last_seen_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class LinkConnectionPatch(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=160)
    transport_kind: LinkTransportKind | None = None
    provider: str | None = Field(default=None, max_length=160)
    status: LinkConnectionStatus | None = None
    priority_rank: int | None = Field(default=None, ge=0)
    availability_scope: LinkAvailabilityScope | None = None
    metered: bool | None = None
    monthly_bytes: int | None = Field(default=None, ge=0)
    bulk_daily_bytes: int | None = Field(default=None, ge=0)
    expected_downlink_mbps: float | None = Field(default=None, ge=0)
    expected_uplink_mbps: float | None = Field(default=None, ge=0)
    expected_latency_ms: int | None = Field(default=None, ge=0)
    packet_loss_percent: float | None = Field(default=None, ge=0)
    last_seen_at: datetime | None = None
    metadata: dict[str, object] | None = None


class LinkSiteSummaryResponse(BaseModel):
    site_id: UUID
    site_name: str
    site_tz: str
    link_state: str
    active_connection: dict[str, object] | None = None
    connection_count: int
    metered_connection_count: int
    latest_probe: dict[str, object] | None = None
    queue_depth: dict[str, int] = Field(default_factory=dict)
    queued_bytes: int
    budget: dict[str, object] | None = None
    last_sync_at: datetime | None = None
    passport_hash: str


@router.get("/sites/summary", response_model=list[LinkSiteSummaryResponse])
async def get_link_site_summaries(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[LinkSiteSummaryResponse]:
    sites = await services.sites.list_sites(tenant_context)
    summary_records = await services.link.alist_site_summaries(
        tenant_id=tenant_context.tenant_id,
        sites=[{"id": site.id, "name": site.name, "tz": site.tz} for site in sites],
    )
    return [_site_summary_payload(summary) for summary in summary_records]


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


@router.get("/sites/{site_id}/connections")
async def get_link_connections(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[JsonObject]:
    await _ensure_tenant_site(services, tenant_context, site_id)
    return [
        _connection_payload(connection)
        for connection in await services.link.alist_connections(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
        )
    ]


@router.post("/sites/{site_id}/connections", status_code=status.HTTP_201_CREATED)
async def post_link_connection(
    site_id: UUID,
    payload: LinkConnectionCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, site_id)
    try:
        connection = await services.link.aupsert_connection(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
            label=payload.label,
            transport_kind=payload.transport_kind,
            provider=payload.provider,
            status=payload.status,
            priority_rank=payload.priority_rank,
            availability_scope=payload.availability_scope,
            metered=payload.metered,
            monthly_bytes=payload.monthly_bytes,
            bulk_daily_bytes=payload.bulk_daily_bytes,
            expected_downlink_mbps=payload.expected_downlink_mbps,
            expected_uplink_mbps=payload.expected_uplink_mbps,
            expected_latency_ms=payload.expected_latency_ms,
            packet_loss_percent=payload.packet_loss_percent,
            last_seen_at=payload.last_seen_at,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _connection_payload(connection)


@router.get("/sites/{site_id}/connections/selection")
async def get_link_connection_selection(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    priority_lane: PriorityLaneQuery = "bulk",
    remaining_budget_bytes: RemainingBudgetBytesQuery = 0,
) -> JsonObject | None:
    await _ensure_tenant_site(services, tenant_context, site_id)
    connection = await services.link.aselect_connection(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        priority_lane=priority_lane,
        remaining_budget_bytes=remaining_budget_bytes,
    )
    return _connection_payload(connection) if connection is not None else None


@router.patch("/sites/{site_id}/connections/{connection_id}")
async def patch_link_connection(
    site_id: UUID,
    connection_id: UUID,
    payload: LinkConnectionPatch,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, site_id)
    existing = await services.link.aget_connection(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        connection_id=connection_id,
    )
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    updates = payload.model_dump(exclude_unset=True)
    _reject_null_required_connection_fields(updates)
    try:
        connection = await services.link.aupsert_connection(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
            connection_id=connection_id,
            label=updates.get("label", existing.label),
            transport_kind=updates.get("transport_kind", existing.transport_kind),
            provider=updates.get("provider", existing.provider),
            status=updates.get("status", existing.status),
            priority_rank=updates.get("priority_rank", existing.priority_rank),
            availability_scope=updates.get("availability_scope", existing.availability_scope),
            metered=updates.get("metered", existing.metered),
            monthly_bytes=updates.get("monthly_bytes", existing.monthly_bytes),
            bulk_daily_bytes=updates.get("bulk_daily_bytes", existing.bulk_daily_bytes),
            expected_downlink_mbps=updates.get(
                "expected_downlink_mbps",
                existing.expected_downlink_mbps,
            ),
            expected_uplink_mbps=updates.get(
                "expected_uplink_mbps",
                existing.expected_uplink_mbps,
            ),
            expected_latency_ms=updates.get("expected_latency_ms", existing.expected_latency_ms),
            packet_loss_percent=updates.get("packet_loss_percent", existing.packet_loss_percent),
            last_seen_at=updates.get("last_seen_at", existing.last_seen_at),
            metadata=updates.get("metadata", existing.metadata),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _connection_payload(connection)


@router.delete(
    "/sites/{site_id}/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_link_connection(
    site_id: UUID,
    connection_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> None:
    await _ensure_tenant_site(services, tenant_context, site_id)
    deleted = await services.link.adelete_connection(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        connection_id=connection_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")


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
    try:
        probe = await services.link.arecord_probe(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
            connection_id=payload.connection_id,
            latency_ms=payload.latency_ms,
            throughput_mbps=payload.throughput_mbps,
            packet_loss_percent=payload.packet_loss_percent,
            reachable=payload.reachable,
            source=payload.source,
            target_id=payload.target_id,
            target_label=payload.target_label,
            target_address=payload.target_address,
            probe_type=payload.probe_type,
            source_type=payload.source_type,
            source_label=payload.source_label,
            sample_kind=payload.sample_kind,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _probe_payload(probe)


@router.delete("/sites/{site_id}/probes/{probe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link_probe(
    site_id: UUID,
    probe_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    await _ensure_tenant_site(services, tenant_context, site_id)
    deleted = await services.link.adelete_probe(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        probe_id=probe_id,
    )
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Probe sample not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


def _site_summary_payload(summary: LinkSiteSummaryRecord) -> LinkSiteSummaryResponse:
    return LinkSiteSummaryResponse(
        site_id=summary.site_id,
        site_name=summary.site_name,
        site_tz=summary.site_tz,
        link_state=summary.link_state,
        active_connection=(
            _connection_payload(summary.active_connection)
            if summary.active_connection is not None
            else None
        ),
        connection_count=summary.connection_count,
        metered_connection_count=summary.metered_connection_count,
        latest_probe=(
            _probe_payload(summary.latest_probe)
            if summary.latest_probe is not None
            else None
        ),
        queue_depth={str(lane): count for lane, count in summary.queue_depth.items()},
        queued_bytes=summary.queued_bytes,
        budget=_budget_payload(summary.budget) if summary.budget is not None else None,
        last_sync_at=summary.last_sync_at,
        passport_hash=summary.passport_hash,
    )


async def _ensure_tenant_site(
    services: AppServices,
    tenant_context: TenantContext,
    site_id: UUID,
) -> None:
    try:
        await services.sites.get_site(tenant_context, site_id)
    except HTTPException:
        raise


def _reject_null_required_connection_fields(updates: dict[str, object]) -> None:
    null_fields = sorted(
        field
        for field in REQUIRED_CONNECTION_PATCH_FIELDS
        if field in updates and updates[field] is None
    )
    if null_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Connection fields cannot be null: {', '.join(null_fields)}.",
        )


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


def _connection_payload(connection: LinkConnectionRecord) -> JsonObject:
    return {
        "id": str(connection.id),
        "tenant_id": str(connection.tenant_id),
        "site_id": str(connection.site_id),
        "label": connection.label,
        "transport_kind": connection.transport_kind,
        "provider": connection.provider,
        "status": connection.status,
        "priority_rank": connection.priority_rank,
        "availability_scope": connection.availability_scope,
        "metered": connection.metered,
        "monthly_bytes": connection.monthly_bytes,
        "bulk_daily_bytes": connection.bulk_daily_bytes,
        "expected_downlink_mbps": connection.expected_downlink_mbps,
        "expected_uplink_mbps": connection.expected_uplink_mbps,
        "expected_latency_ms": connection.expected_latency_ms,
        "packet_loss_percent": connection.packet_loss_percent,
        "last_seen_at": connection.last_seen_at.isoformat()
        if connection.last_seen_at is not None
        else None,
        "metadata": connection.metadata,
        "created_at": connection.created_at.isoformat(),
        "updated_at": connection.updated_at.isoformat(),
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
        "connection_id": str(probe.connection_id) if probe.connection_id is not None else None,
        "latency_ms": probe.latency_ms,
        "throughput_mbps": probe.throughput_mbps,
        "packet_loss_percent": probe.packet_loss_percent,
        "reachable": probe.reachable,
        "source": probe.source,
        "recorded_at": probe.recorded_at.isoformat(),
        "target_id": probe.target_id,
        "target_label": probe.target_label,
        "target_address": probe.target_address,
        "probe_type": probe.probe_type,
        "source_type": probe.source_type,
        "source_label": probe.source_label,
        "sample_kind": probe.sample_kind,
        "deleted_at": probe.deleted_at.isoformat() if probe.deleted_at is not None else None,
    }
