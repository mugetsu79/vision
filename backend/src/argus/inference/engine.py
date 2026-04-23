from __future__ import annotations

import argparse
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import cv2
import httpx
import numpy as np
from numpy.typing import NDArray
from prometheus_client import start_http_server
from pydantic import BaseModel, ConfigDict, Field

from argus.core.config import Settings
from argus.core.db import DatabaseManager, TrackingEventStore
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.core.logging import configure_logging
from argus.core.metrics import (
    INFERENCE_FRAME_DURATION_SECONDS,
    INFERENCE_FRAMES_PROCESSED_TOTAL,
    INFERENCE_STAGE_DURATION_SECONDS,
)
from argus.inference.publisher import (
    HttpPublisher,
    NatsPublisher,
    ResilientPublisher,
    TelemetryFrame,
    TelemetryTrack,
)
from argus.models.enums import ProcessingMode, RuleAction, TrackerType
from argus.services.incident_capture import (
    IncidentClipCaptureService,
    IncidentTriggeredEvent,
    SQLIncidentRepository,
)
from argus.services.object_store import MinioObjectStore
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
from argus.vision.detector import DetectionModelConfig, YoloDetector
from argus.vision.homography import Homography
from argus.vision.privacy import PrivacyConfig, PrivacyFilter
from argus.vision.runtime import import_onnxruntime, resolve_execution_policy
from argus.vision.tracker import TrackerConfig, create_tracker
from argus.vision.types import Detection
from argus.vision.zones import Zones

type Frame = NDArray[np.uint8]

logger = logging.getLogger(__name__)


class ModelSettings(BaseModel):
    name: str
    path: str
    classes: list[str]
    input_shape: dict[str, int]
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45


class CameraSettings(BaseModel):
    rtsp_url: str
    frame_skip: int = 1
    fps_cap: int = 25


class PublishSettings(BaseModel):
    subject_prefix: str = "evt.tracking"
    http_fallback_url: str | None = None


class StreamSettings(BaseModel):
    profile_id: str = "native"
    kind: str = "passthrough"
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    fps: int = Field(default=25, ge=1)


class TrackerSettings(BaseModel):
    tracker_type: TrackerType
    frame_rate: int = 25


class EngineConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    camera_id: UUID
    mode: ProcessingMode
    profile: PublishProfile | None = None
    camera: CameraSettings
    publish: PublishSettings = Field(default_factory=PublishSettings)
    stream: StreamSettings = Field(default_factory=StreamSettings)
    model: ModelSettings
    secondary_model: ModelSettings | None = None
    tracker: TrackerSettings
    privacy: PrivacyPolicy = Field(default_factory=PrivacyPolicy)
    active_classes: list[str] = Field(default_factory=list)
    attribute_rules: list[dict[str, Any]] = Field(default_factory=list)
    zones: list[dict[str, Any]] = Field(default_factory=list)
    homography: dict[str, Any] | None = None


class CameraCommand(BaseModel):
    active_classes: list[str] | None = None
    tracker_type: TrackerType | None = None
    privacy: PrivacyPolicy | None = None
    attribute_rules: list[dict[str, Any]] | None = None
    zones: list[dict[str, Any]] | None = None


class FrameSource(Protocol):
    def next_frame(self) -> Frame: ...

    def close(self) -> None: ...


class Detector(Protocol):
    def detect(self, frame: Frame, allowed_classes: list[str]) -> list[Detection]: ...


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
    async def record(self, camera_id: UUID, ts: datetime, detections: list[Detection]) -> None: ...


class RuleEvaluator(Protocol):
    async def evaluate(
        self,
        *,
        camera_id: UUID,
        detections: list[Detection],
        ts: datetime,
    ) -> list[object]: ...


class EventSubscriber(Protocol):
    async def subscribe(self, subject: str, handler: Any) -> Any: ...

    async def publish(self, subject: str, payload: BaseModel) -> Any: ...


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


