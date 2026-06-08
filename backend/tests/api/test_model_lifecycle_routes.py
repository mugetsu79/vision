from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import ModelImportJobResponse, ModelImportRequest, TenantContext
from argus.api.v1 import router
from argus.compat import UTC
from argus.core.security import AuthenticatedUser
from argus.models.enums import ModelImportSource, ModelLifecycleJobStatus, RoleEnum

TENANT_ID = uuid4()


def _user(role: RoleEnum) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=f"{role.value}-1",
        email=f"{role.value}@argus.local",
        role=role,
        issuer="http://issuer",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )


def _tenant_context(user: AuthenticatedUser) -> TenantContext:
    return TenantContext(
        tenant_id=TENANT_ID,
        tenant_slug="argus-dev",
        user=user,
    )


class _FakeTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id=None,  # noqa: ANN001
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        return self.user


class _FakeModelService:
    async def list_catalog_status(self) -> list[object]:
        return []


class _FakeModelLifecycleService:
    def __init__(self, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id
        self.registered_catalog_id: str | None = None
        self.import_payload: ModelImportRequest | None = None

    async def register_catalog_entry(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        catalog_id: str,
    ) -> ModelImportJobResponse:
        self.registered_catalog_id = catalog_id
        return _job_response(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            catalog_id=catalog_id,
            source=ModelImportSource.CATALOG,
            status=ModelLifecycleJobStatus.SUCCEEDED,
            model_id=uuid4(),
        )

    async def import_model_from_request(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        payload: ModelImportRequest,
    ) -> ModelImportJobResponse:
        self.import_payload = payload
        return _job_response(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            source=payload.source,
            status=ModelLifecycleJobStatus.QUEUED,
            source_uri=payload.source_uri,
            target_path=payload.source_uri or "",
            expected_sha256=payload.expected_sha256,
        )

    async def list_import_jobs(self, tenant_id: UUID) -> list[ModelImportJobResponse]:
        return [
            _job_response(
                tenant_id=tenant_id,
                actor_subject="admin@argus.local",
                source=ModelImportSource.URL,
                status=ModelLifecycleJobStatus.QUEUED,
                source_uri="https://models.example.test/yolo26n.onnx",
                expected_sha256="a" * 64,
            )
        ]

    async def queue_catalog_download(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        catalog_id: str,
    ) -> ModelImportJobResponse:
        raise ValueError(
            "Model artifact is expected to be bundled or mounted at models/yolo26n.onnx; "
            "no trusted download source is configured."
        )


def _create_app(user: AuthenticatedUser) -> FastAPI:
    context = _tenant_context(user)
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        models=_FakeModelService(),
        model_lifecycle=_FakeModelLifecycleService(context.tenant_id),
    )
    app.state.security = _FakeSecurity(user)
    return app


@pytest.mark.asyncio
async def test_catalog_register_requires_admin() -> None:
    app = _create_app(_user(RoleEnum.ADMIN))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/model-catalog/yolo26n-coco-onnx/register",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 201
    assert response.json()["status"] == "succeeded"
    assert app.state.services.model_lifecycle.registered_catalog_id == "yolo26n-coco-onnx"


@pytest.mark.asyncio
async def test_models_import_url_requires_admin() -> None:
    app = _create_app(_user(RoleEnum.VIEWER))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/models/import-url",
            headers={"Authorization": "Bearer token"},
            json={
                "source": "url",
                "source_uri": "https://models.example.test/yolo26n.onnx",
                "expected_sha256": "a" * 64,
                "name": "YOLO26n COCO",
                "version": "2026.1",
                "task": "detect",
                "format": "onnx",
                "capability": "fixed_vocab",
                "input_shape": {"width": 640, "height": 640},
                "classes": [],
                "license": "AGPL-3.0",
            },
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_model_import_jobs_route_returns_jobs() -> None:
    app = _create_app(_user(RoleEnum.ADMIN))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/model-import-jobs",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["status"] == "queued"
    assert body[0]["source"] == "url"


@pytest.mark.asyncio
async def test_catalog_download_for_bundled_entry_returns_conflict() -> None:
    app = _create_app(_user(RoleEnum.ADMIN))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/model-catalog/yolo26n-coco-onnx/download",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 409
    assert "bundled or mounted" in response.json()["detail"]


def _job_response(
    *,
    tenant_id: UUID,
    actor_subject: str,
    source: ModelImportSource,
    status: ModelLifecycleJobStatus,
    catalog_id: str | None = None,
    model_id: UUID | None = None,
    source_uri: str | None = None,
    target_path: str = "models/yolo26n.onnx",
    expected_sha256: str | None = None,
) -> ModelImportJobResponse:
    now = datetime.now(UTC)
    return ModelImportJobResponse(
        id=uuid4(),
        tenant_id=tenant_id,
        catalog_id=catalog_id,
        source=source,
        status=status,
        actor_subject=actor_subject,
        model_id=model_id,
        source_uri=source_uri,
        target_path=target_path,
        expected_sha256=expected_sha256,
        observed_sha256=None,
        size_bytes=None,
        progress={},
        error=None,
        created_at=now,
        updated_at=now,
    )
