morya@printer vision % docker compose -f infra/docker-compose.dev.yml exec backend /tmp/argus-backend-venv/bin/alembic upgrade head
OCI runtime exec failed: exec failed: unable to start container process: exec: "/tmp/argus-backend-venv/bin/alembic": stat /tmp/argus-backend-venv/bin/alembic: no such file or directory: unknown
morya@printer vision % docker compose -f infra/docker-compose.dev.yml exec backend /tmp/argus-backend-venv/bin/alembic upgrade head
