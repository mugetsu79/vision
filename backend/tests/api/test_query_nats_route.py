from __future__ import annotations

import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import QueryRequest, TenantContext
from argus.core.config import Settings
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.core.security import (
    AuthenticatedUser,
    get_current_user,
    get_current_websocket_user,
)
from argus.main import create_app
from argus.models.enums import QueryResolutionMode, RoleEnum, RuntimeVocabularySource
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


@dataclass(slots=True, frozen=True)
class StubDetectorContext:
    resolution_mode: QueryResolutionMode
    allowed_classes: list[str]
    runtime_vocabulary: list[str]
    runtime_vocabulary_version: int = 0
    max_runtime_terms: int | None = None


@dataclass
class FixedVocabInventory(StubInventory):
    async def detector_context_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> StubDetectorContext:
        return StubDetectorContext(
            resolution_mode=QueryResolutionMode.FIXED_FILTER,
            allowed_classes=["bus", "car", "truck"],
            runtime_vocabulary=[],
        )


@dataclass
class OpenVocabInventory(StubInventory):
    async def allowed_classes_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> list[str]:
        return ["forklift", "pallet jack"]

    async def detector_context_for_cameras(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
    ) -> StubDetectorContext:
        return StubDetectorContext(
            resolution_mode=QueryResolutionMode.OPEN_VOCAB,
            allowed_classes=["forklift", "pallet jack"],
            runtime_vocabulary=["forklift"],
            runtime_vocabulary_version=1,
            max_runtime_terms=32,
        )


class RecordingOpenVocabInventory(OpenVocabInventory):
    def __init__(self) -> None:
        self.snapshots: list[dict[str, object]] = []

    async def record_runtime_vocabulary_snapshot(
        self,
        *,
        tenant_context: TenantContext,
        camera_ids: list[UUID],
        terms: list[str],
        source: RuntimeVocabularySource,
        version: int,
        vocabulary_hash: str,
    ) -> None:
        self.snapshots.append(
            {
                "tenant_id": tenant_context.tenant_id,
                "camera_ids": list(camera_ids),
                "terms": list(terms),
                "source": source,
                "version": version,
                "vocabulary_hash": vocabulary_hash,
            }
        )


@dataclass
class StubParser:
    resolved_classes: list[str] | None = None

    async def resolve_classes(
        self,
        *,
        prompt: str,
        allowed_classes: list[str],
    ) -> QueryServiceResult:
        return QueryServiceResult(
            resolved_classes=self.resolved_classes or ["bus", "truck"],
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
class CapturingEvents:
    published: list[tuple[str, object]]

    async def publish(self, subject: str, payload: object) -> None:
        self.published.append((subject, payload))


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


@dataclass
class RejectingQuotaEnforcer:
    async def assert_query_allowed(self, *, tenant_context: TenantContext) -> None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Tenant query rate limit exceeded.",
        )


def _expected_vocabulary_hash(terms: list[str]) -> str:
    payload = json.dumps([term.strip() for term in terms if term.strip()], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_query_service_reports_fixed_filter_mode_and_command_payload() -> None:
    camera_id = uuid4()
    tenant_context = TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )
    events = CapturingEvents(published=[])
    service = QueryService(
        inventory=FixedVocabInventory(),
        parser=StubParser(resolved_classes=["bus"]),
        events=events,
        audit_logger=NullAuditLogger(),
    )

    response = await service.resolve_query(
        tenant_context,
        payload=QueryRequest(prompt="only show buses", camera_ids=[camera_id]),
    )

    assert response.resolution_mode == QueryResolutionMode.FIXED_FILTER
    assert response.resolved_classes == ["bus"]
    assert response.resolved_vocabulary == []
    assert events.published[0][0] == f"cmd.camera.{camera_id}"
    command = events.published[0][1]
    assert command.active_classes == ["bus"]
    assert command.runtime_vocabulary is None


@pytest.mark.asyncio
async def test_query_service_reports_open_vocab_mode_and_command_payload() -> None:
    camera_id = uuid4()
    tenant_context = TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )
    events = CapturingEvents(published=[])
    service = QueryService(
        inventory=OpenVocabInventory(),
        parser=StubParser(resolved_classes=["forklift", "pallet jack"]),
        events=events,
        audit_logger=NullAuditLogger(),
    )

    response = await service.resolve_query(
        tenant_context,
        payload=QueryRequest(prompt="forklifts and pallet jacks", camera_ids=[camera_id]),
    )

    assert response.resolution_mode == QueryResolutionMode.OPEN_VOCAB
    assert response.resolved_classes == []
    assert response.resolved_vocabulary == ["forklift", "pallet jack"]
    assert events.published[0][0] == f"cmd.camera.{camera_id}"
    command = events.published[0][1]
    assert command.active_classes is None
    assert command.runtime_vocabulary == ["forklift", "pallet jack"]
    assert command.runtime_vocabulary_source == RuntimeVocabularySource.QUERY
    assert command.runtime_vocabulary_version == 2


@pytest.mark.asyncio
async def test_query_service_records_runtime_vocabulary_snapshot_for_open_vocab() -> None:
    camera_id = uuid4()
    tenant_context = TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )
    events = CapturingEvents(published=[])
    inventory = RecordingOpenVocabInventory()
    service = QueryService(
        inventory=inventory,
        parser=StubParser(resolved_classes=["forklift", "pallet jack"]),
        events=events,
        audit_logger=NullAuditLogger(),
    )

    await service.resolve_query(
        tenant_context,
        payload=QueryRequest(prompt="forklifts and pallet jacks", camera_ids=[camera_id]),
    )

    assert inventory.snapshots == [
        {
            "tenant_id": tenant_context.tenant_id,
            "camera_ids": [camera_id],
            "terms": ["forklift", "pallet jack"],
            "source": RuntimeVocabularySource.QUERY,
            "version": 2,
            "vocabulary_hash": _expected_vocabulary_hash(["forklift", "pallet jack"]),
        }
    ]


@pytest.mark.asyncio
async def test_query_route_publishes_nats_command_within_one_second() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=True,
        enable_tracing=False,
        nats_url=os.getenv("ARGUS_TEST_NATS_URL", "nats://127.0.0.1:4222"),
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
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=UUID(str(user.tenant_context)),
        tenant_slug="argus-dev",
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


@pytest.mark.asyncio
async def test_query_route_returns_429_when_tenant_rate_limit_is_exceeded() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    user = AuthenticatedUser(
        subject="operator-1",
        email="operator@argus.local",
        role=RoleEnum.OPERATOR,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )
    tenant_context = TenantContext(
        tenant_id=UUID(str(user.tenant_context)),
        tenant_slug="argus-dev",
        user=user,
    )
    app = create_app(settings=settings)
    app.state.services = QueryOnlyServices(
        tenancy=StubTenancy(tenant_context),
        query=QueryService(
            inventory=StubInventory(),
            parser=StubParser(),
            events=None,
            audit_logger=NullAuditLogger(),
            quota_enforcer=RejectingQuotaEnforcer(),
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
                "prompt": "show me buses only",
                "camera_ids": [str(uuid4())],
            },
        )

    assert response.status_code == 429
    assert response.json()["detail"] == "Tenant query rate limit exceeded."
