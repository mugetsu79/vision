from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from argus.models.enums import TrackerType
from argus.vision.types import Detection

TrackerSceneProfile = Literal["efficient", "difficult"]


@dataclass(slots=True)
class TrackerConfig:
    tracker_type: TrackerType
    scene_profile: TrackerSceneProfile = "efficient"
    frame_rate: int = 30
    track_high_thresh: float = 0.25
    track_low_thresh: float = 0.1
    new_track_thresh: float = 0.35
    match_thresh: float = 0.8
    track_buffer: int = 90
    fuse_score: bool = True
    with_reid: bool = False
    model: str = "auto"
    proximity_thresh: float = 0.5
    appearance_thresh: float = 0.25
    # Traffic cameras are fixed; frame-to-frame GMC feature matching is costly and noisy.
    gmc_method: str = "none"

    @classmethod
    def for_scene_profile(
        cls,
        scene_profile: TrackerSceneProfile = "efficient",
        *,
        tracker_type: TrackerType | None = None,
        frame_rate: int = 30,
    ) -> TrackerConfig:
        if scene_profile == "efficient":
            return cls(
                tracker_type=tracker_type or TrackerType.BOTSORT,
                scene_profile=scene_profile,
                frame_rate=frame_rate,
            )

        if tracker_type is not None and tracker_type is not TrackerType.BOTSORT:
            raise ValueError("difficult scene profile requires botsort tracker")

        return cls(
            tracker_type=TrackerType.BOTSORT,
            scene_profile=scene_profile,
            frame_rate=frame_rate,
            match_thresh=0.85,
            track_buffer=150,
            with_reid=False,
            proximity_thresh=0.5,
            appearance_thresh=0.8,
            model="auto",
        )

    def to_namespace(self) -> SimpleNamespace:
        return SimpleNamespace(
            track_high_thresh=self.track_high_thresh,
            track_low_thresh=self.track_low_thresh,
            new_track_thresh=self.new_track_thresh,
            match_thresh=self.match_thresh,
            track_buffer=self.track_buffer,
            fuse_score=self.fuse_score,
            with_reid=self.with_reid,
            model=self.model,
            proximity_thresh=self.proximity_thresh,
            appearance_thresh=self.appearance_thresh,
            gmc_method=self.gmc_method,
        )


class TrackerBackend(Protocol):
    def update(
        self,
        results: _TrackerResults,
        img: NDArray[np.uint8] | None = None,
        feats: NDArray[np.float32] | None = None,
    ) -> list[list[float]] | NDArray[np.float32]: ...


TrackerBackendFactory = Callable[[str, TrackerConfig], TrackerBackend]


class _TrackerResults:
    def __init__(self, detections: list[Detection]) -> None:
        self._detections = detections
        self.xyxy = np.asarray(
            [detection.bbox for detection in detections],
            dtype=np.float32,
        ).reshape((-1, 4))
        self.conf = np.asarray([detection.confidence for detection in detections], dtype=np.float32)
        self.cls = np.asarray(
            [
                detection.class_id if detection.class_id is not None else -1
                for detection in detections
            ],
            dtype=np.float32,
        )

    @property
    def xywh(self) -> NDArray[np.float32]:
        widths = self.xyxy[:, 2] - self.xyxy[:, 0]
        heights = self.xyxy[:, 3] - self.xyxy[:, 1]
        center_x = self.xyxy[:, 0] + widths / 2.0
        center_y = self.xyxy[:, 1] + heights / 2.0
        return np.stack((center_x, center_y, widths, heights), axis=1)

    def __len__(self) -> int:
        return len(self._detections)

    def __getitem__(self, item: Any) -> _TrackerResults:
        if isinstance(item, np.ndarray):
            if item.dtype == np.bool_:
                indices = np.flatnonzero(item).tolist()
            else:
                indices = item.astype(int).tolist()
        elif isinstance(item, slice):
            indices = list(range(len(self._detections)))[item]
        elif isinstance(item, int):
            indices = [item]
        else:
            indices = list(item)
        return _TrackerResults([self._detections[index] for index in indices])


class UltralyticsTrackerAdapter:
    def __init__(self, name: str, backend: TrackerBackend) -> None:
        self.name = name
        self.backend = backend

    def update(
        self,
        detections: list[Detection],
        frame: NDArray[np.uint8] | None = None,
    ) -> list[Detection]:
        tracker_results = _TrackerResults(detections)
        raw_tracks = self.backend.update(tracker_results, img=frame)
        if isinstance(raw_tracks, np.ndarray):
            rows = raw_tracks.tolist()
        else:
            rows = raw_tracks

        tracked: list[Detection] = []
        for row in rows:
            if len(row) < 7:
                continue
            x1, y1, x2, y2 = [float(value) for value in row[:4]]
            track_id = int(row[4])
            confidence = float(row[5])
            class_id = int(row[6])
            detection_index = int(row[7]) if len(row) >= 8 else None
            if detection_index is not None and 0 <= detection_index < len(detections):
                original = detections[detection_index]
                class_name = original.class_name
                attributes = dict(original.attributes)
                zone_id = original.zone_id
            else:
                class_name = next(
                    (
                        detection.class_name
                        for detection in detections
                        if detection.class_id == class_id
                    ),
                    str(class_id),
                )
                attributes = {}
                zone_id = None
            tracked.append(
                Detection(
                    class_name=class_name,
                    class_id=class_id,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                    track_id=track_id,
                    attributes=attributes,
                    zone_id=zone_id,
                )
            )
        return tracked


def create_tracker(
    config: TrackerConfig,
    *,
    backend_factory: TrackerBackendFactory | None = None,
) -> UltralyticsTrackerAdapter:
    tracker_name = config.tracker_type.value
    backend = (backend_factory or _default_backend_factory)(tracker_name, config)
    return UltralyticsTrackerAdapter(name=tracker_name, backend=backend)


def _default_backend_factory(tracker_name: str, config: TrackerConfig) -> TrackerBackend:
    if tracker_name == TrackerType.BOTSORT.value:
        from ultralytics.trackers.bot_sort import BOTSORT

        return BOTSORT(config.to_namespace(), frame_rate=config.frame_rate)

    if tracker_name == TrackerType.BYTETRACK.value:
        from ultralytics.trackers.byte_tracker import BYTETracker

        return BYTETracker(config.to_namespace(), frame_rate=config.frame_rate)

    raise ValueError(f"Unsupported tracker type: {tracker_name}")
