from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field, model_validator

from argus.api.contracts import SiteResponse, TenantContext
from argus.api.dependencies import (
    SupervisorOrAdminTenantDependency,
    get_app_services,
    get_tenant_context,
)
from argus.compat import UTC
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
    LinkReflectorProfileRecord,
    LinkSiteSummaryRecord,
    LinkTransportKind,
)
from argus.link.probe_runner import (
    ProbeTarget,
    ThroughputProbeTarget,
    measure_backend_throughput,
    run_backend_probe,
)
from argus.link.reflector import start_reflector, stop_reflector
from argus.link.reflector_profiles import decrypt_reflector_secret
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

router = APIRouter(prefix="/api/v1/link", tags=["link"])

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
PriorityLaneQuery = Annotated[LinkPriorityLane, Query()]
RemainingBudgetBytesQuery = Annotated[int, Query(ge=0)]
LinkEdgeProbeMethod = Literal["icmp_sequence", "udp_sequence"]
LinkSiteRole = Literal["edge", "control_plane"]
LinkReflectorSecretState = Literal["missing", "present"]
LinkControlTargetMode = Literal["https_only", "udp_reflector", "https_and_udp_reflector"]
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
    target_site_id: UUID | None = None
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
    measurement_metadata: JsonObject = Field(default_factory=dict)


class LinkEdgeProbeSampleCreate(BaseModel):
    agent_id: str = Field(min_length=1, max_length=96)
    agent_label: str | None = Field(default=None, max_length=128)
    method: LinkEdgeProbeMethod = "icmp_sequence"
    packet_count: int = Field(gt=0, le=10_000)
    packets_received: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    jitter_ms: float | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    dscp: int | None = Field(default=None, ge=0, le=63)
    measured_at: datetime | None = None
    measurement_metadata: JsonObject = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_packet_counts(self) -> LinkEdgeProbeSampleCreate:
        if self.packets_received > self.packet_count:
            raise ValueError("packets_received cannot exceed packet_count.")
        return self


class LinkPolicyUpdate(BaseModel):
    policy: dict[str, object] = Field(default_factory=dict)


class LinkReflectorProfileUpdate(BaseModel):
    public_address: str | None = Field(default=None, max_length=255)
    bind_address: str | None = Field(default=None, max_length=64)
    udp_port: int | None = Field(default=None, ge=1, le=65_535)
    allowed_edge_site_ids: list[UUID] | None = None
    allowed_source_cidrs: list[str] | None = None
    rate_limit_pps_per_source: int | None = Field(default=None, ge=0)


class LinkReflectorProfileResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID
    profile_kind: str
    enabled: bool
    mode: str
    public_address: str | None
    bind_address: str
    udp_port: int
    key_id: str
    allowed_edge_site_ids: list[UUID]
    allowed_source_cidrs: list[str]
    rate_limit_pps_per_source: int
    last_status: str
    last_error: str | None
    secret_state: LinkReflectorSecretState
    created_at: datetime
    updated_at: datetime


class LinkMasterControlTargetCreate(BaseModel):
    mode: LinkControlTargetMode
    connection_id: UUID | None = None
    connection_label: str = Field(default="Vezor control", min_length=1, max_length=160)
    address: str | None = None
    interval_seconds: int = Field(default=300, ge=30)
    packet_count: int = Field(default=50, gt=0, le=10_000)
    packet_spacing_ms: int = Field(default=100, ge=1)
    loss_timeout_ms: int = Field(default=1000, ge=1)
    dscp: int | None = Field(default=None, ge=0, le=63)


class LinkMasterReflectorEdgeAgentConfigResponse(BaseModel):
    site_id: UUID
    target_id: str
    target_site_id: UUID
    method: Literal["udp_sequence"]
    reflector_address: str
    reflector_port: int
    reflector_key_id: str
    reflector_secret: str
    packet_count: int
    packet_spacing_ms: int
    loss_timeout_ms: int
    dscp: int | None = None


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
    site_role: LinkSiteRole = "edge"
    capabilities: dict[str, bool] = Field(default_factory=dict)
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


