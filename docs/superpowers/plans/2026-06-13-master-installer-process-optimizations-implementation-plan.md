# Master Installer Process Optimizations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make bare-metal Linux and macOS master installs easier to preflight, rerun, diagnose, and release-harden while preserving current product install behavior.

**Architecture:** Keep the existing shell entrypoints for privileged host operations and move brittle parsing, manifest policy, redacted diagnostics, and health waits into small tested Python helpers. Add explicit `install`, `preflight`, and `reconfigure` modes without changing the edge installer or central acceleration claims.

**Tech Stack:** Bash installers, Python 3.12 installer package, pytest, Docker/Podman Compose appliance, systemd, launchd, HTTP health probes.

---

## Execution Notes

- Preserve unrelated and untracked local files.
- Write failing tests before implementation.
- Do not commit or push unless the user explicitly asks. When a task says "commit checkpoint", skip that step unless explicit permission has been given.
- Do not change edge installer runtime profiles in this plan.
- Do not claim central Dockerized GPU, Apple M-series, CUDA, OpenVINO, TensorRT, or DeepStream acceleration.
- Do not print secrets, bootstrap tokens, bearer tokens, RTSP credentials, sudo passwords, raw environment values, or raw process arguments.

## File Structure

- Modify `installer/linux/install-master.sh`: add `--mode`, preflight and reconfigure flow, shared helper calls, central CPU tuning flags, post-start health gate.
- Modify `installer/macos/install-master.sh`: add `--mode`, aligned preflight flow, central CPU tuning flags, post-start health gate.
- Create `installer/lib/master_install_common.sh`: shared shell glue for mode values and helper invocation.
- Create `installer/vezor_installer/master_manifest.py`: manifest policy and image key validation.
- Create `installer/vezor_installer/master_preflight.py`: public URL, Docker, disk, port, and redaction diagnostics.
- Create `installer/vezor_installer/master_health.py`: bounded backend, frontend, Keycloak, and supervisor health waits.
- Create `installer/tests/test_master_manifest.py`: manifest policy tests.
- Create `installer/tests/test_master_preflight.py`: diagnostics and redaction tests.
- Create `installer/tests/test_master_health.py`: health gate tests.
- Modify `installer/tests/test_linux_master_artifacts.py`: Linux mode, reconfigure, and CPU flag assertions.
- Modify `installer/tests/test_macos_master_artifacts.py`: macOS mode, Docker Desktop, and health assertions.
- Modify `installer/README.md`: document modes and safe diagnostics.
- Modify `docs/full-installation-guide.md`: document preflight, reconfigure, and central CPU tuning.

---

### Task 1: Manifest Policy Helper

**Files:**
- Create: `installer/tests/test_master_manifest.py`
- Create: `installer/vezor_installer/master_manifest.py`

- [ ] **Step 1: Write failing manifest policy tests**

Create `installer/tests/test_master_manifest.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vezor_installer.master_manifest import ManifestPolicyError, resolve_master_images


def _manifest(tmp_path: Path, *, channel: str, images: dict[str, str]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "release_channel": channel,
                "images": {
                    key: {"reference": value}
                    for key, value in images.items()
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_dev_manifest_allows_fallback_images(tmp_path: Path) -> None:
    path = _manifest(tmp_path, channel="dev", images={})

    images = resolve_master_images(path, allow_dev_fallbacks=True)

    assert images["backend"] == "vezor/backend:portable-demo"
    assert images["frontend"] == "vezor/frontend:portable-demo"
    assert images["supervisor"] == "vezor/backend:portable-demo"


def test_pilot_manifest_requires_product_image_keys(tmp_path: Path) -> None:
    path = _manifest(tmp_path, channel="pilot", images={"backend": "ghcr.io/acme/backend:v1"})

    with pytest.raises(ManifestPolicyError, match="missing required image keys"):
        resolve_master_images(path, allow_dev_fallbacks=False)


def test_stable_manifest_rejects_mutable_image_tags(tmp_path: Path) -> None:
    path = _manifest(
        tmp_path,
        channel="stable",
        images={
            "postgres": "timescale/timescaledb@sha256:" + "a" * 64,
            "redis": "redis@sha256:" + "b" * 64,
            "nats": "nats@sha256:" + "c" * 64,
            "minio": "minio/minio@sha256:" + "d" * 64,
            "keycloak": "quay.io/keycloak/keycloak@sha256:" + "e" * 64,
            "mediamtx": "bluenviron/mediamtx@sha256:" + "f" * 64,
            "backend": "ghcr.io/acme/backend:latest",
            "frontend": "ghcr.io/acme/frontend@sha256:" + "1" * 64,
            "supervisor": "ghcr.io/acme/backend@sha256:" + "2" * 64,
        },
    )

    with pytest.raises(ManifestPolicyError, match="immutable"):
        resolve_master_images(path, allow_dev_fallbacks=False)


def test_supervisor_can_reuse_backend_image_when_missing_in_dev(tmp_path: Path) -> None:
    path = _manifest(tmp_path, channel="dev", images={"backend": "vezor/backend:dev"})

    images = resolve_master_images(path, allow_dev_fallbacks=True)

    assert images["supervisor"] == "vezor/backend:dev"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_master_manifest.py -q
```

