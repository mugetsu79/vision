from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from argus.models.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class SupportBundle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "support_bundles"
    __table_args__ = (
        Index("ix_support_bundles_tenant_site_created", "tenant_id", "site_id", "created_at"),
        Index("ix_support_bundles_pack", "pack_id"),
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
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    include_logs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SupportSession(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "support_sessions"
    __table_args__ = (
        Index("ix_support_sessions_tenant_site_status", "tenant_id", "site_id", "status"),
        Index("ix_support_sessions_operator", "operator_id"),
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
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    operator_id: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billable_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_meter_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="support_session_hour",
    )
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class SupportTunnel(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "support_tunnels"
    __table_args__ = (
        Index("ix_support_tunnels_tenant_site_status", "tenant_id", "site_id", "status"),
        Index("ix_support_tunnels_node_status", "node_id", "status"),
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
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transport: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="requested")
    credential_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    credential_ref_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    relay_host: Mapped[str] = mapped_column(String(255), nullable=False)
    allowed_ports: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    dispatch_method: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class BreakGlassAccessRecord(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "break_glass_access_records"
    __table_args__ = (
        Index("ix_break_glass_records_tenant_started", "tenant_id", "started_at"),
        Index("ix_break_glass_records_actor", "actor_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    actor_id: Mapped[str] = mapped_column(String(160), nullable=False)
    approver_id: Mapped[str] = mapped_column(String(160), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closure_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audit_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class OnboardingCheckRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "onboarding_check_runs"
    __table_args__ = (
        Index("ix_onboarding_check_runs_tenant_site_created", "tenant_id", "site_id", "created_at"),
        Index("ix_onboarding_check_runs_pack", "pack_id"),
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
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checks: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    attributes: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
