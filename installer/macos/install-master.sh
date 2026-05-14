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

run install -d -m 0755 "$CONFIG_DIR" "$CONFIG_DIR/secrets" "$DATA_DIR" /var/log/vezor
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
  "platform": "macos",
  "version": "${VERSION:-unversioned}",
  "public_url": "$PUBLIC_URL",
  "data_dir": "$DATA_DIR",
  "config_dir": "$CONFIG_DIR",
  "compose_file": "/opt/vezor/current/infra/install/compose/compose.master.yml"
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
