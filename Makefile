UV ?= uv
PNPM ?= pnpm
REGISTRY ?= ghcr.io/mugetsu79/vision
TAG ?= local
BUILD_PLATFORMS ?= linux/amd64,linux/arm64

.PHONY: fmt lint test models dev-up dev-down migrate revision build-multiarch build-central build-edge build-frontend helm-template verify-all verify-installers

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

build-central:
	docker buildx build \
		--platform linux/amd64 \
		-f backend/Dockerfile \
		-t $(REGISTRY)/argus-backend:$(TAG) \
		backend

build-edge:
	docker buildx build \
		--platform linux/arm64 \
		-f backend/Dockerfile.edge \
		$(if $(JETSON_ORT_WHEEL_URL),--build-arg JETSON_ORT_WHEEL_URL=$(JETSON_ORT_WHEEL_URL),) \
		-t $(REGISTRY)/argus-edge:$(TAG) \
		backend

build-frontend:
	docker buildx build \
		--platform linux/amd64 \
		-f frontend/Dockerfile \
		-t $(REGISTRY)/argus-frontend:$(TAG) \
		frontend

build-multiarch:
	docker buildx build \
		--platform linux/amd64 \
		-f backend/Dockerfile \
		-t $(REGISTRY)/argus-backend:$(TAG) \
		backend
	docker buildx build \
		--platform linux/arm64 \
		-f backend/Dockerfile.edge \
		$(if $(JETSON_ORT_WHEEL_URL),--build-arg JETSON_ORT_WHEEL_URL=$(JETSON_ORT_WHEEL_URL),) \
		-t $(REGISTRY)/argus-edge:$(TAG) \
		backend
	docker buildx build \
		--platform linux/amd64 \
		-f frontend/Dockerfile \
		-t $(REGISTRY)/argus-frontend:$(TAG) \
		frontend

helm-template:
	helm template argus infra/helm/argus

verify-all:
	./scripts/run-full-validation.sh

verify-installers:
	./scripts/validate-installers.sh