Expected: FAIL because `vezor_installer.master_manifest` does not exist.

- [ ] **Step 3: Implement manifest helper**

Create `installer/vezor_installer/master_manifest.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping


MASTER_IMAGE_FALLBACKS: dict[str, str] = {
    "postgres": "timescale/timescaledb:latest-pg16",
    "redis": "redis:7",
    "nats": "nats:2",
    "minio": "minio/minio:latest",
    "keycloak": "quay.io/keycloak/keycloak:latest",
    "mediamtx": "bluenviron/mediamtx:latest",
    "backend": "vezor/backend:portable-demo",
    "frontend": "vezor/frontend:portable-demo",
}
REQUIRED_MASTER_IMAGE_KEYS = tuple(MASTER_IMAGE_FALLBACKS) + ("supervisor",)
_DIGEST_RE = re.compile(r"@sha256:[0-9a-fA-F]{64}$")
_APPROVED_STABLE_TAG_RE = re.compile(r":[0-9]+\\.[0-9]+\\.[0-9]+(?:[-+][A-Za-z0-9_.-]+)?$")


class ManifestPolicyError(ValueError):
    pass


def load_manifest(path: Path) -> Mapping[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_master_images(
    path: Path | None,
    *,
    allow_dev_fallbacks: bool,
) -> dict[str, str]:
    if path is None:
        if not allow_dev_fallbacks:
            raise ManifestPolicyError("production master install requires a release manifest")
        images = dict(MASTER_IMAGE_FALLBACKS)
        images["supervisor"] = images["backend"]
        return images

    manifest = load_manifest(path)
    channel = str(manifest.get("release_channel") or "dev")
    raw_images = manifest.get("images") or {}
    if not isinstance(raw_images, Mapping):
        raise ManifestPolicyError("manifest images must be an object")

    resolved: dict[str, str] = {}
    for key in MASTER_IMAGE_FALLBACKS:
        reference = _image_reference(raw_images, key)
        if reference:
            resolved[key] = reference
        elif channel == "dev" and allow_dev_fallbacks:
            resolved[key] = MASTER_IMAGE_FALLBACKS[key]

    supervisor_reference = _image_reference(raw_images, "supervisor")
    if supervisor_reference:
        resolved["supervisor"] = supervisor_reference
    elif "backend" in resolved:
        resolved["supervisor"] = resolved["backend"]

    missing = [key for key in REQUIRED_MASTER_IMAGE_KEYS if key not in resolved]
    if missing:
        raise ManifestPolicyError(f"missing required image keys: {', '.join(missing)}")

    if channel == "stable":
        mutable = [
            key
            for key, reference in resolved.items()
            if not _is_immutable_or_approved_release(reference)
        ]
        if mutable:
            raise ManifestPolicyError(
                "stable manifest image references must be immutable or approved release tags: "
                + ", ".join(mutable)
            )

    return resolved


def _image_reference(raw_images: Mapping[object, object], key: str) -> str | None:
    payload = raw_images.get(key)
    if not isinstance(payload, Mapping):
        return None
    reference = payload.get("reference")
    return reference if isinstance(reference, str) and reference.strip() else None


def _is_immutable_or_approved_release(reference: str) -> bool:
    return bool(_DIGEST_RE.search(reference) or _APPROVED_STABLE_TAG_RE.search(reference))
```

