from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from pytest import MonkeyPatch

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "validation" / "whole_product_live_smoke.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("whole_product_live_smoke", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))


def _report_check(report: dict[str, Any], name: str) -> dict[str, Any]:
    for check in report["checks"]:
        if check["name"] == name:
            return cast("dict[str, Any]", check)
    raise AssertionError(f"Missing report check: {name}")


def test_status_names_distinguish_blocked_and_not_run() -> None:
    module = _load_module()

    assert [status.value for status in module.SmokeStatus] == [
        "PASS",
        "FAIL",
        "BLOCKED",
        "NOT RUN",
    ]


def test_rtsp_redaction_keeps_credentials_out_of_report() -> None:
    module = _load_module()

    assert module.redact_rtsp_url("rtsp://user:pass@host/ch1") == "rtsp://***@host/ch1"


def test_rtsp_redaction_handles_uppercase_scheme() -> None:
    module = _load_module()

    redacted = module.redact_rtsp_url("RtSp://user:pass@host/ch1")

    assert redacted == "RtSp://***@host/ch1"
    assert "user" not in redacted
    assert "pass" not in redacted


def test_rtsp_redaction_leaves_uncredentialed_urls_unchanged() -> None:
    module = _load_module()

    assert module.redact_rtsp_url("rtsp://host/ch1") == "rtsp://host/ch1"


def test_rtsp_redaction_redacts_multiple_urls_in_one_string() -> None:
    module = _load_module()

    redacted = module.redact_rtsp_url(
        "primary rtsp://alice:first@camera-a.local/ch1 "
        "backup RTSP://bob:second@camera-b.local/ch2"
    )

    assert "rtsp://***@camera-a.local/ch1" in redacted
    assert "RTSP://***@camera-b.local/ch2" in redacted
    assert "alice" not in redacted
    assert "first" not in redacted
    assert "bob" not in redacted
    assert "second" not in redacted


def test_write_report_serializes_enum_values(tmp_path: Path) -> None:
    module = _load_module()
    report_path = tmp_path / "report.json"

    module.write_report(
        report_path,
        [
            module.SmokeCheck(
                name="status taxonomy",
                status=module.SmokeStatus.PASS,
                evidence=["PASS, FAIL, BLOCKED, NOT RUN are distinct"],
            )
        ],
        metadata={"api_url": "http://api.test", "real_rtsp": "none"},
    )

    assert _read_json(report_path) == {
        "metadata": {"api_url": "http://api.test", "real_rtsp": "none"},
        "checks": [
            {
                "name": "status taxonomy",
                "status": "PASS",
                "evidence": ["PASS, FAIL, BLOCKED, NOT RUN are distinct"],
            }
        ]
    }


def test_main_writes_report_file(tmp_path: Path) -> None:
    module = _load_module()
    report_path = tmp_path / "whole-product-smoke.json"

    result = module.main(
        [
            "--api-url",
            "http://api.local.test:8000",
            "--report",
            str(report_path),
            "--real-rtsp",
            "none",
        ]
    )

    assert result == 0
    report = _read_json(report_path)
    assert report["metadata"] == {
        "api_url": "http://api.local.test:8000",
        "real_rtsp": "none",
    }
    assert report["checks"][0]["name"] == "status taxonomy"
    assert report["checks"][0]["status"] == "PASS"
    real_rtsp_check = _report_check(report, "Real RTSP source")
    assert real_rtsp_check["status"] == "NOT RUN"
    assert "skipped" in " ".join(real_rtsp_check["evidence"]).lower()


def test_real_rtsp_env_name_maps_optional_lanes() -> None:
    module = _load_module()

    assert module.real_rtsp_env_name("none") is None
    assert module.real_rtsp_env_name("720p") == "VEZOR_SMOKE_REAL_RTSP_720P_URL"
    assert module.real_rtsp_env_name("1296p") == "VEZOR_SMOKE_REAL_RTSP_1296P_URL"


def test_real_rtsp_missing_env_reports_blocked_with_env_name_only() -> None:
    module = _load_module()

    for selection, env_name in [
        ("720p", "VEZOR_SMOKE_REAL_RTSP_720P_URL"),
        ("1296p", "VEZOR_SMOKE_REAL_RTSP_1296P_URL"),
    ]:
        check = module.build_real_rtsp_check(selection, {})
        evidence = " ".join(check.evidence)

        assert check.name == "Real RTSP source"
        assert check.status.value == "BLOCKED"
        assert env_name in evidence
        assert "rtsp://" not in evidence.lower()


def test_real_rtsp_present_env_reports_blocked_without_raw_credentials() -> None:
    module = _load_module()
    raw_url = "rtsp://alice:s3cr3t@camera.local/ch1"

    check = module.build_real_rtsp_check(
        "720p",
        {"VEZOR_SMOKE_REAL_RTSP_720P_URL": raw_url},
    )
    evidence = " ".join(check.evidence)

    assert check.status.value == "BLOCKED"
    assert "Real RTSP probe not implemented in skeleton" in evidence
    assert "rtsp://***@camera.local/ch1" in evidence
    assert raw_url not in evidence
    assert "alice" not in evidence
    assert "s3cr3t" not in evidence


def test_main_reports_selected_real_rtsp_lane_when_env_missing(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    module = _load_module()
    report_path = tmp_path / "whole-product-smoke.json"
    monkeypatch.delenv("VEZOR_SMOKE_REAL_RTSP_1296P_URL", raising=False)

    result = module.main(["--report", str(report_path), "--real-rtsp", "1296p"])

    assert result == 0
    report = _read_json(report_path)
    real_rtsp_check = _report_check(report, "Real RTSP source")
    assert real_rtsp_check["status"] == "BLOCKED"
    evidence = " ".join(real_rtsp_check["evidence"])
    assert "VEZOR_SMOKE_REAL_RTSP_1296P_URL" in evidence
    assert "rtsp://" not in evidence.lower()
