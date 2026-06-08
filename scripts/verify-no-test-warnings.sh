#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

backend_log="$(mktemp)"
frontend_log="$(mktemp)"
trap 'rm -f "$backend_log" "$frontend_log"' EXIT

echo "==> backend warning gate"
(
  cd backend
  python3 -m uv run pytest -q \
    -W error::DeprecationWarning \
    -W error::UserWarning
) 2>&1 | tee "$backend_log"

if rg -n 'directory "/run/secrets" does not exist|HTTP_422_UNPROCESSABLE_ENTITY|DeprecationWarning|UserWarning' "$backend_log"; then
  echo "backend warning gate failed" >&2
  exit 1
fi

echo "==> frontend warning gate"
corepack pnpm --dir frontend test 2>&1 | tee "$frontend_log"

if rg -n 'not wrapped in act|React Router Future Flag Warning' "$frontend_log"; then
  echo "frontend warning gate failed" >&2
  exit 1
fi

echo "test warning gates passed"
