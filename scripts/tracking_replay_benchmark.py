#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2

_IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
_TRACKER_CHOICES = ("botsort", "bytetrack")
_PROFILE_CHOICES = ("central-person", "edge-mixed")

BoundingBox = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class ReplayDetection:
    class_name: str
    class_id: int | None
    confidence: float
    bbox: BoundingBox


@dataclass(frozen=True, slots=True)
class GroundTruthObject:
    frame_id: int
    gt_id: str
    class_name: str
    bbox: BoundingBox
    visibility: float
    ignore: bool


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    frame_id: int
    image_path: Path | None
    detections: list[ReplayDetection]
    ground_truth: list[GroundTruthObject]


@dataclass(frozen=True, slots=True)
class ReplayTrack:
    stable_track_id: int
    class_name: str
    bbox: BoundingBox


class _EmptyDetector:
    def detect(self, frame: object, classes: list[str]) -> list[object]:
        return []


def load_replay_fixture(fixture_dir: Path) -> tuple[dict[str, Any], list[ReplayFrame]]:
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    detection_rows = _read_jsonl(fixture_dir / "detections.jsonl")
    gt_rows = _read_jsonl(fixture_dir / "ground_truth.jsonl")
    gt_by_frame: dict[int, list[GroundTruthObject]] = {}

    for row in gt_rows:
        gt = GroundTruthObject(
            frame_id=int(row["frame_id"]),
            gt_id=str(row["gt_id"]),
            class_name=str(row["class_name"]),
            bbox=_bbox_tuple(row["bbox"]),
            visibility=float(row.get("visibility", 1.0)),
            ignore=bool(row.get("ignore", False)),
        )
        gt_by_frame.setdefault(gt.frame_id, []).append(gt)

    distinct_gt_ids = {
        gt.gt_id for values in gt_by_frame.values() for gt in values if not gt.ignore
    }
    if len(distinct_gt_ids) < 2:
        raise ValueError(
            "Replay fixture must contain at least two distinct ground-truth identities."
        )

    frames: list[ReplayFrame] = []
    for row in detection_rows:
        frame_id = int(row["frame_id"])
        image_value = row.get("image")
        frames.append(
            ReplayFrame(
                frame_id=frame_id,
                image_path=fixture_dir / str(image_value) if image_value else None,
                detections=[
                    ReplayDetection(
                        class_name=str(det["class_name"]),
                        class_id=int(det["class_id"]) if det.get("class_id") is not None else None,
                        confidence=float(det["confidence"]),
                        bbox=_bbox_tuple(det["bbox"]),
                    )
                    for det in row.get("detections", [])
                ],
                ground_truth=gt_by_frame.get(frame_id, []),
            )
        )
    return manifest, frames


def evaluate_tracks(
    frames: list[ReplayFrame],
    *,
    track_outputs_by_frame: dict[int, list[ReplayTrack]],
    iou_match_threshold: float,
) -> dict[str, object]:
    previous_match_by_gt: dict[str, int] = {}
    matched_ids_by_gt: dict[str, set[int]] = {}
    visible_frames_by_gt: Counter[str] = Counter()
    matched_frames_by_gt: Counter[str] = Counter()
    track_lifetime_frames: Counter[int] = Counter()
    id_switches = 0
    duplicate_active_track_frames = 0

    for frame in frames:
        gt_objects = [gt for gt in frame.ground_truth if not gt.ignore and gt.visibility > 0.0]
        tracks = track_outputs_by_frame.get(frame.frame_id, [])
        for gt in gt_objects:
            visible_frames_by_gt[gt.gt_id] += 1

        candidate_pairs: list[tuple[float, str, int]] = []
        duplicate_matches_by_gt: Counter[str] = Counter()
        for gt in gt_objects:
            for track in tracks:
                if gt.class_name != track.class_name:
                    continue
                overlap = _iou(gt.bbox, track.bbox)
                if overlap >= iou_match_threshold:
                    duplicate_matches_by_gt[gt.gt_id] += 1
                    candidate_pairs.append((overlap, gt.gt_id, track.stable_track_id))

        duplicate_active_track_frames += sum(
            1 for count in duplicate_matches_by_gt.values() if count > 1
        )

        used_gt: set[str] = set()
        used_track: set[int] = set()
        for overlap, gt_id, stable_track_id in sorted(candidate_pairs, reverse=True):
            del overlap
            if gt_id in used_gt or stable_track_id in used_track:
                continue
            used_gt.add(gt_id)
            used_track.add(stable_track_id)
            matched_frames_by_gt[gt_id] += 1
            matched_ids_by_gt.setdefault(gt_id, set()).add(stable_track_id)
            previous = previous_match_by_gt.get(gt_id)
            if previous is not None and previous != stable_track_id:
                id_switches += 1
            previous_match_by_gt[gt_id] = stable_track_id
            track_lifetime_frames[stable_track_id] += 1

    fragmentation_by_gt = {
        gt_id: max(0, len(stable_ids) - 1) for gt_id, stable_ids in matched_ids_by_gt.items()
    }
    visible_total = sum(visible_frames_by_gt.values())
    matched_total = sum(matched_frames_by_gt.values())
    lifetimes = sorted(track_lifetime_frames.values())
    fragments = sorted(fragmentation_by_gt.values())
    return {
        "id_switches": id_switches,
        "track_fragmentation_sum": sum(fragmentation_by_gt.values()),
        "median_fragments_per_gt": _median(fragments),
        "median_track_lifetime_frames": _median(lifetimes),
        "coverage_ratio": matched_total / visible_total if visible_total else 0.0,
        "duplicate_active_track_frames": duplicate_active_track_frames,
    }


