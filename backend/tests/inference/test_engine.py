from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import numpy as np
import pytest

from argus.inference.engine import (
    CameraCommand,
    CameraSettings,
    EngineConfig,
    InferenceEngine,
    ModelSettings,
    PublishSettings,
    StreamSettings,
    TrackerSettings,
)
from argus.inference.publisher import TelemetryFrame
from argus.models.enums import ProcessingMode, RuleAction, TrackerType
from argus.services.incident_capture import IncidentTriggeredEvent
from argus.streaming.mediamtx import (
    PrivacyPolicy,
    PublishProfile,
    StreamMode,
    StreamRegistration,
)
from argus.vision.rules import RuleEventRecord
from argus.vision.types import Detection


class _FakeFrameSource:
    def __init__(self, frames: list[np.ndarray]) -> None:
        self._frames = iter(frames)

    def next_frame(self) -> np.ndarray:
        return next(self._frames)

    def close(self) -> None:
        return None


class _FakeDetector:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def detect(self, frame: np.ndarray, allowed_classes: list[str]) -> list[Detection]:
        self.calls.append(list(allowed_classes))
        return [
            Detection(class_name="car", confidence=0.95, bbox=(10.0, 10.0, 30.0, 30.0), class_id=0),
            Detection(class_name="bus", confidence=0.91, bbox=(40.0, 12.0, 90.0, 80.0), class_id=1),
        ]


@dataclass(slots=True)
class _FakeTracker:
    tracker_type: TrackerType

    def update(
        self,
        detections: list[Detection],
        frame: np.ndarray | None = None,
    ) -> list[Detection]:
        return [
            detection.with_updates(track_id=index + 1)
            for index, detection in enumerate(detections)
        ]


class _FakePublisher:
    def __init__(self) -> None:
        self.frames: list[TelemetryFrame] = []

    async def publish(self, frame: TelemetryFrame) -> None:
        self.frames.append(frame)

    async def close(self) -> None:
        return None


class _FakeTrackingStore:
    def __init__(self) -> None:
        self.records: list[tuple[UUID, list[Detection]]] = []

    async def record(self, camera_id: UUID, ts: datetime, detections: list[Detection]) -> None:
        self.records.append((camera_id, detections))


class _FakeRuleEngine:
    async def evaluate(
        self,
        *,
        camera_id: UUID,
        detections: list[Detection],
        ts: datetime,
    ) -> list[object]:
        return []


class _FakeEventClient:
    def __init__(self) -> None:
        self.handlers: dict[str, object] = {}
        self.published: list[tuple[str, object]] = []

    async def subscribe(self, subject: str, handler: object) -> None:
        self.handlers[subject] = handler

    async def publish(self, subject: str, payload: object) -> None:
        self.published.append((subject, payload))


class _FakeStreamClient:
    def __init__(self) -> None:
        self.registrations: list[tuple[PublishProfile, PrivacyPolicy]] = []
        self.pushed_modes: list[StreamMode] = []

    async def register_stream(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        privacy: PrivacyPolicy,
    ) -> StreamRegistration:
        self.registrations.append((profile, privacy))
        mode = (
            StreamMode.FILTERED_PREVIEW
            if privacy.blur_faces or privacy.blur_plates
            else StreamMode.PASSTHROUGH
        )
        if profile is PublishProfile.CENTRAL_GPU:
            mode = StreamMode.ANNOTATED_WHIP
        return StreamRegistration(
            camera_id=camera_id,
            mode=mode,
            read_path=f"rtsp://mediamtx.internal/{camera_id}/{mode.value}",
            publish_path=f"rtsp://mediamtx.internal/{camera_id}/{mode.value}",
        )

    async def push_frame(
        self,
        registration: StreamRegistration,
        frame: np.ndarray,
        *,
        ts: datetime,
    ) -> None:
        self.pushed_modes.append(registration.mode)


class _RuleIncidentEngine:
    async def evaluate(
        self,
        *,
        camera_id: UUID,
        detections: list[Detection],
        ts: datetime,
    ) -> list[RuleEventRecord]:
        return [
            RuleEventRecord(
                rule_id=uuid4(),
                camera_id=camera_id,
                action=RuleAction.ALERT,
                name="wrong-way",
                ts=ts,
                detection={
                    "class_name": "car",
                    "track_id": 1,
                    "bbox": {"x1": 10, "y1": 10, "x2": 30, "y2": 30},
                },
            )
        ]