- [ ] **Step 4: Run tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_master_manifest.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if requested**

```bash
git add installer/vezor_installer/master_manifest.py installer/tests/test_master_manifest.py
git commit -m "feat: add master manifest policy helper"
```

---

### Task 2: Preflight Diagnostics And Redaction Helper

**Files:**
- Create: `installer/tests/test_master_preflight.py`
- Create: `installer/vezor_installer/master_preflight.py`

- [ ] **Step 1: Write failing preflight tests**

Create `installer/tests/test_master_preflight.py`:

```python
from __future__ import annotations

from vezor_installer.master_preflight import (
    PortOwner,
    derive_public_origins,
    oidc_disable_pkce_for_public_url,
    redact_process_owner,
    redact_value,
)


def test_public_origin_derivation_preserves_hostname_and_sets_ports() -> None:
    origins = derive_public_origins("http://master.local:3000")

    assert origins.frontend_url == "http://master.local:3000"
    assert origins.api_base_url == "http://master.local:8000"
    assert origins.keycloak_url == "http://master.local:8080"
    assert origins.oidc_authority == "http://master.local:8080/realms/argus-dev"


def test_oidc_pkce_is_disabled_only_for_non_loopback_http() -> None:
    assert oidc_disable_pkce_for_public_url("http://192.0.2.10:3000") is True
    assert oidc_disable_pkce_for_public_url("http://localhost:3000") is False
    assert oidc_disable_pkce_for_public_url("https://master.example:3000") is False


def test_redaction_masks_secrets_tokens_rtsp_and_raw_args() -> None:
    raw = (
        "rtsp://"
        + "user"
        + ":"
        + "pass"
        + "@camera.local:8554/ch1?token="
        + "TEST_TOKEN"
    )
    bearer = "Bearer" + " " + "TEST_TOKEN"

    assert redact_value(raw) == "rtsp://***:***@camera.local:8554/ch1"
    assert redact_value(bearer) == "***"
    assert redact_value("vzboot" + "_TEST") == "***"
    assert redact_value("vzplat" + "_TEST") == "***"


def test_process_owner_redaction_excludes_raw_command_args() -> None:
    owner = PortOwner(pid=123, process_name="python", command="COMMAND_WITH_PRIVATE_ARGS")

    redacted = redact_process_owner(owner)

    assert redacted == "pid=123 process=python"
    assert "COMMAND_WITH_PRIVATE_ARGS" not in redacted
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_master_preflight.py -q
```

Expected: FAIL because `master_preflight.py` does not exist.

- [ ] **Step 3: Implement preflight helper**

Create `installer/vezor_installer/master_preflight.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True, slots=True)
class PublicOrigins:
    frontend_url: str
    api_base_url: str
    keycloak_url: str
    oidc_authority: str
    hostname: str


@dataclass(frozen=True, slots=True)
class PortOwner:
    pid: int
    process_name: str
    command: str | None = None


def derive_public_origins(public_url: str) -> PublicOrigins:
    parsed = urlsplit(public_url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid public URL: {public_url}")
    host = parsed.hostname
    host_for_netloc = f"[{host}]" if ":" in host and not host.startswith("[") else host
    frontend = urlunsplit((parsed.scheme, f"{host_for_netloc}:3000", "", "", ""))
    api = urlunsplit((parsed.scheme, f"{host_for_netloc}:8000", "", "", ""))
    keycloak = urlunsplit((parsed.scheme, f"{host_for_netloc}:8080", "", "", ""))
    return PublicOrigins(
        frontend_url=frontend,
        api_base_url=api,
        keycloak_url=keycloak,
        oidc_authority=f"{keycloak}/realms/argus-dev",
        hostname=host,
    )


def oidc_disable_pkce_for_public_url(public_url: str) -> bool:
    parsed = urlsplit(public_url)
    hostname = parsed.hostname or ""
    if parsed.scheme != "http":
        return False
    return hostname not in {"localhost", "127.0.0.1", "::1"} and not hostname.startswith("127.")


def redact_value(value: str) -> str:
    text = value.strip()
    if text.startswith("rtsp://"):
        parsed = urlsplit(text)
        host = parsed.hostname or "<host>"
        path = parsed.path or ""
        return f"rtsp://***:***@{host}:8554{path}"
    lowered = text.lower()
    if "bearer " in lowered or text.startswith(("vzboot_", "vzplat_", "vzcred_")):
        return "***"
    if any(marker in lowered for marker in ("token=", "password=", "secret=", "pairing_code=")):
        return "***"
    return text


def redact_process_owner(owner: PortOwner) -> str:
    return f"pid={owner.pid} process={owner.process_name}"
```

