from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    EdgeNodeHardwareReportResponse,
    FleetBootstrapRequest,
    FleetBootstrapResponse,
    FleetCameraWorkerSummary,
    FleetOverviewResponse,
    FleetSummary,
    HardwarePerformanceSample,
    LifecycleRequestClaim,
    LifecycleRequestCompletion,
    NodeCredentialRotateResponse,
    OperationalMemoryPatternResponse,
    OperationsLifecycleRequestCreate,
    OperationsLifecycleRequestResponse,
    RuntimePassportSummary,
    SupervisorPollRequest,
    SupervisorPollResponse,
    SupervisorRuntimeReportCreate,
    SupervisorRuntimeReportResponse,
    TenantContext,
    WorkerAssignmentCreate,
    WorkerAssignmentResponse,
    WorkerModelAdmissionRequest,
    WorkerModelAdmissionResponse,
)
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import ModelAdmissionStatus, ProcessingMode, RoleEnum


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
        explicit_tenant_id=None,
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        if request.headers.get("Authorization") == "Bearer node-credential":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer is not trusted.",
            )
        return self.user


class _FakeDeploymentService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context
        self.credential_material: str | None = None
        self.supervisor_id: str | None = None
        self.revoked_credentials: set[str] = set()

    async def authenticate_supervisor_credential(
        self,
        *,
        credential_material: str,
        supervisor_id: str | None = None,
    ) -> TenantContext:
        self.credential_material = credential_material
        self.supervisor_id = supervisor_id
        if (
            credential_material in self.revoked_credentials
            or credential_material != "node-credential"
        ):
            raise ValueError("Invalid supervisor credential.")
        return TenantContext(
            tenant_id=self.context.tenant_id,
            tenant_slug=self.context.tenant_slug,
            user=AuthenticatedUser(
                subject="supervisor:edge-supervisor-1",
                email=None,
                role=RoleEnum.OPERATOR,
                issuer="vezor-node-credential",
                realm=self.context.tenant_slug,
                is_superadmin=False,
                tenant_context=str(self.context.tenant_id),
                claims={"auth_type": "supervisor_node_credential"},
            ),
        )


