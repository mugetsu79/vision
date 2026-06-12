#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import TypedDict

_ENV_THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
_METRIC_SAMPLE_LIMIT = 50
_METRIC_NAME_VALUE_RE = re.compile(
    r"^([A-Za-z_:][A-Za-z0-9_:]*)\s+(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$"
)


class _ThreadStat(TypedDict):
    tid: int
    user_seconds: float
    system_seconds: float
    total_seconds: float


def _clock_ticks_per_second() -> float:
    try:
        return float(os.sysconf("SC_CLK_TCK"))
    except (AttributeError, OSError, ValueError):
        return 100.0


def _thread_stat_from_line(line: str, *, tid: int, clock_ticks: float) -> _ThreadStat | None:
    command_end = line.rfind(")")
    if command_end < 0:
        return None
    fields = line[command_end + 2 :].split()
    if len(fields) <= 12:
        return None
    try:
        user_seconds = int(fields[11]) / clock_ticks
        system_seconds = int(fields[12]) / clock_ticks
    except ValueError:
        return None
    return {
        "tid": tid,
        "user_seconds": user_seconds,
        "system_seconds": system_seconds,
        "total_seconds": user_seconds + system_seconds,
    }


def collect_proc_cpu_seconds(pid: int) -> dict[str, object]:
    task_dir = Path("/proc") / str(pid) / "task"
    if not task_dir.exists():
        return {
            "process_cpu_seconds": {
                "available": False,
                "reason": "procfs task stats unavailable",
            },
            "thread_cpu_seconds": {
                "available": False,
                "thread_count": 0,
                "threads": [],
            },
        }

    clock_ticks = _clock_ticks_per_second()
    threads: list[_ThreadStat] = []
    for stat_path in sorted(task_dir.glob("*/stat")):
        try:
            tid = int(stat_path.parent.name)
            stat = _thread_stat_from_line(
                stat_path.read_text(encoding="utf-8"),
                tid=tid,
                clock_ticks=clock_ticks,
            )
        except (OSError, ValueError):
            continue
        if stat is not None:
            threads.append(stat)

    if not threads:
        return {
            "process_cpu_seconds": {
                "available": False,
                "reason": "no readable procfs task stats",
            },
            "thread_cpu_seconds": {
                "available": False,
                "thread_count": 0,
                "threads": [],
            },
        }

    user_seconds = sum(thread["user_seconds"] for thread in threads)
    system_seconds = sum(thread["system_seconds"] for thread in threads)
    top_threads = sorted(
        threads,
        key=lambda thread: thread["total_seconds"],
        reverse=True,
    )[:32]
    return {
        "process_cpu_seconds": {
            "available": True,
            "user_seconds": user_seconds,
            "system_seconds": system_seconds,
            "total_seconds": user_seconds + system_seconds,
            "thread_count": len(threads),
        },
        "thread_cpu_seconds": {
            "available": True,
            "thread_count": len(threads),
            "threads": top_threads,
        },
    }


def environment_thread_settings() -> dict[str, str | None]:
    return {key: os.environ.get(key) for key in _ENV_THREAD_KEYS}


def fetch_metrics_summary(url: str | None, *, timeout_seconds: float) -> dict[str, object]:
    if url is None:
        return {"available": False, "reason": "not requested"}

    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            body = response.read(256_000).decode("utf-8", errors="replace")
            status_code = response.status
    except (OSError, urllib.error.URLError) as exc:
        return {
            "available": False,
            "reason": type(exc).__name__,
        }

    samples: dict[str, float] = {}
    total_lines = 0
    skipped_lines = 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        total_lines += 1
        match = _METRIC_NAME_VALUE_RE.match(stripped)
        if match is None:
            skipped_lines += 1
            continue
        if len(samples) < _METRIC_SAMPLE_LIMIT:
            samples[match.group(1)] = float(match.group(2))

    return {
        "available": True,
        "status_code": status_code,
        "total_metric_lines": total_lines,
        "skipped_metric_lines": skipped_lines,
        "numeric_samples": samples,
        "sample_limit": _METRIC_SAMPLE_LIMIT,
    }


def build_probe_payload(
    *,
    origin: str,
    pid: int,
    metrics_url: str | None,
    metrics_timeout_seconds: float,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "origin": origin,
        "target_pid": pid,
        "environment_thread_settings": environment_thread_settings(),
        "metrics_summary": fetch_metrics_summary(
            metrics_url,
            timeout_seconds=metrics_timeout_seconds,
        ),
        "notes": [],
    }
    payload.update(collect_proc_cpu_seconds(pid))
    if origin == "central":
        payload["notes"] = [
            "Current runtime evidence is Dockerized CPU only; no M4 GPU/CoreML "
            "acceleration is claimed."
        ]
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect sanitized local worker CPU and metrics evidence."
    )
    parser.add_argument("--origin", choices=("edge", "central"), required=True)
    parser.add_argument(
        "--pid",
        type=int,
        default=os.getpid(),
        help="Process ID to inspect via procfs task stats; defaults to this process.",
    )
    parser.add_argument(
        "--metrics-url",
        help="Optional worker metrics endpoint. Only plain metric names and numeric values are emitted.",
    )
    parser.add_argument(
        "--metrics-timeout-seconds",
        type=float,
        default=1.0,
        help="Timeout for the optional metrics endpoint.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    payload = build_probe_payload(
        origin=args.origin,
        pid=args.pid,
        metrics_url=args.metrics_url,
        metrics_timeout_seconds=args.metrics_timeout_seconds,
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