- [ ] **Step 4: Run tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_master_preflight.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if requested**

```bash
git add installer/vezor_installer/master_preflight.py installer/tests/test_master_preflight.py
git commit -m "feat: add master preflight redaction helper"
```

---

### Task 3: Post-Start Health Helper

**Files:**
- Create: `installer/tests/test_master_health.py`
- Create: `installer/vezor_installer/master_health.py`

- [ ] **Step 1: Write failing health tests**

Create `installer/tests/test_master_health.py`:

```python
from __future__ import annotations

import pytest

from vezor_installer.master_health import HealthCheckResult, wait_for_master_health


def test_wait_for_master_health_reports_pass_for_all_checks() -> None:
    calls: list[str] = []

    def probe(url: str, timeout: float) -> bool:
        calls.append(url)
        return True

    result = wait_for_master_health(
        frontend_url="http://master:3000",
        api_base_url="http://master:8000",
        keycloak_url="http://master:8080",
        supervisor_probe=lambda: True,
        http_probe=probe,
        attempts=1,
        sleep_seconds=0,
    )

    assert result == HealthCheckResult(ok=True, failed_check=None)
    assert "http://master:8000/healthz" in calls
    assert "http://master:3000" in calls
    assert "http://master:8080" in calls


def test_wait_for_master_health_reports_failed_dependency_without_logs() -> None:
    def probe(url: str, timeout: float) -> bool:
        return "8000" not in url

    result = wait_for_master_health(
        frontend_url="http://master:3000",
        api_base_url="http://master:8000",
        keycloak_url="http://master:8080",
        supervisor_probe=lambda: True,
        http_probe=probe,
        attempts=1,
        sleep_seconds=0,
    )

    assert result == HealthCheckResult(ok=False, failed_check="backend")
    assert "secret" not in repr(result).lower()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_master_health.py -q
```

Expected: FAIL because `master_health.py` does not exist.

- [ ] **Step 3: Implement health helper**

Create `installer/vezor_installer/master_health.py`:

```python
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    ok: bool
    failed_check: str | None


HttpProbe = Callable[[str, float], bool]
SupervisorProbe = Callable[[], bool]


def default_http_probe(url: str, timeout: float) -> bool:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= int(response.status) < 500
    except OSError:
        return False


def wait_for_master_health(
    *,
    frontend_url: str,
    api_base_url: str,
    keycloak_url: str,
    supervisor_probe: SupervisorProbe,
    http_probe: HttpProbe = default_http_probe,
    attempts: int = 60,
    sleep_seconds: float = 2.0,
    timeout_seconds: float = 2.0,
) -> HealthCheckResult:
    checks: tuple[tuple[str, Callable[[], bool]], ...] = (
        ("backend", lambda: http_probe(f"{api_base_url.rstrip('/')}/healthz", timeout_seconds)),
        ("frontend", lambda: http_probe(frontend_url, timeout_seconds)),
        ("keycloak", lambda: http_probe(keycloak_url, timeout_seconds)),
        ("supervisor", supervisor_probe),
    )
    for _ in range(attempts):
        for name, check in checks:
            if not check():
                failed = name
                break
        else:
            return HealthCheckResult(ok=True, failed_check=None)
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return HealthCheckResult(ok=False, failed_check=failed)
```

- [ ] **Step 4: Run tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_master_health.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if requested**

```bash
git add installer/vezor_installer/master_health.py installer/tests/test_master_health.py
git commit -m "feat: add master health wait helper"
```

---

### Task 4: Linux Master Mode And Reconfigure Flow

**Files:**
- Modify: `installer/tests/test_linux_master_artifacts.py`
- Modify: `installer/linux/install-master.sh`
- Create: `installer/lib/master_install_common.sh`

