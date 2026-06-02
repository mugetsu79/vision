# Network-Reachable MediaMTX Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:executing-plans to implement this plan task-by-task. This plan is
> intentionally single-worker because the renderer and installer call sites are
> tightly coupled.

**Goal:** Ensure installed master and edge MediaMTX configs work when the master
is reached through a dedicated private IP or DNS name, without exposing private
infrastructure services to the network.

**Architecture:** Add a standard-library MediaMTX config renderer used by macOS
master, Linux master, and Linux edge installers. The renderer rewrites only known
MediaMTX keys for browser origins, WebRTC advertised hosts, and optional JWKS
URL, while preserving the rest of the source template.

**Tech Stack:** Bash installers, Python standard library, pytest installer
artifact tests, existing MacBook/Jetson install documentation.

---

## Implementation Sequence

Implement sequentially:

1. Renderer tests.
2. Renderer helper.
3. Master installer wiring.
4. Edge installer wiring.
5. Documentation and full verification.

Do not change Docker Compose loopback binds for private services.

## Files

Create:

- `installer/lib/render_mediamtx_config.py`
- `installer/tests/test_mediamtx_config_renderer.py`

Modify:

- `installer/macos/install-master.sh`
- `installer/linux/install-master.sh`
- `installer/linux/install-edge.sh`
- `installer/tests/test_macos_master_artifacts.py`
- `installer/tests/test_linux_master_artifacts.py`
- `installer/tests/test_edge_installer_artifacts.py`
- `docs/macbook-jetson-cross-network-reinstall-guide.md`

Reference:

- `infra/mediamtx/mediamtx.yml`
- `infra/install/compose/compose.master.yml`
- `infra/install/compose/compose.supervisor.yml`

## Task 1: Write Failing Renderer Tests

- [ ] Create `installer/tests/test_mediamtx_config_renderer.py`.

- [ ] Add a test that renders from `infra/mediamtx/mediamtx.yml` with:

```text
frontend origins:
  http://192.168.1.25:3000
  http://localhost:3000
  http://127.0.0.1:3000
webrtc hosts:
  192.168.1.25
  localhost
  127.0.0.1
```

Assert:

- `apiAllowOrigins`, `webrtcAllowOrigins`, and `hlsAllowOrigins` each contain
  `http://192.168.1.25:3000`
- `webrtcAdditionalHosts` contains `192.168.1.25`
- duplicate loopback entries are not emitted
- unrelated path configuration remains present

- [ ] Add a test that renders with:

```text
jwks url:
  http://192.168.1.25:8000/.well-known/argus/mediamtx/jwks.json
frontend origin:
  http://192.168.1.25:3000
webrtc host:
  jetson-01.local
```

Assert:

- `authJWTJWKS` is rewritten to the passed URL
- browser-origin allow lists include the master frontend origin
- `webrtcAdditionalHosts` includes `jetson-01.local`

- [ ] Run:

```bash
python3 -m pytest installer/tests/test_mediamtx_config_renderer.py -q
```

Expected: fail because the renderer helper does not exist.

## Task 2: Implement MediaMTX Config Renderer

- [ ] Create `installer/lib/render_mediamtx_config.py`.

- [ ] Implement CLI arguments:

```text
--source PATH
--dest PATH
--frontend-origin ORIGIN  repeatable
--webrtc-host HOST        repeatable
--jwks-url URL            optional
```

- [ ] Implement helpers:

- `dedupe_preserve_order(values: Iterable[str]) -> list[str]`
- `normalize_origin(value: str) -> str`
- `replace_scalar(text: str, key: str, value: str) -> str`
- `replace_list_block(text: str, key: str, values: list[str]) -> str`

- [ ] Keep the renderer standard-library only.

- [ ] Make the renderer fail with a clear message if any required key is missing:

- `apiAllowOrigins`
- `webrtcAllowOrigins`
- `hlsAllowOrigins`
- `webrtcAdditionalHosts`

- [ ] Write the destination atomically by writing to a temporary sibling file,
  then replacing the final path.

- [ ] Re-run:

```bash
python3 -m pytest installer/tests/test_mediamtx_config_renderer.py -q
```

Expected: pass.

## Task 3: Wire macOS And Linux Master Installers

- [ ] In `installer/macos/install-master.sh`, derive the public host from
  `PUBLIC_URL` using the existing URL parsing helper or add a small reusable
  helper if needed.

- [ ] Replace:

```bash
run install -m 0644 /opt/vezor/current/infra/mediamtx/mediamtx.yml "$CONFIG_DIR/mediamtx/mediamtx.yml"
```

with a renderer invocation that passes:

- `--source /opt/vezor/current/infra/mediamtx/mediamtx.yml`
- `--dest "$CONFIG_DIR/mediamtx/mediamtx.yml"`
- `--frontend-origin "$PUBLIC_URL"`
- `--frontend-origin "http://localhost:3000"`
- `--frontend-origin "http://127.0.0.1:3000"`
- `--webrtc-host "$PUBLIC_HOST"`
- `--webrtc-host "localhost"`
- `--webrtc-host "127.0.0.1"`

- [ ] Apply the same change to `installer/linux/install-master.sh`.

- [ ] Update `installer/tests/test_macos_master_artifacts.py` and
  `installer/tests/test_linux_master_artifacts.py` to assert:

