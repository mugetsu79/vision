from __future__ import annotations

from argus.compat import StrEnum


class RoleEnum(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class ProcessingMode(StrEnum):
    CENTRAL = "central"
    EDGE = "edge"
    HYBRID = "hybrid"


class CameraSourceKind(StrEnum):
    RTSP = "rtsp"
    USB = "usb"
    JETSON_CSI = "jetson_csi"


class TrackerType(StrEnum):
    BOTSORT = "botsort"
    BYTETRACK = "bytetrack"
    OCSORT = "ocsort"


class DetectorCapability(StrEnum):
    FIXED_VOCAB = "fixed_vocab"
    OPEN_VOCAB = "open_vocab"


class RuntimeArtifactScope(StrEnum):
    MODEL = "model"
    SCENE = "scene"


class RuntimeArtifactKind(StrEnum):
    ONNX_EXPORT = "onnx_export"
    TENSORRT_ENGINE = "tensorrt_engine"


class RuntimeArtifactPrecision(StrEnum):
    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"


class RuntimeArtifactValidationStatus(StrEnum):
    UNVALIDATED = "unvalidated"
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"
    MISSING_ARTIFACT = "missing_artifact"
    TARGET_MISMATCH = "target_mismatch"


class RuntimeVocabularySource(StrEnum):
    DEFAULT = "default"
    QUERY = "query"
    MANUAL = "manual"


class QueryResolutionMode(StrEnum):
    FIXED_FILTER = "fixed_filter"
    OPEN_VOCAB = "open_vocab"


class ModelTask(StrEnum):
    DETECT = "detect"
    CLASSIFY = "classify"
    ATTRIBUTE = "attribute"


class HistoryMetric(StrEnum):
    OCCUPANCY = "occupancy"
    COUNT_EVENTS = "count_events"
    OBSERVATIONS = "observations"


class HistoryCoverageStatus(StrEnum):
    POPULATED = "populated"
    ZERO = "zero"
    NO_TELEMETRY = "no_telemetry"
    CAMERA_OFFLINE = "camera_offline"
    WORKER_OFFLINE = "worker_offline"
    SOURCE_UNAVAILABLE = "source_unavailable"
    NO_SCOPE = "no_scope"
    ACCESS_LIMITED = "access_limited"


class IncidentReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"


class EvidenceArtifactKind(StrEnum):
    EVENT_CLIP = "event_clip"
    SNAPSHOT = "snapshot"
    MANIFEST_EXPORT = "manifest_export"
    CASE_EXPORT = "case_export"


class EvidenceArtifactStatus(StrEnum):
    AVAILABLE = "available"
    LOCAL_ONLY = "local_only"
    REMOTE_AVAILABLE = "remote_available"
    UPLOAD_PENDING = "upload_pending"
    QUOTA_EXCEEDED = "quota_exceeded"
    CAPTURE_FAILED = "capture_failed"
    EXPIRED = "expired"


class EvidenceStorageProvider(StrEnum):
    LOCAL_FILESYSTEM = "local_filesystem"
    MINIO = "minio"
    S3_COMPATIBLE = "s3_compatible"


class EvidenceStorageScope(StrEnum):
    EDGE = "edge"
    CENTRAL = "central"
    CLOUD = "cloud"


class EvidenceLedgerAction(StrEnum):
    INCIDENT_TRIGGERED = "incident.triggered"
    SCENE_CONTRACT_ATTACHED = "scene_contract.attached"
    PRIVACY_MANIFEST_ATTACHED = "privacy_manifest.attached"
    CLIP_CAPTURE_STARTED = "evidence.clip.capture_started"
    CLIP_AVAILABLE = "evidence.clip.available"
    CLIP_QUOTA_EXCEEDED = "evidence.clip.quota_exceeded"
    CLIP_CAPTURE_FAILED = "evidence.clip.capture_failed"
    INCIDENT_REVIEWED = "incident.reviewed"
    INCIDENT_REOPENED = "incident.reopened"


class OperatorConfigProfileKind(StrEnum):
    EVIDENCE_STORAGE = "evidence_storage"
    STREAM_DELIVERY = "stream_delivery"
    RUNTIME_SELECTION = "runtime_selection"
    PRIVACY_POLICY = "privacy_policy"
    LLM_PROVIDER = "llm_provider"
    OPERATIONS_MODE = "operations_mode"


class OperatorConfigScope(StrEnum):
    TENANT = "tenant"
    SITE = "site"
    EDGE_NODE = "edge_node"
    CAMERA = "camera"


class OperatorConfigValidationStatus(StrEnum):
    UNVALIDATED = "unvalidated"
    VALID = "valid"
    INVALID = "invalid"


class CountEventType(StrEnum):
    LINE_CROSS = "line_cross"
    ZONE_ENTER = "zone_enter"
    ZONE_EXIT = "zone_exit"


class ModelFormat(StrEnum):
    ONNX = "onnx"
    ENGINE = "engine"
    PT = "pt"


class RuleAction(StrEnum):
    COUNT = "count"
    ALERT = "alert"
    RECORD_CLIP = "record_clip"
    WEBHOOK = "webhook"
