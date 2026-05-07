from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from argus.api.contracts import (
    CameraCreate,
    CameraResponse,
    CameraUpdate,
    EdgeHeartbeatRequest,
    EdgeHeartbeatResponse,
    EdgeRegisterRequest,
    EdgeRegisterResponse,
    ExportArtifact,
    HistoryPoint,
    IncidentResponse,
    ModelCreate,
    ModelResponse,
    ModelUpdate,
    QueryRequest,
    QueryResponse,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
    StreamOfferRequest,
    StreamOfferResponse,
    TelemetryEnvelope,
    TenantContext,
    WorkerConfigResponse,
)
from argus.core.config import Settings
from argus.core.security import (
    AuthenticatedUser,
    get_current_user,
    get_current_websocket_user,
)
from argus.inference.publisher import TelemetryFrame, TelemetryTrack
from argus.main import create_app
from argus.models.enums import (
    DetectorCapability,
    IncidentReviewStatus,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    RoleEnum,
    TrackerType,
)
from argus.streaming.mediamtx import PublishProfile, StreamMode


def _sample_user(
    *,
    role: RoleEnum = RoleEnum.ADMIN,
    tenant_id: UUID | None = None,
) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="user-1",
        email="admin@argus.local",
        role=role,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=role is RoleEnum.SUPERADMIN,
        tenant_context=str(tenant_id or uuid4()),
        claims={},
    )


def _tenant_context(user: AuthenticatedUser) -> TenantContext:
    return TenantContext(
        tenant_id=UUID(str(user.tenant_context)),
        tenant_slug=user.realm,
        user=user,
    )


def _site_response(tenant_id: UUID) -> SiteResponse:
    return SiteResponse(
        id=uuid4(),
        tenant_id=tenant_id,
        name="HQ",
        description="Main site",
        tz="Europe/Zurich",
        geo_point={"lat": 47.3769, "lon": 8.5417},
        created_at=datetime.now(tz=UTC),
    )


def _model_response(task: ModelTask = ModelTask.DETECT) -> ModelResponse:
    return ModelResponse(
        id=uuid4(),
        name="Argus YOLO",
        version="1.0.0",
        task=task,
        path="/models/argus.onnx",
        format=ModelFormat.ONNX,
        classes=["bus", "car", "person", "truck"],
        input_shape={"h": 640, "w": 640, "c": 3},
        sha256="a" * 64,
        size_bytes=123456,
        license="Apache-2.0",
    )


def _camera_payload(site_id: UUID, primary_model_id: UUID) -> CameraCreate:
    return CameraCreate(
        site_id=site_id,
        name="Dock Camera",
        rtsp_url="rtsp://example.local/live",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=primary_model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["bus", "truck"],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": False,
            "method": "gaussian",
            "strength": 7,
        },
        frame_skip=1,
        fps_cap=25,
    )


