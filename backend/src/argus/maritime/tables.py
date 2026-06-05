from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from argus.models.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class MaritimeVessel(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "maritime_vessels"
    __table_args__ = (
        UniqueConstraint("tenant_id", "site_id", name="uq_maritime_vessels_tenant_site"),
        UniqueConstraint("tenant_id", "imo_number", name="uq_maritime_vessels_tenant_imo"),
        UniqueConstraint("tenant_id", "mmsi", name="uq_maritime_vessels_tenant_mmsi"),
        UniqueConstraint("tenant_id", "call_sign", name="uq_maritime_vessels_tenant_call_sign"),
        Index("ix_maritime_vessels_tenant_active", "tenant_id", "active"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    imo_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mmsi: Mapped[str | None] = mapped_column(String(16), nullable=True)
    call_sign: Mapped[str | None] = mapped_column(String(32), nullable=True)
    flag_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vessel_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    owner_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    manager_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    charterer_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class MaritimeVoyage(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "maritime_voyages"
    __table_args__ = (
        Index("ix_maritime_voyages_tenant_vessel", "tenant_id", "vessel_id"),
        Index(
            "ix_maritime_voyages_one_active_per_vessel",
            "tenant_id",
            "vessel_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    vessel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    voyage_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(160), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    scheduled_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scheduled_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class MaritimePortCall(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "maritime_port_calls"
    __table_args__ = (
        Index("ix_maritime_port_calls_tenant_voyage", "tenant_id", "voyage_id"),
        Index("ix_maritime_port_calls_tenant_vessel", "tenant_id", "vessel_id"),
        CheckConstraint(
            "status IN ('scheduled', 'arrived', 'alongside', 'departed', 'cancelled')",
            name="status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    vessel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=False,
    )
    voyage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_voyages.id"),
        nullable=False,
    )
    port_name: Mapped[str] = mapped_column(String(255), nullable=False)
    un_locode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    terminal_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    berth: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ata: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    etd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    atd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    link_profile: Mapped[str | None] = mapped_column(String(80), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class MaritimeRole(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "maritime_roles"
    __table_args__ = (
        Index("ix_maritime_roles_tenant_label", "tenant_id", "label"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    vessel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class MaritimeWatchRotation(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "maritime_watch_rotations"
    __table_args__ = (
        Index("ix_maritime_watch_rotations_tenant_label", "tenant_id", "label"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    vessel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    member_user_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class MaritimeAISPosition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maritime_ais_positions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source",
            "mmsi",
            "reported_at",
            "latitude",
            "longitude",
            name="uq_maritime_ais_positions_tenant_source_mmsi_reported_position",
        ),
        Index(
            "ix_maritime_ais_positions_tenant_vessel_reported",
            "tenant_id",
            "vessel_id",
            "reported_at",
        ),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="longitude"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    vessel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mmsi: Mapped[str] = mapped_column(String(16), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    speed_over_ground: Mapped[float | None] = mapped_column(Float, nullable=True)
    course_over_ground: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    navigational_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class MaritimeNMEAReading(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maritime_nmea_readings"
    __table_args__ = (
        Index(
            "ix_maritime_nmea_readings_tenant_vessel_created",
            "tenant_id",
            "vessel_id",
            "created_at",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    vessel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sentence_type: Mapped[str] = mapped_column(String(16), nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    values: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    raw_sentence: Mapped[str] = mapped_column(Text, nullable=False)


class MaritimeCarrierTerminal(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "maritime_carrier_terminals"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "terminal_id",
            name="uq_maritime_carrier_terminals_tenant_terminal",
        ),
        Index(
            "ix_maritime_carrier_terminals_tenant_vessel",
            "tenant_id",
            "vessel_id",
        ),
        CheckConstraint(
            "status IN ('unknown', 'online', 'degraded', 'offline', 'blocked')",
            name="status",
        ),
        CheckConstraint(
            (
                "link_state IN ("
                "'unknown', 'satellite_good', 'satellite_degraded', "
                "'port_wifi', 'dark', 'recovering'"
                ")"
            ),
            name="link_state",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    vessel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=False,
    )
    terminal_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="generic")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    link_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    downlink_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    uplink_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class MaritimeTelemetryIngestEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maritime_telemetry_ingest_events"
    __table_args__ = (
        Index(
            "ix_maritime_telemetry_ingest_events_tenant_created",
            "tenant_id",
            "created_at",
        ),
        CheckConstraint("status IN ('succeeded', 'partial', 'failed')", name="status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    vessel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class MaritimeEvidenceContext(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "maritime_evidence_contexts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "incident_id",
            name="uq_maritime_evidence_contexts_tenant_incident",
        ),
        Index(
            "ix_maritime_evidence_contexts_tenant_camera",
            "tenant_id",
            "camera_id",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=True,
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    incident_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    vessel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_vessels.id"),
        nullable=True,
    )
    voyage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_voyages.id"),
        nullable=True,
    )
    port_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maritime_port_calls.id"),
        nullable=True,
    )
    resolution_source: Mapped[str] = mapped_column(String(80), nullable=False)
    vessel_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ais_position: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    carrier_terminal: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    telemetry_freshness: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class MaritimeEvidenceExport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maritime_evidence_exports"
    __table_args__ = (
        Index(
            "ix_maritime_evidence_exports_tenant_incident_created",
            "tenant_id",
            "incident_id",
            "created_at",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", name="fk_maritime_evidence_exports_incident"),
        nullable=False,
    )
    export_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    artifact_hashes: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
