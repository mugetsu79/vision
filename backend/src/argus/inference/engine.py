from __future__ import annotations

import argparse
import asyncio
import contextlib
import inspect
import logging
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import cv2
import httpx
import numpy as np
from numpy.typing import NDArray
from prometheus_client import start_http_server
from pydantic import BaseModel, ConfigDict, Field, model_validator

from argus.api.contracts import (
    CameraSourceSettings,
    DetectionRegion,
    EvidenceRecordingPolicy,
    SceneVisionProfile,
    TriggerRuleSummary,
    WorkerEvidenceStorageSettings,
    WorkerIncidentRule,
    WorkerIncidentRulePredicate,
    WorkerPrivacyPolicySettings,
    WorkerRuntimeSelectionSettings,
)
from argus.compat import UTC
from argus.core.config import Settings
from argus.core.db import (
    CountEventStore,
    DatabaseManager,
    TrackingEventBatchRecord,
    TrackingEventStore,
)
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.core.logging import configure_logging, redact_url_secrets
from argus.core.metrics import (
    CANDIDATE_PASSED_TOTAL,
    CANDIDATE_REJECTED_TOTAL,
    DETECTION_REGION_FILTERED_TOTAL,
    INFERENCE_FRAME_DURATION_SECONDS,
    INFERENCE_FRAMES_PROCESSED_TOTAL,
    INFERENCE_STAGE_DURATION_SECONDS,
    MOTION_SPEED_DISABLED_TOTAL,
    MOTION_SPEED_SAMPLES_TOTAL,
)
from argus.inference.publisher import (
    BufferedTelemetryPublisher,
    HttpPublisher,
    NatsPublisher,
    ResilientPublisher,
    TelemetryFrame,
    TelemetryTrack,
)
from argus.models.enums import (
    CameraSourceKind,
    DetectorCapability,
    IncidentRuleSeverity,
    ProcessingMode,
    RuleAction,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeVocabularySource,
    TrackerType,
)
from argus.services.evidence_storage import ResolvedEvidenceStorageResolver, build_evidence_store
from argus.services.incident_capture import (
    IncidentClipCaptureService,
    IncidentTriggeredEvent,
    SQLIncidentRepository,
)
from argus.services.rule_events import SQLRuleEventStore
from argus.streaming.mediamtx import (
    MediaMTXClient,
    PrivacyPolicy,
    PublishProfile,
    StreamMode,
    StreamRegistration,
    default_profile_probe,
    probe_publish_profile,
)
from argus.streaming.webrtc import MediaMTXTokenIssuer
from argus.vision.anpr import LineCrossingAnprProcessor
from argus.vision.attributes import AttributeClassifier, AttributeModelConfig
from argus.vision.camera import CameraSourceConfig, create_camera_source
from argus.vision.candidate_quality import CandidateDecision, CandidateQualityGate
from argus.vision.count_events import CountEventProcessor, CountEventRecord
from argus.vision.detection_regions import DetectionRegionDecision, DetectionRegionPolicy
from argus.vision.detector import YoloDetector
from argus.vision.detector_factory import build_detector as _build_detector
from argus.vision.homography import Homography
from argus.vision.privacy import PrivacyConfig, PrivacyFilter
from argus.vision.profiles import resolve_scene_vision_profile
from argus.vision.rules import RuleDefinition, RuleEngine, RuleEventRecord, RuleStore
from argus.vision.runtime import (
    RuntimeExecutionPolicy,
    import_onnxruntime,
    resolve_execution_policy,
)
from argus.vision.runtime_selection import RuntimeSelection, select_runtime_artifact
from argus.vision.track_lifecycle import LifecycleTrack, TrackLifecycleManager
from argus.vision.tracker import TrackerConfig, create_tracker
from argus.vision.types import Detection
from argus.vision.vocabulary import hash_vocabulary
from argus.vision.zones import Zones

Frame = NDArray[np.uint8]

logger = logging.getLogger(__name__)
_CAPTURE_WAIT_SPIKE_WARNING_THRESHOLD_S = 0.250

_FACE_PRIVACY_DETECTION_CLASSES = ("person", "pedestrian")
_ACTIVE_ANNOTATION_COLORS_BGR: dict[str, tuple[int, int, int]] = {
    "person": (80, 255, 170),
    "pedestrian": (80, 255, 170),
    "car": (255, 145, 72),
    "bus": (255, 145, 72),
    "truck": (255, 145, 72),
    "bicycle": (255, 145, 72),
    "motorcycle": (255, 145, 72),
    "hardhat": (80, 210, 255),
    "helmet": (80, 210, 255),
    "vest": (80, 210, 255),
}
_DEFAULT_ACTIVE_ANNOTATION_COLOR_BGR = (255, 196, 64)
_COASTING_ANNOTATION_COLORS_BGR: dict[str, tuple[int, int, int]] = {
    "person": (72, 184, 128),
    "pedestrian": (72, 184, 128),
}
_DEFAULT_COASTING_ANNOTATION_COLOR_BGR = (140, 154, 178)
_DASHED_BOX_SEGMENT_PX = 8
_TIMEOUT_ERRORS: tuple[type[BaseException], ...] = (TimeoutError,)
_asyncio_timeout_error = getattr(asyncio, "TimeoutError", None)
if (
    isinstance(_asyncio_timeout_error, type)
    and issubclass(_asyncio_timeout_error, BaseException)
    and _asyncio_timeout_error is not TimeoutError
):
    _TIMEOUT_ERRORS = (TimeoutError, _asyncio_timeout_error)


class RuntimeVocabularySettings(BaseModel):
    terms: list[str] = Field(default_factory=list)
    source: RuntimeVocabularySource = RuntimeVocabularySource.DEFAULT
    version: int = 0
    updated_at: datetime | None = None


class ModelSettings(BaseModel):
    name: str
    path: str
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB
    capability_config: dict[str, Any] = Field(default_factory=dict)
    classes: list[str]
    runtime_vocabulary: RuntimeVocabularySettings = Field(
        default_factory=RuntimeVocabularySettings
    )
    input_shape: dict[str, int]
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45


class RuntimeArtifactSettings(BaseModel):
    id: UUID
    scope: RuntimeArtifactScope
    kind: RuntimeArtifactKind
    capability: DetectorCapability
    runtime_backend: str
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


class CameraSettings(BaseModel):
    rtsp_url: str | None = None
    source_uri: str | None = None
    camera_source: CameraSourceSettings | None = None
    frame_skip: int = 1
    fps_cap: int = 25

    @property
    def source_kind(self) -> CameraSourceKind:
        if self.camera_source is not None:
            return self.camera_source.kind
        return CameraSourceKind.RTSP

    @property
    def resolved_source_uri(self) -> str:
        if self.source_uri is not None:
            return self.source_uri
        if self.rtsp_url is not None:
            return self.rtsp_url
        if self.camera_source is not None:
            return self.camera_source.uri
        raise ValueError("Camera settings require source_uri or rtsp_url.")

    @model_validator(mode="after")
    def resolve_source_fields(self) -> CameraSettings:
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
            raise ValueError("Camera settings require source_uri or rtsp_url.")
        return self


class PublishSettings(BaseModel):
    subject_prefix: str = "evt.tracking"
    http_fallback_url: str | None = None


class StreamSettings(BaseModel):
    profile_id: str = "native"
    kind: str = "passthrough"
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    fps: int = Field(default=25, ge=1)


class StreamDeliverySettings(BaseModel):
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_hash: str | None = Field(default=None, min_length=64, max_length=64)
    delivery_mode: str = "native"
    public_base_url: str | None = None
    edge_override_url: str | None = None


class TrackerSettings(BaseModel):
    tracker_type: TrackerType
    frame_rate: int = 25


class EngineConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    camera_id: UUID
    mode: ProcessingMode
    scene_contract_hash: str | None = Field(default=None, min_length=64, max_length=64)
    privacy_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    runtime_passport_snapshot_id: UUID | None = None
    runtime_passport_hash: str | None = Field(default=None, min_length=64, max_length=64)
    recording_policy: EvidenceRecordingPolicy = Field(default_factory=EvidenceRecordingPolicy)
    evidence_storage: WorkerEvidenceStorageSettings | None = None
    profile: PublishProfile | None = None
    camera: CameraSettings
    publish: PublishSettings = Field(default_factory=PublishSettings)
    stream: StreamSettings = Field(default_factory=StreamSettings)
    stream_delivery: StreamDeliverySettings | None = None
    model: ModelSettings
    secondary_model: ModelSettings | None = None
    tracker: TrackerSettings
    privacy: PrivacyPolicy = Field(default_factory=PrivacyPolicy)
    privacy_policy: WorkerPrivacyPolicySettings | None = None
    active_classes: list[str] = Field(default_factory=list)
    runtime_selection: WorkerRuntimeSelectionSettings = Field(
        default_factory=WorkerRuntimeSelectionSettings
    )
    runtime_artifacts: list[RuntimeArtifactSettings] = Field(default_factory=list)
    attribute_rules: list[dict[str, Any]] = Field(default_factory=list)
    incident_rules: list[WorkerIncidentRule] = Field(default_factory=list)
    zones: list[dict[str, Any]] = Field(default_factory=list)
    vision_profile: SceneVisionProfile = Field(default_factory=SceneVisionProfile)
    detection_regions: list[DetectionRegion] = Field(default_factory=list)
    homography: dict[str, Any] | None = None


