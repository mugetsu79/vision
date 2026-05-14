#!/usr/bin/env bash
set -euo pipefail

PURGE_DATA=0
CONFIRMATION=""
PLIST_PATH="/Library/LaunchDaemons/com.vezor.master.plist"

usage() {
  cat <<'USAGE'
Uninstall the Vezor macOS appliance services.

Options:
  --purge-data CONFIRMATION   Delete Vezor data only when CONFIRMATION is delete-vezor-data.
  -h, --help                  Show this help.

Default behavior unloads launchd services while preserving Vezor data.
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

if command -v launchctl >/dev/null 2>&1; then
  launchctl bootout system "$PLIST_PATH" 2>/dev/null || true
  rm -f "$PLIST_PATH"
fi

if [[ "$PURGE_DATA" -eq 1 ]]; then
  if [[ "$CONFIRMATION" != "delete-vezor-data" ]]; then
    echo "Refusing to purge data without confirmation: delete-vezor-data" >&2
    exit 2
  fi
  rm -rf /var/lib/vezor /etc/vezor /var/log/vezor
  echo "Deleted Vezor data and configuration."
else
  echo "Preserving Vezor data under /var/lib/vezor and configuration under /etc/vezor."
fi
