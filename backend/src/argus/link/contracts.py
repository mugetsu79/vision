from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

JsonObject = dict[str, object]

LinkState = Literal["unknown", "healthy", "degraded", "dark", "recovering", "port_wifi"]
LinkPriorityLane = Literal["safety", "evidence", "telemetry", "bulk"]

LINK_PRIORITY_ORDER: dict[LinkPriorityLane, int] = {
    "safety": 0,
    "evidence": 1,
    "telemetry": 2,
    "bulk": 3,
}


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
    latency_ms: int
    throughput_mbps: float
    packet_loss_percent: float
    reachable: bool
    source: str
    recorded_at: datetime


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
class BackpressureDecision:
    paused_lanes: set[LinkPriorityLane] = field(default_factory=set)
    allowed_lanes: set[LinkPriorityLane] = field(default_factory=set)
    reason: str = "link_healthy"
