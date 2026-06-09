# Core Link Install-Time Throughput Payload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an installer-created throughput `.bin`, run an initial edge-origin speed sample, and make Link Performance active-connection state meaningful for edge-agent control paths.

**Architecture:** Generate a bounded payload on the master host and serve it through the backend with admin/node-credential auth. Extend edge-agent config and run modes to include optional throughput measurement. Add a small run-request contract for manual edge-origin throughput triggers and improve summary/UI fallback labels.

**Tech Stack:** Bash installers, FastAPI streaming responses, Python edge agent, SQLAlchemy link service, React/Vitest, pytest.

---

## File Structure

- Modify: `installer/macos/install-master.sh`
  - Create the throughput payload and SHA256 sidecar.
- Modify: `installer/linux/install-master.sh`
  - Create the throughput payload and SHA256 sidecar.
- Modify: `infra/install/compose/compose.master.yml`
  - Mount the throughput payload directory into backend read-only.
- Modify: `backend/src/argus/core/config.py`
  - Add throughput payload path, max bytes, and public URL settings.
- Modify: `backend/src/argus/link/api.py`
  - Add payload streaming route and edge throughput run-request route.
- Modify: `backend/src/argus/link/edge_agent.py`
  - Add `--include-throughput`, download measurement, and payload hash checks.
- Modify: `backend/src/argus/link/contracts.py`
  - Add metadata fields for throughput bytes, duration, URL id, and payload hash.
- Modify: `backend/src/argus/link/service.py`
  - Store and summarize edge throughput samples and synthesize control-path active connection labels.
- Modify: `installer/linux/install-edge.sh`
  - Run one edge-agent throughput sample after service install.
- Modify: `bin/vezor-edge-agent`
  - Pass include-throughput flags from env.
- Modify: `frontend/src/components/link/LinkPosturePanel.tsx`
  - Show control-path active connection fallback instead of `unknown / unknown`.
- Modify: `frontend/src/components/link/LinkProbePanel.tsx`
  - Add **Measure edge throughput** action for edge-agent targets.
- Modify: `frontend/src/hooks/use-link.ts`
  - Add mutation for edge throughput trigger.
- Modify: `docs/core-link-performance-guide.md`
  - Document payload, install-time sample, and manual trigger semantics.

## Task 1: Master Installer Throughput Payload

- [ ] **Step 1: Write failing installer tests**

Update `installer/tests/test_macos_master_artifacts.py` and
`installer/tests/test_linux_master_artifacts.py`:

```python
def test_master_install_creates_link_throughput_payload() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "VEZOR_LINK_THROUGHPUT_DIR" in script
    assert "vezor-speed-test-64MiB.bin" in script
    assert "sha256sum" in script or "shasum -a 256" in script
    assert "create_link_throughput_payload" in script
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m uv run --project installer pytest installer/tests/test_macos_master_artifacts.py::test_master_install_creates_link_throughput_payload installer/tests/test_linux_master_artifacts.py::test_master_install_creates_link_throughput_payload -q
```

Expected: FAIL because installers do not create the payload.

- [ ] **Step 3: Implement payload creation**

Add to both master installers:

```bash
LINK_THROUGHPUT_DIR="$DATA_DIR/link-throughput"
LINK_THROUGHPUT_PAYLOAD="$LINK_THROUGHPUT_DIR/vezor-speed-test-64MiB.bin"
LINK_THROUGHPUT_SHA256="$LINK_THROUGHPUT_PAYLOAD.sha256"

create_link_throughput_payload() {
  run install -d -m 0755 "$LINK_THROUGHPUT_DIR"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] create link throughput payload $LINK_THROUGHPUT_PAYLOAD"
    return 0
  fi
  if [[ ! -s "$LINK_THROUGHPUT_PAYLOAD" || "$(stat -f%z "$LINK_THROUGHPUT_PAYLOAD" 2>/dev/null || stat -c%s "$LINK_THROUGHPUT_PAYLOAD")" != "67108864" ]]; then
    python3 - "$LINK_THROUGHPUT_PAYLOAD" <<'PY'
from pathlib import Path
import hashlib
import sys

path = Path(sys.argv[1])
block = hashlib.sha256(b"vezor-link-throughput-v1").digest()
with path.open("wb") as handle:
    for _ in range(67108864 // len(block)):
        handle.write(block)
    remaining = 67108864 % len(block)
    if remaining:
        handle.write(block[:remaining])
PY
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$LINK_THROUGHPUT_PAYLOAD" > "$LINK_THROUGHPUT_SHA256"
  else
    shasum -a 256 "$LINK_THROUGHPUT_PAYLOAD" > "$LINK_THROUGHPUT_SHA256"
  fi
  chmod 0644 "$LINK_THROUGHPUT_PAYLOAD" "$LINK_THROUGHPUT_SHA256"
}
```

Call `create_link_throughput_payload` before writing `master.env`.

- [ ] **Step 4: Run installer tests**

Run:

```bash
python3 -m uv run --project installer pytest installer/tests/test_macos_master_artifacts.py installer/tests/test_linux_master_artifacts.py -q
```

Expected: PASS.

