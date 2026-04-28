# Fleet Operations Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder Settings page with a Fleet and Operations workbench that shows desired worker state, runtime state, edge bootstrap material, manual dev commands, and source-aware delivery diagnostics.

**Architecture:** Add a read-first operations API that aggregates existing tenant-scoped `EdgeNode` and `Camera` data, derives desired worker state from camera config, and reports runtime health from heartbeats where available. The frontend replaces `/settings` with dense operational panels. Phase 1 does not start or stop host processes; it explains manual dev commands and prepares a production supervisor model.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, React, TypeScript, TanStack Query, openapi-fetch, Vitest, React Testing Library, pytest.

---

## File Structure

- Create: `backend/src/argus/api/v1/operations.py`
  - Admin operations endpoints for fleet overview and bootstrap material.
- Modify: `backend/src/argus/api/v1/__init__.py`
  - Include the operations router.
- Modify: `backend/src/argus/api/contracts.py`
  - Add operations response/request models.
- Modify: `backend/src/argus/services/app.py`
  - Add `OperationsService`, wire it into `AppServices`, and derive fleet state from existing tables.
- Test: `backend/tests/api/test_operations_endpoints.py`
  - Route-level tests with fake services.
- Test: `backend/tests/services/test_operations_service.py`
  - Service-level tests for desired state, health mapping, tenant scoping, and diagnostics.
- Create: `frontend/src/hooks/use-operations.ts`
  - TanStack Query hooks for fleet overview and bootstrap.
- Modify: `frontend/src/pages/Settings.tsx`
  - Replace placeholder with Fleet and Operations workbench.
- Test: `frontend/src/pages/Settings.test.tsx`
  - Page rendering, manual dev commands, delivery diagnostics, bootstrap result.
- Modify: `frontend/src/components/layout/TopNav.tsx`
  - Rename nav item from `Settings` to `Operations`.
- Test: `frontend/src/components/layout/AppShell.test.tsx`
  - Navigation label coverage for the renamed route.

---

## Task 1: Add Operations Contracts And Route Skeleton

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Create: `backend/src/argus/api/v1/operations.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Test: `backend/tests/api/test_operations_endpoints.py`

- [ ] **Step 1: Write the failing route tests**

Create `backend/tests/api/test_operations_endpoints.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    FleetBootstrapRequest,
    FleetBootstrapResponse,
    FleetOverviewResponse,
    FleetSummary,
    TenantContext,
)
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum


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
        return self.user


class _FakeOperationsService:
    def __init__(self) -> None:
        self.bootstrap_payload: FleetBootstrapRequest | None = None

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
            camera_workers=[],
            delivery_diagnostics=[],
        )

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


def _create_app(context: TenantContext, operations: _FakeOperationsService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        operations=operations,
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
    assert body["camera_workers"] == []


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
```

- [ ] **Step 2: Run the failing route tests**

Run:

```bash
cd backend
python3 -m uv run pytest tests/api/test_operations_endpoints.py -q
```

Expected: FAIL because `FleetOverviewResponse`, `FleetBootstrapRequest`, and the operations route do not exist.

- [ ] **Step 3: Add operations contracts**

In `backend/src/argus/api/contracts.py`, add `from enum import StrEnum` near the top, then near the edge contracts add:

```python
class FleetLifecycleMode(StrEnum):
    MANUAL_DEV = "manual_dev"
    SUPERVISED = "supervised"
    MIXED = "mixed"


class FleetNodeStatus(StrEnum):
    HEALTHY = "healthy"
    STALE = "stale"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class WorkerDesiredState(StrEnum):
    DESIRED = "desired"
    NOT_DESIRED = "not_desired"
    MANUAL = "manual"
    SUPERVISED = "supervised"


class WorkerRuntimeStatus(StrEnum):
    RUNNING = "running"
    STALE = "stale"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    NOT_REPORTED = "not_reported"


class FleetSummary(BaseModel):
    desired_workers: int
    running_workers: int
    stale_nodes: int
    offline_nodes: int
    native_unavailable_cameras: int


class FleetNodeSummary(BaseModel):
    id: UUID | None = None
    kind: Literal["central", "edge"]
    hostname: str
    site_id: UUID | None = None
    status: FleetNodeStatus
    version: str | None = None
    last_seen_at: datetime | None = None
    assigned_camera_ids: list[UUID] = Field(default_factory=list)
    reported_camera_count: int | None = None


class FleetCameraWorkerSummary(BaseModel):
    camera_id: UUID
    camera_name: str
    site_id: UUID
    node_id: UUID | None = None
    node_hostname: str | None = None
    processing_mode: ProcessingMode
    desired_state: WorkerDesiredState
    runtime_status: WorkerRuntimeStatus
    lifecycle_owner: Literal["manual_dev", "central_supervisor", "edge_supervisor", "none"]
    dev_run_command: str | None = None
    detail: str | None = None


class FleetDeliveryDiagnostic(BaseModel):
    camera_id: UUID
    camera_name: str
    processing_mode: ProcessingMode
    assigned_node_id: UUID | None = None
    source_capability: SourceCapability | None = None
    default_profile: BrowserDeliveryProfileId
    available_profiles: list[BrowserDeliveryProfile] = Field(default_factory=list)
    native_status: NativeAvailability = Field(default_factory=NativeAvailability)
    selected_stream_mode: Literal["passthrough", "transcode"]


class FleetOverviewResponse(BaseModel):
    mode: FleetLifecycleMode
    generated_at: datetime
    summary: FleetSummary
    nodes: list[FleetNodeSummary]
    camera_workers: list[FleetCameraWorkerSummary]
    delivery_diagnostics: list[FleetDeliveryDiagnostic]


class FleetBootstrapRequest(BaseModel):
    site_id: UUID
    hostname: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)


