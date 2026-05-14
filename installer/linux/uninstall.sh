#!/usr/bin/env bash
set -euo pipefail

PURGE_DATA=0
CONFIRMATION=""

usage() {
  cat <<'USAGE'
Uninstall the Vezor Linux appliance services.

Options:
  --purge-data CONFIRMATION   Delete Vezor data only when CONFIRMATION is delete-vezor-data.
  -h, --help                  Show this help.

Default behavior stops and disables services while preserving Vezor data.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge-data)
      PURGE_DATA=1
      CONFIRMATION="${2:?--purge-data requires confirmation text}"
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

if command -v systemctl >/dev/null 2>&1; then
  systemctl stop vezor-master.service 2>/dev/null || true
  systemctl disable vezor-master.service 2>/dev/null || true
  rm -f /etc/systemd/system/vezor-master.service
  systemctl daemon-reload
fi

if [[ "$PURGE_DATA" -eq 1 ]]; then
  if [[ "$CONFIRMATION" != "delete-vezor-data" ]]; then
    echo "Refusing to purge data without confirmation: delete-vezor-data" >&2
    exit 2
  fi
  rm -rf /var/lib/vezor /etc/vezor /var/log/vezor /run/vezor
  echo "Deleted Vezor data and configuration."
else
  echo "Preserving Vezor data under /var/lib/vezor and configuration under /etc/vezor."
fi
