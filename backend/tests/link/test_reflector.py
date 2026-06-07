from __future__ import annotations

import asyncio

import pytest

from argus.link.reflector import start_reflector, stop_reflector
from argus.link.udp_sequence import build_probe_packet, parse_probe_packet


@pytest.mark.asyncio
async def test_udp_reflector_replies_to_authenticated_request() -> None:
    secret = b"reflector-secret"
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=secret,
        key_id="master-reflector-test",
    )
    assert runtime is not None
    try:
        request = build_probe_packet(
            session_id=bytes.fromhex("44" * 16),
            sequence=17,
            transmit_ns=123_456,
            nonce=99,
            secret=secret,
            reply=False,
        )

        response = await _send_udp_packet(request, host="127.0.0.1", port=runtime.port)

        decoded = parse_probe_packet(response, secret=secret)
        assert decoded.reply is True
        assert decoded.session_id == bytes.fromhex("44" * 16)
        assert decoded.sequence == 17
        assert decoded.transmit_ns == 123_456
        assert decoded.nonce == 99
        assert len(response) <= len(request)
    finally:
        stop_reflector(runtime)


@pytest.mark.asyncio
async def test_udp_reflector_drops_unauthenticated_request() -> None:
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=b"reflector-secret",
        key_id="master-reflector-test",
    )
    assert runtime is not None
    try:
        request = build_probe_packet(
            session_id=bytes.fromhex("55" * 16),
            sequence=3,
            transmit_ns=123_456,
            nonce=77,
            secret=b"wrong-secret",
            reply=False,
        )

        with pytest.raises(TimeoutError):
            await _send_udp_packet(
                request,
                host="127.0.0.1",
                port=runtime.port,
                wait_seconds=0.1,
            )
    finally:
        stop_reflector(runtime)


@pytest.mark.asyncio
async def test_udp_reflector_disabled_profile_does_not_bind() -> None:
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=b"reflector-secret",
        key_id="master-reflector-test",
        enabled=False,
    )

    assert runtime is None


async def _send_udp_packet(
    payload: bytes,
    *,
    host: str,
    port: int,
    wait_seconds: float = 1.0,
) -> bytes:
    loop = asyncio.get_running_loop()
    response: asyncio.Future[bytes] = loop.create_future()

    class ClientProtocol(asyncio.DatagramProtocol):
        transport: asyncio.DatagramTransport

        def connection_made(self, transport: asyncio.BaseTransport) -> None:
            self.transport = transport  # type: ignore[assignment]
            self.transport.sendto(payload, (host, port))

        def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
            if not response.done():
                response.set_result(data)

        def error_received(self, exc: Exception) -> None:
            if not response.done():
                response.set_exception(exc)

    transport, _ = await loop.create_datagram_endpoint(
        ClientProtocol,
        local_addr=("127.0.0.1", 0),
    )
    try:
        return await asyncio.wait_for(response, timeout=wait_seconds)
    finally:
        transport.close()