class FleetBootstrapResponse(EdgeRegisterResponse):
    dev_compose_command: str
    supervisor_environment: dict[str, str] = Field(default_factory=dict)
```

- [ ] **Step 4: Add the route skeleton**

Create `backend/src/argus/api/v1/operations.py`:

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from argus.api.contracts import (
    FleetBootstrapRequest,
    FleetBootstrapResponse,
    FleetOverviewResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("/fleet", response_model=FleetOverviewResponse)
async def get_fleet_overview(
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> FleetOverviewResponse:
    return await services.operations.get_fleet_overview(tenant_context)


@router.post(
    "/bootstrap",
    response_model=FleetBootstrapResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bootstrap_material(
    payload: FleetBootstrapRequest,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> FleetBootstrapResponse:
    return await services.operations.create_bootstrap_material(tenant_context, payload)
```

Modify `backend/src/argus/api/v1/__init__.py`:

```python
from argus.api.v1 import (
    cameras,
    edge,
    export,
    history,
    incidents,
    models,
    operations,
    query,
    sites,
    streams,
    system,
    telemetry_ws,
)

router.include_router(operations.router)
```

- [ ] **Step 5: Add a temporary service attribute shape**

In `backend/src/argus/services/app.py`, add `operations: OperationsService` to `AppServices`. The actual service class is implemented in Task 2.

- [ ] **Step 6: Run the route tests**

Run:

```bash
cd backend
python3 -m uv run pytest tests/api/test_operations_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/argus/api/contracts.py backend/src/argus/api/v1/__init__.py backend/src/argus/api/v1/operations.py backend/src/argus/services/app.py backend/tests/api/test_operations_endpoints.py
git commit -m "feat(operations): add fleet operations API contracts"
```

---

## Task 2: Implement Operations Service Fleet Overview

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_operations_service.py`

- [ ] **Step 1: Write failing service tests**

Create `backend/tests/services/test_operations_service.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from argus.api.contracts import FleetBootstrapRequest, TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import ProcessingMode, RoleEnum, TrackerType
from argus.models.tables import Camera, EdgeNode, Site
from argus.services.app import OperationsService


class _FakeResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _FakeSession:
    def __init__(self, result_sets: list[list[object]]) -> None:
        self._result_sets = result_sets

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _FakeResult:  # noqa: ANN001
        return _FakeResult(self._result_sets.pop(0))


class _FakeSessionFactory:
    def __init__(self, *result_sets: list[object]) -> None:
        self.result_sets = [list(result_set) for result_set in result_sets]

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.result_sets)


def _tenant_context(tenant_id) -> TenantContext:
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
            tenant_context=None,
            claims={},
        ),
    )


def _site(tenant_id) -> Site:  # noqa: ANN001
    return Site(
        id=uuid4(),
        tenant_id=tenant_id,
        name="HQ",
        description=None,
        tz="UTC",
        geo_point=None,
    )


@pytest.mark.asyncio
async def test_fleet_overview_derives_manual_central_worker() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=None,
        name="Lobby",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["person"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={
            "default_profile": "720p10",
            "allow_native_on_demand": True,
            "profiles": [{"id": "720p10", "kind": "transcode"}],
        },
        source_capability={"width": 1280, "height": 720, "fps": 10.0, "codec": "h264"},
        frame_skip=1,
        fps_cap=25,
    )
    session_factory = _FakeSessionFactory([], [(camera, site)])
    service = OperationsService(session_factory=session_factory, settings=Settings())
    response = await service.get_fleet_overview(_tenant_context(tenant_id))

    assert response.mode == "manual_dev"
    assert response.summary.desired_workers == 1
    assert response.camera_workers[0].camera_name == "Lobby"
    assert response.camera_workers[0].desired_state == "manual"
    assert response.camera_workers[0].runtime_status == "not_reported"
    assert "argus.inference.engine --camera-id" in response.camera_workers[0].dev_run_command
    assert response.delivery_diagnostics[0].source_capability is not None


@pytest.mark.asyncio
async def test_fleet_overview_maps_edge_heartbeat_status() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    edge = EdgeNode(
        id=uuid4(),
        site_id=site.id,
        hostname="jetson-1",
        public_key="seed",
        version="0.1.0",
        last_seen_at=datetime.now(tz=UTC) - timedelta(minutes=10),
    )
    camera = Camera(
        id=uuid4(),
        site_id=site.id,
        edge_node_id=edge.id,
        name="Driveway",
        rtsp_url_encrypted="encrypted-rtsp-url",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BYTETRACK,
        active_classes=["car"],
        attribute_rules=[],
        zones=[],
        homography=None,
        privacy={},
        browser_delivery={},
        source_capability=None,
        frame_skip=1,
        fps_cap=25,
    )
    session_factory = _FakeSessionFactory([(edge, site)], [(camera, site)])
    service = OperationsService(session_factory=session_factory, settings=Settings())
    response = await service.get_fleet_overview(_tenant_context(tenant_id))
    edge_node = next(node for node in response.nodes if node.hostname == "jetson-1")

    assert edge_node.status == "stale"
    assert response.camera_workers[0].lifecycle_owner == "edge_supervisor"
    assert response.camera_workers[0].runtime_status == "stale"
