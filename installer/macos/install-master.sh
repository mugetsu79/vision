#!/usr/bin/env bash
set -euo pipefail

VERSION=""
MANIFEST=""
PUBLIC_URL="http://localhost:3000"
DATA_DIR="/var/lib/vezor"
CONFIG_DIR="/etc/vezor"
DEFAULT_MASTER_CONFIG="/etc/vezor/master.json"
DRY_RUN=0
PLIST_PATH="/Library/LaunchDaemons/com.vezor.master.plist"

export PATH="/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"

usage() {
  cat <<'USAGE'
Install the Vezor macOS master appliance.

Options:
  --dry-run             Print actions without changing the host.
  --version VERSION     Release version to install.
  --manifest PATH       Release manifest path.
  --public-url URL      Public frontend URL for first-run links.
  --data-dir PATH       Persistent data directory. Default: /var/lib/vezor.
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

prepare_secret_for_docker_desktop() {
  local path="$1"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] set Docker Desktop-readable secret permissions $path"
    return 0
  fi

  chgrp staff "$path"
  chmod 0640 "$path"
}

prepare_config_for_docker_desktop() {
  local path="$1"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] set Docker Desktop-readable config permissions $path"
    return 0
  fi

  chgrp staff "$path"
  chmod 0640 "$path"
}

docker_desktop_host_user() {
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER:-}" != "root" ]]; then
    printf '%s\n' "$SUDO_USER"
    return 0
  fi

  stat -f "%Su" /dev/console
}

docker_desktop_host_group() {
  local owner="$1"

  id -gn "$owner" 2>/dev/null || printf 'staff\n'
}

prepare_data_dir_for_docker_desktop() {
  local path="$1"
  local owner
  local group

  owner="$(docker_desktop_host_user)"
  if [[ -z "$owner" || "$owner" == "root" ]]; then
    echo "Unable to determine the macOS console user for Docker Desktop data directory ownership." >&2
    exit 1
  fi
  group="$(docker_desktop_host_group "$owner")"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] set Docker Desktop-writable data permissions $path for $owner:$group"
    return 0
  fi

  chown -R "$owner:$group" "$path"
  chmod -R u+rwX "$path"
}

write_secret_if_missing() {
  local path="$1"
  local value="${2:-}"

  if [[ -f "$path" ]]; then
    prepare_secret_for_docker_desktop "$path"
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
  prepare_secret_for_docker_desktop "$path"
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

build_local_master_images() {
  if [[ "$(manifest_release_channel)" != "dev" ]]; then
    return 0
  fi

  require_command docker
  echo "Building local Vezor master images for dev manifest..."
  run docker build -f /opt/vezor/current/backend/Dockerfile -t "$BACKEND_IMAGE" /opt/vezor/current/backend
  if [[ "$SUPERVISOR_IMAGE" != "$BACKEND_IMAGE" ]]; then
    run docker tag "$BACKEND_IMAGE" "$SUPERVISOR_IMAGE"
  fi
  run docker build -f /opt/vezor/current/frontend/Dockerfile -t "$FRONTEND_IMAGE" /opt/vezor/current/frontend
}

start_local_master_containers() {
  echo "Starting local Vezor master containers..."
  run /opt/vezor/current/bin/vezor-master up --config "$MASTER_CONFIG"
}

stop_existing_master() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] stop existing com.vezor.master launchd job"
    echo "[dry-run] stop existing Vezor master containers"
    return 0
  fi

  launchctl bootout system "$PLIST_PATH" 2>/dev/null || true
  if [[ -x /opt/vezor/current/bin/vezor-master && -f "$DEFAULT_MASTER_CONFIG" ]]; then
    /opt/vezor/current/bin/vezor-master down \
      --config "$DEFAULT_MASTER_CONFIG" >/dev/null 2>&1 || true
  fi
}

check_port_available() {
  local port="$1"
  local port_owner=""
  if command -v lsof >/dev/null 2>&1 \
    && port_owner="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null)"; then
    echo "Port $port is already in use." >&2
    printf '%s\n' "$port_owner" >&2
    echo "Stop any development stack or other service using port $port, then rerun the installer." >&2
    exit 1
  fi
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer target is macOS master. Detected: $(uname -s)" >&2
  exit 1
fi

ARCH="$(uname -m)"
case "$ARCH" in
  arm64|x86_64)
    ;;
  *)
    echo "Unsupported macOS architecture: $ARCH" >&2
    exit 1
    ;;
esac

if [[ ! -d /Applications/Docker.app ]]; then
  echo "Docker Desktop is required for this portable macOS master appliance." >&2
  echo "Install Docker Desktop, start it once, then rerun this installer." >&2
  exit 1
fi

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

stop_existing_master

for port in 3000 8000 8080 8554 8888 8889 9000; do
  check_port_available "$port"
done

run install -d -m 0755 \
  "$CONFIG_DIR" \
  "$CONFIG_DIR/secrets" \
  "$CONFIG_DIR/nats" \
  "$CONFIG_DIR/mediamtx" \
  "$DATA_DIR" \
  /var/log/vezor \
  /var/log/vezor/backend
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

for docker_data_dir in \
  "$DATA_DIR/postgres" \
  "$DATA_DIR/redis" \
  "$DATA_DIR/nats" \
  "$DATA_DIR/minio" \
  "$DATA_DIR/mediamtx" \
  "$DATA_DIR/credentials" \
  "$DATA_DIR/evidence" \
  "$DATA_DIR/bootstrap" \
  /var/log/vezor/backend
do
  prepare_data_dir_for_docker_desktop "$docker_data_dir"
done

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
  "platform": "macos",
  "version": "${VERSION:-unversioned}",
  "public_url": "$PUBLIC_URL",
  "data_dir": "$DATA_DIR",
  "config_dir": "$CONFIG_DIR",
  "compose_file": "/opt/vezor/current/infra/install/compose/compose.master.yml"
}
JSON
  umask "$old_umask"
fi
prepare_config_for_docker_desktop "$MASTER_CONFIG"

SUPERVISOR_CONFIG="$CONFIG_DIR/supervisor.json"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $SUPERVISOR_CONFIG"
else
  old_umask="$(umask)"
  umask 027
  cat > "$SUPERVISOR_CONFIG" <<JSON
{
  "supervisor_id": "central-master-1",
  "role": "central",
  "api_base_url": "http://backend:8000",
  "credential_store_path": "/run/vezor/credentials/supervisor.credential",
  "service_manager": "compose",
  "version": "${VERSION:-unversioned}"
}
JSON
  umask "$old_umask"
fi
prepare_config_for_docker_desktop "$SUPERVISOR_CONFIG"

build_local_master_images
start_local_master_containers

run install -m 0644 \
  /opt/vezor/current/infra/install/launchd/com.vezor.master.plist \
  "$PLIST_PATH"

run launchctl bootstrap system "$PLIST_PATH"
run launchctl enable system/com.vezor.master

echo "Vezor macOS master install complete."
echo "Open the first-run UI: $PUBLIC_URL/first-run"
