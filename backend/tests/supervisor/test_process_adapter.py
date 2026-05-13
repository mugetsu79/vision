from __future__ import annotations

import sys
from collections.abc import Mapping
from uuid import uuid4

import pytest

from argus.supervisor.process_adapter import (
    LocalWorkerProcessAdapter,
    WorkerLaunchConfig,
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