@dataclass(slots=True)
class _EngineState:
    active_classes: list[str]
    tracker_type: TrackerType
    privacy: PrivacyPolicy
    attribute_rules: list[dict[str, Any]]
    zones: list[dict[str, Any]]


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

    def add(self, stage_timings: dict[str, float]) -> None:
        self.frame_count += 1
        for stage_name, duration in stage_timings.items():
            self.stage_totals[stage_name] = self.stage_totals.get(stage_name, 0.0) + duration
            self.stage_maximums[stage_name] = max(
                self.stage_maximums.get(stage_name, 0.0),
                duration,
            )

    def reset(self) -> None:
        self.frame_count = 0
        self.stage_totals.clear()
        self.stage_maximums.clear()


def _format_stage_timings_ms(stage_timings: dict[str, float]) -> str:
    return ", ".join(
        f"{stage_name}={duration_ms:.1f}"
        for stage_name, duration_ms in stage_timings.items()
    )


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
        rule_engine: RuleEvaluator,
        event_client: EventSubscriber,
        stream_client: StreamClient,
        attribute_classifier: AttributeClassifier | None = None,
        anpr_processor: LineCrossingAnprProcessor | None = None,
        incident_capture: IncidentClipCaptureService | None = None,
        homography: Homography | None = None,
        privacy_filter: PrivacyFilter | None = None,
        preprocessor: Preprocessor | None = None,
        diagnostics_enabled: bool = False,
        timing_summary_interval_frames: int = 120,
    ) -> None:
        self.config = config
        self.frame_source = frame_source
        self.detector = detector
        self._tracker_factory = tracker_factory
        self.publisher = publisher
        self.tracking_store = tracking_store
        self.rule_engine = rule_engine
        self.event_client = event_client
        self.stream_client = stream_client
        self.attribute_classifier = attribute_classifier
        self.anpr_processor = anpr_processor
        self.incident_capture = incident_capture
        self.homography = homography or _build_homography(config.homography)
        self.preprocessor = preprocessor or _identity_preprocessor
        self._diagnostics_enabled = diagnostics_enabled
        self._timing_summary_interval_frames = max(0, timing_summary_interval_frames)
        self.privacy_filter = privacy_filter or PrivacyFilter(
            config=PrivacyConfig(
                blur_faces=config.privacy.blur_faces,
                blur_plates=config.privacy.blur_plates,
            )
        )
        self._state = _EngineState(
            active_classes=list(config.active_classes),
            tracker_type=config.tracker.tracker_type,
            privacy=config.privacy,
            attribute_rules=list(config.attribute_rules),
            zones=list(config.zones),
        )
        self._tracker = self._tracker_factory(self._state.tracker_type)
        self._zones = Zones(self._state.zones) if self._state.zones else None
        self._stream_registration: StreamRegistration | None = None
        self._track_history: dict[int, list[tuple[float, float]]] = defaultdict(list)
        self._frame_attempt_index = 0
        self._last_stage_timings: dict[str, float] = {}
        self._timing_summary = _TimingSummaryWindow()
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._stream_registration = await self.stream_client.register_stream(
            camera_id=self.config.camera_id,
            rtsp_url=self.config.camera.rtsp_url,
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
        processed = self.preprocessor(frame.copy())
        stage_timer.record_stage("preprocess", ended_at=loop.time())
        self._log_frame_diagnostic(
            "Worker frame detect starting",
            frame_attempt=frame_attempt,
            stage="detect",
            active_classes=list(self.active_classes),
        )
        detections = self.detector.detect(processed, self.active_classes)
        self._log_frame_diagnostic(
            "Worker frame detect completed",
            frame_attempt=frame_attempt,
            stage="detect",
            detection_count=len(detections),
        )
        stage_timer.record_stage("detect", ended_at=loop.time())
        filtered = [
            detection
            for detection in detections
            if detection.class_name in self.active_classes
        ]
        tracked = self._tracker.update(filtered, frame=processed)
        stage_timer.record_stage("track", ended_at=loop.time())
        tracked = self._apply_speed(tracked)
        stage_timer.record_stage("speed", ended_at=loop.time())
        tracked = self._apply_attributes(processed, tracked)
        stage_timer.record_stage("attributes", ended_at=loop.time())
        tracked = self._apply_zones(tracked)
        stage_timer.record_stage("zones", ended_at=loop.time())
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
            await self.event_client.publish(
                f"incident.triggered.{self.config.camera_id}",
                incident_event,
                )
        stage_timer.record_stage("rules", ended_at=loop.time())
        stream_frame = self._build_stream_frame(frame, tracked)
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
            await self.stream_client.push_frame(
                self._stream_registration,
                stream_frame,
                ts=current_ts,
            )
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
            counts=_counts_by_class(tracked),
            tracks=[_telemetry_track_from_detection(detection) for detection in tracked],
        )
        await self.publisher.publish(telemetry)
        stage_timer.record_stage("publish_telemetry", ended_at=loop.time())
        await self.tracking_store.record(self.config.camera_id, current_ts, tracked)
        stage_timer.record_stage("persist_tracking", ended_at=loop.time())
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
        if command.active_classes is not None:
            self._state.active_classes = list(command.active_classes)
        if command.tracker_type is not None and command.tracker_type != self._state.tracker_type:
            self._state.tracker_type = command.tracker_type
            self._tracker = self._tracker_factory(command.tracker_type)
        if command.privacy is not None and command.privacy != self._state.privacy:
            self._state.privacy = command.privacy
            self.privacy_filter = PrivacyFilter(
                config=PrivacyConfig(
                    blur_faces=command.privacy.blur_faces,
                    blur_plates=command.privacy.blur_plates,
                )
            )
            if self._started:
                self._stream_registration = await self.stream_client.register_stream(
                    camera_id=self.config.camera_id,
                    rtsp_url=self.config.camera.rtsp_url,
                    profile=self.profile,
                    stream_kind=self.config.stream.kind,
                    privacy=self._state.privacy,
                    target_fps=self.config.stream.fps,
                    target_width=self.config.stream.width,
                    target_height=self.config.stream.height,
                )
        if command.attribute_rules is not None:
            self._state.attribute_rules = list(command.attribute_rules)
        if command.zones is not None:
            self._state.zones = list(command.zones)
            self._zones = Zones(self._state.zones) if self._state.zones else None

    @property
    def active_classes(self) -> list[str]:
        if self._state.active_classes:
            return list(self._state.active_classes)
        return list(self.config.model.classes)

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

    def _apply_speed(self, detections: list[Detection]) -> list[Detection]:
        if self.homography is None:
            return detections
        enriched: list[Detection] = []
        for detection in detections:
            if detection.track_id is None:
                enriched.append(detection)
                continue
            x1, y1, x2, y2 = detection.bbox
            bottom_center = ((x1 + x2) / 2.0, y2)
            history = self._track_history[detection.track_id]
            history.append(bottom_center)
            if len(history) > 16:
                del history[:-16]
            speed_kph = self.homography.speed_kph(
                history,
                fps=max(1.0, float(self.config.camera.fps_cap)),
            )
            enriched.append(detection.with_updates(speed_kph=speed_kph))
        return enriched

    def _build_stream_frame(self, frame: Frame, detections: list[Detection]) -> Frame:
        if (
            self._stream_registration is None
            or self._stream_registration.mode is StreamMode.PASSTHROUGH
        ):
            return frame
        stream_frame = frame.copy()
        if self._state.privacy.requires_filtering:
            stream_frame = self.privacy_filter.apply(stream_frame)
        if self._stream_registration.mode is StreamMode.ANNOTATED_WHIP:
            self._draw_annotations(stream_frame, detections)
        return stream_frame

    def _draw_annotations(self, frame: Frame, detections: list[Detection]) -> None:
        for detection in detections:
            x1, y1, x2, y2 = (int(value) for value in detection.bbox)
            color = (255, 196, 64)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = detection.class_name
            if detection.track_id is not None:
                label = f"{label} #{detection.track_id}"
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

    def _rule_events_to_incidents(self, events: list[object]) -> list[IncidentTriggeredEvent]:
        incidents: list[IncidentTriggeredEvent] = []
        for event in events:
            action = getattr(event, "action", None)
            if action is None or action is RuleAction.COUNT:
                continue
            ts = getattr(event, "ts", datetime.now(tz=UTC))
            incidents.append(
                IncidentTriggeredEvent(
                    camera_id=self.config.camera_id,
                    ts=ts,
                    type=f"rule.{action.value}",
                    payload={
                        "name": getattr(event, "name", "rule-triggered"),
                        "action": action.value,
                        "detection": getattr(event, "detection", {}),
                    },
                )
                )
        return incidents

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
        logger.info(
            "Inference stage timing summary "
            "camera_id=%s frame_count=%s stage_avg_ms={%s} stage_max_ms={%s}",
            str(self.config.camera_id),
            frame_count,
            _format_stage_timings_ms(stage_avg_ms),
            _format_stage_timings_ms(stage_max_ms),
            extra={
                "camera_id": str(self.config.camera_id),
                "frame_count": frame_count,
                "stage_avg_ms": stage_avg_ms,
                "stage_max_ms": stage_max_ms,
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


def build_runtime_engine(
    config: EngineConfig,
    *,
    settings: Settings,
    events_client: NatsJetStreamClient,
    tracking_store: TrackingStore | None = None,
    rule_engine: RuleEvaluator | None = None,
    incident_capture: IncidentClipCaptureService | None = None,
) -> InferenceEngine:
    frame_source = create_camera_source(
        CameraSourceConfig(
            source_uri=config.camera.rtsp_url,
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
    detector = YoloDetector(
        DetectionModelConfig(
            name=config.model.name,
            path=config.model.path,
            classes=config.model.classes,
            input_shape=config.model.input_shape,
            confidence_threshold=config.model.confidence_threshold,
            iou_threshold=config.model.iou_threshold,
        ),
        runtime=runtime,
        runtime_policy=runtime_policy,
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

    token_issuer = MediaMTXTokenIssuer.from_settings(settings)

    return InferenceEngine(
        config=config,
        frame_source=frame_source,
        detector=detector,
        tracker_factory=tracker_factory,
        publisher=publisher,
        tracking_store=tracking_store or _NoopTrackingStore(),
        rule_engine=rule_engine or _NoopRuleEngine(),
        event_client=events_client,
        stream_client=MediaMTXClient(
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
        ),
        attribute_classifier=attribute_classifier,
        anpr_processor=anpr_processor,
        incident_capture=incident_capture,
        diagnostics_enabled=settings.worker_diagnostics_enabled,
    )


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
    engine = build_runtime_engine(
        config,
        settings=resolved_settings,
        events_client=events_client,
        tracking_store=TrackingEventStore(db_manager.session_factory),
        incident_capture=IncidentClipCaptureService(
            object_store=MinioObjectStore(resolved_settings),
            repository=SQLIncidentRepository(db_manager.session_factory),
            pre_seconds=resolved_settings.incident_clip_pre_seconds,
            post_seconds=resolved_settings.incident_clip_post_seconds,
            fps=resolved_settings.incident_clip_fps,
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


def _counts_by_class(detections: list[Detection]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for detection in detections:
        counts[detection.class_name] = counts.get(detection.class_name, 0) + 1
    return counts


def _telemetry_track_from_detection(detection: Detection) -> TelemetryTrack:
    x1, y1, x2, y2 = detection.bbox
    return TelemetryTrack(
        class_name=detection.class_name,
        confidence=detection.confidence,
        bbox={
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
        },
        track_id=detection.track_id or 0,
        speed_kph=detection.speed_kph,
        direction_deg=detection.direction_deg,
        zone_id=detection.zone_id,
        attributes=detection.attributes,
    )


class _NoopTrackingStore:
    async def record(self, camera_id: UUID, ts: datetime, detections: list[Detection]) -> None:
        return None


class _NoopRuleEngine:
    async def evaluate(
        self,
        *,
        camera_id: UUID,
        detections: list[Detection],
        ts: datetime,
    ) -> list[object]:
        return []


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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
