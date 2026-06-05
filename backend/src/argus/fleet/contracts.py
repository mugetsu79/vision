from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

JsonObject = dict[str, object]

HeartbeatStatus = Literal["unknown", "healthy", "stale", "offline"]
FleetLinkState = Literal["unknown", "healthy", "degraded", "dark", "recovering", "port_wifi"]
RuntimeStatus = Literal["unknown", "running", "degraded", "stopped"]
FleetIntegrityStatus = Literal["unknown", "ok", "mismatch"]
AssignmentAssigneeType = Literal["support_queue", "user", "team", "service_account"]
FleetExceptionKind = Literal[
    "active_incident",
    "stopped_worker",
    "privacy_mismatch",
    "model_artifact_mismatch",
    "degraded_link",
    "evidence_backlog",
    "stale_heartbeat",
]

EXCEPTION_ATTENTION_ORDER: dict[FleetExceptionKind, int] = {
    "active_incident": 0,
    "stopped_worker": 1,
    "privacy_mismatch": 2,
    "model_artifact_mismatch": 3,
    "degraded_link": 4,
    "evidence_backlog": 5,
    "stale_heartbeat": 6,
}


@dataclass(frozen=True, slots=True)
class SiteGroup:
    id: UUID
    tenant_id: UUID
    label: str
    kind: str
    created_at: datetime
    updated_at: datetime
    pack_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SiteHierarchyNode:
    id: str
    tenant_id: UUID
    label: str
    kind: str
    sort_order: int
    parent_id: str | None = None
    site_id: UUID | None = None
    pack_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SiteHierarchy:
    tenant_id: UUID
    nodes: list[SiteHierarchyNode] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SiteState:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    heartbeat_status: HeartbeatStatus
    link_state: FleetLinkState
    runtime_status: RuntimeStatus
    evidence_backlog_count: int
    active_incident_count: int
    privacy_status: FleetIntegrityStatus
    model_artifact_status: FleetIntegrityStatus
    created_at: datetime
    updated_at: datetime
    pack_id: str | None = None
    last_heartbeat_at: datetime | None = None
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SiteAssignment:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    assignee_type: AssignmentAssigneeType
    assignee_id: str
    created_at: datetime
    updated_at: datetime
    rotation_group_id: UUID | None = None
    pack_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RotationGroup:
    id: UUID
    tenant_id: UUID
    label: str
    member_user_ids: list[str]
    created_at: datetime
    updated_at: datetime
    pack_labels: dict[str, str] = field(default_factory=dict)
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FleetException:
    id: str
    kind: FleetExceptionKind
    attention_rank: int
    tenant_id: UUID | None = None
    site_id: UUID | None = None
    count: int | None = None
    pack_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)