@router.get("/reflectors/master", response_model=LinkReflectorProfileResponse)
async def get_master_reflector_profile(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> LinkReflectorProfileResponse:
    master_site = await _master_control_plane_site(services, tenant_context)
    profile = await services.link.aget_master_reflector_profile(
        tenant_id=tenant_context.tenant_id,
        site_id=master_site.id,
    )
    return _reflector_profile_payload(
        profile
        or _default_master_reflector_profile(
            tenant_id=tenant_context.tenant_id,
            site_id=master_site.id,
        )
    )


@router.put("/reflectors/master", response_model=LinkReflectorProfileResponse)
async def put_master_reflector_profile(
    request: Request,
    payload: LinkReflectorProfileUpdate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> LinkReflectorProfileResponse:
    master_site = await _master_control_plane_site(services, tenant_context)
    try:
        profile = await services.link.aupdate_master_reflector_profile(
            tenant_id=tenant_context.tenant_id,
            site_id=master_site.id,
            public_address=payload.public_address,
            bind_address=payload.bind_address,
            udp_port=payload.udp_port,
            allowed_edge_site_ids=payload.allowed_edge_site_ids,
            allowed_source_cidrs=payload.allowed_source_cidrs,
            rate_limit_pps_per_source=payload.rate_limit_pps_per_source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    profile = await _reconcile_master_reflector_runtime(
        request,
        services,
        tenant_context,
        profile,
    )
    return _reflector_profile_payload(profile)


@router.post("/reflectors/master/enable", response_model=LinkReflectorProfileResponse)
async def enable_master_reflector_profile(
    request: Request,
    payload: LinkReflectorProfileUpdate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> LinkReflectorProfileResponse:
    master_site = await _master_control_plane_site(services, tenant_context)
    existing = await services.link.aensure_master_reflector_profile(
        tenant_id=tenant_context.tenant_id,
        site_id=master_site.id,
        public_address=payload.public_address,
    )
    public_address = payload.public_address or existing.public_address
    try:
        profile = await services.link.aenable_master_reflector_profile(
            tenant_id=tenant_context.tenant_id,
            site_id=master_site.id,
            public_address=public_address,
            bind_address=payload.bind_address or existing.bind_address,
            udp_port=payload.udp_port or existing.udp_port,
            rate_limit_pps_per_source=(
                payload.rate_limit_pps_per_source
                if payload.rate_limit_pps_per_source is not None
                else existing.rate_limit_pps_per_source
            ),
        )
        if payload.allowed_edge_site_ids is not None or payload.allowed_source_cidrs is not None:
            profile = await services.link.aupdate_master_reflector_profile(
                tenant_id=tenant_context.tenant_id,
                site_id=master_site.id,
                allowed_edge_site_ids=payload.allowed_edge_site_ids,
                allowed_source_cidrs=payload.allowed_source_cidrs,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    profile = await _reconcile_master_reflector_runtime(
        request,
        services,
        tenant_context,
        profile,
    )
    return _reflector_profile_payload(profile)


@router.post("/reflectors/master/disable", response_model=LinkReflectorProfileResponse)
async def disable_master_reflector_profile(
    request: Request,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> LinkReflectorProfileResponse:
    master_site = await _master_control_plane_site(services, tenant_context)
    profile = await services.link.adisable_master_reflector_profile(
        tenant_id=tenant_context.tenant_id,
        site_id=master_site.id,
    )
    profile = await _reconcile_master_reflector_runtime(
        request,
        services,
        tenant_context,
        profile,
    )
    return _reflector_profile_payload(profile)


@router.post("/reflectors/master/rotate-key", response_model=LinkReflectorProfileResponse)
async def rotate_master_reflector_key(
    request: Request,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> LinkReflectorProfileResponse:
    master_site = await _master_control_plane_site(services, tenant_context)
    profile = await services.link.arotate_master_reflector_key(
        tenant_id=tenant_context.tenant_id,
        site_id=master_site.id,
    )
    profile = await _reconcile_master_reflector_runtime(
        request,
        services,
        tenant_context,
        profile,
    )
    return _reflector_profile_payload(profile)


@router.get("/sites/summary", response_model=list[LinkSiteSummaryResponse])
async def get_link_site_summaries(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[LinkSiteSummaryResponse]:
    sites = await services.sites.list_link_performance_sites(tenant_context)
    summary_records = await services.link.alist_site_summaries(
        tenant_id=tenant_context.tenant_id,
        sites=[{"id": site.id, "name": site.name, "tz": site.tz} for site in sites],
    )
    sites_by_id = {site.id: site for site in sites}
    summaries: list[LinkSiteSummaryResponse] = []
    for summary in summary_records:
        site = sites_by_id[summary.site_id]
        site_role = _site_role(site)
        latest_probe = summary.latest_probe
        link_state = summary.link_state
        last_sync_at = summary.last_sync_at
        if site_role == "control_plane":
            target_probes = await services.link.alist_target_site_probes(
                tenant_id=tenant_context.tenant_id,
                target_site_id=summary.site_id,
            )
            latest_probe = target_probes[0] if target_probes else None
            link_state = services.link.derive_link_state(latest_probe)
            last_sync_at = latest_probe.recorded_at if latest_probe is not None else None
        summaries.append(
            _site_summary_payload(
                summary,
                site_role=site_role,
                latest_probe=latest_probe,
                link_state=link_state,
                last_sync_at=last_sync_at,
            )
        )
    return summaries


@router.get("/sites/{site_id}/status")
async def get_link_status(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    site = await _ensure_link_site(services, tenant_context, site_id)
    if _site_role(site) == "control_plane":
        return await _target_site_status_payload(
            services,
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
        )
    passport = await services.link.apreview_passport(
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
    await _ensure_link_edge_site(services, tenant_context, site_id)
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
    await _ensure_link_edge_site(services, tenant_context, site_id)
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
    await _ensure_link_edge_site(services, tenant_context, site_id)
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
    await _ensure_link_edge_site(services, tenant_context, site_id)
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


@router.post("/sites/{site_id}/control-targets/master", status_code=status.HTTP_201_CREATED)
async def post_master_control_target(
    site_id: UUID,
    payload: LinkMasterControlTargetCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_link_edge_site(services, tenant_context, site_id)
    master_site = await _master_control_plane_site(services, tenant_context)
    profile = await services.link.aensure_master_reflector_profile(
        tenant_id=tenant_context.tenant_id,
        site_id=master_site.id,
    )
    connection = await _connection_for_control_target(
        services,
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        connection_id=payload.connection_id,
        connection_label=payload.connection_label,
    )
    targets = _master_control_targets(payload, master_site=master_site, profile=profile)
    metadata = _metadata_with_master_control_targets(connection.metadata, targets)
    try:
        updated = await services.link.aupsert_connection(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
            connection_id=connection.id,
            label=connection.label,
            transport_kind=connection.transport_kind,
            provider=connection.provider,
            status=connection.status,
            priority_rank=connection.priority_rank,
            availability_scope=connection.availability_scope,
            metered=connection.metered,
            monthly_bytes=connection.monthly_bytes,
            bulk_daily_bytes=connection.bulk_daily_bytes,
            expected_downlink_mbps=connection.expected_downlink_mbps,
            expected_uplink_mbps=connection.expected_uplink_mbps,
            expected_latency_ms=connection.expected_latency_ms,
            packet_loss_percent=connection.packet_loss_percent,
            last_seen_at=connection.last_seen_at,
            metadata=metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _connection_payload(updated)


@router.get(
    "/sites/{site_id}/control-targets/master/edge-agent-config",
    response_model=LinkMasterReflectorEdgeAgentConfigResponse,
)
async def get_master_reflector_edge_agent_config(
    site_id: UUID,
    request: Request,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> LinkMasterReflectorEdgeAgentConfigResponse:
    return await _master_reflector_edge_agent_config(
        site_id=site_id,
        request=request,
        tenant_context=tenant_context,
        services=services,
    )


@router.get(
    "/control-targets/master/edge-agent-config",
    response_model=LinkMasterReflectorEdgeAgentConfigResponse,
)
async def get_my_master_reflector_edge_agent_config(
    request: Request,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> LinkMasterReflectorEdgeAgentConfigResponse:
    site_id = await services.operations.supervisor_edge_site_id(tenant_context)
    return await _master_reflector_edge_agent_config(
        site_id=site_id,
        request=request,
        tenant_context=tenant_context,
        services=services,
    )


async def _master_reflector_edge_agent_config(
    *,
    site_id: UUID,
    request: Request,
    tenant_context: TenantContext,
    services: AppServices,
) -> LinkMasterReflectorEdgeAgentConfigResponse:
    site = await _ensure_link_edge_site(services, tenant_context, site_id)
    await services.operations.assert_supervisor_edge_site_scope(tenant_context, site_id)
    master_site = await _master_control_plane_site(services, tenant_context)
    profile = await services.link.aget_master_reflector_profile(
        tenant_id=tenant_context.tenant_id,
        site_id=master_site.id,
    )
    if profile is None or not profile.enabled or profile.encrypted_secret is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Master reflector secret is not ready.",
        )
    profile = await _ensure_master_reflector_runtime_for_edge_agent_config(
        request=request,
        services=services,
        tenant_context=tenant_context,
        profile=profile,
    )
    target = await services.link.atarget_for_connection_metadata(
        tenant_id=tenant_context.tenant_id,
        site_id=site.id,
        target_id="vezor-master-udp-reflector",
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master UDP reflector target not found.",
        )
    secret = decrypt_reflector_secret(profile.encrypted_secret, settings=services.link.settings)
    return LinkMasterReflectorEdgeAgentConfigResponse(
        site_id=site.id,
        target_id="vezor-master-udp-reflector",
        target_site_id=master_site.id,
        method="udp_sequence",
        reflector_address=profile.public_address or profile.bind_address,
        reflector_port=profile.udp_port,
        reflector_key_id=profile.key_id,
        reflector_secret=secret,
        packet_count=_target_positive_int(target, "loss_packet_count", default=20),
        packet_spacing_ms=_target_positive_int(target, "loss_packet_spacing_ms", default=100),
        loss_timeout_ms=_target_positive_int(target, "loss_timeout_ms", default=1000),
        dscp=_target_optional_dscp(target),
    )


async def _ensure_master_reflector_runtime_for_edge_agent_config(
    *,
    request: Request,
    services: AppServices,
    tenant_context: TenantContext,
    profile: LinkReflectorProfileRecord,
) -> LinkReflectorProfileRecord:
    if not hasattr(request.app.state, "link_reflector_runtime"):
        return profile
    runtime = request.app.state.link_reflector_runtime
    if _reflector_runtime_matches_profile(runtime, profile):
        return profile

    reconciled = await _reconcile_master_reflector_runtime(
        request,
        services,
        tenant_context,
        profile,
    )
    if not _reflector_runtime_matches_profile(request.app.state.link_reflector_runtime, reconciled):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=reconciled.last_error or "Master UDP reflector is not listening.",
        )
    return reconciled


def _reflector_runtime_matches_profile(
    runtime: object | None,
    profile: LinkReflectorProfileRecord,
) -> bool:
    if runtime is None:
        return False
    if getattr(runtime, "bind_host", None) != profile.bind_address:
        return False
    if getattr(runtime, "port", None) != profile.udp_port:
        return False
    if getattr(runtime, "key_id", None) != profile.key_id:
        return False
    protocol = getattr(runtime, "protocol", None)
    if getattr(protocol, "rate_limit_pps", None) != profile.rate_limit_pps_per_source:
        return False
    allowed_networks = tuple(
        str(network) for network in getattr(protocol, "allowed_source_networks", ())
    )
    return allowed_networks == tuple(profile.allowed_source_cidrs)


@router.get("/sites/{site_id}/connections/selection")
async def get_link_connection_selection(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    priority_lane: PriorityLaneQuery = "bulk",
    remaining_budget_bytes: RemainingBudgetBytesQuery = 0,
) -> JsonObject | None:
    await _ensure_link_edge_site(services, tenant_context, site_id)
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
    await _ensure_link_edge_site(services, tenant_context, site_id)
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
    await _ensure_link_edge_site(services, tenant_context, site_id)
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
    await _ensure_link_edge_site(services, tenant_context, site_id)
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
    site = await _ensure_link_site(services, tenant_context, site_id)
    if _site_role(site) == "control_plane":
        probes = await services.link.alist_target_site_probes(
            tenant_id=tenant_context.tenant_id,
            target_site_id=site_id,
        )
    else:
        probes = await services.link.alist_probes(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
        )
    return [_probe_payload(probe) for probe in probes]


@router.post("/sites/{site_id}/probes", status_code=status.HTTP_201_CREATED)
async def post_link_probe(
    site_id: UUID,
    payload: LinkProbeCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_link_edge_site(
        services,
        tenant_context,
        site_id,
        detail="Core Link probes can only be recorded for edge sites.",
    )
    if payload.target_site_id is not None:
        await _ensure_link_site(services, tenant_context, payload.target_site_id)
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
            target_site_id=payload.target_site_id,
            target_id=payload.target_id,
            target_label=payload.target_label,
            target_address=payload.target_address,
            probe_type=payload.probe_type,
            source_type=payload.source_type,
            source_label=payload.source_label,
            sample_kind=payload.sample_kind,
            measurement_metadata=payload.measurement_metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _probe_payload(probe)


@router.post(
    "/sites/{site_id}/probe-targets/{target_id}/edge-samples",
    status_code=status.HTTP_201_CREATED,
)
async def post_link_edge_probe_sample(
    site_id: UUID,
    target_id: str,
    payload: LinkEdgeProbeSampleCreate,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_link_edge_site(
        services,
        tenant_context,
        site_id,
        detail="Core Link probes can only be recorded for edge sites.",
    )
    await services.operations.assert_supervisor_edge_site_scope(tenant_context, site_id)
    target = await services.link.atarget_for_connection_metadata(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        target_id=target_id,
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Probe target not found.")
    if payload.method == "udp_sequence" and target.get("probe_type") != "udp":
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="UDP sequence samples require a UDP probe target.",
        )

    target_site_id = await _target_site_id_from_metadata(services, tenant_context, target)
    packets_lost = payload.packet_count - payload.packets_received
    packet_loss_percent = round((packets_lost / payload.packet_count) * 100, 4)
    source_label = payload.agent_label or payload.agent_id
    probe = await services.link.arecord_probe(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        latency_ms=payload.latency_ms,
        throughput_mbps=0.0,
        packet_loss_percent=packet_loss_percent,
        reachable=payload.packets_received > 0,
        source=f"edge_agent:{payload.agent_id}",
        target_site_id=target_site_id,
        target_id=target_id,
        target_label=_target_text(target, "label"),
        target_address=_target_text(target, "address"),
        probe_type=_edge_probe_type_from_metadata(target, payload.method),
        source_type="edge_agent",
        source_label=source_label,
        sample_kind="automated",
        measurement_metadata=_edge_measurement_metadata(payload, packets_lost),
    )
    return _probe_payload(probe)


@router.delete("/sites/{site_id}/probes/{probe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link_probe(
    site_id: UUID,
    probe_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    await _ensure_link_edge_site(
        services,
        tenant_context,
        site_id,
        detail="Core Link probes can only be recorded for edge sites.",
    )
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


@router.post(
    "/sites/{site_id}/probe-targets/{target_id}/run",
    status_code=status.HTTP_201_CREATED,
)
async def run_link_probe_target(
    site_id: UUID,
    target_id: str,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_link_edge_site(
        services,
        tenant_context,
        site_id,
        detail="Core Link probes can only be recorded for edge sites.",
    )
    target = await services.link.atarget_for_connection_metadata(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        target_id=target_id,
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Probe target not found.")
    target_site_id = await _target_site_id_from_metadata(services, tenant_context, target)
    result = await run_backend_probe(_probe_target_from_metadata(target))
    probe = await services.link.arecord_probe(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        latency_ms=result.latency_ms,
        throughput_mbps=result.throughput_mbps,
        packet_loss_percent=result.packet_loss_percent,
        reachable=result.reachable,
        source=result.source,
        target_site_id=target_site_id,
        target_id=result.target_id,
        target_label=result.target_label,
        target_address=result.target_address,
        probe_type=result.probe_type,
        source_type=result.source_type,
        source_label=result.source_label,
        sample_kind=result.sample_kind,
    )
    return _probe_payload(probe)


@router.post(
    "/sites/{site_id}/probe-targets/{target_id}/measure-throughput",
    status_code=status.HTTP_201_CREATED,
)
async def measure_link_probe_target_throughput(
    site_id: UUID,
    target_id: str,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_link_edge_site(
        services,
        tenant_context,
        site_id,
        detail="Core Link probes can only be recorded for edge sites.",
    )
    target = await services.link.atarget_for_connection_metadata(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        target_id=target_id,
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Probe target not found.")
    target_site_id = await _target_site_id_from_metadata(services, tenant_context, target)
    result = await measure_backend_throughput(_throughput_target_from_metadata(target))
    probe = await services.link.arecord_probe(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
        latency_ms=result.latency_ms,
        throughput_mbps=result.throughput_mbps,
        packet_loss_percent=result.packet_loss_percent,
        reachable=result.reachable,
        source=result.source,
        target_site_id=target_site_id,
        target_id=result.target_id,
        target_label=result.target_label,
        target_address=result.target_address,
        probe_type=result.probe_type,
        source_type=result.source_type,
        source_label=result.source_label,
        sample_kind=result.sample_kind,
    )
    return _probe_payload(probe)


@router.get("/sites/{site_id}/policies")
async def get_link_policies(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_link_edge_site(services, tenant_context, site_id)
    return await services.link.aget_policy(tenant_id=tenant_context.tenant_id, site_id=site_id)


@router.put("/sites/{site_id}/policies")
async def put_link_policies(
    site_id: UUID,
    payload: LinkPolicyUpdate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_link_edge_site(services, tenant_context, site_id)
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


def _site_summary_payload(
    summary: LinkSiteSummaryRecord,
    *,
    site_role: LinkSiteRole,
    latest_probe: LinkHealthProbeRecord | None,
    link_state: str,
    last_sync_at: datetime | None,
) -> LinkSiteSummaryResponse:
    return LinkSiteSummaryResponse(
        site_id=summary.site_id,
        site_name=summary.site_name,
        site_tz=summary.site_tz,
        site_role=site_role,
        capabilities=_site_capabilities(site_role),
        link_state=link_state,
        active_connection=(
            _connection_payload(summary.active_connection)
            if summary.active_connection is not None
            and site_role == "edge"
            else None
        ),
        connection_count=summary.connection_count,
        metered_connection_count=summary.metered_connection_count,
        latest_probe=(
            _probe_payload(latest_probe)
            if latest_probe is not None
            else None
        ),
        queue_depth={str(lane): count for lane, count in summary.queue_depth.items()},
        queued_bytes=summary.queued_bytes,
        budget=(
            _budget_payload(summary.budget)
            if summary.budget is not None and site_role == "edge"
            else None
        ),
        last_sync_at=last_sync_at,
        passport_hash=summary.passport_hash,
    )


def _site_role(site: SiteResponse) -> LinkSiteRole:
    return "control_plane" if site.site_kind == "control_plane" else "edge"


def _site_capabilities(site_role: LinkSiteRole) -> dict[str, bool]:
    return {
        "can_configure_links": site_role == "edge",
        "can_record_manual_samples": site_role == "edge",
        "can_receive_edge_probes": site_role == "control_plane",
    }


async def _ensure_link_site(
    services: AppServices,
    tenant_context: TenantContext,
    site_id: UUID,
) -> SiteResponse:
    return await services.sites.get_site(tenant_context, site_id)


async def _ensure_link_edge_site(
    services: AppServices,
    tenant_context: TenantContext,
    site_id: UUID,
    *,
    detail: str = "Core Link can only be configured for edge sites.",
) -> SiteResponse:
    site = await _ensure_link_site(services, tenant_context, site_id)
    if not await services.sites.is_edge_site(tenant_context, site_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    return site


async def _master_control_plane_site(
    services: AppServices,
    tenant_context: TenantContext,
) -> SiteResponse:
    sites = await services.sites.list_link_performance_sites(tenant_context)
    for site in sites:
        if _site_role(site) == "control_plane":
            return site
    return await services.sites.ensure_control_plane_site(tenant_context)


def _reflector_profile_payload(
    profile: LinkReflectorProfileRecord,
) -> LinkReflectorProfileResponse:
    return LinkReflectorProfileResponse(
        id=profile.id,
        tenant_id=profile.tenant_id,
        site_id=profile.site_id,
        profile_kind=profile.profile_kind,
        enabled=profile.enabled,
        mode=profile.mode,
        public_address=profile.public_address,
        bind_address=profile.bind_address,
        udp_port=profile.udp_port,
        key_id=profile.key_id,
        allowed_edge_site_ids=profile.allowed_edge_site_ids,
        allowed_source_cidrs=profile.allowed_source_cidrs,
        rate_limit_pps_per_source=profile.rate_limit_pps_per_source,
        last_status=profile.last_status,
        last_error=profile.last_error,
        secret_state="present" if profile.encrypted_secret is not None else "missing",
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _default_master_reflector_profile(
    *,
    tenant_id: UUID,
    site_id: UUID,
) -> LinkReflectorProfileRecord:
    now = datetime.now(tz=UTC)
    return LinkReflectorProfileRecord(
        id=uuid5(NAMESPACE_URL, f"argus:link-reflector-profile:{tenant_id}:{site_id}:master"),
        tenant_id=tenant_id,
        site_id=site_id,
        profile_kind="master",
        enabled=False,
        mode="vezor_udp_sequence",
        public_address=None,
        bind_address="0.0.0.0",
        udp_port=8622,
        key_id="master-reflector-default",
        encrypted_secret=None,
        allowed_edge_site_ids=[],
        allowed_source_cidrs=[],
        rate_limit_pps_per_source=100,
        last_status="disabled",
        last_error=None,
        created_at=now,
        updated_at=now,
    )


async def _reconcile_master_reflector_runtime(
    request: Request,
    services: AppServices,
    tenant_context: TenantContext,
    profile: LinkReflectorProfileRecord,
) -> LinkReflectorProfileRecord:
    if not hasattr(request.app.state, "link_reflector_runtime"):
        return profile

    stop_reflector(request.app.state.link_reflector_runtime)
    request.app.state.link_reflector_runtime = None

    if not profile.enabled:
        return profile
    if profile.encrypted_secret is None:
        return await services.link.aupdate_master_reflector_profile(
            tenant_id=tenant_context.tenant_id,
            site_id=profile.site_id,
            last_status="unhealthy",
            last_error="Reflector profile is enabled without a secret.",
        )

    try:
        secret = decrypt_reflector_secret(
            profile.encrypted_secret,
            settings=services.link.settings,
        )
        runtime = await start_reflector(
            bind_host=profile.bind_address,
            port=profile.udp_port,
            secret=secret.encode("utf-8"),
            key_id=profile.key_id,
            rate_limit_pps=profile.rate_limit_pps_per_source,
            allowed_source_cidrs=profile.allowed_source_cidrs,
        )
    except Exception as exc:
        return await services.link.aupdate_master_reflector_profile(
            tenant_id=tenant_context.tenant_id,
            site_id=profile.site_id,
            last_status="unhealthy",
            last_error=str(exc),
        )

    request.app.state.link_reflector_runtime = runtime
    return await services.link.aupdate_master_reflector_profile(
        tenant_id=tenant_context.tenant_id,
        site_id=profile.site_id,
        last_status="listening",
        last_error=None,
    )


async def _connection_for_control_target(
    services: AppServices,
    *,
    tenant_id: UUID,
    site_id: UUID,
    connection_id: UUID | None,
    connection_label: str,
) -> LinkConnectionRecord:
    if connection_id is not None:
        connection = await services.link.aget_connection(
            tenant_id=tenant_id,
            site_id=site_id,
            connection_id=connection_id,
        )
        if connection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found.",
            )
        return connection
    return await services.link.aupsert_connection(
        tenant_id=tenant_id,
        site_id=site_id,
        label=connection_label,
        transport_kind="other",
        provider="Vezor",
        status="unknown",
        priority_rank=100,
        availability_scope="always",
        metered=False,
        metadata={"monitoring_targets": []},
    )


def _master_control_targets(
    payload: LinkMasterControlTargetCreate,
    *,
    master_site: SiteResponse,
    profile: LinkReflectorProfileRecord,
) -> list[JsonObject]:
    targets: list[JsonObject] = []
    if payload.mode in {"https_only", "https_and_udp_reflector"}:
        targets.append(_master_https_target(payload, master_site=master_site, profile=profile))
    if payload.mode in {"udp_reflector", "https_and_udp_reflector"}:
        targets.append(
            _master_udp_reflector_target(payload, master_site=master_site, profile=profile)
        )
    return targets


def _master_https_target(
    payload: LinkMasterControlTargetCreate,
    *,
    master_site: SiteResponse,
    profile: LinkReflectorProfileRecord,
) -> JsonObject:
    return {
        "id": "vezor-master-https",
        "label": "Vezor Master API",
        "address": payload.address or _default_master_https_address(profile),
        "target_site_id": str(master_site.id),
        "probe_type": "https",
        "purpose": "vezor_control",
        "monitoring": {
            "enabled": True,
            "source_type": "edge_agent",
            "interval_seconds": payload.interval_seconds,
        },
        "loss_method": "icmp_sequence",
        "loss_packet_count": 20,
    }


def _master_udp_reflector_target(
    payload: LinkMasterControlTargetCreate,
    *,
    master_site: SiteResponse,
    profile: LinkReflectorProfileRecord,
) -> JsonObject:
    if not profile.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Master reflector is disabled.",
        )
    reflector_address = payload.address or profile.public_address
    if not reflector_address:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Master reflector public address is not configured.",
        )
    target: JsonObject = {
        "id": "vezor-master-udp-reflector",
        "label": "Vezor Master reflector",
        "address": reflector_address,
        "target_site_id": str(master_site.id),
        "probe_type": "udp",
        "purpose": "vezor_control",
        "monitoring": {
            "enabled": True,
            "source_type": "edge_agent",
            "interval_seconds": payload.interval_seconds,
        },
        "loss_method": "udp_sequence",
        "loss_packet_count": payload.packet_count,
        "loss_packet_spacing_ms": payload.packet_spacing_ms,
        "loss_timeout_ms": payload.loss_timeout_ms,
        "reflector_profile_id": "master-reflector-default",
        "reflector_address": reflector_address,
        "reflector_port": profile.udp_port,
        "reflector_mode": profile.mode,
        "reflector_key_id": profile.key_id,
    }
    if payload.dscp is not None:
        target["loss_dscp"] = payload.dscp
    return target


def _metadata_with_master_control_targets(
    metadata: Mapping[str, object],
    targets: list[JsonObject],
) -> JsonObject:
    updated = dict(metadata)
    existing_targets = [
        target
        for target in _metadata_targets(updated)
        if target.get("id") not in {"vezor-master-https", "vezor-master-udp-reflector"}
    ]
    updated["monitoring_targets"] = [*existing_targets, *targets]
    return updated


def _metadata_targets(metadata: Mapping[str, object]) -> list[JsonObject]:
    targets = metadata.get("monitoring_targets")
    if not isinstance(targets, list):
        return []
    return [dict(target) for target in targets if isinstance(target, Mapping)]


def _default_master_https_address(profile: LinkReflectorProfileRecord) -> str:
    if profile.public_address:
        return f"https://{profile.public_address.rstrip('/')}/healthz"
    return "https://vezor-master/healthz"


async def _target_site_status_payload(
    services: AppServices,
    *,
    tenant_id: UUID,
    site_id: UUID,
) -> JsonObject:
    probes = await services.link.alist_target_site_probes(
        tenant_id=tenant_id,
        target_site_id=site_id,
    )
    latest_probe = probes[0] if probes else None
    payload: JsonObject = {
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "site_id": str(site_id),
        "camera_id": None,
        "incident_id": None,
        "evidence_artifact_id": None,
        "pack_id": None,
        "link_state": services.link.derive_link_state(latest_probe),
        "active_connection": None,
        "connections": [],
        "budget": None,
        "queue_depth": {},
        "latest_probe": _probe_payload(latest_probe) if latest_probe is not None else None,
        "last_sync_at": latest_probe.recorded_at.isoformat() if latest_probe is not None else None,
    }
    payload["passport_hash"] = services.link.hash_passport_payload(payload)
    return payload


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
        "target_site_id": str(probe.target_site_id) if probe.target_site_id is not None else None,
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
        "measurement_metadata": probe.measurement_metadata,
    }


def _target_text(target: JsonObject, field: str) -> str | None:
    value = target.get(field)
    return value if isinstance(value, str) else None


def _target_positive_int(target: JsonObject, field: str, *, default: int) -> int:
    value = target.get(field)
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=f"Probe target {field} must be a positive integer.",
        ) from exc
    if parsed <= 0:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=f"Probe target {field} must be a positive integer.",
        )
    return parsed


def _target_optional_dscp(target: JsonObject) -> int | None:
    value = target.get("loss_dscp")
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Probe target loss_dscp must be between 0 and 63.",
        ) from exc
    if parsed < 0 or parsed > 63:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Probe target loss_dscp must be between 0 and 63.",
        )
    return parsed


async def _target_site_id_from_metadata(
    services: AppServices,
    tenant_context: TenantContext,
    target: JsonObject,
) -> UUID | None:
    value = target.get("target_site_id")
    if value is None:
        return None
    if isinstance(value, UUID):
        target_site_id = value
    elif isinstance(value, str):
        try:
            target_site_id = UUID(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail="Probe target target_site_id must be a UUID.",
            ) from exc
    else:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Probe target target_site_id must be a UUID.",
        )
    await _ensure_link_site(services, tenant_context, target_site_id)
    return target_site_id


def _edge_probe_type_from_metadata(
    target: JsonObject,
    method: LinkEdgeProbeMethod,
) -> LinkProbeType:
    probe_type = target.get("probe_type")
    if probe_type in {"icmp", "tcp", "http", "https", "udp"}:
        return cast(LinkProbeType, probe_type)
    return "icmp" if method == "icmp_sequence" else "udp"


def _edge_measurement_metadata(
    payload: LinkEdgeProbeSampleCreate,
    packets_lost: int,
) -> JsonObject:
    metadata: JsonObject = dict(payload.measurement_metadata)
    metadata.update(
        {
        "agent_id": payload.agent_id,
        "method": payload.method,
        "packet_count": payload.packet_count,
        "packets_received": payload.packets_received,
        "packets_lost": packets_lost,
        }
    )
    if payload.agent_label is not None:
        metadata["agent_label"] = payload.agent_label
    if payload.jitter_ms is not None:
        metadata["jitter_ms"] = payload.jitter_ms
    if payload.duration_ms is not None:
        metadata["duration_ms"] = payload.duration_ms
    if payload.dscp is not None:
        metadata["dscp"] = payload.dscp
    if payload.measured_at is not None:
        metadata["measured_at"] = payload.measured_at.isoformat()
    return metadata


def _probe_target_from_metadata(target: JsonObject) -> ProbeTarget:
    probe_type = target.get("probe_type")
    if probe_type not in {"icmp", "tcp", "http", "https"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported probe target type.",
        )
    target_id = target.get("id")
    label = target.get("label")
    address = target.get("address")
    if not isinstance(target_id, str) or not isinstance(label, str) or not isinstance(address, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Probe target is missing required fields.",
        )
    port_value = target.get("port")
    return ProbeTarget(
        target_id=target_id,
        label=label,
        address=address,
        probe_type=cast(LinkProbeType, probe_type),
        port=port_value if isinstance(port_value, int) else None,
    )


def _throughput_target_from_metadata(target: JsonObject) -> ThroughputProbeTarget:
    probe_target = _probe_target_from_metadata(target)
    throughput_test_url = target.get("throughput_test_url")
    throughput_test_max_bytes = target.get("throughput_test_max_bytes")
    return ThroughputProbeTarget(
        target_id=probe_target.target_id,
        label=probe_target.label,
        address=probe_target.address,
        probe_type=probe_target.probe_type,
        port=probe_target.port,
        throughput_test_url=(
            throughput_test_url if isinstance(throughput_test_url, str) else None
        ),
        throughput_test_max_bytes=(
            throughput_test_max_bytes
            if isinstance(throughput_test_max_bytes, int)
            else None
        ),
    )
