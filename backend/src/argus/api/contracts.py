from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from argus.compat import StrEnum
from argus.core.security import AuthenticatedUser
from argus.inference.publisher import TelemetryFrame
from argus.models.enums import (
    CameraSourceKind,
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
    HistoryCoverageStatus,
    HistoryMetric,
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
    PolicyDraftStatus,
    ProcessingMode,
    QueryResolutionMode,
    RuleAction,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactSoakStatus,
    RuntimeArtifactValidationStatus,
    RuntimeVocabularySource,
    SupervisorMode,
    TrackerType,
    WorkerRuntimeState,
)


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    tz: str = Field(default="UTC", min_length=1, max_length=64)
    geo_point: dict[str, float] | None = None


class SiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    tz: str | None = Field(default=None, min_length=1, max_length=64)
    geo_point: dict[str, float] | None = None


class SiteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None = None
    tz: str
    geo_point: dict[str, float] | None = None
    created_at: datetime


class ModelCapabilityConfig(BaseModel):
    supports_runtime_vocabulary_updates: bool = False
    max_runtime_terms: int | None = None
    prompt_format: Literal["labels", "phrases"] | None = None
    execution_profiles: list[str] = Field(default_factory=list)
    model_family: Literal["yolo11", "yolo12", "yolo26", "yolo_world", "yoloe"] | None = None
    runtime_backend: (
        Literal["onnxruntime", "ultralytics_yolo_world", "ultralytics_yoloe", "tensorrt_engine"]
        | None
    ) = None
    readiness: Literal["ready", "experimental", "planned"] | None = None
    recommended_profiles: list[str] = Field(default_factory=list)
    requires_gpu: bool = False
    supports_masks: bool = False
    source_url: str | None = None


class RuntimeVocabularyState(BaseModel):
    terms: list[str] = Field(default_factory=list)
    source: RuntimeVocabularySource = RuntimeVocabularySource.DEFAULT
    version: int = 0
    updated_at: datetime | None = None


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    task: ModelTask
    path: str = Field(min_length=1)
    format: ModelFormat
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB
    capability_config: ModelCapabilityConfig = Field(default_factory=ModelCapabilityConfig)
    classes: list[str] | None = None
    input_shape: dict[str, int]
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0)
    license: str | None = Field(default=None, max_length=255)


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    version: str | None = Field(default=None, min_length=1, max_length=64)
    task: ModelTask | None = None
    path: str | None = Field(default=None, min_length=1)
    format: ModelFormat | None = None
    capability: DetectorCapability | None = None
    capability_config: ModelCapabilityConfig | None = None
    classes: list[str] | None = None
    input_shape: dict[str, int] | None = None
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    size_bytes: int | None = Field(default=None, gt=0)
    license: str | None = Field(default=None, max_length=255)


class ModelResponse(BaseModel):
    id: UUID
    name: str
    version: str
    task: ModelTask
    path: str
    format: ModelFormat
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB
    capability_config: ModelCapabilityConfig = Field(default_factory=ModelCapabilityConfig)
    classes: list[str]
    input_shape: dict[str, int]
    sha256: str
    size_bytes: int
    license: str | None = None


RuntimeBackend = Literal[
    "onnxruntime",
    "ultralytics_yolo_world",
    "ultralytics_yoloe",
    "tensorrt_engine",
]
StreamDeliveryMode = Literal["native", "webrtc", "hls", "mjpeg", "transcode"]
RuntimeArtifactPreference = Literal["tensorrt_first", "onnx_first", "dynamic_first"]


EvidenceStorageConfigProvider = EvidenceStorageProvider | Literal["local_first"]


class EvidenceStorageProfileConfig(BaseModel):
    provider: EvidenceStorageConfigProvider = EvidenceStorageProvider.MINIO
    storage_scope: EvidenceStorageScope = EvidenceStorageScope.CENTRAL
    endpoint: str | None = Field(default=None, min_length=1)
    region: str | None = Field(default=None, min_length=1)
    bucket: str | None = Field(default=None, min_length=1)
    secure: bool = False
    path_prefix: str | None = Field(default=None, min_length=1)
    local_root: str | None = Field(default=None, min_length=1)
    remote_profile_id: UUID | None = None


class StreamDeliveryProfileConfig(BaseModel):
    delivery_mode: StreamDeliveryMode = "native"
    public_base_url: str | None = Field(default=None, min_length=1)
    edge_override_url: str | None = Field(default=None, min_length=1)


class RuntimeSelectionProfileConfig(BaseModel):
    preferred_backend: RuntimeBackend | None = None
    artifact_preference: RuntimeArtifactPreference = "tensorrt_first"
    fallback_allowed: bool = True


class PrivacyPolicyProfileConfig(BaseModel):
    retention_days: int = Field(default=30, ge=0)
    storage_quota_bytes: int = Field(default=10 * 1024 * 1024 * 1024, ge=0)
    plaintext_plate_storage: Literal["blocked", "allowed"] = "blocked"
    residency: Literal["edge", "central", "cloud", "local_first"] = "central"


class LLMProviderProfileConfig(BaseModel):
    provider: str = Field(default="openai", min_length=1)
    model: str = Field(default="gpt-4.1-mini", min_length=1)
    base_url: str | None = Field(default=None, min_length=1)
    api_key_required: bool = True


class OperationsModeProfileConfig(BaseModel):
    lifecycle_owner: Literal["manual", "edge_supervisor", "central_supervisor"] = "manual"
    supervisor_mode: Literal["disabled", "polling", "push"] = "disabled"
    restart_policy: Literal["never", "on_failure", "always"] = "on_failure"


_OPERATOR_CONFIG_MODELS: dict[OperatorConfigProfileKind, type[BaseModel]] = {
    OperatorConfigProfileKind.EVIDENCE_STORAGE: EvidenceStorageProfileConfig,
    OperatorConfigProfileKind.STREAM_DELIVERY: StreamDeliveryProfileConfig,
    OperatorConfigProfileKind.RUNTIME_SELECTION: RuntimeSelectionProfileConfig,
    OperatorConfigProfileKind.PRIVACY_POLICY: PrivacyPolicyProfileConfig,
    OperatorConfigProfileKind.LLM_PROVIDER: LLMProviderProfileConfig,
    OperatorConfigProfileKind.OPERATIONS_MODE: OperationsModeProfileConfig,
}


def _normalize_operator_config(
    kind: OperatorConfigProfileKind,
    config: dict[str, Any],
) -> dict[str, Any]:
    config_model = _OPERATOR_CONFIG_MODELS[kind]
    return config_model.model_validate(config).model_dump(mode="json", exclude_none=True)


class OperatorConfigProfileBase(BaseModel):
    kind: OperatorConfigProfileKind
    scope: OperatorConfigScope = OperatorConfigScope.TENANT
    site_id: UUID | None = None
    edge_node_id: UUID | None = None
    camera_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    is_default: bool = False
    config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_config(self) -> OperatorConfigProfileBase:
        self.config = _normalize_operator_config(self.kind, self.config)
        return self


class OperatorConfigProfileCreate(OperatorConfigProfileBase):
    secrets: dict[str, str] = Field(default_factory=dict)


class OperatorConfigProfileUpdate(BaseModel):
    site_id: UUID | None = None
    edge_node_id: UUID | None = None
    camera_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    is_default: bool | None = None
    config: dict[str, Any] | None = None
    secrets: dict[str, str] | None = None


OperatorSecretState = Literal["missing", "present"]
OperatorConfigResolutionStatus = Literal["resolved", "unresolved"]


class OperatorConfigProfileResponse(OperatorConfigProfileBase):
    id: UUID
    tenant_id: UUID
    secret_state: dict[str, OperatorSecretState] = Field(default_factory=dict)
    validation_status: OperatorConfigValidationStatus = (
        OperatorConfigValidationStatus.UNVALIDATED
    )
    validation_message: str | None = None
    validated_at: datetime | None = None
    config_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime
    updated_at: datetime


class OperatorConfigBindingRequest(BaseModel):
    kind: OperatorConfigProfileKind
    scope: OperatorConfigScope
    scope_key: str = Field(min_length=1, max_length=255)
    profile_id: UUID


