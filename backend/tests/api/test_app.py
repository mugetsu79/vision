from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from argus.core.config import Settings
from argus.main import create_app


@pytest.mark.asyncio
async def test_health_and_metrics_routes_are_exposed() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        health_response = await client.get("/healthz")
        metrics_response = await client.get("/metrics")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert metrics_response.status_code == 200
    assert "python_info" in metrics_response.text
    assert "argus_http_requests_total" in metrics_response.text


@pytest.mark.asyncio
async def test_cors_allows_local_frontend_origin() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.options(
            "/api/v1/sites",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
