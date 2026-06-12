from __future__ import annotations

import sys
from collections.abc import Mapping
from uuid import uuid4

import pytest

from argus.supervisor.process_adapter import (
    LocalWorkerProcessAdapter,
    WorkerLaunchConfig,
    WorkerMetricsLaunchConfig,
)


@pytest.mark.asyncio
async def test_start_uses_structured_default_worker_argv_and_env() -> None:
    camera_id = uuid4()
    edge_node_id = uuid4()
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] = []

    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        calls.append((argv, env))
        return _FakeProcess()

    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(
            api_base_url="http://127.0.0.1:8000",
            bearer_token="token",
            edge_node_id=edge_node_id,
            base_env={"ARGUS_MINIO_ENDPOINT": "127.0.0.1:9000"},
        ),
        subprocess_exec=_exec,
    )

    result = await adapter.start(camera_id)

    assert result.runtime_state == "running"
    assert adapter.is_running(camera_id)
    assert calls[0][0] == (
        sys.executable,
        "-m",
        "argus.inference.engine",
        "--camera-id",
        str(camera_id),
    )
    env = calls[0][1]
    assert env["ARGUS_API_BASE_URL"] == "http://127.0.0.1:8000"
    assert env["ARGUS_API_BEARER_TOKEN"] == "token"
    assert env["ARGUS_EDGE_NODE_ID"] == str(edge_node_id)
    assert env["ARGUS_MINIO_ENDPOINT"] == "127.0.0.1:9000"


@pytest.mark.asyncio
async def test_start_can_inject_bearer_token_from_async_provider() -> None:
    camera_id = uuid4()
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] = []

    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        calls.append((argv, env))
        return _FakeProcess()

    async def _token_provider() -> str:
        return "fresh-worker-token"

    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(
            api_base_url="http://127.0.0.1:8000",
            bearer_token_provider=_token_provider,
            base_env={},
        ),
        subprocess_exec=_exec,
    )

    result = await adapter.start(camera_id)

    assert result.runtime_state == "running"
    assert calls[0][1]["ARGUS_API_BEARER_TOKEN"] == "fresh-worker-token"


@pytest.mark.asyncio
async def test_stop_terminates_tracked_process_and_reports_stopped() -> None:
    camera_id = uuid4()
    process = _FakeProcess()
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}),
        subprocess_exec=_exec_factory(process),
    )
    await adapter.start(camera_id)

    result = await adapter.stop(camera_id)

    assert result.runtime_state == "stopped"
    assert not adapter.is_running(camera_id)
    assert process.terminate_called is True
    assert process.kill_called is False


@pytest.mark.asyncio
async def test_stop_terminates_matching_stale_process_when_process_map_is_empty() -> None:
    camera_id = uuid4()
    stale_process = _FakeProcess()
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}),
        process_finder=lambda requested_camera_id: (
            [stale_process] if requested_camera_id == camera_id else []
        ),
    )

    result = await adapter.stop(camera_id)

    assert result.runtime_state == "stopped"
    assert result.last_error is None
    assert stale_process.terminate_called is True


@pytest.mark.asyncio
async def test_stop_reports_error_when_matching_process_survives_verification() -> None:
    camera_id = uuid4()
    stale_process = _StubbornProcess()
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}, graceful_timeout_seconds=0.01),
        process_finder=lambda requested_camera_id: (
            [stale_process] if requested_camera_id == camera_id else []
        ),
    )

    result = await adapter.stop(camera_id)

    assert result.runtime_state == "error"
    assert result.last_error == "Matching worker process remained after stop."
    assert stale_process.terminate_called is True
    assert stale_process.kill_called is True


@pytest.mark.asyncio
async def test_restart_stops_then_starts_worker() -> None:
    camera_id = uuid4()
    first_process = _FakeProcess()
    second_process = _FakeProcess()
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}),
        subprocess_exec=_exec_sequence([first_process, second_process]),
    )
    await adapter.start(camera_id)

    result = await adapter.restart(camera_id)

    assert result.runtime_state == "running"
    assert first_process.terminate_called is True
    assert second_process.terminate_called is False


