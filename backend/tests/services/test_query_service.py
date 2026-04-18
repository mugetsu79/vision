from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import QueryRequest, TenantContext
from argus.core.config import Settings
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum
from argus.services.query import QueryService, QueryServiceResult


@dataclass
class StubInventory:
    allowed_classes: list[str]

    async def allowed_classes_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> list[str]:
        return self.allowed_classes


@dataclass
class StubParser:
    result: QueryServiceResult

    async def resolve_classes(
        self,
        *,
        prompt: str,
        allowed_classes: list[str],
    ) -> QueryServiceResult:
        return self.result


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


@pytest.mark.asyncio
async def test_query_service_publishes_camera_commands_over_nats() -> None:
    settings = Settings(
        _env_file=None,
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
    service = QueryService(
        inventory=StubInventory(allowed_classes=["bus", "car", "truck"]),
        parser=StubParser(
            QueryServiceResult(
                resolved_classes=["bus", "truck"],
                provider="keyword-fallback",
                model="fallback",
                latency_ms=4,
            )
        ),
        events=events,
        audit_logger=NullAuditLogger(),
    )
    tenant_context = TenantContext(
        tenant_id=uuid4(),
        tenant_slug="traffic-monitor-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost:8080/realms/traffic-monitor-dev",
            realm="traffic-monitor-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )

    response = await service.resolve_query(
        tenant_context,
        QueryRequest(
            prompt="only watch buses and trucks",
            camera_ids=[camera_id],
        ),
    )
    message = await asyncio.wait_for(received, timeout=1)

    assert response.resolved_classes == ["bus", "truck"]
    assert message.subject == f"cmd.camera.{camera_id}"
    assert "bus" in message.data
    assert "truck" in message.data

    await subscription.unsubscribe()
    await events.close()