```

- [ ] **Step 2: Run the failing service tests**

Run:

```bash
cd backend
python3 -m uv run pytest tests/services/test_operations_service.py -q
```

Expected: FAIL because `OperationsService` does not exist.

- [ ] **Step 3: Implement `OperationsService`**

In `backend/src/argus/services/app.py`, add `Literal` to the existing `typing` import:

```python
from typing import TYPE_CHECKING, Any, Literal, cast
```

Then add operations contracts to the existing `argus.api.contracts` import:

```python
from argus.api.contracts import (
    BrowserDeliverySettings,
    EdgeRegisterRequest,
    FleetBootstrapRequest,
    FleetBootstrapResponse,
    FleetCameraWorkerSummary,
    FleetDeliveryDiagnostic,
    FleetLifecycleMode,
    FleetNodeStatus,
    FleetNodeSummary,
    FleetOverviewResponse,
    FleetSummary,
    SourceCapability,
    WorkerDesiredState,
    WorkerRuntimeStatus,
)
```

Add the service before `HistoryService`:

```python
class OperationsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        edge_service: EdgeService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.edge_service = edge_service

    async def get_fleet_overview(self, tenant_context: TenantContext) -> FleetOverviewResponse:
        now = datetime.now(tz=UTC)
        async with self.session_factory() as session:
            edge_rows = (
                await session.execute(
                    select(EdgeNode, Site)
                    .join(Site, Site.id == EdgeNode.site_id)
                    .where(Site.tenant_id == tenant_context.tenant_id)
                    .order_by(EdgeNode.hostname)
                )
            ).all()
            camera_rows = (
                await session.execute(
                    select(Camera, Site)
                    .join(Site, Site.id == Camera.site_id)
                    .where(Site.tenant_id == tenant_context.tenant_id)
                    .order_by(Camera.name)
                )
            ).all()

        edge_by_id = {edge.id: edge for edge, _site in edge_rows}
        assigned_camera_ids: dict[UUID, list[UUID]] = {edge.id: [] for edge, _site in edge_rows}
        for camera, _site in camera_rows:
            if camera.edge_node_id in assigned_camera_ids:
                assigned_camera_ids[camera.edge_node_id].append(camera.id)

        nodes: list[FleetNodeSummary] = [
            FleetNodeSummary(
                id=None,
                kind="central",
                hostname="central",
                status=FleetNodeStatus.UNKNOWN,
                assigned_camera_ids=[
                    camera.id
                    for camera, _site in camera_rows
                    if camera.edge_node_id is None
                    and camera.processing_mode in {ProcessingMode.CENTRAL, ProcessingMode.HYBRID}
                ],
            )
        ]
        for edge, site in edge_rows:
            status = _fleet_node_status(edge.last_seen_at, now)
            nodes.append(
                FleetNodeSummary(
                    id=edge.id,
                    kind="edge",
                    hostname=edge.hostname,
                    site_id=site.id,
                    status=status,
                    version=edge.version,
                    last_seen_at=edge.last_seen_at,
                    assigned_camera_ids=assigned_camera_ids.get(edge.id, []),
                    reported_camera_count=None,
                )
            )

        camera_workers: list[FleetCameraWorkerSummary] = []
        delivery_diagnostics: list[FleetDeliveryDiagnostic] = []
        for camera, site in camera_rows:
            desired, runtime, owner, detail = _derive_worker_lifecycle(
                camera=camera,
                edge_by_id=edge_by_id,
                now=now,
            )
            camera_workers.append(
                FleetCameraWorkerSummary(
                    camera_id=camera.id,
                    camera_name=camera.name,
                    site_id=site.id,
                    node_id=camera.edge_node_id,
                    node_hostname=(
                        edge_by_id[camera.edge_node_id].hostname
                        if camera.edge_node_id in edge_by_id
                        else None
                    ),
                    processing_mode=camera.processing_mode,
                    desired_state=desired,
                    runtime_status=runtime,
                    lifecycle_owner=owner,
                    dev_run_command=(
                        _central_dev_run_command(camera.id)
                        if owner == "manual_dev"
                        else None
                    ),
                    detail=detail,
                )
            )
            delivery_diagnostics.append(_camera_delivery_diagnostic(camera))

        summary = FleetSummary(
            desired_workers=sum(
                1
                for worker in camera_workers
                if worker.desired_state
                in {WorkerDesiredState.DESIRED, WorkerDesiredState.MANUAL, WorkerDesiredState.SUPERVISED}
            ),
            running_workers=sum(
                1 for worker in camera_workers if worker.runtime_status == WorkerRuntimeStatus.RUNNING
            ),
            stale_nodes=sum(1 for node in nodes if node.status == FleetNodeStatus.STALE),
            offline_nodes=sum(1 for node in nodes if node.status == FleetNodeStatus.OFFLINE),
            native_unavailable_cameras=sum(
                1
                for diagnostic in delivery_diagnostics
                if diagnostic.native_status.available is False
            ),
        )
        return FleetOverviewResponse(
            mode=FleetLifecycleMode.MANUAL_DEV,
            generated_at=now,
            summary=summary,
            nodes=nodes,
            camera_workers=camera_workers,
            delivery_diagnostics=delivery_diagnostics,
        )
```

- [ ] **Step 4: Add helper functions**

In `backend/src/argus/services/app.py`, add near the other private helpers:

```python
def _fleet_node_status(last_seen_at: datetime | None, now: datetime) -> FleetNodeStatus:
    if last_seen_at is None:
        return FleetNodeStatus.OFFLINE
    age = now - last_seen_at
    if age <= timedelta(minutes=2):
        return FleetNodeStatus.HEALTHY
    if age <= timedelta(minutes=15):
        return FleetNodeStatus.STALE
    return FleetNodeStatus.OFFLINE


