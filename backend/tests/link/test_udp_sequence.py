from __future__ import annotations

import pytest

from argus.link.udp_sequence import (
    SequenceReply,
    UdpSequencePacketError,
    build_probe_packet,
    parse_probe_packet,
    summarize_sequence_results,
)


def test_udp_sequence_packet_round_trips_authenticated_request() -> None:
    secret = b"shared-secret"
    session_id = bytes.fromhex("00" * 15 + "07")

    packet = build_probe_packet(
        session_id=session_id,
        sequence=7,
        transmit_ns=123_456_789,
        nonce=42,
        secret=secret,
        reply=False,
    )

    decoded = parse_probe_packet(packet, secret=secret)

    assert decoded.session_id == session_id
    assert decoded.sequence == 7
    assert decoded.transmit_ns == 123_456_789
    assert decoded.nonce == 42
    assert decoded.reply is False


def test_udp_sequence_packet_round_trips_authenticated_reply() -> None:
    secret = b"shared-secret"
    session_id = bytes.fromhex("11" * 16)

    packet = build_probe_packet(
        session_id=session_id,
        sequence=99,
        transmit_ns=987_654_321,
        nonce=123,
        secret=secret,
        reply=True,
    )

    decoded = parse_probe_packet(packet, secret=secret)

    assert decoded.session_id == session_id
    assert decoded.sequence == 99
    assert decoded.transmit_ns == 987_654_321
    assert decoded.nonce == 123
    assert decoded.reply is True


@pytest.mark.parametrize(
    ("offset", "value"),
    [
        (0, b"BAD!"),
        (4, b"\x02"),
    ],
)
def test_udp_sequence_packet_rejects_bad_magic_or_version(
    offset: int,
    value: bytes,
) -> None:
    secret = b"shared-secret"
    packet = bytearray(
        build_probe_packet(
            session_id=bytes.fromhex("22" * 16),
            sequence=1,
            transmit_ns=1,
            nonce=1,
            secret=secret,
            reply=False,
        )
    )
    packet[offset : offset + len(value)] = value

    with pytest.raises(UdpSequencePacketError):
        parse_probe_packet(bytes(packet), secret=secret)


def test_udp_sequence_packet_rejects_bad_auth_tag() -> None:
    secret = b"shared-secret"
    packet = bytearray(
        build_probe_packet(
            session_id=bytes.fromhex("33" * 16),
            sequence=1,
            transmit_ns=1,
            nonce=1,
            secret=secret,
            reply=False,
        )
    )
    packet[-1] ^= 0xFF

    with pytest.raises(UdpSequencePacketError):
        parse_probe_packet(bytes(packet), secret=secret)


def test_udp_sequence_statistics_counts_loss_late_duplicates_and_out_of_order() -> None:
    stats = summarize_sequence_results(
        sent_sequences=[1, 2, 3, 4, 5],
        replies=[
            SequenceReply(sequence=1, rtt_ms=10.0, late=False),
            SequenceReply(sequence=3, rtt_ms=30.0, late=False),
            SequenceReply(sequence=3, rtt_ms=31.0, late=False),
            SequenceReply(sequence=2, rtt_ms=20.0, late=False),
            SequenceReply(sequence=5, rtt_ms=100.0, late=True),
        ],
    )

    assert stats.packet_count == 5
    assert stats.packets_received == 3
    assert stats.packets_lost == 2
    assert stats.packets_duplicate == 1
    assert stats.packets_late == 1
    assert stats.packets_out_of_order == 1
    assert stats.rtt_min_ms == 10.0
    assert stats.rtt_avg_ms == 20.0
    assert stats.rtt_p95_ms == 30.0
    assert stats.rtt_max_ms == 30.0
    assert stats.rtt_variation_ms == 8.165