def _engine_config(camera_id: UUID) -> EngineConfig:
    return EngineConfig(
        camera_id=camera_id,
        mode=ProcessingMode.CENTRAL,
        profile=PublishProfile.CENTRAL_GPU,
        camera=CameraSettings(
            rtsp_url="rtsp://camera.internal/live",
            frame_skip=1,
            fps_cap=25,
        ),
        publish=PublishSettings(
            subject_prefix="evt.tracking",
            http_fallback_url="http://backend.internal/api/v1/edge/telemetry",
        ),
        stream=StreamSettings(),
        model=ModelSettings(
            name="vehicles",
            path="/models/vehicles.onnx",
            classes=["car", "bus"],
            input_shape={"width": 96, "height": 96},
        ),
        tracker=TrackerSettings(tracker_type=TrackerType.BOTSORT),
        privacy=PrivacyPolicy(blur_faces=False, blur_plates=False),
        active_classes=["car"],
        attribute_rules=[],
        zones=[],
    )


@pytest.mark.asyncio
async def test_engine_applies_live_class_and_tracker_updates_without_restart() -> None:
    camera_id = uuid4()
    frames = [np.zeros((64, 64, 3), dtype=np.uint8), np.zeros((64, 64, 3), dtype=np.uint8)]
    detector = _FakeDetector()
    publisher = _FakePublisher()
    tracker_creations: list[TrackerType] = []

    def tracker_factory(tracker_type: TrackerType) -> _FakeTracker:
        tracker_creations.append(tracker_type)
        return _FakeTracker(tracker_type=tracker_type)

    engine = InferenceEngine(
        config=_engine_config(camera_id),
        frame_source=_FakeFrameSource(frames),
        detector=detector,
        tracker_factory=tracker_factory,
        publisher=publisher,
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=_FakeStreamClient(),
    )

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 18, 12, 0, tzinfo=UTC))
    await engine.apply_command(
        CameraCommand(
            active_classes=["bus"],
            tracker_type=TrackerType.BYTETRACK,
            privacy=PrivacyPolicy(blur_faces=True, blur_plates=False),
        )
    )
    await engine.run_once(ts=datetime(2026, 4, 18, 12, 0, 1, tzinfo=UTC))
    await engine.close()

    assert detector.calls == [["car"], ["bus"]]
    assert tracker_creations == [TrackerType.BOTSORT, TrackerType.BYTETRACK]
    assert [frame.counts for frame in publisher.frames] == [{"car": 1}, {"bus": 1}]


@pytest.mark.asyncio
async def test_engine_registers_filtered_stream_when_privacy_is_required_on_jetson() -> None:
    camera_id = uuid4()
    stream_client = _FakeStreamClient()
    config = _engine_config(camera_id).model_copy(
        update={
            "profile": PublishProfile.JETSON_NANO,
            "privacy": PrivacyPolicy(blur_faces=True, blur_plates=False),
        }
    )
    engine = InferenceEngine(
        config=config,
        frame_source=_FakeFrameSource([np.zeros((32, 32, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=stream_client,
    )

    await engine.start()

    assert stream_client.registrations == [
        (PublishProfile.JETSON_NANO, PrivacyPolicy(blur_faces=True, blur_plates=False))
    ]


@pytest.mark.asyncio
async def test_engine_publishes_incident_events_for_non_count_rule_matches() -> None:
    camera_id = uuid4()
    event_client = _FakeEventClient()
    engine = InferenceEngine(
        config=_engine_config(camera_id),
        frame_source=_FakeFrameSource([np.zeros((32, 32, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_RuleIncidentEngine(),
        event_client=event_client,
        stream_client=_FakeStreamClient(),
    )

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 19, 12, 10, tzinfo=UTC))

    assert len(event_client.published) == 1
    subject, payload = event_client.published[0]
    assert subject == f"incident.triggered.{camera_id}"
    assert isinstance(payload, IncidentTriggeredEvent)
    assert payload.type == "rule.alert"
