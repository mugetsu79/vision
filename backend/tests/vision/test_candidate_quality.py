from __future__ import annotations

from argus.vision.candidate_quality import CandidateQualityConfig, CandidateQualityGate
from argus.vision.profiles import resolve_scene_vision_profile
from argus.vision.track_lifecycle import LifecycleTrack
from argus.vision.types import Detection

FRAME_SHAPE = (720, 1280, 3)


def _person(
    *,
    confidence: float,
    bbox: tuple[float, float, float, float] = (100.0, 100.0, 260.0, 520.0),
    track_id: int | None = None,
) -> Detection:
    return Detection(
        class_name="person",
        confidence=confidence,
        bbox=bbox,
        track_id=track_id,
    )


def _car(
    *,
    confidence: float,
    bbox: tuple[float, float, float, float],
    track_id: int | None = None,
) -> Detection:
    return Detection(
        class_name="car",
        confidence=confidence,
        bbox=bbox,
        track_id=track_id,
    )


def _stable_person_track() -> LifecycleTrack:
    return LifecycleTrack(
        stable_track_id=1,
        source_track_id=10,
        state="active",
        detection=Detection(
            class_name="person",
            confidence=0.91,
            bbox=(100.0, 100.0, 260.0, 520.0),
            track_id=10,
        ),
        last_seen_age_ms=0,
    )


def test_high_confidence_new_person_candidate_passes() -> None:
    detection = _person(confidence=0.72)

    filtered, decisions = CandidateQualityGate().filter_detections(
        [detection],
        existing_tracks=[],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == [detection]
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (True, "new_track_high_confidence")
    ]


def test_low_confidence_new_person_candidate_is_rejected() -> None:
    detection = _person(confidence=0.44, bbox=(500.0, 120.0, 640.0, 520.0))

    filtered, decisions = CandidateQualityGate().filter_detections(
        [detection],
        existing_tracks=[],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == []
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (False, "new_track_low_confidence")
    ]


def test_low_confidence_detection_near_existing_track_passes_for_association() -> None:
    detection = _person(confidence=0.22, bbox=(112.0, 106.0, 272.0, 526.0), track_id=99)

    filtered, decisions = CandidateQualityGate().filter_detections(
        [detection],
        existing_tracks=[_stable_person_track()],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == [detection]
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (True, "existing_track_continuation")
    ]


def test_low_confidence_shrunken_continuation_is_not_rejected_as_fragment() -> None:
    detection = _person(confidence=0.22, bbox=(130.0, 150.0, 230.0, 430.0), track_id=99)

    filtered, decisions = CandidateQualityGate().filter_detections(
        [detection],
        existing_tracks=[_stable_person_track()],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == [detection]
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (True, "existing_track_continuation")
    ]


def test_nested_person_fragment_near_existing_track_is_rejected() -> None:
    detection = _person(confidence=0.48, bbox=(130.0, 150.0, 230.0, 430.0), track_id=99)

    filtered, decisions = CandidateQualityGate().filter_detections(
        [detection],
        existing_tracks=[_stable_person_track()],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == []
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (False, "duplicate_fragment")
    ]


def test_duplicate_fragment_suppression_can_be_disabled_by_profile() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "compute_tier": "cpu_low",
            "accuracy_mode": "fast",
            "candidate_quality": {
                "new_track_min_confidence": {
                    "person": 0.45,
                }
            },
        },
        has_homography=False,
    )
    detection = _person(confidence=0.48, bbox=(130.0, 150.0, 230.0, 430.0), track_id=99)

    filtered, decisions = CandidateQualityGate.from_profile_candidate_quality(
        resolved.candidate_quality
    ).filter_detections(
        [detection],
        existing_tracks=[_stable_person_track()],
        frame_shape=FRAME_SHAPE,
    )

    assert resolved.candidate_quality.duplicate_suppression_enabled is False
    assert filtered == [detection]
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (True, "new_track_high_confidence")
    ]


def test_duplicate_vehicle_fragment_uses_class_specific_thresholds() -> None:
    existing_track = LifecycleTrack(
        stable_track_id=2,
        source_track_id=20,
        state="active",
        detection=_car(
            confidence=0.89,
            bbox=(300.0, 220.0, 620.0, 480.0),
            track_id=20,
        ),
        last_seen_age_ms=0,
    )
    detection = _car(
        confidence=0.36,
        bbox=(360.0, 260.0, 540.0, 420.0),
        track_id=21,
    )

    filtered, decisions = CandidateQualityGate().filter_detections(
        [detection],
        existing_tracks=[existing_track],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == []
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (False, "duplicate_fragment")
    ]


def test_vehicle_family_uses_vehicle_threshold_when_exact_class_is_absent() -> None:
    gate = CandidateQualityGate(
        CandidateQualityConfig(new_track_min_confidence={"vehicle": 0.50, "default": 0.30})
    )
    detection = _car(confidence=0.45, bbox=(20.0, 20.0, 80.0, 80.0))

    filtered, decisions = gate.filter_detections(
        [detection],
        existing_tracks=[],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == []
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (False, "new_track_low_confidence")
    ]


def test_resolved_vehicle_profile_applies_threshold_to_concrete_vehicle_classes() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "compute_tier": "edge_advanced_jetson",
            "accuracy_mode": "maximum_accuracy",
            "object_domain": "vehicles",
        },
        has_homography=False,
    )
    detection = _car(confidence=0.42, bbox=(20.0, 20.0, 80.0, 80.0))

    filtered, decisions = CandidateQualityGate.from_profile_candidate_quality(
        resolved.candidate_quality
    ).filter_detections(
        [detection],
        existing_tracks=[],
        frame_shape=FRAME_SHAPE,
    )

    assert resolved.candidate_quality.new_track_min_confidence["car"] == 0.45
    assert filtered == []
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (False, "new_track_low_confidence")
    ]


def test_default_mixed_profile_applies_vehicle_threshold_to_concrete_vehicle_classes() -> None:
    resolved = resolve_scene_vision_profile({}, has_homography=False)
    detection = _car(confidence=0.36, bbox=(20.0, 20.0, 80.0, 80.0))

    filtered, decisions = CandidateQualityGate.from_profile_candidate_quality(
        resolved.candidate_quality
    ).filter_detections(
        [detection],
        existing_tracks=[],
        frame_shape=FRAME_SHAPE,
    )

    assert resolved.candidate_quality.new_track_min_confidence["car"] == 0.4
    assert filtered == []
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (False, "new_track_low_confidence")
    ]


def test_unknown_class_uses_default_threshold() -> None:
    low_score = Detection(
        class_name="traffic_cone",
        confidence=0.39,
        bbox=(20.0, 20.0, 50.0, 80.0),
    )
    high_score = low_score.with_updates(confidence=0.41, bbox=(80.0, 20.0, 110.0, 80.0))

    filtered, decisions = CandidateQualityGate().filter_detections(
        [low_score, high_score],
        existing_tracks=[],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == [high_score]
    assert [(decision.accepted, decision.reason) for decision in decisions] == [
        (False, "new_track_low_confidence"),
        (True, "new_track_high_confidence"),
    ]
