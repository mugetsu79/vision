from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from argus.compat import StrEnum
from argus.models.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from argus.models.enums import (
    CountEventType,
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DeploymentServiceManager,
    DetectorCapability,
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
    IncidentReviewStatus,
    IncidentRuleSeverity,
    ModelAdmissionStatus,
    ModelFormat,
    ModelTask,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
    OperatorConfigProfileKind,
    OperatorConfigScope,
    OperatorConfigValidationStatus,
    PolicyDraftLedgerAction,
    PolicyDraftStatus,
    ProcessingMode,
    RoleEnum,
    RuleAction,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
    RuntimeVocabularySource,
    TrackerType,
    WorkerRuntimeState,
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
    capability: Mapped[DetectorCapability] = mapped_column(
        enum_column(DetectorCapability, "detector_capability_enum"),
        nullable=False,
        default=DetectorCapability.FIXED_VOCAB,
    )
    capability_config: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    input_shape: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ModelRuntimeArtifact(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "model_runtime_artifacts"

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    scope: Mapped[RuntimeArtifactScope] = mapped_column(
        enum_column(RuntimeArtifactScope, "runtime_artifact_scope_enum"),
        nullable=False,
    )
    kind: Mapped[RuntimeArtifactKind] = mapped_column(
        enum_column(RuntimeArtifactKind, "runtime_artifact_kind_enum"),
        nullable=False,
    )
    capability: Mapped[DetectorCapability] = mapped_column(
        enum_column(DetectorCapability, "runtime_artifact_detector_capability_enum"),
        nullable=False,
    )
    runtime_backend: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    target_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    precision: Mapped[RuntimeArtifactPrecision] = mapped_column(
        enum_column(RuntimeArtifactPrecision, "runtime_artifact_precision_enum"),
        nullable=False,
    )
    input_shape: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    classes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    vocabulary_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vocabulary_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_model_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    builder: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    runtime_versions: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    validation_status: Mapped[RuntimeArtifactValidationStatus] = mapped_column(
        enum_column(
            RuntimeArtifactValidationStatus,
            "runtime_artifact_validation_status_enum",
        ),
        nullable=False,
        default=RuntimeArtifactValidationStatus.UNVALIDATED,
    )
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    build_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    source_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_config: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    evidence_recording_policy: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
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
    runtime_vocabulary: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    runtime_vocabulary_source: Mapped[RuntimeVocabularySource] = mapped_column(
        enum_column(RuntimeVocabularySource, "runtime_vocabulary_source_enum"),
        nullable=False,
        default=RuntimeVocabularySource.DEFAULT,
    )
    runtime_vocabulary_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runtime_vocabulary_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attribute_rules: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    zones: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    vision_profile: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    detection_regions: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    homography: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    privacy: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    browser_delivery: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    source_capability: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    frame_skip: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    fps_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=25)


class SceneContractSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_contract_snapshots"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    contract: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class PrivacyManifestSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "privacy_manifest_snapshots"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    manifest: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class RuntimePassportSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runtime_passport_snapshots"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=True,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    passport_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    passport: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class DetectionRule(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "detection_rules"
    __table_args__ = (
        UniqueConstraint(
            "camera_id",
            "incident_type",
            name="uq_detection_rules_camera_incident_type",
        ),
        Index("ix_detection_rules_camera_enabled", "camera_id", "enabled"),
        Index("ix_detection_rules_rule_hash", "rule_hash"),
    )

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[IncidentRuleSeverity] = mapped_column(
        enum_column(IncidentRuleSeverity, "incident_rule_severity_enum"),
        nullable=False,
        default=IncidentRuleSeverity.WARNING,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    predicate: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    action: Mapped[RuleAction] = mapped_column(
        enum_column(RuleAction, "rule_action_enum"),
        nullable=False,
    )
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_hash: Mapped[str] = mapped_column(String(64), nullable=False)


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
    vocabulary_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vocabulary_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CameraVocabularySnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "camera_vocabulary_snapshots"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    vocabulary_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[RuntimeVocabularySource] = mapped_column(
        enum_column(RuntimeVocabularySource, "camera_vocabulary_snapshot_source_enum"),
        nullable=False,
    )
    terms: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


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
    vocabulary_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vocabulary_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


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
    scene_contract_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scene_contract_snapshots.id"),
        nullable=True,
    )
    scene_contract_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    privacy_manifest_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("privacy_manifest_snapshots.id"),
        nullable=True,
    )
    privacy_manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runtime_passport_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runtime_passport_snapshots.id"),
        nullable=True,
    )
    runtime_passport_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recording_policy: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    review_status: Mapped[IncidentReviewStatus] = mapped_column(
        enum_column(IncidentReviewStatus, "incident_review_status_enum"),
        nullable=False,
        default=IncidentReviewStatus.PENDING,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)