def compare_to_baseline(current: dict[str, object], baseline: dict[str, object]) -> list[str]:
    failures: list[str] = []
    base_metrics = baseline["metrics"]
    for key in (
        "fixture_id",
        "fixture_sha256",
        "tracker_scene_profile",
        "effective_processing_fps",
    ):
        if key not in baseline:
            failures.append(f"baseline missing {key}")
        elif current.get(key) != baseline[key]:
            failures.append(f"{key} does not match baseline")
    base_id_switches = int(base_metrics["id_switches"])
    base_fragments = int(base_metrics["track_fragmentation_sum"])
    if base_id_switches + base_fragments < 5:
        failures.append(
            "baseline continuity defects are below the required floor of 5"
        )
    current_id_switches = int(current["id_switches"])
    if base_id_switches >= 3:
        if current_id_switches > base_id_switches * 0.70:
            failures.append("id_switches did not improve by at least 30 percent")
    elif current_id_switches > base_id_switches:
        failures.append("id_switches increased")

    current_fragments = int(current["track_fragmentation_sum"])
    if base_fragments > 0:
        if current_fragments > base_fragments * 0.80:
            failures.append("track_fragmentation_sum did not improve by at least 20 percent")
    elif current_fragments > 0:
        failures.append("track_fragmentation_sum regressed from zero")

    if float(current["coverage_ratio"]) + 0.02 < float(base_metrics["coverage_ratio"]):
        failures.append("coverage_ratio regressed by more than 2 percentage points")
    if float(current["median_track_lifetime_frames"]) < float(
        base_metrics["median_track_lifetime_frames"]
    ):
        failures.append("median_track_lifetime_frames decreased")
    if int(current["duplicate_active_track_frames"]) > int(
        base_metrics["duplicate_active_track_frames"]
    ):
        failures.append("duplicate_active_track_frames increased")
    if "median_tracker_lifecycle_ms" not in base_metrics:
        failures.append("baseline missing median_tracker_lifecycle_ms")
    elif "median_tracker_lifecycle_ms" not in current:
        failures.append("median_tracker_lifecycle_ms missing from current metrics")
    elif float(current["median_tracker_lifecycle_ms"]) > float(
        base_metrics["median_tracker_lifecycle_ms"]
    ) * 1.10:
        failures.append("median_tracker_lifecycle_ms regressed by more than 10 percent")
    return failures


