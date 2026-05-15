#!/usr/bin/env bash
set -euo pipefail

API_URL=""
PAIRING_CODE=""
SESSION_ID=""
EDGE_NAME="jetson-edge"
MODEL_DIR="/var/lib/vezor/models"
VERSION=""
MANIFEST=""
JETSON_ORT_WHEEL_URL="${JETSON_ORT_WHEEL_URL:-}"
ALLOW_CPU_ONNX_RUNTIME="${VEZOR_ALLOW_CPU_ONNX_RUNTIME:-0}"
CONFIG_DIR="/etc/vezor"
EDGE_CONFIG="/etc/vezor/edge.json"
SUPERVISOR_CONFIG="/etc/vezor/supervisor.json"
DATA_DIR="/var/lib/vezor"
UNPAIRED=0
DRY_RUN=0
RELEASE_DIR="/opt/vezor/current"
CONTAINER_ENGINE="docker"

usage() {
  cat <<'USAGE'
Install the Vezor Linux/Jetson edge appliance.

Options:
  --api-url URL          Master API URL used for pairing and health checks.
  --pairing-code CODE    One-time pairing code from Control -> Deployment.
  --session-id ID        Pairing session id from Control -> Deployment.
  --unpaired             Install service without claiming a pairing session.
  --edge-name NAME       Local edge node name. Default: jetson-edge.
  --model-dir PATH       Local model directory. Default: /var/lib/vezor/models.
  --version VERSION      Release version to record in supervisor config.
  --manifest PATH        Release manifest path. Dev manifests build a local edge image.
  --jetson-ort-wheel-url URL
                         Required Jetson ONNX Runtime GPU wheel URL for local dev builds.
  --allow-cpu-onnx-runtime
                         Diagnostic only: allow CPU ONNX Runtime when no Jetson GPU wheel is set.
  --dry-run              Print actions without changing the host.
  -h, --help             Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-url)
      API_URL="${2:?--api-url requires a value}"
      shift 2
      ;;
    --pairing-code)
      PAIRING_CODE="${2:?--pairing-code requires a value}"
      shift 2
      ;;
    --session-id)
      SESSION_ID="${2:?--session-id requires a value}"
      shift 2
      ;;
    --unpaired)
      UNPAIRED=1
      shift
      ;;
    --edge-name)
      EDGE_NAME="${2:?--edge-name requires a value}"
      shift 2
      ;;
    --model-dir)
      MODEL_DIR="${2:?--model-dir requires a value}"
      shift 2
      ;;
    --version)
      VERSION="${2:?--version requires a value}"
      shift 2
      ;;
    --manifest)
      MANIFEST="${2:?--manifest requires a value}"
      shift 2
      ;;
    --jetson-ort-wheel-url)
      JETSON_ORT_WHEEL_URL="${2:?--jetson-ort-wheel-url requires a value}"
      shift 2
      ;;
    --allow-cpu-onnx-runtime)
      ALLOW_CPU_ONNX_RUNTIME=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
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

build_local_edge_image() {
  if [[ "$(manifest_release_channel)" != "dev" ]]; then
    return 0
  fi

  require_command "$CONTAINER_ENGINE"
  if [[ -z "$JETSON_ORT_WHEEL_URL" && "$ALLOW_CPU_ONNX_RUNTIME" != "1" ]]; then
    echo "Jetson ONNX Runtime GPU wheel is required for dev manifest edge builds." >&2
    echo "Pass --jetson-ort-wheel-url with the Jetson cp310 linux_aarch64 GPU wheel." >&2
    echo "Use --allow-cpu-onnx-runtime only for CPU-only diagnostics, not product demos." >&2
    exit 2
  fi
  echo "Building local Vezor Jetson edge image for dev manifest..."
  run "$CONTAINER_ENGINE" build \
    -f /opt/vezor/current/backend/Dockerfile.edge \
    --build-arg "JETSON_ORT_WHEEL_URL=$JETSON_ORT_WHEEL_URL" \
    --build-arg "ALLOW_CPU_ONNX_RUNTIME=$ALLOW_CPU_ONNX_RUNTIME" \
    -t "$EDGE_WORKER_IMAGE" \
    /opt/vezor/current/backend
}

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer target is Linux or Jetson edge. Detected: $(uname -s)" >&2
  exit 1
fi

if [[ -n "$MANIFEST" && ! -f "$MANIFEST" ]]; then
  echo "Manifest not found: $MANIFEST" >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  CONTAINER_ENGINE="docker"