- [ ] **Step 1: Add failing Linux artifact tests**

Append to `installer/tests/test_linux_master_artifacts.py`:

```python
def test_linux_master_installer_accepts_modes_and_cpu_tuning_flags() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "--mode MODE" in script
    assert "install|preflight|reconfigure" in script
    assert "--central-worker-cpu-fps-cap" in script
    assert "--central-worker-intra-op-threads" in script
    assert "--central-worker-inter-op-threads" in script
    assert "MODE=\"install\"" in script


def test_linux_master_reconfigure_stops_vezor_before_port_checks() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "stop_existing_master" in script
    assert 'if [[ "$MODE" == "reconfigure" ]]' in script
    assert script.index('if [[ "$MODE" == "reconfigure" ]]') < script.index("for port in 3000")
    assert "systemctl stop vezor-master.service" in script
    assert "docker prune" not in script


def test_linux_master_preflight_exits_before_writes() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "run_master_preflight" in script
    assert 'if [[ "$MODE" == "preflight" ]]' in script
    assert script.index('if [[ "$MODE" == "preflight" ]]') < script.index("run install -d -m 0755")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_linux_master_artifacts.py -q
```

Expected: FAIL because mode and preflight flow are missing.

- [ ] **Step 3: Add shared shell helper**

Create `installer/lib/master_install_common.sh`:

```bash
validate_master_mode() {
  case "$MODE" in
    install|preflight|reconfigure)
      ;;
    *)
      echo "Unsupported --mode: $MODE" >&2
      exit 2
      ;;
  esac
}

run_master_preflight() {
  python3 -m vezor_installer.master_preflight "$@"
}

run_master_health_gate() {
  python3 -m vezor_installer.master_health "$@"
}
```

- [ ] **Step 4: Wire Linux mode parsing**

In `installer/linux/install-master.sh`, add variable:

```bash
MODE="install"
CENTRAL_WORKER_CPU_FPS_CAP=""
CENTRAL_WORKER_INTRA_OP_THREADS=""
CENTRAL_WORKER_INTER_OP_THREADS=""
```

Update usage:

```text
  --mode MODE           install, preflight, or reconfigure. Default: install.
  --central-worker-cpu-fps-cap N
                         Optional CPU fallback FPS cap for central workers.
  --central-worker-intra-op-threads N
                         Optional ONNX Runtime intra-op threads for central workers.
  --central-worker-inter-op-threads N
                         Optional ONNX Runtime inter-op threads for central workers.
```

Add parsing:

```bash
    --mode)
      MODE="${2:?--mode requires a value}"
      shift 2
      ;;
    --central-worker-cpu-fps-cap)
      CENTRAL_WORKER_CPU_FPS_CAP="${2:?--central-worker-cpu-fps-cap requires a value}"
      shift 2
      ;;
    --central-worker-intra-op-threads)
      CENTRAL_WORKER_INTRA_OP_THREADS="${2:?--central-worker-intra-op-threads requires a value}"
      shift 2
      ;;
    --central-worker-inter-op-threads)
      CENTRAL_WORKER_INTER_OP_THREADS="${2:?--central-worker-inter-op-threads requires a value}"
      shift 2
      ;;
```

Source helper after parsing:

```bash
source /opt/vezor/current/installer/lib/master_install_common.sh
validate_master_mode
```

- [ ] **Step 5: Add Linux reconfigure and preflight gates**

Add:

```bash
stop_existing_master() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] stop existing Vezor master service"
    return 0
  fi
  systemctl stop vezor-master.service >/dev/null 2>&1 || true
  if [[ -x /opt/vezor/current/bin/vezor-master && -f "$CONFIG_DIR/master.json" ]]; then
    /opt/vezor/current/bin/vezor-master down --config "$CONFIG_DIR/master.json" >/dev/null 2>&1 || true
  fi
}

if [[ "$MODE" == "reconfigure" ]]; then
  stop_existing_master
fi

if [[ "$MODE" == "preflight" ]]; then
  run_master_preflight --platform linux --public-url "$PUBLIC_URL" --manifest "$MANIFEST"
  exit 0
fi
```

