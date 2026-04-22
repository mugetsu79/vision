from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import pytest

from argus.inference.engine import (
    CameraSettings,
    EngineConfig,
    InferenceEngine,
    ModelSettings,
    PublishSettings,
    StreamSettings,
    TrackerSettings,
)
from argus.inference.publisher import TelemetryFrame
from argus.models.enums import ProcessingMode, TrackerType
from argus.streaming.mediamtx import (
    PrivacyPolicy,
    PublishProfile,
    StreamMode,
    StreamRegistration,
)
from argus.vision.types import Detection


class _SingleFrameSource:
    def __init__(self, frame: np.ndarray) -> None:
        self.frame = frame

    def next_frame(self) -> np.ndarray:
        return self.frame.copy()

    def close(self) -> None:
        return None


class _SyntheticDetector:
    def detect(self, frame: np.ndarray, allowed_classes: list[str]) -> list[Detection]:
        return [
            Detection(
                class_name=allowed_classes[0],
                confidence=0.94,
                bbox=(12.0, 12.0, 54.0, 54.0),
                class_id=0,
            )
        ]


@dataclass(slots=True)
class _SyntheticTracker:
    tracker_type: TrackerType

    def update(
        self,
        detections: list[Detection],
        frame: np.ndarray | None = None,
    ) -> list[Detection]:
        return [detection.with_updates(track_id=1) for detection in detections]


class _RecordingPublisher:
    def __init__(self) -> None:
        self.frames: list[TelemetryFrame] = []

    async def publish(self, frame: TelemetryFrame) -> None:
        self.frames.append(frame)

    async def close(self) -> None:
        return None


class _RecordingStore:
    def __init__(self) -> None:
        self.rows: list[tuple[datetime, list[Detection]]] = []

    async def record(self, camera_id, ts: datetime, detections: list[Detection]) -> None:
        self.rows.append((ts, detections))


class _NoopRuleEngine:
    async def evaluate(
        self,
        *,
        camera_id,
        detections: list[Detection],
        ts: datetime,
    ) -> list[object]:
        return []


class _NoopEvents:
    async def subscribe(self, subject: str, handler: object) -> None:
        return None


class _RecordingStreamClient:
    def __init__(self) -> None:
        self.modes: list[StreamMode] = []

    async def register_stream(
        self,
        *,
        camera_id,
        rtsp_url: str,
        profile: PublishProfile,
        stream_kind: str,
        privacy: PrivacyPolicy,
        target_fps: int,
        target_width: int | None = None,
        target_height: int | None = None,
    ) -> StreamRegistration:
        del target_fps, target_width, target_height
        if profile is PublishProfile.CENTRAL_GPU and stream_kind != StreamMode.PASSTHROUGH.value:
            mode = StreamMode.ANNOTATED_WHIP
        elif privacy.blur_faces or privacy.blur_plates:
            mode = StreamMode.FILTERED_PREVIEW
        else:
            mode = StreamMode.PASSTHROUGH
        self.modes.append(mode)
        return StreamRegistration(
            camera_id=camera_id,
            mode=mode,
            read_path=f"rtsp://mediamtx/{camera_id}/{mode.value}",
            publish_path=f"rtsp://mediamtx/{camera_id}/{mode.value}",
        )

    async def push_frame(
        self,
        registration: StreamRegistration,
        frame: np.ndarray,
        *,
        ts: datetime,
    ) -> None:
        self.modes.append(registration.mode)


def _config(camera_id, profile: PublishProfile, privacy: PrivacyPolicy) -> EngineConfig:
    return EngineConfig(
        camera_id=camera_id,
        mode=(
            ProcessingMode.CENTRAL
            if profile is PublishProfile.CENTRAL_GPU
            else ProcessingMode.EDGE
        ),
        profile=profile,
        camera=CameraSettings(rtsp_url="rtsp://camera.internal/live"),
        publish=PublishSettings(subject_prefix="evt.tracking"),
        stream=(
            StreamSettings(
                profile_id="720p10",
                kind="transcode",
                width=1280,
                height=720,
                fps=10,
            )
            if profile is PublishProfile.CENTRAL_GPU
            else StreamSettings()
        ),
        model=ModelSettings(
            name="synthetic",
            path="/models/synthetic.onnx",
            classes=["car"],
            input_shape={"width": 64, "height": 64},
        ),
        tracker=TrackerSettings(tracker_type=TrackerType.BOTSORT),
        privacy=privacy,
        active_classes=["car"],
        attribute_rules=[],
        zones=[],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("profile", "privacy", "expected_mode"),
    [
        (
            PublishProfile.CENTRAL_GPU,
            PrivacyPolicy(blur_faces=False, blur_plates=False),
            StreamMode.ANNOTATED_WHIP,
        ),
        (
            PublishProfile.JETSON_NANO,
            PrivacyPolicy(blur_faces=False, blur_plates=False),
            StreamMode.PASSTHROUGH,
        ),
        (
            PublishProfile.JETSON_NANO,
            PrivacyPolicy(blur_faces=True, blur_plates=False),
            StreamMode.FILTERED_PREVIEW,
        ),
    ],
)
async def test_worker_pipeline_emits_rows_and_expected_stream_variant(
    profile: PublishProfile,
    privacy: PrivacyPolicy,
    expected_mode: StreamMode,
) -> None:
    camera_id = uuid4()
    publisher = _RecordingPublisher()
    store = _RecordingStore()
    stream_client = _RecordingStreamClient()
    engine = InferenceEngine(
        config=_config(camera_id, profile, privacy),
        frame_source=_SingleFrameSource(np.zeros((64, 64, 3), dtype=np.uint8)),
        detector=_SyntheticDetector(),
        tracker_factory=lambda tracker_type: _SyntheticTracker(tracker_type),
        publisher=publisher,
        tracking_store=store,
        rule_engine=_NoopRuleEngine(),
        event_client=_NoopEvents(),
        stream_client=stream_client,
    )

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 18, 12, 0, tzinfo=UTC))

    assert len(store.rows) == 1
    assert publisher.frames[0].stream_mode is expected_mode
    assert stream_client.modes[0] is expected_mode
