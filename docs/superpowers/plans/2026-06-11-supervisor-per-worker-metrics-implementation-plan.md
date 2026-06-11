# Supervisor Per-Worker Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add robust per-camera FPS and stage latency reporting when a central or edge supervisor runs multiple child camera workers.

**Architecture:** The supervisor process allocates a private local metrics port for each child worker and injects that port through the worker environment. The supervisor metrics probe scrapes each worker endpoint independently and posts per-camera performance samples in hardware reports. Existing single-endpoint metrics support remains as a compatibility fallback.

**Tech Stack:** Python 3.12/3.10, Pydantic settings, asyncio subprocess workers, Prometheus client, pytest, Docker Compose install files.

---

## File Map

- Modify `backend/src/argus/supervisor/process_adapter.py`
  - Owns per-worker metrics port allocation, child env injection, and release.
- Modify `backend/tests/supervisor/test_process_adapter.py`
  - Tests allocation, env injection, release, startup failure cleanup, and exhausted ranges.
- Modify `backend/src/argus/inference/engine.py`
  - Adds bind address support to the child worker metrics server.
- Modify `backend/src/argus/core/config.py`
  - Adds child worker `worker_metrics_bind_addr`.
- Modify `backend/tests/inference/test_engine.py`
  - Tests bind address is passed to Prometheus server.
- Modify `backend/src/argus/supervisor/metrics_probe.py`
  - Adds per-context metrics URL scraping and per-URL previous snapshots.
- Modify `backend/tests/supervisor/test_metrics_probe.py`
  - Tests multi-target scrape, partial failure, and legacy single-target behavior.
- Modify `backend/src/argus/supervisor/runner.py`
  - Parses supervisor per-worker metrics settings, wires process adapter config, attaches metrics URLs to contexts.
- Modify `backend/tests/supervisor/test_runner.py`
  - Tests config parsing and context URL attachment.
- Modify `infra/install/compose/compose.master.yml`
  - Enables central per-worker metrics internally without publishing host ports.
- Modify `docs/runbook.md`
  - Documents local-only per-worker metrics and central FPS troubleshooting.

---

### Task 1: Process Adapter Per-Worker Metrics Allocation

**Files:**
- Modify: `backend/src/argus/supervisor/process_adapter.py`
- Test: `backend/tests/supervisor/test_process_adapter.py`

- [ ] **Step 1: Write failing tests**

Add tests for:

```python
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
```

Also add tests named:

- `test_start_without_worker_metrics_config_does_not_inject_metrics_env`
- `test_stop_releases_worker_metrics_url`
- `test_start_releases_worker_metrics_port_when_startup_probe_fails`
- `test_start_reports_error_when_worker_metrics_ports_are_exhausted`

- [ ] **Step 2: Verify tests fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/supervisor/test_process_adapter.py -q
```

Expected: failures because `WorkerMetricsLaunchConfig` and `metrics_url_for()` do not exist.

- [ ] **Step 3: Implement minimal process adapter support**

Add `WorkerMetricsLaunchConfig`:

```python
@dataclass(frozen=True, slots=True)
class WorkerMetricsLaunchConfig:
    enabled: bool = False
    bind_addr: str = "127.0.0.1"
    scrape_host: str = "127.0.0.1"
    port_base: int = 19108
    port_count: int = 200
```

Add `worker_metrics: WorkerMetricsLaunchConfig = field(default_factory=WorkerMetricsLaunchConfig)` to `WorkerLaunchConfig`.

Add allocation helpers:

```python
def metrics_url_for(self, camera_id: UUID) -> str | None:
    if not self.is_running(camera_id):
        return None
    return self._metrics_urls.get(camera_id)
```

Allocate before subprocess start, inject env keys, release on stop/startup failure/exited replacement.

- [ ] **Step 4: Verify process adapter tests pass**

Run:

```bash
backend/.venv/bin/pytest backend/tests/supervisor/test_process_adapter.py -q
```

Expected: all tests pass.

---

### Task 2: Child Worker Metrics Bind Address

**Files:**
- Modify: `backend/src/argus/core/config.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write failing test**

Update the worker metrics server test to expect the bind address:

```python
def test_worker_metrics_server_uses_configured_bind_address(monkeypatch) -> None:
    calls: list[tuple[int, str]] = []

    def fake_start_http_server(port: int, addr: str = "0.0.0.0") -> None:
        calls.append((port, addr))

    monkeypatch.setattr(engine_module, "start_http_server", fake_start_http_server)

    engine_module._start_worker_metrics_server(19108, addr="127.0.0.1")

    assert calls == [(19108, "127.0.0.1")]
```