class CameraCommand(BaseModel):
    active_classes: list[str] | None = None
    runtime_vocabulary: list[str] | None = None
    runtime_vocabulary_source: RuntimeVocabularySource | None = None
    runtime_vocabulary_version: int | None = None
    tracker_type: TrackerType | None = None
    privacy: PrivacyPolicy | None = None
    stream: StreamSettings | None = None
    attribute_rules: list[dict[str, Any]] | None = None
    incident_rules: list[WorkerIncidentRule] | None = None
    zones: list[dict[str, Any]] | None = None
    vision_profile: SceneVisionProfile | None = None
    detection_regions: list[DetectionRegion] | None = None
    homography: dict[str, Any] | None = None


class FrameSource(Protocol):
    def next_frame(self) -> Frame: ...

    def close(self) -> None: ...


class Detector(Protocol):
    capability: DetectorCapability

    def detect(
        self,
        frame: Frame,
        allowed_classes: list[str] | None = None,
    ) -> list[Detection]: ...

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None: ...


class Preprocessor(Protocol):
    def __call__(self, frame: Frame) -> Frame: ...


class Tracker(Protocol):
    def update(
        self,
        detections: list[Detection],
        frame: Frame | None = None,
    ) -> list[Detection]: ...


class TrackerFactory(Protocol):
    def __call__(self, tracker_type: TrackerType) -> Tracker: ...


class Publisher(Protocol):
    async def publish(self, frame: TelemetryFrame) -> None: ...

    async def close(self) -> None: ...


class TrackingStore(Protocol):
    async def record(
        self,
        camera_id: UUID,
        ts: datetime,
        detections: list[Detection],
        *,
        vocabulary_version: int | None = None,
        vocabulary_hash: str | None = None,
    ) -> None: ...


class CountEventStoreProtocol(Protocol):
    async def record(
        self,
        camera_id: UUID,
        events: list[CountEventRecord],
        *,
        vocabulary_version: int | None = None,
        vocabulary_hash: str | None = None,
    ) -> None: ...


class RuleEvaluator(Protocol):
    async def evaluate(
        self,
        *,
        camera_id: UUID,
        detections: list[Detection],
        ts: datetime,
    ) -> list[RuleEventRecord]: ...


class EventSubscriber(Protocol):
    async def subscribe(self, subject: str, handler: Any) -> Any: ...

    async def publish(self, subject: str, payload: BaseModel) -> Any: ...


