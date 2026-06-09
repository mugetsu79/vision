from __future__ import annotations

import inspect
import socket

import httpx
import pytest

from argus.link.edge_agent import (
    PingStatistics,
    build_edge_sample_payload,
    build_udp_sequence_edge_sample_payload,
    fetch_edge_agent_config,
    parse_args,
    parse_ping_output,
    post_edge_sample,
    run_udp_sequence_probe,
)
from argus.link.reflector import start_reflector, stop_reflector


def test_parse_macos_ping_output_reports_packets_and_timing() -> None:
    output = """
PING 8.8.8.8 (8.8.8.8): 56 data bytes
64 bytes from 8.8.8.8: icmp_seq=0 ttl=117 time=15.420 ms
64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=22.135 ms

--- 8.8.8.8 ping statistics ---
20 packets transmitted, 19 packets received, 5.0% packet loss
round-trip min/avg/max/stddev = 15.420/22.135/40.215/5.612 ms
"""

    stats = parse_ping_output(output)

    assert stats.packet_count == 20
    assert stats.packets_received == 19
    assert stats.latency_ms == 22
    assert stats.jitter_ms == 5.612
    assert stats.duration_ms is None


def test_parse_linux_ping_output_reports_packets_duration_and_mdev() -> None:
    output = """
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=14.8 ms

--- 8.8.8.8 ping statistics ---
20 packets transmitted, 18 received, 10% packet loss, time 19024ms
rtt min/avg/max/mdev = 14.880/22.250/40.010/6.110 ms
"""

    stats = parse_ping_output(output)

    assert stats.packet_count == 20
    assert stats.packets_received == 18
    assert stats.latency_ms == 22
    assert stats.jitter_ms == 6.11
    assert stats.duration_ms == 19024


def test_build_edge_sample_payload_uses_ping_statistics() -> None:
    payload = build_edge_sample_payload(
        agent_id="macbook-home",
        agent_label="MacBook at home",
        stats=PingStatistics(
            packet_count=20,
            packets_received=19,
            latency_ms=22,
            jitter_ms=5.612,
            duration_ms=19024,
        ),
    )

    assert payload == {
        "agent_id": "macbook-home",
        "agent_label": "MacBook at home",
        "method": "icmp_sequence",
        "packet_count": 20,
        "packets_received": 19,
        "latency_ms": 22,
        "jitter_ms": 5.612,
        "duration_ms": 19024,
    }


def test_parse_args_accepts_udp_sequence_reflector_options() -> None:
    args = parse_args(
        [
            "--api-base-url",
            "http://api.local",
            "--bearer-token",
            "secret-token",
            "--site-id",
            "site-1",
            "--target-id",
            "vezor-master-udp-reflector",
            "--target",
            "vezor.example.local",
            "--method",
            "udp_sequence",
            "--reflector",
            "vezor.example.local",
            "--reflector-port",
            "8622",
            "--reflector-key-id",
            "master-reflector-test",
            "--reflector-secret",
            "reflector-secret",
            "--packet-spacing-ms",
            "10",
            "--loss-timeout-ms",
            "250",
            "--once",
        ]
    )

    assert args.method == "udp_sequence"
    assert args.reflector == "vezor.example.local"
    assert args.reflector_port == 8622
    assert args.reflector_key_id == "master-reflector-test"
    assert args.reflector_secret == "reflector-secret"
    assert args.packet_spacing_ms == 10
    assert args.loss_timeout_ms == 250


def test_parse_args_accepts_config_url_without_probe_details() -> None:
    args = parse_args(
        [
            "--api-base-url",
            "http://api.local",
            "--bearer-token",
            "secret-token",
            "--config-url",
            "http://api.local/api/v1/link/sites/site-1/control-targets/master/edge-agent-config",
            "--once",
        ]
    )

    assert args.config_url.endswith("/edge-agent-config")
    assert args.site_id is None
    assert args.target_id is None


def test_parse_args_reads_bearer_token_from_owner_only_file(tmp_path) -> None:
    token_path = tmp_path / "supervisor.credential"
    token_path.write_text("node-credential\n", encoding="utf-8")

    args = parse_args(
        [
            "--api-base-url",
            "http://api.local",
            "--bearer-token-file",
            str(token_path),
            "--config-url",
            "http://api.local/api/v1/link/control-targets/master/edge-agent-config",
            "--once",
        ]
    )

    assert args.bearer_token == "node-credential"
    assert args.bearer_token_file == token_path


@pytest.mark.asyncio
async def test_fetch_edge_agent_config_sends_bearer_token() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "site_id": "site-1",
                "target_id": "vezor-master-udp-reflector",
                "method": "udp_sequence",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await fetch_edge_agent_config(
            config_url="http://api.local/config",
            bearer_token="secret-token",
            http_client=http_client,
        )

    assert result["site_id"] == "site-1"
    assert seen[0].headers["authorization"] == "Bearer secret-token"


