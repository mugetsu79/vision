from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    RuntimeArtifactCreate,
    RuntimeArtifactResponse,
    RuntimeArtifactUpdate,
)
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, get_current_user
from argus.main import create_app
from argus.models.enums import (
    DetectorCapability,
    RoleEnum,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
)


def _sample_user(role: RoleEnum) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="user-1",
        email="user@argus.local",
        role=role,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=role is RoleEnum.SUPERADMIN,
        tenant_context=str(uuid4()),
        claims={},
    )


def _artifact_payload() -> dict[str, object]:
    return {
        "scope": "model",
        "kind": "tensorrt_engine",
        "capability": "fixed_vocab",
        "runtime_backend": "tensorrt_engine",
        "path": "/models/yolo26n.engine",
        "target_profile": "linux-aarch64-nvidia-jetson",
        "precision": "fp16",
        "input_shape": {"width": 640, "height": 640},
        "classes": ["person", "car"],
        "source_model_sha256": "a" * 64,
        "sha256": "b" * 64,
        "size_bytes": 4321,
    }


def _artifact_response(model_id: UUID) -> RuntimeArtifactResponse:
    return RuntimeArtifactResponse(
        id=uuid4(),
        model_id=model_id,
        camera_id=None,
        scope=RuntimeArtifactScope.MODEL,
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.FIXED_VOCAB,
        runtime_backend="tensorrt_engine",
        path="/models/yolo26n.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "car"],
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=4321,
        validation_status=RuntimeArtifactValidationStatus.UNVALIDATED,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


class _FakeRuntimeArtifactService:
    def __init__(self, artifact: RuntimeArtifactResponse) -> None:
        self.artifacts = [artifact]
        self.created_payload: RuntimeArtifactCreate | None = None
        self.updated_payload: RuntimeArtifactUpdate | None = None

    async def list_for_model(self, model_id: UUID) -> list[RuntimeArtifactResponse]:
        return [artifact for artifact in self.artifacts if artifact.model_id == model_id]

    async def create_for_model(
        self,
        model_id: UUID,
        payload: RuntimeArtifactCreate,
    ) -> RuntimeArtifactResponse:
        self.created_payload = payload
        artifact = _artifact_response(model_id).model_copy(
            update=payload.model_dump(mode="python")
        )
        self.artifacts.append(artifact)
        return artifact

    async def update_artifact(
        self,
        model_id: UUID,
        artifact_id: UUID,
        payload: RuntimeArtifactUpdate,
    ) -> RuntimeArtifactResponse:
        self.updated_payload = payload
        existing = next(artifact for artifact in self.artifacts if artifact.id == artifact_id)
        updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
        self.artifacts[self.artifacts.index(existing)] = updated
        return updated

    async def validate_artifact(self, model_id: UUID, artifact_id: UUID) -> RuntimeArtifactResponse:
        return await self.update_artifact(
            model_id,
            artifact_id,
            RuntimeArtifactUpdate(validation_status=RuntimeArtifactValidationStatus.UNVALIDATED),
        )


class _FakeServices:
    def __init__(self, runtime_artifacts: _FakeRuntimeArtifactService) -> None:
        self.runtime_artifacts = runtime_artifacts


def _build_app(user: AuthenticatedUser, service: _FakeRuntimeArtifactService):
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = _FakeServices(service)
    app.dependency_overrides[get_current_user] = lambda: user
    return app


@pytest.mark.asyncio
async def test_runtime_artifact_routes_allow_viewer_list() -> None:
    model_id = uuid4()
    service = _FakeRuntimeArtifactService(_artifact_response(model_id))
    app = _build_app(_sample_user(RoleEnum.VIEWER), service)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/v1/models/{model_id}/runtime-artifacts")

    assert response.status_code == 200
    assert response.json()[0]["model_id"] == str(model_id)


@pytest.mark.asyncio
async def test_runtime_artifact_routes_require_admin_for_create() -> None:
    model_id = uuid4()
    service = _FakeRuntimeArtifactService(_artifact_response(model_id))
    viewer_app = _build_app(_sample_user(RoleEnum.VIEWER), service)

    async with AsyncClient(
        transport=ASGITransport(app=viewer_app),
        base_url="http://testserver",
    ) as client:
        forbidden_response = await client.post(
            f"/api/v1/models/{model_id}/runtime-artifacts",
            json=_artifact_payload(),
        )

    admin_app = _build_app(_sample_user(RoleEnum.ADMIN), service)
    async with AsyncClient(
        transport=ASGITransport(app=admin_app),
        base_url="http://testserver",
    ) as client:
        created_response = await client.post(
            f"/api/v1/models/{model_id}/runtime-artifacts",
            json=_artifact_payload(),
        )

    assert forbidden_response.status_code == 403
    assert created_response.status_code == 201
    assert created_response.json()["runtime_backend"] == "tensorrt_engine"
    assert service.created_payload is not None
