from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    FleetOverviewResponse,
    HardwarePerformanceSample,
    OperationsLifecycleRequestResponse,
)
from argus.models.enums import (
    DetectorCapability,
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
)
from argus.supervisor.credential_store import InMemoryCredentialStore
from argus.supervisor.operations_client import (
    PasswordGrantTokenProvider,
    SupervisorClientError,
    SupervisorOperationsClient,
)


@pytest.mark.asyncio
async def test_client_sends_bearer_token_and_records_hardware_report() -> None:
    edge_node_id = uuid4()
    tenant_id = uuid4()
    seen: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            201,
            json={
                **_hardware_report_response_json(
                    tenant_id=tenant_id,
                    edge_node_id=edge_node_id,
                    supervisor_id="edge-supervisor-1",
                ),
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as http_client:
        client = SupervisorOperationsClient(
            api_base_url="http://api.local",
            supervisor_id="edge-supervisor-1",
            bearer_token="secret-token",
            http_client=http_client,
        )

        response = await client.record_hardware_report(
            EdgeNodeHardwareReportCreate(
                edge_node_id=edge_node_id,
                reported_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
                host_profile="linux-aarch64-nvidia-jetson",
                os_name="linux",
                machine_arch="aarch64",
                provider_capabilities={"TensorrtExecutionProvider": True},
                observed_performance=[
                    HardwarePerformanceSample(
                        model_name="YOLO26n COCO",
                        runtime_backend="tensorrt_engine",
                        input_width=1280,
                        input_height=720,
                        target_fps=10,
                        stage_p95_ms={"total": 80.0},
                        stage_p99_ms={"total": 95.0},
                    )
                ],
            )
        )

    assert response.supervisor_id == "edge-supervisor-1"
    assert seen[0].method == "POST"
    assert seen[0].url.path == "/api/v1/operations/supervisors/edge-supervisor-1/hardware-reports"
    assert seen[0].headers["authorization"] == "Bearer secret-token"
    assert json.loads(seen[0].content)["edge_node_id"] == str(edge_node_id)


@pytest.mark.asyncio
async def test_client_calls_lifecycle_runtime_and_admission_routes() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    assignment_id = uuid4()
    lifecycle_request = _lifecycle_request_json(
        tenant_id=tenant_id,
        camera_id=camera_id,
        edge_node_id=edge_node_id,
        assignment_id=assignment_id,
    )
    fleet = _fleet_overview_json(
        tenant_id=tenant_id,
        camera_id=camera_id,
        edge_node_id=edge_node_id,
        assignment_id=assignment_id,
    )
    seen: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path == "/api/v1/operations/supervisors/edge-supervisor-1/poll":
            return httpx.Response(
                200,
                json={
                    "supervisor_id": "edge-supervisor-1",
                    "edge_node_id": str(edge_node_id),
                    "requests": [lifecycle_request],
                },
            )
        if path.endswith("/claim"):
            return httpx.Response(
                200,
                json={**lifecycle_request, "status": "acknowledged"},
            )
        if path.endswith("/complete"):
            return httpx.Response(
                200,
                json={**lifecycle_request, "status": "completed"},
            )
        if path == "/api/v1/operations/runtime-reports":
            return httpx.Response(
                201,
                json={
                    "id": str(uuid4()),
                    "tenant_id": str(tenant_id),
                    "camera_id": str(camera_id),
                    "edge_node_id": str(edge_node_id),
                    "assignment_id": str(assignment_id),
                    "heartbeat_at": "2026-05-13T12:00:00Z",
                    "runtime_state": "running",
                    "restart_count": 0,
                    "last_error": None,
                    "runtime_artifact_id": None,
                    "scene_contract_hash": None,
                    "created_at": "2026-05-13T12:00:00Z",
                },
            )
        if path == "/api/v1/operations/fleet":
            return httpx.Response(200, json=fleet)
        if path == f"/api/v1/operations/workers/{camera_id}/model-admission/evaluate":
            return httpx.Response(
                200,
                json={
                    "id": str(uuid4()),
                    "tenant_id": str(tenant_id),
                    "camera_id": str(camera_id),
                    "edge_node_id": str(edge_node_id),
                    "assignment_id": str(assignment_id),
                    "hardware_report_id": str(uuid4()),
                    "model_id": fleet["camera_workers"][0]["latest_model_admission"]["model_id"],
                    "model_name": "YOLO26n COCO",
                    "model_capability": "fixed_vocab",
                    "runtime_artifact_id": str(
                        fleet["camera_workers"][0]["runtime_passport"]["runtime_artifact_id"]
                    ),
                    "runtime_selection_profile_id": None,
                    "stream_profile": {"width": 1280, "height": 720, "fps": 10},
                    "status": "recommended",
                    "selected_backend": "CoreMLExecutionProvider",
                    "recommended_model_id": None,
                    "recommended_model_name": None,
                    "recommended_runtime_profile_id": None,
                    "recommended_backend": "CoreMLExecutionProvider",
                    "rationale": "CoreML fits",
                    "constraints": {},
                    "evaluated_at": "2026-05-13T12:00:00Z",
                    "created_at": "2026-05-13T12:00:00Z",
                },
            )
        return httpx.Response(404, text=path)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as http_client:
        client = SupervisorOperationsClient(
            api_base_url="http://api.local",
            supervisor_id="edge-supervisor-1",
            bearer_token="secret-token",
            http_client=http_client,
        )

        polled = await client.poll_lifecycle_requests(
            tenant_id=tenant_id,
            supervisor_id="edge-supervisor-1",
            edge_node_id=edge_node_id,
            limit=5,
        )
        claimed = await client.claim_lifecycle_request(
            tenant_id=tenant_id,
            request_id=polled[0].id,
            supervisor_id="edge-supervisor-1",
            edge_node_id=edge_node_id,
        )
        await client.record_runtime_report_for_request(
            tenant_id=tenant_id,
            request=claimed,
            runtime_state="running",
        )
        admission = await client.evaluate_model_admission_for_request(
            tenant_id=tenant_id,
            request=claimed,
        )
        await client.complete_lifecycle_request(
            tenant_id=tenant_id,
            request_id=claimed.id,
            supervisor_id="edge-supervisor-1",
            status=OperationsLifecycleStatus.COMPLETED,
            admission_report_id=admission.id,
        )

    assert [request.url.path for request in seen] == [
        "/api/v1/operations/supervisors/edge-supervisor-1/poll",
        f"/api/v1/operations/lifecycle-requests/{claimed.id}/claim",
        "/api/v1/operations/runtime-reports",
        "/api/v1/operations/fleet",
        f"/api/v1/operations/workers/{camera_id}/model-admission/evaluate",
        f"/api/v1/operations/lifecycle-requests/{claimed.id}/complete",
    ]
    assert json.loads(seen[0].content) == {"edge_node_id": str(edge_node_id), "limit": 5}
    assert json.loads(seen[1].content) == {
        "supervisor_id": "edge-supervisor-1",
        "edge_node_id": str(edge_node_id),
    }
    runtime_body = json.loads(seen[2].content)
    assert runtime_body["camera_id"] == str(camera_id)
    assert runtime_body["runtime_state"] == "running"
    admission_body = json.loads(seen[4].content)
    assert admission_body["camera_id"] == str(camera_id)
    assert admission_body["assignment_id"] == str(assignment_id)
    assert admission_body["model_name"] == "YOLO26n COCO"
    assert admission_body["model_capability"] == "fixed_vocab"
    assert admission_body["selected_backend"] == "CoreMLExecutionProvider"
    assert admission_body["preferred_backend"] == "CoreMLExecutionProvider"
    assert admission.status is ModelAdmissionStatus.RECOMMENDED
    assert json.loads(seen[5].content)["status"] == "completed"


@pytest.mark.asyncio
async def test_client_error_includes_method_path_status_and_body() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(503, text="offline"))
    ) as http_client:
        client = SupervisorOperationsClient(
            api_base_url="http://api.local",
            supervisor_id="edge-supervisor-1",
            bearer_token="secret-token",
            http_client=http_client,
        )

        with pytest.raises(SupervisorClientError) as exc_info:
            await client.poll_lifecycle_requests(
                tenant_id=uuid4(),
                supervisor_id="edge-supervisor-1",
                edge_node_id=None,
                limit=10,
            )

    assert exc_info.value.method == "POST"
    assert exc_info.value.path == "/api/v1/operations/supervisors/edge-supervisor-1/poll"
    assert exc_info.value.status_code == 503
    assert exc_info.value.response_body == "offline"