class _FakeOperationsService:
    def __init__(self) -> None:
        self.bootstrap_payload: FleetBootstrapRequest | None = None
        self.assignment_payload: WorkerAssignmentCreate | None = None
        self.runtime_report_payload: SupervisorRuntimeReportCreate | None = None
        self.lifecycle_payload: OperationsLifecycleRequestCreate | None = None
        self.poll_payload: SupervisorPollRequest | None = None
        self.claim_payload: LifecycleRequestClaim | None = None
        self.completion_payload: LifecycleRequestCompletion | None = None
        self.hardware_payload: EdgeNodeHardwareReportCreate | None = None
        self.admission_payload: WorkerModelAdmissionRequest | None = None
        self.rotated_edge_node_id: UUID | None = None
        self.deployment: _FakeDeploymentService | None = None

    async def get_fleet_overview(self, tenant_context: TenantContext) -> FleetOverviewResponse:
        return FleetOverviewResponse(
            mode="manual_dev",
            generated_at=datetime(2026, 4, 28, 7, 0, tzinfo=UTC),
            summary=FleetSummary(
                desired_workers=1,
                running_workers=0,
                stale_nodes=0,
                offline_nodes=0,
                native_unavailable_cameras=0,
            ),
            nodes=[],
            camera_workers=[
                FleetCameraWorkerSummary(
                    camera_id=UUID("00000000-0000-0000-0000-000000000321"),
                    camera_name="Dock Camera",
                    site_id=UUID("00000000-0000-0000-0000-000000000456"),
                    node_id=None,
                    node_hostname=None,
                    processing_mode=ProcessingMode.EDGE,
                    desired_state="manual",
                    runtime_status="running",
                    lifecycle_owner="manual_dev",
                    runtime_passport=RuntimePassportSummary(
                        id=UUID("00000000-0000-0000-0000-000000000654"),
                        passport_hash="e" * 64,
                        selected_backend="tensorrt_engine",
                        model_hash="f" * 64,
                        runtime_artifact_hash="d" * 64,
                        target_profile="linux-aarch64-nvidia-jetson",
                        precision="fp16",
                        validated_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
                        fallback_reason=None,
                    ),
                    rule_runtime={
                        "configured_rule_count": 2,
                        "effective_rule_hash": "c" * 64,
                        "latest_rule_event_at": datetime(
                            2026,
                            5,
                            12,
                            9,
                            30,
                            tzinfo=UTC,
                        ),
                        "load_status": "loaded",
                    },
                )
            ],
            delivery_diagnostics=[],
        )

    async def list_memory_patterns(
        self,
        tenant_context: TenantContext,
        *,
        incident_id=None,
        camera_id=None,
        site_id=None,
        limit: int = 20,
    ) -> list[OperationalMemoryPatternResponse]:
        return [
            OperationalMemoryPatternResponse(
                id=UUID("00000000-0000-0000-0000-000000000901"),
                tenant_id=tenant_context.tenant_id,
                site_id=site_id or UUID("00000000-0000-0000-0000-000000000456"),
                camera_id=camera_id or UUID("00000000-0000-0000-0000-000000000321"),
                pattern_type="event_burst",
                severity="warning",
                summary="Observed pattern: 3 incidents in one zone.",
                window_started_at=datetime(2026, 5, 12, 8, 0, tzinfo=UTC),
                window_ended_at=datetime(2026, 5, 12, 8, 15, tzinfo=UTC),
                source_incident_ids=[
                    incident_id or UUID("00000000-0000-0000-0000-000000000701")
                ],
                source_contract_hashes=["a" * 64],
                dimensions={"zone_id": "server-room"},
                evidence={"incident_count": 3},
                pattern_hash="b" * 64,
                created_at=datetime(2026, 5, 12, 8, 20, tzinfo=UTC),
            )
        ][:limit]

    async def create_bootstrap_material(
        self,
        tenant_context: TenantContext,
        payload: FleetBootstrapRequest,
    ) -> FleetBootstrapResponse:
        self.bootstrap_payload = payload
        return FleetBootstrapResponse(
            edge_node_id=UUID("00000000-0000-0000-0000-000000000123"),
            api_key="edge_secret_once",
            nats_nkey_seed="nats_secret_once",
            subjects=["evt.tracking.00000000-0000-0000-0000-000000000123"],
            mediamtx_url="http://mediamtx:9997",
            overlay_network_hints={"nats_url": "nats://nats:4222"},
            dev_compose_command=(
                "ARGUS_EDGE_CAMERA_ID=<camera-id> "
                "docker compose -f infra/docker-compose.edge.yml up inference-worker"
            ),
            supervisor_environment={
                "ARGUS_API_BASE_URL": "http://argus-backend:8000",
                "ARGUS_EDGE_NODE_ID": "00000000-0000-0000-0000-000000000123",
            },
        )

    async def create_worker_assignment(
        self,
        tenant_context: TenantContext,
        payload: WorkerAssignmentCreate,
    ) -> WorkerAssignmentResponse:
        self.assignment_payload = payload
        return WorkerAssignmentResponse(
            id=UUID("00000000-0000-0000-0000-000000000811"),
            tenant_id=tenant_context.tenant_id,
            camera_id=payload.camera_id,
            edge_node_id=payload.edge_node_id,
            desired_state=payload.desired_state,
            active=True,
            supersedes_assignment_id=None,
            assigned_by_subject=tenant_context.user.subject,
            created_at=datetime(2026, 5, 13, 8, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, 8, 0, tzinfo=UTC),
        )

    async def record_worker_runtime_report(
        self,
        tenant_context: TenantContext,
        payload: SupervisorRuntimeReportCreate,
    ) -> SupervisorRuntimeReportResponse:
        self.runtime_report_payload = payload
        return SupervisorRuntimeReportResponse(
            id=UUID("00000000-0000-0000-0000-000000000812"),
            tenant_id=tenant_context.tenant_id,
            camera_id=payload.camera_id,
            edge_node_id=payload.edge_node_id,
            assignment_id=payload.assignment_id,
            heartbeat_at=payload.heartbeat_at,
            runtime_state=payload.runtime_state,
            restart_count=payload.restart_count,
            last_error=payload.last_error,
            runtime_artifact_id=payload.runtime_artifact_id,
            scene_contract_hash=payload.scene_contract_hash,
            created_at=datetime(2026, 5, 13, 8, 1, tzinfo=UTC),
        )

    async def create_lifecycle_request(
        self,
        tenant_context: TenantContext,
        payload: OperationsLifecycleRequestCreate,
    ) -> OperationsLifecycleRequestResponse:
        self.lifecycle_payload = payload
        return OperationsLifecycleRequestResponse(
            id=UUID("00000000-0000-0000-0000-000000000813"),
            tenant_id=tenant_context.tenant_id,
            camera_id=payload.camera_id,
            edge_node_id=payload.edge_node_id,
            assignment_id=payload.assignment_id,
            action=payload.action,
            status="requested",
            requested_by_subject=tenant_context.user.subject,
            requested_at=datetime(2026, 5, 13, 8, 2, tzinfo=UTC),
            acknowledged_at=None,
            completed_at=None,
            error=None,
            request_payload=payload.request_payload,
            created_at=datetime(2026, 5, 13, 8, 2, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, 8, 2, tzinfo=UTC),
        )

    async def poll_supervisor_lifecycle_requests(
        self,
        tenant_context: TenantContext,
        supervisor_id: str,
        payload: SupervisorPollRequest,
    ) -> SupervisorPollResponse:
        self.poll_payload = payload
        return SupervisorPollResponse(
            supervisor_id=supervisor_id,
            edge_node_id=payload.edge_node_id,
            requests=[
                OperationsLifecycleRequestResponse(
                    id=UUID("00000000-0000-0000-0000-000000000814"),
                    tenant_id=tenant_context.tenant_id,
                    camera_id=UUID("00000000-0000-0000-0000-000000000321"),
                    edge_node_id=payload.edge_node_id,
                    assignment_id=None,
                    action="start",
                    status="requested",
                    requested_by_subject="operator-1",
                    requested_at=datetime(2026, 5, 13, 8, 3, tzinfo=UTC),
                    acknowledged_at=None,
                    claimed_by_supervisor=None,
                    claimed_at=None,
                    completed_at=None,
                    admission_report_id=None,
                    error=None,
                    request_payload={},
                    created_at=datetime(2026, 5, 13, 8, 3, tzinfo=UTC),
                    updated_at=datetime(2026, 5, 13, 8, 3, tzinfo=UTC),
                )
            ],
        )

    async def claim_lifecycle_request(
        self,
        tenant_context: TenantContext,
        request_id: UUID,
        payload: LifecycleRequestClaim,
    ) -> OperationsLifecycleRequestResponse:
        self.claim_payload = payload
        return OperationsLifecycleRequestResponse(
            id=request_id,
            tenant_id=tenant_context.tenant_id,
            camera_id=UUID("00000000-0000-0000-0000-000000000321"),
            edge_node_id=payload.edge_node_id,
            assignment_id=None,
            action="start",
            status="acknowledged",
            requested_by_subject="operator-1",
            requested_at=datetime(2026, 5, 13, 8, 3, tzinfo=UTC),
            acknowledged_at=datetime(2026, 5, 13, 8, 4, tzinfo=UTC),
            claimed_by_supervisor=payload.supervisor_id,
            claimed_at=datetime(2026, 5, 13, 8, 4, tzinfo=UTC),
            completed_at=None,
            admission_report_id=None,
            error=None,
            request_payload={},
            created_at=datetime(2026, 5, 13, 8, 3, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, 8, 4, tzinfo=UTC),
        )

    async def complete_lifecycle_request(
        self,
        tenant_context: TenantContext,
        request_id: UUID,
        payload: LifecycleRequestCompletion,
    ) -> OperationsLifecycleRequestResponse:
        self.completion_payload = payload
        return OperationsLifecycleRequestResponse(
            id=request_id,
            tenant_id=tenant_context.tenant_id,
            camera_id=UUID("00000000-0000-0000-0000-000000000321"),
            edge_node_id=None,
            assignment_id=None,
            action="start",
            status=payload.status,
            requested_by_subject="operator-1",
            requested_at=datetime(2026, 5, 13, 8, 3, tzinfo=UTC),
            acknowledged_at=datetime(2026, 5, 13, 8, 4, tzinfo=UTC),
            claimed_by_supervisor=payload.supervisor_id,
            claimed_at=datetime(2026, 5, 13, 8, 4, tzinfo=UTC),
            completed_at=datetime(2026, 5, 13, 8, 5, tzinfo=UTC),
            admission_report_id=payload.admission_report_id,
            error=payload.error,
            request_payload={},
            created_at=datetime(2026, 5, 13, 8, 3, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, 8, 5, tzinfo=UTC),
        )

    async def record_hardware_report(
        self,
        tenant_context: TenantContext,
        supervisor_id: str,
        payload: EdgeNodeHardwareReportCreate,
    ) -> EdgeNodeHardwareReportResponse:
        self.hardware_payload = payload
        return _hardware_report_response(
            tenant_id=tenant_context.tenant_id,
            supervisor_id=supervisor_id,
            payload=payload,
        )

    async def latest_hardware_report_for_supervisor(
        self,
        tenant_context: TenantContext,
        supervisor_id: str,
    ) -> EdgeNodeHardwareReportResponse | None:
        return _hardware_report_response(
            tenant_id=tenant_context.tenant_id,
            supervisor_id=supervisor_id,
            payload=_hardware_payload(edge_node_id=None),
        )

    async def latest_hardware_report_for_edge_node(
        self,
        tenant_context: TenantContext,
        edge_node_id: UUID,
    ) -> EdgeNodeHardwareReportResponse | None:
        return _hardware_report_response(
            tenant_id=tenant_context.tenant_id,
            supervisor_id="edge-supervisor-1",
            payload=_hardware_payload(edge_node_id=edge_node_id),
        )

    async def evaluate_worker_model_admission(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: WorkerModelAdmissionRequest,
    ) -> WorkerModelAdmissionResponse:
        self.admission_payload = payload
        return WorkerModelAdmissionResponse(
            id=UUID("00000000-0000-0000-0000-000000000816"),
            tenant_id=tenant_context.tenant_id,
            camera_id=camera_id,
            edge_node_id=payload.edge_node_id,
            assignment_id=payload.assignment_id,
            hardware_report_id=UUID("00000000-0000-0000-0000-000000000815"),
            model_id=payload.model_id,
            model_name=payload.model_name,
            model_capability=payload.model_capability,
            runtime_artifact_id=payload.runtime_artifact_id,
            runtime_selection_profile_id=payload.runtime_selection_profile_id,
            stream_profile=payload.stream_profile,
            status=ModelAdmissionStatus.RECOMMENDED,
            selected_backend=payload.selected_backend,
            recommended_model_id=None,
            recommended_model_name=None,
            recommended_runtime_profile_id=None,
            recommended_backend=payload.selected_backend,
            rationale="CoreML p95 total fits the frame budget.",
            constraints={"frame_budget_ms": 100.0},
            evaluated_at=datetime(2026, 5, 13, 8, 6, tzinfo=UTC),
            created_at=datetime(2026, 5, 13, 8, 6, tzinfo=UTC),
        )

    async def rotate_edge_node_credentials(
        self,
        tenant_context: TenantContext,
        edge_node_id: UUID,
    ) -> NodeCredentialRotateResponse:
        self.rotated_edge_node_id = edge_node_id
        if self.deployment is not None:
            self.deployment.revoked_credentials.add("node-credential")
        return NodeCredentialRotateResponse(
            node_id=UUID("00000000-0000-0000-0000-000000000817"),
            credential_id=UUID("00000000-0000-0000-0000-000000000818"),
            credential_material="vzcred_edge_rotated_once",
            credential_hash="c" * 64,
            credential_version=2,
            revoked_credentials=1,
            credential_status="active",
            node={
                "id": "00000000-0000-0000-0000-000000000817",
                "tenant_id": str(tenant_context.tenant_id),
                "node_kind": "edge",
                "edge_node_id": str(edge_node_id),
                "supervisor_id": "edge-supervisor-1",
                "hostname": "edge-supervisor",
                "install_status": "installed",
                "credential_status": "active",
                "service_manager": None,
                "service_status": None,
                "version": None,
                "os_name": None,
                "host_profile": None,
                "last_service_reported_at": None,
                "diagnostics": {},
                "created_at": "2026-05-13T08:06:00Z",
                "updated_at": "2026-05-13T08:07:00Z",
            },
        )


