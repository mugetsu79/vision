#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SmokeStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT RUN"


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    status: SmokeStatus
    evidence: list[str] = field(default_factory=list)


REQUIRED_CLOSURE_LANES: tuple[str, ...] = (
    "Fresh destructive reset proof",
    "First-run auth and tenant claims",
    "Central supervisor credential binding",
    "Real Jetson supervisor API",
    "Jetson model sync inventory",
    "Jetson TensorRT artifact build",
    "Office RTSP live native annotated",
    "Deterministic history incident evidence",
    "Billing usage invoice FleetOps",
    "Master reflector secret distribution",
    "UDP edge-agent probe",
    "Core Link master target-only behavior",
)


_RTSP_CREDENTIALS_RE = re.compile(r"\b([Rr][Tt][Ss][Pp]://)([^/@\s]+@)")
_URL_CREDENTIALS_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9+.-]*://)([^/@\s]+@)")


def redact_rtsp_url(value: str) -> str:
    return _RTSP_CREDENTIALS_RE.sub(lambda match: f"{match.group(1)}***@", value)


def _redact_url_credentials(value: str) -> str:
    return _URL_CREDENTIALS_RE.sub(lambda match: f"{match.group(1)}***@", value)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def real_rtsp_env_name(selection: str) -> str | None:
    if selection == "none":
        return None
    if selection == "720p":
        return "VEZOR_SMOKE_REAL_RTSP_720P_URL"
    if selection == "1296p":
        return "VEZOR_SMOKE_REAL_RTSP_1296P_URL"
    raise ValueError(f"Unsupported real RTSP selection: {selection}")


def build_real_rtsp_check(
    selection: str,
    environ: Mapping[str, str] | None = None,
) -> SmokeCheck:
    env_name = real_rtsp_env_name(selection)
    if env_name is None:
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.NOT_RUN,
            evidence=["Skipped because --real-rtsp=none"],
        )

    source = os.environ if environ is None else environ
    value = source.get(env_name)
    if not value:
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.BLOCKED,
            evidence=[f"Missing {env_name}; set it locally to enable the real RTSP lane"],
        )

    return probe_real_rtsp_source(value)


def probe_real_rtsp_source(value: str, timeout_seconds: int = 20) -> SmokeCheck:
    redacted_url = redact_rtsp_url(value)
    command = [
        "ffprobe",
        "-v",
        "error",
        "-rtsp_transport",
        "tcp",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,codec_name,avg_frame_rate",
        "-of",
        "json",
        value,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.BLOCKED,
            evidence=["ffprobe is not installed on the host running the smoke harness."],
        )
    except subprocess.TimeoutExpired:
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.FAIL,
            evidence=[f"ffprobe timed out after {timeout_seconds}s for {redacted_url}"],
        )

    if completed.returncode != 0:
        stderr = redact_rtsp_url((completed.stderr or "").strip())
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.FAIL,
            evidence=[
                f"ffprobe failed for {redacted_url}",
                f"stderr={stderr[:500] if stderr else 'empty'}",
            ],
        )

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.FAIL,
            evidence=[f"ffprobe returned non-JSON stream metadata for {redacted_url}"],
        )
    streams = payload.get("streams")
    if not isinstance(streams, list) or not streams:
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.FAIL,
            evidence=[f"ffprobe found no video stream for {redacted_url}"],
        )

    stream = streams[0]
    if not isinstance(stream, dict):
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.FAIL,
            evidence=[f"ffprobe returned malformed stream metadata for {redacted_url}"],
        )
    width = stream.get("width")
    height = stream.get("height")
    codec = stream.get("codec_name") or "unknown"
    frame_rate = stream.get("avg_frame_rate") or "unknown"
    if not isinstance(width, int) or not isinstance(height, int):
        return SmokeCheck(
            name="Real RTSP source",
            status=SmokeStatus.FAIL,
            evidence=[f"ffprobe stream metadata was missing width/height for {redacted_url}"],
        )
    return SmokeCheck(
        name="Real RTSP source",
        status=SmokeStatus.PASS,
        evidence=[
            f"ffprobe video stream width={width} height={height} codec={codec} avg_frame_rate={frame_rate}",
            f"source={redacted_url}",
        ],
    )


def report_real_rtsp_not_run(selection: str) -> SmokeCheck | None:
    if selection != "none":
        return None
    return build_real_rtsp_check(selection, {})


def write_report(
    path: Path,
    checks: list[SmokeCheck],
    metadata: Mapping[str, str] | None = None,
) -> None:
    payload = {
        "metadata": dict(metadata or {}),
        "checks": [
            {
                "name": check.name,
                "status": check.status.value,
                "evidence": list(check.evidence),
            }
            for check in checks
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def status_taxonomy_check() -> SmokeCheck:
    return SmokeCheck(
        name="status taxonomy",
        status=SmokeStatus.PASS,
        evidence=["SmokeStatus exposes PASS, FAIL, BLOCKED, and NOT RUN"],
    )


def default_closure_checks() -> list[SmokeCheck]:
    return [
        SmokeCheck(
            name=name,
            status=SmokeStatus.NOT_RUN,
            evidence=["Live validation has not executed this lane in this harness run."],
        )
        for name in REQUIRED_CLOSURE_LANES
    ]


def build_central_credential_check(proof: Mapping[str, object]) -> SmokeCheck:
    config_hash = str(proof.get("config_secret_sha256") or "")
    runtime_hash = str(proof.get("runtime_credential_sha256") or "")
    status_value = str(proof.get("central_node_credential_status") or "")
    manual_repair_used = bool(proof.get("manual_repair_used"))
    evidence = [
        f"config credential sha256={config_hash or 'missing'}",
        f"runtime credential sha256={runtime_hash or 'missing'}",
        f"central node credential_status={status_value or 'missing'}",
    ]
    if manual_repair_used:
        return SmokeCheck(
            name="Central supervisor credential binding",
            status=SmokeStatus.FAIL,
            evidence=[*evidence, "Manual repair was required after first-run."],
        )
    if config_hash and runtime_hash and config_hash == runtime_hash and status_value == "active":
        return SmokeCheck(
            name="Central supervisor credential binding",
            status=SmokeStatus.PASS,
            evidence=evidence,
        )
    return SmokeCheck(
        name="Central supervisor credential binding",
        status=SmokeStatus.BLOCKED,
        evidence=evidence,
    )


def build_checks(
    api_url: str,
    real_rtsp: str,
    environ: Mapping[str, str] | None = None,
) -> list[SmokeCheck]:
    checks = [status_taxonomy_check()]
    checks.append(build_real_rtsp_check(real_rtsp, environ))
    checks.append(
        SmokeCheck(
            name="API target",
            status=SmokeStatus.NOT_RUN,
            evidence=["Live API orchestration deferred; --api-url accepted for future checks"],
        )
    )
    checks.extend(default_closure_checks())
    return checks


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the whole-product live smoke harness.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--real-rtsp", choices=["none", "720p", "1296p"], default="none")
    parser.add_argument("--token-env", default="VEZOR_SMOKE_TOKEN")
    parser.add_argument("--jetson-node-id")
    parser.add_argument("--office-site-id")
    parser.add_argument("--office-camera-id")
    parser.add_argument("--smoke-run-id")
    parser.add_argument("--reflector-config-url")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    checks = build_checks(args.api_url, args.real_rtsp)
    write_report(
        args.report,
        checks,
        metadata={
            "api_url": _redact_url_credentials(args.api_url),
            "real_rtsp": args.real_rtsp,
            "token_env": args.token_env,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
