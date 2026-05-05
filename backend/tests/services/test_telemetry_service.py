from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from nats.js import api as js_api

from argus.api.contracts import TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum
from argus.services.app import NatsTelemetryService


class _FakeSubscription:
    async def unsubscribe(self) -> None:
        return None


class _FakeEventClient:
    def __init__(self) -> None:
        self.subject: str | None = None
        self.kwargs: dict[str, Any] = {}

    async def subscribe(self, subject: str, handler: Any, **kwargs: Any) -> _FakeSubscription:
        self.subject = subject
        self.kwargs = kwargs
        return _FakeSubscription()


@pytest.mark.asyncio
async def test_telemetry_subscription_only_receives_new_frames() -> None:
    event_client = _FakeEventClient()
    service = NatsTelemetryService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    allowed_camera_id = uuid4()

    async def camera_ids_for_tenant(_tenant_context: TenantContext) -> set[Any]:
        return {allowed_camera_id}

    service._camera_ids_for_tenant = camera_ids_for_tenant  # type: ignore[method-assign]
    tenant_context = TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )

    subscription = await service.subscribe(tenant_context)

    assert event_client.subject == "evt.tracking.*"
    assert event_client.kwargs["deliver_policy"] is js_api.DeliverPolicy.NEW

    await subscription.close()