elif command -v podman >/dev/null 2>&1; then
  CONTAINER_ENGINE="podman"
else
  echo "Docker or Podman is required for the Vezor edge appliance." >&2
  exit 1
fi

MEDIAMTX_IMAGE="$(manifest_image_ref mediamtx bluenviron/mediamtx:latest)"
EDGE_WORKER_IMAGE="$(manifest_image_ref edge-worker vezor/edge-worker:portable-demo)"

if [[ "$UNPAIRED" -eq 0 && -z "$PAIRING_CODE" ]]; then
  echo "Provide --pairing-code or choose --unpaired for deferred pairing." >&2
  exit 2
fi

if [[ -n "$PAIRING_CODE" && -z "$SESSION_ID" ]]; then
  echo "--pairing-code requires --session-id." >&2
  exit 2
fi

if [[ "$UNPAIRED" -eq 0 && -z "$API_URL" ]]; then
  echo "Paired install requires --api-url." >&2
  exit 2
fi

if command -v curl >/dev/null 2>&1 && [[ -n "$API_URL" ]]; then
  curl -fsS "$API_URL/healthz" >/dev/null
fi

if [[ -x "$RELEASE_DIR/scripts/jetson-preflight.sh" ]]; then
  (cd "$RELEASE_DIR" && scripts/jetson-preflight.sh --installer --json)
fi

run install -d -m 0755 \
  "$CONFIG_DIR" \
  "$CONFIG_DIR/secrets" \
  "$CONFIG_DIR/mediamtx" \
  "$DATA_DIR" \
  /var/log/vezor \
  /run/vezor
run install -d -m 0755 "$MODEL_DIR" "$DATA_DIR/edge" "$DATA_DIR/mediamtx" "$DATA_DIR/credentials"

run install -m 0644 "$RELEASE_DIR/infra/mediamtx/mediamtx.yml" "$CONFIG_DIR/mediamtx/mediamtx.yml"

EDGE_ENV="$CONFIG_DIR/edge.env"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $EDGE_ENV"
else
  cat > "$EDGE_ENV" <<ENV
VEZOR_MEDIAMTX_IMAGE=$MEDIAMTX_IMAGE
VEZOR_SUPERVISOR_IMAGE=$EDGE_WORKER_IMAGE
VEZOR_CREDENTIALS_HOST_DIR=$DATA_DIR/credentials
ENV
  chmod 0644 "$EDGE_ENV"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $EDGE_CONFIG"
  echo "[dry-run] write $SUPERVISOR_CONFIG"
else
  old_umask="$(umask)"
  umask 027
  cat > "$EDGE_CONFIG" <<JSON
{
  "role": "edge",
  "edge_name": "$EDGE_NAME",
  "api_url": "$API_URL",
  "model_dir": "$MODEL_DIR",
  "container_engine": "$CONTAINER_ENGINE",
  "local_mediamtx_rtsp_url": "rtsp://127.0.0.1:8554",
  "compose_file": "/opt/vezor/current/infra/install/compose/compose.supervisor.yml"
}
JSON
  cat > "$SUPERVISOR_CONFIG" <<JSON
{
  "supervisor_id": "$EDGE_NAME",
  "role": "edge",
  "api_base_url": "$API_URL",
  "credential_store_path": "/run/vezor/credentials/supervisor.credential",
  "worker_metrics_url": "http://127.0.0.1:9108/metrics",
  "service_manager": "systemd",
  "version": "${VERSION:-edge-installer}"
}
JSON
  umask "$old_umask"
fi

if [[ "$UNPAIRED" -eq 0 ]]; then
  run /opt/vezor/current/bin/vezorctl pair \
    --api-url "$API_URL" \
    --session-id "$SESSION_ID" \
    --pairing-code "$PAIRING_CODE" \
    --supervisor-id "$EDGE_NAME" \
    --hostname "$(hostname)" \
    --config "$SUPERVISOR_CONFIG" \
    --credential-path "$DATA_DIR/credentials/supervisor.credential"
fi

build_local_edge_image

run install -m 0644 \
  /opt/vezor/current/infra/install/systemd/vezor-edge.service \
  /etc/systemd/system/vezor-edge.service

run systemctl daemon-reload
run systemctl enable vezor-edge.service
run systemctl start vezor-edge.service

echo "Vezor edge install complete."
echo "Open Control -> Deployment to confirm service health and credential status."