@pytest.mark.asyncio
async def test_drain_stops_accepting_new_work_and_only_terminates_target_worker() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    process_a = _FakeProcess()
    process_b = _FakeProcess()
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}),
        subprocess_exec=_exec_sequence([process_a, process_b]),
    )
    await adapter.start(camera_a)
    await adapter.start(camera_b)

    result = await adapter.drain(camera_a)

    assert result.runtime_state == "stopped"
    assert adapter.accepting_new_work is False
    assert process_a.terminate_called is True
    assert process_b.terminate_called is False


@pytest.mark.asyncio
async def test_start_resumes_after_drain_for_explicit_operator_start() -> None:
    camera_id = uuid4()
    first_process = _FakeProcess()
    second_process = _FakeProcess()
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}),
        subprocess_exec=_exec_sequence([first_process, second_process]),
    )
    await adapter.start(camera_id)
    await adapter.drain(camera_id)

    result = await adapter.start(camera_id)

    assert result.runtime_state == "running"
    assert result.last_error is None
    assert adapter.accepting_new_work is True
    assert adapter.is_running(camera_id)
    assert first_process.terminate_called is True
    assert second_process.terminate_called is False


@pytest.mark.asyncio
async def test_start_reports_error_when_subprocess_creation_fails() -> None:
    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        del argv, env
        raise OSError("no python")

    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}),
        subprocess_exec=_exec,
    )

    result = await adapter.start(uuid4())

    assert result.runtime_state == "error"
    assert result.last_error == "no python"


@pytest.mark.asyncio
async def test_start_reports_error_when_worker_exits_during_startup_probe() -> None:
    camera_id = uuid4()
    process = _FakeProcess()
    process.returncode = 2
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}, startup_probe_seconds=0),
        subprocess_exec=_exec_factory(process),
    )

    result = await adapter.start(camera_id)

    assert result.runtime_state == "error"
    assert result.last_error == "Worker exited during startup with code 2."
    assert not adapter.is_running(camera_id)


@pytest.mark.asyncio
async def test_start_allocates_distinct_worker_metrics_ports_and_env() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] = []

    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        calls.append((argv, env))
        return _FakeProcess()

    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(
            base_env={},
            worker_metrics=WorkerMetricsLaunchConfig(
                enabled=True,
                bind_addr="127.0.0.1",
                scrape_host="127.0.0.1",
                port_base=19108,
                port_count=2,
            ),
        ),
        subprocess_exec=_exec,
    )

    assert (await adapter.start(camera_a)).runtime_state == "running"
    assert (await adapter.start(camera_b)).runtime_state == "running"

    assert calls[0][1]["ARGUS_ENABLE_WORKER_METRICS_SERVER"] == "true"
    assert calls[0][1]["ARGUS_WORKER_METRICS_BIND_ADDR"] == "127.0.0.1"
    assert calls[0][1]["ARGUS_WORKER_METRICS_PORT"] == "19108"
    assert calls[1][1]["ARGUS_WORKER_METRICS_PORT"] == "19109"
    assert adapter.metrics_url_for(camera_a) == "http://127.0.0.1:19108/metrics"
    assert adapter.metrics_url_for(camera_b) == "http://127.0.0.1:19109/metrics"


@pytest.mark.asyncio
async def test_start_without_worker_metrics_config_does_not_inject_metrics_env() -> None:
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] = []

    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        calls.append((argv, env))
        return _FakeProcess()

    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(base_env={}),
        subprocess_exec=_exec,
    )

    result = await adapter.start(uuid4())

    assert result.runtime_state == "running"
    assert "ARGUS_ENABLE_WORKER_METRICS_SERVER" not in calls[0][1]
    assert "ARGUS_WORKER_METRICS_BIND_ADDR" not in calls[0][1]
    assert "ARGUS_WORKER_METRICS_PORT" not in calls[0][1]