def _derive_worker_lifecycle(
    *,
    camera: Camera,
    edge_by_id: dict[UUID, EdgeNode],
    now: datetime,
) -> tuple[
    WorkerDesiredState,
    WorkerRuntimeStatus,
    Literal["manual_dev", "central_supervisor", "edge_supervisor", "none"],
    str,
]:
    if camera.processing_mode is ProcessingMode.EDGE and camera.edge_node_id is None:
        return (
            WorkerDesiredState.NOT_DESIRED,
            WorkerRuntimeStatus.UNKNOWN,
            "none",
            "Edge processing requires an assigned edge node.",
        )
    if camera.edge_node_id is not None:
        edge = edge_by_id.get(camera.edge_node_id)
        if edge is None:
            return (
                WorkerDesiredState.SUPERVISED,
                WorkerRuntimeStatus.OFFLINE,
                "edge_supervisor",
                "Assigned edge node is missing.",
            )
        node_status = _fleet_node_status(edge.last_seen_at, now)
        runtime = (
            WorkerRuntimeStatus.STALE
            if node_status is FleetNodeStatus.STALE
            else WorkerRuntimeStatus.OFFLINE
            if node_status is FleetNodeStatus.OFFLINE
            else WorkerRuntimeStatus.NOT_REPORTED
        )
        return (
            WorkerDesiredState.SUPERVISED,
            runtime,
            "edge_supervisor",
            "Edge supervisor owns this worker process.",
        )
    if camera.processing_mode in {ProcessingMode.CENTRAL, ProcessingMode.HYBRID}:
        return (
            WorkerDesiredState.MANUAL,
            WorkerRuntimeStatus.NOT_REPORTED,
            "manual_dev",
            "Start this worker manually in local development.",
        )
    return (
        WorkerDesiredState.NOT_DESIRED,
        WorkerRuntimeStatus.NOT_REPORTED,
        "none",
        "No worker is desired for this camera.",
    )


def _central_dev_run_command(camera_id: UUID) -> str:
    return (
        "cd backend && "
        "ARGUS_API_BASE_URL=http://127.0.0.1:8000 "
        "ARGUS_API_BEARER_TOKEN=<token> "
        f"python3 -m uv run python -m argus.inference.engine --camera-id {camera_id}"
    )


def _camera_delivery_diagnostic(camera: Camera) -> FleetDeliveryDiagnostic:
    source_capability = (
        SourceCapability.model_validate(camera.source_capability)
        if camera.source_capability is not None
        else None
    )
    requested = BrowserDeliverySettings.model_validate(camera.browser_delivery or {})
    resolved = _build_source_aware_browser_delivery(
        requested=requested,
        privacy=camera.privacy,
        source_capability=source_capability,
    )
    selected = _resolve_worker_stream_settings(
        browser_delivery=resolved,
        fps_cap=camera.fps_cap,
        processed_native=_uses_processed_native_delivery(camera),
    )
    return FleetDeliveryDiagnostic(
        camera_id=camera.id,
        camera_name=camera.name,
        processing_mode=camera.processing_mode,
        assigned_node_id=camera.edge_node_id,
        source_capability=source_capability,
        default_profile=resolved.default_profile,
        available_profiles=resolved.profiles,
        native_status=resolved.native_status,
        selected_stream_mode=selected.kind,
    )
```

- [ ] **Step 5: Wire the service**

In `build_app_services`, instantiate `edge_service` once and pass it to `OperationsService`:

```python
edge_service = EdgeService(db.session_factory, settings, events, audit_logger)
return AppServices(
    tenancy=TenancyService(db.session_factory, settings),
    sites=SiteService(db.session_factory, audit_logger),
    cameras=CameraService(db.session_factory, settings, audit_logger, events),
    models=ModelService(db.session_factory, audit_logger),
    edge=edge_service,
    operations=OperationsService(
        db.session_factory,
        settings,
        edge_service=edge_service,
    ),
    history=HistoryService(db.session_factory),
    incidents=IncidentService(db.session_factory),
    streams=StreamService(db.session_factory, mediamtx, settings),
    query=query_service,
    telemetry=NatsTelemetryService(...),
)
```

- [ ] **Step 6: Run service tests**

Run:

```bash
cd backend
python3 -m uv run pytest tests/services/test_operations_service.py -q
```

Expected: PASS.

- [ ] **Step 7: Run route tests**

Run:

```bash
cd backend
python3 -m uv run pytest tests/api/test_operations_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/argus/services/app.py backend/tests/services/test_operations_service.py
git commit -m "feat(operations): derive fleet worker lifecycle overview"
```

---

## Task 3: Add Bootstrap Material Through Operations

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_operations_service.py`

- [ ] **Step 1: Add failing bootstrap service test**

Append to `backend/tests/services/test_operations_service.py`:

```python
class _FakeEdgeService:
    def __init__(self) -> None:
        self.payload = None

    async def register_edge_node(self, tenant_context, payload):
        self.payload = payload
        from argus.api.contracts import EdgeRegisterResponse

        return EdgeRegisterResponse(
            edge_node_id=uuid4(),
            api_key="edge_secret_once",
            nats_nkey_seed="nats_secret_once",
            subjects=["evt.tracking.node"],
            mediamtx_url="http://mediamtx:9997",
            overlay_network_hints={"nats_url": "nats://nats:4222"},
        )


@pytest.mark.asyncio
async def test_create_bootstrap_material_wraps_edge_registration() -> None:
    tenant_id = uuid4()
    site = _site(tenant_id)
    session_factory = _FakeSessionFactory()
    edge_service = _FakeEdgeService()
    service = OperationsService(
        session_factory=session_factory,
        settings=Settings(),
        edge_service=edge_service,
    )

    response = await service.create_bootstrap_material(
        _tenant_context(tenant_id),
        FleetBootstrapRequest(site_id=site.id, hostname="edge-kit-01", version="0.1.0"),
    )

    assert edge_service.payload is not None
    assert edge_service.payload.hostname == "edge-kit-01"
    assert response.api_key == "edge_secret_once"
    assert "docker compose -f infra/docker-compose.edge.yml up inference-worker" in response.dev_compose_command
    assert response.supervisor_environment["ARGUS_EDGE_NODE_ID"] == str(response.edge_node_id)
```

