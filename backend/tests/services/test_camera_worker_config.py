from __future__ import annotations

from uuid import uuid4

from argus.api.contracts import SourceCapability
from argus.core.config import Settings
from argus.models.enums import ModelFormat, ModelTask, ProcessingMode, TrackerType
from argus.models.tables import Camera, Model
from argus.services.app import _camera_to_worker_config, derive_browser_profiles


def test_source_capability_hides_1080p_above_720p_source() -> None:
    source = SourceCapability(width=1280, height=720, fps=20, codec="h264")

    profiles = derive_browser_profiles(source)

    assert [profile.id for profile in profiles.allowed] == ["native", "720p10", "540p5"]
    assert profiles.unsupported[0].id == "1080p15"
    assert profiles.unsupported[0].reason == "source_resolution_too_small"


def test_camera_worker_config_maps_camera_models_and_homography_for_engine() -> None:
    camera_id = uuid4()
    primary_model_id = uuid4()
    secondary_model_id = uuid4()
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=primary_model_id,
        secondary_model_id=secondary_model_id,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["bus", "truck"],
        attribute_rules=[{"kind": "ppe"}],
        zones=[{"id": "gate-1", "type": "line"}],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={"blur_faces": True, "blur_plates": False, "method": "gaussian", "strength": 7},
        browser_delivery={
            "default_profile": "720p10",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=2,
        fps_cap=10,
    )
    primary_model = Model(
        id=primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car", "bus", "truck"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    secondary_model = Model(
        id=secondary_model_id,
        name="PPE",
        version="lab-1",
        task=ModelTask.ATTRIBUTE,
        path="/models/ppe.onnx",
        format=ModelFormat.ONNX,
        classes=["hi_vis", "hard_hat"],
        input_shape={"width": 224, "height": 224},
        sha256="b" * 64,
        size_bytes=456,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=secondary_model,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.camera_id == camera_id
    assert config.mode is ProcessingMode.CENTRAL
    assert config.camera.rtsp_url == "rtsp://lab-camera.local/live"
    assert config.camera.frame_skip == 2
    assert config.camera.fps_cap == 10
    assert config.model.name == "YOLO12n"
    assert config.model.path == "/models/yolo12n.onnx"
    assert config.model.classes == ["person", "car", "bus", "truck"]
    assert config.secondary_model is not None
    assert config.secondary_model.name == "PPE"
    assert config.publish.subject_prefix == "evt.tracking"
    assert config.publish.http_fallback_url is None
    assert config.stream.model_dump() == {
        "profile_id": "720p10",
        "kind": "transcode",
        "width": 1280,
        "height": 720,
        "fps": 10,
    }
    assert config.tracker.tracker_type is TrackerType.BOTSORT
    assert config.tracker.frame_rate == 10
    assert config.privacy.blur_faces is True
    assert config.privacy.blur_plates is False
    assert config.active_classes == ["bus", "truck"]
    assert config.attribute_rules == [{"kind": "ppe"}]
    assert [zone.model_dump(exclude_none=True, mode="python") for zone in config.zones] == [
        {"id": "gate-1", "type": "line"}
    ]
    assert config.homography == {
        "src_points": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "dst_points": [[0, 0], [10, 0], [10, 10], [0, 10]],
        "ref_distance_m": 12.5,
    }


def test_edge_native_browser_delivery_keeps_passthrough_stream() -> None:
    camera = Camera(
        id=uuid4(),
        site_id=uuid4(),
        edge_node_id=uuid4(),
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={"blur_faces": False, "blur_plates": False, "method": "gaussian", "strength": 7},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=17,
    )
    primary_model = Model(
        id=camera.primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.stream.model_dump() == {
        "profile_id": "native",
        "kind": "passthrough",
        "width": None,
        "height": None,
        "fps": 17,
    }
    assert config.model.classes == ["person", "car"]


def test_central_native_browser_delivery_uses_processed_full_rate_stream() -> None:
    camera = Camera(
        id=uuid4(),
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={"blur_faces": False, "blur_plates": False, "method": "gaussian", "strength": 7},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=17,
    )
    primary_model = Model(
        id=camera.primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.stream.model_dump() == {
        "profile_id": "native",
        "kind": "transcode",
        "width": None,
        "height": None,
        "fps": 17,
    }
