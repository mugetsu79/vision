from __future__ import annotations

import argparse

from argus.models.enums import TrackerType
from argus.vision.benchmarking import (
    benchmark_async,
    benchmark_sync,
    build_synthetic_attribute_classifier,
    build_synthetic_detections,
    build_synthetic_detector,
    build_synthetic_frame,
    format_result,
    fresh_rule_evaluation,
    synthetic_tracker_backend_factory,
)
from argus.vision.homography import Homography
from argus.vision.preprocess import (
    apply_clahe,
    apply_dark_channel_dehaze,
    apply_tonemap_drago,
)
from argus.vision.privacy import PrivacyConfig, PrivacyFilter
from argus.vision.tracker import TrackerConfig, create_tracker
from argus.vision.zones import Zones


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Prompt 3 vision modules.")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = build_synthetic_frame()
    base_detections = build_synthetic_detections()
    homography = Homography(
        src_points=[(0.0, 0.0), (640.0, 0.0), (640.0, 640.0), (0.0, 640.0)],
        dst_points=[(0.0, 0.0), (12.0, 0.0), (12.0, 12.0), (0.0, 12.0)],
        ref_distance_m=12.0,
    )
    zones = Zones(
        [
            {"id": "yard", "polygon": [[0, 0], [959, 0], [959, 1079], [0, 1079]]},
            {"id": "restricted", "polygon": [[960, 0], [1919, 0], [1919, 1079], [960, 1079]]},
        ]
    )
    privacy_filter = PrivacyFilter(
        config=PrivacyConfig(method="pixelate", blur_faces=True, blur_plates=True, strength=10),
    )

    print("Argus vision microbenchmarks on a synthetic 1080p frame")
    print()
    for provider_name in ("CPUExecutionProvider", "CUDAExecutionProvider"):
        detector = build_synthetic_detector(provider_name)
        attribute_classifier = build_synthetic_attribute_classifier(provider_name)
        tracker = create_tracker(
            TrackerConfig(tracker_type=TrackerType.BOTSORT, frame_rate=25),
            backend_factory=synthetic_tracker_backend_factory,
        )
        results = [
            benchmark_sync(
                name="preprocess.clahe",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda: apply_clahe(frame),
            ),
            benchmark_sync(
                name="preprocess.tonemap",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda: apply_tonemap_drago(frame),
            ),
            benchmark_sync(
                name="preprocess.dehaze",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda: apply_dark_channel_dehaze(frame, strength=0.85, window_size=9),
            ),
            benchmark_sync(
                name="detector.detect",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda detector=detector: detector.detect(
                    frame,
                    allowed_classes={"car", "person", "hi_vis_worker"},
                ),
            ),
            benchmark_sync(
                name="tracker.update",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda tracker=tracker: tracker.update(base_detections, frame),
            ),
            benchmark_sync(
                name="attributes.classify",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda attribute_classifier=attribute_classifier: attribute_classifier.classify(
                    frame,
                    base_detections,
                ),
            ),
            benchmark_sync(
                name="privacy.apply",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda: privacy_filter.apply(frame.copy()),
            ),
            benchmark_sync(
                name="homography.speed",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda: homography.speed_kph(
                    track_history=[(0.0, 0.0), (2.0, 0.0), (4.0, 0.0), (6.0, 0.0)],
                    fps=25.0,
                ),
            ),
            benchmark_sync(
                name="zones.lookup",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=lambda: zones.zone_for_point(1200.0, 540.0),
            ),
            benchmark_async(
                name="rules.evaluate",
                provider=provider_name,
                iterations=args.iterations,
                warmup=args.warmup,
                fn=fresh_rule_evaluation(),
            ),
        ]

        print(f"[{provider_name}]")
        for result in results:
            print(format_result(result))
        print()


if __name__ == "__main__":
    main()
