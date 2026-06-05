from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

JsonObject = dict[str, object]
VoyageStatus = Literal["planned", "active", "completed", "cancelled"]
PortCallStatus = Literal["scheduled", "arrived", "alongside", "departed", "cancelled"]
CarrierStatus = Literal["unknown", "online", "degraded", "offline", "blocked"]
CarrierLinkState = Literal[
    "unknown",
    "satellite_good",
    "satellite_degraded",
    "port_wifi",
    "dark",
    "recovering",
]


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


@dataclass(frozen=True, slots=True)
class MaritimeAISPositionRecord:
    id: UUID
    tenant_id: UUID
    vessel_id: UUID
    source: str
    received_at: datetime
    reported_at: datetime
    mmsi: str
    latitude: float
    longitude: float
    raw_payload: JsonObject
    created_at: datetime
    speed_over_ground: float | None = None
    course_over_ground: float | None = None
    heading: float | None = None
    navigational_status: str | None = None


@dataclass(frozen=True, slots=True)
class MaritimeNMEAReadingRecord:
    id: UUID
    tenant_id: UUID
    vessel_id: UUID
    source: str
    received_at: datetime
    sentence_type: str
    values: JsonObject
    raw_sentence: str
    created_at: datetime
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class MaritimeCarrierTerminalRecord:
    id: UUID
    tenant_id: UUID
    vessel_id: UUID
    terminal_id: str
    provider: str
    status: CarrierStatus
    link_state: CarrierLinkState
    last_seen_at: datetime
    raw_payload: JsonObject
    created_at: datetime
    updated_at: datetime
    downlink_mbps: float | None = None
    uplink_mbps: float | None = None
    latency_ms: float | None = None
    packet_loss_percent: float | None = None


@dataclass(frozen=True, slots=True)
class MaritimeTelemetryIngestEventRecord:
    id: UUID
    tenant_id: UUID
    source: str
    event_type: str
    status: str
    raw_payload: JsonObject
    created_at: datetime
    vessel_id: UUID | None = None
    summary: str | None = None
    failure_count: int = 0


@dataclass(frozen=True, slots=True)
class MaritimeTelemetrySnapshot:
    vessel_id: UUID
    latest_ais_position: MaritimeAISPositionRecord | None = None
    carrier_terminal: MaritimeCarrierTerminalRecord | None = None
    recent_nmea_readings: list[MaritimeNMEAReadingRecord] = field(default_factory=list)
    recent_ingest_events: list[MaritimeTelemetryIngestEventRecord] = field(
        default_factory=list
    )


@dataclass(frozen=True, slots=True)
class MaritimeEvidenceContextRecord:
    id: UUID
    tenant_id: UUID
    incident_id: UUID | None
    camera_id: UUID | None
    incident_time: datetime | None
    resolution_source: str
    telemetry_freshness: JsonObject
    partial: bool
    created_at: datetime
    updated_at: datetime
    vessel_id: UUID | None = None
    voyage_id: UUID | None = None
    port_call_id: UUID | None = None
    vessel_name: str | None = None
    port_name: str | None = None
    ais_position: JsonObject | None = None
    carrier_terminal: JsonObject | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MaritimeEvidenceExportRecord:
    id: UUID
    tenant_id: UUID
    incident_id: UUID
    metadata: JsonObject
    artifact_hashes: dict[str, str]
    created_at: datetime
