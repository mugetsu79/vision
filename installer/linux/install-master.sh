#!/usr/bin/env bash
set -euo pipefail

VERSION=""
MANIFEST=""
PUBLIC_URL="http://localhost:3000"
DATA_DIR="/var/lib/vezor"
CONFIG_DIR="/etc/vezor"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Install the Vezor Linux master appliance.

Options:
  --dry-run             Print actions without changing the host.
  --version VERSION     Release version to install.
  --manifest PATH       Release manifest path.
  --public-url URL      Public frontend URL for first-run links.
  --data-dir PATH       Persistent data directory. Default: /var/lib/vezor.
  --config-dir PATH     Configuration directory. Default: /etc/vezor.
  -h, --help            Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --version)
      VERSION="${2:?--version requires a value}"
      shift 2
      ;;
    --manifest)
      MANIFEST="${2:?--manifest requires a value}"
      shift 2
      ;;
    --public-url)
      PUBLIC_URL="${2:?--public-url requires a value}"
      shift 2
      ;;
    --data-dir)
      DATA_DIR="${2:?--data-dir requires a value}"
      shift 2
      ;;
    --config-dir)
      CONFIG_DIR="${2:?--config-dir requires a value}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] %q' "$1"
    shift
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
    return 0
  fi
  "$@"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import secrets

print(secrets.token_urlsafe(32))
PY
    return 0
  fi
  echo "openssl or python3 is required to generate appliance secrets." >&2
  exit 1
}

write_secret_if_missing() {
  local path="$1"
  local value="${2:-}"

  if [[ -f "$path" ]]; then
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] write secret $path"
    return 0
  fi

  if [[ -z "$value" ]]; then
    value="$(random_secret)"
  fi
  write_secret "$path" "$value"
}

write_secret() {
  local path="$1"
  local value="$2"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] write secret $path"
    return 0
  fi

  local old_umask
  old_umask="$(umask)"
  umask 077
  printf '%s\n' "$value" > "$path"
  umask "$old_umask"
}

write_backend_db_url_secret() {
  local postgres_password

  if [[ "$DRY_RUN" -eq 1 ]]; then
    postgres_password="dry-run-postgres-password"
  else
    postgres_password="$(tr -d '\r\n' < "$CONFIG_DIR/secrets/postgres_password")"
  fi

  write_secret \
    "$CONFIG_DIR/secrets/backend_db_url" \
    "postgresql+asyncpg://${VEZOR_POSTGRES_USER:-argus}:${postgres_password}@postgres:5432/${VEZOR_POSTGRES_DB:-argus}"
}

manifest_image_ref() {
  local image_key="$1"
  local fallback="$2"

  if [[ -z "$MANIFEST" ]]; then
    printf '%s\n' "$fallback"
    return 0
  fi

  python3 - "$MANIFEST" "$image_key" "$fallback" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
image_key = sys.argv[2]
fallback = sys.argv[3]
image = manifest.get("images", {}).get(image_key, {})
reference = image.get("reference") if isinstance(image, dict) else None
print(reference if isinstance(reference, str) and reference else fallback)
PY
}

manifest_release_channel() {
  if [[ -z "$MANIFEST" ]]; then
    printf 'dev\n'
    return 0
  fi

  python3 - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
release_channel = manifest.get("release_channel")
print(release_channel if isinstance(release_channel, str) else "")
PY
}

read_existing_supervisor_id() {
  local path="$1"

  if [[ ! -f "$path" ]] || ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi

  python3 - "$path" <<'PY' 2>/dev/null || true
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
supervisor_id = payload.get("supervisor_id")
if isinstance(supervisor_id, str) and supervisor_id:
    print(supervisor_id)
PY
}

build_local_master_images() {
  if [[ "$(manifest_release_channel)" != "dev" ]]; then
    return 0
  fi

  echo "Building local Vezor master images for dev manifest..."
  run $CONTAINER_ENGINE build -f /opt/vezor/current/backend/Dockerfile -t "$BACKEND_IMAGE" /opt/vezor/current/backend
  if [[ "$SUPERVISOR_IMAGE" != "$BACKEND_IMAGE" ]]; then
    run $CONTAINER_ENGINE tag "$BACKEND_IMAGE" "$SUPERVISOR_IMAGE"
  fi
  run $CONTAINER_ENGINE build -f /opt/vezor/current/frontend/Dockerfile -t "$FRONTEND_IMAGE" /opt/vezor/current/frontend
}

require_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This installer target is Linux master. Detected: $(uname -s)" >&2
    exit 1
  fi
}

check_port_available() {
  local port="$1"
  if command -v ss >/dev/null 2>&1 && ss -ltn "( sport = :$port )" | grep -q ":$port"; then
    echo "Port $port is already in use." >&2
    exit 1
  fi
}

require_linux
require_command systemctl

if command -v docker >/dev/null 2>&1; then
  CONTAINER_ENGINE="docker"
elif command -v podman >/dev/null 2>&1; then
  CONTAINER_ENGINE="podman"
else
  echo "Docker or Podman is required for the Vezor master appliance." >&2
  exit 1
fi

for port in 3000 8000 8080 8554 8888 8889 9000; do
  check_port_available "$port"
done

if [[ -n "$MANIFEST" && ! -f "$MANIFEST" ]]; then
  echo "Manifest not found: $MANIFEST" >&2
  exit 1
fi

