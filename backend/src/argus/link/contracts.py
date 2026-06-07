from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

JsonObject = dict[str, object]

LinkState = Literal["unknown", "healthy", "degraded", "dark", "recovering", "port_wifi"]
LinkPriorityLane = Literal["safety", "evidence", "telemetry", "bulk"]
LinkTransportKind = Literal["satellite", "lte", "5g", "wifi", "fiber", "ethernet", "other"]
LinkConnectionStatus = Literal["unknown", "online", "degraded", "offline", "blocked", "recovering"]
LinkAvailabilityScope = Literal["always", "remote", "nearby", "local", "maintenance"]
LinkProbeType = Literal["icmp", "tcp", "http", "https", "manual"]
LinkProbeSourceType = Literal["manual", "backend_synthetic", "edge_agent", "provider_api", "import"]
LinkProbeSampleKind = Literal["manual", "automated", "imported"]

LINK_PRIORITY_ORDER: dict[LinkPriorityLane, int] = {
    "safety": 0,
    "evidence": 1,
    "telemetry": 2,
    "bulk": 3,
}


@dataclass(frozen=True, slots=True)
class LinkConnectionRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    label: str
    transport_kind: LinkTransportKind
    provider: str | None
    status: LinkConnectionStatus
    priority_rank: int
    availability_scope: LinkAvailabilityScope
    metered: bool
    monthly_bytes: int | None
    bulk_daily_bytes: int | None
    expected_downlink_mbps: float | None
    expected_uplink_mbps: float | None
    expected_latency_ms: int | None
    packet_loss_percent: float | None
    last_seen_at: datetime | None
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class LinkBudgetSnapshot:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    monthly_bytes: int
    bulk_daily_bytes: int
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class LinkQueueItemRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    priority_lane: LinkPriorityLane
    byte_size: int
    source_object_type: str
    source_object_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    camera_id: UUID | None = None
    incident_id: UUID | None = None
    evidence_artifact_id: UUID | None = None
    last_successful_transfer_at: datetime | None = None
    paused_at: datetime | None = None
    pause_reason: str | None = None


@dataclass(frozen=True, slots=True)
class LinkTransferAttemptRecord:
    id: UUID
    queue_item_id: UUID
    status: str
    bytes_transferred: int
    created_at: datetime
    resume_token: str | None = None
    interruption_reason: str | None = None


@dataclass(frozen=True, slots=True)
class LinkHealthProbeRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    connection_id: UUID | None
    latency_ms: int
    throughput_mbps: float
    packet_loss_percent: float
    reachable: bool
    source: str
    recorded_at: datetime
    target_id: str | None = None
    target_label: str | None = None
    target_address: str | None = None
    probe_type: LinkProbeType | None = None
    source_type: LinkProbeSourceType = "manual"
    source_label: str | None = None
    sample_kind: LinkProbeSampleKind = "manual"
    deleted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class LinkPassportSnapshotRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    link_state: LinkState
    passport_hash: str
    payload: JsonObject
    created_at: datetime
    camera_id: UUID | None = None
    incident_id: UUID | None = None
    evidence_artifact_id: UUID | None = None
    pack_id: str | None = None
    last_sync_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class LinkSiteSummaryRecord:
    site_id: UUID
    site_name: str
    site_tz: str
    link_state: LinkState
    active_connection: LinkConnectionRecord | None
    connection_count: int
    metered_connection_count: int
    latest_probe: LinkHealthProbeRecord | None
    queue_depth: dict[LinkPriorityLane, int]
    queued_bytes: int
    budget: LinkBudgetSnapshot | None
    last_sync_at: datetime | None
    passport_hash: str


@dataclass(frozen=True, slots=True)
class BackpressureDecision:
    paused_lanes: set[LinkPriorityLane] = field(default_factory=set)
    allowed_lanes: set[LinkPriorityLane] = field(default_factory=set)
    reason: str = "link_healthy"
