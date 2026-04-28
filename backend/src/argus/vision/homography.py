from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from math import hypot

import cv2
import numpy as np
from numpy.typing import NDArray


@dataclass(slots=True)
class Homography:
    src_points: Sequence[tuple[float, float]]
    dst_points: Sequence[tuple[float, float]]
    ref_distance_m: float
    smoothing_window: int = 5
    _src: NDArray[np.float32] = field(init=False, repr=False)
    _dst: NDArray[np.float32] = field(init=False, repr=False)
    _matrix: NDArray[np.float32] = field(init=False, repr=False)
    _scale: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.src_points) != 4 or len(self.dst_points) != 4:
            raise ValueError("Homography requires exactly four source and destination points.")

        self._src = np.asarray(self.src_points, dtype=np.float32)
        self._dst = np.asarray(self.dst_points, dtype=np.float32)
        self._matrix = np.asarray(
            cv2.getPerspectiveTransform(self._src, self._dst),
            dtype=np.float32,
        )
        reference_span = hypot(
            float(self._dst[1][0] - self._dst[0][0]),
            float(self._dst[1][1] - self._dst[0][1]),
        )
        self._scale = self.ref_distance_m / reference_span if reference_span > 0 else 1.0

    def pixel_to_world(self, x: float, y: float) -> tuple[float, float]:
        source_point = np.asarray([[[x, y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(source_point, self._matrix)[0, 0]
        return float(transformed[0] * self._scale), float(transformed[1] * self._scale)

    def speed_kph(self, track_history: Sequence[tuple[float, float]], fps: float) -> float:
        if fps <= 0 or len(track_history) < 2:
            return 0.0

        world_points = [self.pixel_to_world(x, y) for x, y in track_history]
        distances = [
            hypot(current[0] - previous[0], current[1] - previous[1])
            for previous, current in zip(world_points, world_points[1:], strict=False)
        ]
        if not distances:
            return 0.0

        window = max(1, self.smoothing_window)
        smoothed_distances = distances[-window:]
        mean_distance_m = float(sum(smoothed_distances) / len(smoothed_distances))
        meters_per_second = mean_distance_m * fps
        return meters_per_second * 3.6

    def speed_kph_for_timed_points(
        self,
        track_history: Sequence[tuple[datetime, tuple[float, float]]],
    ) -> float:
        if len(track_history) < 2:
            return 0.0

        world_points = [
            (ts, self.pixel_to_world(point[0], point[1]))
            for ts, point in track_history
        ]
        segment_speeds_mps = [
            hypot(current_point[0] - previous_point[0], current_point[1] - previous_point[1])
            / elapsed_seconds
            for (previous_ts, previous_point), (current_ts, current_point) in zip(
                world_points,
                world_points[1:],
                strict=False,
            )
            if (elapsed_seconds := (current_ts - previous_ts).total_seconds()) > 0
        ]
        if not segment_speeds_mps:
            return 0.0

        window = max(1, self.smoothing_window)
        smoothed_speeds = segment_speeds_mps[-window:]
        meters_per_second = float(sum(smoothed_speeds) / len(smoothed_speeds))
        return meters_per_second * 3.6
