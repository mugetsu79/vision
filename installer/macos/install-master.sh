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

  umask 077
  if [[ -z "$value" ]]; then
    value="$(random_secret)"
  fi
  printf '%s\n' "$value" > "$path"
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

run install -d -m 0755 \
  "$CONFIG_DIR" \
  "$CONFIG_DIR/secrets" \
  "$CONFIG_DIR/nats" \
  "$CONFIG_DIR/mediamtx" \
  "$DATA_DIR" \
  /var/log/vezor \
  /run/vezor \
  /run/vezor/credentials
run install -d -m 0755 \
  "$DATA_DIR/postgres" \
  "$DATA_DIR/redis" \
  "$DATA_DIR/nats" \
  "$DATA_DIR/minio" \
  "$DATA_DIR/mediamtx" \
  "$DATA_DIR/models" \
  "$DATA_DIR/evidence" \
  "$DATA_DIR/bootstrap"

write_secret_if_missing "$CONFIG_DIR/secrets/postgres_password"
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
VEZOR_POSTGRES_IMAGE=$(manifest_image_ref postgres postgres:16)
VEZOR_REDIS_IMAGE=$(manifest_image_ref redis redis:7)
VEZOR_NATS_IMAGE=$(manifest_image_ref nats nats:2)
VEZOR_MINIO_IMAGE=$(manifest_image_ref minio minio/minio:latest)
VEZOR_KEYCLOAK_IMAGE=$(manifest_image_ref keycloak quay.io/keycloak/keycloak:latest)
VEZOR_MEDIAMTX_IMAGE=$(manifest_image_ref mediamtx bluenviron/mediamtx:latest)
VEZOR_BACKEND_IMAGE=$(manifest_image_ref backend ghcr.io/vezor/backend:dev)
VEZOR_FRONTEND_IMAGE=$(manifest_image_ref frontend ghcr.io/vezor/frontend:dev)
VEZOR_SUPERVISOR_IMAGE=$(manifest_image_ref supervisor ghcr.io/vezor/supervisor:dev)
VEZOR_PUBLIC_FRONTEND_URL=$PUBLIC_URL
VEZOR_PUBLIC_API_BASE_URL=${PUBLIC_URL%:*}:8000
VEZOR_PUBLIC_OIDC_AUTHORITY=${PUBLIC_URL%:*}:8080/realms/vezor
ENV
fi

MASTER_CONFIG="$CONFIG_DIR/master.json"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $MASTER_CONFIG"
else
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
fi

SUPERVISOR_CONFIG="$CONFIG_DIR/supervisor.json"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $SUPERVISOR_CONFIG"
else
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
fi

run install -m 0644 \
  /opt/vezor/current/infra/install/launchd/com.vezor.master.plist \
  "$PLIST_PATH"

if [[ "$DRY_RUN" -eq 0 ]]; then
  launchctl bootout system "$PLIST_PATH" 2>/dev/null || true
fi
run launchctl bootstrap system "$PLIST_PATH"
run launchctl enable system/com.vezor.master

echo "Vezor macOS master install complete."
echo "Open the first-run UI: $PUBLIC_URL/first-run"
