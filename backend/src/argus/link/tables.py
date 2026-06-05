from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from argus.models.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


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
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    throughput_mbps: Mapped[float] = mapped_column(Float, nullable=False)
    packet_loss_percent: Mapped[float] = mapped_column(Float, nullable=False)
    reachable: Mapped[bool] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LinkPassportSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "link_passport_snapshots"
    __table_args__ = (
        Index("ix_link_passports_tenant_site_created", "tenant_id", "site_id", "created_at"),
        Index("ix_link_passports_incident", "incident_id"),
        Index("ix_link_passports_hash", "passport_hash", unique=True),
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
