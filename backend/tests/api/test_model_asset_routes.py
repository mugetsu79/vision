from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum

TENANT_ID = UUID("00000000-0000-0000-0000-000000002000")
NODE_ID = UUID("00000000-0000-0000-0000-000000002001")
OTHER_NODE_ID = UUID("00000000-0000-0000-0000-000000002002")
MODEL_ID = UUID("00000000-0000-0000-0000-000000002003")


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=TENANT_ID,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=str(TENANT_ID),
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
        del user, explicit_tenant_id
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        authorization = request.headers.get("Authorization")
        if authorization is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token.",
            )
        if authorization == "Bearer node-credential":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer is not trusted.",
            )
        return self.user


class _FakeDeploymentService:
    def __init__(
        self,
        context: TenantContext,
        credential_node_id: UUID | str | None = NODE_ID,
    ) -> None:
        self.context = context
        self.credential_node_id = credential_node_id

    async def authenticate_supervisor_credential(
        self,
        *,
        credential_material: str,
        supervisor_id: str | None = None,
    ) -> TenantContext:
        del supervisor_id
        if credential_material != "node-credential":
            raise ValueError("Invalid supervisor credential.")
        user = AuthenticatedUser(
            subject="supervisor:edge-supervisor-1",
            email=None,
            role=RoleEnum.OPERATOR,
            issuer="vezor-node-credential",
            realm=self.context.tenant_slug,
            is_superadmin=False,
            tenant_context=str(self.context.tenant_id),
            claims={
                "auth_type": "supervisor_node_credential",
                **(
                    {"deployment_node_id": str(self.credential_node_id)}
                    if self.credential_node_id is not None
                    else {}
                ),
            },
        )
        return TenantContext(
            tenant_id=self.context.tenant_id,
            tenant_slug=self.context.tenant_slug,
            user=user,
        )


class _FakeModelLifecycleService:
    def __init__(self, path) -> None:  # noqa: ANN001
        self.path = path
        self.authenticated_node_id: UUID | None = None

    async def get_model_asset_download(
        self,
        *,
        tenant_id: UUID,
        asset_id: UUID,
        authenticated_node_id: UUID | None,
    ):
        del tenant_id
        if asset_id != MODEL_ID:
            raise ValueError("Model asset not found.")
        self.authenticated_node_id = authenticated_node_id
        if authenticated_node_id == OTHER_NODE_ID:
            raise PermissionError("Model asset is not assigned to this deployment node.")
        return SimpleNamespace(path=self.path, filename="yolo26n.onnx")


def _create_app(
    context: TenantContext,
    model_lifecycle: _FakeModelLifecycleService,
    *,
    credential_node_id: UUID = NODE_ID,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        deployment=_FakeDeploymentService(context, credential_node_id=credential_node_id),
        model_lifecycle=model_lifecycle,
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_admin_can_download_model_asset(tmp_path) -> None:  # noqa: ANN001
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"model-bytes")
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService(model_path)
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/model-assets/{MODEL_ID}/download",
            headers={"Authorization": "Bearer admin-token"},
        )

    assert response.status_code == 200
    assert response.content == b"model-bytes"
    assert model_lifecycle.authenticated_node_id is None


@pytest.mark.asyncio
async def test_supervisor_can_download_assigned_model_asset(tmp_path) -> None:  # noqa: ANN001
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"model-bytes")
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService(model_path)
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/model-assets/{MODEL_ID}/download",
            headers={"Authorization": "Bearer node-credential"},
        )

    assert response.status_code == 200
    assert response.content == b"model-bytes"
    assert model_lifecycle.authenticated_node_id == NODE_ID


@pytest.mark.asyncio
async def test_supervisor_cannot_download_unassigned_model_asset(tmp_path) -> None:  # noqa: ANN001
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"model-bytes")
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService(model_path)
    app = _create_app(
        context,
        model_lifecycle,
        credential_node_id=OTHER_NODE_ID,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/model-assets/{MODEL_ID}/download",
            headers={"Authorization": "Bearer node-credential"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_supervisor_model_asset_download_fails_closed_for_malformed_node_claim(
    tmp_path,
) -> None:
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"model-bytes")
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService(model_path)
    app = _create_app(
        context,
        model_lifecycle,
        credential_node_id="not-a-uuid",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/model-assets/{MODEL_ID}/download",
            headers={"Authorization": "Bearer node-credential"},
        )

    assert response.status_code == 403
