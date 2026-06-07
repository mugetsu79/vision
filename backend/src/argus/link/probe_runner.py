from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

from argus.link.contracts import LinkProbeSampleKind, LinkProbeSourceType, LinkProbeType


@dataclass(frozen=True, slots=True)
class ProbeTarget:
    target_id: str
    label: str
    address: str
    probe_type: LinkProbeType
    port: int | None = None


@dataclass(frozen=True, slots=True)
class ThroughputProbeTarget(ProbeTarget):
    throughput_test_url: str | None = None
    throughput_test_max_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class ProbeResult:
    target_id: str
    target_label: str
    target_address: str
    probe_type: LinkProbeType
    latency_ms: int
    throughput_mbps: float
    packet_loss_percent: float
    reachable: bool
    source: str
    source_type: LinkProbeSourceType
    source_label: str
    sample_kind: LinkProbeSampleKind
    failure_reason: str | None = None


async def run_backend_probe(
    target: ProbeTarget,
    *,
    source_label: str = "backend:primary",
    timeout_seconds: float = 5.0,
    http_client: httpx.AsyncClient | None = None,
) -> ProbeResult:
    started = time.perf_counter()
    if target.probe_type == "icmp":
        return _result(target, 0, False, source_label, "backend_synthetic_icmp_unsupported")
    if target.probe_type in {"http", "https"}:
        return await _run_http_probe(target, started, source_label, timeout_seconds, http_client)
    if target.probe_type == "tcp":
        return await _run_tcp_probe(target, started, source_label, timeout_seconds)
    return _result(target, 0, False, source_label, "unsupported_probe_type")


async def measure_backend_throughput(
    target: ThroughputProbeTarget,
    *,
    source_label: str = "backend:primary/manual-throughput",
    timeout_seconds: float = 15.0,
    http_client: httpx.AsyncClient | None = None,
) -> ProbeResult:
    started = time.perf_counter()
    if target.probe_type not in {"http", "https"}:
        return _result(target, 0, False, source_label, "throughput_http_required")
    if not target.throughput_test_url:
        return _result(target, 0, False, source_label, "throughput_test_url_required")

    max_bytes = _throughput_byte_cap(target.throughput_test_max_bytes)
    client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
    owns_client = http_client is None
    bytes_read = 0
    try:
        async with client.stream(
            "GET",
            target.throughput_test_url,
            headers={"Range": f"bytes=0-{max_bytes - 1}"},
        ) as response:
            if response.status_code >= 400:
                return _result(
                    target,
                    _elapsed_ms(started),
                    False,
                    source_label,
                    f"http_status_{response.status_code}",
                )
            async for chunk in response.aiter_bytes():
                bytes_read += len(chunk)
                if bytes_read >= max_bytes:
                    bytes_read = max_bytes
                    break
        if bytes_read <= 0:
            return _result(target, _elapsed_ms(started), False, source_label, "empty_response")
        elapsed_seconds = max(time.perf_counter() - started, 0.001)
        throughput_mbps = (bytes_read * 8) / elapsed_seconds / 1_000_000
        return ProbeResult(
            target_id=target.target_id,
            target_label=target.label,
            target_address=target.address,
            probe_type=target.probe_type,
            latency_ms=_elapsed_ms(started),
            throughput_mbps=throughput_mbps,
            packet_loss_percent=0.0,
            reachable=True,
            source=f"backend_synthetic:{source_label}",
            source_type="backend_synthetic",
            source_label=source_label,
            sample_kind="automated",
            failure_reason=None,
        )
    except httpx.HTTPError as exc:
        return _result(target, _elapsed_ms(started), False, source_label, exc.__class__.__name__)
    finally:
        if owns_client:
            await client.aclose()


async def _run_http_probe(
    target: ProbeTarget,
    started: float,
    source_label: str,
    timeout_seconds: float,
    http_client: httpx.AsyncClient | None,
) -> ProbeResult:
    client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
    owns_client = http_client is None
    try:
        response = await client.get(_target_url(target))
        return _result(
            target,
            _elapsed_ms(started),
            response.status_code < 500,
            source_label,
            None if response.status_code < 500 else f"http_status_{response.status_code}",
        )
    except httpx.HTTPError as exc:
        return _result(target, _elapsed_ms(started), False, source_label, exc.__class__.__name__)
    finally:
        if owns_client:
            await client.aclose()


async def _run_tcp_probe(
    target: ProbeTarget,
    started: float,
    source_label: str,
    timeout_seconds: float,
) -> ProbeResult:
    if target.port is None:
        return _result(target, 0, False, source_label, "tcp_port_required")
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target.address, target.port),
            timeout=timeout_seconds,
        )
        writer.close()
        await writer.wait_closed()
        return _result(target, _elapsed_ms(started), True, source_label, None)
    except (OSError, TimeoutError) as exc:
        return _result(target, _elapsed_ms(started), False, source_label, exc.__class__.__name__)


def _target_url(target: ProbeTarget) -> str:
    if target.address.startswith(("http://", "https://")):
        return target.address
    if target.port is None or (target.probe_type == "http" and target.port == 80):
        return f"{target.probe_type}://{target.address}"
    if target.probe_type == "https" and target.port == 443:
        return f"{target.probe_type}://{target.address}"
    return f"{target.probe_type}://{target.address}:{target.port}"


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _throughput_byte_cap(value: int | None) -> int:
    if value is None:
        return 1_000_000
    return min(max(value, 1), 50_000_000)


def _result(
    target: ProbeTarget,
    latency_ms: int,
    reachable: bool,
    source_label: str,
    failure_reason: str | None,
) -> ProbeResult:
    return ProbeResult(
        target_id=target.target_id,
        target_label=target.label,
        target_address=target.address,
        probe_type=target.probe_type,
        latency_ms=latency_ms,
        throughput_mbps=0.0,
        packet_loss_percent=0.0 if reachable else 100.0,
        reachable=reachable,
        source=f"backend_synthetic:{source_label}",
        source_type="backend_synthetic",
        source_label=source_label,
        sample_kind="automated",
        failure_reason=failure_reason,
    )