def _camera_response(payload: CameraCreate) -> CameraResponse:
    return CameraResponse(
        id=uuid4(),
        site_id=payload.site_id,
        edge_node_id=None,
        name=payload.name,
        rtsp_url_masked="rtsp://***",
        processing_mode=payload.processing_mode,
        primary_model_id=payload.primary_model_id,
        secondary_model_id=payload.secondary_model_id,
        tracker_type=payload.tracker_type,
        active_classes=payload.active_classes,
        runtime_vocabulary=payload.runtime_vocabulary,
        attribute_rules=payload.attribute_rules,
        zones=payload.zones,
        homography=payload.homography,
        privacy=payload.privacy,
        browser_delivery=payload.browser_delivery,
        frame_skip=payload.frame_skip,
        fps_cap=payload.fps_cap,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


class FakeTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        if explicit_tenant_id is not None:
            return TenantContext(
                tenant_id=explicit_tenant_id,
                tenant_slug=self.context.tenant_slug,
                user=user,
            )
        return TenantContext(
            tenant_id=self.context.tenant_id,
            tenant_slug=self.context.tenant_slug,
            user=user,
        )


class FakeSiteService:
    def __init__(self, tenant_id: UUID) -> None:
        self.sites: dict[UUID, SiteResponse] = {}
        self.tenant_id = tenant_id

    async def list_sites(self, context: TenantContext) -> list[SiteResponse]:
        return list(self.sites.values())

    async def get_site(self, context: TenantContext, site_id: UUID) -> SiteResponse:
        return self.sites[site_id]

    async def create_site(self, context: TenantContext, payload: SiteCreate) -> SiteResponse:
        site = SiteResponse(
            id=uuid4(),
            tenant_id=context.tenant_id,
            name=payload.name,
            description=payload.description,
            tz=payload.tz,
            geo_point=payload.geo_point,
            created_at=datetime.now(tz=UTC),
        )
        self.sites[site.id] = site
        return site

    async def update_site(
        self,
        context: TenantContext,
        site_id: UUID,
        payload: SiteUpdate,
    ) -> SiteResponse:
        existing = self.sites[site_id]
        updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
        self.sites[site_id] = updated
        return updated

    async def delete_site(self, context: TenantContext, site_id: UUID) -> None:
        self.sites.pop(site_id)


class FakeModelService:
    def __init__(self) -> None:
        self.models: dict[UUID, ModelResponse] = {}

    async def list_models(self) -> list[ModelResponse]:
        return list(self.models.values())

    async def create_model(self, payload: ModelCreate) -> ModelResponse:
        if payload.capability is DetectorCapability.OPEN_VOCAB:
            if payload.capability_config.supports_runtime_vocabulary_updates is not True:
                raise HTTPException(
                    status_code=422,
                    detail="open_vocab models must declare runtime vocabulary support.",
                )
            classes = list(payload.classes or [])
        else:
            classes = self._resolve_classes(
                path=payload.path,
                format=payload.format,
                declared_classes=payload.classes,
            )
        model = ModelResponse(
            id=uuid4(),
            name=payload.name,
            version=payload.version,
            task=payload.task,
            path=payload.path,
            format=payload.format,
            capability=payload.capability,
            capability_config=payload.capability_config,
            classes=classes,
            input_shape=payload.input_shape,
            sha256=payload.sha256,
            size_bytes=payload.size_bytes,
            license=payload.license,
        )
        self.models[model.id] = model
        return model

    async def update_model(self, model_id: UUID, payload: ModelUpdate) -> ModelResponse:
        existing = self.models[model_id]
        update_data = payload.model_dump(exclude_unset=True, mode="python")
        if any(
            field_name in update_data
            for field_name in {"path", "format", "classes", "capability", "capability_config"}
        ):
            capability = update_data.get("capability", existing.capability)
            resolved_format = update_data.get("format", existing.format)
            if capability is DetectorCapability.OPEN_VOCAB:
                config = update_data.get("capability_config", existing.capability_config)
                if config["supports_runtime_vocabulary_updates"] is not True:
                    raise HTTPException(
                        status_code=422,
                        detail="open_vocab models must declare runtime vocabulary support.",
                    )
                update_data["classes"] = list(update_data.get("classes", existing.classes))
            else:
                update_data["classes"] = self._resolve_classes(
                    path=str(update_data.get("path", existing.path)),
                    format=resolved_format,
                    declared_classes=(
                        update_data["classes"]
                        if "classes" in update_data
                        else None
                        if resolved_format is ModelFormat.ONNX
                        else existing.classes
                    ),
                )
        updated = existing.model_copy(update=update_data)
        self.models[model_id] = updated
        return updated

    @staticmethod
    def _embedded_classes_for_path(path: str) -> list[str]:
        if path.endswith("/models/ppe.onnx"):
            return ["hard_hat", "hi_vis"]
        return ["bus", "car", "person", "truck"]

    @classmethod
    def _resolve_classes(
        cls,
        *,
        path: str,
        format: ModelFormat,
        declared_classes: list[str] | None,
    ) -> list[str]:
        if format is ModelFormat.ONNX:
            embedded_classes = cls._embedded_classes_for_path(path)
            if declared_classes is None:
                return embedded_classes
            if declared_classes != embedded_classes:
                raise HTTPException(
                    status_code=422,
                    detail="Declared classes do not match the embedded ONNX class metadata.",
                )
            return declared_classes
        if declared_classes is not None:
            return declared_classes
        raise HTTPException(status_code=422, detail="classes are required for non-ONNX models.")


class FakeCameraService:
    def __init__(
        self,
        *,
        forced_blur_faces: bool = False,
        forced_blur_plates: bool = False,
        model_classes_by_id: dict[UUID, list[str]] | None = None,
        model_capabilities_by_id: dict[UUID, DetectorCapability] | None = None,
        model_capability_config_by_id: dict[UUID, dict[str, object]] | None = None,
    ) -> None:
        self.cameras: dict[UUID, CameraResponse] = {}
        self.forced_blur_faces = forced_blur_faces
        self.forced_blur_plates = forced_blur_plates
        self.model_classes_by_id = model_classes_by_id or {}
        self.model_capabilities_by_id = model_capabilities_by_id or {}
        self.model_capability_config_by_id = model_capability_config_by_id or {}

    async def list_cameras(
        self,
        context: TenantContext,
        *,
        site_id: UUID | None = None,
    ) -> list[CameraResponse]:
        cameras = list(self.cameras.values())
        if site_id is None:
            return cameras
        return [camera for camera in cameras if camera.site_id == site_id]

    async def get_camera(self, context: TenantContext, camera_id: UUID) -> CameraResponse:
        return self.cameras[camera_id]

    async def create_camera(self, context: TenantContext, payload: CameraCreate) -> CameraResponse:
        if self.forced_blur_faces and not payload.privacy.blur_faces:
            raise HTTPException(status_code=422, detail="Tenant policy requires blur_faces=true.")
        if self.forced_blur_plates and not payload.privacy.blur_plates:
            raise HTTPException(status_code=422, detail="Tenant policy requires blur_plates=true.")
        self._validate_detector_state(
            payload.primary_model_id,
            payload.active_classes,
            payload.runtime_vocabulary.terms,
        )
        camera = _camera_response(payload)
        self.cameras[camera.id] = camera
        return camera

    async def update_camera(
        self,
        context: TenantContext,
        camera_id: UUID,
        payload: CameraUpdate,
    ) -> CameraResponse:
        if (
            self.forced_blur_faces
            and payload.privacy is not None
            and not payload.privacy.blur_faces
        ):
            raise HTTPException(status_code=422, detail="Tenant policy requires blur_faces=true.")
        existing = self.cameras[camera_id]
        primary_model_id = payload.primary_model_id or existing.primary_model_id
        active_classes = (
            payload.active_classes
            if payload.active_classes is not None
            else existing.active_classes
        )
        runtime_vocabulary = (
            payload.runtime_vocabulary.terms
            if payload.runtime_vocabulary is not None
            else existing.runtime_vocabulary.terms
        )
        self._validate_detector_state(primary_model_id, active_classes, runtime_vocabulary)
        updated = existing.model_copy(
            update=payload.model_dump(exclude_unset=True, mode="python"),
        )
        self.cameras[camera_id] = updated
        return updated

    async def delete_camera(self, context: TenantContext, camera_id: UUID) -> None:
        self.cameras.pop(camera_id)

    async def get_worker_config(
        self,
        context: TenantContext,
        camera_id: UUID,
    ) -> WorkerConfigResponse:
        camera = self.cameras[camera_id]
        return WorkerConfigResponse(
            camera_id=camera.id,
            mode=camera.processing_mode,
            camera={
                "rtsp_url": "rtsp://example.local/live",
                "frame_skip": camera.frame_skip,
                "fps_cap": camera.fps_cap,
            },
            publish={
                "subject_prefix": "evt.tracking",
                "http_fallback_url": None,
            },
            stream={},
            model={
                "name": "Argus YOLO",
                "path": "/models/argus.onnx",
                "classes": ["bus", "car", "person", "truck"],
                "input_shape": {"width": 640, "height": 640},
                "confidence_threshold": 0.25,
                "iou_threshold": 0.45,
            },
            secondary_model=None,
            tracker={
                "tracker_type": camera.tracker_type,
                "frame_rate": camera.fps_cap,
            },
            privacy={
                "blur_faces": camera.privacy.blur_faces,
                "blur_plates": camera.privacy.blur_plates,
            },
            active_classes=camera.active_classes,
            attribute_rules=camera.attribute_rules,
            zones=camera.zones,
            homography={
                "src_points": camera.homography.src,
                "dst_points": camera.homography.dst,
                "ref_distance_m": camera.homography.ref_distance_m,
            },
        )

    def _validate_detector_state(
        self,
        primary_model_id: UUID,
        active_classes: list[str],
        runtime_vocabulary: list[str],
    ) -> None:
        capability = self.model_capabilities_by_id.get(
            primary_model_id,
            DetectorCapability.FIXED_VOCAB,
        )
        if capability is DetectorCapability.OPEN_VOCAB:
            config = self.model_capability_config_by_id.get(primary_model_id, {})
            max_terms = int(config.get("max_runtime_terms") or 0)
            if max_terms > 0 and len(runtime_vocabulary) > max_terms:
                raise HTTPException(
                    status_code=422,
                    detail=f"runtime_vocabulary exceeds max_runtime_terms={max_terms}.",
                )
            return

        allowed_classes = set(self.model_classes_by_id.get(primary_model_id, []))
        if not allowed_classes:
            return
        invalid_classes = sorted(
            class_name for class_name in active_classes if class_name not in allowed_classes
        )
        if invalid_classes:
            raise HTTPException(
                status_code=422,
                detail=(
                    "active_classes must be a subset of the selected primary model classes. "
                    f"Unknown classes: {', '.join(invalid_classes)}."
                ),
            )


class FakeEdgeService:
    def __init__(self) -> None:
        self.ingested_keys: set[tuple[UUID, datetime, int]] = set()

    async def register_edge_node(
        self,
        context: TenantContext,
        payload: EdgeRegisterRequest,
    ) -> EdgeRegisterResponse:
        return EdgeRegisterResponse(
            edge_node_id=uuid4(),
            api_key="edge-secret",
            nats_nkey_seed="SUAXXX",
            subjects=[f"evt.tracking.{payload.site_id}", f"edge.heartbeat.{payload.hostname}"],
            mediamtx_url="http://mediamtx.local",
            mediamtx_username="argus",
            mediamtx_password="secret",
            overlay_network_hints={"tailscale": "enabled"},
        )

    async def ingest_telemetry(self, payload: TelemetryEnvelope) -> dict[str, int]:
        inserted = 0
        for frame in payload.events:
            for track in frame.tracks:
                key = (frame.camera_id, frame.ts, track.track_id)
                if key in self.ingested_keys:
                    continue
                self.ingested_keys.add(key)
                inserted += 1
        return {"inserted": inserted}

    async def record_heartbeat(self, payload: EdgeHeartbeatRequest) -> EdgeHeartbeatResponse:
        return EdgeHeartbeatResponse(status="ok", received_at=datetime.now(tz=UTC))


class FakeHistoryService:
    async def query_history(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: object | None = None,
    ) -> list[HistoryPoint]:
        return [
            HistoryPoint(
                bucket=starts_at,
                camera_id=camera_ids[0] if camera_ids else None,
                class_name=(class_names or ["truck"])[0],
                event_count=12,
                granularity=granularity,
            )
        ]

    async def query_series(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: object | None = None,
        include_speed: bool = False,
        speed_threshold: float | None = None,
    ) -> dict[str, object]:
        selected_classes = class_names or ["truck"]
        return {
            "granularity": granularity,
            "class_names": selected_classes,
            "rows": [
                {
                    "bucket": starts_at.isoformat(),
                    "values": {selected_classes[0]: 12},
                    "total_count": 12,
                }
            ],
        }

    async def export_history(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        format_name: str,
        metric: object | None = None,
    ) -> ExportArtifact:
        if format_name == "parquet":
            return ExportArtifact(
                filename="history.parquet",
                media_type="application/x-parquet",
                content=b"PAR1fake",
            )
        return ExportArtifact(
            filename="history.csv",
            media_type="text/csv; charset=utf-8",
            content=b"bucket,class_name,event_count\n2026-01-01T00:00:00Z,truck,12\n",
        )


class FakeIncidentService:
    async def list_incidents(
        self,
        context: TenantContext,
        *,
        camera_id: UUID | None = None,
        incident_type: str | None = None,
        review_status: IncidentReviewStatus | None = None,
        limit: int = 50,
    ) -> list[IncidentResponse]:
        return [
            IncidentResponse(
                id=uuid4(),
                camera_id=camera_id or uuid4(),
                camera_name="North Gate",
                ts=datetime.now(tz=UTC),
                type=incident_type or "ppe-missing",
                payload={"hard_hat": False},
                snapshot_url="https://minio.local/snapshots/1.jpg",
                review_status=review_status or IncidentReviewStatus.PENDING,
            )
        ][:limit]


class FakeStreamService:
    async def create_offer(
        self,
        context: TenantContext,
        *,
        camera_id: UUID,
        offer: StreamOfferRequest,
    ) -> StreamOfferResponse:
        return StreamOfferResponse(
            camera_id=camera_id,
            sdp_answer="v=0\r\no=mediamtx 1 1 IN IP4 127.0.0.1\r\n",
        )


class FakeQueryService:
    async def resolve_query(self, context: TenantContext, payload: QueryRequest) -> QueryResponse:
        return QueryResponse(
            resolved_classes=["bus", "truck"],
            provider="keyword-fallback",
            model="fallback",
            latency_ms=5,
            camera_ids=payload.camera_ids,
        )


class FakeTelemetrySubscription:
    def __init__(self, frame: TelemetryFrame) -> None:
        self._queue: asyncio.Queue[TelemetryFrame] = asyncio.Queue()
        self._queue.put_nowait(frame)

    async def receive(self) -> TelemetryFrame:
        return await self._queue.get()

    async def close(self) -> None:
        return None


class FakeTelemetryService:
    def __init__(self, frame: TelemetryFrame) -> None:
        self.frame = frame

    async def subscribe(self, context: TenantContext) -> FakeTelemetrySubscription:
        return FakeTelemetrySubscription(self.frame)


@dataclass
class FakeServices:
    tenancy: FakeTenancyService
    sites: FakeSiteService
    cameras: FakeCameraService
    models: FakeModelService
    edge: FakeEdgeService
    history: FakeHistoryService
    incidents: FakeIncidentService
    streams: FakeStreamService
    query: FakeQueryService
    telemetry: FakeTelemetryService


def _build_app(services: FakeServices, user: AuthenticatedUser) -> TestClient:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user
    return TestClient(app)


@pytest.mark.asyncio
async def test_sites_crud_contract() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=FakeSiteService(context.tenant_id),
        cameras=FakeCameraService(),
        models=FakeModelService(),
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(
            TelemetryFrame(
                camera_id=uuid4(),
                ts=datetime.now(tz=UTC),
                profile=PublishProfile.CENTRAL_GPU,
                stream_mode=StreamMode.ANNOTATED_WHIP,
                counts={"truck": 1},
                tracks=[],
            )
        ),
    )
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/sites",
            json={
                "name": "HQ",
                "description": "Main site",
                "tz": "Europe/Zurich",
                "geo_point": {"lat": 47.3769, "lon": 8.5417},
            },
        )
        site_id = UUID(create_response.json()["id"])

        list_response = await client.get("/api/v1/sites")
        detail_response = await client.get(f"/api/v1/sites/{site_id}")
        update_response = await client.patch(
            f"/api/v1/sites/{site_id}",
            json={"name": "HQ Updated"},
        )
        delete_response = await client.delete(f"/api/v1/sites/{site_id}")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "HQ Updated"
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_models_routes_contract() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=FakeSiteService(context.tenant_id),
        cameras=FakeCameraService(),
        models=FakeModelService(),
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(
            TelemetryFrame(
                camera_id=uuid4(),
                ts=datetime.now(tz=UTC),
                profile=PublishProfile.CENTRAL_GPU,
                stream_mode=StreamMode.ANNOTATED_WHIP,
                counts={},
                tracks=[],
            )
        ),
    )
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        mismatch_response = await client.post(
            "/api/v1/models",
            json={
                "name": "Argus PPE mismatch",
                "version": "1.0.0",
                "task": "attribute",
                "path": "/models/ppe.onnx",
                "format": "onnx",
                "classes": ["person"],
                "input_shape": {"h": 224, "w": 224, "c": 3},
                "sha256": "c" * 64,
                "size_bytes": 2048,
                "license": "Apache-2.0",
            },
        )
        create_response = await client.post(
            "/api/v1/models",
            json={
                "name": "Argus PPE",
                "version": "1.0.0",
                "task": "attribute",
                "path": "/models/ppe.onnx",
                "format": "onnx",
                "input_shape": {"h": 224, "w": 224, "c": 3},
                "sha256": "b" * 64,
                "size_bytes": 2048,
                "license": "Apache-2.0",
            },
        )
        model_id = UUID(create_response.json()["id"])
        list_response = await client.get("/api/v1/models")
        patch_response = await client.patch(
            f"/api/v1/models/{model_id}",
            json={"license": "MIT"},
        )

    assert mismatch_response.status_code == 422
    assert create_response.status_code == 201
    assert create_response.json()["classes"] == ["hard_hat", "hi_vis"]
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert patch_response.status_code == 200
    assert patch_response.json()["license"] == "MIT"


