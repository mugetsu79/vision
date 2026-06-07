from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from argus.models.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class LinkConnection(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "link_connections"
    __table_args__ = (
        Index("ix_link_connections_tenant_site_rank", "tenant_id", "site_id", "priority_rank"),
        CheckConstraint(
            "transport_kind IN ('satellite', 'lte', '5g', 'wifi', 'fiber', 'ethernet', 'other')",
            name="transport_kind",
        ),
        CheckConstraint(
            "status IN ('unknown', 'online', 'degraded', 'offline', 'blocked', 'recovering')",
            name="status",
        ),
        CheckConstraint(
            "availability_scope IN ('always', 'remote', 'nearby', 'local', 'maintenance')",
            name="availability_scope",
        ),
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
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    transport_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    availability_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="always")
    metered: Mapped[bool] = mapped_column(nullable=False, default=False)
    monthly_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bulk_daily_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expected_downlink_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_uplink_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    packet_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connection_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class LinkBudget(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "link_budgets"
    __table_args__ = (
        Index("ix_link_budgets_tenant_site", "tenant_id", "site_id", unique=True),
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
    monthly_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bulk_daily_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    policy: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class LinkQueueItem(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "link_queue_items"
    __table_args__ = (
        Index("ix_link_queue_items_tenant_site_lane", "tenant_id", "site_id", "priority_lane"),
        Index("ix_link_queue_items_incident", "incident_id"),
        CheckConstraint(
            "priority_lane IN ('safety', 'evidence', 'telemetry', 'bulk')",
            name="priority_lane",
        ),
        CheckConstraint(
            "status IN ('queued', 'paused', 'interrupted', 'succeeded', 'failed')",
            name="status",
        ),
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
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=True,
    )
    evidence_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_artifacts.id"),
        nullable=True,
    )
    priority_lane: Mapped[str] = mapped_column(String(32), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_transfer_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class LinkTransferAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "link_transfer_attempts"
    __table_args__ = (
        Index("ix_link_transfer_attempts_queue_item", "queue_item_id", "created_at"),
        CheckConstraint(
            "status IN ('interrupted', 'succeeded', 'failed')",
            name="status",
        ),
    )

    queue_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("link_queue_items.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    bytes_transferred: Mapped[int] = mapped_column(BigInteger, nullable=False)
    resume_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    interruption_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class LinkHealthProbe(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "link_health_probes"
    __table_args__ = (
        Index("ix_link_health_probes_tenant_site_recorded", "tenant_id", "site_id", "recorded_at"),
        Index(
            "ix_link_health_probes_tenant_target_site_recorded",
            "tenant_id",
            "target_site_id",
            "recorded_at",
        ),
        Index("ix_link_health_probes_connection", "connection_id"),
        Index("ix_link_health_probes_target", "target_id"),
        Index("ix_link_health_probes_deleted", "deleted_at"),
        CheckConstraint(
            "probe_type IS NULL OR probe_type IN ('icmp', 'tcp', 'http', 'https', 'udp', 'manual')",
            name="probe_type",
        ),
        CheckConstraint(
            "source_type IN "
            "('manual', 'backend_synthetic', 'edge_agent', 'provider_api', 'import')",
            name="source_type",
        ),
        CheckConstraint(
            "sample_kind IN ('manual', 'automated', 'imported')",
            name="sample_kind",
        ),
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
    target_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("link_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    throughput_mbps: Mapped[float] = mapped_column(Float, nullable=False)
    packet_loss_percent: Mapped[float] = mapped_column(Float, nullable=False)
    reachable: Mapped[bool] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    target_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    probe_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sample_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    measurement_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)


class LinkReflectorProfile(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "link_reflector_profiles"
    __table_args__ = (
        Index(
            "ix_link_reflector_profiles_tenant_site_kind",
            "tenant_id",
            "site_id",
            "profile_kind",
            unique=True,
        ),
        CheckConstraint("profile_kind IN ('master')", name="profile_kind"),
        CheckConstraint("mode IN ('vezor_udp_sequence')", name="mode"),
        CheckConstraint(
            "last_status IN ('disabled', 'starting', 'listening', 'unhealthy')",
            name="last_status",
        ),
        CheckConstraint("udp_port > 0 AND udp_port <= 65535", name="udp_port_range"),
        CheckConstraint(
            "rate_limit_pps_per_source >= 0",
            name="rate_limit_pps_per_source_nonnegative",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="vezor_udp_sequence")
    public_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bind_address: Mapped[str] = mapped_column(String(64), nullable=False, default="0.0.0.0")
    udp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=8622)
    key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_edge_site_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    allowed_source_cidrs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    rate_limit_pps_per_source: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    last_status: Mapped[str] = mapped_column(String(32), nullable=False, default="disabled")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class LinkPassportSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "link_passport_snapshots"
    __table_args__ = (
        Index("ix_link_passports_tenant_site_created", "tenant_id", "site_id", "created_at"),
        Index("ix_link_passports_incident", "incident_id"),
        Index("ix_link_passports_hash", "passport_hash", unique=True),
        CheckConstraint(
            "link_state IN ('unknown', 'healthy', 'degraded', 'dark', 'recovering', 'port_wifi')",
            name="link_state",
        ),
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
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=True,
    )
    evidence_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_artifacts.id"),
        nullable=True,
    )
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    link_state: Mapped[str] = mapped_column(String(32), nullable=False)
    passport_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    passport: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