class OperatorConfigBindingResponse(OperatorConfigBindingRequest):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class OperatorConfigTestResponse(BaseModel):
    profile_id: UUID
    status: OperatorConfigValidationStatus
    message: str | None = None
    tested_at: datetime


class ResolvedOperatorConfigEntryResponse(BaseModel):
    kind: OperatorConfigProfileKind
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_slug: str | None = None
    profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
    winner_scope: OperatorConfigScope | None = None
    winner_scope_key: str | None = None
    validation_status: OperatorConfigValidationStatus | None = None
    resolution_status: OperatorConfigResolutionStatus = "unresolved"
    applies_to_runtime: bool = False
    secret_state: dict[str, OperatorSecretState] = Field(default_factory=dict)
    operator_message: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class ResolvedOperatorConfigResponse(BaseModel):
    entries: dict[OperatorConfigProfileKind, ResolvedOperatorConfigEntryResponse] = Field(
        default_factory=dict
    )
    profiles: dict[OperatorConfigProfileKind, OperatorConfigProfileResponse] = Field(
        default_factory=dict
    )


class RuntimeArtifactBase(BaseModel):
    camera_id: UUID | None = None
    scope: RuntimeArtifactScope
    kind: RuntimeArtifactKind
    capability: DetectorCapability
    runtime_backend: RuntimeBackend
    path: str = Field(min_length=1)
    target_profile: str = Field(min_length=1)
    precision: RuntimeArtifactPrecision
    input_shape: dict[str, int]
    classes: list[str] = Field(default_factory=list)
    vocabulary_hash: str | None = Field(default=None, min_length=64, max_length=64)
    vocabulary_version: int | None = None
    source_model_sha256: str = Field(min_length=64, max_length=64)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0)
    builder: dict[str, Any] = Field(default_factory=dict)
    runtime_versions: dict[str, Any] = Field(default_factory=dict)
    validation_status: RuntimeArtifactValidationStatus = (
        RuntimeArtifactValidationStatus.UNVALIDATED
    )
    validation_error: str | None = None
    build_duration_seconds: float | None = None
    validation_duration_seconds: float | None = None
    validated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> RuntimeArtifactBase:
        if self.scope is RuntimeArtifactScope.SCENE and self.camera_id is None:
            raise ValueError("camera_id is required for scene-scoped artifacts.")
        if self.scope is RuntimeArtifactScope.MODEL and self.camera_id is not None:
            raise ValueError("camera_id must be null for model-scoped artifacts.")
        if self.capability is DetectorCapability.OPEN_VOCAB and not self.vocabulary_hash:
            raise ValueError("vocabulary_hash is required for open-vocab artifacts.")
        return self


class RuntimeArtifactCreate(RuntimeArtifactBase):
    pass


class RuntimeArtifactUpdate(BaseModel):
    validation_status: RuntimeArtifactValidationStatus | None = None
    validation_error: str | None = None
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    size_bytes: int | None = Field(default=None, gt=0)
    builder: dict[str, Any] | None = None
    runtime_versions: dict[str, Any] | None = None
    build_duration_seconds: float | None = None
    validation_duration_seconds: float | None = None
    validated_at: datetime | None = None


class RuntimeArtifactResponse(RuntimeArtifactBase):
    id: UUID
    model_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RuntimeArtifactSoakRunCreate(BaseModel):
    edge_node_id: UUID | None = None
    runtime_artifact_id: UUID
    operations_assignment_id: UUID | None = None
    runtime_selection_profile_id: UUID | None = None
    hardware_report_id: UUID | None = None
    model_admission_report_id: UUID | None = None
    status: RuntimeArtifactSoakStatus
    started_at: datetime
    ended_at: datetime | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    fallback_reason: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_time_window(self) -> RuntimeArtifactSoakRunCreate:
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at must be after started_at.")
        return self


class RuntimeArtifactSoakRunResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    edge_node_id: UUID | None = None
    camera_id: UUID | None = None
    runtime_artifact_id: UUID
    runtime_kind: RuntimeArtifactKind
    runtime_backend: RuntimeBackend
    model_id: UUID | None = None
    model_name: str | None = None
    model_capability: DetectorCapability | None = None
    target_profile: str
    status: RuntimeArtifactSoakStatus
    started_at: datetime
    ended_at: datetime | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    fallback_reason: str | None = None
    notes: str | None = None
    operations_assignment_id: UUID | None = None
    runtime_selection_profile_id: UUID | None = None
    runtime_selection_profile_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    hardware_report_id: UUID | None = None
    model_admission_report_id: UUID | None = None
    hardware_admission_status: ModelAdmissionStatus | None = None
    model_recommendation_rationale: str | None = None
    created_at: datetime


class ModelCatalogRegistrationState(StrEnum):
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    MISSING_ARTIFACT = "missing_artifact"
    PLANNED = "planned"


class ModelCatalogEntryResponse(BaseModel):
    id: str
    name: str
    version: str
    task: ModelTask
    path_hint: str
    format: ModelFormat
    capability: DetectorCapability
    capability_config: ModelCapabilityConfig
    classes: list[str] = Field(default_factory=list)
    input_shape: dict[str, int]
    sha256: str | None = None
    size_bytes: int | None = None
    license: str | None = None
    registration_state: ModelCatalogRegistrationState
    registered_model_id: UUID | None = None
    artifact_exists: bool = False
    note: str


class HomographyPayload(BaseModel):
    src: list[list[float]]
    dst: list[list[float]]
    ref_distance_m: float = Field(gt=0)

    @field_validator("src", "dst")
    @classmethod
    def validate_four_points(cls, value: list[list[float]]) -> list[list[float]]:
        if len(value) != 4:
            raise ValueError("Homography requires exactly four points.")
        for point in value:
            if len(point) != 2:
                raise ValueError("Each homography point must contain exactly two coordinates.")
        return value


class FrameSize(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


Coordinate = list[float]
NormalizedCoordinate = list[float]


class ZoneBase(BaseModel):
    id: str | None = None
    class_names: list[str] | None = None
    frame_size: FrameSize | None = None
    points_normalized: list[NormalizedCoordinate] | None = None

    model_config = ConfigDict(extra="allow")

    @field_validator("points_normalized")
    @classmethod
    def validate_points_normalized(
        cls,
        value: list[NormalizedCoordinate] | None,
    ) -> list[NormalizedCoordinate] | None:
        if value is None:
            return value
        for point in value:
            if len(point) != 2:
                raise ValueError("Each normalized zone point must contain exactly two coordinates.")
            if point[0] < 0 or point[0] > 1 or point[1] < 0 or point[1] > 1:
                raise ValueError("Normalized zone coordinates must be between 0 and 1.")
        return value


class LineZone(ZoneBase):
    type: Literal["line"]
    points: list[Coordinate]

    @field_validator("points")
    @classmethod
    def validate_points(cls, value: list[Coordinate]) -> list[Coordinate]:
        if len(value) != 2:
            raise ValueError("Line zones must contain exactly two points.")
        for point in value:
            if len(point) != 2:
                raise ValueError("Each line zone point must contain exactly two coordinates.")
        return value


class PolygonZone(ZoneBase):
    type: Literal["polygon"] | None = None
    polygon: list[Coordinate]

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: list[Coordinate]) -> list[Coordinate]:
        if len(value) < 3:
            raise ValueError("Polygon zones must contain at least three vertices.")
        for point in value:
            if len(point) != 2:
                raise ValueError("Each polygon zone point must contain exactly two coordinates.")
        return value


class LegacyZone(ZoneBase):
    type: str | None = None

    model_config = ConfigDict(extra="allow")


CameraZone = LineZone | PolygonZone
StoredCameraZone = LineZone | PolygonZone | LegacyZone


class MotionMetricsSettings(BaseModel):
    speed_enabled: bool = False


