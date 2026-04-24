from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import numpy as np
import pytest

from argus.core import metrics as core_metrics
from argus.inference import engine as engine_module
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
from argus.vision.runtime import (
    CpuVendor,
    ExecutionProfile,
    ExecutionProvider,
    HostClassification,
    RuntimeExecutionPolicy,
)
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


class _FakeAttributeClassifier:
    def classify(
        self,
        frame: np.ndarray,
        detections: list[Detection],
    ) -> list[dict[str, object]]:
        return [{"color": "blue"} for _ in detections]


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
        self.registrations: list[tuple[PublishProfile, str, PrivacyPolicy]] = []
        self.pushed_modes: list[StreamMode] = []
        self.pushed_frames: list[np.ndarray] = []
        self.register_stream_calls: list[dict[str, object]] = []

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
    ) -> StreamRegistration:
        self.register_stream_calls.append(
            {
                "stream_kind": stream_kind,
                "target_fps": target_fps,
                "target_width": target_width,
                "target_height": target_height,
            }
        )
        self.registrations.append((profile, stream_kind, privacy))
        mode = (
            StreamMode.FILTERED_PREVIEW
            if privacy.blur_faces or privacy.blur_plates
            else StreamMode.PASSTHROUGH
        )
        if profile is PublishProfile.CENTRAL_GPU and stream_kind != StreamMode.PASSTHROUGH.value:
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
        self.pushed_frames.append(frame.copy())
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


def _metric_sample_value(metric: object, sample_name: str, labels: dict[str, str]) -> float:
    for family in metric.collect():
        for sample in family.samples:
            if sample.name == sample_name and sample.labels == labels:
                return float(sample.value)
    return 0.0


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
        (
            PublishProfile.JETSON_NANO,
            "passthrough",
            PrivacyPolicy(blur_faces=True, blur_plates=False),
        )
    ]