- [ ] **Step 2: Verify test fails**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "worker_metrics_server" -q
```

Expected: failure because `_start_worker_metrics_server` only accepts a port.

- [ ] **Step 3: Implement bind address support**

Add to `Settings`:

```python
worker_metrics_bind_addr: str = "0.0.0.0"
```

Change worker startup:

```python
if resolved_settings.enable_worker_metrics_server:
    _start_worker_metrics_server(
        resolved_settings.worker_metrics_port,
        addr=resolved_settings.worker_metrics_bind_addr,
    )
```

Change helper:

```python
def _start_worker_metrics_server(port: int, *, addr: str = "0.0.0.0") -> None:
    try:
        start_http_server(port, addr=addr)
```

- [ ] **Step 4: Verify engine metrics tests pass**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "worker_metrics_server" -q
```

Expected: all selected tests pass.

---

### Task 3: Multi-Target Metrics Probe

**Files:**
- Modify: `backend/src/argus/supervisor/metrics_probe.py`
- Test: `backend/tests/supervisor/test_metrics_probe.py`

- [ ] **Step 1: Write failing tests**

Add `metrics_url` to `WorkerMetricsContext` uses in tests. Add a multi-target test:

```python
@pytest.mark.asyncio
async def test_metrics_probe_scrapes_each_worker_metrics_url_once() -> None:
    camera_a = uuid4()
    camera_b = uuid4()
    now = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        camera_id = camera_a if "19108" in str(request.url) else camera_b
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
    assert {sample.input_width for sample in samples} == {1280}
    assert len(samples) == 2
```

Add a partial-failure test where one URL returns `503` and the other still yields one sample.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/supervisor/test_metrics_probe.py -q
```

Expected: failures because `WorkerMetricsContext.metrics_url` and multi-target scraping do not exist.

- [ ] **Step 3: Implement multi-target probe**

Add `metrics_url: str | None = None` to `WorkerMetricsContext`.

Refactor `WorkerMetricsProbe` so `build_performance_samples()`:

- groups contexts by `context.metrics_url or self.metrics_url`
- scrapes each distinct URL through a new `_scrape_url(url)` helper
- stores previous snapshots in `self.previous_snapshots: dict[str, MetricsSnapshot]`
- preserves `previous_snapshot` argument for legacy tests
- skips only failed URLs

- [ ] **Step 4: Verify metrics probe tests pass**

Run:

```bash
backend/.venv/bin/pytest backend/tests/supervisor/test_metrics_probe.py -q
```

Expected: all tests pass.

---

### Task 4: Runner Wiring And Configuration

**Files:**
- Modify: `backend/src/argus/supervisor/runner.py`
- Test: `backend/tests/supervisor/test_runner.py`

- [ ] **Step 1: Write failing tests**

Add tests that prove:

- product config reads supervisor worker metrics settings from env when using `--config`
- `_worker_contexts_from_fleet()` attaches URLs from a `metrics_url_for(camera_id)` callback
- `build_runner()` passes `WorkerMetricsLaunchConfig` to `LocalWorkerProcessAdapter`

Example context test:

```python
def test_worker_contexts_include_adapter_metrics_urls() -> None:
    camera_id = uuid4()
    fleet = FleetOverviewResponse(
        summary=FleetSummary(total_cameras=1, running_workers=1, degraded_workers=0),
        camera_workers=[_fleet_worker(camera_id=camera_id)],
    )

    contexts = runner_module._worker_contexts_from_fleet(
        fleet,
        metrics_url_for=lambda value: f"http://127.0.0.1:19108/metrics"
        if value == camera_id
        else None,
    )

    assert contexts[0].metrics_url == "http://127.0.0.1:19108/metrics"
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/supervisor/test_runner.py -q
```

Expected: failures because runner config and context URL callback do not exist.

- [ ] **Step 3: Implement runner wiring**

Add to `RunnerConfig`:

```python
worker_metrics_enabled: bool = False
worker_metrics_bind_addr: str = "127.0.0.1"
worker_metrics_scrape_host: str = "127.0.0.1"
worker_metrics_port_base: int = 19108
worker_metrics_port_count: int = 200
```

Add env parsing for:

- `ARGUS_SUPERVISOR_WORKER_METRICS_ENABLED`
- `ARGUS_SUPERVISOR_WORKER_METRICS_BIND_ADDR`
- `ARGUS_SUPERVISOR_WORKER_METRICS_SCRAPE_HOST`
- `ARGUS_SUPERVISOR_WORKER_METRICS_PORT_BASE`
- `ARGUS_SUPERVISOR_WORKER_METRICS_PORT_COUNT`

Store `self.process_adapter = process_adapter` in `SupervisorRunner`.

Change:

```python
worker_contexts = _worker_contexts_from_fleet(fleet)
```

to:

```python
metrics_url_for = getattr(self.process_adapter, "metrics_url_for", None)
worker_contexts = _worker_contexts_from_fleet(
    fleet,
    metrics_url_for=metrics_url_for if callable(metrics_url_for) else None,
)
```

Build `LocalWorkerProcessAdapter` with `WorkerMetricsLaunchConfig(...)`.

- [ ] **Step 4: Verify runner tests pass**

Run:

```bash
backend/.venv/bin/pytest backend/tests/supervisor/test_runner.py -q
```

Expected: all tests pass.

---

### Task 5: Install Compose And Runbook

**Files:**
- Modify: `infra/install/compose/compose.master.yml`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Update master install compose**

Add to the `vezor-supervisor.environment` block:

```yaml
ARGUS_SUPERVISOR_WORKER_METRICS_ENABLED: ${ARGUS_SUPERVISOR_WORKER_METRICS_ENABLED:-true}
ARGUS_SUPERVISOR_WORKER_METRICS_BIND_ADDR: ${ARGUS_SUPERVISOR_WORKER_METRICS_BIND_ADDR:-127.0.0.1}
ARGUS_SUPERVISOR_WORKER_METRICS_SCRAPE_HOST: ${ARGUS_SUPERVISOR_WORKER_METRICS_SCRAPE_HOST:-127.0.0.1}
ARGUS_SUPERVISOR_WORKER_METRICS_PORT_BASE: ${ARGUS_SUPERVISOR_WORKER_METRICS_PORT_BASE:-19108}
ARGUS_SUPERVISOR_WORKER_METRICS_PORT_COUNT: ${ARGUS_SUPERVISOR_WORKER_METRICS_PORT_COUNT:-200}
```

Do not add host `ports` for the worker metrics range.

- [ ] **Step 2: Update runbook**

Document that central worker FPS comes from per-worker local metrics scraped by the supervisor into `edge_node_hardware_reports.observed_performance`. Include a troubleshooting note:

```bash
docker exec vezor-master-vezor-supervisor-1 sh -lc 'python - <<PY
from pathlib import Path
import socket, struct
for path in ("/proc/net/tcp", "/proc/net/tcp6"):
    try:
        lines = Path(path).read_text().splitlines()[1:]
    except OSError:
        continue
    for line in lines:
        parts = line.split()
        local = parts[1]
        state = parts[3]
        if state == "0A":
            print(local)
