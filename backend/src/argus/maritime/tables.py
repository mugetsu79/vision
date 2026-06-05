from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
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