@pytest.mark.asyncio
async def test_models_routes_allow_open_vocab_empty_static_classes() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=FakeSiteService(context.tenant_id),
        cameras=FakeCameraService(),
        models=FakeModelService(),
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(
            TelemetryFrame(
                camera_id=uuid4(),
                ts=datetime.now(tz=UTC),
                profile=PublishProfile.CENTRAL_GPU,
                stream_mode=StreamMode.ANNOTATED_WHIP,
                counts={},
                tracks=[],
            )
        ),
    )
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/models",
            json={
                "name": "YOLO World",
                "version": "1.0.0",
                "task": "detect",
                "path": "/models/yolo-world.onnx",
                "format": "onnx",
                "capability": "open_vocab",
                "classes": [],
                "capability_config": {
                    "supports_runtime_vocabulary_updates": True,
                    "max_runtime_terms": 32,
                    "prompt_format": "labels",
                    "execution_profiles": ["x86_64_gpu", "arm64_jetson"],
                },
                "input_shape": {"width": 640, "height": 640},
                "sha256": "b" * 64,
                "size_bytes": 1,
            },
        )

    assert response.status_code == 201
    assert response.json()["capability"] == "open_vocab"
    assert response.json()["classes"] == []


@pytest.mark.asyncio
async def test_camera_routes_validate_policy_and_crud() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    site = _site_response(context.tenant_id)
    model = _model_response()
    site_service = FakeSiteService(context.tenant_id)
    site_service.sites[site.id] = site
    model_service = FakeModelService()
    model_service.models[model.id] = model
    camera_service = FakeCameraService(
        forced_blur_faces=True,
        model_classes_by_id={model.id: model.classes},
    )
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=site_service,
        cameras=camera_service,
        models=model_service,
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(
            TelemetryFrame(
                camera_id=uuid4(),
                ts=datetime.now(tz=UTC),
                profile=PublishProfile.CENTRAL_GPU,
                stream_mode=StreamMode.ANNOTATED_WHIP,
                counts={},
                tracks=[],
            )
        ),
    )
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user
    payload = _camera_payload(site.id, model.id).model_dump(mode="json")
    payload["privacy"]["blur_faces"] = False

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        policy_response = await client.post("/api/v1/cameras", json=payload)

        payload["privacy"]["blur_faces"] = True
        payload["active_classes"] = ["airplane"]
        invalid_classes_response = await client.post("/api/v1/cameras", json=payload)

        payload["active_classes"] = ["bus", "truck"]
        create_response = await client.post("/api/v1/cameras", json=payload)
        camera_id = UUID(create_response.json()["id"])
        list_response = await client.get("/api/v1/cameras", params={"site_id": str(site.id)})
        detail_response = await client.get(f"/api/v1/cameras/{camera_id}")
        patch_response = await client.patch(
            f"/api/v1/cameras/{camera_id}",
            json={"active_classes": ["person"]},
        )
        delete_response = await client.delete(f"/api/v1/cameras/{camera_id}")

    assert policy_response.status_code == 422
    assert invalid_classes_response.status_code == 422
    assert create_response.status_code == 201
    assert create_response.json()["browser_delivery"]["default_profile"] == "720p10"
    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["active_classes"] == ["person"]
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_camera_routes_persist_open_vocab_runtime_vocabulary() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    site = _site_response(context.tenant_id)
    model = _model_response().model_copy(
        update={
            "name": "YOLO World",
            "path": "/models/yolo-world.onnx",
            "capability": DetectorCapability.OPEN_VOCAB,
            "capability_config": {
                "supports_runtime_vocabulary_updates": True,
                "max_runtime_terms": 32,
                "prompt_format": "labels",
                "execution_profiles": ["x86_64_gpu", "arm64_jetson"],
            },
            "classes": [],
        }
    )
    site_service = FakeSiteService(context.tenant_id)
    site_service.sites[site.id] = site
    model_service = FakeModelService()
    model_service.models[model.id] = model
    camera_service = FakeCameraService(
        model_capabilities_by_id={model.id: DetectorCapability.OPEN_VOCAB},
        model_capability_config_by_id={
            model.id: {
                "supports_runtime_vocabulary_updates": True,
                "max_runtime_terms": 32,
                "prompt_format": "labels",
                "execution_profiles": ["x86_64_gpu", "arm64_jetson"],
            }
        },
    )
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=site_service,
        cameras=camera_service,
        models=model_service,
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(
            TelemetryFrame(
                camera_id=uuid4(),
                ts=datetime.now(tz=UTC),
                profile=PublishProfile.CENTRAL_GPU,
                stream_mode=StreamMode.ANNOTATED_WHIP,
                counts={},
                tracks=[],
            )
        ),
    )
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user
    payload = _camera_payload(site.id, model.id).model_dump(mode="json")
    payload["active_classes"] = []
    payload["runtime_vocabulary"] = {
        "terms": ["forklift", "pallet jack"],
        "source": "manual",
        "version": 1,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/api/v1/cameras", json=payload)

    assert response.status_code == 201
    assert response.json()["active_classes"] == []
    assert response.json()["runtime_vocabulary"]["terms"] == ["forklift", "pallet jack"]
    assert response.json()["runtime_vocabulary"]["source"] == "manual"
    assert response.json()["runtime_vocabulary"]["version"] == 1


@pytest.mark.asyncio
async def test_camera_worker_config_route_returns_engine_ready_payload() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    site = _site_response(context.tenant_id)
    model = _model_response()
    site_service = FakeSiteService(context.tenant_id)
    site_service.sites[site.id] = site
    model_service = FakeModelService()
    model_service.models[model.id] = model
    camera_service = FakeCameraService(model_classes_by_id={model.id: model.classes})
    payload = _camera_payload(site.id, model.id)
    camera = await camera_service.create_camera(context, payload)
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=site_service,
        cameras=camera_service,
        models=model_service,
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(
            TelemetryFrame(
                camera_id=uuid4(),
                ts=datetime.now(tz=UTC),
                profile=PublishProfile.CENTRAL_GPU,
                stream_mode=StreamMode.ANNOTATED_WHIP,
                counts={},
                tracks=[],
            )
        ),
    )
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/v1/cameras/{camera.id}/worker-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["camera_id"] == str(camera.id)
    assert payload["mode"] == "central"
    assert payload["camera"]["rtsp_url"] == "rtsp://example.local/live"
    assert payload["publish"]["subject_prefix"] == "evt.tracking"
    assert payload["publish"]["http_fallback_url"] is None
    assert payload["tracker"]["tracker_type"] == "botsort"
    assert payload["tracker"]["frame_rate"] == 25
    assert payload["privacy"] == {
        "blur_faces": True,
        "blur_plates": False,
        "method": "gaussian",
        "strength": 7,
    }
    assert payload["homography"] == {
        "src_points": [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0]],
        "dst_points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
        "ref_distance_m": 12.5,
    }