def _hardware_payload(edge_node_id: UUID | None) -> EdgeNodeHardwareReportCreate:
    return EdgeNodeHardwareReportCreate(
        edge_node_id=edge_node_id,
        reported_at=datetime(2026, 5, 13, 8, 6, tzinfo=UTC),
        host_profile="macos-x86_64-intel",
        os_name="darwin",
        machine_arch="x86_64",
        cpu_model="Intel Core i7",
        cpu_cores=8,
        memory_total_mb=32768,
        accelerators=["coreml"],
        provider_capabilities={"CoreMLExecutionProvider": True},
        observed_performance=[
            HardwarePerformanceSample(
                model_id=UUID("00000000-0000-0000-0000-000000000611"),
                model_name="YOLO26n COCO",
                runtime_backend="CoreMLExecutionProvider",
                input_width=1280,
                input_height=720,
                target_fps=10.0,
                observed_fps=10.0,
                stage_p95_ms={"total": 92.0},
                stage_p99_ms={"total": 118.0},
            )
        ],
        thermal_state="nominal",
    )


def _hardware_report_response(
    *,
    tenant_id: UUID,
    supervisor_id: str,
    payload: EdgeNodeHardwareReportCreate,
) -> EdgeNodeHardwareReportResponse:
    return EdgeNodeHardwareReportResponse(
        id=UUID("00000000-0000-0000-0000-000000000815"),
        tenant_id=tenant_id,
        edge_node_id=payload.edge_node_id,
        supervisor_id=supervisor_id,
        reported_at=payload.reported_at,
        host_profile=payload.host_profile,
        os_name=payload.os_name,
        machine_arch=payload.machine_arch,
        cpu_model=payload.cpu_model,
        cpu_cores=payload.cpu_cores,
        memory_total_mb=payload.memory_total_mb,
        accelerators=payload.accelerators,
        provider_capabilities=payload.provider_capabilities,
        observed_performance=payload.observed_performance,
        thermal_state=payload.thermal_state,
        report_hash="b" * 64,
        created_at=datetime(2026, 5, 13, 8, 6, tzinfo=UTC),
    )


