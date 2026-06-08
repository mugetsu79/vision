from __future__ import annotations

import argparse
import asyncio
import os
from collections import defaultdict, deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from ipaddress import ip_address, ip_network
from time import monotonic
from typing import cast

from argus.link.udp_sequence import build_probe_packet, parse_probe_packet


@dataclass(slots=True)
class SourceCounters:
    received: int = 0
    replied: int = 0
    dropped_auth: int = 0
    dropped_source_disallowed: int = 0
    dropped_rate_limited: int = 0
    packet_times: deque[float] = field(default_factory=deque)


@dataclass(slots=True)
class ReflectorRuntime:
    transport: asyncio.DatagramTransport
    protocol: UdpSequenceReflectorProtocol
    bind_host: str
    port: int
    key_id: str


class UdpSequenceReflectorProtocol(asyncio.DatagramProtocol):
    def __init__(
        self,
        *,
        secret: bytes,
        key_id: str,
        rate_limit_pps: int = 100,
        allowed_source_cidrs: Sequence[str] | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.secret = secret
        self.key_id = key_id
        self.rate_limit_pps = rate_limit_pps
        self.allowed_source_networks = tuple(
            ip_network(cidr, strict=False) for cidr in (allowed_source_cidrs or [])
        )
        self.clock = clock
        self.counters: dict[str, SourceCounters] = defaultdict(SourceCounters)
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        source = addr[0]
        counters = self.counters[source]
        counters.received += 1

        if not self._source_allowed(source):
            counters.dropped_source_disallowed += 1
            return

        if self._rate_limited(counters):
            counters.dropped_rate_limited += 1
            return

        try:
            packet = parse_probe_packet(data, secret=self.secret)
        except ValueError:
            counters.dropped_auth += 1
            return

        if packet.reply:
            return

        reply = build_probe_packet(
            session_id=packet.session_id,
            sequence=packet.sequence,
            transmit_ns=packet.transmit_ns,
            nonce=packet.nonce,
            secret=self.secret,
            reply=True,
        )
        if len(reply) > len(data):
            return
        if self.transport is None:
            return
        self.transport.sendto(reply, addr)
        counters.replied += 1

    def _source_allowed(self, source: str) -> bool:
        if not self.allowed_source_networks:
            return True
        try:
            source_address = ip_address(source)
        except ValueError:
            return False
        return any(source_address in network for network in self.allowed_source_networks)

    def _rate_limited(self, counters: SourceCounters) -> bool:
        if self.rate_limit_pps <= 0:
            return False
        now = self.clock()
        window_start = now - 1.0
        while counters.packet_times and counters.packet_times[0] < window_start:
            counters.packet_times.popleft()
        if len(counters.packet_times) >= self.rate_limit_pps:
            return True
        counters.packet_times.append(now)
        return False


async def start_reflector(
    *,
    bind_host: str,
    port: int,
    secret: bytes,
    key_id: str,
    rate_limit_pps: int = 100,
    allowed_source_cidrs: Sequence[str] | None = None,
    enabled: bool = True,
) -> ReflectorRuntime | None:
    if not enabled:
        return None
    loop = asyncio.get_running_loop()
    protocol = UdpSequenceReflectorProtocol(
        secret=secret,
        key_id=key_id,
        rate_limit_pps=rate_limit_pps,
        allowed_source_cidrs=allowed_source_cidrs,
    )
    transport, _ = await loop.create_datagram_endpoint(
        lambda: protocol,
        local_addr=(bind_host, port),
    )
    sockname = transport.get_extra_info("sockname")
    actual_port = int(sockname[1]) if isinstance(sockname, tuple) and len(sockname) >= 2 else port
    return ReflectorRuntime(
        transport=transport,
        protocol=protocol,
        bind_host=bind_host,
        port=actual_port,
        key_id=key_id,
    )


def stop_reflector(runtime: ReflectorRuntime | None) -> None:
    if runtime is not None:
        runtime.transport.close()


async def async_main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    secret = args.secret.encode("utf-8")
    runtime = await start_reflector(
        bind_host=args.bind,
        port=args.port,
        secret=secret,
        key_id=args.key_id,
        rate_limit_pps=args.rate_limit_pps,
    )
    if runtime is None:
        return 0
    try:
        await asyncio.Event().wait()
    finally:
        stop_reflector(runtime)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Vezor Core Link UDP reflector.")
    parser.add_argument("--bind", default=os.getenv("ARGUS_LINK_REFLECTOR_BIND_ADDRESS", "0.0.0.0"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ARGUS_LINK_REFLECTOR_PORT", "8622")),
    )
    parser.add_argument("--secret", default=os.getenv("ARGUS_LINK_REFLECTOR_SECRET"))
    parser.add_argument(
        "--key-id",
        default=os.getenv("ARGUS_LINK_REFLECTOR_KEY_ID", "master-reflector-default"),
    )
    parser.add_argument(
        "--rate-limit-pps",
        type=int,
        default=int(os.getenv("ARGUS_LINK_REFLECTOR_RATE_LIMIT_PPS", "100")),
    )
    args = parser.parse_args(argv)
    if not args.secret:
        parser.error("--secret or ARGUS_LINK_REFLECTOR_SECRET is required")
    if args.port <= 0 or args.port > 65_535:
        parser.error("--port must be between 1 and 65535")
    if args.rate_limit_pps < 0:
        parser.error("--rate-limit-pps must be non-negative")
    return args


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