def run_fixture_benchmark(
    *,
    fixture_dir: Path,
    output_json: bool,
    track_runner: Callable[[ReplayFrame], list[ReplayTrack]] | None = None,
) -> dict[str, object]:
    manifest, frames = load_replay_fixture(fixture_dir)
    tracker_scene_profile = str(manifest.get("tracker_scene_profile", "difficult"))
    runner = track_runner or _default_track_runner(
        int(manifest["fps"]),
        tracker_scene_profile=tracker_scene_profile,
    )
    outputs: dict[int, list[ReplayTrack]] = {}
    frame_durations_ms: list[float] = []
    for frame in frames:
        started = time.perf_counter()
        outputs[frame.frame_id] = runner(frame)
        frame_durations_ms.append((time.perf_counter() - started) * 1000.0)
    del output_json
    summary = evaluate_tracks(
        frames,
        track_outputs_by_frame=outputs,
        iou_match_threshold=float(manifest.get("iou_match_threshold", 0.5)),
    )
    summary.update(
        {
            "effective_processing_fps": int(manifest["fps"]),
            "fixture_id": str(manifest.get("fixture_id", "")),
            "fixture_sha256": _fixture_sha256(fixture_dir),
            "median_tracker_lifecycle_ms": _median(frame_durations_ms),
            "tracker_scene_profile": tracker_scene_profile,
        }
    )
    return summary


def _default_track_runner(
    fps: int,
    *,
    tracker_scene_profile: str = "difficult",
) -> Callable[[ReplayFrame], list[ReplayTrack]]:
    import inspect
    from datetime import UTC, datetime, timedelta

    from argus.models.enums import TrackerType
    from argus.vision.track_lifecycle import TrackLifecycleConfig, TrackLifecycleManager
    from argus.vision.tracker import TrackerConfig, create_tracker
    from argus.vision.types import Detection

    if tracker_scene_profile not in {"efficient", "difficult"}:
        raise ValueError("tracker_scene_profile must be 'efficient' or 'difficult'.")

    safe_fps = max(1, fps)
    frame_interval_ms = 1000.0 / safe_fps
    tracker = create_tracker(
        TrackerConfig.for_scene_profile(
            tracker_scene_profile,
            tracker_type=TrackerType.BOTSORT,
            frame_rate=safe_fps,
        )
    )
    lifecycle_config_kwargs: dict[str, float] = {}
    if "nominal_frame_interval_ms" in inspect.signature(TrackLifecycleConfig).parameters:
        lifecycle_config_kwargs["nominal_frame_interval_ms"] = frame_interval_ms
    lifecycle = TrackLifecycleManager(TrackLifecycleConfig(**lifecycle_config_kwargs))
    start = datetime(2026, 1, 1, tzinfo=UTC)

    def run(frame: ReplayFrame) -> list[ReplayTrack]:
        detections = [
            Detection(
                class_name=detection.class_name,
                class_id=detection.class_id,
                confidence=detection.confidence,
                bbox=detection.bbox,
            )
            for detection in frame.detections
        ]
        image = (
            cv2.imread(str(frame.image_path))
            if frame.image_path is not None and frame.image_path.exists()
            else None
        )
        tracked = tracker.update(detections, frame=image)
        lifecycle_tracks = lifecycle.update(
            detections=tracked,
            ts=start + timedelta(milliseconds=(frame.frame_id - 1) * frame_interval_ms),
            frame_shape=image.shape if image is not None else None,
        )
        return [
            ReplayTrack(
                stable_track_id=track.stable_track_id,
                class_name=track.detection.class_name,
                bbox=track.detection.bbox,
            )
            for track in lifecycle_tracks
        ]

    return run


