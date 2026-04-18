from __future__ import annotations

import argparse
import asyncio
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from argus.models.enums import RuleAction, TrackerType
from argus.vision.benchmarking import (
    build_synthetic_detector,
    build_synthetic_frame,
    synthetic_tracker_backend_factory,
)
from argus.vision.homography import Homography
from argus.vision.rules import RuleDefinition, RuleEngine
from argus.vision.tracker import TrackerConfig, create_tracker
from argus.vision.types import Detection
from argus.vision.zones import Zones


class _JetsonPublisher:
    async def publish(self, subject: str, payload: object) -> None:  # noqa: ARG002
        return None


class _JetsonStore:
    async def record(self, event: object) -> None:  # noqa: ARG002
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Jetson-focused Prompt 3 benchmark for YOLO12n + BoT-SORT + zones + rules."
    )
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--expected-fps", type=float, default=25.0)
    return parser.parse_args()


async def _run_pipeline(iterations: int) -> float:
    frame = build_synthetic_frame()
    detector = build_synthetic_detector("TensorrtExecutionProvider")
    tracker = create_tracker(
        TrackerConfig(tracker_type=TrackerType.BOTSORT, frame_rate=25),
        backend_factory=synthetic_tracker_backend_factory,
    )
    zones = Zones(
        [
            {"id": "yard", "polygon": [[0, 0], [959, 0], [959, 1079], [0, 1079]]},
            {"id": "restricted", "polygon": [[960, 0], [1919, 0], [1919, 1079], [960, 1079]]},
        ]
    )
    homography = Homography(
        src_points=[(0.0, 0.0), (640.0, 0.0), (640.0, 640.0), (0.0, 640.0)],
        dst_points=[(0.0, 0.0), (12.0, 0.0), (12.0, 12.0), (0.0, 12.0)],
        ref_distance_m=12.0,
    )
    camera_id = uuid4()
    engine = RuleEngine(
        rules=[
            RuleDefinition(
                id=uuid4(),
                camera_id=camera_id,
                name="restricted-worker",
                predicate={"class_names": ["hi_vis_worker"], "zone_ids": ["restricted"]},
                action=RuleAction.COUNT,
            )
        ],
        publisher=_JetsonPublisher(),
        store=_JetsonStore(),
    )

    started_at = time.perf_counter()
    for frame_index in range(iterations):
        detections = detector.detect(frame, allowed_classes={"car", "person", "hi_vis_worker"})
        tracked = tracker.update(detections, frame)
        enriched: list[Detection] = []
        for tracked_detection in tracked:
            x1, y1, x2, y2 = tracked_detection.bbox
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            zone_id = zones.zone_for_point(center_x, center_y)
            speed_kph = homography.speed_kph(
                track_history=[
                    (center_x - 6.0, center_y),
                    (center_x - 3.0, center_y),
                    (center_x, center_y),
                ],
                fps=25.0,
            )
            enriched.append(
                tracked_detection.with_updates(zone_id=zone_id, speed_kph=speed_kph)
            )
        await engine.evaluate(
            camera_id=camera_id,
            detections=enriched,
            ts=time_to_datetime(frame_index),
        )
    elapsed_seconds = time.perf_counter() - started_at
    return iterations / elapsed_seconds


def time_to_datetime(frame_index: int) -> datetime:
    return datetime(2026, 4, 18, 12, 0, tzinfo=UTC) + timedelta(milliseconds=40 * frame_index)


def main() -> None:
    args = parse_args()
    fps = asyncio.run(_run_pipeline(args.iterations))
    print("Argus Jetson synthetic pipeline benchmark")
    print("Provider profile: TensorrtExecutionProvider (synthetic)")
    print("Target: YOLO12n @ 640x640 FP16 + BoT-SORT + zones + rules on a single 1080p stream")
    print(f"Measured FPS: {fps:.2f}")
    if fps >= args.expected_fps:
        print(f"PASS: >= {args.expected_fps:.2f} FPS")
    else:
        print(f"FAIL: < {args.expected_fps:.2f} FPS")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