- [ ] **Step 2: Run the failing bootstrap test**

Run:

```bash
cd backend
python3 -m uv run pytest tests/services/test_operations_service.py::test_create_bootstrap_material_wraps_edge_registration -q
```

Expected: FAIL because `create_bootstrap_material` does not exist.

- [ ] **Step 3: Implement bootstrap material**

In `OperationsService`, add:

```python
    async def create_bootstrap_material(
        self,
        tenant_context: TenantContext,
        payload: FleetBootstrapRequest,
    ) -> FleetBootstrapResponse:
        if self.edge_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Edge registration service is unavailable.",
            )
        edge_response = await self.edge_service.register_edge_node(
            tenant_context,
            EdgeRegisterRequest(
                site_id=payload.site_id,
                hostname=payload.hostname,
                version=payload.version,
            ),
        )
        return FleetBootstrapResponse(
            **edge_response.model_dump(),
            dev_compose_command=_edge_dev_compose_command(edge_response.edge_node_id),
            supervisor_environment={
                "ARGUS_API_BASE_URL": self.settings.api_base_url,
                "ARGUS_EDGE_NODE_ID": str(edge_response.edge_node_id),
                "ARGUS_EDGE_API_KEY": edge_response.api_key,
            },
        )
```

Add helper:

```python
def _edge_dev_compose_command(edge_node_id: UUID) -> str:
    return (
        "ARGUS_EDGE_CAMERA_ID=<camera-id> "
        "ARGUS_API_BASE_URL=http://<master-host>:8000 "
        "ARGUS_API_BEARER_TOKEN=<token> "
        "docker compose -f infra/docker-compose.edge.yml up inference-worker"
    )
```

If `Settings` has no `api_base_url`, use `self.settings.public_api_base_url` if present. If neither exists, use `"http://<master-host>:8000"` in the environment value.

- [ ] **Step 4: Run bootstrap service test**

Run:

```bash
cd backend
python3 -m uv run pytest tests/services/test_operations_service.py::test_create_bootstrap_material_wraps_edge_registration -q
```

Expected: PASS.

- [ ] **Step 5: Run all operations backend tests**

Run:

```bash
cd backend
python3 -m uv run pytest tests/services/test_operations_service.py tests/api/test_operations_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/argus/services/app.py backend/tests/services/test_operations_service.py
git commit -m "feat(operations): expose edge bootstrap material"
```

---

## Task 4: Generate OpenAPI Types And Add Frontend Operations Hook

**Files:**
- Modify: `frontend/src/lib/api.generated.ts`
- Create: `frontend/src/hooks/use-operations.ts`
- Test: `frontend/src/hooks/use-operations.test.ts`

- [ ] **Step 1: Generate API types**

Run:

```bash
corepack pnpm --dir frontend generate:api
```

Expected: PASS and `frontend/src/lib/api.generated.ts` contains `/api/v1/operations/fleet`.

- [ ] **Step 2: Write failing hook tests**

Create `frontend/src/hooks/use-operations.test.ts`:

```ts
import { describe, expect, test, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    GET: vi.fn(async () => ({
      data: {
        mode: "manual_dev",
        generated_at: "2026-04-28T07:00:00Z",
        summary: {
          desired_workers: 1,
          running_workers: 0,
          stale_nodes: 0,
          offline_nodes: 0,
          native_unavailable_cameras: 0,
        },
        nodes: [],
        camera_workers: [],
        delivery_diagnostics: [],
      },
      error: undefined,
    })),
    POST: vi.fn(async () => ({
      data: {
        edge_node_id: "00000000-0000-0000-0000-000000000123",
        api_key: "edge_secret_once",
        nats_nkey_seed: "nats_secret_once",
        subjects: [],
        mediamtx_url: "http://mediamtx:9997",
        overlay_network_hints: {},
        dev_compose_command: "docker compose -f infra/docker-compose.edge.yml up inference-worker",
        supervisor_environment: {},
      },
      error: undefined,
    })),
  },
  toApiError: (error: unknown, fallback: string) => new Error(fallback),
}));

import { apiClient } from "@/lib/api";
import { createBootstrapMutationOptions, fleetOverviewQueryOptions } from "@/hooks/use-operations";

describe("use-operations query helpers", () => {
  test("builds the fleet overview query", async () => {
    const options = fleetOverviewQueryOptions();
    const data = await options.queryFn();

    expect(options.queryKey).toEqual(["operations", "fleet"]);
    expect(data.mode).toBe("manual_dev");
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/operations/fleet");
  });

  test("builds the bootstrap mutation", async () => {
    const options = createBootstrapMutationOptions();
    const data = await options.mutationFn({
      site_id: "00000000-0000-0000-0000-000000000001",
      hostname: "edge-kit-01",
      version: "0.1.0",
    });

    expect(data.api_key).toBe("edge_secret_once");
    expect(apiClient.POST).toHaveBeenCalledWith("/api/v1/operations/bootstrap", {
      body: {
        site_id: "00000000-0000-0000-0000-000000000001",
        hostname: "edge-kit-01",
        version: "0.1.0",
      },
    });
  });
});
```

- [ ] **Step 3: Run the failing hook tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/hooks/use-operations.test.ts
```

Expected: FAIL because `use-operations.ts` does not exist.

- [ ] **Step 4: Implement the hook**

Create `frontend/src/hooks/use-operations.ts`:

```ts
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";
import type { components } from "@/lib/api.generated";

export type FleetOverview = components["schemas"]["FleetOverviewResponse"];
export type FleetBootstrapRequest = components["schemas"]["FleetBootstrapRequest"];
export type FleetBootstrapResponse = components["schemas"]["FleetBootstrapResponse"];