## Task 2: Authenticated Payload Route

- [ ] **Step 1: Write failing API tests**

Add to `backend/tests/api/test_link_routes.py`:

```python
async def test_admin_can_download_link_throughput_payload(tmp_path, app_with_link_services):
    payload = tmp_path / "vezor-speed-test-64MiB.bin"
    payload.write_bytes(b"x" * 1024)
    app_with_link_services.state.settings.link_throughput_payload_path = str(payload)

    async with AsyncClient(transport=ASGITransport(app=app_with_link_services), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/link/throughput/payload.bin",
            headers={"Authorization": "Bearer admin-token"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.content == b"x" * 1024
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_link_routes.py::test_admin_can_download_link_throughput_payload -q
```

Expected: FAIL because the route does not exist.

- [ ] **Step 3: Implement route**

Add config:

```python
link_throughput_payload_path: str = "/var/lib/vezor/link-throughput/vezor-speed-test-64MiB.bin"
link_throughput_payload_max_bytes: int = 67_108_864
```

Add route in `backend/src/argus/link/api.py`:

```python
@router.get("/throughput/payload.bin")
async def get_link_throughput_payload(current_user: CurrentUserDependency, services: ServicesDependency):
    enforce_role(current_user, RoleEnum.VIEWER)
    path = Path(services.settings.link_throughput_payload_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Throughput payload is not installed.")
    return FileResponse(path, media_type="application/octet-stream", filename="vezor-speed-test.bin")
```

Then add the same route access for authorized node credentials using the
existing node-credential dependency pattern from deployment/link edge-agent
config routes.

