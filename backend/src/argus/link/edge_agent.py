from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from argus.link.udp_sequence import (
    HEADER_LENGTH,
    SequenceReply,
    build_probe_packet,
    parse_probe_packet,
    summarize_sequence_results,
)


@dataclass(frozen=True, slots=True)
class PingStatistics:
    packet_count: int
    packets_received: int
    latency_ms: int
    jitter_ms: float | None = None
    duration_ms: int | None = None
    measurement_metadata: dict[str, object] | None = None


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


def build_udp_sequence_edge_sample_payload(
    *,
    agent_id: str,
    agent_label: str | None,
    stats: PingStatistics,
    dscp: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "agent_id": agent_id,
        "method": "udp_sequence",
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
    if stats.measurement_metadata is not None:
        payload["measurement_metadata"] = stats.measurement_metadata
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


async def fetch_edge_agent_config(
    *,
    config_url: str,
    bearer_token: str,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, object]:
    client = http_client or httpx.AsyncClient()
    owns_client = http_client is None
    try:
        response = await client.get(
            config_url,
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(f"Edge-agent config fetch failed with HTTP {response.status_code}")
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


async def run_udp_sequence_probe(
    *,
    reflector_host: str,
    reflector_port: int,
    reflector_secret: str,
    reflector_key_id: str,
    packet_count: int,
    packet_spacing_ms: int,
    loss_timeout_ms: int,
    dscp: int | None = None,
) -> PingStatistics:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[bytes, int]] = asyncio.Queue()

    class ClientProtocol(asyncio.DatagramProtocol):
        transport: asyncio.DatagramTransport

        def connection_made(self, transport: asyncio.BaseTransport) -> None:
            self.transport = transport  # type: ignore[assignment]
            if dscp is not None:
                socket_info = self.transport.get_extra_info("socket")
                if isinstance(socket_info, socket.socket):
                    socket_info.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, dscp << 2)

        def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
            queue.put_nowait((data, time.monotonic_ns()))

    transport, protocol = await loop.create_datagram_endpoint(
        ClientProtocol,
        remote_addr=(reflector_host, reflector_port),
    )
    datagram_transport = protocol.transport
    secret_bytes = reflector_secret.encode("utf-8")
    session_id = os.urandom(16)
    sent_sequences: list[int] = []
    sequence_deadlines_ns: dict[int, int] = {}
    replies: list[SequenceReply] = []
    start_ns = time.monotonic_ns()
    try:
        for sequence in range(1, packet_count + 1):
            transmit_ns = time.monotonic_ns()
            sent_sequences.append(sequence)
            sequence_deadlines_ns[sequence] = transmit_ns + (loss_timeout_ms * 1_000_000)
            datagram_transport.sendto(
                build_probe_packet(
                    session_id=session_id,
                    sequence=sequence,
                    transmit_ns=transmit_ns,
                    nonce=secrets.randbelow(2**64),
                    secret=secret_bytes,
                    reply=False,
                )
            )
            if sequence != packet_count:
                await asyncio.sleep(packet_spacing_ms / 1000)

        deadline = loop.time() + (loss_timeout_ms / 1000)
        seen_sequences: set[int] = set()
        while loop.time() < deadline and len(seen_sequences) < packet_count:
            remaining = max(0.0, deadline - loop.time())
            try:
                data, received_ns = await asyncio.wait_for(queue.get(), timeout=remaining)
            except TimeoutError:
                break
            try:
                packet = parse_probe_packet(data, secret=secret_bytes)
            except ValueError:
                continue
            if packet.session_id != session_id or not packet.reply:
                continue
            rtt_ms = (received_ns - packet.transmit_ns) / 1_000_000
            sequence_deadline_ns = sequence_deadlines_ns.get(packet.sequence, received_ns)
            replies.append(
                SequenceReply(
                    sequence=packet.sequence,
                    rtt_ms=rtt_ms,
                    late=received_ns > sequence_deadline_ns,
                )
            )
            seen_sequences.add(packet.sequence)
    finally:
        transport.close()

    duration_ms = round((time.monotonic_ns() - start_ns) / 1_000_000)
    stats = summarize_sequence_results(sent_sequences=sent_sequences, replies=replies)
    metadata: dict[str, object] = {
        "protocol": "vezor_udp_sequence",
        "protocol_version": 1,
        "reflector_key_id": reflector_key_id,
        "reflector_address": reflector_host,
        "reflector_port": reflector_port,
        "session_id": session_id.hex(),
        "packet_count": stats.packet_count,
        "packets_received": stats.packets_received,
        "packets_lost": stats.packets_lost,
        "packets_late": stats.packets_late,
        "packets_duplicate": stats.packets_duplicate,
        "packets_out_of_order": stats.packets_out_of_order,
        "loss_timeout_ms": loss_timeout_ms,
        "packet_spacing_ms": packet_spacing_ms,
        "packet_size_bytes": HEADER_LENGTH,
        "clock_sync": "not_required_round_trip",
    }
    if stats.rtt_min_ms is not None:
        metadata["rtt_min_ms"] = stats.rtt_min_ms
    if stats.rtt_avg_ms is not None:
        metadata["rtt_avg_ms"] = stats.rtt_avg_ms
    if stats.rtt_p95_ms is not None:
        metadata["rtt_p95_ms"] = stats.rtt_p95_ms
    if stats.rtt_max_ms is not None:
        metadata["rtt_max_ms"] = stats.rtt_max_ms
    if stats.rtt_variation_ms is not None:
        metadata["rtt_variation_ms"] = stats.rtt_variation_ms
    if dscp is not None:
        metadata["dscp"] = dscp

    return PingStatistics(
        packet_count=stats.packet_count,
        packets_received=stats.packets_received,
        latency_ms=round(stats.rtt_avg_ms or 0),
        jitter_ms=stats.rtt_variation_ms,
        duration_ms=duration_ms,
        measurement_metadata=metadata,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Vezor Core Link edge-agent probes.")
    parser.add_argument("--api-base-url", default=os.getenv("ARGUS_API_BASE_URL"))
    parser.add_argument("--bearer-token", default=os.getenv("ARGUS_API_BEARER_TOKEN"))
    parser.add_argument("--config-url", default=os.getenv("ARGUS_LINK_EDGE_AGENT_CONFIG_URL"))
    parser.add_argument("--site-id", default=os.getenv("ARGUS_LINK_SITE_ID"))
    parser.add_argument("--target-id", default=os.getenv("ARGUS_LINK_TARGET_ID"))
    parser.add_argument("--target", default=os.getenv("ARGUS_LINK_TARGET"))
    parser.add_argument(
        "--method",
        choices=("icmp_sequence", "udp_sequence"),
        default=os.getenv("ARGUS_LINK_METHOD", "icmp_sequence"),
    )
    parser.add_argument("--reflector", default=os.getenv("ARGUS_LINK_REFLECTOR"))
    parser.add_argument(
        "--reflector-port",
        type=int,
        default=int(os.getenv("ARGUS_LINK_REFLECTOR_PORT", "8622")),
    )
    parser.add_argument("--reflector-key-id", default=os.getenv("ARGUS_LINK_REFLECTOR_KEY_ID"))
    parser.add_argument("--reflector-secret", default=os.getenv("ARGUS_LINK_REFLECTOR_SECRET"))
    parser.add_argument("--packet-spacing-ms", type=int, default=100)
    parser.add_argument("--loss-timeout-ms", type=int, default=1000)
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
    if not args.site_id and not args.config_url:
        parser.error("--site-id or ARGUS_LINK_SITE_ID is required")
    if not args.target_id and not args.config_url:
        parser.error("--target-id or ARGUS_LINK_TARGET_ID is required")
    if not args.target and not args.config_url:
        parser.error("--target or ARGUS_LINK_TARGET is required")
    if args.packet_count <= 0 or args.packet_count > 10_000:
        parser.error("--packet-count must be between 1 and 10000")
    if args.packet_spacing_ms <= 0:
        parser.error("--packet-spacing-ms must be positive")
    if args.loss_timeout_ms <= 0:
        parser.error("--loss-timeout-ms must be positive")
    if args.dscp is not None and (args.dscp < 0 or args.dscp > 63):
        parser.error("--dscp must be between 0 and 63")
    if args.method == "udp_sequence" and not args.config_url:
        if not args.reflector:
            parser.error("--reflector or ARGUS_LINK_REFLECTOR is required for udp_sequence")
        if args.reflector_port <= 0 or args.reflector_port > 65_535:
            parser.error("--reflector-port must be between 1 and 65535")
        if not args.reflector_secret:
            parser.error("--reflector-secret or ARGUS_LINK_REFLECTOR_SECRET is required")
        if not args.reflector_key_id:
            parser.error("--reflector-key-id or ARGUS_LINK_REFLECTOR_KEY_ID is required")
    return args


async def async_main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.config_url:
        config = await fetch_edge_agent_config(
            config_url=args.config_url,
            bearer_token=args.bearer_token,
        )
        _apply_edge_agent_config(args, config)
        _validate_resolved_args(args)
    while True:
        if args.method == "udp_sequence":
            stats = await run_udp_sequence_probe(
                reflector_host=args.reflector,
                reflector_port=args.reflector_port,
                reflector_secret=args.reflector_secret,
                reflector_key_id=args.reflector_key_id,
                packet_count=args.packet_count,
                packet_spacing_ms=args.packet_spacing_ms,
                loss_timeout_ms=args.loss_timeout_ms,
                dscp=args.dscp,
            )
            payload = build_udp_sequence_edge_sample_payload(
                agent_id=args.agent_id,
                agent_label=args.agent_label,
                stats=stats,
                dscp=args.dscp,
            )
        else:
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


def _apply_edge_agent_config(args: argparse.Namespace, config: Mapping[str, object]) -> None:
    args.site_id = args.site_id or _config_string(config, "site_id")
    args.target_id = args.target_id or _config_string(config, "target_id")
    args.method = _config_string(config, "method") or args.method
    args.reflector = args.reflector or _config_string(config, "reflector_address")
    args.target = args.target or args.reflector
    args.reflector_port = _config_int(config, "reflector_port") or args.reflector_port
    args.reflector_key_id = args.reflector_key_id or _config_string(config, "reflector_key_id")
    args.reflector_secret = args.reflector_secret or _config_string(config, "reflector_secret")
    args.packet_count = _config_int(config, "packet_count") or args.packet_count
    args.packet_spacing_ms = _config_int(config, "packet_spacing_ms") or args.packet_spacing_ms
    args.loss_timeout_ms = _config_int(config, "loss_timeout_ms") or args.loss_timeout_ms
    args.dscp = _config_int(config, "dscp") if config.get("dscp") is not None else args.dscp


def _validate_resolved_args(args: argparse.Namespace) -> None:
    missing = [
        name
        for name in ("site_id", "target_id", "target")
        if not getattr(args, name, None)
    ]
    if missing:
        raise RuntimeError(f"Edge-agent config missing required field(s): {', '.join(missing)}")
    if args.method == "udp_sequence":
        missing_udp = [
            name
            for name in ("reflector", "reflector_key_id", "reflector_secret")
            if not getattr(args, name, None)
        ]
        if missing_udp:
            raise RuntimeError(
                "Edge-agent config missing required UDP field(s): "
                f"{', '.join(missing_udp)}"
            )
        if args.reflector_port <= 0 or args.reflector_port > 65_535:
            raise RuntimeError("Edge-agent config reflector_port must be between 1 and 65535")


def _config_string(config: Mapping[str, object], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _config_int(config: Mapping[str, object], key: str) -> int | None:
    value = config.get(key)
    if value is None:
        return None
    return int(value)


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