class OperationalMemoryPattern(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "operational_memory_patterns"
    __table_args__ = (
        UniqueConstraint("pattern_hash", name="uq_operational_memory_pattern_hash"),
        Index("ix_operational_memory_tenant_created", "tenant_id", "created_at"),
        Index("ix_operational_memory_camera_created", "camera_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=True,
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    pattern_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[IncidentRuleSeverity] = mapped_column(
        enum_column(IncidentRuleSeverity, "incident_rule_severity_enum"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_incident_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_contract_hashes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    dimensions: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    pattern_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class CrossCameraThread(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cross_camera_threads"
    __table_args__ = (
        UniqueConstraint("thread_hash", name="uq_cross_camera_thread_hash"),
        Index("ix_cross_camera_threads_tenant_created", "tenant_id", "created_at"),
        Index("ix_cross_camera_threads_site_created", "site_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=True,
    )
    camera_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_incident_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    privacy_manifest_hashes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    signals: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    privacy_labels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    thread_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class WorkerAssignment(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "worker_assignments"
    __table_args__ = (
        Index("ix_worker_assignments_tenant_camera", "tenant_id", "camera_id"),
        Index("ix_worker_assignments_edge_active", "edge_node_id", "active"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    desired_state: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    supersedes_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("worker_assignments.id"),
        nullable=True,
    )
    assigned_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)


class WorkerRuntimeReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "worker_runtime_reports"
    __table_args__ = (
        Index("ix_worker_reports_tenant_camera", "tenant_id", "camera_id", "heartbeat_at"),
        Index("ix_worker_reports_assignment", "assignment_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("worker_assignments.id"),
        nullable=True,
    )
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    runtime_state: Mapped[WorkerRuntimeState] = mapped_column(
        enum_column(WorkerRuntimeState, "worker_runtime_state_enum"),
        nullable=False,
    )
    restart_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_runtime_artifacts.id"),
        nullable=True,
    )
    scene_contract_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class OperationsLifecycleRequest(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "operations_lifecycle_requests"
    __table_args__ = (
        Index("ix_lifecycle_requests_tenant_camera", "tenant_id", "camera_id", "requested_at"),
        Index("ix_lifecycle_requests_assignment", "assignment_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("worker_assignments.id"),
        nullable=True,
    )
    action: Mapped[OperationsLifecycleAction] = mapped_column(
        enum_column(OperationsLifecycleAction, "operations_lifecycle_action_enum"),
        nullable=False,
    )
    status: Mapped[OperationsLifecycleStatus] = mapped_column(
        enum_column(OperationsLifecycleStatus, "operations_lifecycle_status_enum"),
        nullable=False,
        default=OperationsLifecycleStatus.REQUESTED,
    )
    requested_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    claimed_by_supervisor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admission_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("worker_model_admission_reports.id"),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )


class EdgeNodeHardwareReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "edge_node_hardware_reports"
    __table_args__ = (
        UniqueConstraint(
            "supervisor_id",
            "report_hash",
            name="uq_hardware_reports_supervisor_hash",
        ),
        Index("ix_hardware_reports_edge_reported", "edge_node_id", "reported_at"),
        Index("ix_hardware_reports_tenant_reported", "tenant_id", "reported_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    supervisor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    host_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    os_name: Mapped[str] = mapped_column(String(64), nullable=False)
    machine_arch: Mapped[str] = mapped_column(String(64), nullable=False)
    cpu_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_total_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accelerators: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    provider_capabilities: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    observed_performance: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    thermal_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class WorkerModelAdmissionReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "worker_model_admission_reports"
    __table_args__ = (
        Index("ix_model_admissions_camera_eval", "camera_id", "evaluated_at"),
        Index("ix_model_admissions_edge_eval", "edge_node_id", "evaluated_at"),
        Index("ix_model_admissions_status_eval", "status", "evaluated_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("worker_assignments.id"),
        nullable=True,
    )
    hardware_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_node_hardware_reports.id"),
        nullable=True,
    )
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id"),
        nullable=True,
    )
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_capability: Mapped[DetectorCapability | None] = mapped_column(
        enum_column(DetectorCapability, "admission_detector_capability_enum"),
        nullable=True,
    )
    runtime_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_runtime_artifacts.id"),
        nullable=True,
    )
    runtime_selection_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_config_profiles.id"),
        nullable=True,
    )
    stream_profile: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[ModelAdmissionStatus] = mapped_column(
        enum_column(ModelAdmissionStatus, "model_admission_status_enum"),
        nullable=False,
    )
    selected_backend: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recommended_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id"),
        nullable=True,
    )
    recommended_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recommended_runtime_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_config_profiles.id"),
        nullable=True,
    )
    recommended_backend: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeploymentNode(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "deployment_nodes"
    __table_args__ = (
        CheckConstraint(
            "(node_kind = 'central' AND edge_node_id IS NULL) "
            "OR (node_kind = 'edge' AND edge_node_id IS NOT NULL)",
            name="ck_deploy_nodes_kind_edge",
        ),
        UniqueConstraint("tenant_id", "supervisor_id", name="uq_deploy_nodes_supervisor"),
        Index("ix_deploy_nodes_tenant_kind", "tenant_id", "node_kind"),
        Index("ix_deploy_nodes_edge", "edge_node_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    supervisor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    node_kind: Mapped[DeploymentNodeKind] = mapped_column(
        enum_column(DeploymentNodeKind, "deployment_node_kind_enum"),
        nullable=False,
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    install_status: Mapped[DeploymentInstallStatus] = mapped_column(
        enum_column(DeploymentInstallStatus, "deployment_install_status_enum"),
        nullable=False,
        default=DeploymentInstallStatus.NOT_INSTALLED,
    )
    credential_status: Mapped[DeploymentCredentialStatus] = mapped_column(
        enum_column(DeploymentCredentialStatus, "deployment_credential_status_enum"),
        nullable=False,
        default=DeploymentCredentialStatus.MISSING,
    )
    service_manager: Mapped[DeploymentServiceManager | None] = mapped_column(
        enum_column(DeploymentServiceManager, "deployment_service_manager_enum"),
        nullable=True,
    )
    service_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    host_profile: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_service_reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    diagnostics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SupervisorServiceStatusReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supervisor_service_status_reports"
    __table_args__ = (
        CheckConstraint(
            "(node_kind = 'central' AND edge_node_id IS NULL) "
            "OR (node_kind = 'edge' AND edge_node_id IS NOT NULL)",
            name="ck_svc_reports_kind_edge",
        ),
        Index("ix_svc_reports_node_heartbeat", "deployment_node_id", "heartbeat_at"),
        Index("ix_svc_reports_supervisor", "tenant_id", "supervisor_id", "heartbeat_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_nodes.id"),
        nullable=False,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    supervisor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    node_kind: Mapped[DeploymentNodeKind] = mapped_column(
        enum_column(DeploymentNodeKind, "deployment_report_node_kind_enum"),
        nullable=False,
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    service_manager: Mapped[DeploymentServiceManager] = mapped_column(
        enum_column(DeploymentServiceManager, "deployment_report_service_manager_enum"),
        nullable=False,
    )
    service_status: Mapped[str] = mapped_column(String(64), nullable=False)
    install_status: Mapped[DeploymentInstallStatus] = mapped_column(
        enum_column(DeploymentInstallStatus, "deployment_report_install_status_enum"),
        nullable=False,
    )
    credential_status: Mapped[DeploymentCredentialStatus] = mapped_column(
        enum_column(DeploymentCredentialStatus, "deployment_report_credential_status_enum"),
        nullable=False,
    )
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os_name: Mapped[str] = mapped_column(String(64), nullable=False)
    host_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    diagnostics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class NodePairingSession(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "node_pairing_sessions"
    __table_args__ = (
        Index("ix_pairing_sessions_tenant_status", "tenant_id", "status"),
        Index("ix_pairing_sessions_node", "deployment_node_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    deployment_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_nodes.id"),
        nullable=True,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    node_kind: Mapped[DeploymentNodeKind] = mapped_column(
        enum_column(DeploymentNodeKind, "pairing_session_node_kind_enum"),
        nullable=False,
    )
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pairing_code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by_supervisor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SupervisorNodeCredential(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "supervisor_node_credentials"
    __table_args__ = (
        Index("ix_node_credentials_node_status", "deployment_node_id", "status"),
        Index("ix_node_credentials_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_nodes.id"),
        nullable=False,
    )
    supervisor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    credential_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_credential: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DeploymentCredentialStatus] = mapped_column(
        enum_column(DeploymentCredentialStatus, "supervisor_credential_status_enum"),
        nullable=False,
        default=DeploymentCredentialStatus.ACTIVE,
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeploymentCredentialEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deployment_credential_events"
    __table_args__ = (
        Index("ix_credential_events_node_time", "deployment_node_id", "occurred_at"),
        Index("ix_credential_events_tenant_time", "tenant_id", "occurred_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_nodes.id"),
        nullable=False,
    )
    credential_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supervisor_node_credentials.id"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class PolicyDraft(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "policy_drafts"
    __table_args__ = (
        Index("ix_policy_drafts_tenant_created", "tenant_id", "created_at"),
        Index("ix_policy_drafts_camera_created", "camera_id", "created_at"),
        Index("ix_policy_drafts_status_created", "status", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=True,
    )
    status: Mapped[PolicyDraftStatus] = mapped_column(
        enum_column(PolicyDraftStatus, "policy_draft_status_enum"),
        nullable=False,
        default=PolicyDraftStatus.DRAFT,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    structured_diff: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    draft_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejected_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    applied_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PolicyDraftLedgerEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policy_draft_ledger_entries"
    __table_args__ = (
        UniqueConstraint(
            "policy_draft_id",
            "sequence",
            name="uq_policy_draft_ledger_sequence",
        ),
        Index("ix_policy_draft_ledger_draft_sequence", "policy_draft_id", "sequence"),
        Index("ix_policy_draft_ledger_tenant_created", "tenant_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    policy_draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_drafts.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[PolicyDraftLedgerAction] = mapped_column(
        enum_column(PolicyDraftLedgerAction, "policy_draft_ledger_action_enum"),
        nullable=False,
    )
    actor_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    previous_entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class EvidenceArtifact(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "evidence_artifacts"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    kind: Mapped[EvidenceArtifactKind] = mapped_column(
        enum_column(EvidenceArtifactKind, "evidence_artifact_kind_enum"),
        nullable=False,
    )
    status: Mapped[EvidenceArtifactStatus] = mapped_column(
        enum_column(EvidenceArtifactStatus, "evidence_artifact_status_enum"),
        nullable=False,
    )
    storage_provider: Mapped[EvidenceStorageProvider] = mapped_column(
        enum_column(EvidenceStorageProvider, "evidence_storage_provider_enum"),
        nullable=False,
    )
    storage_scope: Mapped[EvidenceStorageScope] = mapped_column(
        enum_column(EvidenceStorageScope, "evidence_storage_scope_enum"),
        nullable=False,
    )
    bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    clip_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clip_ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scene_contract_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    privacy_manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class EvidenceLedgerEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence_ledger_entries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[EvidenceLedgerAction] = mapped_column(
        enum_column(EvidenceLedgerAction, "evidence_ledger_action_enum"),
        nullable=False,
    )
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    previous_entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class LocalFirstSyncAttempt(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "local_first_sync_attempts"
    __table_args__ = (
        UniqueConstraint("artifact_id", name="uq_local_first_sync_artifact"),
        Index("ix_local_first_sync_tenant_status", "tenant_id", "latest_status"),
        Index("ix_local_first_sync_profile", "remote_profile_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_artifacts.id"),
        nullable=False,
    )
    remote_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_config_profiles.id"),
        nullable=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    latest_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OperatorConfigProfile(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "operator_config_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "kind", "slug", name="uq_op_cfg_profile_slug"),
        Index("ix_op_cfg_profile_tenant_kind", "tenant_id", "kind"),
        Index("ix_op_cfg_profile_tenant_default", "tenant_id", "kind", "is_default"),
        Index("ix_op_cfg_profile_site_kind", "site_id", "kind"),
        Index("ix_op_cfg_profile_edge_kind", "edge_node_id", "kind"),
        Index("ix_op_cfg_profile_camera_kind", "camera_id", "kind"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=True,
    )
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_nodes.id"),
        nullable=True,
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    kind: Mapped[OperatorConfigProfileKind] = mapped_column(
        enum_column(OperatorConfigProfileKind, "operator_config_profile_kind_enum"),
        nullable=False,
    )
    scope: Mapped[OperatorConfigScope] = mapped_column(
        enum_column(OperatorConfigScope, "operator_config_scope_enum"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)
    config: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    validation_status: Mapped[OperatorConfigValidationStatus] = mapped_column(
        enum_column(
            OperatorConfigValidationStatus,
            "operator_config_validation_status_enum",
        ),
        nullable=False,
        default=OperatorConfigValidationStatus.UNVALIDATED,
    )
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class OperatorConfigSecret(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "operator_config_secrets"
    __table_args__ = (
        UniqueConstraint("profile_id", "key", name="uq_op_cfg_secret_key"),
        Index("ix_op_cfg_secret_tenant_profile", "tenant_id", "profile_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_config_profiles.id"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class OperatorConfigBinding(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "operator_config_bindings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "kind",
            "scope",
            "scope_key",
            name="uq_op_cfg_binding_scope",
        ),
        Index("ix_op_cfg_binding_profile", "profile_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    kind: Mapped[OperatorConfigProfileKind] = mapped_column(
        enum_column(OperatorConfigProfileKind, "operator_config_profile_kind_enum"),
        nullable=False,
    )
    scope: Mapped[OperatorConfigScope] = mapped_column(
        enum_column(OperatorConfigScope, "operator_config_scope_enum"),
        nullable=False,
    )
    scope_key: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_config_profiles.id"),
        nullable=False,
    )


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
