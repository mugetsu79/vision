from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import TenantContext
from argus.core.config import Settings
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.core.security import (
    AuthenticatedUser,
    get_current_user,
    get_current_websocket_user,
)
from argus.main import create_app
from argus.models.enums import RoleEnum
from argus.services.query import QueryService, QueryServiceResult


@dataclass
class StubInventory:
    async def allowed_classes_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> list[str]:
        return ["bus", "car", "truck"]


@dataclass
class StubParser:
    async def resolve_classes(
        self,
        *,
        prompt: str,
        allowed_classes: list[str],
    ) -> QueryServiceResult:
        return QueryServiceResult(
            resolved_classes=["bus", "truck"],
            provider="keyword-fallback",
            model="fallback",
            latency_ms=3,
        )


@dataclass
class NullAuditLogger:
    async def record_query(
        self,
        *,
        tenant_context: TenantContext,
        prompt: str,
        resolved_classes: list[str],
        provider: str,
        model: str,
        latency_ms: int,
    ) -> None:
        return None


@dataclass
class StubTenancy:
    context: TenantContext

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        return self.context


@dataclass
class QueryOnlyServices:
    tenancy: StubTenancy
    query: QueryService


@pytest.mark.asyncio
async def test_query_route_publishes_nats_command_within_one_second() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=True,
        enable_tracing=False,
        nats_url=os.getenv("TRAFFIC_MONITOR_TEST_NATS_URL", "nats://127.0.0.1:4222"),
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    events = NatsJetStreamClient(settings)

    try:
        await events.connect()
    except Exception as exc:  # pragma: no cover - integration guard
        pytest.skip(f"NATS is not available for Prompt 5 verification: {exc}")

    camera_id = uuid4()
    received: asyncio.Future[EventMessage] = asyncio.get_running_loop().create_future()

    async def handle_message(message: EventMessage) -> None:
        if not received.done():
            received.set_result(message)

    subscription = await events.subscribe(f"cmd.camera.{camera_id}", handle_message)
    user = AuthenticatedUser(
        subject="operator-1",
        email="operator@argus.local",
        role=RoleEnum.OPERATOR,
        issuer="http://localhost:8080/realms/traffic-monitor-dev",
        realm="traffic-monitor-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=UUID(str(user.tenant_context)),
        tenant_slug="traffic-monitor-dev",
        user=user,
    )
    app = create_app(settings=settings)
    app.state.events = events
    app.state.services = QueryOnlyServices(
        tenancy=StubTenancy(tenant_context),
        query=QueryService(
            inventory=StubInventory(),
            parser=StubParser(),
            events=events,
            audit_logger=NullAuditLogger(),
        ),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_websocket_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/query",
            json={
                "prompt": "only watch buses and trucks",
                "camera_ids": [str(camera_id)],
            },
        )

    message = await asyncio.wait_for(received, timeout=1)

    assert response.status_code == 200
    assert response.json()["resolved_classes"] == ["bus", "truck"]
    assert message.subject == f"cmd.camera.{camera_id}"

    await subscription.unsubscribe()
    await events.close()