@pytest.mark.asyncio
async def test_run_udp_sequence_probe_measures_loopback_reflector() -> None:
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=b"reflector-secret",
        key_id="master-reflector-test",
    )
    assert runtime is not None
    try:
        stats = await run_udp_sequence_probe(
            reflector_host="127.0.0.1",
            reflector_port=runtime.port,
            reflector_secret="reflector-secret",
            reflector_key_id="master-reflector-test",
            packet_count=3,
            packet_spacing_ms=1,
            loss_timeout_ms=250,
        )
    finally:
        stop_reflector(runtime)

    assert stats.packet_count == 3
    assert stats.packets_received == 3
    assert stats.latency_ms >= 0
    assert stats.jitter_ms is not None
    assert stats.measurement_metadata["protocol"] == "vezor_udp_sequence"
    assert stats.measurement_metadata["reflector_port"] == runtime.port
    assert stats.measurement_metadata["packets_lost"] == 0


@pytest.mark.asyncio
async def test_run_udp_sequence_probe_uses_reply_arrival_time_not_drain_time() -> None:
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=b"reflector-secret",
        key_id="master-reflector-test",
    )
    assert runtime is not None
    try:
        stats = await run_udp_sequence_probe(
            reflector_host="127.0.0.1",
            reflector_port=runtime.port,
            reflector_secret="reflector-secret",
            reflector_key_id="master-reflector-test",
            packet_count=4,
            packet_spacing_ms=30,
            loss_timeout_ms=250,
        )
    finally:
        stop_reflector(runtime)

    assert stats.packets_received == 4
    assert stats.measurement_metadata["rtt_max_ms"] < 30


@pytest.mark.asyncio
async def test_run_udp_sequence_probe_records_total_loss_without_raising() -> None:
    socket_handle = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_handle.bind(("127.0.0.1", 0))
    unused_port = socket_handle.getsockname()[1]
    socket_handle.close()

    stats = await run_udp_sequence_probe(
        reflector_host="127.0.0.1",
        reflector_port=unused_port,
        reflector_secret="reflector-secret",
        reflector_key_id="master-reflector-test",
        packet_count=2,
        packet_spacing_ms=1,
        loss_timeout_ms=10,
    )

    assert stats.packet_count == 2
    assert stats.packets_received == 0
    assert stats.latency_ms == 0
    assert stats.measurement_metadata["packets_lost"] == 2
    assert stats.measurement_metadata["reflector_port"] == unused_port


def test_run_udp_sequence_probe_catches_python310_asyncio_timeout() -> None:
    source = inspect.getsource(run_udp_sequence_probe)

    assert "asyncio.TimeoutError" in source


def test_build_udp_sequence_edge_sample_payload_includes_sequence_metadata() -> None:
    payload = build_udp_sequence_edge_sample_payload(
        agent_id="macbook-home",
        agent_label="MacBook at home",
        stats=PingStatistics(
            packet_count=5,
            packets_received=4,
            latency_ms=22,
            jitter_ms=1.4,
            duration_ms=450,
            measurement_metadata={
                "protocol": "vezor_udp_sequence",
                "reflector_address": "vezor.example.local",
                "reflector_port": 8622,
                "packets_lost": 1,
            },
        ),
        dscp=46,
    )

    assert payload["method"] == "udp_sequence"
    assert payload["packet_count"] == 5
    assert payload["packets_received"] == 4
    assert payload["latency_ms"] == 22
    assert payload["jitter_ms"] == 1.4
    assert payload["duration_ms"] == 450
    assert payload["dscp"] == 46
    assert payload["measurement_metadata"] == {
        "protocol": "vezor_udp_sequence",
        "reflector_address": "vezor.example.local",
        "reflector_port": 8622,
        "packets_lost": 1,
    }


@pytest.mark.asyncio
async def test_post_edge_sample_sends_site_target_path_and_bearer_token() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={"id": "probe-1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await post_edge_sample(
            api_base_url="http://api.local/",
            bearer_token="secret-token",
            site_id="site-1",
            target_id="target-google-dns",
            payload={
                "agent_id": "macbook-home",
                "method": "icmp_sequence",
                "packet_count": 20,
                "packets_received": 19,
                "latency_ms": 22,
            },
            http_client=http_client,
        )

    assert result == {"id": "probe-1"}
    assert seen[0].method == "POST"
    assert (
        seen[0].url.path
        == "/api/v1/link/sites/site-1/probe-targets/target-google-dns/edge-samples"
    )
    assert seen[0].headers["authorization"] == "Bearer secret-token"