Place the `reconfigure` block before port checks. Place the `preflight` block before any writes.

- [ ] **Step 6: Write CPU tuning env values**

When writing `MASTER_ENV`, add:

```bash
VEZOR_CPU_FALLBACK_PROCESSING_FPS_CAP=$CENTRAL_WORKER_CPU_FPS_CAP
VEZOR_WORKER_INFERENCE_SESSION_INTRA_OP_THREADS=$CENTRAL_WORKER_INTRA_OP_THREADS
VEZOR_WORKER_INFERENCE_SESSION_INTER_OP_THREADS=$CENTRAL_WORKER_INTER_OP_THREADS
```

- [ ] **Step 7: Run Linux artifact tests and syntax**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_linux_master_artifacts.py -q
bash -n installer/linux/install-master.sh installer/lib/master_install_common.sh
```

Expected: PASS.

- [ ] **Step 8: Commit checkpoint if requested**

```bash
git add installer/linux/install-master.sh installer/lib/master_install_common.sh installer/tests/test_linux_master_artifacts.py
git commit -m "feat: add linux master installer modes"
```

---

### Task 5: macOS Master Mode Alignment

**Files:**
- Modify: `installer/tests/test_macos_master_artifacts.py`
- Modify: `installer/macos/install-master.sh`

- [ ] **Step 1: Add failing macOS artifact tests**

Append to `installer/tests/test_macos_master_artifacts.py`:

```python
def test_macos_master_installer_accepts_modes_and_cpu_tuning_flags() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "--mode MODE" in script
    assert "install|preflight|reconfigure" in script
    assert "--central-worker-cpu-fps-cap" in script
    assert "--central-worker-intra-op-threads" in script
    assert "--central-worker-inter-op-threads" in script
    assert "MODE=\"install\"" in script


def test_macos_master_preflight_exits_before_writes() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "run_master_preflight" in script
    assert 'if [[ "$MODE" == "preflight" ]]' in script
    assert script.index('if [[ "$MODE" == "preflight" ]]') < script.index("run install -d -m 0755")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_macos_master_artifacts.py -q
```

Expected: FAIL because mode and CPU flags are missing.

- [ ] **Step 3: Wire mode parsing and helper**

Mirror the Linux parsing from Task 4 in `installer/macos/install-master.sh`. Add:

```bash
MODE="install"
CENTRAL_WORKER_CPU_FPS_CAP=""
CENTRAL_WORKER_INTRA_OP_THREADS=""
CENTRAL_WORKER_INTER_OP_THREADS=""
```

Add the same usage and parsing blocks. Source the shared helper after parsing:

```bash
source /opt/vezor/current/installer/lib/master_install_common.sh
validate_master_mode
```

- [ ] **Step 4: Add macOS preflight and reconfigure mode behavior**

Before writes:

```bash
if [[ "$MODE" == "preflight" ]]; then
  run_master_preflight --platform macos --public-url "$PUBLIC_URL" --manifest "$MANIFEST"
  exit 0
fi

if [[ "$MODE" == "reconfigure" ]]; then
  stop_existing_master
fi
```

Keep existing `stop_existing_master` bounded to the Vezor launchd job and Vezor master containers.

- [ ] **Step 5: Add CPU env values**

Add the same `VEZOR_CPU_FALLBACK_PROCESSING_FPS_CAP` and thread env values into macOS `MASTER_ENV`.

- [ ] **Step 6: Run macOS artifact tests and syntax**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_macos_master_artifacts.py -q
bash -n installer/macos/install-master.sh
```

Expected: PASS.

- [ ] **Step 7: Commit checkpoint if requested**

```bash
git add installer/macos/install-master.sh installer/tests/test_macos_master_artifacts.py
git commit -m "feat: align macos master installer modes"
```

---

### Task 6: Wire Manifest Helper Into Installers

**Files:**
- Modify: `installer/linux/install-master.sh`
- Modify: `installer/macos/install-master.sh`
- Modify: `installer/tests/test_linux_master_artifacts.py`
- Modify: `installer/tests/test_macos_master_artifacts.py`

- [ ] **Step 1: Add failing helper usage tests**

Add to both Linux and macOS artifact tests:

