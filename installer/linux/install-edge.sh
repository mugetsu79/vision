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
PUBLIC_STREAM_HOST="${VEZOR_EDGE_PUBLIC_STREAM_HOST:-}"
PUBLIC_MEDIAMTX_RTSP_URL="${VEZOR_EDGE_PUBLIC_MEDIAMTX_RTSP_URL:-}"
MASTER_NATS_LEAF_URL="${VEZOR_MASTER_NATS_LEAF_URL:-}"
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
  --public-stream-host HOST
                         Host/IP the master can use to read this edge MediaMTX service.
  --public-mediamtx-rtsp-url URL
                         Full public RTSP base URL. Defaults to rtsp://HOST:8554.
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
    --public-stream-host)
      PUBLIC_STREAM_HOST="${2:?--public-stream-host requires a value}"
      shift 2
      ;;
    --public-mediamtx-rtsp-url)
      PUBLIC_MEDIAMTX_RTSP_URL="${2:?--public-mediamtx-rtsp-url requires a value}"
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

detect_public_stream_host() {
  if [[ -n "$PUBLIC_STREAM_HOST" ]]; then
    printf '%s\n' "$PUBLIC_STREAM_HOST"
    return 0
  fi

  local first_ip
  first_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ -n "$first_ip" ]]; then
    printf '%s\n' "$first_ip"
    return 0
  fi

  hostname -f 2>/dev/null || hostname
}

existing_supervisor_config_value() {
  local key="$1"
  if [[ ! -f "$SUPERVISOR_CONFIG" ]]; then
    return 0
  fi

  python3 - "$SUPERVISOR_CONFIG" "$key" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
payload = json.loads(path.read_text(encoding="utf-8"))
if not isinstance(payload, dict):
    raise SystemExit(0)
value = payload.get(key)
if isinstance(value, str):
    print(value)
PY
}

master_nats_leaf_url() {
  if [[ -n "$MASTER_NATS_LEAF_URL" ]]; then
    printf '%s\n' "$MASTER_NATS_LEAF_URL"
    return 0
  fi

  python3 - "$API_URL" <<'PY'
import sys
from urllib.parse import urlparse

api_url = sys.argv[1]
parsed = urlparse(api_url)
host = parsed.hostname
if not host:
    raise SystemExit("Unable to derive master NATS leaf URL from --api-url.")
if ":" in host and not host.startswith("["):
    host = f"[{host}]"
print(f"nats://{host}:7422")
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

stop_existing_edge_appliance() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] stop existing vezor-edge appliance if present"
    return 0
  fi
  if command -v systemctl >/dev/null 2>&1; then
    systemctl stop vezor-edge.service >/dev/null 2>&1 || true
  fi
  if [[ -x "$RELEASE_DIR/bin/vezor-edge" && -f "$EDGE_CONFIG" ]]; then
    VEZOR_MEDIAMTX_IMAGE="$MEDIAMTX_IMAGE" \
    VEZOR_NATS_IMAGE="$NATS_IMAGE" \
    VEZOR_SUPERVISOR_IMAGE="$EDGE_WORKER_IMAGE" \
      "$RELEASE_DIR/bin/vezor-edge" down --config "$EDGE_CONFIG" >/dev/null 2>&1 || true
  fi
  if command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    "$CONTAINER_ENGINE" rm -f \
      vezor-supervisor \
      vezor-edge-mediamtx \
      vezor-edge-nats-leaf \
      >/dev/null 2>&1 || true
  fi
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
NATS_IMAGE="$(manifest_image_ref nats nats:2)"
EDGE_WORKER_IMAGE="$(manifest_image_ref edge-worker vezor/edge-worker:portable-demo)"
if [[ -z "$PUBLIC_MEDIAMTX_RTSP_URL" ]]; then
  PUBLIC_MEDIAMTX_RTSP_URL="rtsp://$(detect_public_stream_host):8554"
fi

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

CONFIG_API_URL="$(existing_supervisor_config_value api_base_url)"
if [[ -z "$API_URL" && -n "$CONFIG_API_URL" ]]; then
  API_URL="$CONFIG_API_URL"
fi

if [[ -z "$API_URL" ]]; then
  echo "Edge install requires --api-url or an existing supervisor api_base_url." >&2
  exit 2
fi

MASTER_NATS_LEAF_URL="$(master_nats_leaf_url)"

if command -v curl >/dev/null 2>&1 && [[ -n "$API_URL" ]]; then
  curl -fsS "$API_URL/healthz" >/dev/null
fi

CONFIG_EDGE_NODE_ID="$(existing_supervisor_config_value edge_node_id)"
CONFIG_HOSTNAME="$(existing_supervisor_config_value hostname)"
if [[ -z "$CONFIG_HOSTNAME" ]]; then
  CONFIG_HOSTNAME="$(hostname)"
fi
if [[ "$UNPAIRED" -eq 1 && -z "$CONFIG_EDGE_NODE_ID" ]]; then
  echo "Unpaired edge update requires an existing paired supervisor config with edge_node_id." >&2
  echo "Create a fresh Pair Jetson edge session and rerun without --unpaired." >&2
  exit 2
fi

stop_existing_edge_appliance

