from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status

from argus.api.contracts import CameraSourceSettings
from argus.core.logging import redact_url_secrets
from argus.models.enums import CameraSourceKind, ProcessingMode


@dataclass(frozen=True, slots=True)
class NormalizedCameraSource:
    kind: CameraSourceKind
    uri: str
    capture_uri: str
    redacted_uri: str
    label: str | None = None


def normalize_camera_source(source: CameraSourceSettings) -> NormalizedCameraSource:
    if source.kind is CameraSourceKind.USB:
        path = source.uri.removeprefix("usb://")
        if not path.startswith("/dev/video"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="USB sources must use usb:///dev/videoN.",
            )
        return NormalizedCameraSource(
            kind=source.kind,
            uri=source.uri,
            capture_uri=path,
            redacted_uri="usb://***",
            label=source.label,
        )
    if source.kind is CameraSourceKind.JETSON_CSI:
        return NormalizedCameraSource(
            kind=source.kind,
            uri=source.uri,
            capture_uri=source.uri,
            redacted_uri="csi://***",
            label=source.label,
        )
    return NormalizedCameraSource(
        kind=source.kind,
        uri=source.uri,
        capture_uri=source.uri,
        redacted_uri=redact_url_secrets(source.uri),
        label=source.label,
    )


def redact_camera_source_uri(source: NormalizedCameraSource | CameraSourceSettings) -> str:
    normalized = (
        source
        if isinstance(source, NormalizedCameraSource)
        else normalize_camera_source(source)
    )
    return normalized.redacted_uri


def validate_camera_source_assignment(
    *,
    source: CameraSourceSettings,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> None:
    if source.kind is CameraSourceKind.USB and (
        processing_mode is not ProcessingMode.EDGE or edge_node_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="USB sources require edge processing and an edge node.",
        )