```python
def test_master_installer_uses_master_manifest_helper() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "vezor_installer.master_manifest" in script
    assert "resolve_master_images" in script
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_linux_master_artifacts.py installer/tests/test_macos_master_artifacts.py -q
```

Expected: FAIL because installers still inline image resolution.

- [ ] **Step 3: Add shell bridge function**

In both installers, replace or supplement repeated `manifest_image_ref` calls with:

```bash
resolve_master_images() {
  local manifest_arg=()
  if [[ -n "$MANIFEST" ]]; then
    manifest_arg=(--manifest "$MANIFEST")
  fi
  python3 -m vezor_installer.master_manifest "${manifest_arg[@]}" --shell
}
```

Add a CLI block to `master_manifest.py`:

```python
def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--shell", action="store_true")
    args = parser.parse_args(argv)
    images = resolve_master_images(args.manifest, allow_dev_fallbacks=True)
    if args.shell:
        for key, value in images.items():
            env_name = f"{key.upper().replace('-', '_')}_IMAGE"
            print(f"{env_name}={value!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

In shell, call:

```bash
eval "$(resolve_master_images)"
```

Keep variable names compatible with existing Compose envs:

```bash
POSTGRES_IMAGE="${POSTGRES_IMAGE:?}"
REDIS_IMAGE="${REDIS_IMAGE:?}"
NATS_IMAGE="${NATS_IMAGE:?}"
MINIO_IMAGE="${MINIO_IMAGE:?}"
KEYCLOAK_IMAGE="${KEYCLOAK_IMAGE:?}"
MEDIAMTX_IMAGE="${MEDIAMTX_IMAGE:?}"
BACKEND_IMAGE="${BACKEND_IMAGE:?}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:?}"
SUPERVISOR_IMAGE="${SUPERVISOR_IMAGE:?}"
```

- [ ] **Step 4: Run tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_master_manifest.py installer/tests/test_linux_master_artifacts.py installer/tests/test_macos_master_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if requested**

```bash
git add installer/vezor_installer/master_manifest.py installer/linux/install-master.sh installer/macos/install-master.sh installer/tests/test_linux_master_artifacts.py installer/tests/test_macos_master_artifacts.py
git commit -m "feat: use shared master manifest helper"
```

---

### Task 7: Post-Start Health Gate Wiring

**Files:**
- Modify: `installer/linux/install-master.sh`
- Modify: `installer/macos/install-master.sh`
- Modify: `installer/tests/test_linux_master_artifacts.py`
- Modify: `installer/tests/test_macos_master_artifacts.py`

- [ ] **Step 1: Add failing health gate usage tests**

Add to both artifact test files:

```python
def test_master_installer_runs_post_start_health_gate() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "run_master_health_gate" in script
    assert "VEZOR_PUBLIC_FRONTEND_URL" in script
    assert "VEZOR_PUBLIC_API_BASE_URL" in script
    assert "VEZOR_PUBLIC_KEYCLOAK_URL" in script
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_linux_master_artifacts.py installer/tests/test_macos_master_artifacts.py -q
```

Expected: FAIL because health gate is not wired.

- [ ] **Step 3: Add CLI to health helper**

Add to `installer/vezor_installer/master_health.py`:

```python
def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--keycloak-url", required=True)
    args = parser.parse_args(argv)
    result = wait_for_master_health(
        frontend_url=args.frontend_url,
        api_base_url=args.api_base_url,
        keycloak_url=args.keycloak_url,
        supervisor_probe=lambda: True,
    )
    if result.ok:
        print("PASS master health gate")
        return 0
    print(f"FAIL master health gate: {result.failed_check}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Call health gate after start**

In Linux after `systemctl start vezor-master.service`, add:

```bash
run_master_health_gate \
  --frontend-url "$PUBLIC_URL" \
  --api-base-url "$PUBLIC_API_BASE_URL" \
  --keycloak-url "$PUBLIC_KEYCLOAK_URL"
```

In macOS after `launchctl enable system/com.vezor.master`, add the same call.

- [ ] **Step 5: Run tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_master_health.py installer/tests/test_linux_master_artifacts.py installer/tests/test_macos_master_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit checkpoint if requested**

```bash
git add installer/vezor_installer/master_health.py installer/linux/install-master.sh installer/macos/install-master.sh installer/tests/test_linux_master_artifacts.py installer/tests/test_macos_master_artifacts.py
git commit -m "feat: add master post start health gate"
```

---

### Task 8: Documentation And Final Verification

**Files:**
- Modify: `installer/README.md`
- Modify: `docs/full-installation-guide.md`
- Modify: `docs/superpowers/plans/2026-06-13-master-installer-process-optimizations-implementation-plan.md`

- [ ] **Step 1: Add docs assertions**

Append to `installer/tests/test_linux_master_artifacts.py`:

```python
INSTALLER_README = REPO_ROOT / "installer" / "README.md"
FULL_INSTALL_GUIDE = REPO_ROOT / "docs" / "full-installation-guide.md"


def test_master_installer_docs_describe_preflight_reconfigure_and_no_gpu_claims() -> None:
    docs = _read(INSTALLER_README) + "\n" + _read(FULL_INSTALL_GUIDE)

    assert "--mode preflight" in docs
    assert "--mode reconfigure" in docs
    assert "central worker CPU" in docs
    assert "does not configure central Dockerized GPU" in docs
    assert "Apple M-series" in docs
    assert "DeepStream acceleration" in docs
```

- [ ] **Step 2: Run docs test to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_linux_master_artifacts.py::test_master_installer_docs_describe_preflight_reconfigure_and_no_gpu_claims -q
```

Expected: FAIL because docs do not mention the new flow.

- [ ] **Step 3: Update installer README**

Add to `installer/README.md`:

````markdown
## Master Installer Modes

Run preflight before changing the host:

```bash
sudo ./bin/vezor install master --mode preflight --public-url http://MASTER_IP:3000
```

Use reconfigure to rerun the installer against an existing Vezor master
without purging data or regenerating secrets:

```bash
sudo ./bin/vezor install master --mode reconfigure --public-url http://MASTER_IP:3000
```

Central worker CPU tuning can be set during install or reconfigure:

```bash
sudo ./bin/vezor install master \
  --central-worker-cpu-fps-cap 8 \
  --central-worker-intra-op-threads 2 \
  --central-worker-inter-op-threads 1
```

These settings are CPU-only controls. The master installer does not
configure central Dockerized GPU, Apple M-series, CUDA, OpenVINO,
TensorRT, or DeepStream acceleration.
````

- [ ] **Step 4: Update full installation guide**

Add under the master install section:

````markdown
Run preflight first on production pilots:

```bash
sudo ./bin/vezor install master --mode preflight --public-url http://MASTER_HOST_OR_IP:3000
```

For reruns against an already-installed master, use reconfigure:

```bash
sudo ./bin/vezor install master --mode reconfigure --public-url http://MASTER_HOST_OR_IP:3000
```

The master installer supports central worker CPU tuning through
`--central-worker-cpu-fps-cap`, `--central-worker-intra-op-threads`,
and `--central-worker-inter-op-threads`. These flags do not configure
central GPU acceleration.
````

- [ ] **Step 5: Run final targeted tests**

Run:

```bash
./installer/.venv/bin/pytest \
  installer/tests/test_master_manifest.py \
  installer/tests/test_master_preflight.py \
  installer/tests/test_master_health.py \
  installer/tests/test_linux_master_artifacts.py \
  installer/tests/test_macos_master_artifacts.py \
  -q
bash -n installer/linux/install-master.sh installer/macos/install-master.sh installer/lib/master_install_common.sh
git diff --check
```

Expected: PASS.

- [ ] **Step 6: Safety scan**

Run:

```bash
rg -n "Bearer |ARGUS_API_BEARER_TOKEN|vzboot_[A-Za-z0-9]|vzplat_[A-Za-z0-9]|rtsp://[^*].*:[^*].*@|sudo password|central Dockerized GPU|Apple M-series acceleration|DeepStream acceleration" \
  installer docs/full-installation-guide.md
```

Expected: no matches except intentional non-claim text for central acceleration.

- [ ] **Step 7: Commit checkpoint if requested**

```bash
git add installer/README.md docs/full-installation-guide.md docs/superpowers/plans/2026-06-13-master-installer-process-optimizations-implementation-plan.md
git commit -m "docs: plan master installer process optimizations"
```
