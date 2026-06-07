from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class PingStatistics:
    packet_count: int
    packets_received: int
    latency_ms: int
    jitter_ms: float | None = None
    duration_ms: int | None = None


def parse_ping_output(output: str) -> PingStatistics:
    packet_match = re.search(
        r"(?P<sent>\d+)\s+packets transmitted,\s+"
        r"(?P<received>\d+)\s+(?:packets\s+)?received",
        output,
    )
    if packet_match is None:
        raise RuntimeError("Ping output did not include packet statistics.")

    sent = int(packet_match.group("sent"))
    received = int(packet_match.group("received"))
    if sent <= 0:
        raise RuntimeError("Ping output reported zero transmitted packets.")
    if received > sent:
        raise RuntimeError("Ping output reported more received packets than transmitted.")

    timing_match = re.search(
        r"(?:round-trip|rtt)\s+min/avg/max/(?:stddev|mdev)\s+=\s+"
        r"(?P<min>[0-9.]+)/(?P<avg>[0-9.]+)/(?P<max>[0-9.]+)/(?P<jitter>[0-9.]+)\s+ms",
        output,
    )
    duration_match = re.search(r"time\s+(?P<duration>[0-9.]+)\s*ms", output)
    return PingStatistics(
        packet_count=sent,
        packets_received=received,
        latency_ms=round(float(timing_match.group("avg"))) if timing_match is not None else 0,
        jitter_ms=(
            float(timing_match.group("jitter")) if timing_match is not None else None
        ),
        duration_ms=(
            round(float(duration_match.group("duration")))
            if duration_match is not None
            else None
        ),
    )


def build_edge_sample_payload(
    *,
    agent_id: str,
    agent_label: str | None,
    stats: PingStatistics,
    dscp: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "agent_id": agent_id,
        "method": "icmp_sequence",
        "packet_count": stats.packet_count,
        "packets_received": stats.packets_received,
        "latency_ms": stats.latency_ms,
    }
    if agent_label:
        payload["agent_label"] = agent_label
    if stats.jitter_ms is not None:
        payload["jitter_ms"] = stats.jitter_ms
    if stats.duration_ms is not None:
        payload["duration_ms"] = stats.duration_ms
    if dscp is not None:
        payload["dscp"] = dscp
    return payload


async def post_edge_sample(
    *,
    api_base_url: str,
    bearer_token: str,
    site_id: str,
    target_id: str,
    payload: Mapping[str, object],
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, object]:
    client = http_client or httpx.AsyncClient()
    owns_client = http_client is None
    path = f"/api/v1/link/sites/{site_id}/probe-targets/{target_id}/edge-samples"
    try:
        response = await client.post(
            f"{api_base_url.rstrip('/')}{path}",
            json=dict(payload),
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(
                f"Edge sample POST failed with HTTP {response.status_code}: {response.text}"
            )
        body: Any = response.json()
        return dict(body) if isinstance(body, Mapping) else {}
    finally:
        if owns_client:
            await client.aclose()


def run_ping_probe(
    *,
    target: str,
    packet_count: int,
    timeout_seconds: float,
) -> PingStatistics:
    command = _ping_command(
        target=target,
        packet_count=packet_count,
        timeout_seconds=timeout_seconds,
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return parse_ping_output(output)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Vezor Core Link edge-agent probes.")
    parser.add_argument("--api-base-url", default=os.getenv("ARGUS_API_BASE_URL"))
    parser.add_argument("--bearer-token", default=os.getenv("ARGUS_API_BEARER_TOKEN"))
    parser.add_argument("--site-id", default=os.getenv("ARGUS_LINK_SITE_ID"))
    parser.add_argument("--target-id", default=os.getenv("ARGUS_LINK_TARGET_ID"))
    parser.add_argument("--target", default=os.getenv("ARGUS_LINK_TARGET"))
    parser.add_argument(
        "--agent-id",
        default=os.getenv("ARGUS_LINK_EDGE_AGENT_ID") or platform.node() or "edge-agent",
    )
    parser.add_argument("--agent-label", default=os.getenv("ARGUS_LINK_EDGE_AGENT_LABEL"))
    parser.add_argument("--packet-count", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--interval-seconds", type=float, default=300.0)
    parser.add_argument("--dscp", type=int)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)

    if not args.api_base_url:
        parser.error("--api-base-url or ARGUS_API_BASE_URL is required")
    if not args.bearer_token:
        parser.error("--bearer-token or ARGUS_API_BEARER_TOKEN is required")
    if not args.site_id:
        parser.error("--site-id or ARGUS_LINK_SITE_ID is required")
    if not args.target_id:
        parser.error("--target-id or ARGUS_LINK_TARGET_ID is required")
    if not args.target:
        parser.error("--target or ARGUS_LINK_TARGET is required")
    if args.packet_count <= 0 or args.packet_count > 10_000:
        parser.error("--packet-count must be between 1 and 10000")
    if args.dscp is not None and (args.dscp < 0 or args.dscp > 63):
        parser.error("--dscp must be between 0 and 63")
    return args


async def async_main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    while True:
        stats = run_ping_probe(
            target=args.target,
            packet_count=args.packet_count,
            timeout_seconds=args.timeout_seconds,
        )
        payload = build_edge_sample_payload(
            agent_id=args.agent_id,
            agent_label=args.agent_label,
            stats=stats,
            dscp=args.dscp,
        )
        result = await post_edge_sample(
            api_base_url=args.api_base_url,
            bearer_token=args.bearer_token,
            site_id=args.site_id,
            target_id=args.target_id,
            payload=payload,
        )
        print(json.dumps(result, sort_keys=True))
        if args.once:
            return 0
        await asyncio.sleep(args.interval_seconds)


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


def _ping_command(
    *,
    target: str,
    packet_count: int,
    timeout_seconds: float,
) -> list[str]:
    if sys.platform == "darwin":
        timeout_ms = max(1, round(timeout_seconds * 1000))
        return ["ping", "-c", str(packet_count), "-W", str(timeout_ms), target]
    return ["ping", "-c", str(packet_count), "-W", str(max(1, round(timeout_seconds))), target]


if __name__ == "__main__":
    main()
