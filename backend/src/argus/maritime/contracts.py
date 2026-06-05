from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

JsonObject = dict[str, object]
VoyageStatus = Literal["planned", "active", "completed", "cancelled"]
PortCallStatus = Literal["scheduled", "arrived", "alongside", "departed", "cancelled"]


@dataclass(frozen=True, slots=True)
class MaritimeRuntimeContribution:
    pack_id: str
    manifest_version: str
    enabled: bool
    implementation_commitment: bool
    required_core_capabilities: list[str]
    engine_required_capabilities: list[str]
    scene_templates: list[JsonObject] = field(default_factory=list)
    model_presets: JsonObject = field(default_factory=dict)
    evidence_fields: list[str] = field(default_factory=list)
    integrations: list[JsonObject] = field(default_factory=list)
    ui_labels: dict[str, str] = field(default_factory=dict)
    ui_panels: list[str] = field(default_factory=list)
    billing_labels: list[str] = field(default_factory=list)
    billing_meters: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MaritimeVesselRecord:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    imo_number: str | None = None
    mmsi: str | None = None
    call_sign: str | None = None
    flag_state: str | None = None
    vessel_type: str | None = None
    owner_label: str | None = None
    manager_label: str | None = None
    charterer_label: str | None = None
    active: bool = True
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MaritimeVoyageRecord:
    id: UUID
    tenant_id: UUID
    vessel_id: UUID
    name: str
    status: VoyageStatus
    created_at: datetime
    updated_at: datetime
    voyage_number: str | None = None
    origin: str | None = None
    destination: str | None = None
    scheduled_departure_at: datetime | None = None
    scheduled_arrival_at: datetime | None = None
    actual_departure_at: datetime | None = None
    actual_arrival_at: datetime | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MaritimePortCallRecord:
    id: UUID
    tenant_id: UUID
    vessel_id: UUID
    voyage_id: UUID
    port_name: str
    status: PortCallStatus
    created_at: datetime
    updated_at: datetime
    un_locode: str | None = None
    terminal_name: str | None = None
    berth: str | None = None
    eta: datetime | None = None
    ata: datetime | None = None
    etd: datetime | None = None
    atd: datetime | None = None
    link_profile: str | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MaritimeRoleRecord:
    id: UUID
    tenant_id: UUID
    label: str
    created_at: datetime
    updated_at: datetime
    vessel_id: UUID | None = None
    active: bool = True
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MaritimeWatchRotationRecord:
    id: UUID
    tenant_id: UUID
    label: str
    created_at: datetime
    updated_at: datetime
    vessel_id: UUID | None = None
    member_user_ids: list[str] = field(default_factory=list)
    metadata: JsonObject = field(default_factory=dict)
