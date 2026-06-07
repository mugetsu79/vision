from __future__ import annotations

import httpx
import pytest

from argus.link.edge_agent import (
    PingStatistics,
    build_edge_sample_payload,
    parse_ping_output,
    post_edge_sample,
)


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