@pytest.mark.asyncio
async def test_edge_routes_history_export_incidents_and_stream_offer_contract() -> None:
    user = _sample_user()
    context = _tenant_context(user)
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=FakeSiteService(context.tenant_id),
        cameras=FakeCameraService(),
        models=FakeModelService(),
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(
            TelemetryFrame(
                camera_id=uuid4(),
                ts=datetime.now(tz=UTC),
                profile=PublishProfile.CENTRAL_GPU,
                stream_mode=StreamMode.ANNOTATED_WHIP,
                counts={},
                tracks=[],
            )
        ),
    )
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user
    camera_id = uuid4()
    now = datetime.now(tz=UTC).replace(microsecond=0)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        register_response = await client.post(
            "/api/v1/edge/register",
            json={"site_id": str(uuid4()), "hostname": "edge-1", "version": "1.2.3"},
        )
        telemetry_response = await client.post(
            "/api/v1/edge/telemetry",
            json={
                "events": [
                    {
                        "camera_id": str(camera_id),
                        "ts": now.isoformat(),
                        "profile": "central-gpu",
                        "stream_mode": "annotated-whip",
                        "counts": {"truck": 1},
                        "tracks": [
                            {
                                "class_name": "truck",
                                "confidence": 0.99,
                                "bbox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
                                "track_id": 7,
                                "speed_kph": 42.0,
                                "direction_deg": 180.0,
                                "zone_id": "lane-a",
                                "attributes": {},
                            }
                        ],
                    }
                ]
            },
            headers={"X-Edge-Key": "dev-edge-key"},
        )
        heartbeat_response = await client.post(
            "/api/v1/edge/heartbeat",
            json={"node_id": str(uuid4()), "version": "1.2.3", "cameras": 3},
            headers={"X-Edge-Key": "dev-edge-key"},
        )
        history_response = await client.get(
            "/api/v1/history",
            params={
                "camera_id": str(camera_id),
                "granularity": "1m",
                "from": now.isoformat(),
                "to": now.isoformat(),
            },
        )
        csv_export_response = await client.get(
            "/api/v1/export",
            params={
                "camera_id": str(camera_id),
                "granularity": "1m",
                "from": now.isoformat(),
                "to": now.isoformat(),
                "format": "csv",
            },
        )
        parquet_export_response = await client.get(
            "/api/v1/export",
            params={
                "camera_id": str(camera_id),
                "granularity": "1m",
                "from": now.isoformat(),
                "to": now.isoformat(),
                "format": "parquet",
            },
        )
        incidents_response = await client.get("/api/v1/incidents")
        offer_response = await client.post(
            f"/api/v1/streams/{camera_id}/offer",
            json={"sdp_offer": "v=0\r\n"},
        )

    assert register_response.status_code == 201
    assert telemetry_response.status_code == 202
    assert telemetry_response.json() == {"inserted": 1}
    assert heartbeat_response.status_code == 202
    assert history_response.status_code == 200
    assert history_response.json()[0]["class_name"] == "truck"
    assert csv_export_response.status_code == 200
    assert csv_export_response.headers["content-type"].startswith("text/csv")
    assert parquet_export_response.status_code == 200
    assert parquet_export_response.headers["content-type"].startswith("application/x-parquet")
    assert incidents_response.status_code == 200
    assert offer_response.status_code == 200
    assert "sdp_answer" in offer_response.json()


