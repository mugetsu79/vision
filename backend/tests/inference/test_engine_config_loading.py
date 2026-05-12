from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from argus.core.config import Settings
from argus.inference.engine import load_engine_config

ENGINE_PATH = Path(__file__).resolve().parents[2] / "src" / "argus" / "inference" / "engine.py"


@pytest.mark.asyncio
async def test_load_engine_config_sends_bearer_token_when_configured() -> None:
    camera_id = uuid4()
    seen_authorization: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_authorization.append(request.headers.get("Authorization"))
        return httpx.Response(
            200,
            json={
                "camera_id": str(camera_id),
                "mode": "central",
                "camera": {
                    "rtsp_url": "rtsp://lab-camera.local/live",
                    "frame_skip": 1,
                    "fps_cap": 10,
                },
                "publish": {
                    "subject_prefix": "evt.tracking",
                    "http_fallback_url": None,
                },
                "stream": {},
                "model": {
                    "name": "YOLO12n",
                    "path": "/models/yolo12n.onnx",
                    "classes": ["car", "bus"],
                    "input_shape": {"width": 640, "height": 640},
                    "confidence_threshold": 0.25,
                    "iou_threshold": 0.45,
                },
                "tracker": {
                    "tracker_type": "botsort",
                    "frame_rate": 10,
                },
                "privacy": {
                    "blur_faces": True,
                    "blur_plates": False,
                },
                "active_classes": ["bus"],
                "attribute_rules": [],
                "incident_rules": [
                    {
                        "id": str(uuid4()),
                        "camera_id": str(camera_id),
                        "enabled": True,
                        "name": "Restricted person",
                        "incident_type": "restricted_person",
                        "severity": "critical",
                        "predicate": {
                            "class_names": ["person"],
                            "zone_ids": ["restricted"],
                            "min_confidence": 0.7,
                            "attributes": {"hi_vis": False},
                        },
                        "action": "record_clip",
                        "cooldown_seconds": 60,
                        "webhook_url": None,
                        "rule_hash": "c" * 64,
                    }
                ],
                "zones": [],
                "homography": None,
            },
        )

    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        api_base_url="http://testserver",
        api_bearer_token="worker-token",
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=settings.api_base_url,
    ) as client:
        config = await load_engine_config(camera_id, settings=settings, http_client=client)

    assert config.camera_id == camera_id
    assert seen_authorization == ["Bearer worker-token"]
    assert config.incident_rules[0].incident_type == "restricted_person"
    assert config.incident_rules[0].rule_hash == "c" * 64


@pytest.mark.asyncio
async def test_load_engine_config_reports_api_base_url_on_connect_error() -> None:
    camera_id = uuid4()
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        api_base_url="http://192.168.1.20:8000",
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=settings.api_base_url,
    ) as client:
        with pytest.raises(RuntimeError, match="ARGUS_API_BASE_URL"):
            await load_engine_config(camera_id, settings=settings, http_client=client)


def test_worker_api_headers_is_defined_before_main_guard() -> None:
    source = ENGINE_PATH.read_text(encoding="utf-8")

    assert source.index("def _worker_api_headers") < source.index('if __name__ == "__main__"')