def _create_app(context: TenantContext, operations: _FakeOperationsService) -> FastAPI:
    app = FastAPI()
    deployment = _FakeDeploymentService(context)
    operations.deployment = deployment
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        operations=operations,
        deployment=deployment,
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_operations_fleet_route_returns_overview() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeOperationsService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/operations/fleet",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "manual_dev"
    assert body["summary"]["desired_workers"] == 1
    assert body["camera_workers"][0]["runtime_passport"]["selected_backend"] == ("tensorrt_engine")
    assert body["camera_workers"][0]["runtime_passport"]["runtime_artifact_hash"] == "d" * 64
    assert body["camera_workers"][0]["rule_runtime"] == {
        "configured_rule_count": 2,
        "effective_rule_hash": "c" * 64,
        "latest_rule_event_at": "2026-05-12T09:30:00Z",
        "load_status": "loaded",
    }


@pytest.mark.asyncio
async def test_operations_memory_patterns_route_returns_observed_patterns() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeOperationsService())
    incident_id = UUID("00000000-0000-0000-0000-000000000701")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/operations/memory-patterns?incident_id={incident_id}",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["pattern_type"] == "event_burst"
    assert body[0]["severity"] == "warning"
    assert body[0]["summary"].startswith("Observed pattern")
    assert body[0]["source_incident_ids"] == [str(incident_id)]
    assert body[0]["source_contract_hashes"] == ["a" * 64]


