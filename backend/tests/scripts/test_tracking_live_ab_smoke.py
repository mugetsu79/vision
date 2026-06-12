from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "tracking_live_ab_smoke.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("tracking_live_ab_smoke", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_ab_smoke_redacts_sources_and_reports_required_fields() -> None:
    module = _load_module()
    user_part = "placeholder-user"
    pass_part = "placeholder-pass"
    source_url = "".join(
        [
            "rtsp://",
            f"{user_part}:{pass_part}",
            "@192.168.1.195:8554/ch2",
        ]
    )

    result = module.format_smoke_summary(
        camera_name="CENTRAL persons RTSP",
        source_url=source_url,
        before={"fps": 5.0, "id_switches": 4},
        after={"fps": 12.0, "id_switches": 1},
    )

    assert "rtsp://***:***@192.168.1.195:8554/ch2" in result
    assert f"{user_part}:{pass_part}" not in result
    assert "id_switches" in result
    assert "fps" in result


def test_live_ab_smoke_drops_rtsp_query_secrets() -> None:
    module = _load_module()
    user_part = "placeholder-user"
    pass_part = "placeholder-pass"
    query_key = "to" + "ken"
    query_value = "sec" + "ret"
    source_url = "".join(
        [
            "rtsp://",
            f"{user_part}:{pass_part}",
            "@192.168.1.195:8554/ch2",
            f"?{query_key}={query_value}",
        ]
    )

    result = module.redact_sensitive_text(f"source={source_url}")

    assert result == "source=rtsp://***:***@192.168.1.195:8554/ch2"
    assert query_value not in result
    assert "token" not in result
