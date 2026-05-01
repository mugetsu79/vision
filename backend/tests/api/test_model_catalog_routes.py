from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import ModelCatalogEntryResponse, TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import DetectorCapability, ModelFormat, ModelTask, RoleEnum


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
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
    async def list_catalog_status(self) -> list[ModelCatalogEntryResponse]:
        return [
            ModelCatalogEntryResponse(
                id="yolo26n-coco-onnx",
                name="YOLO26n COCO",
                version="2026.1",
                task=ModelTask.DETECT,
                path_hint="models/yolo26n.onnx",
                format=ModelFormat.ONNX,
                capability=DetectorCapability.FIXED_VOCAB,
                capability_config={"runtime_backend": "onnxruntime", "readiness": "ready"},
                classes=[],
                input_shape={"width": 640, "height": 640},
                registration_state="unregistered",
                registered_model_id=None,
                artifact_exists=False,
                note="Default fast detector.",
            )
        ]


def _create_app(context: TenantContext) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        models=_FakeModelService(),
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_model_catalog_route_returns_entries() -> None:
    context = _tenant_context()
    app = _create_app(context)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/model-catalog",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "yolo26n-coco-onnx"
    assert body[0]["capability"] == "fixed_vocab"