class SceneVisionProfile(BaseModel):
    compute_tier: Literal[
        "cpu_low",
        "edge_standard",
        "edge_advanced_jetson",
        "central_gpu",
    ] = "edge_standard"
    accuracy_mode: Literal[
        "fast",
        "balanced",
        "maximum_accuracy",
        "open_vocabulary",
    ] = "balanced"
    scene_difficulty: Literal[
        "open",
        "cluttered",
        "occluded",
        "crowded",
        "traffic",
        "custom",
    ] = "cluttered"
    object_domain: Literal["people", "vehicles", "mixed", "open_vocab"] = "mixed"
    motion_metrics: MotionMetricsSettings = Field(default_factory=MotionMetricsSettings)
    candidate_quality: dict[str, Any] = Field(default_factory=dict)
    tracker_profile: dict[str, Any] = Field(default_factory=dict)
    verifier_profile: dict[str, Any] = Field(default_factory=dict)


class DetectionRegion(BaseModel):
    id: str
    mode: Literal["include", "exclude"]
    polygon: list[Coordinate]
    class_names: list[str] = Field(default_factory=list)
    frame_size: FrameSize | None = None
    points_normalized: list[Coordinate] | None = None

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: list[Coordinate]) -> list[Coordinate]:
        if len(value) < 3:
            raise ValueError("Detection regions must contain at least three vertices.")
        for point in value:
            if len(point) != 2:
                raise ValueError(
                    "Each detection region point must contain exactly two coordinates."
                )
        return value

    @field_validator("points_normalized")
    @classmethod
    def validate_points_normalized(
        cls,
        value: list[Coordinate] | None,
    ) -> list[Coordinate] | None:
        if value is None:
            return value
        for point in value:
            if len(point) != 2:
                raise ValueError(
                    "Each normalized detection region point must contain exactly two coordinates."
                )
            if point[0] < 0 or point[0] > 1 or point[1] < 0 or point[1] > 1:
                raise ValueError(
                    "Normalized detection region coordinates must be between 0 and 1."
                )
        return value

    @model_validator(mode="after")
    def normalize_polygon_coordinates(self) -> DetectionRegion:
        if self.frame_size is None:
            return self
        normalized: list[Coordinate] = []
        for point in self.polygon:
            x = float(point[0])
            y = float(point[1])
            if x < 0 or x > self.frame_size.width or y < 0 or y > self.frame_size.height:
                raise ValueError(
                    "Detection region coordinates must fall within the declared frame_size."
                )
            normalized.append(
                [
                    round(x / self.frame_size.width, 6),
                    round(y / self.frame_size.height, 6),
                ]
            )
        self.points_normalized = normalized
        return self


class PrivacySettings(BaseModel):
    blur_faces: bool = True
    blur_plates: bool = True
    method: Literal["gaussian", "pixelate"] = "gaussian"
    strength: int = Field(default=7, ge=1, le=100)


BrowserDeliveryProfileId = Literal[
    "native",
    "annotated",
    "1080p25",
    "1080p20",
    "1080p15",
    "1080p10",
    "1080p5",
    "900p25",
    "900p20",
    "900p15",
    "900p10",
    "900p5",
    "720p25",
    "720p20",
    "720p15",
    "720p10",
    "720p5",
    "540p25",
    "540p20",
    "540p15",
    "540p10",
    "540p5",
    "360p25",
    "360p20",
    "360p15",
    "360p10",
    "360p5",
    "240p25",
    "240p20",
    "240p15",
    "240p10",
    "240p5",
]


def _default_browser_delivery_profiles() -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = [
        {"id": "native", "kind": "passthrough"},
        {"id": "annotated", "kind": "transcode"},
    ]
    for label, width, height in (
        ("1080p", 1920, 1080),
        ("900p", 1600, 900),
        ("720p", 1280, 720),
        ("540p", 960, 540),
        ("360p", 640, 360),
        ("240p", 426, 240),
    ):
        for fps in (25, 20, 15, 10, 5):
            profiles.append(
                {
                    "id": f"{label}{fps}",
                    "kind": "transcode",
                    "w": width,
                    "h": height,
                    "fps": fps,
                }
            )
    return profiles


class SourceCapability(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int | None = Field(default=None, ge=1)
    codec: str | None = None
    aspect_ratio: str | None = None


EvidenceStorageProfile = Literal["edge_local", "central", "cloud", "local_first"]


class CameraSourceSettings(BaseModel):
    kind: CameraSourceKind = CameraSourceKind.RTSP
    uri: str = Field(min_length=1)
    label: str | None = None

    @model_validator(mode="after")
    def validate_source_uri(self) -> CameraSourceSettings:
        if self.kind is CameraSourceKind.RTSP and not self.uri.startswith(
            ("rtsp://", "rtsps://")
        ):
            raise ValueError("RTSP sources must use rtsp:// or rtsps://.")
        if self.kind is CameraSourceKind.USB and not self.uri.startswith("usb://"):
            raise ValueError("USB sources must use usb:///dev/videoN.")
        if self.kind is CameraSourceKind.JETSON_CSI and not self.uri.startswith("csi://"):
            raise ValueError("Jetson CSI sources must use csi://N.")
        return self


class EvidenceRecordingPolicy(BaseModel):
    enabled: bool = True
    mode: Literal["event_clip"] = "event_clip"
    pre_seconds: int = Field(default=4, ge=0, le=30)
    post_seconds: int = Field(default=8, ge=1, le=60)
    fps: int = Field(default=10, ge=1, le=30)
    max_duration_seconds: int = Field(default=15, ge=1, le=90)
    storage_profile: EvidenceStorageProfile = "central"
    storage_profile_id: UUID | None = None
    snapshot_enabled: bool = False
    snapshot_offset_seconds: float = Field(default=0.0, ge=-30.0, le=60.0)
    snapshot_quality: int = Field(default=85, ge=1, le=100)

    @model_validator(mode="after")
    def validate_window(self) -> EvidenceRecordingPolicy:
        if self.pre_seconds + self.post_seconds > self.max_duration_seconds:
            raise ValueError("pre_seconds plus post_seconds must fit max_duration_seconds.")
        return self


class BrowserDeliveryProfile(BaseModel):
    id: BrowserDeliveryProfileId
    kind: Literal["passthrough", "transcode"]
    w: int | None = Field(default=None, gt=0)
    h: int | None = Field(default=None, gt=0)
    fps: int | None = Field(default=None, ge=1)
    label: str | None = None
    description: str | None = None
    reason: str | None = None

    model_config = ConfigDict(extra="allow")


class DerivedBrowserProfiles(BaseModel):
    allowed: list[BrowserDeliveryProfile]
    unsupported: list[BrowserDeliveryProfile] = Field(default_factory=list)


class NativeAvailability(BaseModel):
    available: bool = True
    reason: str | None = None


class BrowserDeliverySettings(BaseModel):
    default_profile: BrowserDeliveryProfileId = "720p10"
    allow_native_on_demand: bool = True
    delivery_profile_id: UUID | None = None
    delivery_profile_name: str | None = None
    delivery_profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
    delivery_mode: StreamDeliveryMode | None = None
    public_base_url: str | None = Field(default=None, min_length=1)
    edge_override_url: str | None = Field(default=None, min_length=1)
    profiles: list[dict[str, Any]] = Field(default_factory=_default_browser_delivery_profiles)
    unsupported_profiles: list[dict[str, Any]] = Field(default_factory=list)
    native_status: NativeAvailability = Field(default_factory=NativeAvailability)


class CameraSourceProbeRequest(BaseModel):
    camera_id: UUID | None = None
    rtsp_url: str | None = Field(default=None, min_length=1)
    camera_source: CameraSourceSettings | None = None
    processing_mode: ProcessingMode = ProcessingMode.CENTRAL
    edge_node_id: UUID | None = None
    browser_delivery: BrowserDeliverySettings | None = None
    privacy: PrivacySettings | None = None


class CameraSourceProbeResponse(BaseModel):
    source_capability: SourceCapability | None = None
    browser_delivery: BrowserDeliverySettings


class WorkerCameraSettings(BaseModel):
    rtsp_url: str | None = Field(default=None, min_length=1)
    source_uri: str | None = Field(default=None, min_length=1)
    camera_source: CameraSourceSettings | None = None
    frame_skip: int = Field(default=1, ge=1)
    fps_cap: int = Field(default=25, ge=1)

    @model_validator(mode="after")
    def resolve_source_uri(self) -> WorkerCameraSettings:
        if self.source_uri is None and self.rtsp_url is not None:
            self.source_uri = self.rtsp_url
        if self.camera_source is None and self.rtsp_url is not None:
            self.camera_source = CameraSourceSettings(
                kind=CameraSourceKind.RTSP,
                uri=self.rtsp_url,
            )
        if self.source_uri is None and self.camera_source is not None:
            self.source_uri = self.camera_source.uri
        if (
            self.rtsp_url is None
            and self.camera_source is not None
            and self.camera_source.kind is CameraSourceKind.RTSP
        ):
            self.rtsp_url = self.camera_source.uri
        if self.source_uri is None:
            raise ValueError("Worker camera settings require source_uri or rtsp_url.")
        return self


class WorkerPublishSettings(BaseModel):
    subject_prefix: str = "evt.tracking"
    http_fallback_url: str | None = None


class WorkerStreamSettings(BaseModel):
    profile_id: BrowserDeliveryProfileId = "native"
    kind: Literal["passthrough", "transcode"] = "passthrough"
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    fps: int = Field(default=25, ge=1)


class WorkerStreamDeliverySettings(BaseModel):
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
    delivery_mode: StreamDeliveryMode = "native"
    public_base_url: str | None = Field(default=None, min_length=1)
    edge_override_url: str | None = Field(default=None, min_length=1)


class WorkerRuntimeSelectionSettings(BaseModel):
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
    preferred_backend: RuntimeBackend | None = None
    artifact_preference: RuntimeArtifactPreference = "tensorrt_first"
    fallback_allowed: bool = True


class WorkerPrivacyPolicySettings(BaseModel):
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
    retention_days: int = Field(default=30, ge=0)
    storage_quota_bytes: int = Field(default=10 * 1024 * 1024 * 1024, ge=0)
    plaintext_plate_storage: Literal["blocked", "allowed"] = "blocked"
    residency: Literal["edge", "central", "cloud", "local_first"] = "central"


class WorkerEvidenceStorageSettings(BaseModel):
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_hash: str | None = None
    provider: EvidenceStorageConfigProvider
    storage_scope: EvidenceStorageScope
    config: dict[str, object] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)