POSTGRES_IMAGE="$(manifest_image_ref postgres timescale/timescaledb:latest-pg16)"
REDIS_IMAGE="$(manifest_image_ref redis redis:7)"
NATS_IMAGE="$(manifest_image_ref nats nats:2)"
MINIO_IMAGE="$(manifest_image_ref minio minio/minio:latest)"
KEYCLOAK_IMAGE="$(manifest_image_ref keycloak quay.io/keycloak/keycloak:latest)"
MEDIAMTX_IMAGE="$(manifest_image_ref mediamtx bluenviron/mediamtx:latest)"
BACKEND_IMAGE="$(manifest_image_ref backend vezor/backend:portable-demo)"
FRONTEND_IMAGE="$(manifest_image_ref frontend vezor/frontend:portable-demo)"
SUPERVISOR_IMAGE="$(manifest_image_ref supervisor "$BACKEND_IMAGE")"

run install -d -m 0755 \
  "$CONFIG_DIR" \
  "$CONFIG_DIR/secrets" \
  "$CONFIG_DIR/nats" \
  "$CONFIG_DIR/mediamtx" \
  "$DATA_DIR" \
  /var/log/vezor \
  /run/vezor
run install -d -m 0755 \
  "$DATA_DIR/postgres" \
  "$DATA_DIR/redis" \
  "$DATA_DIR/nats" \
  "$DATA_DIR/minio" \
  "$DATA_DIR/mediamtx" \
  "$DATA_DIR/models" \
  "$DATA_DIR/credentials" \
  "$DATA_DIR/evidence" \
  "$DATA_DIR/bootstrap"

write_secret_if_missing "$CONFIG_DIR/secrets/postgres_password"
write_backend_db_url_secret
write_secret_if_missing "$CONFIG_DIR/secrets/minio_root_user" "vezor-minio"
write_secret_if_missing "$CONFIG_DIR/secrets/minio_root_password"
write_secret_if_missing "$CONFIG_DIR/secrets/keycloak_admin_username" "admin"
write_secret_if_missing "$CONFIG_DIR/secrets/keycloak_admin_password"

run install -m 0644 /opt/vezor/current/infra/nats/nats.conf "$CONFIG_DIR/nats/nats.conf"
run install -m 0644 /opt/vezor/current/infra/mediamtx/mediamtx.yml "$CONFIG_DIR/mediamtx/mediamtx.yml"

MASTER_ENV="$CONFIG_DIR/master.env"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $MASTER_ENV"
else
  cat > "$MASTER_ENV" <<ENV
VEZOR_POSTGRES_IMAGE=$POSTGRES_IMAGE
VEZOR_REDIS_IMAGE=$REDIS_IMAGE
VEZOR_NATS_IMAGE=$NATS_IMAGE
VEZOR_MINIO_IMAGE=$MINIO_IMAGE
VEZOR_KEYCLOAK_IMAGE=$KEYCLOAK_IMAGE
VEZOR_MEDIAMTX_IMAGE=$MEDIAMTX_IMAGE
VEZOR_BACKEND_IMAGE=$BACKEND_IMAGE
VEZOR_FRONTEND_IMAGE=$FRONTEND_IMAGE
VEZOR_SUPERVISOR_IMAGE=$SUPERVISOR_IMAGE
VEZOR_CREDENTIALS_HOST_DIR=$DATA_DIR/credentials
VEZOR_PUBLIC_FRONTEND_URL=$PUBLIC_URL
VEZOR_PUBLIC_API_BASE_URL=${PUBLIC_URL%:*}:8000
VEZOR_PUBLIC_KEYCLOAK_URL=${PUBLIC_URL%:*}:8080
VEZOR_PUBLIC_OIDC_AUTHORITY=${PUBLIC_URL%:*}:8080/realms/argus-dev
VEZOR_OIDC_CLIENT_ID=argus-frontend
ENV
  chmod 0644 "$MASTER_ENV"
fi

MASTER_CONFIG="$CONFIG_DIR/master.json"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $MASTER_CONFIG"
else
  old_umask="$(umask)"
  umask 027
  cat > "$MASTER_CONFIG" <<JSON
{
  "role": "master",
  "version": "${VERSION:-unversioned}",
  "public_url": "$PUBLIC_URL",
  "data_dir": "$DATA_DIR",
  "config_dir": "$CONFIG_DIR",
  "container_engine": "$CONTAINER_ENGINE",
  "compose_file": "/opt/vezor/current/infra/install/compose/compose.master.yml"
}
JSON
  umask "$old_umask"
fi

SUPERVISOR_CONFIG="$CONFIG_DIR/supervisor.json"
CENTRAL_SUPERVISOR_ID="$(read_existing_supervisor_id "$SUPERVISOR_CONFIG")"
CENTRAL_SUPERVISOR_ID="${CENTRAL_SUPERVISOR_ID:-central-master-1}"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $SUPERVISOR_CONFIG"
else
  old_umask="$(umask)"
  umask 027
  cat > "$SUPERVISOR_CONFIG" <<JSON
{
  "supervisor_id": "$CENTRAL_SUPERVISOR_ID",
  "role": "central",
  "api_base_url": "http://backend:8000",
  "credential_store_path": "/run/vezor/credentials/supervisor.credential",
  "service_manager": "compose",
  "version": "${VERSION:-unversioned}"
}
JSON
  umask "$old_umask"
fi

build_local_master_images

run install -m 0644 \
  /opt/vezor/current/infra/install/systemd/vezor-master.service \
  /etc/systemd/system/vezor-master.service

run systemctl daemon-reload
run systemctl enable vezor-master.service
run systemctl start vezor-master.service

echo "Vezor Linux master install complete."
echo "Open the first-run UI: $PUBLIC_URL/first-run"