@pytest.mark.asyncio
async def test_stop_releases_worker_metrics_url() -> None:
    camera_id = uuid4()
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(
            base_env={},
            worker_metrics=WorkerMetricsLaunchConfig(
                enabled=True,
                port_base=19108,
                port_count=1,
            ),
        ),
        subprocess_exec=_exec_factory(_FakeProcess()),
    )
    await adapter.start(camera_id)

    result = await adapter.stop(camera_id)

    assert result.runtime_state == "stopped"
    assert adapter.metrics_url_for(camera_id) is None


@pytest.mark.asyncio
async def test_start_releases_worker_metrics_port_when_startup_probe_fails() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    failed_process = _FakeProcess()
    failed_process.returncode = 2
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] = []

    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        calls.append((argv, env))
        return failed_process if len(calls) == 1 else _FakeProcess()

    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(
            base_env={},
            startup_probe_seconds=0,
            worker_metrics=WorkerMetricsLaunchConfig(
                enabled=True,
                port_base=19108,
                port_count=1,
            ),
        ),
        subprocess_exec=_exec,
    )

    failed = await adapter.start(camera_a)
    started = await adapter.start(camera_b)

    assert failed.runtime_state == "error"
    assert started.runtime_state == "running"
    assert calls[0][1]["ARGUS_WORKER_METRICS_PORT"] == "19108"
    assert calls[1][1]["ARGUS_WORKER_METRICS_PORT"] == "19108"
    assert adapter.metrics_url_for(camera_a) is None
    assert adapter.metrics_url_for(camera_b) == "http://127.0.0.1:19108/metrics"


@pytest.mark.asyncio
async def test_start_reports_error_when_worker_metrics_ports_are_exhausted() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(
            base_env={},
            worker_metrics=WorkerMetricsLaunchConfig(
                enabled=True,
                port_base=19108,
                port_count=1,
            ),
        ),
        subprocess_exec=_exec_factory(_FakeProcess()),
    )

    started = await adapter.start(camera_a)
    exhausted = await adapter.start(camera_b)

    assert started.runtime_state == "running"
    assert exhausted.runtime_state == "error"
    assert exhausted.last_error == "No worker metrics ports available in range 19108-19108."
    assert adapter.metrics_url_for(camera_b) is None


@pytest.mark.asyncio
async def test_start_releases_dead_worker_metrics_port_before_starting_different_camera() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    process_a = _FakeProcess()
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] = []

    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        calls.append((argv, env))
        return process_a if len(calls) == 1 else _FakeProcess()

    adapter = LocalWorkerProcessAdapter(
        WorkerLaunchConfig(
            base_env={},
            worker_metrics=WorkerMetricsLaunchConfig(
                enabled=True,
                port_base=19108,
                port_count=1,
            ),
        ),
        subprocess_exec=_exec,
    )
    assert (await adapter.start(camera_a)).runtime_state == "running"
    process_a.returncode = 9

    result = await adapter.start(camera_b)

    assert result.runtime_state == "running"
    assert calls[1][1]["ARGUS_WORKER_METRICS_PORT"] == "19108"
    assert adapter.metrics_url_for(camera_a) is None
    assert adapter.metrics_url_for(camera_b) == "http://127.0.0.1:19108/metrics"


class _FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminate_called = False
        self.kill_called = False

    def terminate(self) -> None:
        self.terminate_called = True
        self.returncode = 0

    def kill(self) -> None:
        self.kill_called = True
        self.returncode = -9

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


class _StubbornProcess(_FakeProcess):
    def terminate(self) -> None:
        self.terminate_called = True

    def kill(self) -> None:
        self.kill_called = True

    async def wait(self) -> int:
        return 0


def _exec_factory(process: _FakeProcess):
    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        del argv, env
        return process

    return _exec


def _exec_sequence(processes: list[_FakeProcess]):
    async def _exec(*argv: str, env: Mapping[str, str]) -> _FakeProcess:
        del argv, env
        return processes.pop(0)

    return _exec
