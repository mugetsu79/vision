from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import CameraSourceSettings
from argus.models.enums import CameraSourceKind, ProcessingMode
from argus.services.camera_sources import (
    normalize_camera_source,
    redact_camera_source_uri,
    validate_camera_source_assignment,
)


def test_normalizes_usb_source_to_edge_device_path() -> None:
    source = normalize_camera_source(
        CameraSourceSettings(kind=CameraSourceKind.USB, uri="usb:///dev/video0")
    )

    assert source.kind is CameraSourceKind.USB
    assert source.uri == "usb:///dev/video0"
    assert source.capture_uri == "/dev/video0"
    assert redact_camera_source_uri(source) == "usb://***"


def test_usb_source_requires_edge_processing_and_edge_node() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_camera_source_assignment(
            source=CameraSourceSettings(kind=CameraSourceKind.USB, uri="usb:///dev/video0"),
            processing_mode=ProcessingMode.CENTRAL,
            edge_node_id=None,
        )

    assert exc.value.status_code == 422
    assert "USB sources require edge processing and an edge node" in str(exc.value.detail)


def test_usb_source_accepts_edge_processing_with_edge_node() -> None:
    validate_camera_source_assignment(
        source=CameraSourceSettings(kind=CameraSourceKind.USB, uri="usb:///dev/video0"),
        processing_mode=ProcessingMode.EDGE,
        edge_node_id=uuid4(),
    )
