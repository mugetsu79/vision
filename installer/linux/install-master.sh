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

run install -d -m 0755 "$CONFIG_DIR" "$CONFIG_DIR/secrets" "$DATA_DIR" /var/log/vezor /run/vezor
run install -d -m 0755 \
  "$DATA_DIR/postgres" \
  "$DATA_DIR/redis" \
  "$DATA_DIR/nats" \
  "$DATA_DIR/minio" \
  "$DATA_DIR/mediamtx" \
  "$DATA_DIR/models" \
  "$DATA_DIR/evidence" \
  "$DATA_DIR/bootstrap"

MASTER_CONFIG="$CONFIG_DIR/master.json"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $MASTER_CONFIG"
else
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
fi

run install -m 0644 \
  /opt/vezor/current/infra/install/systemd/vezor-master.service \
  /etc/systemd/system/vezor-master.service

run systemctl daemon-reload
run systemctl enable vezor-master.service
run systemctl start vezor-master.service

echo "Vezor Linux master install complete."
echo "Open the first-run UI: $PUBLIC_URL/first-run"
