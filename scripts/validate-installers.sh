#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> installer pytest"
python3 -m uv run --project installer pytest installer/tests -q

echo "==> installer shell syntax"
bash -n installer/linux/install-master.sh
bash -n installer/linux/install-edge.sh
bash -n installer/linux/uninstall.sh
bash -n installer/macos/install-master.sh
bash -n installer/macos/uninstall.sh
bash -n scripts/jetson-preflight.sh
bash -n bin/vezor-appliance
bash -n bin/vezor-master
bash -n bin/vezor-edge
bash -n bin/vezorctl

echo "==> manifest validation"
python3 -m uv run --project installer python - <<'PY'
import json
from pathlib import Path

from vezor_installer.manifest import Manifest

path = Path("installer/manifests/dev-example.json")
Manifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
print(f"validated {path}")
PY

echo "==> product secret scan"
python3 -m uv run --project installer python - <<'PY'
from pathlib import Path

product_artifacts = [
    Path("infra/install/compose/compose.master.yml"),
    Path("infra/install/compose/compose.supervisor.yml"),
    Path("infra/install/systemd/vezor-master.service"),
    Path("infra/install/systemd/vezor-edge.service"),
    Path("infra/install/launchd/com.vezor.master.plist"),
    Path("bin/vezor-appliance"),
    Path("bin/vezor-master"),
    Path("bin/vezor-edge"),
    Path("bin/vezorctl"),
    Path("installer/linux/install-master.sh"),
    Path("installer/linux/install-edge.sh"),
    Path("installer/linux/uninstall.sh"),
    Path("installer/macos/install-master.sh"),
    Path("installer/macos/uninstall.sh"),
]
forbidden = (
    "ARGUS_API_BEARER_TOKEN",
    "Bearer ",
    "admin-dev",
    "argus-admin-pass",
    "make dev-up",
    "docker compose up",
)
failures: list[str] = []
for path in product_artifacts:
    text = path.read_text(encoding="utf-8")
    for pattern in forbidden:
        if pattern in text:
            failures.append(f"{path}: contains {pattern!r}")

guide = Path("docs/product-installer-and-first-run-guide.md")
guide_dev_patterns = (
    "make dev-up",
    "ARGUS_API_BEARER_TOKEN",
    "docker compose -f infra/docker-compose",
    "docker compose up",
)
for lineno, line in enumerate(guide.read_text(encoding="utf-8").splitlines(), start=1):
    if any(pattern in line for pattern in guide_dev_patterns):
        if "Development fallback" not in line and "Break-glass" not in line:
            failures.append(f"{guide}:{lineno}: dev/break-glass command is not labelled")

if failures:
    print("\n".join(failures))
    raise SystemExit(1)

print("product service files and installer docs passed secret scan")
PY

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  tmp_master_env="$(mktemp)"
  trap 'rm -f "$tmp_master_env"' EXIT

  echo "==> compose render: master"
  env \
    VEZOR_MASTER_ENV_FILE="$tmp_master_env" \
    VEZOR_POSTGRES_IMAGE=postgres:16 \
    VEZOR_REDIS_IMAGE=redis:7 \
    VEZOR_NATS_IMAGE=nats:2 \
    VEZOR_MINIO_IMAGE=minio/minio:latest \
    VEZOR_KEYCLOAK_IMAGE=quay.io/keycloak/keycloak:latest \
    VEZOR_MEDIAMTX_IMAGE=bluenviron/mediamtx:latest \
    VEZOR_BACKEND_IMAGE=ghcr.io/vezor/backend:dev \
    VEZOR_FRONTEND_IMAGE=ghcr.io/vezor/frontend:dev \
    VEZOR_SUPERVISOR_IMAGE=ghcr.io/vezor/supervisor:dev \
    docker compose -f infra/install/compose/compose.master.yml config >/dev/null

  echo "==> compose render: edge"
  env \
    VEZOR_MEDIAMTX_IMAGE=bluenviron/mediamtx:latest \
    VEZOR_SUPERVISOR_IMAGE=ghcr.io/vezor/supervisor:dev \
    docker compose -f infra/install/compose/compose.supervisor.yml config >/dev/null
else
  echo "docker unavailable; skipping installer Compose render"
fi

echo "installer validation passed"
