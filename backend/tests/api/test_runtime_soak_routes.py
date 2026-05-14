from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    RuntimeArtifactSoakRunCreate,
    RuntimeArtifactSoakRunResponse,
    TenantContext,
)
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import (
    DetectorCapability,
    ModelAdmissionStatus,
    RoleEnum,
    RuntimeArtifactKind,
    RuntimeArtifactSoakStatus,
)


def _tenant_context(role: RoleEnum = RoleEnum.ADMIN) -> TenantContext:
    return TenantContext(
        tenant_id=UUID("00000000-0000-0000-0000-000000000101"),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=role,
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
        explicit_tenant_id=None,
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        if request.headers.get("Authorization") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token.",
            )
        return self.user


class _FakeRuntimeSoakService:
    def __init__(self) -> None:
        self.created_payload: RuntimeArtifactSoakRunCreate | None = None
        self.list_artifact_id: UUID | None = None

    async def record_soak_run(
        self,
        *,
        tenant_id: UUID,
        payload: RuntimeArtifactSoakRunCreate,
    ) -> RuntimeArtifactSoakRunResponse:
        self.created_payload = payload
        return _soak_response(tenant_id=tenant_id, payload=payload)

    async def list_soak_runs(
        self,
        *,
        tenant_id: UUID,
        runtime_artifact_id: UUID | None = None,
        edge_node_id: UUID | None = None,
        limit: int = 50,
    ) -> list[RuntimeArtifactSoakRunResponse]:
        del edge_node_id, limit
        self.list_artifact_id = runtime_artifact_id
        return [
            _soak_response(
                tenant_id=tenant_id,
                payload=RuntimeArtifactSoakRunCreate(
                    edge_node_id=UUID("00000000-0000-0000-0000-000000000102"),
                    runtime_artifact_id=runtime_artifact_id or uuid4(),
                    runtime_selection_profile_id=UUID(
                        "00000000-0000-0000-0000-000000000103"
                    ),
                    status=RuntimeArtifactSoakStatus.PASSED,
                    started_at=datetime(2026, 5, 14, 8, 0, tzinfo=UTC),
                    ended_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
                    metrics={"duration_minutes": 60},
                    notes="Track A/B Jetson soak evidence.",
                ),
            )
        ]


def _create_app(context: TenantContext, runtime_soak: _FakeRuntimeSoakService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        runtime_soak=runtime_soak,
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_runtime_soak_create_route_records_jetson_soak_context() -> None:
    context = _tenant_context()
    runtime_soak = _FakeRuntimeSoakService()
    app = _create_app(context, runtime_soak)
    artifact_id = UUID("00000000-0000-0000-0000-000000000201")
    edge_node_id = UUID("00000000-0000-0000-0000-000000000202")
    assignment_id = UUID("00000000-0000-0000-0000-000000000203")
    profile_id = UUID("00000000-0000-0000-0000-000000000204")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/runtime-artifacts/soak-runs",
            headers={"Authorization": "Bearer token"},
            json={
                "edge_node_id": str(edge_node_id),
                "runtime_artifact_id": str(artifact_id),
                "operations_assignment_id": str(assignment_id),
                "runtime_selection_profile_id": str(profile_id),
                "status": "passed",
                "started_at": "2026-05-14T08:00:00Z",
                "ended_at": "2026-05-14T09:00:00Z",
                "metrics": {"fps_p50": 10.2, "worker_restarts": 0},
                "fallback_reason": None,
                "notes": "Fixed-vocab YOLO26n TensorRT Jetson soak passed.",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["runtime_artifact_id"] == str(artifact_id)
    assert body["runtime_kind"] == "tensorrt_engine"
    assert body["target_profile"] == "linux-aarch64-nvidia-jetson"
    assert body["status"] == "passed"
    assert body["metrics"]["fps_p50"] == 10.2
    assert body["operations_assignment_id"] == str(assignment_id)
    assert body["runtime_selection_profile_id"] == str(profile_id)
    assert body["runtime_selection_profile_hash"] == "c" * 64
    assert body["hardware_admission_status"] == "recommended"
    assert "frame budget" in body["model_recommendation_rationale"]
    assert runtime_soak.created_payload is not None
    assert runtime_soak.created_payload.runtime_artifact_id == artifact_id


@pytest.mark.asyncio
async def test_runtime_soak_list_route_filters_by_artifact() -> None:
    context = _tenant_context()
    runtime_soak = _FakeRuntimeSoakService()
    app = _create_app(context, runtime_soak)
    artifact_id = UUID("00000000-0000-0000-0000-000000000201")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/runtime-artifacts/soak-runs?runtime_artifact_id={artifact_id}",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["runtime_artifact_id"] == str(artifact_id)
    assert body[0]["notes"] == "Track A/B Jetson soak evidence."
    assert runtime_soak.list_artifact_id == artifact_id


@pytest.mark.asyncio
async def test_runtime_soak_routes_reject_non_admin_create() -> None:
    context = _tenant_context(RoleEnum.VIEWER)
    runtime_soak = _FakeRuntimeSoakService()
    app = _create_app(context, runtime_soak)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/runtime-artifacts/soak-runs",
            headers={"Authorization": "Bearer token"},
            json={
                "runtime_artifact_id": str(uuid4()),
                "status": "passed",
                "started_at": "2026-05-14T08:00:00Z",
                "metrics": {},
            },
        )

    assert response.status_code == 403
    assert runtime_soak.created_payload is None


def _soak_response(
    *,
    tenant_id: UUID,
    payload: RuntimeArtifactSoakRunCreate,
) -> RuntimeArtifactSoakRunResponse:
    return RuntimeArtifactSoakRunResponse(
        id=UUID("00000000-0000-0000-0000-000000000301"),
        tenant_id=tenant_id,
        edge_node_id=payload.edge_node_id,
        camera_id=UUID("00000000-0000-0000-0000-000000000302"),
        runtime_artifact_id=payload.runtime_artifact_id,
        runtime_kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        runtime_backend="tensorrt_engine",
        model_id=UUID("00000000-0000-0000-0000-000000000303"),
        model_name="YOLO26n COCO Edge",
        model_capability=DetectorCapability.FIXED_VOCAB,
        target_profile="linux-aarch64-nvidia-jetson",
        status=payload.status,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        metrics=payload.metrics,
        fallback_reason=payload.fallback_reason,
        notes=payload.notes,
        operations_assignment_id=payload.operations_assignment_id,
        runtime_selection_profile_id=payload.runtime_selection_profile_id,
        runtime_selection_profile_hash="c" * 64,
        hardware_report_id=UUID("00000000-0000-0000-0000-000000000304"),
        model_admission_report_id=UUID("00000000-0000-0000-0000-000000000305"),
        hardware_admission_status=ModelAdmissionStatus.RECOMMENDED,
        model_recommendation_rationale="TensorRT p95 total fits the frame budget.",
        created_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
    )
