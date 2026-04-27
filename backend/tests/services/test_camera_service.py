from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from argus.api.contracts import (
    BrowserDeliverySettings,
    CameraCreate,
    CameraUpdate,
    FrameSize,
    HomographyPayload,
    PrivacySettings,
    TenantContext,
)
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, decrypt_rtsp_url
from argus.models.enums import ModelFormat, ModelTask, ProcessingMode, RoleEnum, TrackerType
from argus.models.tables import Camera, Model, Site
from argus.services import app as app_services
from argus.services.app import CameraService

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class _FakeSession:
    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, camera: Camera) -> None:
        return None


class _FakeSessionFactory:
    def __call__(self) -> _FakeSession:
        return _FakeSession()


class _FakeAuditLogger:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def record(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


class _FakeEvents:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def publish(self, subject: str, payload: object) -> None:
        self.calls.append((subject, payload))


@pytest.mark.asyncio
async def test_update_camera_accepts_full_wizard_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    site_id = uuid4()
    model_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    audit_logger = _FakeAuditLogger()
    camera = Camera(
        id=camera_id,
        site_id=site_id,
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=audit_logger,
        events=None,
    )
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    payload = CameraUpdate(
        site_id=site_id,
        name="Dock Camera Updated",
        rtsp_url="rtsp://new-camera/live",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        homography=HomographyPayload(
            src=[[0, 0], [20, 0], [20, 20], [0, 20]],
            dst=[[0, 0], [10, 0], [10, 10], [0, 10]],
            ref_distance_m=10.0,
        ),
        privacy=PrivacySettings(
            blur_faces=True,
            blur_plates=True,
            method="gaussian",
            strength=7,
        ),
        browser_delivery=BrowserDeliverySettings(default_profile="540p5"),
        frame_skip=2,
        fps_cap=12,
        zones=[
            {
                "id": "entry-line",
                "type": "line",
                "points": [[5, 5], [100, 100]],
                "class_names": ["person"],
            }
        ],
    )
    model = Model(
        id=model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )
    site = Site(
        id=site_id,
        tenant_id=tenant_id,
        name="HQ",
        description=None,
        tz="Europe/Zurich",
        geo_point=None,
        created_at=now,
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        assert model_id_arg == model_id
        return model

    async def fake_load_site(session, tenant_id_arg, site_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert site_id_arg == site_id
        return site

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services, "_load_model", fake_load_model)
    monkeypatch.setattr(app_services, "_load_site", fake_load_site)

    response = await service.update_camera(tenant_context, camera_id, payload)

    assert response.name == "Dock Camera Updated"
    assert response.browser_delivery.default_profile == "540p5"
    assert response.frame_skip == 2
    assert response.fps_cap == 12
    assert [zone.model_dump(mode="python") for zone in response.zones] == [
        {
            "id": "entry-line",
            "type": "line",
            "points": [[5.0, 5.0], [100.0, 100.0]],
            "class_names": ["person"],
            "frame_size": None,
            "points_normalized": None,
        }
    ]
    assert camera.homography == {
        "src": [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]],
        "dst": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
        "ref_distance_m": 10.0,
    }
    assert decrypt_rtsp_url(camera.rtsp_url_encrypted, settings) == "rtsp://new-camera/live"
    assert audit_logger.calls[0]["action"] == "camera.update"
    audit_meta = audit_logger.calls[0]["meta"]
    assert isinstance(audit_meta, dict)
    assert audit_meta["site_id"] == str(site_id)
    assert audit_meta["primary_model_id"] == str(model_id)


@pytest.mark.asyncio
async def test_update_camera_normalizes_line_zone_coordinates_when_frame_size_is_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    site_id = uuid4()
    model_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    audit_logger = _FakeAuditLogger()
    camera = Camera(
        id=camera_id,
        site_id=site_id,
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=audit_logger,
        events=None,
    )
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    payload = CameraUpdate(
        zones=[
            {
                "id": "room-split",
                "type": "line",
                "points": [[640, 120], [640, 710]],
                "class_names": ["person"],
                "frame_size": {"width": 1280, "height": 720},
            }
        ]
    )
    model = Model(
        id=model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        assert model_id_arg == model_id
        return model

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services, "_load_model", fake_load_model)

    response = await service.update_camera(tenant_context, camera_id, payload)

    assert len(response.zones) == 1
    zone = response.zones[0]
    assert zone.type == "line"
    assert zone.points == [[640.0, 120.0], [640.0, 710.0]]
    assert zone.frame_size.model_dump() == {"width": 1280, "height": 720}
    assert zone.points_normalized == [[0.5, 0.166667], [0.5, 0.986111]]
    assert camera.zones == [zone.model_dump(exclude_none=True, mode="python")]


@pytest.mark.asyncio
async def test_update_camera_normalizes_polygon_zone_coordinates_when_frame_size_is_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    site_id = uuid4()
    model_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    audit_logger = _FakeAuditLogger()
    camera = Camera(
        id=camera_id,
        site_id=site_id,
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=audit_logger,
        events=None,
    )
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    payload = CameraUpdate(
        zones=[
            {
                "id": "desk-zone",
                "type": "polygon",
                "polygon": [[700, 420], [1180, 420], [1180, 710], [700, 710]],
                "frame_size": {"width": 1280, "height": 720},
            }
        ]
    )
    model = Model(
        id=model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        assert model_id_arg == model_id
        return model

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services, "_load_model", fake_load_model)

    response = await service.update_camera(tenant_context, camera_id, payload)

    assert len(response.zones) == 1
    zone = response.zones[0]
    assert zone.type == "polygon"
    assert zone.polygon == [[700.0, 420.0], [1180.0, 420.0], [1180.0, 710.0], [700.0, 710.0]]
    assert zone.frame_size.model_dump() == {"width": 1280, "height": 720}
    assert zone.points_normalized == [
        [0.546875, 0.583333],
        [0.921875, 0.583333],
        [0.921875, 0.986111],
        [0.546875, 0.986111],
    ]
    assert camera.zones == [zone.model_dump(exclude_none=True, mode="python")]


@pytest.mark.asyncio
async def test_camera_update_rejects_line_zone_with_more_than_two_points() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CameraUpdate(
            zones=[
                {
                    "id": "invalid-line",
                    "type": "line",
                    "points": [[0, 0], [10, 10], [20, 20]],
                }
            ]
        )

    assert "exactly two points" in str(exc_info.value)


@pytest.mark.asyncio
async def test_camera_update_rejects_polygon_zone_with_fewer_than_three_vertices() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CameraUpdate(
            zones=[
                {
                    "id": "invalid-polygon",
                    "type": "polygon",
                    "polygon": [[0, 0], [10, 10]],
                }
            ]
        )

    assert "at least three vertices" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_camera_rejects_zone_coordinates_outside_declared_frame_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    model_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    payload = CameraUpdate(
        zones=[
            {
                "id": "room-split",
                "type": "line",
                "points": [[1281, 120], [640, 710]],
                "class_names": ["person"],
                "frame_size": {"width": 1280, "height": 720},
            }
        ]
    )
    model = Model(
        id=model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        assert model_id_arg == model_id
        return model

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services, "_load_model", fake_load_model)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_camera(tenant_context, camera_id, payload)

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE
    assert exc_info.value.detail == "Zone coordinates must fall within the declared frame_size."


@pytest.mark.asyncio
async def test_get_setup_preview_returns_frame_size_and_preview_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(
        app_services,
        "_capture_setup_preview_snapshot",
        lambda camera_arg, settings_arg: app_services._SetupPreviewSnapshot(
            image_bytes=b"preview-jpeg",
            frame_size=FrameSize(width=1280, height=720),
            captured_at=now,
        ),
    )

    response = await service.get_setup_preview(tenant_context, camera_id)

    assert response.camera_id == camera_id
    assert response.frame_size.model_dump() == {"width": 1280, "height": 720}
    assert response.preview_url == (
        f"/api/v1/cameras/{camera_id}/setup-preview/image?rev={int(now.timestamp() * 1000)}"
    )
    assert response.captured_at == now


@pytest.mark.asyncio
async def test_get_setup_preview_returns_503_when_capture_fails_without_cached_still(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(
        app_services,
        "_capture_setup_preview_snapshot",
        lambda camera_arg, settings_arg: (_ for _ in ()).throw(
            RuntimeError("Timed out while capturing a setup preview frame after 20s.")
        ),
    )

    with pytest.raises(HTTPException, match="Unable to capture an analytics still"):
        await service.get_setup_preview(tenant_context, camera_id)


@pytest.mark.asyncio
async def test_get_setup_preview_uses_captured_still_dimensions_instead_of_stale_zone_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[
            {
                "id": "stale-zone",
                "type": "line",
                "points": [[100, 100], [300, 300]],
                "frame_size": {"width": 960, "height": 540},
                "points_normalized": [[0.104167, 0.185185], [0.3125, 0.555556]],
            }
        ],
        homography={
            "src": [[120, 80], [920, 80], [920, 680], [120, 680]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery={
            "default_profile": "540p5",
            "allow_native_on_demand": True,
            "profiles": [
                {"id": "540p5", "kind": "transcode", "w": 960, "h": 540, "fps": 5}
            ],
        },
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(
        app_services,
        "_capture_setup_preview_snapshot",
        lambda camera_arg, settings_arg: app_services._SetupPreviewSnapshot(
            image_bytes=b"preview-jpeg",
            frame_size=FrameSize(width=1600, height=900),
            captured_at=now,
        ),
    )

    response = await service.get_setup_preview(tenant_context, camera_id)

    assert response.frame_size.model_dump() == {"width": 1600, "height": 900}
    assert response.preview_url.startswith(f"/api/v1/cameras/{camera_id}/setup-preview/image")


@pytest.mark.asyncio
async def test_get_setup_preview_runs_blocking_capture_via_to_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[120, 80], [920, 80], [920, 680], [120, 680]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    to_thread_calls: list[tuple[object, tuple[object, ...]]] = []

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_to_thread(func, *args):  # noqa: ANN001
        to_thread_calls.append((func, args))
        return func(*args)

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        app_services,
        "_capture_setup_preview_snapshot",
        lambda camera_arg, settings_arg: app_services._SetupPreviewSnapshot(
            image_bytes=b"preview-jpeg",
            frame_size=FrameSize(width=1600, height=900),
            captured_at=now,
        ),
    )

    response = await service.get_setup_preview(tenant_context, camera_id)

    assert response.frame_size.model_dump() == {"width": 1600, "height": 900}
    assert len(to_thread_calls) == 1
    assert to_thread_calls[0][0] is app_services._capture_setup_preview_snapshot
    assert to_thread_calls[0][1] == (camera, settings)


@pytest.mark.asyncio
async def test_get_setup_preview_image_reuses_cached_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[120, 80], [920, 80], [920, 680], [120, 680]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    capture_calls: list[tuple[object, object]] = []

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    def fake_capture_setup_preview_snapshot(camera_arg, settings_arg):  # noqa: ANN001
        capture_calls.append((camera_arg, settings_arg))
        return app_services._SetupPreviewSnapshot(
            image_bytes=b"preview-jpeg",
            frame_size=FrameSize(width=1280, height=720),
            captured_at=now,
        )

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(
        app_services,
        "_capture_setup_preview_snapshot",
        fake_capture_setup_preview_snapshot,
    )

    await service.get_setup_preview(tenant_context, camera_id)
    snapshot = await service.get_setup_preview_image(tenant_context, camera_id)

    assert len(capture_calls) == 1
    assert snapshot.image_bytes == b"preview-jpeg"
    assert snapshot.frame_size.model_dump() == {"width": 1280, "height": 720}


@pytest.mark.asyncio
async def test_get_setup_preview_reuses_cached_snapshot_when_refresh_capture_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[120, 80], [920, 80], [920, 680], [120, 680]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    capture_calls = 0

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    def fake_capture_setup_preview_snapshot(camera_arg, settings_arg):  # noqa: ANN001
        nonlocal capture_calls
        capture_calls += 1
        if capture_calls == 1:
            return app_services._SetupPreviewSnapshot(
                image_bytes=b"preview-jpeg",
                frame_size=FrameSize(width=1280, height=720),
                captured_at=now,
            )
        raise RuntimeError("Timed out while capturing a setup preview frame after 20s.")

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(
        app_services,
        "_capture_setup_preview_snapshot",
        fake_capture_setup_preview_snapshot,
    )
    caplog.set_level("WARNING", logger="argus.services.app")

    original = await service.get_setup_preview(tenant_context, camera_id)
    refreshed = await service.get_setup_preview(tenant_context, camera_id, force_refresh=True)

    assert capture_calls == 2
    assert refreshed.frame_size == original.frame_size
    assert refreshed.preview_url == original.preview_url
    assert any("reusing cached still" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_get_worker_config_materializes_pixel_coordinates_from_normalized_zones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    model_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["person"],
        attribute_rules=[],
        zones=[
            {
                "id": "room-split",
                "type": "line",
                "points": [[640, 120], [640, 710]],
                "class_names": ["person"],
                "frame_size": {"width": 1280, "height": 720},
                "points_normalized": [[0.5, 0.166667], [0.5, 0.986111]],
            }
        ],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    model = Model(
        id=model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        assert model_id_arg == model_id
        return model

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services, "_load_model", fake_load_model)

    response = await service.get_worker_config(tenant_context, camera_id)

    assert len(response.zones) == 1
    zone = response.zones[0]
    assert zone.type == "line"
    assert zone.points == [[640.0, 120.0], [640.0, 710.0]]
    assert not hasattr(zone, "frame_size")
    assert not hasattr(zone, "points_normalized")


@pytest.mark.asyncio
async def test_get_worker_config_materializes_polygon_coordinates_from_normalized_zones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    model_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["person"],
        attribute_rules=[],
        zones=[
            {
                "id": "desk-zone",
                "type": "polygon",
                "polygon": [[700, 420], [1180, 420], [1180, 710], [700, 710]],
                "frame_size": {"width": 1280, "height": 720},
                "points_normalized": [
                    [0.546875, 0.583333],
                    [0.921875, 0.583333],
                    [0.921875, 0.986111],
                    [0.546875, 0.986111],
                ],
            }
        ],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        events=None,
    )
    user = AuthenticatedUser(
        subject="viewer-1",
        email="viewer@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    model = Model(
        id=model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        assert model_id_arg == model_id
        return model

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services, "_load_model", fake_load_model)

    response = await service.get_worker_config(tenant_context, camera_id)

    assert len(response.zones) == 1
    zone = response.zones[0]
    assert zone.type == "polygon"
    assert zone.polygon == [[700.0, 420.0], [1180.0, 420.0], [1180.0, 710.0], [700.0, 710.0]]


@pytest.mark.asyncio
async def test_create_camera_rejects_active_classes_outside_primary_model_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    site_id = uuid4()
    model_id = uuid4()
    audit_logger = _FakeAuditLogger()
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=audit_logger,
        events=None,
    )
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    model = Model(
        id=model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )
    site = Site(
        id=site_id,
        tenant_id=tenant_id,
        name="HQ",
        description=None,
        tz="Europe/Zurich",
        geo_point=None,
        created_at=datetime.now(tz=UTC),
    )

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        assert model_id_arg == model_id
        return model

    async def fake_load_site(session, tenant_id_arg, site_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert site_id_arg == site_id
        return site

    monkeypatch.setattr(app_services, "_load_model", fake_load_model)
    monkeypatch.setattr(app_services, "_load_site", fake_load_site)

    payload = CameraCreate(
        site_id=site_id,
        name="Dock Camera",
        rtsp_url="rtsp://new-camera/live",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["person", "truck"],
        attribute_rules=[],
        zones=[],
        homography=HomographyPayload(
            src=[[0, 0], [20, 0], [20, 20], [0, 20]],
            dst=[[0, 0], [10, 0], [10, 10], [0, 10]],
            ref_distance_m=10.0,
        ),
        privacy=PrivacySettings(),
        frame_skip=1,
        fps_cap=25,
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.create_camera(tenant_context, payload)

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE


@pytest.mark.asyncio
async def test_update_camera_rejects_active_classes_when_primary_model_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    site_id = uuid4()
    current_model_id = uuid4()
    replacement_model_id = uuid4()
    camera_id = uuid4()
    audit_logger = _FakeAuditLogger()
    camera = Camera(
        id=camera_id,
        site_id=site_id,
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=current_model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=audit_logger,
        events=None,
    )
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    payload = CameraUpdate(primary_model_id=replacement_model_id)
    current_model = Model(
        id=current_model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )
    replacement_model = Model(
        id=replacement_model_id,
        name="Replacement detector",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/replacement.onnx",
        format=ModelFormat.ONNX,
        classes=["bus"],
        input_shape={"width": 640, "height": 640},
        sha256="b" * 64,
        size_bytes=1024,
        license="lab",
    )
    site = Site(
        id=site_id,
        tenant_id=tenant_id,
        name="HQ",
        description=None,
        tz="Europe/Zurich",
        geo_point=None,
        created_at=datetime.now(tz=UTC),
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        if model_id_arg == current_model_id:
            return current_model
        if model_id_arg == replacement_model_id:
            return replacement_model
        raise AssertionError(f"unexpected model id {model_id_arg}")

    async def fake_load_site(session, tenant_id_arg, site_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert site_id_arg == site_id
        return site

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services, "_load_model", fake_load_model)
    monkeypatch.setattr(app_services, "_load_site", fake_load_site)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_camera(tenant_context, camera_id, payload)

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE


@pytest.mark.asyncio
async def test_update_camera_publishes_zone_command_to_running_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    tenant_id = uuid4()
    site_id = uuid4()
    model_id = uuid4()
    camera_id = uuid4()
    now = datetime.now(tz=UTC)
    audit_logger = _FakeAuditLogger()
    events = _FakeEvents()
    camera = Camera(
        id=camera_id,
        site_id=site_id,
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted=app_services.encrypt_rtsp_url("rtsp://old-camera/live", settings),
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "dst": [[0, 0], [5, 0], [5, 5], [0, 5]],
            "ref_distance_m": 5.0,
        },
        privacy={
            "blur_faces": True,
            "blur_plates": True,
            "method": "gaussian",
            "strength": 7,
        },
        browser_delivery=BrowserDeliverySettings().model_dump(mode="python"),
        frame_skip=1,
        fps_cap=25,
        created_at=now,
        updated_at=now,
    )
    service = CameraService(
        session_factory=_FakeSessionFactory(),
        settings=settings,
        audit_logger=audit_logger,
        events=events,
    )
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=user,
    )
    payload = CameraUpdate(
        zones=[
            {
                "id": "room-split",
                "type": "line",
                "points": [[640, 120], [640, 710]],
                "class_names": ["person"],
                "frame_size": {"width": 1280, "height": 720},
            },
        ]
    )
    model = Model(
        id=model_id,
        name="Vezor YOLO12n",
        version="lab-imac",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=1024,
        license="lab",
    )

    async def fake_load_camera(session, tenant_id_arg, camera_id_arg):  # noqa: ANN001
        assert tenant_id_arg == tenant_id
        assert camera_id_arg == camera_id
        return camera

    async def fake_load_model(session, model_id_arg):  # noqa: ANN001
        assert model_id_arg == model_id
        return model

    monkeypatch.setattr(app_services, "_load_camera", fake_load_camera)
    monkeypatch.setattr(app_services, "_load_model", fake_load_model)

    await service.update_camera(tenant_context, camera_id, payload)

    assert events.calls
    subject, command = events.calls[0]
    assert subject == f"cmd.camera.{camera_id}"
    assert isinstance(command, dict)
    assert command["zones"] == [
        {
            "id": "room-split",
            "type": "line",
            "points": [[640, 120], [640, 710]],
            "class_names": ["person"],
        }
    ]
    assert command["active_classes"] == ["person"]