- [ ] **Step 4: Run link API tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_link_routes.py -q
```

Expected: PASS.

## Task 3: Edge Agent Throughput Measurement

- [ ] **Step 1: Write failing edge-agent test**

Add to `backend/tests/link/test_edge_agent.py`:

```python
async def test_edge_agent_measures_authenticated_payload_throughput(httpx_mock):
    payload = b"x" * 1048576
    httpx_mock.add_response(
        method="GET",
        url="http://master/api/v1/link/throughput/payload.bin",
        content=payload,
    )

    result = await measure_throughput_payload(
        url="http://master/api/v1/link/throughput/payload.bin",
        bearer_token="node-token",
        max_bytes=1048576,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert result.bytes_received == 1048576
    assert result.throughput_mbps > 0
    assert result.sha256 == hashlib.sha256(payload).hexdigest()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/link/test_edge_agent.py::test_edge_agent_measures_authenticated_payload_throughput -q
```

Expected: FAIL because throughput measurement is not implemented in edge agent.

- [ ] **Step 3: Implement measurement helper**

In `backend/src/argus/link/edge_agent.py`, add:

```python
@dataclass(frozen=True)
class ThroughputMeasurement:
    bytes_received: int
    duration_seconds: float
    throughput_mbps: float
    sha256: str


async def measure_throughput_payload(
    *,
    url: str,
    bearer_token: str,
    max_bytes: int,
    expected_sha256: str | None,
) -> ThroughputMeasurement:
    started = time.perf_counter()
    digest = hashlib.sha256()
    received = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", url, headers={"Authorization": f"Bearer {bearer_token}"}) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                if not chunk:
                    continue
                allowed = min(len(chunk), max_bytes - received)
                digest.update(chunk[:allowed])
                received += allowed
                if received >= max_bytes:
                    break
    duration = max(time.perf_counter() - started, 0.001)
    sha256 = digest.hexdigest()
    if expected_sha256 and sha256 != expected_sha256:
        raise RuntimeError("Throughput payload SHA256 mismatch.")
    return ThroughputMeasurement(
        bytes_received=received,
        duration_seconds=duration,
        throughput_mbps=(received * 8) / duration / 1_000_000,
        sha256=sha256,
    )
```

- [ ] **Step 4: Include throughput in posted sample metadata**

When `--include-throughput` is passed and edge-agent config contains a
throughput URL, add metadata:

```python
{
    "throughput_bytes": measurement.bytes_received,
    "throughput_duration_seconds": measurement.duration_seconds,
    "throughput_payload_sha256": measurement.sha256,
    "throughput_url_id": "master-installed-payload",
}
```

Set `throughput_mbps` to the measured Mbps instead of `0.0`.

- [ ] **Step 5: Run edge-agent tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/link/test_edge_agent.py -q
```

Expected: PASS.

## Task 4: Install-Time Edge Sample

- [ ] **Step 1: Write failing installer artifact test**

Update `installer/tests/test_edge_installer_artifacts.py`:

```python
def test_edge_installer_runs_initial_edge_throughput_sample() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "VEZOR_LINK_EDGE_AGENT_INCLUDE_THROUGHPUT=1" in script
    assert "vezor-edge-agent --once" in script
    assert "Initial edge-agent throughput sample" in script
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project installer pytest installer/tests/test_edge_installer_artifacts.py::test_edge_installer_runs_initial_edge_throughput_sample -q
```

Expected: FAIL because edge installer does not run the throughput sample.

- [ ] **Step 3: Update wrapper and installer**

In `bin/vezor-edge-agent`, support:

```bash
if [[ "${VEZOR_LINK_EDGE_AGENT_INCLUDE_THROUGHPUT:-0}" = "1" ]]; then
  EXTRA_ARGS+=(--include-throughput)
fi
```

In `installer/linux/install-edge.sh`, after starting `vezor-edge.service`:

```bash
echo "Initial edge-agent throughput sample..."
VEZOR_LINK_EDGE_AGENT_INCLUDE_THROUGHPUT=1 \
  /opt/vezor/current/bin/vezor-edge-agent --once || \
  echo "Initial edge-agent throughput sample did not complete; inspect vezor-edge-agent.service logs."
```

- [ ] **Step 4: Run installer tests**

Run:

```bash
python3 -m uv run --project installer pytest installer/tests/test_edge_installer_artifacts.py -q
scripts/validate-installers.sh
```

Expected: PASS.

## Task 5: Manual Edge-Origin Throughput Trigger And UI

- [ ] **Step 1: Write failing route test**

Add to `backend/tests/api/test_link_routes.py`:

```python
async def test_admin_can_request_edge_origin_throughput_sample(client, edge_site):
    response = await client.post(
        f"/api/v1/link/sites/{edge_site.id}/probe-targets/vezor-master-udp-reflector/measure-edge-throughput",
        headers={"Authorization": "Bearer admin-token"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
```

- [ ] **Step 2: Implement run request**

Create a lightweight persisted request in the link service, or reuse the
existing probe-target metadata if a durable queue already exists. The response
must include `queued`, `request_id`, `site_id`, and `target_id`.

- [ ] **Step 3: Write failing UI test**

Update `frontend/src/components/link/LinkProbePanel.test.tsx`:

```tsx
test("offers edge-origin throughput measurement for edge-agent targets", async () => {
  render(<LinkProbePanel siteId="site-1" connections={[edgeAgentConnection]} probes={[]} />);

  await userEvent.click(screen.getByRole("button", { name: /measure edge throughput/i }));

  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("/measure-edge-throughput"),
    expect.objectContaining({ method: "POST" }),
  );
});
```

- [ ] **Step 4: Implement hook and UI action**

Add `useMeasureEdgeThroughputTarget` to `frontend/src/hooks/use-link.ts` and a
button labeled **Measure edge throughput** on edge-agent targets. Keep existing
backend-synthetic **Measure throughput** only for configured HTTP/HTTPS targets.

- [ ] **Step 5: Run link tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_link_routes.py -q
corepack pnpm --dir frontend test src/components/link src/hooks/use-link.test.ts
```

Expected: PASS.

## Task 6: Active Connection Fallback Clarity

- [ ] **Step 1: Write failing UI test**

Update `frontend/src/components/link/LinkPosturePanel.test.tsx`:

```tsx
test("shows edge-agent control path instead of unknown active connection", () => {
  render(
    <LinkPosturePanel
      status={{
        link_state: "healthy",
        active_connection: null,
        fallback_active_path: {
          label: "Vezor Master reflector via jetson-orin-1 Core Link",
          detail: "Latest edge-agent sample 4 ms / 128 Mbps / 0% loss",
        },
      }}
    />,
  );

  expect(screen.getByText("Vezor Master reflector via jetson-orin-1 Core Link")).toBeInTheDocument();
  expect(screen.queryByText("unknown / unknown")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Implement service fallback**

Extend the link status response with:

```python
fallback_active_path: {
    "label": "Vezor Master reflector via jetson-orin-1 Core Link",
    "detail": "Latest edge-agent sample 4 ms / 128 Mbps / 0% loss",
}
```

when there is no explicit active connection but the site has a recent
edge-agent target sample.

- [ ] **Step 3: Update UI**

Update `LinkPosturePanel.tsx` so Active connection displays:

1. selected configured connection if present;
2. fallback active path if present;
3. "No configured link path" if neither exists.

- [ ] **Step 4: Run frontend tests**

Run:

```bash
corepack pnpm --dir frontend test src/components/link/LinkPosturePanel.test.tsx src/components/link/LinkProbePanel.test.tsx
```

Expected: PASS.

## Task 7: Installed Smoke

- [ ] **Step 1: Fresh master install evidence**

Verify:

```bash
ls -lh /var/lib/vezor/link-throughput/vezor-speed-test-64MiB.bin
shasum -a 256 /var/lib/vezor/link-throughput/vezor-speed-test-64MiB.bin
```

Expected: 64 MiB payload and matching sidecar.

- [ ] **Step 2: Fresh edge install evidence**

Run the Jetson edge installer and confirm one install-time sample:

```bash
ssh ai-user@JETSON 'journalctl -u vezor-edge-agent.service -n 100 --no-pager'
```

Expected: an edge-agent sample with `throughput_mbps > 0`, `throughput_bytes`,
and `throughput_payload_sha256`.

- [ ] **Step 3: UI evidence**

Open Link Performance, select the edge site, click **Measure edge throughput**,
and verify:

- sample history adds a new edge-agent throughput sample;
- Active connection shows a meaningful edge-agent/control path label;
- no raw token or node credential appears in browser console, network logs, or
  report output.