class WorkerModelSettings(BaseModel):
    name: str
    path: str
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB
    capability_config: ModelCapabilityConfig = Field(default_factory=ModelCapabilityConfig)
    classes: list[str]
    input_shape: dict[str, int]
    runtime_vocabulary: RuntimeVocabularyState = Field(default_factory=RuntimeVocabularyState)
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45


class WorkerRuntimeArtifact(BaseModel):
    id: UUID
    scope: RuntimeArtifactScope
    kind: RuntimeArtifactKind
    capability: DetectorCapability
    runtime_backend: RuntimeBackend
    path: str
    target_profile: str
    precision: RuntimeArtifactPrecision
    input_shape: dict[str, int]
    classes: list[str] = Field(default_factory=list)
    vocabulary_hash: str | None = None
    vocabulary_version: int | None = None
    source_model_sha256: str
    sha256: str
    size_bytes: int


class WorkerTrackerSettings(BaseModel):
    tracker_type: TrackerType
    frame_rate: int = Field(default=25, ge=1)


class WorkerPrivacySettings(BaseModel):
    blur_faces: bool = True
    blur_plates: bool = True
    method: Literal["gaussian", "pixelate"] = "gaussian"
    strength: int = Field(default=7, ge=1, le=100)


class WorkerZoneBase(BaseModel):
    id: str | None = None
    class_names: list[str] | None = None

    model_config = ConfigDict(extra="allow")


class WorkerLineZone(WorkerZoneBase):
    type: Literal["line"]
    points: list[Coordinate]

    @field_validator("points")
    @classmethod
    def validate_points(cls, value: list[Coordinate]) -> list[Coordinate]:
        if len(value) != 2:
            raise ValueError("Line zones must contain exactly two points.")
        for point in value:
            if len(point) != 2:
                raise ValueError("Each line zone point must contain exactly two coordinates.")
        return value


class WorkerPolygonZone(WorkerZoneBase):
    type: Literal["polygon"] | None = None
    polygon: list[Coordinate]

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: list[Coordinate]) -> list[Coordinate]:
        if len(value) < 3:
            raise ValueError("Polygon zones must contain at least three vertices.")
        for point in value:
            if len(point) != 2:
                raise ValueError("Each polygon zone point must contain exactly two coordinates.")
        return value


WorkerZone = WorkerLineZone | WorkerPolygonZone | LegacyZone


class IncidentRulePredicate(BaseModel):
    class_names: list[str] = Field(default_factory=list)
    zone_ids: list[str] = Field(default_factory=list)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("class_names", "zone_ids")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            stripped = item.strip()
            if stripped and stripped not in normalized:
                normalized.append(stripped)
        return normalized


class IncidentRuleCreate(BaseModel):
    enabled: bool = True
    name: str = Field(min_length=1, max_length=255)
    incident_type: str | None = Field(default=None, min_length=1, max_length=255)
    severity: IncidentRuleSeverity = IncidentRuleSeverity.WARNING
    description: str | None = Field(default=None, max_length=2000)
    predicate: IncidentRulePredicate = Field(default_factory=IncidentRulePredicate)
    action: RuleAction = RuleAction.RECORD_CLIP
    cooldown_seconds: int = Field(default=0, ge=0, le=86400)
    webhook_url: str | None = Field(default=None, min_length=1, max_length=2048)

    @model_validator(mode="after")
    def validate_webhook_action(self) -> IncidentRuleCreate:
        if self.action is RuleAction.WEBHOOK and self.webhook_url is None:
            raise ValueError("webhook_url is required for webhook rules.")
        return self


class IncidentRuleUpdate(BaseModel):
    enabled: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    incident_type: str | None = Field(default=None, min_length=1, max_length=255)
    severity: IncidentRuleSeverity | None = None
    description: str | None = Field(default=None, max_length=2000)
    predicate: IncidentRulePredicate | None = None
    action: RuleAction | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0, le=86400)
    webhook_url: str | None = Field(default=None, min_length=1, max_length=2048)


class IncidentRuleResponse(BaseModel):
    id: UUID
    camera_id: UUID
    enabled: bool
    name: str
    incident_type: str
    severity: IncidentRuleSeverity
    description: str | None = None
    predicate: IncidentRulePredicate
    action: RuleAction
    cooldown_seconds: int
    webhook_url_present: bool = False
    rule_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime
    updated_at: datetime


class IncidentRuleValidationRequest(BaseModel):
    rule: IncidentRuleCreate
    sample_detection: dict[str, Any] = Field(default_factory=dict)


class IncidentRuleValidationResponse(BaseModel):
    valid: bool
    matches: bool
    errors: list[str] = Field(default_factory=list)
    normalized_incident_type: str | None = None
    rule_hash: str | None = Field(default=None, min_length=64, max_length=64)


class WorkerIncidentRulePredicate(BaseModel):
    class_names: list[str] = Field(default_factory=list)
    zone_ids: list[str] = Field(default_factory=list)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("class_names", "zone_ids")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            stripped = item.strip()
            if stripped and stripped not in normalized:
                normalized.append(stripped)
        return normalized


class WorkerIncidentRule(BaseModel):
    id: UUID
    camera_id: UUID
    enabled: bool = True
    name: str
    incident_type: str
    severity: IncidentRuleSeverity = IncidentRuleSeverity.WARNING
    predicate: WorkerIncidentRulePredicate = Field(default_factory=WorkerIncidentRulePredicate)
    action: RuleAction = RuleAction.RECORD_CLIP
    cooldown_seconds: int = Field(default=0, ge=0)
    webhook_url: str | None = None
    rule_hash: str = Field(min_length=64, max_length=64)


class TriggerRuleSummary(BaseModel):
    id: UUID
    name: str
    incident_type: str
    severity: IncidentRuleSeverity = IncidentRuleSeverity.WARNING
    action: RuleAction
    cooldown_seconds: int = Field(default=0, ge=0)
    predicate: WorkerIncidentRulePredicate = Field(default_factory=WorkerIncidentRulePredicate)
    rule_hash: str | None = Field(default=None, min_length=64, max_length=64)


