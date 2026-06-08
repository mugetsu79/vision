from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    DeploymentModelAssignmentCreate,
    DeploymentModelAssignmentResponse,
    DeploymentModelInventoryReport,
    EdgeConfigurationResponse,
    EdgeConfigurationUpdate,
    TenantContext,
)
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import (
    DeploymentModelAssignmentStatus,
    EdgeConfigurationApplyStatus,
    RoleEnum,
)

NODE_ID = UUID("00000000-0000-0000-0000-000000000901")
OTHER_NODE_ID = UUID("00000000-0000-0000-0000-000000000902")
MODEL_ID = UUID("00000000-0000-0000-0000-000000000903")
SUPERVISOR_ID = "central-imac-1"
REPORTED_AT = datetime(2026, 6, 8, 9, 0)


def _tenant_context() -> TenantContext:
    tenant_id = UUID("00000000-0000-0000-0000-000000000900")
    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=str(tenant_id),
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
        explicit_tenant_id=None,
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
        if credential_material != "node-credential" or supervisor_id != SUPERVISOR_ID:
            raise ValueError("Invalid supervisor credential.")
        user = AuthenticatedUser(
            subject=f"supervisor:{SUPERVISOR_ID}",
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
    def __init__(self) -> None:
        self.assignment_payload: DeploymentModelAssignmentCreate | None = None
        self.report_payload: DeploymentModelInventoryReport | None = None
        self.edge_configuration_payload: EdgeConfigurationUpdate | None = None
        self.edge_configuration_report: dict[str, object] | None = None
        self.supervisor_node_ids = {SUPERVISOR_ID: NODE_ID}
        self.inventory = DeploymentModelInventoryReport(items=[_inventory_item()])
        self.edge_configuration = _edge_configuration_response(
            tenant_id=UUID("00000000-0000-0000-0000-000000000900"),
            deployment_node_id=NODE_ID,
            revision=1,
            apply_status=EdgeConfigurationApplyStatus.PENDING,
        )

    async def assign_model_to_node(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
        payload: DeploymentModelAssignmentCreate,
        actor_subject: str,
    ) -> DeploymentModelAssignmentResponse:
        del actor_subject
        self.assignment_payload = payload
        return DeploymentModelAssignmentResponse(
            id=uuid4(),
            tenant_id=tenant_id,
            deployment_node_id=deployment_node_id,
            model_id=payload.model_id,
            status=DeploymentModelAssignmentStatus.DESIRED,
            desired_path=payload.desired_path,
            last_sync_job_id=None,
            error=None,
            created_at=REPORTED_AT,
            updated_at=REPORTED_AT,
        )

    async def list_model_inventory(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
    ) -> DeploymentModelInventoryReport:
        del tenant_id, deployment_node_id
        return self.inventory

    async def record_model_inventory(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        payload: DeploymentModelInventoryReport,
    ) -> DeploymentModelInventoryReport:
        del tenant_id
        expected_node_id = self.supervisor_node_ids[supervisor_id]
        if authenticated_node_id is not None and authenticated_node_id != expected_node_id:
            raise PermissionError(
                "Supervisor credential cannot report inventory for another deployment node."
            )
        self.report_payload = payload
        self.inventory = payload
        return payload

    async def get_edge_configuration(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
    ) -> EdgeConfigurationResponse:
        del tenant_id
        if deployment_node_id != self.edge_configuration.deployment_node_id:
            raise ValueError("Edge configuration assignment not found.")
        return self.edge_configuration

    async def update_edge_configuration(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
        payload: EdgeConfigurationUpdate,
        actor_subject: str,
    ) -> EdgeConfigurationResponse:
        del actor_subject
        self.edge_configuration_payload = payload
        self.edge_configuration = _edge_configuration_response(
            tenant_id=tenant_id,
            deployment_node_id=deployment_node_id,
            revision=self.edge_configuration.revision + 1,
            apply_status=EdgeConfigurationApplyStatus.PENDING,
            desired_config=payload.desired_config,
        )
        return self.edge_configuration

    async def get_supervisor_edge_configuration(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
    ) -> EdgeConfigurationResponse:
        del tenant_id
        expected_node_id = self.supervisor_node_ids[supervisor_id]
        if authenticated_node_id is not None and authenticated_node_id != expected_node_id:
            raise PermissionError(
                "Supervisor credential cannot manage edge configuration for another "
                "deployment node."
            )
        return self.edge_configuration

    async def record_edge_configuration_apply_report(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        revision: int,
        status: EdgeConfigurationApplyStatus,
        error: str | None,
    ) -> EdgeConfigurationResponse:
        del tenant_id
        expected_node_id = self.supervisor_node_ids[supervisor_id]
        if authenticated_node_id is not None and authenticated_node_id != expected_node_id:
            raise PermissionError(
                "Supervisor credential cannot manage edge configuration for another "
                "deployment node."
            )
        self.edge_configuration_report = {
            "revision": revision,
            "status": status,
            "error": error,
        }
        self.edge_configuration = _edge_configuration_response(
            tenant_id=self.edge_configuration.tenant_id,
            deployment_node_id=self.edge_configuration.deployment_node_id,
            revision=revision,
            apply_status=status,
            desired_config=self.edge_configuration.desired_config,
            applied_revision=revision if status is EdgeConfigurationApplyStatus.APPLIED else None,
        )
        return self.edge_configuration


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
async def test_admin_can_assign_model_to_node() -> None:
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService()
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/nodes/{NODE_ID}/model-assignments",
            headers={"Authorization": "Bearer token"},
            json={"model_id": str(MODEL_ID)},
        )

    assert response.status_code == 201
    assert response.json()["model_id"] == str(MODEL_ID)
    assert model_lifecycle.assignment_payload is not None


