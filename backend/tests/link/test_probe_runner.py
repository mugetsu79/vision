from __future__ import annotations

import asyncio

import httpx
import pytest

from argus.link.probe_runner import ProbeTarget, run_backend_probe


@pytest.mark.asyncio
async def test_backend_probe_records_https_success() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(204))
    async with httpx.AsyncClient(transport=transport) as client:
        result = await run_backend_probe(
            ProbeTarget(
                target_id="target-1",
                label="Vezor ingest",
                address="https://ingest.example.vezor/health",
                probe_type="https",
                port=443,
            ),
            http_client=client,
        )

    assert result.reachable is True
    assert result.packet_loss_percent == 0.0
    assert result.probe_type == "https"
    assert result.source_type == "backend_synthetic"
    assert result.sample_kind == "automated"


@pytest.mark.asyncio
async def test_backend_probe_records_tcp_success() -> None:
    async def handle_client(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        writer.close()
        await writer.wait_closed()
        del reader

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    sockets = server.sockets
    assert sockets is not None
    port = sockets[0].getsockname()[1]

    async with server:
        result = await run_backend_probe(
            ProbeTarget(
                target_id="target-1",
                label="Provider edge",
                address="127.0.0.1",
                probe_type="tcp",
                port=port,
            ),
            timeout_seconds=1.0,
        )

    assert result.reachable is True
    assert result.packet_loss_percent == 0.0
    assert result.probe_type == "tcp"


@pytest.mark.asyncio
async def test_backend_probe_rejects_icmp() -> None:
    result = await run_backend_probe(
        ProbeTarget(
            target_id="target-1",
            label="Gateway",
            address="203.0.113.10",
            probe_type="icmp",
            port=None,
        ),
    )

    assert result.reachable is False
    assert result.failure_reason == "backend_synthetic_icmp_unsupported"
