UV ?= uv
PNPM ?= pnpm

.PHONY: fmt lint test models dev-up dev-down migrate revision

fmt:
	cd backend && $(UV) run ruff format .
	cd frontend && $(PNPM) exec prettier --write .

lint:
	cd backend && $(UV) run ruff check .
	cd backend && $(UV) run mypy --strict src
	cd frontend && $(PNPM) exec eslint .

test:
	cd backend && $(UV) run pytest
	cd frontend && $(PNPM) test

models:
	@mkdir -p models
	@echo "Place ONNX models in ./models"

dev-up:
	docker compose -f infra/docker-compose.dev.yml up -d

dev-down:
	docker compose -f infra/docker-compose.dev.yml down -v

migrate:
	cd backend && $(UV) run alembic upgrade head

revision:
	cd backend && $(UV) run alembic revision --autogenerate -m "$(MESSAGE)"
