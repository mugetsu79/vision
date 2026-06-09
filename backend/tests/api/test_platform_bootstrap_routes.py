from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    PlatformBootstrapComplete,
    PlatformBootstrapCompleteResponse,
    PlatformBootstrapStatusResponse,
)
from argus.api.v1 import router
from argus.core.config import Settings


class _FakePlatformBootstrapService:
    def __init__(self) -> None:
        self.complete_payload: PlatformBootstrapComplete | None = None

    async def status(self) -> PlatformBootstrapStatusResponse:
        return PlatformBootstrapStatusResponse(available=True, consumed_at=None)

    async def complete(
        self,
        payload: PlatformBootstrapComplete,
    ) -> PlatformBootstrapCompleteResponse:
        self.complete_payload = payload
        if payload.bootstrap_token != "vzplat_local_once":
            raise ValueError("Invalid platform bootstrap token.")
        return PlatformBootstrapCompleteResponse(
            email=payload.email,
            realm="platform-admin",
            role="superadmin",
            completed_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        )


def _app(platform_bootstrap: _FakePlatformBootstrapService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.settings = Settings(_env_file=None)
    app.state.services = SimpleNamespace(platform_bootstrap=platform_bootstrap)
    return app


@pytest.mark.asyncio
async def test_platform_bootstrap_status_is_unauthenticated_and_redacted() -> None:
    app = _app(_FakePlatformBootstrapService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/platform/bootstrap/status")

    assert response.status_code == 200
    assert response.json() == {"available": True, "consumed_at": None}
    assert "vzplat_" not in response.text


@pytest.mark.asyncio
async def test_platform_bootstrap_complete_consumes_local_token_without_admin_jwt() -> None:
    platform_bootstrap = _FakePlatformBootstrapService()
    app = _app(platform_bootstrap)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/platform/bootstrap/complete",
            json={
                "bootstrap_token": "vzplat_local_once",
                "email": "owner@example.com",
                "first_name": "Owner",
                "last_name": "One",
                "password": "change-me-123456",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "owner@example.com"
    assert body["realm"] == "platform-admin"
    assert body["role"] == "superadmin"
    assert "password" not in body
    assert "bootstrap_token" not in body
    assert "change-me-123456" not in response.text
    assert "vzplat_local_once" not in response.text
    assert platform_bootstrap.complete_payload is not None


@pytest.mark.asyncio
async def test_platform_bootstrap_complete_rejects_unconfigured_lan_client() -> None:
    app = _app(_FakePlatformBootstrapService())

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.168.1.40", 54123)),
        base_url="http://127.0.0.1:8000",
    ) as client:
        response = await client.post(
            "/api/v1/platform/bootstrap/complete",
            json={
                "bootstrap_token": "vzplat_local_once",
                "email": "owner@example.com",
                "first_name": "Owner",
                "last_name": "One",
                "password": "change-me-123456",
            },
        )

    assert response.status_code == 403
