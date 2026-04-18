from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import httpx
import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from argus.core.config import Settings
from argus.core.db import DatabaseManager, TrackingEventStore
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.inference.publisher import (
    HttpPublisher,
    NatsPublisher,
    ResilientPublisher,
    TelemetryFrame,
    TelemetryTrack,
)
from argus.models.enums import ProcessingMode, TrackerType
from argus.streaming.mediamtx import (
    MediaMTXClient,
    PrivacyPolicy,
    PublishProfile,
    StreamMode,
    StreamRegistration,
    default_profile_probe,
    probe_publish_profile,
)
from argus.vision.attributes import AttributeClassifier, AttributeModelConfig
from argus.vision.camera import CameraSourceConfig, create_camera_source
from argus.vision.detector import DetectionModelConfig, YoloDetector
from argus.vision.homography import Homography
from argus.vision.privacy import PrivacyConfig, PrivacyFilter
from argus.vision.tracker import TrackerConfig, create_tracker
from argus.vision.types import Detection
from argus.vision.zones import Zones

type Frame = NDArray[np.uint8]


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
    pass


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


class StreamClient(Protocol):
    async def register_stream(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        privacy: PrivacyPolicy,
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
        homography: Homography | None = None,
        privacy_filter: PrivacyFilter | None = None,
        preprocessor: Preprocessor | None = None,
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
        self.homography = homography or _build_homography(config.homography)
        self.preprocessor = preprocessor or _identity_preprocessor
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
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._stream_registration = await self.stream_client.register_stream(
            camera_id=self.config.camera_id,
            rtsp_url=self.config.camera.rtsp_url,
            profile=self.profile,
            privacy=self._state.privacy,
        )
        await self.event_client.subscribe(
            f"cmd.camera.{self.config.camera_id}",
            self._handle_command_message,
        )
        self._started = True

    async def close(self) -> None:
        await self.publisher.close()
        self.frame_source.close()

    @property
    def profile(self) -> PublishProfile:
        if self.config.profile is not None:
            return self.config.profile
        return PublishProfile.CENTRAL_GPU

    async def run_once(self, *, ts: datetime | None = None) -> TelemetryFrame:
        if not self._started:
            await self.start()
        current_ts = ts or datetime.now(tz=UTC)
        frame = self.frame_source.next_frame()
        processed = self.preprocessor(frame.copy())
        detections = self.detector.detect(processed, self.active_classes)
        filtered = [
            detection
            for detection in detections
            if detection.class_name in self.active_classes
        ]
        tracked = self._tracker.update(filtered, frame=processed)
        tracked = self._apply_speed(tracked)
        tracked = self._apply_attributes(processed, tracked)
        tracked = self._apply_zones(tracked)
        await self.rule_engine.evaluate(
            camera_id=self.config.camera_id,
            detections=tracked,
            ts=current_ts,
        )
        stream_frame = self._build_stream_frame(frame)
        if (
            self._stream_registration is not None
            and self._stream_registration.mode is not StreamMode.PASSTHROUGH
        ):
            await self.stream_client.push_frame(
                self._stream_registration,
                stream_frame,
                ts=current_ts,
            )
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
        await self.tracking_store.record(self.config.camera_id, current_ts, tracked)
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
                    privacy=self._state.privacy,
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

    def _build_stream_frame(self, frame: Frame) -> Frame:
        should_filter = self._state.privacy.requires_filtering and (
            self._stream_registration is not None
            and self._stream_registration.mode is not StreamMode.PASSTHROUGH
        )
        if not should_filter:
            return frame
        return self.privacy_filter.apply(frame.copy())


async def load_engine_config(
    camera_id: UUID,
    *,
    settings: Settings,
    http_client: httpx.AsyncClient | None = None,
) -> EngineConfig:
    if http_client is not None:
        response = await http_client.get(f"/api/v1/cameras/{camera_id}/worker-config")
        response.raise_for_status()
        return EngineConfig.model_validate(response.json())

    async with httpx.AsyncClient(base_url=settings.api_base_url) as client:
        response = await client.get(f"/api/v1/cameras/{camera_id}/worker-config")
        response.raise_for_status()
        return EngineConfig.model_validate(response.json())


def build_runtime_engine(
    config: EngineConfig,
    *,
    settings: Settings,
    events_client: NatsJetStreamClient,
    tracking_store: TrackingStore | None = None,
    rule_engine: RuleEvaluator | None = None,
) -> InferenceEngine:
    frame_source = create_camera_source(
        CameraSourceConfig(
            source_uri=config.camera.rtsp_url,
            frame_skip=config.camera.frame_skip,
            fps_cap=config.camera.fps_cap,
        )
    )
    detector = YoloDetector(
        DetectionModelConfig(
            name=config.model.name,
            path=config.model.path,
            classes=config.model.classes,
            input_shape=config.model.input_shape,
            confidence_threshold=config.model.confidence_threshold,
            iou_threshold=config.model.iou_threshold,
        )
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
            )
        )
    else:
        attribute_classifier = None

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
        ),
        attribute_classifier=attribute_classifier,
    )


async def run_engine_for_camera(camera_id: UUID, *, settings: Settings | None = None) -> None:
    resolved_settings = settings or Settings()
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
    asyncio.run(run_engine_for_camera(args.camera_id))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


def _identity_preprocessor(frame: Frame) -> Frame:
    return frame
