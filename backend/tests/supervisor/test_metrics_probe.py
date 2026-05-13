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