@pytest.mark.asyncio
async def test_admin_can_list_node_inventory() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeModelLifecycleService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/deployment/nodes/{NODE_ID}/model-inventory",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["asset_id"] == str(MODEL_ID)
    assert body["items"][0]["sha256"] == "a" * 64


@pytest.mark.asyncio
async def test_admin_can_update_and_get_edge_configuration() -> None:
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService()
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        update_response = await client.put(
            f"/api/v1/deployment/nodes/{NODE_ID}/edge-configuration",
            headers={"Authorization": "Bearer token"},
            json={"desired_config": {"model_store_path": "/srv/vezor/models"}},
        )
        get_response = await client.get(
            f"/api/v1/deployment/nodes/{NODE_ID}/edge-configuration",
            headers={"Authorization": "Bearer token"},
        )

    assert update_response.status_code == 200
    assert get_response.status_code == 200
    assert update_response.json()["desired_config"]["model_store_path"] == (
        "/srv/vezor/models"
    )
    assert model_lifecycle.edge_configuration_payload is not None


@pytest.mark.asyncio
async def test_supervisor_can_report_own_inventory() -> None:
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService()
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-inventory",
            headers={"Authorization": "Bearer node-credential"},
            json={"items": [_inventory_item_json()]},
        )

    assert response.status_code == 201
    assert model_lifecycle.report_payload is not None


@pytest.mark.asyncio
async def test_supervisor_can_fetch_and_report_own_edge_configuration() -> None:
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService()
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        get_response = await client.get(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/edge-configuration",
            headers={"Authorization": "Bearer node-credential"},
        )
        report_response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/edge-configuration/apply-report",
            headers={"Authorization": "Bearer node-credential"},
            json={"revision": 1, "status": "applied", "error": None},
        )

    assert get_response.status_code == 200
    assert report_response.status_code == 200
    assert report_response.json()["apply_status"] == "applied"
    assert model_lifecycle.edge_configuration_report == {
        "revision": 1,
        "status": EdgeConfigurationApplyStatus.APPLIED,
        "error": None,
    }


@pytest.mark.asyncio
async def test_supervisor_cannot_report_other_node_edge_configuration() -> None:
    context = _tenant_context()
    app = _create_app(
        context,
        _FakeModelLifecycleService(),
        credential_node_id=OTHER_NODE_ID,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/edge-configuration/apply-report",
            headers={"Authorization": "Bearer node-credential"},
            json={"revision": 1, "status": "applied"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_supervisor_cannot_report_other_node_inventory() -> None:
    context = _tenant_context()
    app = _create_app(
        context,
        _FakeModelLifecycleService(),
        credential_node_id=OTHER_NODE_ID,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-inventory",
            headers={"Authorization": "Bearer node-credential"},
            json={"items": [_inventory_item_json()]},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_supervisor_inventory_report_fails_closed_for_malformed_node_claim() -> None:
    context = _tenant_context()
    app = _create_app(
        context,
        _FakeModelLifecycleService(),
        credential_node_id="not-a-uuid",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-inventory",
            headers={"Authorization": "Bearer node-credential"},
            json={"items": [_inventory_item_json()]},
        )

    assert response.status_code == 403


def _inventory_item() -> dict[str, object]:
    return _inventory_item_json()


def _edge_configuration_response(
    *,
    tenant_id: UUID,
    deployment_node_id: UUID,
    revision: int,
    apply_status: EdgeConfigurationApplyStatus,
    desired_config: dict[str, object] | None = None,
    applied_revision: int | None = None,
) -> EdgeConfigurationResponse:
    return EdgeConfigurationResponse(
        id=uuid4(),
        tenant_id=tenant_id,
        deployment_node_id=deployment_node_id,
        revision=revision,
        desired_config=desired_config or {"model_store_path": "/var/lib/vezor/models"},
        applied_revision=applied_revision,
        apply_status=apply_status,
        last_applied_at=REPORTED_AT if applied_revision is not None else None,
        error=None,
        created_at=REPORTED_AT,
        updated_at=REPORTED_AT,
    )


def _inventory_item_json() -> dict[str, object]:
    return {
        "asset_kind": "model",
        "asset_id": str(MODEL_ID),
        "local_path": "/var/lib/vezor/models/yolo26n.onnx",
        "sha256": "a" * 64,
        "size_bytes": 12_345,
        "target_profile": "linux-aarch64-nvidia-jetson",
        "runtime_versions": {"onnxruntime": "1.20.0"},
        "reported_at": REPORTED_AT.isoformat(),
    }