if [[ -x "$RELEASE_DIR/scripts/jetson-preflight.sh" ]]; then
  (cd "$RELEASE_DIR" && scripts/jetson-preflight.sh --installer --json)
fi

run install -d -m 0755 \
  "$CONFIG_DIR" \
  "$CONFIG_DIR/secrets" \
  "$CONFIG_DIR/mediamtx" \
  "$CONFIG_DIR/nats" \
  "$DATA_DIR" \
  /var/log/vezor \
  /run/vezor
run install -d -m 0755 "$MODEL_DIR" "$DATA_DIR/edge" "$DATA_DIR/mediamtx" "$DATA_DIR/nats" "$DATA_DIR/credentials"

NATS_CONFIG="$CONFIG_DIR/nats/leaf.conf"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write edge NATS leaf config $NATS_CONFIG"
else
  MASTER_NATS_LEAF_URL="$MASTER_NATS_LEAF_URL" python3 - "$RELEASE_DIR/infra/nats/leaf.conf" "$NATS_CONFIG" <<'PY'
import os
import sys
from pathlib import Path

remote_url = os.environ["MASTER_NATS_LEAF_URL"]
source = Path(sys.argv[1]).read_text(encoding="utf-8")
target = source.replace(
    'urls: ["nats://host.docker.internal:7422"]',
    f'urls: ["{remote_url}"]',
)
Path(sys.argv[2]).write_text(target, encoding="utf-8")
PY
  chmod 0644 "$NATS_CONFIG"
fi

MEDIAMTX_CONFIG="$CONFIG_DIR/mediamtx/mediamtx.yml"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write edge MediaMTX config $MEDIAMTX_CONFIG"
else
  API_URL="$API_URL" python3 - "$RELEASE_DIR/infra/mediamtx/mediamtx.yml" "$MEDIAMTX_CONFIG" <<'PY'
import sys
from pathlib import Path

api_url = __import__("os").environ["API_URL"].rstrip("/")
source = Path(sys.argv[1]).read_text(encoding="utf-8")
target = source.replace(
    "authJWTJWKS: http://backend:8000/.well-known/argus/mediamtx/jwks.json",
    f"authJWTJWKS: {api_url}/.well-known/argus/mediamtx/jwks.json",
)
Path(sys.argv[2]).write_text(target, encoding="utf-8")
PY
  chmod 0644 "$MEDIAMTX_CONFIG"
fi

EDGE_ENV="$CONFIG_DIR/edge.env"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write $EDGE_ENV"
else
  cat > "$EDGE_ENV" <<ENV
VEZOR_MEDIAMTX_IMAGE=$MEDIAMTX_IMAGE
VEZOR_NATS_IMAGE=$NATS_IMAGE
VEZOR_SUPERVISOR_IMAGE=$EDGE_WORKER_IMAGE
VEZOR_CREDENTIALS_HOST_DIR=$DATA_DIR/credentials
VEZOR_MODEL_HOST_DIR=$MODEL_DIR
ARGUS_NATS_URL=nats://nats-leaf:4222
VEZOR_NATS_LEAF_REMOTE_URL=$MASTER_NATS_LEAF_URL
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
  CONFIG_EDGE_NODE_ID="$CONFIG_EDGE_NODE_ID" \
  CONFIG_HOSTNAME="$CONFIG_HOSTNAME" \
  EDGE_NAME="$EDGE_NAME" \
  API_URL="$API_URL" \
  PUBLIC_MEDIAMTX_RTSP_URL="$PUBLIC_MEDIAMTX_RTSP_URL" \
  VERSION="${VERSION:-edge-installer}" \
  python3 - "$SUPERVISOR_CONFIG" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = {}
if path.exists():
    existing = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(existing, dict):
        payload.update(existing)

payload.update(
    {
        "supervisor_id": os.environ["EDGE_NAME"],
        "role": "edge",
        "api_base_url": os.environ["API_URL"],
        "credential_store_path": "/run/vezor/credentials/supervisor.credential",
        "worker_metrics_url": "http://127.0.0.1:9108/metrics",
        "public_mediamtx_rtsp_url": os.environ["PUBLIC_MEDIAMTX_RTSP_URL"],
        "service_manager": "systemd",
        "version": os.environ["VERSION"],
    }
)

edge_node_id = os.environ.get("CONFIG_EDGE_NODE_ID", "").strip()
if edge_node_id:
    payload["edge_node_id"] = edge_node_id
else:
    payload.pop("edge_node_id", None)

hostname = os.environ.get("CONFIG_HOSTNAME", "").strip()
if hostname:
    payload["hostname"] = hostname

path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
  chmod 0644 "$EDGE_CONFIG" "$SUPERVISOR_CONFIG"
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
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] chown 10001:10001 $DATA_DIR/credentials/supervisor.credential"
    echo "[dry-run] chmod 0600 $DATA_DIR/credentials/supervisor.credential"
  elif [[ -f "$DATA_DIR/credentials/supervisor.credential" ]]; then
    chown 10001:10001 "$DATA_DIR/credentials/supervisor.credential"
    chmod 0600 "$DATA_DIR/credentials/supervisor.credential"
  fi
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
