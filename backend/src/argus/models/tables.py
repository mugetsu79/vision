from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from argus.models.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from argus.models.enums import (
    CountEventType,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    RoleEnum,
    RuleAction,
    TrackerType,
)


def enum_column(enum_cls: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda enum_values: [member.value for member in enum_values],
    )


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    query_requests_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    incident_storage_quota_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=10 * 1024 * 1024 * 1024,
    )
    anpr_store_plaintext: Mapped[bool] = mapped_column(nullable=False, default=False)
    anpr_plaintext_justification: Mapped[str | None] = mapped_column(Text, nullable=True)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    oidc_sub: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[RoleEnum] = mapped_column(enum_column(RoleEnum, "role_enum"), nullable=False)


class APIKey(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "api_keys"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Site(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sites"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tz: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    geo_point: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)


class EdgeNode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "edge_nodes"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=False,
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Model(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "models"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    task: Mapped[ModelTask] = mapped_column(
        enum_column(ModelTask, "model_task_enum"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[ModelFormat] = mapped_column(
        enum_column(ModelFormat, "model_format_enum"),
        nullable=False,
    )
    classes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    input_shape: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Camera(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "cameras"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rtsp_url_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    processing_mode: Mapped[ProcessingMode] = mapped_column(
        enum_column(ProcessingMode, "processing_mode_enum"),
        nullable=False,
    )
    primary_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id"),
        nullable=False,
    )
    secondary_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id"),
        nullable=True,
    )
    tracker_type: Mapped[TrackerType] = mapped_column(
        enum_column(TrackerType, "tracker_type_enum"),
        nullable=False,
    )
    active_classes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    attribute_rules: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    zones: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    homography: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    privacy: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    browser_delivery: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    frame_skip: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    fps_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=25)


class DetectionRule(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "detection_rules"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    predicate: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    action: Mapped[RuleAction] = mapped_column(
        enum_column(RuleAction, "rule_action_enum"),
        nullable=False,
    )
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TrackingEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tracking_events"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    bbox: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class CountEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "count_events"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[CountEventType] = mapped_column(
        enum_column(CountEventType, "count_event_type_enum"),
        nullable=False,
    )
    boundary_id: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    from_zone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_zone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    attributes: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class RuleEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "rule_events"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("detection_rules.id"),
        nullable=False,
    )
    event_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    snapshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class Incident(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incidents"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    snapshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    clip_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_log"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    meta: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
