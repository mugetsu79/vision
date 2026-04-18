from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import cv2
import numpy as np
from numpy.typing import NDArray

from argus.models.enums import RuleAction
from argus.vision.attributes import AttributeClassifier, AttributeModelConfig
from argus.vision.detector import DetectionModelConfig, YoloDetector
from argus.vision.rules import RuleDefinition, RuleEngine
from argus.vision.tracker import TrackerConfig
from argus.vision.types import Detection


@dataclass(slots=True)
class BenchmarkResult:
    name: str
    provider: str
    p50_ms: float
    p95_ms: float


@dataclass(slots=True)
class _FakeInput:
    name: str


class SyntheticOrtSession:
    def __init__(self, providers: list[str], outputs: list[NDArray[np.float32]]) -> None:
        self._providers = providers
        self._outputs = outputs

    def get_inputs(self) -> list[_FakeInput]:
        return [_FakeInput(name="images")]

    def get_providers(self) -> list[str]:
        return self._providers

    def run(
        self,
        output_names: object,  # noqa: ARG002
        inputs: dict[str, NDArray[np.float32]],  # noqa: ARG002
    ) -> list[NDArray[np.float32]]:
        return self._outputs


class SyntheticOrtRuntime:
    def __init__(self, provider_name: str, outputs: list[NDArray[np.float32]]) -> None:
        self.provider_name = provider_name
        self.outputs = outputs

    def get_available_providers(self) -> list[str]:
        return [self.provider_name, "CPUExecutionProvider"]

    def InferenceSession(
        self,
        model_path: str,  # noqa: ARG002
        providers: list[str],
        sess_options: object | None = None,  # noqa: ARG002
    ) -> SyntheticOrtSession:
        return SyntheticOrtSession(providers=providers, outputs=self.outputs)


class SyntheticTrackerBackend:
    def __init__(self, tracker_name: str) -> None:
        self.tracker_name = tracker_name

    def update(
        self,
        results: Any,
        img: NDArray[np.uint8] | None = None,  # noqa: ARG002
        feats: NDArray[np.float32] | None = None,  # noqa: ARG002
    ) -> list[list[float]]:
        rows: list[list[float]] = []
        for index, bbox in enumerate(results.xyxy):
            rows.append(
                [
                    float(bbox[0]),
                    float(bbox[1]),
                    float(bbox[2]),
                    float(bbox[3]),
                    float(100 + index),
                    float(results.conf[index]),
                    float(results.cls[index]),
                    float(index),
                ]
            )
        return rows


class MemoryPublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, object]] = []

    async def publish(self, subject: str, payload: object) -> None:
        self.messages.append((subject, payload))


class MemoryStore:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def record(self, event: object) -> None:
        self.events.append(event)


def benchmark_sync(
    *,
    name: str,
    provider: str,
    iterations: int,
    warmup: int,
    fn: Callable[[], object],
) -> BenchmarkResult:
    for _ in range(warmup):
        fn()

    samples = []
    for _ in range(iterations):
        started_at = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started_at) * 1000.0)
    return _summarize(name, provider, samples)


def benchmark_async(
    *,
    name: str,
    provider: str,
    iterations: int,
    warmup: int,
    fn: Callable[[], Coroutine[object, object, object]],
) -> BenchmarkResult:
    with asyncio.Runner() as runner:
        for _ in range(warmup):
            runner.run(fn())

        samples = []
        for _ in range(iterations):
            started_at = time.perf_counter()
            runner.run(fn())
            samples.append((time.perf_counter() - started_at) * 1000.0)
    return _summarize(name, provider, samples)


def build_synthetic_frame(
    *,
    width: int = 1920,
    height: int = 1080,
) -> NDArray[np.uint8]:
    x_gradient = np.linspace(40, 220, width, dtype=np.uint8)
    y_gradient = np.linspace(20, 180, height, dtype=np.uint8)
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, 0] = y_gradient[:, np.newaxis]
    frame[:, :, 1] = x_gradient[np.newaxis, :]
    frame[:, :, 2] = np.flipud(frame[:, :, 1])
    cv2.rectangle(frame, (240, 420), (520, 720), (40, 210, 220), thickness=-1)
    cv2.rectangle(frame, (860, 380), (1220, 760), (50, 80, 240), thickness=-1)
    cv2.rectangle(frame, (1380, 460), (1710, 760), (210, 120, 80), thickness=-1)
    return np.asarray(cv2.GaussianBlur(frame, (5, 5), 0), dtype=np.uint8)


