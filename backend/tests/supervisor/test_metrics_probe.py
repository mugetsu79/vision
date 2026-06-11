from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from argus.supervisor.metrics_probe import (
    MetricsSnapshot,
    WorkerMetricsContext,
    WorkerMetricsProbe,
)


def test_worker_metrics_context_accepts_metrics_url() -> None:
    metrics_url = "http://127.0.0.1:19108/metrics"

    context = WorkerMetricsContext(
        camera_id=uuid4(),
        model_id=None,
        model_name=None,
        runtime_backend="onnxruntime",
        input_width=1280,
        input_height=720,
        target_fps=20,
        metrics_url=metrics_url,
    )

    assert context.metrics_url == metrics_url


@pytest.mark.asyncio
async def test_prometheus_histogram_deltas_are_converted_to_p95_p99_milliseconds() -> None:
    camera_id = uuid4()
    now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    metrics_text = "\n".join(
        [
            "# HELP argus_inference_stage_duration_seconds Per-stage inference duration.",
            "# TYPE argus_inference_stage_duration_seconds histogram",
            _stage_bucket(camera_id, "total", "0.05", 110),
            _stage_bucket(camera_id, "total", "0.1", 195),
            _stage_bucket(camera_id, "total", "0.2", 200),
            _stage_bucket(camera_id, "total", "+Inf", 200),
            _stage_bucket(camera_id, "detect", "0.04", 110),
            _stage_bucket(camera_id, "detect", "0.08", 195),
            _stage_bucket(camera_id, "detect", "0.12", 200),
            _stage_bucket(camera_id, "detect", "+Inf", 200),
            (
                "argus_inference_frames_processed_total"
                f'{{camera_id="{camera_id}",profile="720p10",stream_mode="annotated"}} 130'
            ),
        ]
    )
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text=metrics_text))
    async with httpx.AsyncClient(transport=transport) as http_client:
        probe = WorkerMetricsProbe(
            "http://worker.local/metrics",
            http_client=http_client,
            clock=lambda: now,
        )
        previous = MetricsSnapshot(
            captured_at=now - timedelta(seconds=10),
            frame_counts={str(camera_id): 100.0},
            histograms={
                (str(camera_id), "total"): [
                    (0.05, 100),
                    (0.1, 100),
                    (0.2, 100),
                    (float("inf"), 100),
                ],
                (str(camera_id), "detect"): [
                    (0.04, 100),
                    (0.08, 100),
                    (0.12, 100),
                    (float("inf"), 100),
                ],
            },
        )

        samples = await probe.build_performance_samples(
            [
                WorkerMetricsContext(
                    camera_id=camera_id,
                    model_id=None,
                    model_name="YOLO26n COCO",
                    runtime_backend="CoreMLExecutionProvider",
                    input_width=1280,
                    input_height=720,
                    target_fps=10,
                )
            ],
            previous_snapshot=previous,
        )

    assert len(samples) == 1
    sample = samples[0]
    assert sample.model_name == "YOLO26n COCO"
    assert sample.runtime_backend == "CoreMLExecutionProvider"
    assert sample.input_width == 1280
    assert sample.input_height == 720
    assert sample.target_fps == 10
    assert sample.observed_fps == 3.0
    assert sample.stage_p95_ms == {"detect": 80.0, "total": 100.0}
    assert sample.stage_p99_ms == {"detect": 112.0, "total": 180.0}
    assert sample.captured_at == now


@pytest.mark.asyncio
async def test_metrics_probe_scrapes_each_worker_metrics_url_once() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    now = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url)
        requests.append(request_url)
        camera_id = camera_a if "19108" in request_url else camera_b
        text = "\n".join(
            [
                _stage_bucket(camera_id, "total", "0.05", 20),
                _stage_bucket(camera_id, "total", "+Inf", 20),
                (
                    "argus_inference_frames_processed_total"
                    f'{{camera_id="{camera_id}",profile="720p20",stream_mode="annotated"}} 20'
                ),
            ]
        )
        return httpx.Response(200, text=text)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        probe = WorkerMetricsProbe(None, http_client=http_client, clock=lambda: now)
        samples = await probe.build_performance_samples(
            [
                WorkerMetricsContext(
                    camera_id=camera_a,
                    model_id=None,
                    model_name=None,
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=20,
                    metrics_url="http://127.0.0.1:19108/metrics",
                ),
                WorkerMetricsContext(
                    camera_id=camera_b,
                    model_id=None,
                    model_name=None,
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=20,
                    metrics_url="http://127.0.0.1:19109/metrics",
                ),
            ]
        )

    assert sorted(requests) == [
        "http://127.0.0.1:19108/metrics",
        "http://127.0.0.1:19109/metrics",
    ]
    assert len(samples) == 2
    assert {sample.input_width for sample in samples} == {1280}


