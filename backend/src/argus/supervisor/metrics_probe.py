from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

import httpx

from argus.api.contracts import HardwarePerformanceSample
from argus.compat import UTC

_METRIC_LINE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(?P<labels>[^}]*)\})?\s+"
    r"(?P<value>[-+0-9.eE]+)$"
)
_STAGE_BUCKET = "argus_inference_stage_duration_seconds_bucket"
_FRAMES_TOTAL = "argus_inference_frames_processed_total"


@dataclass(frozen=True, slots=True)
class WorkerMetricsContext:
    camera_id: UUID
    model_id: UUID | None
    model_name: str | None
    runtime_backend: str
    input_width: int
    input_height: int
    target_fps: float


@dataclass(slots=True)
class MetricsSnapshot:
    captured_at: datetime
    frame_counts: dict[str, float] = field(default_factory=dict)
    histograms: dict[tuple[str, str], list[tuple[float, float]]] = field(default_factory=dict)


class WorkerMetricsProbe:
    def __init__(
        self,
        metrics_url: str | None,
        http_client: httpx.AsyncClient | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.metrics_url = metrics_url
        self.http_client = http_client
        self.clock = clock or (lambda: datetime.now(tz=UTC))
        self.previous_snapshot: MetricsSnapshot | None = None
        self.latest_snapshot: MetricsSnapshot | None = None

    async def scrape(self) -> MetricsSnapshot | None:
        if not self.metrics_url:
            return None
        owns_client = self.http_client is None
        client = self.http_client or httpx.AsyncClient()
        try:
            response = await client.get(self.metrics_url, timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        finally:
            if owns_client:
                await client.aclose()
        return parse_prometheus_metrics(response.text, captured_at=self.clock())

    async def build_performance_samples(
        self,
        worker_contexts: Iterable[WorkerMetricsContext],
        previous_snapshot: MetricsSnapshot | None = None,
    ) -> list[HardwarePerformanceSample]:
        snapshot = await self.scrape()
        if snapshot is None or not snapshot.histograms:
            return []
        previous = previous_snapshot or self.previous_snapshot
        contexts = list(worker_contexts)
        samples = [
            self._sample_for_context(context, snapshot=snapshot, previous=previous)
            for context in contexts
        ]
        self.previous_snapshot = snapshot
        self.latest_snapshot = snapshot
        return [sample for sample in samples if sample is not None]

    def _sample_for_context(
        self,
        context: WorkerMetricsContext,
        *,
        snapshot: MetricsSnapshot,
        previous: MetricsSnapshot | None,
    ) -> HardwarePerformanceSample | None:
        camera_key = str(context.camera_id)
        stages = {
            stage
            for camera_id, stage in snapshot.histograms
            if camera_id == camera_key
        }
        if not stages:
            return None
        p95 = _stage_quantiles_ms(
            camera_key=camera_key,
            stages=stages,
            snapshot=snapshot,
            previous=previous,
            quantile=0.95,
        )
        p99 = _stage_quantiles_ms(
            camera_key=camera_key,
            stages=stages,
            snapshot=snapshot,
            previous=previous,
            quantile=0.99,
        )
        if not p95 and not p99:
            return None
        return HardwarePerformanceSample(
            model_id=context.model_id,
            model_name=context.model_name,
            runtime_backend=context.runtime_backend,
            input_width=context.input_width,
            input_height=context.input_height,
            target_fps=context.target_fps,
            observed_fps=_observed_fps(camera_key, snapshot=snapshot, previous=previous),
            stage_p95_ms=p95,
            stage_p99_ms=p99,
            captured_at=snapshot.captured_at,
        )


def parse_prometheus_metrics(text: str, *, captured_at: datetime) -> MetricsSnapshot:
    frame_counts: dict[str, float] = {}
    histograms: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _METRIC_LINE_RE.match(line)
        if match is None:
            continue
        name = match.group("name")
        labels = _parse_labels(match.group("labels") or "")
        value = _parse_float(match.group("value"))
        if value is None:
            continue
        camera_id = labels.get("camera_id")
        if not camera_id:
            continue
        if name == _FRAMES_TOTAL:
            frame_counts[camera_id] = frame_counts.get(camera_id, 0.0) + value
        elif name == _STAGE_BUCKET and "stage" in labels and "le" in labels:
            upper_bound = _parse_bucket(labels["le"])
            if upper_bound is None:
                continue
            key = (camera_id, labels["stage"])
            histograms.setdefault(key, []).append((upper_bound, value))
    for buckets in histograms.values():
        buckets.sort(key=lambda item: item[0])
    return MetricsSnapshot(
        captured_at=captured_at,
        frame_counts=frame_counts,
        histograms=histograms,
    )


def _parse_labels(raw: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    if not raw:
        return labels
    for part in _split_labels(raw):
        key, separator, value = part.partition("=")
        if not separator:
            continue
        labels[key.strip()] = value.strip().strip('"')
    return labels


def _split_labels(raw: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_quotes = False
    escaped = False
    for char in raw:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == '"':
            in_quotes = not in_quotes
        if char == "," and not in_quotes:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current))
    return parts


def _parse_float(raw: str) -> float | None:
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_bucket(raw: str) -> float | None:
    if raw == "+Inf":
        return float("inf")
    return _parse_float(raw)


def _histogram_quantile(q: float, buckets: list[tuple[float, float]]) -> float | None:
    if not buckets:
        return None
    buckets = _monotonic_buckets(buckets)
    total = buckets[-1][1]
    if total <= 0:
        return None
    rank = total * q
    previous_bound = 0.0
    previous_count = 0.0
    for bound, count in buckets:
        if count >= rank:
            if bound == float("inf"):
                return previous_bound
            bucket_count = count - previous_count
            if bucket_count <= 0:
                return bound
            position = (rank - previous_count) / bucket_count
            return previous_bound + (bound - previous_bound) * position
        if bound != float("inf"):
            previous_bound = bound
        previous_count = count
    return previous_bound


def _stage_quantiles_ms(
    *,
    camera_key: str,
    stages: set[str],
    snapshot: MetricsSnapshot,
    previous: MetricsSnapshot | None,
    quantile: float,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for stage in sorted(stages):
        histogram = _recent_histogram(
            camera_key=camera_key,
            stage=stage,
            snapshot=snapshot,
            previous=previous,
        )
        if histogram is None:
            continue
        value = _histogram_quantile(quantile, histogram)
        if value is not None:
            values[stage] = round(value * 1000, 3)
    return values


def _recent_histogram(
    *,
    camera_key: str,
    stage: str,
    snapshot: MetricsSnapshot,
    previous: MetricsSnapshot | None,
) -> list[tuple[float, float]] | None:
    key = (camera_key, stage)
    current = snapshot.histograms.get(key)
    if not current:
        return None
    if previous is None or key not in previous.histograms:
        return current
    previous_by_bound = dict(previous.histograms[key])
    deltas: list[tuple[float, float]] = []
    for bound, count in current:
        previous_count = previous_by_bound.get(bound)
        if previous_count is None:
            return current
        delta = count - previous_count
        if delta < 0:
            return current
        deltas.append((bound, delta))
    if not deltas or deltas[-1][1] <= 0:
        return None
    return deltas


def _monotonic_buckets(buckets: list[tuple[float, float]]) -> list[tuple[float, float]]:
    maximum = 0.0
    monotonic: list[tuple[float, float]] = []
    for bound, count in buckets:
        maximum = max(maximum, count)
        monotonic.append((bound, maximum))
    return monotonic


def _observed_fps(
    camera_id: str,
    *,
    snapshot: MetricsSnapshot,
    previous: MetricsSnapshot | None,
) -> float | None:
    if previous is None:
        return None
    current_count = snapshot.frame_counts.get(camera_id)
    previous_count = previous.frame_counts.get(camera_id)
    if current_count is None or previous_count is None:
        return None
    elapsed = (snapshot.captured_at - previous.captured_at).total_seconds()
    if elapsed <= 0:
        return None
    delta = current_count - previous_count
    if delta < 0:
        return None
    return round(delta / elapsed, 3)
