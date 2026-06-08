from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    DeploymentModelSyncJobResponse,
    SupervisorModelJobComplete,
    SupervisorModelJobEventCreate,
    TenantContext,
)
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import ModelLifecycleJobStatus, RoleEnum

TENANT_ID = UUID("00000000-0000-0000-0000-000000001000")
NODE_ID = UUID("00000000-0000-0000-0000-000000001001")
OTHER_NODE_ID = UUID("00000000-0000-0000-0000-000000001002")
ASSIGNMENT_ID = UUID("00000000-0000-0000-0000-000000001003")
MODEL_ID = UUID("00000000-0000-0000-0000-000000001004")
JOB_ID = UUID("00000000-0000-0000-0000-000000001005")
SUPERVISOR_ID = "central-imac-1"
REPORTED_AT = datetime(2026, 6, 8, 9, 0)


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
    def __init__(self, context: TenantContext, credential_node_id: UUID = NODE_ID) -> None:
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
                "deployment_node_id": str(self.credential_node_id),
            },
        )
        return TenantContext(
            tenant_id=self.context.tenant_id,
            tenant_slug=self.context.tenant_slug,
            user=user,
        )


class _FakeModelLifecycleService:
    def __init__(self) -> None:
        self.created_node_id: UUID | None = None
        self.polled_authenticated_node_id: UUID | None = None
        self.polled_limit: int | None = None
        self.event_payload: SupervisorModelJobEventCreate | None = None
        self.complete_payload: SupervisorModelJobComplete | None = None

    async def create_model_sync_job(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
        actor_subject: str,
    ) -> DeploymentModelSyncJobResponse:
        del actor_subject
        self.created_node_id = deployment_node_id
        return _sync_job_response(
            tenant_id=tenant_id,
            deployment_node_id=deployment_node_id,
            status=ModelLifecycleJobStatus.QUEUED,
        )

    async def poll_supervisor_model_jobs(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        limit: int,
    ) -> list[DeploymentModelSyncJobResponse]:
        del supervisor_id
        self._require_node(authenticated_node_id)
        self.polled_authenticated_node_id = authenticated_node_id
        self.polled_limit = limit
        return [
            _sync_job_response(
                tenant_id=tenant_id,
                deployment_node_id=NODE_ID,
                status=ModelLifecycleJobStatus.ACCEPTED,
                claimed_by_supervisor_id=SUPERVISOR_ID,
            )
        ]

    async def record_supervisor_model_job_event(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        job_id: UUID,
        payload: SupervisorModelJobEventCreate,
    ) -> DeploymentModelSyncJobResponse:
        del supervisor_id, job_id
        self._require_node(authenticated_node_id)
        self.event_payload = payload
        return _sync_job_response(
            tenant_id=tenant_id,
            deployment_node_id=NODE_ID,
            status=payload.status,
        )

    async def complete_supervisor_model_job(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        job_id: UUID,
        payload: SupervisorModelJobComplete,
    ) -> DeploymentModelSyncJobResponse:
        del supervisor_id, job_id
        self._require_node(authenticated_node_id)
        self.complete_payload = payload
        return _sync_job_response(
            tenant_id=tenant_id,
            deployment_node_id=NODE_ID,
            status=payload.status,
        )

    def _require_node(self, authenticated_node_id: UUID | None) -> None:
        if authenticated_node_id != NODE_ID:
            raise PermissionError(
                "Supervisor credential cannot manage model jobs for another deployment node."
            )


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
async def test_admin_can_create_model_sync_job_for_node() -> None:
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService()
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/nodes/{NODE_ID}/model-sync-jobs",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    assert response.json()["deployment_node_id"] == str(NODE_ID)
    assert model_lifecycle.created_node_id == NODE_ID


@pytest.mark.asyncio
async def test_supervisor_can_poll_model_jobs_with_node_credential() -> None:
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService()
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-jobs/poll",
            headers={"Authorization": "Bearer node-credential"},
            json={"limit": 5},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["supervisor_id"] == SUPERVISOR_ID
    assert body["jobs"][0]["status"] == "accepted"
    assert model_lifecycle.polled_authenticated_node_id == NODE_ID
    assert model_lifecycle.polled_limit == 5


@pytest.mark.asyncio
async def test_supervisor_can_record_model_job_event_with_node_credential() -> None:
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService()
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-jobs/{JOB_ID}/events",
            headers={"Authorization": "Bearer node-credential"},
            json={
                "job_kind": "model_sync",
                "status": "running",
                "message": "copy started",
                "payload": {"progress": 0.25},
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "running"
    assert model_lifecycle.event_payload is not None
    assert model_lifecycle.event_payload.payload == {"progress": 0.25}


@pytest.mark.asyncio
async def test_supervisor_can_complete_model_job_with_node_credential() -> None:
    context = _tenant_context()
    model_lifecycle = _FakeModelLifecycleService()
    app = _create_app(context, model_lifecycle)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-jobs/{JOB_ID}/complete",
            headers={"Authorization": "Bearer node-credential"},
            json={
                "status": "succeeded",
                "local_path": "/var/lib/vezor/models/yolo26n.onnx",
                "sha256": "a" * 64,
                "size_bytes": 12_345,
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert model_lifecycle.complete_payload is not None
    assert model_lifecycle.complete_payload.sha256 == "a" * 64


@pytest.mark.asyncio
async def test_wrong_node_supervisor_credential_returns_403_for_model_job_routes() -> None:
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
        poll_response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-jobs/poll",
            headers={"Authorization": "Bearer node-credential"},
            json={"limit": 5},
        )
        event_response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-jobs/{JOB_ID}/events",
            headers={"Authorization": "Bearer node-credential"},
            json={
                "job_kind": "model_sync",
                "status": "running",
                "message": "copy started",
                "payload": {},
            },
        )
        complete_response = await client.post(
            f"/api/v1/deployment/supervisors/{SUPERVISOR_ID}/model-jobs/{JOB_ID}/complete",
            headers={"Authorization": "Bearer node-credential"},
            json={
                "status": "failed",
                "error": "wrong node",
            },
        )

    assert poll_response.status_code == 403
    assert event_response.status_code == 403
    assert complete_response.status_code == 403


def _sync_job_response(
    *,
    tenant_id: UUID,
    deployment_node_id: UUID,
    status: ModelLifecycleJobStatus,
    claimed_by_supervisor_id: str | None = None,
) -> DeploymentModelSyncJobResponse:
    return DeploymentModelSyncJobResponse(
        id=JOB_ID,
        tenant_id=tenant_id,
        deployment_node_id=deployment_node_id,
        assignment_id=ASSIGNMENT_ID,
        model_id=MODEL_ID,
        status=status,
        payload={
            "job_type": "model_sync",
            "schema_version": 1,
            "deployment_node_id": str(deployment_node_id),
            "model_id": str(MODEL_ID),
            "model_name": "YOLO26n COCO",
            "source_path": "models/yolo26n.onnx",
            "expected_sha256": "a" * 64,
            "size_bytes": 12_345,
            "target_path": "/var/lib/vezor/models/yolo26n.onnx",
        },
        claimed_by_supervisor_id=claimed_by_supervisor_id,
        claimed_at=REPORTED_AT if claimed_by_supervisor_id is not None else None,
        completed_at=REPORTED_AT if status is ModelLifecycleJobStatus.SUCCEEDED else None,
        error=None,
        created_at=REPORTED_AT,
        updated_at=REPORTED_AT,
    )
