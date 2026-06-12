#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import cv2

_IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
_TRACKER_CHOICES = ("botsort", "bytetrack")
_PROFILE_CHOICES = ("central-person", "edge-mixed")


class _EmptyDetector:
    def detect(self, frame: object, classes: list[str]) -> list[object]:
        return []


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
                raise classes_error

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
    parser = argparse.ArgumentParser(description="Replay image frames through a tracking benchmark.")
    parser.add_argument("--frames", type=Path, required=True, help="Directory containing replay frames.")
    parser.add_argument("--classes", default="person", help="Comma-separated class names to evaluate.")
    parser.add_argument("--tracker", choices=_TRACKER_CHOICES, default="botsort")
    parser.add_argument("--profile", choices=_PROFILE_CHOICES, default="central-person")
    parser.add_argument("--json", action="store_true", help="Print the summary as JSON.")
    parser.add_argument("--markdown", type=Path, help="Optional path for a markdown summary.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
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
