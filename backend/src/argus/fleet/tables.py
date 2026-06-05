from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from argus.models.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class FleetSiteGroup(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "fleet_site_groups"
    __table_args__ = (
        Index("ix_fleet_site_groups_tenant_kind", "tenant_id", "kind"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class FleetHierarchyNode(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "fleet_hierarchy_nodes"
    __table_args__ = (
        Index(
            "ix_fleet_hierarchy_nodes_tenant_node",
            "tenant_id",
            "node_id",
            unique=True,
        ),
        Index("ix_fleet_hierarchy_nodes_tenant_parent", "tenant_id", "parent_id"),
        Index("ix_fleet_hierarchy_nodes_tenant_site", "tenant_id", "site_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class FleetSiteState(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "fleet_site_states"
    __table_args__ = (
        Index("ix_fleet_site_states_tenant_site", "tenant_id", "site_id", unique=True),
        CheckConstraint(
            "heartbeat_status IN ('unknown', 'healthy', 'stale', 'offline')",
            name="heartbeat_status",
        ),
        CheckConstraint(
            "link_state IN ('unknown', 'healthy', 'degraded', 'dark', 'recovering', 'port_wifi')",
            name="link_state",
        ),
        CheckConstraint(
            "runtime_status IN ('unknown', 'running', 'degraded', 'stopped')",
            name="runtime_status",
        ),
        CheckConstraint(
            "privacy_status IN ('unknown', 'ok', 'mismatch')",
            name="privacy_status",
        ),
        CheckConstraint(
            "model_artifact_status IN ('unknown', 'ok', 'mismatch')",
            name="model_artifact_status",
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
    heartbeat_status: Mapped[str] = mapped_column(String(32), nullable=False)
    link_state: Mapped[str] = mapped_column(String(32), nullable=False)
    runtime_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_backlog_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    privacy_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    model_artifact_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unknown",
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class FleetRotationGroup(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "fleet_rotation_groups"
    __table_args__ = (
        Index("ix_fleet_rotation_groups_tenant_label", "tenant_id", "label"),
        UniqueConstraint("tenant_id", "id", name="uq_fleet_rotation_groups_tenant_id_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    member_user_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    pack_labels: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class FleetSiteAssignment(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "fleet_site_assignments"
    __table_args__ = (
        Index(
            "ix_fleet_site_assignments_tenant_site",
            "tenant_id",
            "site_id",
        ),
        Index(
            "ix_fleet_site_assignments_tenant_assignee",
            "tenant_id",
            "assignee_type",
            "assignee_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "rotation_group_id"],
            ["fleet_rotation_groups.tenant_id", "fleet_rotation_groups.id"],
            name="fk_fleet_site_assignments_rotation_group_tenant",
        ),
        CheckConstraint(
            "assignee_type IN ('support_queue', 'user', 'team', 'service_account')",
            name="assignee_type",
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
    assignee_type: Mapped[str] = mapped_column(String(32), nullable=False)
    assignee_id: Mapped[str] = mapped_column(String(160), nullable=False)
    rotation_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
