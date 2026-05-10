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
    CountEventType,
    DetectorCapability,
    HistoryCoverageStatus,
    HistoryMetric,
    IncidentReviewStatus,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    QueryResolutionMode,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
    RuntimeVocabularySource,
    TrackerType,
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


BrowserDeliveryProfileId = Literal["native", "annotated", "1080p15", "720p10", "540p5"]


def _default_browser_delivery_profiles() -> list[dict[str, Any]]:
    return [
        {"id": "native", "kind": "passthrough"},
        {"id": "annotated", "kind": "transcode"},
        {"id": "1080p15", "kind": "transcode", "w": 1920, "h": 1080, "fps": 15},
        {"id": "720p10", "kind": "transcode", "w": 1280, "h": 720, "fps": 10},
        {"id": "540p5", "kind": "transcode", "w": 960, "h": 540, "fps": 5},
    ]


class SourceCapability(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int | None = Field(default=None, ge=1)
    codec: str | None = None
    aspect_ratio: str | None = None


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
    profiles: list[dict[str, Any]] = Field(default_factory=_default_browser_delivery_profiles)
    unsupported_profiles: list[dict[str, Any]] = Field(default_factory=list)
    native_status: NativeAvailability = Field(default_factory=NativeAvailability)


class CameraSourceProbeRequest(BaseModel):
    camera_id: UUID | None = None
    rtsp_url: str | None = Field(default=None, min_length=1)
    processing_mode: ProcessingMode = ProcessingMode.CENTRAL
    edge_node_id: UUID | None = None
    browser_delivery: BrowserDeliverySettings | None = None
    privacy: PrivacySettings | None = None


class CameraSourceProbeResponse(BaseModel):
    source_capability: SourceCapability | None = None
    browser_delivery: BrowserDeliverySettings


class WorkerCameraSettings(BaseModel):
    rtsp_url: str = Field(min_length=1)
    frame_skip: int = Field(default=1, ge=1)
    fps_cap: int = Field(default=25, ge=1)


class WorkerPublishSettings(BaseModel):
    subject_prefix: str = "evt.tracking"
    http_fallback_url: str | None = None


class WorkerStreamSettings(BaseModel):
    profile_id: BrowserDeliveryProfileId = "native"
    kind: Literal["passthrough", "transcode"] = "passthrough"
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    fps: int = Field(default=25, ge=1)


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


class CameraCommandPayload(BaseModel):
    active_classes: list[str] | None = None
    runtime_vocabulary: list[str] | None = None
    runtime_vocabulary_source: RuntimeVocabularySource | None = None
    runtime_vocabulary_version: int | None = None
    tracker_type: TrackerType | None = None
    privacy: WorkerPrivacySettings | None = None
    stream: WorkerStreamSettings | None = None
    attribute_rules: list[dict[str, Any]] | None = None
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
    camera: WorkerCameraSettings
    publish: WorkerPublishSettings = Field(default_factory=WorkerPublishSettings)
    stream: WorkerStreamSettings = Field(default_factory=WorkerStreamSettings)
    model: WorkerModelSettings
    secondary_model: WorkerModelSettings | None = None
    tracker: WorkerTrackerSettings
    privacy: WorkerPrivacySettings = Field(default_factory=WorkerPrivacySettings)
    active_classes: list[str] = Field(default_factory=list)
    runtime_vocabulary: RuntimeVocabularyState = Field(default_factory=RuntimeVocabularyState)
    runtime_capability: WorkerRuntimeCapability = Field(default_factory=WorkerRuntimeCapability)
    runtime_artifacts: list[WorkerRuntimeArtifact] = Field(default_factory=list)
    attribute_rules: list[dict[str, Any]] = Field(default_factory=list)
    zones: list[WorkerZone] = Field(default_factory=list)
    vision_profile: SceneVisionProfile = Field(default_factory=SceneVisionProfile)
    detection_regions: list[DetectionRegion] = Field(default_factory=list)
    homography: dict[str, Any] | None = None


class CameraCreate(BaseModel):
    site_id: UUID
    name: str = Field(min_length=1, max_length=255)
    rtsp_url: str = Field(min_length=1)
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

    @model_validator(mode="after")
    def require_homography_for_speed_metrics(self) -> CameraCreate:
        if self.vision_profile.motion_metrics.speed_enabled and self.homography is None:
            raise ValueError("Homography is required when speed metrics are enabled.")
        return self


class CameraUpdate(BaseModel):
    site_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    rtsp_url: str | None = Field(default=None, min_length=1)
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
