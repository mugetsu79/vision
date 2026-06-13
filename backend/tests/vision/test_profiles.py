from __future__ import annotations

import pytest
from pydantic import ValidationError

from argus.api.contracts import SceneVisionProfile
from argus.models.enums import TrackerType
from argus.vision.profiles import resolve_scene_vision_profile


def test_balanced_profile_resolves_botsort_without_reid() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "accuracy_mode": "balanced",
            "compute_tier": "edge_standard",
            "scene_difficulty": "cluttered",
            "object_domain": "people",
        },
        has_homography=False,
    )

    assert resolved.accuracy_mode == "balanced"
    assert resolved.compute_tier == "edge_standard"
    assert resolved.tracker.tracker_type is TrackerType.BOTSORT
    assert resolved.tracker.with_reid is False
    assert resolved.candidate_quality.duplicate_suppression_enabled is True


def test_cpu_low_fast_profile_disables_verifier_and_speed_by_default() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "accuracy_mode": "fast",
            "compute_tier": "cpu_low",
            "scene_difficulty": "open",
            "object_domain": "people",
        },
        has_homography=False,
    )

    assert resolved.compute_tier == "cpu_low"
    assert resolved.motion_metrics.speed_enabled is False
    assert resolved.tracker.with_reid is False
    assert resolved.verifier.mode == "none"
    assert resolved.candidate_quality.memory_frames <= 12


def test_jetson_advanced_profile_allows_maximum_accuracy_without_deepstream_runtime() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "accuracy_mode": "maximum_accuracy",
            "compute_tier": "edge_advanced_jetson",
            "scene_difficulty": "crowded",
            "object_domain": "people",
        },
        has_homography=False,
    )

    assert resolved.compute_tier == "edge_advanced_jetson"
    assert resolved.tracker.tracker_type is TrackerType.BOTSORT
    assert resolved.tracker.with_reid is False
    assert resolved.tracker.appearance_ready is True
    assert resolved.candidate_quality.new_track_min_confidence["person"] >= 0.45
    assert resolved.verifier.mode in {"none", "suspicious_only"}


def test_central_people_profile_lowers_person_association_confidence_below_display() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "accuracy_mode": "maximum_accuracy",
            "compute_tier": "central_gpu",
            "object_domain": "people",
        },
        has_homography=False,
    )

    assert resolved.candidate_quality.display_min_confidence["person"] == 0.45
    assert resolved.candidate_quality.association_min_confidence["person"] < 0.45


def test_central_people_balanced_profile_uses_tracking_memory_for_intermittent_detections() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "accuracy_mode": "balanced",
            "compute_tier": "central_gpu",
            "scene_difficulty": "cluttered",
            "object_domain": "people",
        },
        has_homography=False,
    )

    assert resolved.candidate_quality.display_min_confidence["person"] == 0.4
    assert resolved.candidate_quality.association_min_confidence["person"] < 0.4
    assert resolved.candidate_quality.memory_frames >= 36
    assert resolved.tracker.coast_seconds >= 3.5


def test_edge_mixed_profile_preserves_class_specific_vehicle_confidence() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "accuracy_mode": "balanced",
            "compute_tier": "edge_standard",
            "object_domain": "mixed",
        },
        has_homography=False,
    )

    assert resolved.candidate_quality.display_min_confidence["car"] == 0.4
    assert resolved.candidate_quality.association_min_confidence["car"] == 0.4
    assert resolved.candidate_quality.display_min_confidence["forklift"] == 0.4


def test_tracker_profile_resolves_explicit_coast_seconds() -> None:
    explicit = resolve_scene_vision_profile(
        {"tracker_profile": {"coast_seconds": 3.25}},
        has_homography=False,
    )

    assert explicit.tracker.coast_seconds == 3.25


def test_tracker_profile_rejects_out_of_range_coast_seconds() -> None:
    with pytest.raises(ValidationError):
        SceneVisionProfile.model_validate({"tracker_profile": {"coast_seconds": 0.2}})
    with pytest.raises(ValidationError):
        SceneVisionProfile.model_validate({"tracker_profile": {"coast_seconds": 20.0}})


def test_tracker_profile_resolves_gmc_method_override() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "accuracy_mode": "balanced",
            "compute_tier": "edge_standard",
            "tracker_profile": {"gmc_method": "sparseOptFlow"},
        },
        has_homography=False,
    )

    assert resolved.tracker.gmc_method == "sparseOptFlow"


def test_tracker_profile_rejects_unknown_gmc_method() -> None:
    with pytest.raises(ValidationError):
        SceneVisionProfile.model_validate({"tracker_profile": {"gmc_method": "ecc"}})


def test_speed_enabled_requires_homography() -> None:
    with pytest.raises(ValueError, match="Homography is required when speed metrics are enabled."):
        resolve_scene_vision_profile(
            {
                "accuracy_mode": "balanced",
                "compute_tier": "edge_standard",
                "motion_metrics": {"speed_enabled": True},
            },
            has_homography=False,
        )
