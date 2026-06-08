#!/usr/bin/env python3
import argparse
import json
import os
import re
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

    return SmokeCheck(
        name="Real RTSP source",
        status=SmokeStatus.BLOCKED,
        evidence=[
            "Real RTSP probe not implemented in skeleton; "
            f"URL redacted as {redact_rtsp_url(value)}"
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
    return checks


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the whole-product live smoke harness.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--real-rtsp", choices=["none", "720p", "1296p"], default="none")
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
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