export function fleetOverviewQueryOptions() {
  return queryOptions({
    queryKey: ["operations", "fleet"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/operations/fleet");
      if (error || !data) {
        throw toApiError(error, "Failed to load fleet operations.");
      }
      return data;
    },
  });
}

export function createBootstrapMutationOptions() {
  return {
    mutationFn: async (payload: FleetBootstrapRequest) => {
      const { data, error } = await apiClient.POST("/api/v1/operations/bootstrap", {
        body: payload,
      });
      if (error || !data) {
        throw toApiError(error, "Failed to create edge bootstrap material.");
      }
      return data;
    },
  };
}

export function useFleetOverview() {
  return useQuery(fleetOverviewQueryOptions());
}

export function useCreateBootstrapMaterial() {
  const queryClient = useQueryClient();
  return useMutation({
    ...createBootstrapMutationOptions(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["operations", "fleet"] });
    },
  });
}
```

- [ ] **Step 5: Run hook tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/hooks/use-operations.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api.generated.ts frontend/src/hooks/use-operations.ts frontend/src/hooks/use-operations.test.ts
git commit -m "feat(operations-ui): add fleet operations hooks"
```

---

## Task 5: Replace Settings Placeholder With Operations Page

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`
- Test: `frontend/src/pages/Settings.test.tsx`

- [ ] **Step 1: Write failing page tests**

Create `frontend/src/pages/Settings.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

const fleetOverview = {
  mode: "manual_dev",
  generated_at: "2026-04-28T07:00:00Z",
  summary: {
    desired_workers: 2,
    running_workers: 0,
    stale_nodes: 1,
    offline_nodes: 0,
    native_unavailable_cameras: 1,
  },
  nodes: [
    {
      id: null,
      kind: "central",
      hostname: "central",
      site_id: null,
      status: "unknown",
      version: null,
      last_seen_at: null,
      assigned_camera_ids: ["00000000-0000-0000-0000-000000000101"],
      reported_camera_count: null,
    },
    {
      id: "00000000-0000-0000-0000-000000000201",
      kind: "edge",
      hostname: "jetson-1",
      site_id: "00000000-0000-0000-0000-000000000301",
      status: "stale",
      version: "0.1.0",
      last_seen_at: "2026-04-28T06:50:00Z",
      assigned_camera_ids: ["00000000-0000-0000-0000-000000000102"],
      reported_camera_count: null,
    },
  ],
  camera_workers: [
    {
      camera_id: "00000000-0000-0000-0000-000000000101",
      camera_name: "Lobby",
      site_id: "00000000-0000-0000-0000-000000000301",
      node_id: null,
      node_hostname: null,
      processing_mode: "central",
      desired_state: "manual",
      runtime_status: "not_reported",
      lifecycle_owner: "manual_dev",
      dev_run_command: "python3 -m uv run python -m argus.inference.engine --camera-id 00000000-0000-0000-0000-000000000101",
      detail: "Start this worker manually in local development.",
    },
    {
      camera_id: "00000000-0000-0000-0000-000000000102",
      camera_name: "Driveway",
      site_id: "00000000-0000-0000-0000-000000000301",
      node_id: "00000000-0000-0000-0000-000000000201",
      node_hostname: "jetson-1",
      processing_mode: "edge",
      desired_state: "supervised",
      runtime_status: "stale",
      lifecycle_owner: "edge_supervisor",
      dev_run_command: null,
      detail: "Edge supervisor owns this worker process.",
    },
  ],
  delivery_diagnostics: [
    {
      camera_id: "00000000-0000-0000-0000-000000000101",
      camera_name: "Lobby",
      processing_mode: "central",
      assigned_node_id: null,
      source_capability: { width: 1280, height: 720, fps: 10, codec: "h264" },
      default_profile: "720p10",
      available_profiles: [{ id: "720p10", kind: "transcode" }],
      native_status: { available: false, reason: "privacy_filtering_required" },
      selected_stream_mode: "transcode",
    },
  ],
};

vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: fleetOverview,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useCreateBootstrapMaterial: () => ({
    mutateAsync: vi.fn(async () => ({
      edge_node_id: "00000000-0000-0000-0000-000000000999",
      api_key: "edge_secret_once",
      nats_nkey_seed: "nats_secret_once",
      subjects: [],
      mediamtx_url: "http://mediamtx:9997",
      overlay_network_hints: {},
      dev_compose_command: "docker compose -f infra/docker-compose.edge.yml up inference-worker",
      supervisor_environment: { ARGUS_EDGE_NODE_ID: "00000000-0000-0000-0000-000000000999" },
    })),
    isPending: false,
  }),
}));

import { SettingsPage } from "@/pages/Settings";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SettingsPage />
    </QueryClientProvider>,
  );
}