def run_benchmark(
    *,
    frames_path: Path,
    classes: list[str],
    output_json: bool,
    detector: object | None = None,
    tracker_type: str = "botsort",
    lifecycle_config: object | None = None,
) -> dict[str, object]:
    if tracker_type not in _TRACKER_CHOICES:
        raise ValueError(f"Unsupported tracker type: {tracker_type}")
    if not frames_path.exists():
        raise FileNotFoundError(f"Frames path does not exist: {frames_path}")
    if not frames_path.is_dir():
        raise NotADirectoryError(f"Frames path is not a directory: {frames_path}")

    del output_json, lifecycle_config

    detector = detector or _EmptyDetector()
    allowed_classes = list(classes)
    frame_paths = _iter_frame_paths(frames_path)
    frames_processed = 0
    detection_count_by_class: Counter[str] = Counter()
    track_classes: dict[str, str] = {}
    track_frame_counts: Counter[str] = Counter()
    active_tracks: set[str] = set()
    last_seen_frame: dict[str, int] = {}
    lost_tracks = 0
    recovered_tracks = 0
    duplicate_suppressed = 0
    id_switches = 0

    for frame_index, frame_path in enumerate(frame_paths, start=1):
        frame = cv2.imread(str(frame_path))
        if frame is None:
            continue

        frames_processed += 1
        detections = _detect(detector, frame, allowed_classes)
        seen_this_frame: set[str] = set()
        current_tracks: set[str] = set()

        for detection_index, detection in enumerate(detections):
            class_name = _class_name(detection)
            if allowed_classes and class_name not in allowed_classes:
                continue

            detection_count_by_class[class_name] += 1
            track_id = _stable_track_id(detection, detection_index=detection_index)
            if track_id in seen_this_frame:
                duplicate_suppressed += 1
                continue

            seen_this_frame.add(track_id)
            current_tracks.add(track_id)
            previous_class = track_classes.get(track_id)
            if previous_class is not None and previous_class != class_name:
                id_switches += 1
            track_classes.setdefault(track_id, class_name)
            track_frame_counts[track_id] += 1
            if track_id in last_seen_frame and last_seen_frame[track_id] < frame_index - 1:
                recovered_tracks += 1
            last_seen_frame[track_id] = frame_index

        lost_tracks += len(active_tracks - current_tracks)
        active_tracks = current_tracks

    stable_track_count_by_class: Counter[str] = Counter()
    for track_id, lifetime in track_frame_counts.items():
        if lifetime > 0:
            stable_track_count_by_class[track_classes[track_id]] += 1

    stable_tracks = sum(stable_track_count_by_class.values())
    average_track_lifetime = (
        sum(track_frame_counts.values()) / len(track_frame_counts) if track_frame_counts else 0.0
    )

    return {
        "frames_processed": frames_processed,
        "stable_tracks": stable_tracks,
        "id_switches": id_switches,
        "detection_count_by_class": dict(sorted(detection_count_by_class.items())),
        "stable_track_count_by_class": dict(sorted(stable_track_count_by_class.items())),
        "track_fragmentation": recovered_tracks,
        "average_track_lifetime": average_track_lifetime,
        "lost_tracks": lost_tracks,
        "recovered_tracks": recovered_tracks,
        "duplicate_suppressed": duplicate_suppressed,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _fixture_sha256(fixture_dir: Path) -> str:
    paths = [
        fixture_dir / "manifest.json",
        fixture_dir / "detections.jsonl",
        fixture_dir / "ground_truth.jsonl",
        *sorted((fixture_dir / "frames").glob("*")),
    ]
    digest = hashlib.sha256()
    for path in paths:
        if not path.is_file():
            continue
        digest.update(path.relative_to(fixture_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _bbox_tuple(value: object) -> BoundingBox:
    values = list(value) if isinstance(value, Sequence) and not isinstance(value, str) else []
    if len(values) != 4:
        raise ValueError(f"Expected bbox with four values, got {value!r}")
    return (float(values[0]), float(values[1]), float(values[2]), float(values[3]))


def _iou(left: BoundingBox, right: BoundingBox) -> float:
    left_x1, left_y1, left_x2, left_y2 = left
    right_x1, right_y1, right_x2, right_y2 = right
    x1 = max(left_x1, right_x1)
    y1 = max(left_y1, right_y1)
    x2 = min(left_x2, right_x2)
    y2 = min(left_y2, right_y2)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection <= 0.0:
        return 0.0
    left_area = max(0.0, left_x2 - left_x1) * max(0.0, left_y2 - left_y1)
    right_area = max(0.0, right_x2 - right_x1) * max(0.0, right_y2 - right_y1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    midpoint = len(values) // 2
    if len(values) % 2 == 1:
        return float(values[midpoint])
    return (values[midpoint - 1] + values[midpoint]) / 2.0


def _iter_frame_paths(frames_path: Path) -> list[Path]:
    return sorted(
        path
        for path in frames_path.iterdir()
        if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
    )


def _detect(detector: object, frame: object, classes: list[str]) -> Sequence[object]:
    detect = getattr(detector, "detect", None)
    if detect is None:
        raise TypeError("detector must expose a detect(...) method")

    try:
        detections = detect(frame, classes=classes)
    except TypeError as classes_error:
        try:
            detections = detect(frame, allowed_classes=classes)
        except TypeError:
            try:
                detections = detect(frame)
            except TypeError:
                raise classes_error from None

    if detections is None:
        return []
    if isinstance(detections, Sequence) and not isinstance(detections, (str, bytes, bytearray)):
        return detections
    if isinstance(detections, Iterable):
        return list(detections)
    raise TypeError("detector.detect(...) must return an iterable of detections")


def _class_name(detection: object) -> str:
    if isinstance(detection, dict):
        return str(detection.get("class_name") or detection.get("class") or detection.get("label"))
    return str(
        getattr(
            detection,
            "class_name",
            getattr(detection, "class_label", getattr(detection, "label", "unknown")),
        )
    )


def _stable_track_id(detection: object, *, detection_index: int) -> str:
    raw_track_id: Any
    if isinstance(detection, dict):
        raw_track_id = detection.get("track_id")
    else:
        raw_track_id = getattr(detection, "track_id", None)
    if raw_track_id is not None:
        return str(raw_track_id)
    return f"det-{detection_index}:{_class_name(detection)}:{_bbox_key(detection)}"


def _bbox_key(detection: object) -> str:
    if isinstance(detection, dict):
        bbox = detection.get("bbox") or detection.get("xyxy") or ()
    else:
        bbox = getattr(detection, "bbox", getattr(detection, "xyxy", ()))
    try:
        return ",".join(f"{float(value):.3f}" for value in bbox)
    except (TypeError, ValueError):
        return "no-bbox"


def _write_markdown_summary(path: Path, summary: dict[str, object]) -> None:
    lines = [
        "# Tracking Replay Benchmark",
        "",
        f"- Frames processed: {summary['frames_processed']}",
        f"- Stable tracks: {summary['stable_tracks']}",
        f"- ID switches: {summary['id_switches']}",
        f"- Average track lifetime: {summary['average_track_lifetime']}",
        f"- Lost tracks: {summary['lost_tracks']}",
        f"- Recovered tracks: {summary['recovered_tracks']}",
        f"- Duplicate suppressed: {summary['duplicate_suppressed']}",
        "",
        "## Detection Count By Class",
        "",
    ]
    detection_counts = summary["detection_count_by_class"]
    if isinstance(detection_counts, dict) and detection_counts:
        lines.extend(f"- {class_name}: {count}" for class_name, count in detection_counts.items())
    else:
        lines.append("- none: 0")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _parse_classes(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay image frames through a tracking benchmark."
    )
    parser.add_argument("--frames", type=Path, help="Directory containing replay frames.")
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Directory containing replay fixture manifest and JSONL streams.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Optional baseline JSON to compare against.",
    )
    parser.add_argument(
        "--assert-improvement",
        action="store_true",
        help="Fail when replay metrics do not satisfy the baseline improvement gate.",
    )
    parser.add_argument(
        "--classes",
        default="person",
        help="Comma-separated class names to evaluate.",
    )
    parser.add_argument("--tracker", choices=_TRACKER_CHOICES, default="botsort")
    parser.add_argument("--profile", choices=_PROFILE_CHOICES, default="central-person")
    parser.add_argument(
        "--json",
        "--output-json",
        dest="json",
        action="store_true",
        help="Print the summary as JSON.",
    )
    parser.add_argument("--markdown", type=Path, help="Optional path for a markdown summary.")
    args = parser.parse_args()
    if args.fixture is None and args.frames is None:
        parser.error("one of --fixture or --frames is required")
    if args.assert_improvement and args.baseline is None:
        parser.error("--assert-improvement requires --baseline")
    return args


def main() -> int:
    args = _parse_args()
    if args.fixture is not None:
        summary = run_fixture_benchmark(
            fixture_dir=args.fixture,
            output_json=args.json,
        )
        failures: list[str] = []
        if args.baseline is not None:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            failures = compare_to_baseline(summary, baseline)
        if args.json:
            print(json.dumps(summary, sort_keys=True))
        for failure in failures:
            print(f"baseline comparison failed: {failure}", file=sys.stderr)
        return 1 if failures else 0

    assert args.frames is not None
    summary = run_benchmark(
        frames_path=args.frames,
        classes=_parse_classes(args.classes),
        output_json=args.json,
        tracker_type=args.tracker,
        lifecycle_config={"profile": args.profile},
    )
    if args.markdown is not None:
        _write_markdown_summary(args.markdown, summary)
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