- the scripts call `render_mediamtx_config.py`
- the scripts pass `$PUBLIC_URL`
- the scripts pass the parsed public host to `--webrtc-host`
- the old raw copy command is gone

- [ ] Run:

```bash
python3 -m pytest \
  installer/tests/test_macos_master_artifacts.py \
  installer/tests/test_linux_master_artifacts.py \
  -q
```

Expected: pass.

## Task 4: Wire Linux Edge Installer

- [ ] In `installer/linux/install-edge.sh`, add optional CLI argument:

```text
--frontend-url URL
```

This is the master frontend URL allowed by edge MediaMTX. If omitted, derive it
from `--api-url` by keeping the scheme and host and using port `3000`.

- [ ] Parse `EDGE_STREAM_HOST` from `PUBLIC_MEDIAMTX_RTSP_URL`.

- [ ] Replace the inline Python heredoc that only rewrites `authJWTJWKS` with the
  shared renderer invocation.

- [ ] Pass:

- `--source "$RELEASE_DIR/infra/mediamtx/mediamtx.yml"`
- `--dest "$MEDIAMTX_CONFIG"`
- `--jwks-url "$API_URL/.well-known/argus/mediamtx/jwks.json"`
- `--frontend-origin "$FRONTEND_URL"`
- `--frontend-origin "http://localhost:3000"`
- `--frontend-origin "http://127.0.0.1:3000"`
- `--webrtc-host "$EDGE_STREAM_HOST"`
- `--webrtc-host "localhost"`
- `--webrtc-host "127.0.0.1"`

- [ ] Update `installer/tests/test_edge_installer_artifacts.py` to assert:

- `--frontend-url` appears in usage and argument parsing
- `render_mediamtx_config.py` is used
- the JWKS URL still comes from `--api-url`
- the edge stream host is passed as a WebRTC host
- the previous JWKS-only heredoc is gone

- [ ] Run:

```bash
python3 -m pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: pass.

## Task 5: Update Operator Documentation

- [ ] Update `docs/macbook-jetson-cross-network-reinstall-guide.md`.

- [ ] Add a dedicated-IP MediaMTX check after master install:

```bash
sudo grep -A8 -E 'apiAllowOrigins|webrtcAllowOrigins|hlsAllowOrigins|webrtcAdditionalHosts' \
  /etc/vezor/mediamtx/mediamtx.yml
```

Expected entries:

- `http://MASTER_PRIVATE_IP:3000`
- `MASTER_PRIVATE_IP`
- loopback fallback entries

- [ ] Add an edge MediaMTX check after edge install:

```bash
sudo grep -A8 -E 'authJWTJWKS|webrtcAdditionalHosts|webrtcAllowOrigins' \
  /etc/vezor/mediamtx/mediamtx.yml
```

Expected entries:

- `http://MASTER_PRIVATE_IP:8000/.well-known/argus/mediamtx/jwks.json`
- master frontend origin
- edge stream host

- [ ] Add a note that loopback binds for private services are expected and safe:

- Postgres
- Redis
- MinIO
- normal NATS and NATS monitoring
- MediaMTX API
- worker metrics

## Task 6: Full Verification

- [ ] Run renderer tests:

```bash
python3 -m pytest installer/tests/test_mediamtx_config_renderer.py -q
```

- [ ] Run installer artifact tests:

```bash
python3 -m pytest \
  installer/tests/test_macos_master_artifacts.py \
  installer/tests/test_linux_master_artifacts.py \
  installer/tests/test_edge_installer_artifacts.py \
  -q
```

- [ ] Run the broader installer verification if time allows:

```bash
make verify-installers
```

- [ ] Manually inspect the changed files for accidental service exposure:

```bash
rg -n "VEZOR_.*_BIND|127\\.0\\.0\\.1|localhost|webrtcAdditionalHosts|AllowOrigins" \
  infra installer docs/macbook-jetson-cross-network-reinstall-guide.md
```

Expected: only MediaMTX browser-facing origins and WebRTC additional hosts are
made network-aware. Private service bind defaults remain loopback.

## Manual Smoke On MacBook And Jetson

After implementation is merged into the test branch:

1. Reinstall the MacBook master with:

```bash
sudo ./installer/macos/install-master.sh \
  --public-url "http://MASTER_PRIVATE_IP:3000"
```

2. Confirm `/etc/vezor/mediamtx/mediamtx.yml` includes the master private IP in
   origins and WebRTC hosts.

3. Reinstall the Jetson edge with:

```bash
sudo ./installer/linux/install-edge.sh \
  --api-url "http://MASTER_PRIVATE_IP:8000" \
  --public-mediamtx-rtsp-url "rtsp://JETSON_PRIVATE_IP:8554"
```

4. Confirm the edge MediaMTX config includes the master API JWKS URL, master
   frontend origin, and Jetson stream host.

5. From a browser that is not the master itself, open:

```text
http://MASTER_PRIVATE_IP:3000
```

6. Test Live with HLS/native and forced WebRTC if the UI profile allows it.

## Completion Criteria

- All renderer and installer tests pass.
- Documentation contains explicit verification steps for master and edge.
- No private service bind is widened from loopback as part of this change.
- Installed MediaMTX config reflects the dedicated private IP or DNS name passed
  to the installer.
