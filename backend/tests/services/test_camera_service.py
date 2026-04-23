from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from argus.api.contracts import (
    BrowserDeliverySettings,
    CameraCreate,
    CameraUpdate,
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