@pytest.mark.asyncio
async def test_metrics_probe_skips_only_failed_worker_metrics_url() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    now = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url)
        if "19108" in request_url:
            return httpx.Response(503, text="nope")
        text = "\n".join(
            [
                _stage_bucket(camera_b, "total", "0.05", 20),
                _stage_bucket(camera_b, "total", "+Inf", 20),
                (
                    "argus_inference_frames_processed_total"
                    f'{{camera_id="{camera_b}",profile="720p20",stream_mode="annotated"}} 20'
                ),
            ]
        )
        return httpx.Response(200, text=text)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        probe = WorkerMetricsProbe(None, http_client=http_client, clock=lambda: now)
        samples = await probe.build_performance_samples(
            [
                WorkerMetricsContext(
                    camera_id=camera_a,
                    model_id=None,
                    model_name="failed",
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=20,
                    metrics_url="http://127.0.0.1:19108/metrics",
                ),
                WorkerMetricsContext(
                    camera_id=camera_b,
                    model_id=None,
                    model_name="successful",
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=20,
                    metrics_url="http://127.0.0.1:19109/metrics",
                ),
            ]
        )

    assert len(samples) == 1
    assert samples[0].model_name == "successful"


@pytest.mark.asyncio
async def test_metrics_probe_keeps_previous_snapshots_per_worker_metrics_url() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    first = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    second = first + timedelta(seconds=10)
    clock_values = [first, first, second, second]
    frame_counts = {
        "http://127.0.0.1:19108/metrics": [10, 30],
        "http://127.0.0.1:19109/metrics": [100, 140],
    }
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url)
        requests.append(request_url)
        camera_id = camera_a if "19108" in request_url else camera_b
        count = frame_counts[request_url].pop(0)
        text = "\n".join(
            [
                _stage_bucket(camera_id, "total", "0.05", count),
                _stage_bucket(camera_id, "total", "+Inf", count),
                (
                    "argus_inference_frames_processed_total"
                    f'{{camera_id="{camera_id}",profile="720p20",stream_mode="annotated"}} {count}'
                ),
            ]
        )
        return httpx.Response(200, text=text)

    contexts = [
        WorkerMetricsContext(
            camera_id=camera_a,
            model_id=None,
            model_name="worker-a",
            runtime_backend="onnxruntime",
            input_width=1280,
            input_height=720,
            target_fps=20,
            metrics_url="http://127.0.0.1:19108/metrics",
        ),
        WorkerMetricsContext(
            camera_id=camera_b,
            model_id=None,
            model_name="worker-b",
            runtime_backend="onnxruntime",
            input_width=1280,
            input_height=720,
            target_fps=20,
            metrics_url="http://127.0.0.1:19109/metrics",
        ),
    ]

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        probe = WorkerMetricsProbe(
            None,
            http_client=http_client,
            clock=lambda: clock_values.pop(0),
        )
        await probe.build_performance_samples(contexts)
        samples = await probe.build_performance_samples(contexts)

    assert requests == [
        "http://127.0.0.1:19108/metrics",
        "http://127.0.0.1:19109/metrics",
        "http://127.0.0.1:19108/metrics",
        "http://127.0.0.1:19109/metrics",
    ]
    assert {sample.model_name: sample.observed_fps for sample in samples} == {
        "worker-a": 2.0,
        "worker-b": 4.0,
    }


