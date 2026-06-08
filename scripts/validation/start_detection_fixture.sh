#!/usr/bin/env bash
set -euo pipefail

: "${VEZOR_SMOKE_FIXTURE_PUBLISH_URL:?VEZOR_SMOKE_FIXTURE_PUBLISH_URL is required}"

IMAGE_PATH="$(
  "${VEZOR_SMOKE_PYTHON:-python3}" - <<'PY' | tail -n 1
from pathlib import Path

try:
    import ultralytics
except ModuleNotFoundError as exc:
    raise SystemExit("ultralytics is required to locate assets/bus.jpg") from exc

print(Path(ultralytics.__file__).resolve().parent / "assets" / "bus.jpg")
PY
)"

if [[ ! -f "$IMAGE_PATH" ]]; then
  printf 'Ultralytics sample image not found at %s\n' "$IMAGE_PATH" >&2
  exit 1
fi

printf 'Publishing deterministic detection fixture from ultralytics/assets/bus.jpg to rtsp://***\n' >&2

exec ffmpeg \
  2> >(sed -E 's#[Rr][Tt][Ss][Pp]://[^[:space:]]+#rtsp://***#g' >&2) \
  -hide_banner \
  -loglevel warning \
  -re \
  -loop 1 \
  -i "$IMAGE_PATH" \
  -vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2" \
  -r 10 \
  -g 10 \
  -keyint_min 10 \
  -sc_threshold 0 \
  -c:v libx264 \
  -preset veryfast \
  -tune zerolatency \
  -pix_fmt yuv420p \
  -f rtsp \
  "$VEZOR_SMOKE_FIXTURE_PUBLISH_URL"