@pytest.mark.asyncio
async def test_operations_bootstrap_route_returns_one_time_material() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    site_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/operations/bootstrap",
            headers={"Authorization": "Bearer token"},
            json={
                "site_id": str(site_id),
                "hostname": "edge-kit-01",
                "version": "0.1.0",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["api_key"] == "edge_secret_once"
    assert "docker compose" in body["dev_compose_command"]
    assert operations.bootstrap_payload is not None
    assert operations.bootstrap_payload.site_id == site_id


@pytest.mark.asyncio
async def test_worker_assignment_route_creates_assignment_record() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    camera_id = uuid4()
    edge_node_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/operations/worker-assignments",
            headers={"Authorization": "Bearer token"},
            json={
                "camera_id": str(camera_id),
                "edge_node_id": str(edge_node_id),
                "desired_state": "supervised",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["camera_id"] == str(camera_id)
    assert body["edge_node_id"] == str(edge_node_id)
    assert body["active"] is True
    assert operations.assignment_payload is not None
    assert operations.assignment_payload.camera_id == camera_id


@pytest.mark.asyncio
async def test_runtime_report_route_records_supervisor_truth() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    camera_id = uuid4()
    heartbeat_at = datetime(2026, 5, 13, 8, 1, tzinfo=UTC)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/operations/runtime-reports",
            headers={"Authorization": "Bearer token"},
            json={
                "camera_id": str(camera_id),
                "heartbeat_at": heartbeat_at.isoformat(),
                "runtime_state": "running",
                "restart_count": 2,
                "last_error": "previous restart recovered",
                "scene_contract_hash": "a" * 64,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["camera_id"] == str(camera_id)
    assert body["runtime_state"] == "running"
    assert body["restart_count"] == 2
    assert body["last_error"] == "previous restart recovered"
    assert body["scene_contract_hash"] == "a" * 64
    assert operations.runtime_report_payload is not None
    assert operations.runtime_report_payload.camera_id == camera_id


@pytest.mark.asyncio
async def test_lifecycle_request_route_records_intent_without_shelling_out() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/operations/lifecycle-requests",
            headers={"Authorization": "Bearer token"},
            json={
                "camera_id": str(camera_id),
                "action": "restart",
                "request_payload": {"reason": "operator_test"},
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["camera_id"] == str(camera_id)
    assert body["action"] == "restart"
    assert body["status"] == "requested"
    assert body["request_payload"] == {"reason": "operator_test"}
    assert operations.lifecycle_payload is not None
    assert operations.lifecycle_payload.action == "restart"


@pytest.mark.asyncio
async def test_supervisor_poll_route_returns_scoped_lifecycle_requests() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    edge_node_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/operations/supervisors/edge-supervisor-1/poll",
            headers={"Authorization": "Bearer token"},
            json={"edge_node_id": str(edge_node_id), "limit": 5},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["supervisor_id"] == "edge-supervisor-1"
    assert body["edge_node_id"] == str(edge_node_id)
    assert body["requests"][0]["action"] == "start"
    assert operations.poll_payload is not None
    assert operations.poll_payload.edge_node_id == edge_node_id


@pytest.mark.asyncio
async def test_supervisor_operations_accept_node_credential_without_admin_jwt() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    edge_node_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/operations/supervisors/edge-supervisor-1/poll",
            headers={"Authorization": "Bearer node-credential"},
            json={"edge_node_id": str(edge_node_id), "limit": 5},
        )

    assert response.status_code == 200
    assert response.json()["supervisor_id"] == "edge-supervisor-1"
    assert app.state.services.deployment.credential_material == "node-credential"
    assert app.state.services.deployment.supervisor_id == "edge-supervisor-1"


@pytest.mark.asyncio
async def test_edge_credential_rotation_returns_one_time_material_and_revokes_old_poll() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    edge_node_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        rotate_response = await client.post(
            f"/api/v1/operations/edge-nodes/{edge_node_id}/credentials/rotate",
            headers={"Authorization": "Bearer token"},
        )
        poll_response = await client.post(
            "/api/v1/operations/supervisors/edge-supervisor-1/poll",
            headers={"Authorization": "Bearer node-credential"},
            json={"edge_node_id": str(edge_node_id), "limit": 5},
        )

    assert rotate_response.status_code == 200
    body = rotate_response.json()
    assert body["credential_material"] == "vzcred_edge_rotated_once"
    assert body["credential_version"] == 2
    assert "bearer" not in str(body).lower()
    assert operations.rotated_edge_node_id == edge_node_id
    assert poll_response.status_code == 401


@pytest.mark.asyncio
async def test_lifecycle_claim_and_completion_routes_update_request_state() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    request_id = uuid4()
    edge_node_id = uuid4()
    admission_report_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        claim_response = await client.post(
            f"/api/v1/operations/lifecycle-requests/{request_id}/claim",
            headers={"Authorization": "Bearer token"},
            json={"supervisor_id": "edge-supervisor-1", "edge_node_id": str(edge_node_id)},
        )
        complete_response = await client.post(
            f"/api/v1/operations/lifecycle-requests/{request_id}/complete",
            headers={"Authorization": "Bearer token"},
            json={
                "supervisor_id": "edge-supervisor-1",
                "status": "completed",
                "admission_report_id": str(admission_report_id),
            },
        )

    assert claim_response.status_code == 200
    assert claim_response.json()["status"] == "acknowledged"
    assert claim_response.json()["claimed_by_supervisor"] == "edge-supervisor-1"
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
    assert complete_response.json()["admission_report_id"] == str(admission_report_id)
    assert operations.claim_payload is not None
    assert operations.claim_payload.edge_node_id == edge_node_id
    assert operations.completion_payload is not None
    assert operations.completion_payload.admission_report_id == admission_report_id


@pytest.mark.asyncio
async def test_node_credential_cannot_act_for_a_different_supervisor() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    request_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/operations/lifecycle-requests/{request_id}/claim",
            headers={"Authorization": "Bearer node-credential"},
            json={"supervisor_id": "other-supervisor"},
        )

    assert response.status_code == 403
    assert operations.claim_payload is None


@pytest.mark.asyncio
async def test_hardware_report_routes_record_and_return_latest_capability() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    edge_node_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/operations/supervisors/edge-supervisor-1/hardware-reports",
            headers={"Authorization": "Bearer token"},
            json=_hardware_payload(edge_node_id).model_dump(mode="json"),
        )
        latest_supervisor_response = await client.get(
            "/api/v1/operations/supervisors/edge-supervisor-1/hardware-reports/latest",
            headers={"Authorization": "Bearer token"},
        )
        latest_edge_response = await client.get(
            f"/api/v1/operations/edge-nodes/{edge_node_id}/hardware-reports/latest",
            headers={"Authorization": "Bearer token"},
        )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["edge_node_id"] == str(edge_node_id)
    assert body["provider_capabilities"]["CoreMLExecutionProvider"] is True
    assert body["observed_performance"][0]["stage_p95_ms"]["total"] == 92.0
    assert latest_supervisor_response.status_code == 200
    assert latest_supervisor_response.json()["supervisor_id"] == "edge-supervisor-1"
    assert latest_edge_response.status_code == 200
    assert latest_edge_response.json()["edge_node_id"] == str(edge_node_id)
    assert operations.hardware_payload is not None
    assert operations.hardware_payload.edge_node_id == edge_node_id


@pytest.mark.asyncio
async def test_worker_model_admission_route_returns_recommendation() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    camera_id = uuid4()
    edge_node_id = uuid4()
    model_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/operations/workers/{camera_id}/model-admission/evaluate",
            headers={"Authorization": "Bearer token"},
            json={
                "camera_id": str(camera_id),
                "edge_node_id": str(edge_node_id),
                "model_id": str(model_id),
                "model_name": "YOLO26n COCO",
                "model_capability": "fixed_vocab",
                "selected_backend": "CoreMLExecutionProvider",
                "stream_profile": {"width": 1280, "height": 720, "fps": 10},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["camera_id"] == str(camera_id)
    assert body["status"] == "recommended"
    assert body["recommended_backend"] == "CoreMLExecutionProvider"
    assert operations.admission_payload is not None
    assert operations.admission_payload.model_id == model_id
