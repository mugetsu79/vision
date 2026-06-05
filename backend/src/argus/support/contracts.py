from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

JsonObject = dict[str, object]


@dataclass(frozen=True, slots=True)
class SupportBundleRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    payload: JsonObject
    created_at: datetime
    node_id: UUID | None = None
    pack_id: str | None = None
    include_logs: bool = False


@dataclass(frozen=True, slots=True)
class SupportSessionRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    operator_id: str
    status: str
    started_at: datetime
    updated_at: datetime
    node_id: UUID | None = None
    ended_at: datetime | None = None
    billable_duration_minutes: int = 0
    usage_meter_key: str = "support_session_hour"
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SupportTunnelRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    node_id: UUID
    transport: str
    status: str
    credential_ref: str
    credential_ref_hash: str
    relay_host: str
    allowed_ports: list[int]
    dispatch_method: str
    requested_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BreakGlassAccessRecord:
    id: UUID
    reason: str
    scope: JsonObject
    actor_id: str
    approver_id: str
    started_at: datetime
    updated_at: datetime
    tenant_id: UUID | None = None
    ended_at: datetime | None = None
    closure_notes: str | None = None
    audit_payload: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OnboardingCheck:
    key: str
    label: str
    status: str
    details: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OnboardingCheckRunRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    checks: list[OnboardingCheck]
    created_at: datetime
    pack_id: str | None = None
    metadata: JsonObject = field(default_factory=dict)
