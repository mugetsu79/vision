from __future__ import annotations

from types import SimpleNamespace

from argus.core.config import Settings
from argus.services.app import build_app_services


def test_build_app_services_passes_settings_to_link_service() -> None:
    settings = Settings()
    services = build_app_services(
        settings=settings,
        db=SimpleNamespace(session_factory=object()),
        events=object(),
        query_service=object(),
        configuration_service=SimpleNamespace(
            llm_provider_runtime=None,
            runtime_configuration=None,
        ),
    )

    assert services.link.settings is settings