@pytest.mark.asyncio
async def test_metrics_probe_does_not_use_legacy_previous_for_per_worker_url() -> None:
    camera_id = uuid4()
    now = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    previous = MetricsSnapshot(
        captured_at=now - timedelta(seconds=10),
        frame_counts={str(camera_id): 100.0},
        histograms={
            (str(camera_id), "total"): [
                (0.05, 100),
                (float("inf"), 100),
            ],
        },
    )
    metrics_text = "\n".join(
        [
            _stage_bucket(camera_id, "total", "0.05", 130),
            _stage_bucket(camera_id, "total", "+Inf", 130),
            (
                "argus_inference_frames_processed_total"
                f'{{camera_id="{camera_id}",profile="720p20",stream_mode="annotated"}} 130'
            ),
        ]
    )

    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text=metrics_text))
    async with httpx.AsyncClient(transport=transport) as http_client:
        probe = WorkerMetricsProbe(
            "http://legacy.local/metrics",
            http_client=http_client,
            clock=lambda: now,
        )
        samples = await probe.build_performance_samples(
            [
                WorkerMetricsContext(
                    camera_id=camera_id,
                    model_id=None,
                    model_name="per-worker",
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=20,
                    metrics_url="http://127.0.0.1:19108/metrics",
                )
            ],
            previous_snapshot=previous,
        )

    assert len(samples) == 1
    assert samples[0].observed_fps is None


@pytest.mark.asyncio
async def test_metrics_probe_does_not_use_per_worker_previous_for_legacy_url() -> None:
    camera_id = uuid4()
    first = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    second = first + timedelta(seconds=10)
    clock_values = [first, second]
    frame_counts = [100, 130]

    def handler(_request: httpx.Request) -> httpx.Response:
        count = frame_counts.pop(0)
        metrics_text = "\n".join(
            [
                _stage_bucket(camera_id, "total", "0.05", count),
                _stage_bucket(camera_id, "total", "+Inf", count),
                (
                    "argus_inference_frames_processed_total"
                    f'{{camera_id="{camera_id}",profile="720p20",stream_mode="annotated"}} {count}'
                ),
            ]
        )
        return httpx.Response(200, text=metrics_text)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        probe = WorkerMetricsProbe(
            "http://legacy.local/metrics",
            http_client=http_client,
            clock=lambda: clock_values.pop(0),
        )
        await probe.build_performance_samples(
            [
                WorkerMetricsContext(
                    camera_id=camera_id,
                    model_id=None,
                    model_name="per-worker",
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=20,
                    metrics_url="http://127.0.0.1:19108/metrics",
                )
            ]
        )
        samples = await probe.build_performance_samples(
            [
                WorkerMetricsContext(
                    camera_id=camera_id,
                    model_id=None,
                    model_name="legacy",
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=20,
                )
            ]
        )

    assert len(samples) == 1
    assert samples[0].observed_fps is None


@pytest.mark.asyncio
async def test_legacy_metrics_url_is_used_when_context_has_no_metrics_url() -> None:
    camera_id = uuid4()
    now = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    requests: list[str] = []
    metrics_text = "\n".join(
        [
            _stage_bucket(camera_id, "total", "0.05", 20),
            _stage_bucket(camera_id, "total", "+Inf", 20),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(200, text=metrics_text)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        probe = WorkerMetricsProbe(
            "http://worker.local/metrics",
            http_client=http_client,
            clock=lambda: now,
        )
        samples = await probe.build_performance_samples(
            [
                WorkerMetricsContext(
                    camera_id=camera_id,
                    model_id=None,
                    model_name="legacy",
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=20,
                )
            ]
        )

    assert requests == ["http://worker.local/metrics"]
    assert len(samples) == 1
    assert samples[0].model_name == "legacy"


@pytest.mark.asyncio
async def test_missing_metrics_url_returns_no_performance_samples() -> None:
    probe = WorkerMetricsProbe(None)

    samples = await probe.build_performance_samples(
        [
            WorkerMetricsContext(
                camera_id=uuid4(),
                model_id=None,
                model_name="YOLO26n COCO",
                runtime_backend="onnxruntime",
                input_width=1280,
                input_height=720,
                target_fps=10,
            )
        ]
    )

    assert samples == []


def _stage_bucket(camera_id: object, stage: str, le: str, value: int) -> str:
    return (
        "argus_inference_stage_duration_seconds_bucket"
        f'{{camera_id="{camera_id}",stage="{stage}",le="{le}"}} {value}'
    )


@pytest.mark.asyncio
async def test_http_failure_returns_no_performance_samples() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(503, text="nope"))
    async with httpx.AsyncClient(transport=transport) as http_client:
        probe = WorkerMetricsProbe("http://worker.local/metrics", http_client=http_client)

        samples = await probe.build_performance_samples(
            [
                WorkerMetricsContext(
                    camera_id=uuid4(),
                    model_id=None,
                    model_name="YOLO26n COCO",
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=10,
                )
            ]
        )

    assert samples == []
