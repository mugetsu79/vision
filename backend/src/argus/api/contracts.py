from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from argus.core.security import AuthenticatedUser
from argus.inference.publisher import TelemetryFrame
from argus.models.enums import ModelFormat, ModelTask, ProcessingMode, TrackerType


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    tz: str = Field(default="UTC", min_length=1, max_length=64)
    geo_point: dict[str, float] | None = None


class SiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    tz: str | None = Field(default=None, min_length=1, max_length=64)
    geo_point: dict[str, float] | None = None


class SiteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None = None
    tz: str
    geo_point: dict[str, float] | None = None
    created_at: datetime


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    task: ModelTask
    path: str = Field(min_length=1)
    format: ModelFormat
    classes: list[str] = Field(min_length=1)
    input_shape: dict[str, int]
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0)
    license: str | None = Field(default=None, max_length=255)


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    version: str | None = Field(default=None, min_length=1, max_length=64)
    task: ModelTask | None = None
    path: str | None = Field(default=None, min_length=1)
    format: ModelFormat | None = None
    classes: list[str] | None = Field(default=None, min_length=1)
    input_shape: dict[str, int] | None = None
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    size_bytes: int | None = Field(default=None, gt=0)
    license: str | None = Field(default=None, max_length=255)


class ModelResponse(BaseModel):
    id: UUID
    name: str
    version: str
    task: ModelTask
    path: str
    format: ModelFormat
    classes: list[str]
    input_shape: dict[str, int]
    sha256: str
    size_bytes: int
    license: str | None = None


class HomographyPayload(BaseModel):
    src: list[list[float]]
    dst: list[list[float]]
    ref_distance_m: float = Field(gt=0)

    @field_validator("src", "dst")
    @classmethod
    def validate_four_points(cls, value: list[list[float]]) -> list[list[float]]:
        if len(value) != 4:
            raise ValueError("Homography requires exactly four points.")
        for point in value:
            if len(point) != 2:
                raise ValueError("Each homography point must contain exactly two coordinates.")
        return value


class PrivacySettings(BaseModel):
    blur_faces: bool = True
    blur_plates: bool = True
    method: Literal["gaussian", "pixelate"] = "gaussian"
    strength: int = Field(default=7, ge=1, le=100)


class CameraCreate(BaseModel):
    site_id: UUID
    name: str = Field(min_length=1, max_length=255)
    rtsp_url: str = Field(min_length=1)
    processing_mode: ProcessingMode
    primary_model_id: UUID
    secondary_model_id: UUID | None = None
    tracker_type: TrackerType
    active_classes: list[str] = Field(default_factory=list)
    attribute_rules: list[dict[str, Any]] = Field(default_factory=list)
    zones: list[dict[str, Any]] = Field(default_factory=list)
    homography: HomographyPayload
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    frame_skip: int = Field(default=1, ge=1)
    fps_cap: int = Field(default=25, ge=1)


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    rtsp_url: str | None = Field(default=None, min_length=1)
    processing_mode: ProcessingMode | None = None
    primary_model_id: UUID | None = None
    secondary_model_id: UUID | None = None
    tracker_type: TrackerType | None = None
    active_classes: list[str] | None = None
    attribute_rules: list[dict[str, Any]] | None = None
    zones: list[dict[str, Any]] | None = None
    homography: HomographyPayload | None = None
    privacy: PrivacySettings | None = None
    frame_skip: int | None = Field(default=None, ge=1)
    fps_cap: int | None = Field(default=None, ge=1)


class CameraResponse(BaseModel):
    id: UUID
    site_id: UUID
    edge_node_id: UUID | None = None
    name: str
    rtsp_url_masked: str
    processing_mode: ProcessingMode
    primary_model_id: UUID
    secondary_model_id: UUID | None = None
    tracker_type: TrackerType
    active_classes: list[str]
    attribute_rules: list[dict[str, Any]]
    zones: list[dict[str, Any]]
    homography: HomographyPayload
    privacy: PrivacySettings
    frame_skip: int
    fps_cap: int
    created_at: datetime
    updated_at: datetime


class EdgeRegisterRequest(BaseModel):
    site_id: UUID
    hostname: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)


class EdgeRegisterResponse(BaseModel):
    edge_node_id: UUID
    api_key: str
    nats_nkey_seed: str
    subjects: list[str]
    mediamtx_url: str
    mediamtx_username: str | None = None
    mediamtx_password: str | None = None
    overlay_network_hints: dict[str, Any] = Field(default_factory=dict)


class EdgeHeartbeatRequest(BaseModel):
    node_id: UUID
    version: str = Field(min_length=1, max_length=64)
    cameras: int = Field(ge=0)


class EdgeHeartbeatResponse(BaseModel):
    status: str
    received_at: datetime


class QueryRequest(BaseModel):
    prompt: str = Field(min_length=1)
    camera_ids: list[UUID] = Field(min_length=1)


class QueryResponse(BaseModel):
    resolved_classes: list[str]
    provider: str
    model: str
    latency_ms: int
    camera_ids: list[UUID]


class HistoryPoint(BaseModel):
    bucket: datetime
    camera_id: UUID | None = None
    class_name: str
    event_count: int
    granularity: str


class IncidentResponse(BaseModel):
    id: UUID
    camera_id: UUID
    ts: datetime
    type: str
    payload: dict[str, Any]
    snapshot_url: str | None = None


class StreamOfferRequest(BaseModel):
    sdp_offer: str = Field(min_length=1)


class StreamOfferResponse(BaseModel):
    camera_id: UUID
    sdp_answer: str


class TelemetryEnvelope(BaseModel):
    events: list[TelemetryFrame] = Field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ExportArtifact:
    filename: str
    media_type: str
    content: bytes


@dataclass(slots=True, frozen=True)
class TenantContext:
    tenant_id: UUID
    tenant_slug: str
    user: AuthenticatedUser
