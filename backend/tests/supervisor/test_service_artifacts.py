from __future__ import annotations

import pytest

from argus.supervisor.service_artifacts import (
    ServiceArtifactConfig,
    assert_no_embedded_long_lived_secret,
    render_compose_service,
    render_launchd_plist,
    render_systemd_unit,
)


def test_systemd_unit_uses_dedicated_user_restart_and_credential_reference() -> None:
    unit = render_systemd_unit(ServiceArtifactConfig(supervisor_id="central-1"))

    assert "User=vezor" in unit
    assert "Group=vezor" in unit
    assert "Restart=on-failure" in unit
    assert "StateDirectory=vezor" in unit
    assert "LogsDirectory=vezor" in unit
    assert "LoadCredential=supervisor-credential:" in unit
    assert "--config /etc/vezor/supervisor.json" in unit
    assert_no_embedded_long_lived_secret(unit)


def test_launchd_plist_restarts_daemon_and_references_config_path() -> None:
    plist = render_launchd_plist(ServiceArtifactConfig(supervisor_id="central-1"))

    assert "<key>Label</key>" in plist
    assert "com.vezor.supervisor" in plist
    assert "<key>RunAtLoad</key>" in plist
    assert "<key>KeepAlive</key>" in plist
    assert "/etc/vezor/supervisor.json" in plist
    assert "Bearer " not in plist
    assert_no_embedded_long_lived_secret(plist)


def test_compose_service_has_healthcheck_restart_and_mounted_credentials() -> None:
    compose = render_compose_service(ServiceArtifactConfig(supervisor_id="edge-1"))

    assert "restart: unless-stopped" in compose
    assert "healthcheck:" in compose
    assert "/etc/vezor/supervisor.json:ro" in compose
    assert "/run/vezor/credentials:ro" in compose
    assert "ARGUS_API_BEARER_TOKEN" not in compose
    assert_no_embedded_long_lived_secret(compose)


@pytest.mark.parametrize(
    "text",
    [
        "Authorization: Bearer abc",
        "ARGUS_API_BEARER_TOKEN=abc",
        "password=token-password",
    ],
)
def test_secret_assertion_rejects_embedded_token_material(text: str) -> None:
    with pytest.raises(ValueError, match="long-lived secret"):
        assert_no_embedded_long_lived_secret(text)