class BufferedTrackingStore:
    def __init__(
        self,
        wrapped_store: TrackingStore,
        *,
        max_queue_size: int = 256,
        shutdown_timeout_seconds: float = 5.0,
        max_batch_size: int = 16,
        batch_flush_interval_seconds: float = 0.1,
    ) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be at least 1")
        if shutdown_timeout_seconds <= 0:
            raise ValueError("shutdown_timeout_seconds must be greater than 0")
        if max_batch_size < 1:
            raise ValueError("max_batch_size must be at least 1")
        if batch_flush_interval_seconds <= 0:
            raise ValueError("batch_flush_interval_seconds must be greater than 0")
        self.wrapped_store = wrapped_store
        self.max_queue_size = max_queue_size
        self.shutdown_timeout_seconds = shutdown_timeout_seconds
        self.max_batch_size = max_batch_size
        self.batch_flush_interval_seconds = batch_flush_interval_seconds
        self.dropped_records = 0
        self._queue: asyncio.Queue[TrackingEventBatchRecord | None] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self._worker_task: asyncio.Task[None] | None = None
        self._closed = False

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    async def record(
        self,
        camera_id: UUID,
        ts: datetime,
        detections: list[Detection],
        *,
        vocabulary_version: int | None = None,
        vocabulary_hash: str | None = None,
    ) -> None:
        if not detections or self._closed:
            return
        self._ensure_worker()
        record = TrackingEventBatchRecord(
            camera_id=camera_id,
            ts=ts,
            detections=list(detections),
            vocabulary_version=vocabulary_version,
            vocabulary_hash=vocabulary_hash,
        )
        try:
            self._queue.put_nowait(record)
        except asyncio.QueueFull:
            self._drop_oldest_pending()
            try:
                self._queue.put_nowait(record)
            except asyncio.QueueFull:
                self.dropped_records += 1
                logger.warning(
                    "Dropped tracking persistence record for camera %s because the "
                    "background queue remained full.",
                    camera_id,
                )

    async def close(self) -> None:
        self._closed = True
        worker_task = self._worker_task
        if worker_task is None:
            return
        if worker_task.done():
            await worker_task
            return
        try:
            await asyncio.wait_for(
                self._queue.put(None),
                timeout=self.shutdown_timeout_seconds,
            )
            await asyncio.wait_for(
                worker_task,
                timeout=self.shutdown_timeout_seconds,
            )
        except _TIMEOUT_ERRORS:
            worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker_task
            logger.warning(
                "Timed out while flushing tracking persistence queue; dropped %s "
                "pending records.",
                self._queue.qsize(),
            )

    def _ensure_worker(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(
                self._drain(),
                name="argus-tracking-persistence",
            )

    def _drop_oldest_pending(self) -> None:
        try:
            dropped = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        self._queue.task_done()
        if dropped is not None:
            self.dropped_records += 1
            logger.warning(
                "Dropped oldest tracking persistence record for camera %s because "
                "the background queue is full.",
                dropped.camera_id,
            )

    async def _drain(self) -> None:
        while True:
            record = await self._queue.get()
            if record is None:
                self._queue.task_done()
                return

            batch, should_stop = await self._collect_batch(record)
            try:
                await self._persist_batch(batch)
            except Exception:
                logger.exception(
                    "Failed to persist buffered tracking event batch for camera %s; "
                    "continuing worker loop.",
                    batch[0].camera_id if batch else "<empty>",
                )
            finally:
                for _ in batch:
                    self._queue.task_done()

            if should_stop:
                return

    async def _collect_batch(
        self,
        first_record: TrackingEventBatchRecord,
    ) -> tuple[list[TrackingEventBatchRecord], bool]:
        batch = [first_record]
        should_stop = False
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.batch_flush_interval_seconds

        while len(batch) < self.max_batch_size:
            timeout = deadline - loop.time()
            if timeout <= 0:
                break
            try:
                next_record = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            except _TIMEOUT_ERRORS:
                break
            if next_record is None:
                self._queue.task_done()
                should_stop = True
                break
            batch.append(next_record)

        return batch, should_stop

    async def _persist_batch(self, batch: list[TrackingEventBatchRecord]) -> None:
        record_many = getattr(self.wrapped_store, "record_many", None)
        if record_many is not None:
            await record_many(batch)
            return
        for record in batch:
            await self.wrapped_store.record(
                record.camera_id,
                record.ts,
                record.detections,
                vocabulary_version=record.vocabulary_version,
                vocabulary_hash=record.vocabulary_hash,
            )


class StreamClient(Protocol):
    async def register_stream(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        stream_kind: str,
        privacy: PrivacyPolicy,
        target_fps: int,
        target_width: int | None = None,
        target_height: int | None = None,
    ) -> StreamRegistration: ...

    async def push_frame(
        self,
        registration: StreamRegistration,
        frame: Frame,
        *,
        ts: datetime,
    ) -> None: ...


def build_detector(
    *,
    model: ModelSettings,
    runtime: Any,
    runtime_policy: RuntimeExecutionPolicy,
    runtime_selection: RuntimeSelection | None = None,
) -> Detector:
    return _build_detector(
        model=model,
        runtime=runtime,
        runtime_policy=runtime_policy,
        runtime_selection=runtime_selection,
        yolo_detector_cls=YoloDetector,
    )


def _build_detector_with_selection(
    *,
    model: ModelSettings,
    runtime: Any,
    runtime_policy: RuntimeExecutionPolicy,
    runtime_selection: RuntimeSelection,
) -> Detector:
    try:
        return build_detector(
            model=model,
            runtime=runtime,
            runtime_policy=runtime_policy,
            runtime_selection=runtime_selection,
        )
    except TypeError as exc:
        if "runtime_selection" not in str(exc):
            raise
        return build_detector(
            model=model,
            runtime=runtime,
            runtime_policy=runtime_policy,
        )


@dataclass(slots=True)
class _EngineState:
    active_classes: list[str]
    runtime_vocabulary: list[str]
    runtime_vocabulary_source: RuntimeVocabularySource
    runtime_vocabulary_version: int
    tracker_type: TrackerType
    privacy: PrivacyPolicy
    attribute_rules: list[dict[str, Any]]
    incident_rules: list[WorkerIncidentRule]
    zones: list[dict[str, Any]]
    vision_profile: SceneVisionProfile
    detection_regions: list[DetectionRegion]


@dataclass(slots=True)
class _FrameStageTimer:
    started_at: float
    last_mark_at: float
    durations: dict[str, float]

    @classmethod
    def start(cls, started_at: float) -> _FrameStageTimer:
        return cls(
            started_at=started_at,
            last_mark_at=started_at,
            durations={},
        )

    def record_stage(self, name: str, *, ended_at: float | None = None) -> None:
        current_at = self.last_mark_at if ended_at is None else ended_at
        self.durations[name] = max(0.0, current_at - self.last_mark_at)
        self.last_mark_at = current_at

    def record_duration(self, name: str, duration: float) -> None:
        self.durations[name] = max(0.0, duration)

    def record_skipped_stage(self, name: str) -> None:
        self.durations[name] = 0.0

    def finish(self, *, ended_at: float) -> dict[str, float]:
        self.durations["total"] = max(0.0, ended_at - self.started_at)
        return dict(self.durations)


@dataclass(slots=True)
class _TimingSummaryWindow:
    frame_count: int = 0
    stage_totals: dict[str, float] = field(default_factory=dict)
    stage_maximums: dict[str, float] = field(default_factory=dict)
    stage_values: dict[str, list[float]] = field(default_factory=dict)

    def add(self, stage_timings: dict[str, float]) -> None:
        self.frame_count += 1
        for stage_name, duration in stage_timings.items():
            self.stage_totals[stage_name] = self.stage_totals.get(stage_name, 0.0) + duration
            self.stage_maximums[stage_name] = max(
                self.stage_maximums.get(stage_name, 0.0),
                duration,
            )
            self.stage_values.setdefault(stage_name, []).append(duration)

    def percentile(self, stage_name: str, percentile: float) -> float | None:
        values = self.stage_values.get(stage_name)
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * (percentile / 100.0)
        lower_index = int(rank)
        upper_index = min(lower_index + 1, len(ordered) - 1)
        fraction = rank - lower_index
        lower = ordered[lower_index]
        upper = ordered[upper_index]
        return lower + ((upper - lower) * fraction)

    def reset(self) -> None:
        self.frame_count = 0
        self.stage_totals.clear()
        self.stage_maximums.clear()
        self.stage_values.clear()


def _format_stage_timings_ms(stage_timings: dict[str, float]) -> str:
    return ", ".join(
        f"{stage_name}={duration_ms:.1f}"
        for stage_name, duration_ms in stage_timings.items()
    )


def _duration_to_ms(duration: float | None) -> float | None:
    if duration is None:
        return None
    return duration * 1000.0


def _stage_percentiles_ms(
    timing_summary: _TimingSummaryWindow,
    percentile: float,
) -> dict[str, float]:
    percentiles: dict[str, float] = {}
    for stage_name in sorted(timing_summary.stage_values):
        value = timing_summary.percentile(stage_name, percentile)
        if value is not None:
            percentiles[stage_name] = value * 1000.0
    return percentiles


def _canonical_model_backend(model: ModelSettings) -> str:
    backend = model.capability_config.get("runtime_backend")
    if backend is not None:
        return str(backend)
    return "onnxruntime"


class InferenceEngine:
    def __init__(
        self,
        *,
        config: EngineConfig,
        frame_source: FrameSource,
        detector: Detector,
        tracker_factory: TrackerFactory,
        publisher: Publisher,
        tracking_store: TrackingStore,
        count_event_store: CountEventStoreProtocol | None = None,
        rule_engine: RuleEvaluator,
        event_client: EventSubscriber,
        stream_client: StreamClient,
        initial_registration: StreamRegistration | None = None,
        attribute_classifier: AttributeClassifier | None = None,
        anpr_processor: LineCrossingAnprProcessor | None = None,
        incident_capture: IncidentClipCaptureService | None = None,
        homography: Homography | None = None,
        privacy_filter: PrivacyFilter | None = None,
        preprocessor: Preprocessor | None = None,
        runtime: Any | None = None,
        runtime_policy: RuntimeExecutionPolicy | None = None,
        diagnostics_enabled: bool = False,
        timing_summary_interval_frames: int = 120,
    ) -> None:
        self.config = config
        self.frame_source = frame_source
        self.detector = detector
        self._tracker_factory = tracker_factory
        self.publisher = publisher
        self.tracking_store = tracking_store
        self._count_event_store = count_event_store or _NoopCountEventStore()
        self.rule_engine = rule_engine
        self.event_client = event_client
        self.stream_client = stream_client
        self._initial_registration = initial_registration
        self.attribute_classifier = attribute_classifier
        self.anpr_processor = anpr_processor
        self.incident_capture = incident_capture
        self.homography = homography or _build_homography(config.homography)
        self.preprocessor = preprocessor or _identity_preprocessor
        self._runtime = runtime
        self._runtime_policy = runtime_policy
        self._diagnostics_enabled = diagnostics_enabled
        self._timing_summary_interval_frames = max(0, timing_summary_interval_frames)
        self.privacy_filter = privacy_filter or PrivacyFilter(
            config=PrivacyConfig(
                blur_faces=config.privacy.blur_faces,
                blur_plates=config.privacy.blur_plates,
                method=config.privacy.method,
                strength=config.privacy.strength,
            )
        )
        vision_profile = SceneVisionProfile.model_validate(config.vision_profile)
        self.config.vision_profile = vision_profile
        self._resolved_vision_profile = resolve_scene_vision_profile(
            vision_profile.model_dump(mode="python"),
            has_homography=self.homography is not None,
        )
        self._state = _EngineState(
            active_classes=list(config.active_classes),
            runtime_vocabulary=list(config.model.runtime_vocabulary.terms),
            runtime_vocabulary_source=config.model.runtime_vocabulary.source,
            runtime_vocabulary_version=config.model.runtime_vocabulary.version,
            tracker_type=config.tracker.tracker_type,
            privacy=config.privacy,
            attribute_rules=list(config.attribute_rules),
            incident_rules=list(config.incident_rules),
            zones=list(config.zones),
            vision_profile=vision_profile,
            detection_regions=list(config.detection_regions),
        )
        self._tracker = self._tracker_factory(self._state.tracker_type)
        self._track_lifecycle = TrackLifecycleManager()
        self._candidate_quality_gate = CandidateQualityGate.from_profile_candidate_quality(
            self._resolved_vision_profile.candidate_quality,
        )
        self._count_event_processor = self._build_count_event_processor()
        self._zones = (
            Zones(_polygon_zone_definitions(self._state.zones))
            if self._state.zones
            else None
        )
        self._detection_region_policy = DetectionRegionPolicy(self._state.detection_regions)
        self._stream_registration: StreamRegistration | None = None
        self._track_history: dict[int, list[tuple[datetime, tuple[float, float]]]] = defaultdict(
            list
        )
        self._frame_attempt_index = 0
        self._last_stage_timings: dict[str, float] = {}
        self._timing_summary = _TimingSummaryWindow()
        self.runtime_selection = RuntimeSelection(
            selected_backend=_canonical_model_backend(config.model),
            artifact=None,
            fallback=True,
            fallback_reason="not_selected",
            profile_id=config.runtime_selection.profile_id,
            profile_name=config.runtime_selection.profile_name,
            profile_hash=config.runtime_selection.profile_hash,
            artifact_preference=config.runtime_selection.artifact_preference,
            fallback_allowed=config.runtime_selection.fallback_allowed,
        )
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        if self._initial_registration is not None:
            self._stream_registration = self._initial_registration
        else:
            self._stream_registration = await self.stream_client.register_stream(
                camera_id=self.config.camera_id,
                rtsp_url=self.config.camera.resolved_source_uri,
                profile=self.profile,
                stream_kind=self.config.stream.kind,
                privacy=self._state.privacy,
                target_fps=self.config.stream.fps,
                target_width=self.config.stream.width,
                target_height=self.config.stream.height,
            )
        await self.event_client.subscribe(
            f"cmd.camera.{self.config.camera_id}",
            self._handle_command_message,
        )
        if self.incident_capture is not None:
            await self.incident_capture.start(
                camera_id=self.config.camera_id,
                event_bus=self.event_client,
            )
        self._started = True

    async def close(self) -> None:
        if self.incident_capture is not None:
            await self.incident_capture.close()
        tracking_store_close = getattr(self.tracking_store, "close", None)
        if tracking_store_close is not None:
            close_result = tracking_store_close()
            if inspect.isawaitable(close_result):
                await close_result
        await self.publisher.close()
        self.frame_source.close()

    @property
    def profile(self) -> PublishProfile:
        if self.config.profile is not None:
            return self.config.profile
        return PublishProfile.CENTRAL_GPU

    @property
    def last_stage_timings(self) -> dict[str, float]:
        return dict(self._last_stage_timings)

    async def run_once(self, *, ts: datetime | None = None) -> TelemetryFrame:
        if not self._started:
            await self.start()
        loop = asyncio.get_running_loop()
        started_at = loop.time()
        self._frame_attempt_index += 1
        frame_attempt = self._frame_attempt_index
        stage_timer = _FrameStageTimer.start(started_at)
        current_ts = ts or datetime.now(tz=UTC)
        self._log_frame_diagnostic(
            "Worker frame capture starting",
            frame_attempt=frame_attempt,
            stage="capture",
        )
        frame = self.frame_source.next_frame()
        self._log_frame_diagnostic(
            "Worker frame capture completed",
            frame_attempt=frame_attempt,
            stage="capture",
            frame_shape=tuple(int(value) for value in frame.shape),
        )
        if self.incident_capture is not None:
            await self.incident_capture.record_frame(
                camera_id=self.config.camera_id,
                frame=frame,
                ts=current_ts,
            )
        stage_timer.record_stage("capture", ended_at=loop.time())
        self._record_frame_source_substage_timings(stage_timer)
        processed = self.preprocessor(frame.copy())
        stage_timer.record_stage("preprocess", ended_at=loop.time())
        visible_classes = self._visible_classes()
        detector_classes = self._detector_classes(visible_classes)
        self._log_frame_diagnostic(
            "Worker frame detect starting",
            frame_attempt=frame_attempt,
            stage="detect",
            active_classes=list(visible_classes),
            detector_classes=list(detector_classes),
        )
        detections = self.detector.detect(processed, detector_classes)
        self._log_frame_diagnostic(
            "Worker frame detect completed",
            frame_attempt=frame_attempt,
            stage="detect",
            detection_count=len(detections),
        )
        stage_timer.record_stage("detect", ended_at=loop.time())
        self._record_detector_substage_timings(stage_timer)
        filtered = self._filter_visible_detections(detections, visible_classes)
        filtered, region_decisions = self._detection_region_policy.filter_detections(filtered)
        self._record_detection_region_decisions(region_decisions)
        quality_filtered, candidate_decisions = self._candidate_quality_gate.filter_detections(
            filtered,
            existing_tracks=self._track_lifecycle.candidate_context_tracks(),
            frame_shape=processed.shape,
        )
        self._record_candidate_decisions(candidate_decisions)
        tracked = self._tracker.update(quality_filtered, frame=processed)
        stage_timer.record_stage("track", ended_at=loop.time())
        if (
            self._state.vision_profile.motion_metrics.speed_enabled
            and self.homography is not None
        ):
            tracked = self._apply_speed(tracked, ts=current_ts)
            self._record_motion_speed_samples(tracked)
        else:
            self._record_motion_speed_disabled()
            tracked = [detection.with_updates(speed_kph=None) for detection in tracked]
        stage_timer.record_stage("speed", ended_at=loop.time())
        tracked = self._apply_attributes(processed, tracked)
        stage_timer.record_stage("attributes", ended_at=loop.time())
        tracked = self._apply_zones(tracked)
        stable_tracks = self._track_lifecycle.update(
            detections=tracked,
            ts=current_ts,
            frame_shape=processed.shape,
        )
        stage_timer.record_stage("zones", ended_at=loop.time())
        count_events = self._count_event_processor.process(ts=current_ts, detections=tracked)
        rule_events = await self.rule_engine.evaluate(
            camera_id=self.config.camera_id,
            detections=tracked,
            ts=current_ts,
        )
        incident_events: list[IncidentTriggeredEvent] = []
        incident_events.extend(self._rule_events_to_incidents(rule_events))
        if self.anpr_processor is not None:
            incident_events.extend(
                self.anpr_processor.process(
                    camera_id=self.config.camera_id,
                    ts=current_ts,
                    detections=tracked,
                )
            )
        for incident_event in incident_events:
            incident_event = self._with_accountable_context(incident_event)
            await self.event_client.publish(
                f"incident.triggered.{self.config.camera_id}",
                incident_event,
                )
        stage_timer.record_stage("rules", ended_at=loop.time())
        stream_frame = self._build_stream_frame(
            frame,
            stable_tracks,
            privacy_detections=_privacy_detections_for_stream(
                raw_detections=detections,
                stable_tracks=stable_tracks,
            ),
        )
        stage_timer.record_stage("annotate", ended_at=loop.time())
        if (
            self._stream_registration is not None
            and self._stream_registration.mode is not StreamMode.PASSTHROUGH
        ):
            self._log_frame_diagnostic(
                "Worker frame publish_stream starting",
                frame_attempt=frame_attempt,
                stage="publish_stream",
                stream_mode=self._stream_registration.mode.value,
                path_name=self._stream_registration.path_name,
            )
            try:
                await self.stream_client.push_frame(
                    self._stream_registration,
                    stream_frame,
                    ts=current_ts,
                )
            except Exception:
                logger.exception(
                    "Failed to publish live video stream for camera %s on path %s; "
                    "continuing worker loop.",
                    self.config.camera_id,
                    self._stream_registration.path_name,
                )
            else:
                self._log_frame_diagnostic(
                    "Worker frame publish_stream completed",
                    frame_attempt=frame_attempt,
                    stage="publish_stream",
                    stream_mode=self._stream_registration.mode.value,
                    path_name=self._stream_registration.path_name,
                )
            stage_timer.record_stage("publish_stream", ended_at=loop.time())
        else:
            stage_timer.record_skipped_stage("publish_stream")
        telemetry = TelemetryFrame(
            camera_id=self.config.camera_id,
            ts=current_ts,
            profile=self.profile,
            stream_mode=(
                self._stream_registration.mode
                if self._stream_registration
                else StreamMode.PASSTHROUGH
            ),
            counts=_counts_by_lifecycle_tracks(stable_tracks),
            tracks=[_telemetry_track_from_lifecycle_track(track) for track in stable_tracks],
        )
        try:
            await self.publisher.publish(telemetry)
        except Exception:
            logger.exception(
                "Failed to publish live telemetry for camera %s; continuing worker loop.",
                self.config.camera_id,
            )
        stage_timer.record_stage("publish_telemetry", ended_at=loop.time())
        vocabulary_version = self._state.runtime_vocabulary_version
        vocabulary_hash = hash_vocabulary(self.runtime_vocabulary)
        await self.tracking_store.record(
            self.config.camera_id,
            current_ts,
            tracked,
            vocabulary_version=vocabulary_version,
            vocabulary_hash=vocabulary_hash,
        )
        stage_timer.record_stage("persist_tracking", ended_at=loop.time())
        try:
            await self._count_event_store.record(
                self.config.camera_id,
                count_events,
                vocabulary_version=vocabulary_version,
                vocabulary_hash=vocabulary_hash,
            )
        except Exception:
            logger.exception(
                "Failed to persist count events for camera %s",
                self.config.camera_id,
            )
        stage_timer.record_stage("persist_count_events", ended_at=loop.time())
        self._last_stage_timings = stage_timer.finish(ended_at=loop.time())
        for stage_name, duration in self._last_stage_timings.items():
            INFERENCE_STAGE_DURATION_SECONDS.labels(
                camera_id=str(self.config.camera_id),
                stage=stage_name,
            ).observe(duration)
        INFERENCE_FRAMES_PROCESSED_TOTAL.labels(
            camera_id=str(self.config.camera_id),
            profile=self.profile.value,
            stream_mode=telemetry.stream_mode.value,
        ).inc()
        INFERENCE_FRAME_DURATION_SECONDS.labels(camera_id=str(self.config.camera_id)).observe(
            self._last_stage_timings["total"]
        )
        self._record_timing_summary()
        self._log_frame_diagnostic(
            "Worker frame completed",
            frame_attempt=frame_attempt,
            stage="complete",
            stream_mode=telemetry.stream_mode.value,
            total_ms=round(self._last_stage_timings["total"] * 1000.0, 1),
        )
        return telemetry

    async def apply_command(self, command: CameraCommand) -> None:
        should_register_stream = False
        visible_classes_before = self._visible_class_key()
        if command.active_classes is not None:
            self._state.active_classes = list(command.active_classes)
        if command.runtime_vocabulary is not None:
            self._state.runtime_vocabulary = list(command.runtime_vocabulary)
            if command.runtime_vocabulary_source is not None:
                self._state.runtime_vocabulary_source = command.runtime_vocabulary_source
            if command.runtime_vocabulary_version is not None:
                self._state.runtime_vocabulary_version = command.runtime_vocabulary_version
            if self.config.model.capability is DetectorCapability.OPEN_VOCAB:
                self.config.model.runtime_vocabulary = (
                    self.config.model.runtime_vocabulary.model_copy(
                        update={
                            "terms": list(self._state.runtime_vocabulary),
                            "source": self._state.runtime_vocabulary_source,
                            "version": self._state.runtime_vocabulary_version,
                        }
                    )
                )
            if (
                self.config.model.capability is DetectorCapability.OPEN_VOCAB
                and self.runtime_selection.artifact is not None
            ):
                self.runtime_selection = RuntimeSelection(
                    selected_backend=_canonical_model_backend(self.config.model),
                    artifact=None,
                    fallback=True,
                    fallback_reason="vocabulary_changed",
                    profile_id=self.runtime_selection.profile_id,
                    profile_name=self.runtime_selection.profile_name,
                    profile_hash=self.runtime_selection.profile_hash,
                    artifact_preference=self.runtime_selection.artifact_preference,
                    fallback_allowed=self.runtime_selection.fallback_allowed,
                )
                if self._runtime is not None and self._runtime_policy is not None:
                    self.detector = _build_detector_with_selection(
                        model=self.config.model,
                        runtime=self._runtime,
                        runtime_policy=self._runtime_policy,
                        runtime_selection=self.runtime_selection,
                    )
            self.detector.update_runtime_vocabulary(self._state.runtime_vocabulary)
            if self.config.model.capability is DetectorCapability.OPEN_VOCAB:
                runtime_state: dict[str, object] = {}
                describe_runtime_state = getattr(self.detector, "describe_runtime_state", None)
                if callable(describe_runtime_state):
                    runtime_state = dict(describe_runtime_state())
                logger.info(
                    "Updated open-vocab runtime vocabulary for camera %s "
                    "runtime_backend=%s vocabulary_terms=%s vocabulary_version=%s",
                    self.config.camera_id,
                    runtime_state.get("runtime_backend", "unknown"),
                    len(self._state.runtime_vocabulary),
                    self._state.runtime_vocabulary_version,
                )
                if self.runtime_selection.fallback_reason == "vocabulary_changed":
                    logger.info(
                        "Open-vocab compiled artifact fallback for camera %s "
                        "selected_backend=%s fallback_reason=vocabulary_changed",
                        self.config.camera_id,
                        self.runtime_selection.selected_backend,
                    )
        if command.tracker_type is not None and command.tracker_type != self._state.tracker_type:
            self._state.tracker_type = command.tracker_type
            self._tracker = self._tracker_factory(command.tracker_type)
            self._track_lifecycle.reset()
            self._count_event_processor = self._build_count_event_processor()
        elif visible_classes_before != self._visible_class_key():
            self._track_lifecycle.reset()
        if command.stream is not None and command.stream != self.config.stream:
            self.config.stream = command.stream
            should_register_stream = True
        if command.privacy is not None and command.privacy != self._state.privacy:
            self._state.privacy = command.privacy
            self.privacy_filter = PrivacyFilter(
                config=PrivacyConfig(
                    blur_faces=command.privacy.blur_faces,
                    blur_plates=command.privacy.blur_plates,
                    method=command.privacy.method,
                    strength=command.privacy.strength,
                )
            )
            should_register_stream = True
        if self._started and should_register_stream:
            self._stream_registration = await self.stream_client.register_stream(
                camera_id=self.config.camera_id,
                rtsp_url=self.config.camera.resolved_source_uri,
                profile=self.profile,
                stream_kind=self.config.stream.kind,
                privacy=self._state.privacy,
                target_fps=self.config.stream.fps,
                target_width=self.config.stream.width,
                target_height=self.config.stream.height,
            )
        if command.attribute_rules is not None:
            self._state.attribute_rules = list(command.attribute_rules)
        if command.incident_rules is not None:
            self._state.incident_rules = list(command.incident_rules)
            self.config.incident_rules = list(command.incident_rules)
            replace_rules = getattr(self.rule_engine, "replace_rules", None)
            if callable(replace_rules):
                replace_rules(_rule_definitions_from_worker_rules(command.incident_rules))
        if command.zones is not None:
            self._state.zones = list(command.zones)
            self._count_event_processor = self._build_count_event_processor()
            self._zones = (
                Zones(_polygon_zone_definitions(self._state.zones)) if self._state.zones else None
            )
        if command.detection_regions is not None:
            self._state.detection_regions = list(command.detection_regions)
            self.config.detection_regions = list(command.detection_regions)
            self._detection_region_policy = DetectionRegionPolicy(self._state.detection_regions)
            self._track_lifecycle.reset()
        if "homography" in command.model_fields_set:
            self.config.homography = (
                dict(command.homography) if command.homography is not None else None
            )
            self.homography = _build_homography(self.config.homography)
            self._track_history.clear()
        if command.vision_profile is not None:
            self._state.vision_profile = command.vision_profile
            self.config.vision_profile = command.vision_profile
            self._resolved_vision_profile = resolve_scene_vision_profile(
                command.vision_profile.model_dump(mode="python"),
                has_homography=self.homography is not None,
            )
            self._candidate_quality_gate = CandidateQualityGate.from_profile_candidate_quality(
                self._resolved_vision_profile.candidate_quality,
            )

    @property
    def active_classes(self) -> list[str]:
        if self._state.active_classes:
            return list(self._state.active_classes)
        return list(self.config.model.classes)

    @property
    def runtime_vocabulary(self) -> list[str]:
        if self._state.runtime_vocabulary:
            return list(self._state.runtime_vocabulary)
        return list(self.config.model.classes)

    def _visible_classes(self) -> list[str]:
        if self.config.model.capability is DetectorCapability.OPEN_VOCAB:
            if self._state.active_classes:
                return list(self._state.active_classes)
            return self.runtime_vocabulary
        return self.active_classes

    def _detector_classes(self, visible_classes: list[str]) -> list[str]:
        detector_classes = list(visible_classes)
        if self._state.privacy.blur_faces:
            for class_name in self._face_privacy_classes():
                if class_name not in detector_classes:
                    detector_classes.append(class_name)
        return detector_classes

    def _visible_class_key(self) -> tuple[str, ...]:
        return tuple(self._visible_classes())

    def _record_detector_substage_timings(self, stage_timer: _FrameStageTimer) -> None:
        last_stage_timings = getattr(self.detector, "last_stage_timings", None)
        if not callable(last_stage_timings):
            return
        for stage_name, duration in last_stage_timings().items():
            if isinstance(stage_name, str) and isinstance(duration, int | float):
                stage_timer.record_duration(f"detect_{stage_name}", float(duration))

    def _record_frame_source_substage_timings(self, stage_timer: _FrameStageTimer) -> None:
        last_stage_timings = getattr(self.frame_source, "last_stage_timings", None)
        if not callable(last_stage_timings):
            return
        for stage_name, duration in last_stage_timings().items():
            if isinstance(stage_name, str) and isinstance(duration, int | float):
                stage_timer.record_duration(f"capture_{stage_name}", float(duration))

    def _face_privacy_classes(self) -> list[str]:
        if self.config.model.capability is DetectorCapability.OPEN_VOCAB:
            return ["person"]
        class_by_lower_name = {
            class_name.strip().lower(): class_name for class_name in self.runtime_vocabulary
        }
        return [
            class_by_lower_name[class_name]
            for class_name in _FACE_PRIVACY_DETECTION_CLASSES
            if class_name in class_by_lower_name
        ]

    @staticmethod
    def _filter_visible_detections(
        detections: list[Detection],
        visible_classes: list[str],
    ) -> list[Detection]:
        allowed = set(visible_classes)
        return [detection for detection in detections if detection.class_name in allowed]

    def _record_detection_region_decisions(
        self,
        decisions: list[DetectionRegionDecision],
    ) -> None:
        camera_id = str(self.config.camera_id)
        for decision in decisions:
            if decision.allowed:
                continue
            DETECTION_REGION_FILTERED_TOTAL.labels(
                camera_id=camera_id,
                class_name=self._metric_class_name(decision.detection.class_name),
                reason=decision.reason,
                mode=decision.mode,
            ).inc()

    def _record_candidate_decisions(self, decisions: list[CandidateDecision]) -> None:
        camera_id = str(self.config.camera_id)
        for decision in decisions:
            metric = (
                CANDIDATE_PASSED_TOTAL
                if decision.accepted
                else CANDIDATE_REJECTED_TOTAL
            )
            metric.labels(
                camera_id=camera_id,
                class_name=self._metric_class_name(decision.detection.class_name),
                reason=decision.reason,
            ).inc()

    def _record_motion_speed_samples(self, detections: list[Detection]) -> None:
        camera_id = str(self.config.camera_id)
        for detection in detections:
            if detection.speed_kph is None:
                continue
            MOTION_SPEED_SAMPLES_TOTAL.labels(
                camera_id=camera_id,
                class_name=self._metric_class_name(detection.class_name),
            ).inc()

    def _metric_class_name(self, class_name: str) -> str:
        if self.config.model.capability is DetectorCapability.OPEN_VOCAB:
            return "open_vocab"

        normalized = class_name.strip().lower()
        if not normalized:
            return "other"

        model_classes = {
            configured_class.strip().lower()
            for configured_class in self.config.model.classes
            if configured_class.strip()
        }
        if self.config.secondary_model is not None:
            model_classes.update(
                configured_class.strip().lower()
                for configured_class in self.config.secondary_model.classes
                if configured_class.strip()
            )
        return normalized if normalized in model_classes else "other"

    def _record_motion_speed_disabled(self) -> None:
        reason = (
            "profile_disabled"
            if not self._state.vision_profile.motion_metrics.speed_enabled
            else "missing_homography"
        )
        MOTION_SPEED_DISABLED_TOTAL.labels(
            camera_id=str(self.config.camera_id),
            mode=self.config.mode.value,
            reason=reason,
        ).inc()

    async def _handle_command_message(self, message: Any) -> None:
        if isinstance(message, CameraCommand):
            command = message
        elif isinstance(message, EventMessage):
            command = CameraCommand.model_validate_json(message.data)
        elif isinstance(message, dict):
            command = CameraCommand.model_validate(message)
        else:
            payload = getattr(message, "data", None)
            if isinstance(payload, str):
                command = CameraCommand.model_validate_json(payload)
            else:
                command = CameraCommand.model_validate(payload)
        await self.apply_command(command)

    def _apply_attributes(self, frame: Frame, detections: list[Detection]) -> list[Detection]:
        if self.attribute_classifier is None or not detections:
            return detections
        attributes = self.attribute_classifier.classify(frame, detections)
        return [
            detection.with_updates(attributes=attributes[index])
            for index, detection in enumerate(detections)
        ]

    def _apply_zones(self, detections: list[Detection]) -> list[Detection]:
        if self._zones is None:
            return detections
        enriched: list[Detection] = []
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            zone_id = self._zones.zone_for_point((x1 + x2) / 2.0, y2)
            enriched.append(detection.with_updates(zone_id=zone_id))
        return enriched

    def _apply_speed(self, detections: list[Detection], *, ts: datetime) -> list[Detection]:
        if not self._state.vision_profile.motion_metrics.speed_enabled:
            return [detection.with_updates(speed_kph=None) for detection in detections]
        if self.homography is None:
            return [detection.with_updates(speed_kph=None) for detection in detections]
        enriched: list[Detection] = []
        for detection in detections:
            if detection.track_id is None:
                enriched.append(detection)
                continue
            x1, y1, x2, y2 = detection.bbox
            bottom_center = ((x1 + x2) / 2.0, y2)
            history = self._track_history[detection.track_id]
            history.append((ts, bottom_center))
            if len(history) > 16:
                del history[:-16]
            speed_kph = (
                self.homography.speed_kph_for_timed_points(history)
                if len(history) >= 2
                else None
            )
            enriched.append(detection.with_updates(speed_kph=speed_kph))
        return enriched

    def _build_count_event_processor(self) -> CountEventProcessor:
        return CountEventProcessor(self._state.zones)

    def _build_stream_frame(
        self,
        frame: Frame,
        tracks: list[LifecycleTrack],
        *,
        privacy_detections: list[Detection] | None = None,
    ) -> Frame:
        if (
            self._stream_registration is None
            or self._stream_registration.mode is StreamMode.PASSTHROUGH
        ):
            return frame
        stream_frame = frame.copy()
        if self._state.privacy.requires_filtering:
            stream_frame = self.privacy_filter.apply(
                stream_frame,
                detections=(
                    privacy_detections
                    if privacy_detections is not None
                    else [track.detection for track in tracks]
                ),
            )
        if (
            self._stream_registration.mode is StreamMode.ANNOTATED_WHIP
            and self.config.stream.profile_id != "native"
        ):
            self._draw_annotations(stream_frame, tracks)
        return stream_frame

    def _draw_annotations(self, frame: Frame, tracks: list[LifecycleTrack]) -> None:
        for track in tracks:
            detection = track.detection
            x1, y1, x2, y2 = (int(value) for value in detection.bbox)
            color = _annotation_color_for_track(track)
            if track.state == "coasting":
                _draw_dashed_rectangle(
                    frame,
                    top_left=(x1, y1),
                    bottom_right=(x2, y2),
                    color=color,
                    thickness=1,
                )
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = _annotation_label_for_track(track)
            cv2.putText(
                frame,
                label,
                (x1, max(18, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )

    def _rule_events_to_incidents(
        self,
        events: Iterable[RuleEventRecord],
    ) -> list[IncidentTriggeredEvent]:
        incidents: list[IncidentTriggeredEvent] = []
        for event in events:
            action = event.action
            if action is None:
                continue
            action_value = action.value if hasattr(action, "value") else str(action)
            if action is RuleAction.COUNT or action_value == RuleAction.COUNT.value:
                continue
            incident_type = event.incident_type or action_value
            trigger_rule = TriggerRuleSummary(
                id=event.rule_id,
                name=event.name,
                incident_type=incident_type,
                severity=IncidentRuleSeverity(
                    event.severity or IncidentRuleSeverity.WARNING.value
                ),
                action=RuleAction(action_value),
                cooldown_seconds=event.cooldown_seconds,
                predicate=WorkerIncidentRulePredicate.model_validate(event.predicate),
                rule_hash=event.rule_hash,
            )
            incidents.append(
                IncidentTriggeredEvent(
                    camera_id=self.config.camera_id,
                    ts=event.ts,
                    type=f"rule.{incident_type}",
                    payload={
                        "name": trigger_rule.name,
                        "action": action_value,
                        "trigger_rule": trigger_rule.model_dump(mode="json"),
                        "detection": getattr(event, "detection", {}),
                    },
                )
                )
        return incidents

    def _with_accountable_context(
        self,
        event: IncidentTriggeredEvent,
    ) -> IncidentTriggeredEvent:
        return event.model_copy(
            update={
                "scene_contract_hash": event.scene_contract_hash
                or self.config.scene_contract_hash,
                "privacy_manifest_hash": event.privacy_manifest_hash
                or self.config.privacy_manifest_hash,
                "runtime_passport_snapshot_id": event.runtime_passport_snapshot_id
                or self.config.runtime_passport_snapshot_id,
                "runtime_passport_hash": event.runtime_passport_hash
                or self.config.runtime_passport_hash,
                "recording_policy": event.recording_policy or self.config.recording_policy,
            }
        )

    def _record_timing_summary(self) -> None:
        if self._timing_summary_interval_frames <= 0:
            return

        self._timing_summary.add(self._last_stage_timings)
        if self._timing_summary.frame_count < self._timing_summary_interval_frames:
            return

        frame_count = self._timing_summary.frame_count
        stage_avg_ms = {
            stage_name: (total / frame_count) * 1000.0
            for stage_name, total in sorted(self._timing_summary.stage_totals.items())
        }
        stage_max_ms = {
            stage_name: duration * 1000.0
            for stage_name, duration in sorted(self._timing_summary.stage_maximums.items())
        }
        stage_p95_ms = _stage_percentiles_ms(self._timing_summary, 95.0)
        stage_p99_ms = _stage_percentiles_ms(self._timing_summary, 99.0)
        capture_wait_p95_ms = _duration_to_ms(
            self._timing_summary.percentile("capture_wait", 95.0)
        )
        capture_wait_p99_ms = _duration_to_ms(
            self._timing_summary.percentile("capture_wait", 99.0)
        )
        extra = {
            "camera_id": str(self.config.camera_id),
            "frame_count": frame_count,
            "stage_avg_ms": stage_avg_ms,
            "stage_max_ms": stage_max_ms,
            "stage_p95_ms": stage_p95_ms,
            "stage_p99_ms": stage_p99_ms,
            "capture_wait_p95_ms": capture_wait_p95_ms,
            "capture_wait_p99_ms": capture_wait_p99_ms,
        }
        logger.info(
            "Inference stage timing summary "
            "camera_id=%s frame_count=%s stage_avg_ms={%s} stage_max_ms={%s} "
            "stage_p95_ms={%s} stage_p99_ms={%s}",
            str(self.config.camera_id),
            frame_count,
            _format_stage_timings_ms(stage_avg_ms),
            _format_stage_timings_ms(stage_max_ms),
            _format_stage_timings_ms(stage_p95_ms),
            _format_stage_timings_ms(stage_p99_ms),
            extra=extra,
        )
        capture_wait_max_s = self._timing_summary.stage_maximums.get("capture_wait")
        if (
            capture_wait_max_s is not None
            and capture_wait_max_s > _CAPTURE_WAIT_SPIKE_WARNING_THRESHOLD_S
        ):
            capture_wait_max_ms = capture_wait_max_s * 1000.0
            capture_wait_threshold_ms = _CAPTURE_WAIT_SPIKE_WARNING_THRESHOLD_S * 1000.0
            logger.warning(
                "Capture wait spike observed "
                "camera_id=%s frame_count=%s capture_wait_max_ms=%.1f "
                "capture_wait_p95_ms=%.1f capture_wait_p99_ms=%.1f "
                "threshold_ms=%.1f",
                str(self.config.camera_id),
                frame_count,
                capture_wait_max_ms,
                capture_wait_p95_ms or 0.0,
                capture_wait_p99_ms or 0.0,
                capture_wait_threshold_ms,
                extra={
                    "camera_id": str(self.config.camera_id),
                    "frame_count": frame_count,
                    "capture_wait_max_ms": capture_wait_max_ms,
                    "capture_wait_p95_ms": capture_wait_p95_ms,
                    "capture_wait_p99_ms": capture_wait_p99_ms,
                    "capture_wait_threshold_ms": capture_wait_threshold_ms,
                },
            )
        self._timing_summary.reset()

    def _log_frame_diagnostic(
        self,
        message: str,
        *,
        frame_attempt: int,
        stage: str,
        **extra: object,
    ) -> None:
        if not self._diagnostics_enabled:
            return

        logger.info(
            "%s camera_id=%s frame_attempt=%s stage=%s details=%s",
            message,
            str(self.config.camera_id),
            frame_attempt,
            stage,
            extra,
            extra={
                "camera_id": str(self.config.camera_id),
                "frame_attempt": frame_attempt,
                "stage": stage,
                **extra,
            },
        )


async def load_engine_config(
    camera_id: UUID,
    *,
    settings: Settings,
    http_client: httpx.AsyncClient | None = None,
) -> EngineConfig:
    headers = _worker_api_headers(settings)
    try:
        if http_client is not None:
            response = await http_client.get(
                f"/api/v1/cameras/{camera_id}/worker-config",
                headers=headers or None,
            )
            response.raise_for_status()
            return EngineConfig.model_validate(response.json())

        async with httpx.AsyncClient(base_url=settings.api_base_url) as client:
            response = await client.get(
                f"/api/v1/cameras/{camera_id}/worker-config",
                headers=headers or None,
            )
            response.raise_for_status()
            return EngineConfig.model_validate(response.json())
    except httpx.ConnectError as exc:
        raise RuntimeError(
            "Unable to connect to the Vezor API while loading worker config "
            f"for camera {camera_id}. ARGUS_API_BASE_URL is {settings.api_base_url!r}; "
            "set it to the master API URL reachable from this worker."
        ) from exc


async def build_runtime_engine(
    config: EngineConfig,
    *,
    settings: Settings,
    events_client: NatsJetStreamClient,
    tracking_store: TrackingStore | None = None,
    count_event_store: CountEventStoreProtocol | None = None,
    rule_engine: RuleEvaluator | None = None,
    rule_event_store: RuleStore | None = None,
    incident_capture: IncidentClipCaptureService | None = None,
) -> InferenceEngine:
    token_issuer = MediaMTXTokenIssuer.from_settings(settings)
    stream_client = MediaMTXClient(
        api_base_url=settings.mediamtx_api_url,
        rtsp_base_url=settings.mediamtx_rtsp_base_url,
        whip_base_url=settings.mediamtx_whip_base_url,
        username=settings.mediamtx_username,
        password=(
            settings.mediamtx_password.get_secret_value()
            if settings.mediamtx_password is not None
            else None
        ),
        publish_token_factory=lambda camera_id, path_name: token_issuer.issue_publish_token(
            subject=f"worker-{camera_id}",
            camera_id=camera_id,
            path_name=path_name,
        ),
        read_token_factory=lambda camera_id, path_name: token_issuer.issue_internal_read_token(
            camera_id=camera_id,
            path_name=path_name,
            ttl_seconds=settings.mediamtx_jwt_worker_ttl_seconds,
        ),
    )

    profile = config.profile if config.profile is not None else PublishProfile.CENTRAL_GPU
    registration = await stream_client.register_stream(
        camera_id=config.camera_id,
        rtsp_url=config.camera.resolved_source_uri,
        profile=profile,
        stream_kind=config.stream.kind,
        privacy=config.privacy,
        target_fps=config.stream.fps,
        target_width=config.stream.width,
        target_height=config.stream.height,
    )
    source_uri = config.camera.resolved_source_uri
    source_uri_factory = None
    source_label = (
        "camera RTSP"
        if config.camera.source_kind is CameraSourceKind.RTSP
        else "camera source"
    )
    if registration.mode is StreamMode.PASSTHROUGH:
        logger.info(
            (
                "Worker ingesting directly from %s while browser delivery "
                "uses MediaMTX passthrough at %s (camera_id=%s)"
            ),
            source_label,
            redact_url_secrets(registration.read_path),
            config.camera_id,
        )
    else:
        logger.info(
            (
                "Worker ingesting directly from %s for processed stream "
                "(stream_mode=%s, output_path=%s, camera_id=%s)"
            ),
            source_label,
            registration.mode.value,
            registration.path_name,
            config.camera_id,
        )

    frame_source = create_camera_source(
        CameraSourceConfig(
            source_uri=source_uri,
            source_uri_factory=source_uri_factory,
            frame_skip=config.camera.frame_skip,
            fps_cap=config.camera.fps_cap,
        )
    )
    runtime = import_onnxruntime()
    runtime_policy = resolve_execution_policy(
        runtime,
        execution_provider_override=settings.inference_execution_provider_override,
        execution_profile_override=settings.inference_execution_profile_override,
        inter_op_threads=settings.inference_session_inter_op_threads,
        intra_op_threads=settings.inference_session_intra_op_threads,
    )
    logger.info(
        "Resolved inference runtime policy "
        "profile=%s system=%s machine=%s cpu_vendor=%s "
        "detection_provider=%s attribute_provider=%s "
        "provider_override=%s profile_override=%s available_providers=%s",
        runtime_policy.profile.value,
        runtime_policy.host.system,
        runtime_policy.host.machine,
        runtime_policy.host.cpu_vendor.value,
        runtime_policy.provider,
        runtime_policy.provider if config.secondary_model is not None else "<disabled>",
        runtime_policy.provider_overridden,
        runtime_policy.profile_overridden,
        list(runtime_policy.available_providers),
    )
    runtime_selection = select_runtime_artifact(
        model=config.model,
        host_profile=runtime_policy.profile.value,
        artifacts=config.runtime_artifacts,
        runtime_vocabulary_hash=(
            hash_vocabulary(config.model.runtime_vocabulary.terms)
            if config.model.capability is DetectorCapability.OPEN_VOCAB
            else None
        ),
        runtime_profile=config.runtime_selection,
    )
    logger.info(
        "Selected inference runtime camera_id=%s model=%s selected_backend=%s "
        "artifact_id=%s host_profile=%s fallback=%s fallback_reason=%s "
        "profile_id=%s profile_hash=%s artifact_preference=%s fallback_allowed=%s",
        config.camera_id,
        config.model.name,
        runtime_selection.selected_backend,
        runtime_selection.artifact.id if runtime_selection.artifact is not None else None,
        runtime_policy.profile.value,
        runtime_selection.fallback,
        runtime_selection.fallback_reason,
        runtime_selection.profile_id,
        runtime_selection.profile_hash,
        runtime_selection.artifact_preference,
        runtime_selection.fallback_allowed,
    )
    detector = _build_detector_with_selection(
        model=config.model,
        runtime=runtime,
        runtime_policy=runtime_policy,
        runtime_selection=runtime_selection,
    )

    def tracker_factory(tracker_type: TrackerType) -> Tracker:
        tracker_config = TrackerConfig(
            tracker_type=tracker_type,
            frame_rate=config.tracker.frame_rate,
        )
        return create_tracker(tracker_config)

    if config.secondary_model is not None:
        attribute_classifier = AttributeClassifier(
            AttributeModelConfig(
                name=config.secondary_model.name,
                path=config.secondary_model.path,
                classes=config.secondary_model.classes,
                input_shape=config.secondary_model.input_shape,
                target_classes=set(config.active_classes or config.model.classes),
            ),
            runtime=runtime,
            runtime_policy=runtime_policy,
        )
    else:
        attribute_classifier = None

    line_definitions = [
        zone
        for zone in config.zones
        if str(zone.get("type", "")).lower() == "line"
    ]
    anpr_processor = (
        LineCrossingAnprProcessor(line_definitions=line_definitions)
        if line_definitions
        else None
    )

    primary_publisher = NatsPublisher(
        events_client,
        subject_prefix=config.publish.subject_prefix,
    )
    publisher: Publisher
    if config.publish.http_fallback_url is not None:
        publisher = ResilientPublisher(
            primary=primary_publisher,
            fallback=HttpPublisher(url=config.publish.http_fallback_url),
        )
    else:
        publisher = primary_publisher
    publisher = BufferedTelemetryPublisher(
        publisher,
        max_queue_size=settings.telemetry_publish_queue_size,
        shutdown_timeout_seconds=settings.telemetry_publish_shutdown_timeout_seconds,
    )
    resolved_rule_engine: RuleEvaluator = rule_engine or RuleEngine(
        rules=_rule_definitions_from_worker_rules(config.incident_rules),
        publisher=events_client,
        store=rule_event_store or _NoopRuleEventStore(),
    )

    engine = InferenceEngine(
        config=config,
        frame_source=frame_source,
        detector=detector,
        tracker_factory=tracker_factory,
        publisher=publisher,
        tracking_store=BufferedTrackingStore(
            tracking_store or _NoopTrackingStore(),
            max_queue_size=settings.tracking_persistence_queue_size,
            shutdown_timeout_seconds=settings.tracking_persistence_shutdown_timeout_seconds,
            max_batch_size=settings.tracking_persistence_batch_size,
            batch_flush_interval_seconds=(
                settings.tracking_persistence_batch_flush_interval_seconds
            ),
        ),
        count_event_store=count_event_store or _NoopCountEventStore(),
        rule_engine=resolved_rule_engine,
        event_client=events_client,
        stream_client=stream_client,
        initial_registration=registration,
        attribute_classifier=attribute_classifier,
        anpr_processor=anpr_processor,
        incident_capture=incident_capture,
        diagnostics_enabled=settings.worker_diagnostics_enabled,
        runtime=runtime,
        runtime_policy=runtime_policy,
    )
    engine.runtime_selection = runtime_selection
    return engine


async def run_engine_for_camera(camera_id: UUID, *, settings: Settings | None = None) -> None:
    resolved_settings = settings or Settings()
    if resolved_settings.enable_worker_metrics_server:
        start_http_server(resolved_settings.worker_metrics_port)
    events_client = NatsJetStreamClient(resolved_settings)
    db_manager = DatabaseManager(resolved_settings)
    await events_client.connect()
    config = await load_engine_config(camera_id, settings=resolved_settings)
    resolved_profile = probe_publish_profile(
        explicit_override=resolved_settings.publish_profile,
        machine=None,
        command_runner=default_profile_probe,
    )
    config = config.model_copy(update={"profile": resolved_profile})
    engine = await build_runtime_engine(
        config,
        settings=resolved_settings,
        events_client=events_client,
        tracking_store=TrackingEventStore(db_manager.session_factory),
        count_event_store=CountEventStore(db_manager.session_factory),
        rule_event_store=SQLRuleEventStore(db_manager.session_factory),
        incident_capture=IncidentClipCaptureService(
            object_store=build_evidence_store(resolved_settings),
            storage_resolver=ResolvedEvidenceStorageResolver(
                settings=resolved_settings,
                evidence_storage=config.evidence_storage,
            ),
            repository=SQLIncidentRepository(db_manager.session_factory),
            recording_policy=config.recording_policy,
            privacy_policy=config.privacy_policy,
        ),
    )
    await engine.start()
    try:
        while True:
            await engine.run_once()
            await asyncio.sleep(0)
    finally:
        await engine.close()
        await events_client.close()
        await db_manager.dispose()


def _build_homography(config: dict[str, Any] | None) -> Homography | None:
    if not config:
        return None
    src_points = config.get("src_points")
    dst_points = config.get("dst_points")
    ref_distance_m = config.get("ref_distance_m")
    if src_points is None or dst_points is None or ref_distance_m is None:
        return None
    return Homography(
        src_points=src_points,
        dst_points=dst_points,
        ref_distance_m=float(ref_distance_m),
    )


def _rule_definitions_from_worker_rules(
    rules: list[WorkerIncidentRule],
) -> list[RuleDefinition]:
    definitions: list[RuleDefinition] = []
    for rule in rules:
        zone_ids = list(rule.predicate.zone_ids)
        definitions.append(
            RuleDefinition(
                id=rule.id,
                camera_id=rule.camera_id,
                name=rule.name,
                enabled=rule.enabled,
                incident_type=rule.incident_type,
                severity=rule.severity.value,
                predicate=rule.predicate.model_dump(mode="python"),
                action=rule.action,
                cooldown_seconds=rule.cooldown_seconds,
                zone_id=zone_ids[0] if len(zone_ids) == 1 else None,
                webhook_url=rule.webhook_url,
                rule_hash=rule.rule_hash,
            )
        )
    return definitions


def _annotation_color_for_track(track: LifecycleTrack) -> tuple[int, int, int]:
    class_name = track.detection.class_name.strip().lower()
    if track.state == "coasting":
        return _COASTING_ANNOTATION_COLORS_BGR.get(
            class_name,
            _DEFAULT_COASTING_ANNOTATION_COLOR_BGR,
        )
    return _ACTIVE_ANNOTATION_COLORS_BGR.get(
        class_name,
        _DEFAULT_ACTIVE_ANNOTATION_COLOR_BGR,
    )


def _annotation_label_for_track(track: LifecycleTrack) -> str:
    class_name = track.detection.class_name
    if track.state != "coasting":
        return class_name
    age_seconds = max(0.0, track.last_seen_age_ms / 1000.0)
    return f"{class_name} held {age_seconds:.1f}s"


def _draw_dashed_rectangle(
    frame: Frame,
    *,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    x1, y1 = top_left
    x2, y2 = bottom_right
    _draw_dashed_line(frame, (x1, y1), (x2, y1), color=color, thickness=thickness)
    _draw_dashed_line(frame, (x2, y1), (x2, y2), color=color, thickness=thickness)
    _draw_dashed_line(frame, (x2, y2), (x1, y2), color=color, thickness=thickness)
    _draw_dashed_line(frame, (x1, y2), (x1, y1), color=color, thickness=thickness)


def _draw_dashed_line(
    frame: Frame,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    length = max(abs(dx), abs(dy))
    if length <= 0:
        return
    for offset in range(0, length, _DASHED_BOX_SEGMENT_PX * 2):
        segment_end = min(offset + _DASHED_BOX_SEGMENT_PX, length)
        start_ratio = offset / length
        end_ratio = segment_end / length
        segment_start = (
            round(x1 + dx * start_ratio),
            round(y1 + dy * start_ratio),
        )
        segment_stop = (
            round(x1 + dx * end_ratio),
            round(y1 + dy * end_ratio),
        )
        cv2.line(
            frame,
            segment_start,
            segment_stop,
            color,
            thickness,
            cv2.LINE_AA,
        )


def _counts_by_lifecycle_tracks(tracks: list[LifecycleTrack]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for track in tracks:
        class_name = track.detection.class_name
        counts[class_name] = counts.get(class_name, 0) + 1
    return counts


def _privacy_detections_for_stream(
    *,
    raw_detections: list[Detection],
    stable_tracks: list[LifecycleTrack],
) -> list[Detection]:
    return [*raw_detections, *(track.detection for track in stable_tracks)]


def _telemetry_track_from_lifecycle_track(track: LifecycleTrack) -> TelemetryTrack:
    detection = track.detection
    x1, y1, x2, y2 = detection.bbox
    track_state = track.state if track.state in ("active", "coasting") else None
    return TelemetryTrack(
        class_name=detection.class_name,
        confidence=detection.confidence,
        bbox={
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
        },
        track_id=track.stable_track_id,
        stable_track_id=track.stable_track_id,
        track_state=track_state,
        last_seen_age_ms=track.last_seen_age_ms,
        source_track_id=track.source_track_id,
        speed_kph=detection.speed_kph,
        direction_deg=detection.direction_deg,
        zone_id=detection.zone_id,
        attributes=detection.attributes,
    )


class _NoopTrackingStore:
    async def record(
        self,
        camera_id: UUID,
        ts: datetime,
        detections: list[Detection],
        *,
        vocabulary_version: int | None = None,
        vocabulary_hash: str | None = None,
    ) -> None:
        return None


class _NoopRuleEngine:
    async def evaluate(
        self,
        *,
        camera_id: UUID,
        detections: list[Detection],
        ts: datetime,
    ) -> list[RuleEventRecord]:
        return []


class _NoopRuleEventStore:
    async def record(self, event: BaseModel) -> None:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an Argus inference worker for a camera.")
    parser.add_argument("--camera-id", required=True, type=UUID)
    args = parser.parse_args(argv)
    settings = Settings()
    configure_logging(settings)
    asyncio.run(run_engine_for_camera(args.camera_id, settings=settings))
    return 0


def _identity_preprocessor(frame: Frame) -> Frame:
    return frame


def _worker_api_headers(settings: Settings) -> dict[str, str]:
    if settings.api_bearer_token is None:
        return {}
    return {"Authorization": f"Bearer {settings.api_bearer_token.get_secret_value()}"}


def _polygon_zone_definitions(zone_definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        zone
        for zone in zone_definitions
        if str(zone.get("type", "polygon")).lower() != "line" and "polygon" in zone
    ]


class _NoopCountEventStore:
    async def record(
        self,
        camera_id: UUID,
        events: list[CountEventRecord],
        *,
        vocabulary_version: int | None = None,
        vocabulary_hash: str | None = None,
    ) -> None:
        return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
