from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from traffic_monitor.core.config import Settings
from traffic_monitor.main import create_app


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
