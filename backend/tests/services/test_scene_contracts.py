from __future__ import annotations

from argus.api.contracts import CameraSourceSettings, EvidenceRecordingPolicy


def test_camera_source_settings_support_usb_edge_source() -> None:
    source = CameraSourceSettings(kind="usb", uri="usb:///dev/video0", label="Dock Door USB")

    assert source.kind == "usb"
    assert source.uri == "usb:///dev/video0"
    assert source.label == "Dock Door USB"


def test_evidence_recording_policy_defaults_to_short_event_clip() -> None:
    policy = EvidenceRecordingPolicy()

    assert policy.enabled is True
    assert policy.mode == "event_clip"
    assert policy.pre_seconds == 4
    assert policy.post_seconds == 8
    assert policy.fps == 10
    assert policy.max_duration_seconds == 15
    assert policy.storage_profile == "central"
