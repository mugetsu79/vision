from __future__ import annotations

from argus.models.enums import (
    CameraSourceKind,
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)


def test_evidence_enums_expose_accountability_values() -> None:
    assert CameraSourceKind.USB.value == "usb"
    assert EvidenceArtifactKind.EVENT_CLIP.value == "event_clip"
    assert EvidenceArtifactStatus.LOCAL_ONLY.value == "local_only"
    assert EvidenceStorageProvider.LOCAL_FILESYSTEM.value == "local_filesystem"
    assert EvidenceStorageScope.EDGE.value == "edge"
    assert EvidenceLedgerAction.INCIDENT_TRIGGERED.value == "incident.triggered"
