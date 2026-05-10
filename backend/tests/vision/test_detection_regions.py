from __future__ import annotations

from argus.vision.detection_regions import DetectionRegionPolicy
from argus.vision.types import Detection


def _region(
    *,
    region_id: str,
    mode: str,
    polygon: list[list[float]],
    class_names: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": region_id,
        "mode": mode,
        "polygon": polygon,
        "class_names": class_names or [],
    }


def test_no_regions_allows_detection() -> None:
    detection = Detection(class_name="person", confidence=0.9, bbox=(10.0, 10.0, 30.0, 50.0))
    policy = DetectionRegionPolicy([])

    allowed, decisions = policy.filter_detections([detection])

    assert allowed == [detection]
    assert len(decisions) == 1
    assert decisions[0].allowed is True


def test_include_region_allows_candidate_inside() -> None:
    detection = Detection(class_name="car", confidence=0.9, bbox=(10.0, 10.0, 30.0, 30.0))
    policy = DetectionRegionPolicy(
        [
            _region(
                region_id="driveway",
                mode="include",
                polygon=[[0, 0], [40, 0], [40, 40], [0, 40]],
            )
        ]
    )

    allowed, decisions = policy.filter_detections([detection])

    assert allowed == [detection]
    assert decisions[0].allowed is True
    assert decisions[0].include_region_ids == ["driveway"]


def test_include_region_rejects_candidate_outside() -> None:
    detection = Detection(class_name="car", confidence=0.9, bbox=(50.0, 50.0, 70.0, 70.0))
    policy = DetectionRegionPolicy(
        [
            _region(
                region_id="driveway",
                mode="include",
                polygon=[[0, 0], [40, 0], [40, 40], [0, 40]],
            )
        ]
    )

    allowed, decisions = policy.filter_detections([detection])

    assert allowed == []
    assert decisions[0].allowed is False
    assert decisions[0].reason == "outside_include_region"


def test_exclusion_region_overrides_include() -> None:
    detection = Detection(class_name="person", confidence=0.9, bbox=(10.0, 10.0, 30.0, 50.0))
    policy = DetectionRegionPolicy(
        [
            _region(
                region_id="floor",
                mode="include",
                polygon=[[0, 0], [100, 0], [100, 100], [0, 100]],
            ),
            _region(
                region_id="doorway",
                mode="exclude",
                polygon=[[0, 40], [50, 40], [50, 60], [0, 60]],
            ),
        ]
    )

    allowed, decisions = policy.filter_detections([detection])

    assert allowed == []
    assert decisions[0].allowed is False
    assert decisions[0].reason == "inside_exclusion_region"
    assert decisions[0].exclude_region_ids == ["doorway"]


def test_class_scoped_region_only_applies_to_matching_class() -> None:
    detection = Detection(class_name="car", confidence=0.9, bbox=(60.0, 60.0, 80.0, 80.0))
    policy = DetectionRegionPolicy(
        [
            _region(
                region_id="people-only",
                mode="include",
                polygon=[[0, 0], [40, 0], [40, 40], [0, 40]],
                class_names=["person"],
            )
        ]
    )

    allowed, decisions = policy.filter_detections([detection])

    assert allowed == [detection]
    assert decisions[0].allowed is True
    assert decisions[0].include_region_ids == []


def test_person_uses_bottom_center_anchor() -> None:
    detection = Detection(class_name="person", confidence=0.9, bbox=(10.0, 10.0, 30.0, 70.0))
    policy = DetectionRegionPolicy(
        [_region(region_id="feet", mode="include", polygon=[[0, 60], [40, 60], [40, 80], [0, 80]])]
    )

    allowed, decisions = policy.filter_detections([detection])

    assert allowed == [detection]
    assert decisions[0].anchor == (20.0, 70.0)


def test_general_object_uses_center_anchor() -> None:
    detection = Detection(class_name="backpack", confidence=0.9, bbox=(10.0, 10.0, 30.0, 70.0))
    policy = DetectionRegionPolicy(
        [
            _region(
                region_id="middle",
                mode="include",
                polygon=[[0, 30], [40, 30], [40, 50], [0, 50]],
            )
        ]
    )

    allowed, decisions = policy.filter_detections([detection])

    assert allowed == [detection]
    assert decisions[0].anchor == (20.0, 40.0)
