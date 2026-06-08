from __future__ import annotations

import pytest
from pydantic import SecretStr

from argus.core.config import Settings
from argus.main import create_app, lifespan


@pytest.mark.asyncio
async def test_app_lifespan_leaves_link_reflector_stopped_when_disabled() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            link_reflector_enabled=False,
        )
    )

    async with lifespan(app):
        assert app.state.link_reflector_runtime is None


@pytest.mark.asyncio
async def test_app_lifespan_starts_and_stops_link_reflector_when_enabled() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            link_reflector_enabled=True,
            link_reflector_bind_address="127.0.0.1",
            link_reflector_port=0,
            link_reflector_secret=SecretStr("test-reflector-secret"),
        )
    )

    async with lifespan(app):
        runtime = app.state.link_reflector_runtime
        assert runtime is not None
        assert runtime.port > 0

    assert runtime.transport.is_closing()
    assert app.state.link_reflector_runtime is None


@pytest.mark.asyncio
async def test_app_lifespan_passes_link_reflector_source_allowlist() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            link_reflector_enabled=True,
            link_reflector_bind_address="127.0.0.1",
            link_reflector_port=0,
            link_reflector_secret=SecretStr("test-reflector-secret"),
            link_reflector_allowed_source_cidrs="192.0.2.0/24",
        )
    )

    async with lifespan(app):
        runtime = app.state.link_reflector_runtime
        assert runtime is not None
        assert str(runtime.protocol.allowed_source_networks[0]) == "192.0.2.0/24"
