#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

_RTSP_URL_RE = re.compile(r"\brtsp://[^\s<>'\"]+", re.IGNORECASE)
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b("
    r"token|access_token|refresh_token|bearer|password|passwd|pwd|secret|"
    r"sudo_password|node_credential|node_secret|registry_password|"
    r"registry_token|docker_password"
    r")([=:\s]+)([^\s,;]+)"
)
_BASIC_AUTH_URL_RE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9+.-]*://)([^/@\s:]+):([^/@\s]+)@"
)

_REQUIRED_EVIDENCE_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("processed FPS", ("processed_fps", "fps")),
    ("stage avg/p95", ("stage_avg_p95", "stage_avg", "stage_p95")),
    ("process CPU percent", ("process_cpu_percent", "cpu_percent")),
    ("RSS", ("rss", "rss_mb", "process_rss")),
    (
        "tracking diagnostics",
        ("tracking_diagnostics", "diagnostics", "id_switches", "fragmentation"),
    ),
    ("persisted frames", ("persisted_frames",)),
    ("broadcasted frames", ("broadcasted_frames",)),
    (
        "JetStream pending/ack-pending",
        (
            "jetstream_pending_ack_pending",
            "jetstream_pending",
            "jetstream_ack_pending",
        ),
    ),
    ("MediaMTX replace count", ("mediamtx_replace_count", "replace_count")),
    ("capture wait spike count", ("capture_wait_spike_count", "capture_wait_spikes")),
)


def _redact_rtsp_url(match: re.Match[str]) -> str:
    raw_url = match.group(0)
    parsed = urlsplit(raw_url)
    host = parsed.hostname or ""
    if not host:
        return "rtsp://***:***@unknown"
    netloc = host
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username is not None or parsed.password is not None:
        netloc = f"***:***@{netloc}"
    redacted = SplitResult(
        scheme=parsed.scheme,
        netloc=netloc,
        path=parsed.path,
        query="",
        fragment="",
    )
    return urlunsplit(redacted)


def redact_sensitive_text(text: str) -> str:
    """Return operator-safe text with credentials and process secrets removed."""
    redacted = _RTSP_URL_RE.sub(_redact_rtsp_url, text)
    redacted = _BEARER_RE.sub("Bearer ***", redacted)
    redacted = _SECRET_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}***",
        redacted,
    )
    return _BASIC_AUTH_URL_RE.sub(lambda match: f"{match.group(1)}***:***@", redacted)


def _value_for(summary: Mapping[str, object], aliases: tuple[str, ...]) -> object:
    if aliases == ("processed_fps", "fps") and (
        "processed_fps" in summary or "fps" in summary
    ):
        value = summary.get("processed_fps", summary.get("fps", "unknown"))
        return f"fps={value}"
    if len(aliases) == 2 and aliases == ("jetstream_pending", "jetstream_ack_pending"):
        return "unknown"
    if "jetstream_pending" in aliases and (
        "jetstream_pending" in summary or "jetstream_ack_pending" in summary
    ):
        pending = summary.get("jetstream_pending", "unknown")
        ack_pending = summary.get("jetstream_ack_pending", "unknown")
        return f"pending={pending}, ack_pending={ack_pending}"
    if "stage_avg" in aliases and ("stage_avg" in summary or "stage_p95" in summary):
        avg = summary.get("stage_avg", "unknown")
        p95 = summary.get("stage_p95", "unknown")
        return f"avg={avg}, p95={p95}"
    if "id_switches" in aliases and (
        "id_switches" in summary or "fragmentation" in summary
    ):
        id_switches = summary.get("id_switches", "unknown")
        fragmentation = summary.get("fragmentation", "unknown")
        return f"id_switches={id_switches}, fragmentation={fragmentation}"
    for alias in aliases:
        if alias in summary:
            return summary[alias]
    return "unknown"


def _format_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def format_smoke_summary(
    *,
    camera_name: str,
    source_url: str,
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> str:
    lines = [
        "# Tracking Live A/B Smoke Summary",
        "",
        f"camera: {camera_name}",
        f"source: {source_url}",
        "",
        "| Evidence | Before | After |",
        "| --- | --- | --- |",
    ]
    for label, aliases in _REQUIRED_EVIDENCE_FIELDS:
        before_value = _format_value(_value_for(before, aliases))
        after_value = _format_value(_value_for(after, aliases))
        lines.append(f"| {label} | {before_value} | {after_value} |")
    lines.extend(
        [
            "",
            "Manual acceptance thresholds:",
            "- central processed FPS >= 10",
            "- edge processed FPS >= 15",
            "- JetStream pending 0 after sample window",
            "- MediaMTX repeated replace count 0 after startup",
            "- capture wait spikes 0 after startup stabilization window",
            "- fallback active false",
            "- tracking ID switches lower than baseline on central two-person scene",
        ]
    )
    return redact_sensitive_text("\n".join(lines))


def _load_mapping(path: Path) -> Mapping[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Format a sanitized live tracking A/B smoke evidence summary."
    )
    parser.add_argument("--camera-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--before-json", type=Path, required=True)
    parser.add_argument("--after-json", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = format_smoke_summary(
        camera_name=args.camera_name,
        source_url=args.source_url,
        before=_load_mapping(args.before_json),
        after=_load_mapping(args.after_json),
    )
    if args.output is None:
        print(summary)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{summary}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