PY'
```

The runbook must not ask operators to print raw worker command arguments.

- [ ] **Step 3: Verify docs/config formatting**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

---

### Task 6: Final Verification

**Files:**
- All touched backend, compose, docs files.

- [ ] **Step 1: Run targeted tests**

```bash
backend/.venv/bin/pytest \
  backend/tests/supervisor/test_process_adapter.py \
  backend/tests/supervisor/test_metrics_probe.py \
  backend/tests/supervisor/test_runner.py \
  backend/tests/inference/test_engine.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run broader supervisor/inference tests**

```bash
backend/.venv/bin/pytest \
  backend/tests/supervisor/test_reconciler.py \
  backend/tests/supervisor/test_operations_client.py \
  backend/tests/services/test_operations_service.py \
  backend/tests/api/test_operations_endpoints.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run lint**

```bash
backend/.venv/bin/ruff check \
  backend/src/argus/supervisor/process_adapter.py \
  backend/src/argus/supervisor/metrics_probe.py \
  backend/src/argus/supervisor/runner.py \
  backend/src/argus/inference/engine.py \
  backend/src/argus/core/config.py \
  backend/tests/supervisor/test_process_adapter.py \
  backend/tests/supervisor/test_metrics_probe.py \
  backend/tests/supervisor/test_runner.py \
  backend/tests/inference/test_engine.py
```

Expected: all checks pass.

- [ ] **Step 4: Live smoke if services are available**

If the master stack is running:

1. Rebuild/redeploy master backend/supervisor from the final branch.
2. Restart central worker.
3. Wait at least two hardware report intervals or temporarily run supervisor once if safe.
4. Confirm central `edge_node_hardware_reports.observed_performance` includes `observed_fps`.
5. Confirm central latest runtime report has `selected_provider=onnxruntime` and `runtime_artifact_id IS NULL`.

If Jetson is running:

1. Confirm edge runtime report remains fresh.
2. Confirm edge performance sample still includes `observed_fps`.

If either stack is unavailable, report `NOT RUN` with evidence.
