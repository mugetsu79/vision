#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log_step() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"

  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  printf 'Timed out waiting for %s at %s\n' "$label" "$url" >&2
  return 1
}

cd "$ROOT_DIR"

CORE_SERVICES=(
  postgres
  redis
  nats
  minio
  keycloak
  mediamtx
  otel-collector
  prometheus
  alertmanager
  loki
  tempo
  grafana
  backend
)

FRONTEND_WAS_RUNNING=0

cleanup() {
  if [[ "$FRONTEND_WAS_RUNNING" -eq 1 ]]; then
    log_step "Restoring Docker frontend service"
    docker compose -f infra/docker-compose.dev.yml up -d frontend >/dev/null
  fi
}

trap cleanup EXIT

log_step "Starting or refreshing backend and infrastructure services"
docker compose -f infra/docker-compose.dev.yml up -d "${CORE_SERVICES[@]}"

if docker compose -f infra/docker-compose.dev.yml ps --services --filter status=running | grep -qx "frontend"; then
  FRONTEND_WAS_RUNNING=1
  log_step "Temporarily stopping the Docker frontend service so Playwright can bind port 3000"
  docker compose -f infra/docker-compose.dev.yml stop frontend >/dev/null
fi

log_step "Waiting for core services"
wait_for_http "http://127.0.0.1:8000/healthz" "backend health"
wait_for_http \
  "http://127.0.0.1:8080/realms/argus-dev/.well-known/openid-configuration" \
  "Keycloak realm configuration"

log_step "Running backend migrations"
(
  cd backend
  python3 -m uv run alembic upgrade head
)

log_step "Regenerating frontend API types"
(
  cd frontend
  corepack pnpm generate:api
)

log_step "Running backend static checks"
(
  cd backend
  python3 -m uv run ruff check .
  python3 -m uv run mypy --strict src
)

log_step "Running backend tests"
(
  cd backend
  python3 -m uv run pytest
)

log_step "Running frontend checks"
(
  cd frontend
  corepack pnpm lint
  corepack pnpm test
  corepack pnpm build
)

log_step "Running frontend Playwright suite"
(
  cd frontend
  corepack pnpm exec playwright test
)

log_step "Rendering Helm templates"
helm template argus infra/helm/argus >/dev/null
helm template argus infra/helm/argus -f infra/helm/argus/values-edge.yaml >/dev/null

log_step "Checking runtime health"
docker compose -f infra/docker-compose.dev.yml ps
curl -fsS http://127.0.0.1:8000/healthz

log_step "Argus full validation completed successfully"