def build_synthetic_detector(provider_name: str) -> YoloDetector:
    runtime = SyntheticOrtRuntime(
        provider_name,
        outputs=[
            np.array(
                [
                    [240.0, 420.0, 520.0, 720.0, 0.96, 3.0],
                    [860.0, 380.0, 1220.0, 760.0, 0.94, 0.0],
                    [1380.0, 460.0, 1710.0, 760.0, 0.92, 2.0],
                ],
                dtype=np.float32,
            )
        ],
    )
    return YoloDetector(
        DetectionModelConfig(
            name="synthetic-yolo",
            path="synthetic.onnx",
            classes=["car", "truck", "person", "hi_vis_worker"],
            input_shape={"width": 640, "height": 640},
            confidence_threshold=0.1,
        ),
        runtime=runtime,
    )


def build_synthetic_attribute_classifier(provider_name: str) -> AttributeClassifier:
    runtime = SyntheticOrtRuntime(
        provider_name,
        outputs=[np.array([[0.88, 0.17]], dtype=np.float32)],
    )
    return AttributeClassifier(
        AttributeModelConfig(
            name="synthetic-attributes",
            path="synthetic-attributes.onnx",
            classes=["hi_vis", "hard_hat"],
            input_shape={"width": 64, "height": 64},
            target_classes={"person", "hi_vis_worker"},
        ),
        runtime=runtime,
    )


def build_synthetic_detections() -> list[Detection]:
    return [
        Detection(
            class_name="hi_vis_worker",
            class_id=3,
            confidence=0.96,
            bbox=(240.0, 420.0, 520.0, 720.0),
            attributes={"hi_vis": True},
        ),
        Detection(
            class_name="car",
            class_id=0,
            confidence=0.94,
            bbox=(860.0, 380.0, 1220.0, 760.0),
        ),
    ]


def synthetic_tracker_backend_factory(
    tracker_name: str,
    tracker_config: TrackerConfig,  # noqa: ARG001
) -> SyntheticTrackerBackend:
    return SyntheticTrackerBackend(tracker_name)


def build_synthetic_rule_engine() -> tuple[UUID, RuleEngine]:
    camera_id = uuid4()
    rule = RuleDefinition(
        id=uuid4(),
        camera_id=camera_id,
        name="restricted-no-vest",
        predicate={
            "class_names": ["person", "hi_vis_worker"],
            "zone_ids": ["restricted"],
            "attributes": {"hi_vis": False},
            "min_confidence": 0.5,
        },
        action=RuleAction.ALERT,
    )
    return camera_id, RuleEngine(
        rules=[rule],
        publisher=MemoryPublisher(),
        store=MemoryStore(),
    )


def fresh_rule_evaluation() -> Callable[[], Coroutine[object, object, object]]:
    async def _evaluate() -> object:
        camera_id, engine = build_synthetic_rule_engine()
        detections = [
            Detection(
                class_name="person",
                class_id=2,
                confidence=0.97,
                bbox=(240.0, 420.0, 520.0, 720.0),
                zone_id="restricted",
                attributes={"hi_vis": False},
                track_id=17,
            )
        ]
        return await engine.evaluate(
            camera_id=camera_id,
            detections=detections,
            ts=datetime.now(tz=UTC),
        )

    return _evaluate


def format_result(result: BenchmarkResult) -> str:
    return (
        f"{result.provider:<8} {result.name:<22} "
        f"p50={result.p50_ms:8.2f} ms  p95={result.p95_ms:8.2f} ms"
    )


def _summarize(name: str, provider: str, samples: list[float]) -> BenchmarkResult:
    percentiles = np.percentile(np.asarray(samples, dtype=np.float64), [50, 95])
    return BenchmarkResult(
        name=name,
        provider=provider,
        p50_ms=float(percentiles[0]),
        p95_ms=float(percentiles[1]),
    )