describe("SettingsPage operations workbench", () => {
  test("renders fleet operations instead of placeholder copy", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: /fleet and operations/i })).toBeInTheDocument();
    expect(screen.getByText(/manual dev mode/i)).toBeInTheDocument();
    expect(screen.getByText(/desired workers/i)).toBeInTheDocument();
    expect(screen.queryByText(/prompt 7 uses this route/i)).not.toBeInTheDocument();
  });

  test("shows worker lifecycle and delivery diagnostics", () => {
    renderPage();

    expect(screen.getByText("Lobby")).toBeInTheDocument();
    expect(screen.getByText(/argus.inference.engine --camera-id/i)).toBeInTheDocument();
    expect(screen.getByText("jetson-1")).toBeInTheDocument();
    expect(screen.getByText(/privacy filtering required/i)).toBeInTheDocument();
    expect(screen.getByText(/1280 x 720/i)).toBeInTheDocument();
  });

  test("generates bootstrap material with one-time warning", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/hostname/i), "edge-kit-01");
    await user.type(screen.getByLabelText(/version/i), "0.1.0");
    await user.click(screen.getByRole("button", { name: /generate bootstrap/i }));

    expect(await screen.findByText(/edge_secret_once/i)).toBeInTheDocument();
    expect(screen.getByText(/shown once/i)).toBeInTheDocument();
    expect(screen.getByText(/docker compose/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run failing page tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx
```

Expected: FAIL because the Settings page still renders placeholder copy.

- [ ] **Step 3: Implement Operations page**

Replace `frontend/src/pages/Settings.tsx` with:

```tsx
import { useMemo, useState, type ReactNode } from "react";
import { Copy, RefreshCw, Server, ShieldAlert, TerminalSquare } from "lucide-react";

import {
  type FleetBootstrapResponse,
  useCreateBootstrapMaterial,
  useFleetOverview,
} from "@/hooks/use-operations";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function SettingsPage() {
  const fleet = useFleetOverview();
  const bootstrap = useCreateBootstrapMaterial();
  const [hostname, setHostname] = useState("");
  const [version, setVersion] = useState("0.1.0");
  const [bootstrapResult, setBootstrapResult] = useState<FleetBootstrapResponse | null>(null);
  const firstSiteId = fleet.data?.camera_workers[0]?.site_id;

  const modeCopy = useMemo(() => {
    if (fleet.data?.mode === "supervised") {
      return "Supervised production mode";
    }
    if (fleet.data?.mode === "mixed") {
      return "Mixed manual and supervised mode";
    }
    return "Manual dev mode";
  }, [fleet.data?.mode]);

  async function handleBootstrap() {
    if (!firstSiteId || hostname.trim().length === 0 || version.trim().length === 0) {
      return;
    }
    const result = await bootstrap.mutateAsync({
      site_id: firstSiteId,
      hostname,
      version,
    });
    setBootstrapResult(result);
  }

  if (fleet.isLoading) {
    return <section className="px-6 py-6 text-sm text-[#d8e2f2]">Loading operations...</section>;
  }

  if (fleet.isError || !fleet.data) {
    return (
      <section className="px-6 py-6 text-sm text-[#ffd6d6]">
        Failed to load fleet operations.
      </section>
    );
  }

  return (
    <section className="space-y-5">
      <header className="rounded-lg border border-white/10 bg-[#111827] px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
              Operations
            </p>
            <h1 className="mt-2 text-2xl font-semibold text-[#f4f8ff]">
              Fleet and operations
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-[#93a7c5]">
              Workers are started by manual dev commands or production supervisors. This page
              shows desired state, runtime reports, bootstrap material, and delivery truth.
            </p>
          </div>
          <Button type="button" onClick={() => void fleet.refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </header>

      <section className="grid gap-3 md:grid-cols-5">
        <SummaryTile label="Desired workers" value={fleet.data.summary.desired_workers} />
        <SummaryTile label="Running workers" value={fleet.data.summary.running_workers} />
        <SummaryTile label="Stale nodes" value={fleet.data.summary.stale_nodes} />
        <SummaryTile label="Offline nodes" value={fleet.data.summary.offline_nodes} />
        <SummaryTile
          label="Native unavailable"
          value={fleet.data.summary.native_unavailable_cameras}
        />
      </section>

      <section className="rounded-lg border border-white/10 bg-[#0f172a] px-5 py-4">
        <div className="flex items-center gap-3">
          <TerminalSquare className="h-5 w-5 text-[#8fd3ff]" />
          <div>
            <h2 className="text-base font-semibold text-[#f4f8ff]">{modeCopy}</h2>
            <p className="text-sm text-[#93a7c5]">
              Start and stop are owned by the local terminal in dev, and by a supervisor in
              production. The UI changes desired state and shows diagnostics.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Panel title="Nodes" icon={<Server className="h-4 w-4" />}>
          <div className="space-y-3">
            {fleet.data.nodes.map((node) => (
              <div key={node.id ?? "central"} className="rounded-md border border-white/10 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-[#f4f8ff]">{node.hostname}</p>
                    <p className="text-xs text-[#93a7c5]">
                      {node.kind} - {node.assigned_camera_ids.length} assigned cameras
                    </p>
                  </div>
                  <Badge>{node.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Bootstrap edge node" icon={<ShieldAlert className="h-4 w-4" />}>
          <div className="space-y-3">
            <Input
              aria-label="Hostname"
              value={hostname}
              onChange={(event) => setHostname(event.target.value)}
              placeholder="edge-kit-01"
            />
            <Input
              aria-label="Version"
              value={version}
              onChange={(event) => setVersion(event.target.value)}
              placeholder="0.1.0"
            />
            <Button type="button" onClick={() => void handleBootstrap()}>
              Generate bootstrap
            </Button>
            {bootstrapResult ? (
              <div className="rounded-md border border-amber-300/30 bg-amber-950/30 p-3 text-sm text-amber-100">
                <p className="font-semibold">Secrets are shown once.</p>
                <CommandBlock text={bootstrapResult.api_key} />
                <CommandBlock text={bootstrapResult.dev_compose_command} />
              </div>
            ) : null}
          </div>
        </Panel>
      </section>

      <Panel title="Camera workers" icon={<TerminalSquare className="h-4 w-4" />}>
        <div className="space-y-3">
          {fleet.data.camera_workers.map((worker) => (
            <div key={worker.camera_id} className="rounded-md border border-white/10 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-[#f4f8ff]">{worker.camera_name}</p>
                  <p className="text-xs text-[#93a7c5]">
                    {worker.processing_mode} - {worker.lifecycle_owner}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Badge>{worker.desired_state}</Badge>
                  <Badge>{worker.runtime_status}</Badge>
                </div>
              </div>
              {worker.detail ? <p className="mt-2 text-sm text-[#93a7c5]">{worker.detail}</p> : null}
              {worker.dev_run_command ? <CommandBlock text={worker.dev_run_command} /> : null}
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Delivery diagnostics" icon={<Copy className="h-4 w-4" />}>
        <div className="space-y-3">
          {fleet.data.delivery_diagnostics.map((diagnostic) => (
            <div key={diagnostic.camera_id} className="rounded-md border border-white/10 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-[#f4f8ff]">{diagnostic.camera_name}</p>
                  <p className="text-xs text-[#93a7c5]">
                    {formatSource(diagnostic.source_capability)} - {diagnostic.default_profile}
                  </p>
                </div>
                <Badge>{diagnostic.selected_stream_mode}</Badge>
              </div>
              {diagnostic.native_status.available === false ? (
                <p className="mt-2 text-sm text-amber-100">
                  Native unavailable: {formatReason(diagnostic.native_status.reason)}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </Panel>
    </section>
  );
}

function SummaryTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-[#101827] px-4 py-3">
      <p className="text-xs text-[#93a7c5]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[#f4f8ff]">{value}</p>
    </div>
  );
}

function Panel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-white/10 bg-[#0b1120] p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#f4f8ff]">
        {icon}
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function CommandBlock({ text }: { text: string }) {
  return (
    <pre className="mt-3 overflow-auto rounded-md bg-black/40 p-3 text-xs text-[#d8e2f2]">
      {text}
    </pre>
  );
}

function formatSource(source: { width?: number; height?: number; fps?: number | null } | null) {
  if (!source?.width || !source.height) {
    return "source unknown";
  }
  return `${source.width} x ${source.height}${source.fps ? ` at ${source.fps} fps` : ""}`;
}

function formatReason(reason: string | null | undefined) {
  return (reason ?? "unknown").replaceAll("_", " ");
}
```

Adjust imports if local UI components use different button/input paths. Keep the rendered text and structure the tests assert.

- [ ] **Step 4: Run page tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx
git commit -m "feat(operations-ui): replace settings with fleet workbench"
```

---

## Task 6: Rename Navigation Affordance To Operations

**Files:**
- Modify: `frontend/src/components/layout/TopNav.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: Write failing nav test**

If `frontend/src/components/layout/AppShell.test.tsx` exists, add:

```tsx
test("labels the settings route as operations", () => {
  renderAppShell();

  const operationsLink = screen.getByRole("link", { name: /operations/i });
  expect(operationsLink).toHaveAttribute("href", "/settings");
});
```

If that helper does not exist, add a small test around `workspaceNavGroups`:

```tsx
import { describe, expect, test } from "vitest";

import { workspaceNavGroups } from "@/components/layout/TopNav";

describe("workspace navigation", () => {
  test("labels the settings route as operations", () => {
    const allItems = workspaceNavGroups.flatMap((group) => group.items);
    expect(allItems).toContainEqual(
      expect.objectContaining({
        label: "Operations",
        to: "/settings",
      }),
    );
  });
});
```

- [ ] **Step 2: Run failing nav test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/AppShell.test.tsx
```

Expected: FAIL because the nav item is still `Settings`.

- [ ] **Step 3: Update nav label**

In `frontend/src/components/layout/TopNav.tsx`, change:

```ts
{ label: "Settings", to: "/settings", icon: Settings2 },
```

to:

```ts
{ label: "Operations", to: "/settings", icon: Settings2 },
```

- [ ] **Step 4: Run nav test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/TopNav.tsx frontend/src/components/layout/AppShell.test.tsx
git commit -m "feat(operations-ui): label settings route as operations"
```

---

## Task 7: Verification And Manual Checks

**Files:**
- Verify backend, frontend, generated types, and browser render.

- [ ] **Step 1: Run backend operations tests**

Run:

```bash
cd backend
python3 -m uv run pytest tests/services/test_operations_service.py tests/api/test_operations_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 2: Run backend lint and type checks**

Run:

```bash
cd backend
python3 -m uv run ruff check src/argus/api/contracts.py src/argus/api/v1/operations.py src/argus/api/v1/__init__.py src/argus/services/app.py tests/services/test_operations_service.py tests/api/test_operations_endpoints.py
python3 -m uv run mypy src/argus/api/contracts.py src/argus/services/app.py
```

Expected: PASS.

- [ ] **Step 3: Run frontend tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/hooks/use-operations.test.ts src/pages/Settings.test.tsx src/components/layout/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 4: Build frontend**

Run:

```bash
corepack pnpm --dir frontend build
```

Expected: PASS.

- [ ] **Step 5: Browser smoke test**

Start the dev stack if needed:

```bash
docker compose -f infra/docker-compose.dev.yml up -d backend frontend
```

Open `http://127.0.0.1:3000/settings` and verify:

- page title says `Fleet and operations`
- summary cards render
- manual dev mode copy renders when no supervisor runtime is available
- a central camera shows a copyable `argus.inference.engine --camera-id` command
- native-unavailable diagnostics show a human-readable reason
- bootstrap form shows one-time secret warning after generation

- [ ] **Step 6: Final status**

Run:

```bash
git status --short --branch
```

Expected: only unrelated pre-existing untracked files remain.

---

## Plan Self-Review

- Spec coverage: Tasks 1 through 3 cover backend contracts, desired/runtime state, delivery diagnostics, and bootstrap. Tasks 4 through 6 cover frontend hooks, Operations UI, manual dev commands, nav naming, and bootstrap display. Task 7 covers verification.
- Placeholder scan: no task uses undefined "fill in" work. Future lifecycle controls are explicitly out of phase 1 scope.
- Type consistency: contract names used by tests and hooks match the planned Pydantic models.
- Scope check: this is a read-first workbench plus bootstrap. Supervisor command processing, process start/stop, reassignment, drain, and log streaming are intentionally left for a follow-on implementation plan.