class CameraCommandPayload(BaseModel):
    active_classes: list[str] | None = None
    runtime_vocabulary: list[str] | None = None
    runtime_vocabulary_source: RuntimeVocabularySource | None = None
    runtime_vocabulary_version: int | None = None
    tracker_type: TrackerType | None = None
    privacy: WorkerPrivacySettings | None = None
    stream: WorkerStreamSettings | None = None
    attribute_rules: list[dict[str, Any]] | None = None
    incident_rules: list[WorkerIncidentRule] | None = None
    zones: list[WorkerZone] | None = None
    vision_profile: SceneVisionProfile | None = None
    detection_regions: list[DetectionRegion] | None = None
    homography: dict[str, Any] | None = None


class WorkerRuntimeCapability(BaseModel):
    execution_profiles: list[str] = Field(default_factory=list)
    detector_capabilities: list[DetectorCapability] = Field(default_factory=list)
    hot_runtime_vocabulary_updates: bool = False
    max_runtime_terms: int | None = None


class WorkerConfigResponse(BaseModel):
    camera_id: UUID
    mode: ProcessingMode
    scene_contract_hash: str | None = Field(default=None, min_length=64, max_length=64)
    privacy_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    runtime_passport_snapshot_id: UUID | None = None
    runtime_passport_hash: str | None = Field(default=None, min_length=64, max_length=64)
    recording_policy: EvidenceRecordingPolicy = Field(default_factory=EvidenceRecordingPolicy)
    evidence_storage: WorkerEvidenceStorageSettings | None = None
    camera: WorkerCameraSettings
    publish: WorkerPublishSettings = Field(default_factory=WorkerPublishSettings)
    stream: WorkerStreamSettings = Field(default_factory=WorkerStreamSettings)
    stream_delivery: WorkerStreamDeliverySettings | None = None
    model: WorkerModelSettings
    secondary_model: WorkerModelSettings | None = None
    tracker: WorkerTrackerSettings
    privacy: WorkerPrivacySettings = Field(default_factory=WorkerPrivacySettings)
    privacy_policy: WorkerPrivacyPolicySettings | None = None
    active_classes: list[str] = Field(default_factory=list)
    runtime_vocabulary: RuntimeVocabularyState = Field(default_factory=RuntimeVocabularyState)
    runtime_selection: WorkerRuntimeSelectionSettings = Field(
        default_factory=WorkerRuntimeSelectionSettings
    )
    runtime_capability: WorkerRuntimeCapability = Field(default_factory=WorkerRuntimeCapability)
    runtime_artifacts: list[WorkerRuntimeArtifact] = Field(default_factory=list)
    attribute_rules: list[dict[str, Any]] = Field(default_factory=list)
    incident_rules: list[WorkerIncidentRule] = Field(default_factory=list)
    zones: list[WorkerZone] = Field(default_factory=list)
    vision_profile: SceneVisionProfile = Field(default_factory=SceneVisionProfile)
    detection_regions: list[DetectionRegion] = Field(default_factory=list)
    homography: dict[str, Any] | None = None


class CameraCreate(BaseModel):
    site_id: UUID
    edge_node_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    rtsp_url: str | None = Field(default=None, min_length=1)
    camera_source: CameraSourceSettings | None = None
    processing_mode: ProcessingMode
    primary_model_id: UUID
    secondary_model_id: UUID | None = None
    tracker_type: TrackerType
    active_classes: list[str] = Field(default_factory=list)
    runtime_vocabulary: RuntimeVocabularyState = Field(default_factory=RuntimeVocabularyState)
    attribute_rules: list[dict[str, Any]] = Field(default_factory=list)
    zones: list[CameraZone] = Field(default_factory=list)
    vision_profile: SceneVisionProfile = Field(default_factory=SceneVisionProfile)
    detection_regions: list[DetectionRegion] = Field(default_factory=list)
    homography: HomographyPayload | None = None
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    browser_delivery: BrowserDeliverySettings = Field(default_factory=BrowserDeliverySettings)
    frame_skip: int = Field(default=1, ge=1)
    fps_cap: int = Field(default=25, ge=1)
    recording_policy: EvidenceRecordingPolicy = Field(default_factory=EvidenceRecordingPolicy)

    @model_validator(mode="after")
    def validate_camera_create(self) -> CameraCreate:
        if self.camera_source is None and self.rtsp_url is None:
            raise ValueError("Either rtsp_url or camera_source is required.")
        if self.camera_source is not None and self.rtsp_url is None:
            self.rtsp_url = self.camera_source.uri
        if self.vision_profile.motion_metrics.speed_enabled and self.homography is None:
            raise ValueError("Homography is required when speed metrics are enabled.")
        return self


class CameraUpdate(BaseModel):
    site_id: UUID | None = None
    edge_node_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    rtsp_url: str | None = Field(default=None, min_length=1)
    camera_source: CameraSourceSettings | None = None
    processing_mode: ProcessingMode | None = None
    primary_model_id: UUID | None = None
    secondary_model_id: UUID | None = None
    tracker_type: TrackerType | None = None
    active_classes: list[str] | None = None
    runtime_vocabulary: RuntimeVocabularyState | None = None
    attribute_rules: list[dict[str, Any]] | None = None
    zones: list[CameraZone] | None = None
    vision_profile: SceneVisionProfile | None = None
    detection_regions: list[DetectionRegion] | None = None
    homography: HomographyPayload | None = None
    privacy: PrivacySettings | None = None
    browser_delivery: BrowserDeliverySettings | None = None
    frame_skip: int | None = Field(default=None, ge=1)
    fps_cap: int | None = Field(default=None, ge=1)
    recording_policy: EvidenceRecordingPolicy | None = None

    @model_validator(mode="after")
    def reject_enabling_speed_while_clearing_homography(self) -> CameraUpdate:
        if "vision_profile" in self.model_fields_set and self.vision_profile is None:
            raise ValueError("vision_profile cannot be null.")
        if "detection_regions" in self.model_fields_set and self.detection_regions is None:
            raise ValueError("detection_regions cannot be null.")
        if (
            self.vision_profile is not None
            and self.vision_profile.motion_metrics.speed_enabled
            and "homography" in self.model_fields_set
            and self.homography is None
        ):
            raise ValueError("Homography is required when speed metrics are enabled.")
        return self


class CameraResponse(BaseModel):
    id: UUID
    site_id: UUID
    edge_node_id: UUID | None = None
    name: str
    rtsp_url_masked: str
    camera_source: CameraSourceSettings = Field(
        default_factory=lambda: CameraSourceSettings(
            kind=CameraSourceKind.RTSP,
            uri="rtsp://***",
        )
    )
    processing_mode: ProcessingMode
    primary_model_id: UUID
    secondary_model_id: UUID | None = None
    tracker_type: TrackerType
    active_classes: list[str]
    runtime_vocabulary: RuntimeVocabularyState = Field(default_factory=RuntimeVocabularyState)
    attribute_rules: list[dict[str, Any]]
    zones: list[StoredCameraZone]
    vision_profile: SceneVisionProfile = Field(default_factory=SceneVisionProfile)
    detection_regions: list[DetectionRegion] = Field(default_factory=list)
    homography: HomographyPayload | None = None
    privacy: PrivacySettings
    browser_delivery: BrowserDeliverySettings
    source_capability: SourceCapability | None = None
    frame_skip: int
    fps_cap: int
    recording_policy: EvidenceRecordingPolicy = Field(default_factory=EvidenceRecordingPolicy)
    created_at: datetime
    updated_at: datetime


class CameraSetupPreviewResponse(BaseModel):
    camera_id: UUID
    preview_url: str = Field(min_length=1)
    frame_size: FrameSize
    captured_at: datetime


class EdgeRegisterRequest(BaseModel):
    site_id: UUID
    hostname: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)


class EdgeRegisterResponse(BaseModel):
    edge_node_id: UUID
    api_key: str
    nats_nkey_seed: str
    subjects: list[str]
    mediamtx_url: str
    mediamtx_username: str | None = None
    mediamtx_password: str | None = None
    overlay_network_hints: dict[str, Any] = Field(default_factory=dict)


class EdgeHeartbeatRequest(BaseModel):
    node_id: UUID
    version: str = Field(min_length=1, max_length=64)
    cameras: int = Field(ge=0)