@pytest.mark.asyncio
async def test_engine_draws_annotations_for_central_stream_frames() -> None:
    camera_id = uuid4()
    stream_client = _FakeStreamClient()
    config = _engine_config(camera_id).model_copy(
        update={
            "stream": StreamSettings(
                profile_id="720p10",
                kind="transcode",
                width=1280,
                height=720,
                fps=10,
            )
        }
    )
    engine = InferenceEngine(
        config=config,
        frame_source=_FakeFrameSource([np.zeros((64, 64, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type=tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=stream_client,
    )

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 18, 12, 0, tzinfo=UTC))
    await engine.close()

    assert stream_client.pushed_modes == [StreamMode.ANNOTATED_WHIP]
    assert np.any(stream_client.pushed_frames[0] != 0)


@pytest.mark.asyncio
async def test_engine_respects_passthrough_stream_kind_even_on_central_profile() -> None:
    camera_id = uuid4()
    stream_client = _FakeStreamClient()
    publisher = _FakePublisher()
    config = _engine_config(camera_id).model_copy(
        update={
            "stream": StreamSettings(
                profile_id="native",
                kind="passthrough",
                width=None,
                height=None,
                fps=25,
            )
        }
    )

    engine = InferenceEngine(
        config=config,
        frame_source=_FakeFrameSource([np.zeros((64, 64, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type=tracker_type),
        publisher=publisher,
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=stream_client,
    )

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 22, 19, 45, tzinfo=UTC))
    await engine.close()

    assert stream_client.register_stream_calls == [{
        "stream_kind": "passthrough",
        "target_fps": 25,
        "target_width": None,
        "target_height": None,
    }]
    assert stream_client.pushed_modes == []
    assert stream_client.pushed_frames == []
    assert publisher.frames[0].stream_mode is StreamMode.PASSTHROUGH


@pytest.mark.asyncio
async def test_engine_registers_browser_delivery_dimensions_and_fps() -> None:
    camera_id = uuid4()
    stream_client = _FakeStreamClient()
    config = _engine_config(camera_id).model_copy(
        update={
            "stream": StreamSettings(
                profile_id="720p10",
                kind="transcode",
                width=1280,
                height=720,
                fps=10,
            )
        }
    )

    engine = InferenceEngine(
        config=config,
        frame_source=_FakeFrameSource([np.zeros((64, 64, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type=tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=stream_client,
    )

    await engine.start()
    await engine.close()

    assert stream_client.register_stream_calls == [{
        "stream_kind": "transcode",
        "target_fps": 10,
        "target_width": 1280,
        "target_height": 720,
    }]


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


@pytest.mark.asyncio
async def test_engine_exposes_last_stage_timings_for_processed_frame() -> None:
    camera_id = uuid4()
    config = _engine_config(camera_id).model_copy(
        update={
            "stream": StreamSettings(
                profile_id="720p10",
                kind="transcode",
                width=1280,
                height=720,
                fps=10,
            )
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
        stream_client=_FakeStreamClient(),
        attribute_classifier=_FakeAttributeClassifier(),
    )

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 21, 19, 40, tzinfo=UTC))

    assert set(engine.last_stage_timings) >= {
        "capture",
        "preprocess",
        "detect",
        "track",
        "speed",
        "attributes",
        "zones",
        "rules",
        "annotate",
        "publish_stream",
        "publish_telemetry",
        "persist_tracking",
        "total",
    }
    assert engine.last_stage_timings["detect"] >= 0.0
    assert engine.last_stage_timings["attributes"] >= 0.0
    assert engine.last_stage_timings["publish_stream"] >= 0.0
    assert engine.last_stage_timings["total"] >= engine.last_stage_timings["detect"]


@pytest.mark.asyncio
async def test_engine_diagnostics_log_frame_stage_boundaries(
    caplog: pytest.LogCaptureFixture,
) -> None:
    camera_id = uuid4()
    config = _engine_config(camera_id).model_copy(
        update={
            "stream": StreamSettings(
                profile_id="720p10",
                kind="transcode",
                width=1280,
                height=720,
                fps=10,
            )
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
        stream_client=_FakeStreamClient(),
        diagnostics_enabled=True,
    )
    caplog.set_level(logging.INFO, logger="argus.inference.engine")

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 23, 9, 30, tzinfo=UTC))

    messages = [record.message for record in caplog.records]
    assert any("Worker frame capture starting" in message for message in messages)
    assert any("Worker frame capture completed" in message for message in messages)
    assert any("Worker frame publish_stream starting" in message for message in messages)
    assert any("Worker frame completed" in message for message in messages)


@pytest.mark.asyncio
async def test_engine_records_stage_duration_metrics_by_camera_and_stage() -> None:
    camera_id = uuid4()
    engine = InferenceEngine(
        config=_engine_config(camera_id),
        frame_source=_FakeFrameSource([np.zeros((32, 32, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=_FakeStreamClient(),
        attribute_classifier=_FakeAttributeClassifier(),
    )

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 21, 19, 41, tzinfo=UTC))

    assert _metric_sample_value(
        core_metrics.INFERENCE_STAGE_DURATION_SECONDS,
        "argus_inference_stage_duration_seconds_count",
        {"camera_id": str(camera_id), "stage": "detect"},
    ) == 1.0
    assert _metric_sample_value(
        core_metrics.INFERENCE_STAGE_DURATION_SECONDS,
        "argus_inference_stage_duration_seconds_count",
        {"camera_id": str(camera_id), "stage": "attributes"},
    ) == 1.0
    assert _metric_sample_value(
        core_metrics.INFERENCE_STAGE_DURATION_SECONDS,
        "argus_inference_stage_duration_seconds_count",
        {"camera_id": str(camera_id), "stage": "publish_stream"},
    ) == 1.0


@pytest.mark.asyncio
async def test_engine_logs_periodic_stage_timing_summary(caplog: pytest.LogCaptureFixture) -> None:
    camera_id = uuid4()
    caplog.set_level(logging.INFO, logger="argus.inference.engine")
    engine = InferenceEngine(
        config=_engine_config(camera_id),
        frame_source=_FakeFrameSource(
            [
                np.zeros((32, 32, 3), dtype=np.uint8),
                np.zeros((32, 32, 3), dtype=np.uint8),
            ]
        ),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=_FakeStreamClient(),
        attribute_classifier=_FakeAttributeClassifier(),
        timing_summary_interval_frames=2,
    )

    await engine.start()
    await engine.run_once(ts=datetime(2026, 4, 21, 19, 42, tzinfo=UTC))
    await engine.run_once(ts=datetime(2026, 4, 21, 19, 42, 1, tzinfo=UTC))

    summary_records = [
        record
        for record in caplog.records
        if record.name == "argus.inference.engine"
        and record.message.startswith("Inference stage timing summary")
    ]

    assert len(summary_records) == 1
    record = summary_records[0]
    assert "camera_id=" in record.message
    assert "stage_avg_ms=" in record.message
    assert "stage_max_ms=" in record.message
    assert "detect" in record.message
    assert "total" in record.message
    assert record.camera_id == str(camera_id)
    assert record.frame_count == 2
    assert "detect" in record.stage_avg_ms
    assert "total" in record.stage_max_ms


def test_worker_main_configures_logging_and_reuses_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    fake_settings = object()
    captured: dict[str, object] = {}

    class _Awaitable:
        def __await__(self) -> object:
            if False:
                yield None
            return None

    def fake_configure_logging(settings: object) -> None:
        captured["configured_settings"] = settings

    def fake_run_engine_for_camera(
        received_camera_id: UUID,
        *,
        settings: object | None = None,
    ) -> _Awaitable:
        captured["camera_id"] = received_camera_id
        captured["worker_settings"] = settings
        return _Awaitable()

    def fake_asyncio_run(awaitable: object) -> None:
        captured["awaitable"] = awaitable
        return None

    monkeypatch.setattr(engine_module, "Settings", lambda: fake_settings)
    monkeypatch.setattr(engine_module, "configure_logging", fake_configure_logging, raising=False)
    monkeypatch.setattr(engine_module, "run_engine_for_camera", fake_run_engine_for_camera)
    monkeypatch.setattr(engine_module.asyncio, "run", fake_asyncio_run)

    assert engine_module.main(["--camera-id", str(camera_id)]) == 0
    assert captured["configured_settings"] is fake_settings
    assert captured["camera_id"] == camera_id
    assert captured["worker_settings"] is fake_settings
    assert captured["awaitable"].__class__.__name__ == "_Awaitable"


@pytest.mark.asyncio
async def test_build_runtime_engine_resolves_provider_policy_once_and_passes_it_to_models(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    camera_id = uuid4()
    fake_runtime = object()
    runtime_policy = RuntimeExecutionPolicy(
        host=HostClassification(
            system="darwin",
            machine="arm64",
            cpu_vendor=CpuVendor.APPLE,
            available_providers=(
                ExecutionProvider.COREML.value,
                ExecutionProvider.CPU.value,
            ),
            profile=ExecutionProfile.MACOS_APPLE_SILICON,
            profile_overridden=False,
        ),
        provider=ExecutionProvider.COREML.value,
        available_providers=(
            ExecutionProvider.COREML.value,
            ExecutionProvider.CPU.value,
        ),
        provider_overridden=False,
        inter_op_threads=2,
        intra_op_threads=4,
    )
    detector_calls: dict[str, object] = {}
    attribute_calls: dict[str, object] = {}

    class _FakeResolvedDetector:
        def __init__(self, model_config: object, runtime: object, runtime_policy: object) -> None:
            detector_calls["model_config"] = model_config
            detector_calls["runtime"] = runtime
            detector_calls["runtime_policy"] = runtime_policy

    class _FakeResolvedAttributeClassifier:
        def __init__(self, model_config: object, runtime: object, runtime_policy: object) -> None:
            attribute_calls["model_config"] = model_config
            attribute_calls["runtime"] = runtime
            attribute_calls["runtime_policy"] = runtime_policy

    monkeypatch.setattr(
        engine_module,
        "create_camera_source",
        lambda camera_config: _FakeFrameSource([]),
    )
    monkeypatch.setattr(engine_module, "import_onnxruntime", lambda: fake_runtime)
    monkeypatch.setattr(
        engine_module,
        "resolve_execution_policy",
        lambda runtime, **kwargs: runtime_policy,
    )
    monkeypatch.setattr(engine_module, "YoloDetector", _FakeResolvedDetector)
    monkeypatch.setattr(engine_module, "AttributeClassifier", _FakeResolvedAttributeClassifier)

    class _StubMediaMTXClient:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

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
        ) -> StreamRegistration:
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.PASSTHROUGH,
                path_name=f"cameras/{camera_id}/passthrough",
                read_path=f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough",
                managed_path_config=True,
                ingest_path=f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough",
            )

    monkeypatch.setattr(engine_module, "MediaMTXClient", _StubMediaMTXClient)

    class _StubTokenIssuer:
        @classmethod
        def from_settings(cls, settings: object) -> _StubTokenIssuer:
            return cls()

        def issue_publish_token(
            self, *, subject: str, camera_id: UUID, path_name: str
        ) -> str:
            return "token"

    monkeypatch.setattr(engine_module, "MediaMTXTokenIssuer", _StubTokenIssuer)

    config = _engine_config(camera_id).model_copy(
        update={
            "secondary_model": ModelSettings(
                name="ppe-attributes",
                path="/models/ppe-attributes.onnx",
                classes=["hi_vis", "hard_hat"],
                input_shape={"width": 64, "height": 64},
            )
        }
    )
    settings = engine_module.Settings(_env_file=None)
    caplog.set_level(logging.INFO, logger="argus.inference.engine")

    await engine_module.build_runtime_engine(
        config,
        settings=settings,
        events_client=_FakeEventClient(),
    )

    assert detector_calls["runtime"] is fake_runtime
    assert detector_calls["runtime_policy"] is runtime_policy
    assert attribute_calls["runtime"] is fake_runtime
    assert attribute_calls["runtime_policy"] is runtime_policy
    assert any(
        "Resolved inference runtime policy" in record.message
        and "detection_provider=CoreMLExecutionProvider" in record.message
        and "attribute_provider=CoreMLExecutionProvider" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_engine_uses_initial_registration_without_calling_register_stream() -> None:
    from argus.streaming.mediamtx import StreamMode, StreamRegistration

    camera_id = uuid4()
    registration = StreamRegistration(
        camera_id=camera_id,
        mode=StreamMode.PASSTHROUGH,
        path_name=f"cameras/{camera_id}/passthrough",
        read_path=f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough",
        managed_path_config=True,
        ingest_path=f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough",
    )

    stream_client = _FakeStreamClient()
    engine = InferenceEngine(
        config=_engine_config(camera_id),
        frame_source=_FakeFrameSource([np.zeros((32, 32, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=stream_client,
        initial_registration=registration,
    )

    await engine.start()

    assert engine._stream_registration is registration
    assert stream_client.register_stream_calls == []
