from __future__ import annotations

import hashlib
import hmac
import statistics
import struct
from dataclasses import dataclass
from typing import Final

MAGIC: Final = b"VZLP"
VERSION: Final = 1
FLAG_REPLY: Final = 0x01
AUTH_TAG_BYTES: Final = 16
HEADER_WITHOUT_AUTH = struct.Struct("!4sBBH16sQQQ")
HEADER_LENGTH: Final = HEADER_WITHOUT_AUTH.size + AUTH_TAG_BYTES


class UdpSequencePacketError(ValueError):
    """Raised when a UDP sequence packet is malformed or unauthenticated."""


@dataclass(frozen=True, slots=True)
class UdpSequencePacket:
    session_id: bytes
    sequence: int
    transmit_ns: int
    nonce: int
    reply: bool


@dataclass(frozen=True, slots=True)
class SequenceReply:
    sequence: int
    rtt_ms: float
    late: bool = False


@dataclass(frozen=True, slots=True)
class UdpSequenceStats:
    packet_count: int
    packets_received: int
    packets_lost: int
    packets_late: int
    packets_duplicate: int
    packets_out_of_order: int
    rtt_min_ms: float | None
    rtt_avg_ms: float | None
    rtt_p95_ms: float | None
    rtt_max_ms: float | None
    rtt_variation_ms: float | None


def build_probe_packet(
    *,
    session_id: bytes,
    sequence: int,
    transmit_ns: int,
    nonce: int,
    secret: bytes,
    reply: bool,
) -> bytes:
    if len(session_id) != 16:
        raise UdpSequencePacketError("UDP sequence session id must be exactly 16 bytes.")
    if sequence < 0:
        raise UdpSequencePacketError("UDP sequence number must be non-negative.")
    if transmit_ns < 0:
        raise UdpSequencePacketError("UDP sequence transmit timestamp must be non-negative.")
    if nonce < 0:
        raise UdpSequencePacketError("UDP sequence nonce must be non-negative.")
    flags = FLAG_REPLY if reply else 0
    unsigned = HEADER_WITHOUT_AUTH.pack(
        MAGIC,
        VERSION,
        flags,
        HEADER_LENGTH,
        session_id,
        sequence,
        transmit_ns,
        nonce,
    )
    return unsigned + _auth_tag(unsigned, secret=secret)


def parse_probe_packet(packet: bytes, *, secret: bytes) -> UdpSequencePacket:
    if len(packet) != HEADER_LENGTH:
        raise UdpSequencePacketError("UDP sequence packet has an invalid length.")
    unsigned = packet[: HEADER_WITHOUT_AUTH.size]
    auth_tag = packet[HEADER_WITHOUT_AUTH.size :]
    expected_tag = _auth_tag(unsigned, secret=secret)
    if not hmac.compare_digest(auth_tag, expected_tag):
        raise UdpSequencePacketError("UDP sequence packet authentication failed.")

    magic, version, flags, header_length, session_id, sequence, transmit_ns, nonce = (
        HEADER_WITHOUT_AUTH.unpack(unsigned)
    )
    if magic != MAGIC:
        raise UdpSequencePacketError("UDP sequence packet has invalid magic.")
    if version != VERSION:
        raise UdpSequencePacketError("UDP sequence packet has unsupported version.")
    if header_length != HEADER_LENGTH:
        raise UdpSequencePacketError("UDP sequence packet has invalid header length.")
    return UdpSequencePacket(
        session_id=session_id,
        sequence=sequence,
        transmit_ns=transmit_ns,
        nonce=nonce,
        reply=bool(flags & FLAG_REPLY),
    )


def summarize_sequence_results(
    *,
    sent_sequences: list[int],
    replies: list[SequenceReply],
) -> UdpSequenceStats:
    sent_unique = set(sent_sequences)
    received_sequences: set[int] = set()
    on_time_rtts: list[float] = []
    duplicate_count = 0
    late_count = 0
    out_of_order_count = 0
    highest_seen: int | None = None

    for reply in replies:
        if reply.sequence not in sent_unique:
            continue
        if reply.late:
            late_count += 1
            continue
        if reply.sequence in received_sequences:
            duplicate_count += 1
            continue
        if highest_seen is not None and reply.sequence < highest_seen:
            out_of_order_count += 1
        highest_seen = reply.sequence if highest_seen is None else max(highest_seen, reply.sequence)
        received_sequences.add(reply.sequence)
        on_time_rtts.append(reply.rtt_ms)

    packet_count = len(sent_unique)
    packets_received = len(received_sequences)
    packets_lost = max(0, packet_count - packets_received)

    return UdpSequenceStats(
        packet_count=packet_count,
        packets_received=packets_received,
        packets_lost=packets_lost,
        packets_late=late_count,
        packets_duplicate=duplicate_count,
        packets_out_of_order=out_of_order_count,
        rtt_min_ms=_round_or_none(min(on_time_rtts) if on_time_rtts else None),
        rtt_avg_ms=_round_or_none(
            sum(on_time_rtts) / len(on_time_rtts) if on_time_rtts else None
        ),
        rtt_p95_ms=_round_or_none(_percentile_nearest_rank(on_time_rtts, 0.95)),
        rtt_max_ms=_round_or_none(max(on_time_rtts) if on_time_rtts else None),
        rtt_variation_ms=_round_or_none(
            statistics.pstdev(on_time_rtts) if len(on_time_rtts) > 1 else None
        ),
    )


def _auth_tag(payload: bytes, *, secret: bytes) -> bytes:
    return hmac.new(secret, payload, hashlib.sha256).digest()[:AUTH_TAG_BYTES]


def _percentile_nearest_rank(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(percentile * len(ordered) + 0.5) - 1))
    return ordered[index]


def _round_or_none(value: float | None) -> float | None:
    return None if value is None else round(value, 3)