@pytest.mark.asyncio
async def test_client_retries_once_with_fresh_token_after_unauthorized() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    tokens = iter(["stale-token", "fresh-token"])
    invalidations = 0
    seen: list[httpx.Request] = []

    class _TokenProvider:
        def invalidate(self) -> None:
            nonlocal invalidations
            invalidations += 1

        async def __call__(self) -> str:
            return next(tokens)

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.headers["authorization"] == "Bearer stale-token":
            return httpx.Response(401, json={"detail": "Token verification failed."})
        return httpx.Response(
            201,
            json=_hardware_report_response_json(
                tenant_id=tenant_id,
                edge_node_id=edge_node_id,
                supervisor_id="edge-supervisor-1",
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as http_client:
        client = SupervisorOperationsClient(
            api_base_url="http://api.local",
            supervisor_id="edge-supervisor-1",
            token_provider=_TokenProvider(),
            http_client=http_client,
        )

        response = await client.record_hardware_report(
            EdgeNodeHardwareReportCreate(
                edge_node_id=edge_node_id,
                reported_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
                host_profile="linux-aarch64-nvidia-jetson",
                os_name="linux",
                machine_arch="aarch64",
                provider_capabilities={"TensorrtExecutionProvider": True},
            )
        )

    assert response.supervisor_id == "edge-supervisor-1"
    assert invalidations == 1
    assert [request.headers["authorization"] for request in seen] == [
        "Bearer stale-token",
        "Bearer fresh-token",
    ]


@pytest.mark.asyncio
async def test_client_can_use_credential_store_without_static_bearer() -> None:
    edge_node_id = uuid4()
    tenant_id = uuid4()
    seen: list[httpx.Request] = []
    store = InMemoryCredentialStore("node-credential-secret")

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            201,
            json=_hardware_report_response_json(
                tenant_id=tenant_id,
                edge_node_id=edge_node_id,
                supervisor_id="edge-supervisor-1",
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as http_client:
        client = SupervisorOperationsClient(
            api_base_url="http://api.local",
            supervisor_id="edge-supervisor-1",
            credential_store=store,
            http_client=http_client,
        )

        await client.record_hardware_report(
            EdgeNodeHardwareReportCreate(
                edge_node_id=edge_node_id,
                reported_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
                host_profile="linux-aarch64-nvidia-jetson",
                os_name="linux",
                machine_arch="aarch64",
                provider_capabilities={"TensorrtExecutionProvider": True},
            )
        )

    assert seen[0].headers["authorization"] == "Bearer node-credential-secret"


@pytest.mark.asyncio
async def test_password_grant_token_provider_caches_and_can_refresh() -> None:
    seen: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "access_token": f"token-{len(seen)}",
                "expires_in": 3600,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as http_client:
        provider = PasswordGrantTokenProvider(
            token_url="http://keycloak.local/token",
            client_id="argus-cli",
            username="admin-dev",
            password="argus-admin-pass",
            http_client=http_client,
        )

        first = await provider()
        second = await provider()
        provider.invalidate()
        third = await provider()

    assert (first, second, third) == ("token-1", "token-1", "token-2")
    assert len(seen) == 2
    assert seen[0].url.path == "/token"
    assert seen[0].content == (
        b"grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass"
    )


def _hardware_report_response_json(
    *,
    tenant_id: UUID,
    edge_node_id: UUID,
    supervisor_id: str,
) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "edge_node_id": str(edge_node_id),
        "supervisor_id": supervisor_id,
        "reported_at": "2026-05-13T12:00:00Z",
        "host_profile": "linux-aarch64-nvidia-jetson",
        "os_name": "linux",
        "machine_arch": "aarch64",
        "cpu_model": None,
        "cpu_cores": None,
        "memory_total_mb": None,
        "accelerators": ["nvidia", "cuda", "tensorrt"],
        "provider_capabilities": {"TensorrtExecutionProvider": True},
        "observed_performance": [],
        "thermal_state": None,
        "report_hash": "a" * 64,
        "created_at": "2026-05-13T12:00:00Z",
    }


def _lifecycle_request_json(
    *,
    tenant_id: UUID,
    camera_id: UUID,
    edge_node_id: UUID,
    assignment_id: UUID,
) -> dict[str, object]:
    return OperationsLifecycleRequestResponse(
        id=uuid4(),
        tenant_id=tenant_id,
        camera_id=camera_id,
        edge_node_id=edge_node_id,
        assignment_id=assignment_id,
        action=OperationsLifecycleAction.START,
        status=OperationsLifecycleStatus.REQUESTED,
        requested_by_subject="operator-1",
        requested_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        request_payload={},
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    ).model_dump(mode="json")


def _fleet_overview_json(
    *,
    tenant_id: UUID,
    camera_id: UUID,
    edge_node_id: UUID,
    assignment_id: UUID,
) -> dict[str, object]:
    model_id = uuid4()
    runtime_artifact_id = uuid4()
    return FleetOverviewResponse.model_validate(
        {
            "mode": "manual_dev",
            "generated_at": "2026-05-13T12:00:00Z",
            "summary": {
                "desired_workers": 1,
                "running_workers": 0,
                "stale_nodes": 0,
                "offline_nodes": 0,
                "native_unavailable_cameras": 0,
            },
            "nodes": [
                {
                    "id": str(edge_node_id),
                    "kind": "edge",
                    "hostname": "jetson-lab-1",
                    "status": "healthy",
                    "assigned_camera_ids": [str(camera_id)],
                }
            ],
            "camera_workers": [
                {
                    "camera_id": str(camera_id),
                    "camera_name": "Lab Camera 2",
                    "site_id": str(uuid4()),
                    "node_id": str(edge_node_id),
                    "processing_mode": "edge",
                    "desired_state": "supervised",
                    "runtime_status": "not_reported",
                    "lifecycle_owner": "edge_supervisor",
                    "runtime_passport": {
                        "id": str(uuid4()),
                        "passport_hash": "b" * 64,
                        "selected_backend": "CoreMLExecutionProvider",
                        "runtime_artifact_id": str(runtime_artifact_id),
                    },
                    "assignment": {
                        "id": str(assignment_id),
                        "tenant_id": str(tenant_id),
                        "camera_id": str(camera_id),
                        "edge_node_id": str(edge_node_id),
                        "desired_state": "supervised",
                        "active": True,
                        "supersedes_assignment_id": None,
                        "assigned_by_subject": "operator-1",
                        "created_at": "2026-05-13T12:00:00Z",
                        "updated_at": "2026-05-13T12:00:00Z",
                    },
                    "latest_model_admission": {
                        "id": str(uuid4()),
                        "tenant_id": str(tenant_id),
                        "camera_id": str(camera_id),
                        "edge_node_id": str(edge_node_id),
                        "assignment_id": str(assignment_id),
                        "hardware_report_id": str(uuid4()),
                        "model_id": str(model_id),
                        "model_name": "YOLO26n COCO",
                        "model_capability": DetectorCapability.FIXED_VOCAB.value,
                        "runtime_artifact_id": str(runtime_artifact_id),
                        "runtime_selection_profile_id": None,
                        "stream_profile": {"width": 1280, "height": 720, "fps": 10},
                        "status": "supported",
                        "selected_backend": "CoreMLExecutionProvider",
                        "recommended_model_id": None,
                        "recommended_model_name": None,
                        "recommended_runtime_profile_id": None,
                        "recommended_backend": "CoreMLExecutionProvider",
                        "rationale": "provider available",
                        "constraints": {},
                        "evaluated_at": "2026-05-13T12:00:00Z",
                        "created_at": "2026-05-13T12:00:00Z",
                    },
                }
            ],
            "delivery_diagnostics": [],
        }
    ).model_dump(mode="json")
