morya@printer vision % docker compose -f infra/docker-compose.dev.yml exec backend /tmp/argus-backend-venv/bin/alembic upgrade head
OCI runtime exec failed: exec failed: unable to start container process: exec: "/tmp/argus-backend-venv/bin/alembic": stat /tmp/argus-backend-venv/bin/alembic: no such file or directory: unknown
morya@printer vision % docker compose -f infra/docker-compose.dev.yml exec backend /tmp/argus-backend-venv/bin/alembic upgrade head



-------------------

cd "$HOME/vision"
git fetch origin
git switch codex/argus-ui-refresh
git pull --rebase origin codex/argus-ui-refresh
make dev-down
make dev-up
docker compose -f infra/docker-compose.dev.yml exec backend /tmp/argus-backend-venv/bin/alembic upgrade head
cd frontend && corepack pnpm generate:api
