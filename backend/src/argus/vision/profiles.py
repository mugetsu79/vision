from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from argus.api.contracts import SceneVisionProfile
from argus.models.enums import TrackerType

VerifierMode = Literal["none", "suspicious_only"]


@dataclass(frozen=True, slots=True)
class ResolvedMotionMetrics:
    speed_enabled: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedCandidateQuality:
    new_track_min_confidence: dict[str, float] = field(default_factory=dict)
    duplicate_suppression_enabled: bool = True
    memory_frames: int = 24


@dataclass(frozen=True, slots=True)
class ResolvedTrackerProfile:
    tracker_type: TrackerType = TrackerType.BOTSORT
    with_reid: bool = False
    appearance_ready: bool = False
    new_track_min_hits: int = 2


@dataclass(frozen=True, slots=True)
class ResolvedVerifierProfile:
    mode: VerifierMode = "none"


@dataclass(frozen=True, slots=True)
class ResolvedSceneVisionProfile:
    compute_tier: str
    accuracy_mode: str
    scene_difficulty: str
    object_domain: str
    motion_metrics: ResolvedMotionMetrics
    candidate_quality: ResolvedCandidateQuality
    tracker: ResolvedTrackerProfile
    verifier: ResolvedVerifierProfile


def resolve_scene_vision_profile(
    profile: Mapping[str, object],
    *,
    has_homography: bool,
) -> ResolvedSceneVisionProfile:
    requested = SceneVisionProfile.model_validate(dict(profile))
    if requested.motion_metrics.speed_enabled and not has_homography:
        raise ValueError("Homography is required when speed metrics are enabled.")

    accuracy_mode = requested.accuracy_mode
    compute_tier = requested.compute_tier

    speed_enabled = requested.motion_metrics.speed_enabled
    verifier_mode: VerifierMode = "none"
    duplicate_suppression_enabled = True
    memory_frames = 24
    new_track_min_hits = 2
    appearance_ready = False
    new_track_min_confidence = _base_new_track_confidence(requested.object_domain)

    if accuracy_mode == "fast" and compute_tier == "cpu_low":
        speed_enabled = False
        duplicate_suppression_enabled = False
        memory_frames = 8
        new_track_min_hits = 1
        new_track_min_confidence.update(_vehicle_thresholds(0.35) | {"person": 0.35})
    elif accuracy_mode == "maximum_accuracy" and compute_tier == "edge_advanced_jetson":
        appearance_ready = True
        memory_frames = 36
        new_track_min_hits = 3
        new_track_min_confidence.update(_vehicle_thresholds(0.45) | {"person": 0.45})
    elif accuracy_mode == "maximum_accuracy" and compute_tier == "central_gpu":
        verifier_mode = "suspicious_only"
        appearance_ready = True
        memory_frames = 36
        new_track_min_hits = 3
        new_track_min_confidence.update(_vehicle_thresholds(0.45) | {"person": 0.45})
    elif accuracy_mode == "open_vocabulary":
        speed_enabled = requested.motion_metrics.speed_enabled
        new_track_min_confidence.update(
            _vehicle_thresholds(0.5) | {"person": 0.5, "default": 0.5}
        )

    quality_overrides = requested.candidate_quality
    if isinstance(quality_overrides.get("new_track_min_confidence"), dict):
        for class_name, value in quality_overrides["new_track_min_confidence"].items():
            if isinstance(class_name, str) and isinstance(value, int | float):
                new_track_min_confidence[class_name] = float(value)
    if isinstance(quality_overrides.get("duplicate_suppression_enabled"), bool):
        duplicate_suppression_enabled = bool(
            quality_overrides["duplicate_suppression_enabled"]
        )
    if isinstance(quality_overrides.get("memory_frames"), int):
        memory_frames = max(1, int(quality_overrides["memory_frames"]))

    tracker_overrides = requested.tracker_profile
    if isinstance(tracker_overrides.get("new_track_min_hits"), int):
        new_track_min_hits = max(1, int(tracker_overrides["new_track_min_hits"]))

    verifier_overrides = requested.verifier_profile
    requested_verifier_mode = verifier_overrides.get("mode")
    if requested_verifier_mode in {"none", "suspicious_only"}:
        verifier_mode = requested_verifier_mode

    return ResolvedSceneVisionProfile(
        compute_tier=compute_tier,
        accuracy_mode=accuracy_mode,
        scene_difficulty=requested.scene_difficulty,
        object_domain=requested.object_domain,
        motion_metrics=ResolvedMotionMetrics(speed_enabled=speed_enabled),
        candidate_quality=ResolvedCandidateQuality(
            new_track_min_confidence=new_track_min_confidence,
            duplicate_suppression_enabled=duplicate_suppression_enabled,
            memory_frames=memory_frames,
        ),
        tracker=ResolvedTrackerProfile(
            tracker_type=TrackerType.BOTSORT,
            with_reid=False,
            appearance_ready=appearance_ready,
            new_track_min_hits=new_track_min_hits,
        ),
        verifier=ResolvedVerifierProfile(mode=verifier_mode),
    )


def _base_new_track_confidence(object_domain: str) -> dict[str, float]:
    if object_domain == "people":
        return {"person": 0.4, "default": 0.4}
    if object_domain == "vehicles":
        return {"vehicle": 0.4, "car": 0.4, "truck": 0.4, "bus": 0.4, "default": 0.4}
    return _vehicle_thresholds(0.4) | {"person": 0.4, "default": 0.4}


def _vehicle_thresholds(value: float) -> dict[str, float]:
    return {
        "vehicle": value,
        "car": value,
        "truck": value,
        "bus": value,
        "forklift": value,
    }