class EdgeHeartbeatResponse(BaseModel):
    status: str
    received_at: datetime


class FleetLifecycleMode(StrEnum):
    MANUAL_DEV = "manual_dev"
    SUPERVISED = "supervised"
    MIXED = "mixed"


class FleetNodeStatus(StrEnum):
    HEALTHY = "healthy"
    STALE = "stale"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class WorkerDesiredState(StrEnum):
    DESIRED = "desired"
    NOT_DESIRED = "not_desired"
    MANUAL = "manual"
    SUPERVISED = "supervised"


class WorkerRuntimeStatus(StrEnum):
    RUNNING = "running"
    STALE = "stale"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    NOT_REPORTED = "not_reported"


RuleLoadStatus = Literal["loaded", "stale", "unknown", "not_configured"]


class FleetSummary(BaseModel):
    desired_workers: int
    running_workers: int
    stale_nodes: int
    offline_nodes: int
    native_unavailable_cameras: int


class FleetNodeSummary(BaseModel):
    id: UUID | None = None
    kind: Literal["central", "edge"]
    hostname: str
    site_id: UUID | None = None
    status: FleetNodeStatus
    version: str | None = None
    last_seen_at: datetime | None = None
    assigned_camera_ids: list[UUID] = Field(default_factory=list)
    reported_camera_count: int | None = None


class RuntimePassportSummary(BaseModel):
    id: UUID
    passport_hash: str = Field(min_length=64, max_length=64)
    selected_backend: str | None = None
    model_hash: str | None = Field(default=None, min_length=64, max_length=64)
    runtime_artifact_id: UUID | None = None
    runtime_artifact_hash: str | None = Field(default=None, min_length=64, max_length=64)
    target_profile: str | None = None
    precision: str | None = None
    validated_at: datetime | None = None
    fallback_reason: str | None = None
    runtime_selection_profile_id: UUID | None = None
    runtime_selection_profile_name: str | None = None
    runtime_selection_profile_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    provider_versions: dict[str, Any] = Field(default_factory=dict)


class FleetRuleRuntimeSummary(BaseModel):
    configured_rule_count: int = Field(default=0, ge=0)
    effective_rule_hash: str | None = Field(default=None, min_length=64, max_length=64)
    latest_rule_event_at: datetime | None = None
    load_status: RuleLoadStatus = "not_configured"


class HardwarePerformanceSample(BaseModel):
    model_id: UUID | None = None
    model_name: str | None = None
    runtime_backend: str = Field(min_length=1, max_length=64)
    input_width: int = Field(gt=0)
    input_height: int = Field(gt=0)
    target_fps: float = Field(gt=0)
    observed_fps: float | None = Field(default=None, ge=0)
    stage_p95_ms: dict[str, float] = Field(default_factory=dict)
    stage_p99_ms: dict[str, float] = Field(default_factory=dict)
    captured_at: datetime | None = None


class EdgeNodeHardwareReportCreate(BaseModel):
    edge_node_id: UUID | None = None
    reported_at: datetime
    host_profile: str = Field(min_length=1, max_length=128)
    os_name: str = Field(min_length=1, max_length=64)
    machine_arch: str = Field(min_length=1, max_length=64)
    cpu_model: str | None = Field(default=None, max_length=255)
    cpu_cores: int | None = Field(default=None, ge=1)
    memory_total_mb: int | None = Field(default=None, ge=1)
    accelerators: list[str] = Field(default_factory=list)
    provider_capabilities: dict[str, bool] = Field(default_factory=dict)
    observed_performance: list[HardwarePerformanceSample] = Field(default_factory=list)
    thermal_state: str | None = Field(default=None, max_length=64)


class EdgeNodeHardwareReportResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    edge_node_id: UUID | None = None
    supervisor_id: str
    reported_at: datetime
    host_profile: str
    os_name: str
    machine_arch: str
    cpu_model: str | None = None
    cpu_cores: int | None = None
    memory_total_mb: int | None = None
    accelerators: list[str] = Field(default_factory=list)
    provider_capabilities: dict[str, bool] = Field(default_factory=dict)
    observed_performance: list[HardwarePerformanceSample] = Field(default_factory=list)
    thermal_state: str | None = None
    report_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime


class SupervisorServiceReportCreate(BaseModel):
    node_kind: DeploymentNodeKind
    edge_node_id: UUID | None = None
    hostname: str = Field(min_length=1, max_length=255)
    service_manager: DeploymentServiceManager
    service_status: str = Field(min_length=1, max_length=64)
    install_status: DeploymentInstallStatus
    credential_status: DeploymentCredentialStatus
    version: str | None = Field(default=None, max_length=64)
    os_name: str = Field(min_length=1, max_length=64)
    host_profile: str = Field(min_length=1, max_length=128)
    heartbeat_at: datetime
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_node_shape(self) -> SupervisorServiceReportCreate:
        if self.node_kind is DeploymentNodeKind.CENTRAL and self.edge_node_id is not None:
            raise ValueError("central deployment nodes cannot include edge_node_id")
        if self.node_kind is DeploymentNodeKind.EDGE and self.edge_node_id is None:
            raise ValueError("edge deployment nodes require edge_node_id")
        return self


class DeploymentNodeResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    node_kind: DeploymentNodeKind
    edge_node_id: UUID | None = None
    supervisor_id: str
    hostname: str
    install_status: DeploymentInstallStatus
    credential_status: DeploymentCredentialStatus
    service_manager: DeploymentServiceManager | None = None
    service_status: str | None = None
    version: str | None = None
    os_name: str | None = None
    host_profile: str | None = None
    last_service_reported_at: datetime | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SupervisorServiceReportResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    deployment_node_id: UUID
    edge_node_id: UUID | None = None
    supervisor_id: str
    node_kind: DeploymentNodeKind
    hostname: str
    service_manager: DeploymentServiceManager
    service_status: str
    install_status: DeploymentInstallStatus
    credential_status: DeploymentCredentialStatus
    version: str | None = None
    os_name: str
    host_profile: str
    heartbeat_at: datetime
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    node: DeploymentNodeResponse


class NodePairingSessionCreate(BaseModel):
    node_kind: DeploymentNodeKind
    edge_node_id: UUID | None = None
    hostname: str = Field(min_length=1, max_length=255)
    requested_ttl_seconds: int = Field(default=300, ge=60, le=900)

    @model_validator(mode="after")
    def _validate_node_shape(self) -> NodePairingSessionCreate:
        if self.node_kind is DeploymentNodeKind.CENTRAL and self.edge_node_id is not None:
            raise ValueError("central pairing sessions cannot include edge_node_id")
        if self.node_kind is DeploymentNodeKind.EDGE and self.edge_node_id is None:
            raise ValueError("edge pairing sessions require edge_node_id")
        return self


class NodePairingSessionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    deployment_node_id: UUID | None = None
    edge_node_id: UUID | None = None
    node_kind: DeploymentNodeKind
    hostname: str | None = None
    status: str
    expires_at: datetime
    consumed_at: datetime | None = None
    claimed_by_supervisor: str | None = None
    created_by_subject: str | None = None
    pairing_code: str | None = None
    created_at: datetime
    updated_at: datetime


class NodePairingClaim(BaseModel):
    pairing_code: str = Field(min_length=4, max_length=128)
    supervisor_id: str = Field(min_length=1, max_length=128)
    hostname: str = Field(min_length=1, max_length=255)


class NodePairingClaimResponse(BaseModel):
    session_id: UUID
    credential_id: UUID
    credential_material: str
    credential_hash: str
    credential_version: int = Field(default=1, ge=1)
    node: DeploymentNodeResponse


class NodeCredentialRevokeResponse(BaseModel):
    node_id: UUID
    revoked_credentials: int = Field(ge=0)
    credential_status: DeploymentCredentialStatus


class NodeCredentialRotateResponse(BaseModel):
    node_id: UUID
    credential_id: UUID
    credential_material: str
    credential_hash: str
    credential_version: int = Field(ge=1)
    revoked_credentials: int = Field(ge=0)
    credential_status: DeploymentCredentialStatus
    node: DeploymentNodeResponse