@pytest.mark.asyncio
async def test_query_route_contract() -> None:
    user = _sample_user(role=RoleEnum.OPERATOR)
    context = _tenant_context(user)
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=FakeSiteService(context.tenant_id),
        cameras=FakeCameraService(),
        models=FakeModelService(),
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(
            TelemetryFrame(
                camera_id=uuid4(),
                ts=datetime.now(tz=UTC),
                profile=PublishProfile.CENTRAL_GPU,
                stream_mode=StreamMode.ANNOTATED_WHIP,
                counts={},
                tracks=[],
            )
        ),
    )
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/query",
            json={"prompt": "only watch buses and trucks", "camera_ids": [str(uuid4())]},
        )

    assert response.status_code == 200
    assert response.json()["resolved_classes"] == ["bus", "truck"]


def test_websocket_telemetry_contract() -> None:
    user = _sample_user(role=RoleEnum.VIEWER)
    context = _tenant_context(user)
    frame = TelemetryFrame(
        camera_id=uuid4(),
        ts=datetime.now(tz=UTC),
        profile=PublishProfile.CENTRAL_GPU,
        stream_mode=StreamMode.ANNOTATED_WHIP,
        counts={"truck": 1},
        tracks=[
            TelemetryTrack(
                class_name="truck",
                confidence=0.98,
                bbox={"x1": 10, "y1": 20, "x2": 30, "y2": 40},
                track_id=9,
            )
        ],
    )
    services = FakeServices(
        tenancy=FakeTenancyService(context),
        sites=FakeSiteService(context.tenant_id),
        cameras=FakeCameraService(),
        models=FakeModelService(),
        edge=FakeEdgeService(),
        history=FakeHistoryService(),
        incidents=FakeIncidentService(),
        streams=FakeStreamService(),
        query=FakeQueryService(),
        telemetry=FakeTelemetryService(frame),
    )
    client = _build_app(services, user)

    with client.websocket_connect("/ws/telemetry") as websocket:
        payload = websocket.receive_json()

    assert payload["camera_id"] == str(frame.camera_id)
    assert payload["counts"]["truck"] == 1