class MasterBootstrapStatusResponse(BaseModel):
    first_run_required: bool
    has_active_local_token: bool
    active_token_expires_at: datetime | None = None
    completed_at: datetime | None = None
    tenant_slug: str | None = None


class MasterBootstrapRotateResponse(BaseModel):
    bootstrap_token: str
    expires_at: datetime


class MasterBootstrapComplete(BaseModel):
    bootstrap_token: str = Field(min_length=8, max_length=256)
    tenant_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str | None = Field(default=None, min_length=1, max_length=255)
    admin_email: str = Field(min_length=3, max_length=320)
    admin_password: str = Field(min_length=8, max_length=256)
    central_node_name: str = Field(min_length=1, max_length=255)
    central_supervisor_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("tenant_slug")
    @classmethod
    def _normalize_tenant_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower().replace("_", "-").replace(" ", "-")
        if not normalized:
            return None
        return normalized

    @field_validator("admin_email")
    @classmethod
    def _normalize_admin_email(cls, value: str) -> str:
        return value.strip().lower()


class MasterBootstrapCompleteResponse(BaseModel):
    first_run_required: bool
    tenant_id: UUID
    tenant_slug: str
    admin_subject: str
    completed_at: datetime
    central_node: DeploymentNodeResponse


class WorkerModelAdmissionRequest(BaseModel):
    camera_id: UUID
    edge_node_id: UUID | None = None
    assignment_id: UUID | None = None
    model_id: UUID | None = None
    model_name: str | None = None
    model_capability: DetectorCapability = DetectorCapability.FIXED_VOCAB
    runtime_artifact_id: UUID | None = None
    runtime_artifact_target_profile: str | None = Field(default=None, max_length=128)
    runtime_selection_profile_id: UUID | None = None
    selected_backend: str | None = Field(default=None, max_length=64)
    preferred_backend: str | None = Field(default=None, max_length=64)
    stream_profile: dict[str, Any] = Field(default_factory=dict)
    fallback_allowed: bool = True


class WorkerModelAdmissionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    camera_id: UUID
    edge_node_id: UUID | None = None
    assignment_id: UUID | None = None
    hardware_report_id: UUID | None = None
    model_id: UUID | None = None
    model_name: str | None = None
    model_capability: DetectorCapability | None = None
    runtime_artifact_id: UUID | None = None
    runtime_selection_profile_id: UUID | None = None
    stream_profile: dict[str, Any] = Field(default_factory=dict)
    status: ModelAdmissionStatus
    selected_backend: str | None = None
    recommended_model_id: UUID | None = None
    recommended_model_name: str | None = None
    recommended_runtime_profile_id: UUID | None = None
    recommended_backend: str | None = None
    rationale: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime
    created_at: datetime


class SupervisorPollRequest(BaseModel):
    edge_node_id: UUID | None = None
    limit: int = Field(default=10, ge=1, le=100)


class SupervisorPollResponse(BaseModel):
    supervisor_id: str
    edge_node_id: UUID | None = None
    requests: list[OperationsLifecycleRequestResponse] = Field(default_factory=list)


class LifecycleRequestClaim(BaseModel):
    supervisor_id: str = Field(min_length=1, max_length=128)
    edge_node_id: UUID | None = None


class LifecycleRequestCompletion(BaseModel):
    supervisor_id: str = Field(min_length=1, max_length=128)
    status: OperationsLifecycleStatus
    admission_report_id: UUID | None = None
    error: str | None = None

    @model_validator(mode="after")
    def _validate_terminal_status(self) -> LifecycleRequestCompletion:
        if self.status not in {
            OperationsLifecycleStatus.COMPLETED,
            OperationsLifecycleStatus.FAILED,
        }:
            raise ValueError("completion status must be completed or failed")
        return self


class WorkerAssignmentCreate(BaseModel):
    camera_id: UUID
    edge_node_id: UUID | None = None
    desired_state: WorkerDesiredState = WorkerDesiredState.SUPERVISED


class WorkerAssignmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    camera_id: UUID
    edge_node_id: UUID | None = None
    desired_state: WorkerDesiredState
    active: bool
    supersedes_assignment_id: UUID | None = None
    assigned_by_subject: str | None = None
    created_at: datetime
    updated_at: datetime


class SupervisorRuntimeReportCreate(BaseModel):
    camera_id: UUID
    edge_node_id: UUID | None = None
    assignment_id: UUID | None = None
    heartbeat_at: datetime
    runtime_state: WorkerRuntimeState = WorkerRuntimeState.UNKNOWN
    restart_count: int = Field(default=0, ge=0)
    last_error: str | None = None
    runtime_artifact_id: UUID | None = None
    scene_contract_hash: str | None = Field(default=None, min_length=64, max_length=64)


class SupervisorRuntimeReportResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    camera_id: UUID
    edge_node_id: UUID | None = None
    assignment_id: UUID | None = None
    heartbeat_at: datetime
    runtime_state: WorkerRuntimeState
    restart_count: int = Field(ge=0)
    last_error: str | None = None
    runtime_artifact_id: UUID | None = None
    scene_contract_hash: str | None = Field(default=None, min_length=64, max_length=64)
    created_at: datetime


class OperationsLifecycleRequestCreate(BaseModel):
    camera_id: UUID
    edge_node_id: UUID | None = None
    assignment_id: UUID | None = None
    action: OperationsLifecycleAction
    request_payload: dict[str, Any] = Field(default_factory=dict)


class OperationsLifecycleRequestResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    camera_id: UUID
    edge_node_id: UUID | None = None
    assignment_id: UUID | None = None
    action: OperationsLifecycleAction
    status: OperationsLifecycleStatus
    requested_by_subject: str | None = None
    requested_at: datetime
    acknowledged_at: datetime | None = None
    claimed_by_supervisor: str | None = None
    claimed_at: datetime | None = None
    completed_at: datetime | None = None
    admission_report_id: UUID | None = None
    error: str | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DeploymentSupportBundleResponse(BaseModel):
    node: DeploymentNodeResponse
    service_reports: list[SupervisorServiceReportResponse] = Field(default_factory=list)
    recent_lifecycle_requests: list[OperationsLifecycleRequestResponse] = Field(
        default_factory=list
    )
    recent_runtime_reports: list[SupervisorRuntimeReportResponse] = Field(
        default_factory=list
    )
    hardware_reports: list[EdgeNodeHardwareReportResponse] = Field(default_factory=list)
    model_admission_reports: list[WorkerModelAdmissionResponse] = Field(
        default_factory=list
    )
    lifecycle_summary: dict[str, Any] = Field(default_factory=dict)
    runtime_summary: dict[str, Any] = Field(default_factory=dict)
    hardware_summary: dict[str, Any] = Field(default_factory=dict)
    model_admission_summary: dict[str, Any] = Field(default_factory=dict)
    config_references: dict[str, Any] = Field(default_factory=dict)
    selected_log_excerpts: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime


class FleetCameraWorkerSummary(BaseModel):
    camera_id: UUID
    camera_name: str
    site_id: UUID
    node_id: UUID | None = None
    node_hostname: str | None = None
    processing_mode: ProcessingMode
    desired_state: WorkerDesiredState
    runtime_status: WorkerRuntimeStatus
    lifecycle_owner: Literal["manual_dev", "central_supervisor", "edge_supervisor", "none"]
    dev_run_command: str | None = None
    detail: str | None = None
    runtime_passport: RuntimePassportSummary | None = None
    rule_runtime: FleetRuleRuntimeSummary = Field(default_factory=FleetRuleRuntimeSummary)
    assignment: WorkerAssignmentResponse | None = None
    runtime_report: SupervisorRuntimeReportResponse | None = None
    latest_lifecycle_request: OperationsLifecycleRequestResponse | None = None
    latest_hardware_report: EdgeNodeHardwareReportResponse | None = None
    latest_model_admission: WorkerModelAdmissionResponse | None = None
    supervisor_mode: SupervisorMode = SupervisorMode.DISABLED
    restart_policy: Literal["never", "on_failure", "always"] = "never"
    allowed_lifecycle_actions: list[OperationsLifecycleAction] = Field(default_factory=list)
    last_error: str | None = None


class OperationalMemoryPatternResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID | None = None
    camera_id: UUID | None = None
    pattern_type: str
    severity: IncidentRuleSeverity
    summary: str
    window_started_at: datetime
    window_ended_at: datetime
    source_incident_ids: list[UUID] = Field(default_factory=list)
    source_contract_hashes: list[str] = Field(default_factory=list)
    dimensions: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    pattern_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime


class PolicyDraftCreate(BaseModel):
    camera_id: UUID
    prompt: str = Field(min_length=1, max_length=8000)
    use_llm: bool = True


class PolicyDraftResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    camera_id: UUID | None = None
    site_id: UUID | None = None
    status: PolicyDraftStatus
    prompt: str
    structured_diff: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by_subject: str | None = None
    approved_by_subject: str | None = None
    rejected_by_subject: str | None = None
    applied_by_subject: str | None = None
    created_at: datetime
    updated_at: datetime
    decided_at: datetime | None = None
    applied_at: datetime | None = None


class FleetDeliveryDiagnostic(BaseModel):
    camera_id: UUID
    camera_name: str
    processing_mode: ProcessingMode
    assigned_node_id: UUID | None = None
    source_capability: SourceCapability | None = None
    default_profile: BrowserDeliveryProfileId
    available_profiles: list[BrowserDeliveryProfile] = Field(default_factory=list)
    native_status: NativeAvailability = Field(default_factory=NativeAvailability)
    selected_stream_mode: Literal["passthrough", "transcode"]


class FleetOverviewResponse(BaseModel):
    mode: FleetLifecycleMode
    generated_at: datetime
    summary: FleetSummary
    nodes: list[FleetNodeSummary]
    camera_workers: list[FleetCameraWorkerSummary]
    delivery_diagnostics: list[FleetDeliveryDiagnostic]


class FleetBootstrapRequest(BaseModel):
    site_id: UUID
    hostname: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)


class FleetBootstrapResponse(EdgeRegisterResponse):
    dev_compose_command: str
    supervisor_environment: dict[str, str] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    prompt: str = Field(min_length=1)
    camera_ids: list[UUID] = Field(min_length=1)


class QueryResponse(BaseModel):
    resolution_mode: QueryResolutionMode = QueryResolutionMode.FIXED_FILTER
    resolved_classes: list[str]
    resolved_vocabulary: list[str] = Field(default_factory=list)
    provider: str
    model: str
    latency_ms: int
    camera_ids: list[UUID]


class CountEventBoundarySummary(BaseModel):
    boundary_id: str
    event_types: list[CountEventType]


class HistoryPoint(BaseModel):
    bucket: datetime
    camera_id: UUID | None = None
    class_name: str
    event_count: int
    granularity: str
    metric: HistoryMetric | None = None


class HistorySeriesRow(BaseModel):
    bucket: datetime
    values: dict[str, int]
    total_count: int
    speed_p50: dict[str, float] | None = None
    speed_p95: dict[str, float] | None = None
    speed_sample_count: dict[str, int] | None = None
    over_threshold_count: dict[str, int] | None = None


class HistoryBucketCoverage(BaseModel):
    bucket: datetime
    status: HistoryCoverageStatus
    reason: str | None = None


class HistorySeriesResponse(BaseModel):
    granularity: str
    metric: HistoryMetric | None = None
    class_names: list[str]
    rows: list[HistorySeriesRow]
    granularity_adjusted: bool = False
    speed_classes_capped: bool = False
    speed_classes_used: list[str] | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    bucket_count: int = 0
    bucket_span: str | None = None
    coverage_status: HistoryCoverageStatus = HistoryCoverageStatus.POPULATED
    coverage_by_bucket: list[HistoryBucketCoverage] = Field(default_factory=list)


class HistoryClassEntry(BaseModel):
    class_name: str
    event_count: int
    has_speed_data: bool


class HistoryClassesResponse(BaseModel):
    from_: datetime = Field(serialization_alias="from", validation_alias="from")
    to: datetime
    metric: HistoryMetric | None = None
    boundaries: list[CountEventBoundarySummary] = Field(default_factory=list)
    classes: list[HistoryClassEntry]


class EvidenceArtifactResponse(BaseModel):
    id: UUID
    incident_id: UUID
    camera_id: UUID
    kind: EvidenceArtifactKind
    status: EvidenceArtifactStatus
    storage_provider: EvidenceStorageProvider
    storage_scope: EvidenceStorageScope
    bucket: str | None = None
    object_key: str
    content_type: str
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    clip_started_at: datetime | None = None
    triggered_at: datetime | None = None
    clip_ended_at: datetime | None = None
    duration_seconds: float | None = None
    fps: int | None = None
    scene_contract_hash: str | None = Field(default=None, min_length=64, max_length=64)
    privacy_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    review_url: str | None = None
    sync_status: str | None = None
    sync_error: str | None = None


class EvidenceLedgerSummary(BaseModel):
    entry_count: int = 0
    latest_action: EvidenceLedgerAction | None = None
    latest_at: datetime | None = None


class EvidenceLedgerEntryResponse(BaseModel):
    id: UUID
    incident_id: UUID
    camera_id: UUID
    sequence: int
    action: EvidenceLedgerAction
    actor_type: str
    actor_subject: str | None = None
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_entry_hash: str | None = Field(default=None, min_length=64, max_length=64)
    entry_hash: str = Field(min_length=64, max_length=64)


class SceneContractSnapshotResponse(BaseModel):
    id: UUID
    camera_id: UUID
    schema_version: int
    contract_hash: str = Field(min_length=64, max_length=64)
    contract: dict[str, Any]
    created_at: datetime | None = None


class PrivacyManifestSnapshotResponse(BaseModel):
    id: UUID
    camera_id: UUID
    schema_version: int
    manifest_hash: str = Field(min_length=64, max_length=64)
    manifest: dict[str, Any]
    created_at: datetime | None = None


class RuntimePassportSnapshotResponse(BaseModel):
    id: UUID
    camera_id: UUID
    incident_id: UUID | None = None
    schema_version: int
    passport_hash: str = Field(min_length=64, max_length=64)
    passport: dict[str, Any]
    summary: RuntimePassportSummary
    created_at: datetime | None = None


class CrossCameraThreadResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID | None = None
    camera_ids: list[UUID]
    source_incident_ids: list[UUID]
    privacy_manifest_hashes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    rationale: list[str] = Field(default_factory=list)
    signals: dict[str, Any] = Field(default_factory=dict)
    privacy_labels: list[str] = Field(default_factory=list)
    thread_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime | None = None


class IncidentResponse(BaseModel):
    id: UUID
    camera_id: UUID
    camera_name: str | None = None
    ts: datetime
    type: str
    payload: dict[str, Any]
    snapshot_url: str | None = None
    clip_url: str | None = None
    storage_bytes: int = 0
    review_status: IncidentReviewStatus = IncidentReviewStatus.PENDING
    reviewed_at: datetime | None = None
    reviewed_by_subject: str | None = None
    scene_contract_hash: str | None = None
    scene_contract_id: UUID | None = None
    privacy_manifest_hash: str | None = None
    privacy_manifest_id: UUID | None = None
    runtime_passport_hash: str | None = None
    runtime_passport_id: UUID | None = None
    runtime_passport: RuntimePassportSummary | None = None
    trigger_rule: TriggerRuleSummary | None = None
    recording_policy: EvidenceRecordingPolicy | None = None
    evidence_artifacts: list[EvidenceArtifactResponse] = Field(default_factory=list)
    ledger_summary: EvidenceLedgerSummary | None = None


class IncidentReviewUpdate(BaseModel):
    review_status: IncidentReviewStatus


class StreamOfferRequest(BaseModel):
    sdp_offer: str = Field(min_length=1)


class StreamOfferResponse(BaseModel):
    camera_id: UUID
    sdp_answer: str


class TelemetryEnvelope(BaseModel):
    events: list[TelemetryFrame] = Field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ExportArtifact:
    filename: str
    media_type: str
    content: bytes


@dataclass(slots=True, frozen=True)
class TenantContext:
    tenant_id: UUID
    tenant_slug: str
    user: AuthenticatedUser
