from __future__ import annotations

from traffic_monitor.core.config import Settings


def test_settings_load_environment_and_secrets(monkeypatch, tmp_path) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "TRAFFIC_MONITOR_RTSP_ENCRYPTION_KEY").write_text(
        "argus-secret-key",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "TRAFFIC_MONITOR_DB_URL",
        "postgresql+asyncpg://argus:argus@db.internal:5432/argus",
    )
    monkeypatch.setenv("TRAFFIC_MONITOR_NATS_URL", "nats://nats.internal:4222")
    monkeypatch.setenv("TRAFFIC_MONITOR_LLM_PROVIDER", "ollama")
    monkeypatch.setenv(
        "TRAFFIC_MONITOR_KEYCLOAK_PUBLIC_SERVER_URL",
        "https://auth.argus.example",
    )

    settings = Settings(_env_file=None, _secrets_dir=secrets_dir)

    assert settings.db_url == "postgresql+asyncpg://argus:argus@db.internal:5432/argus"
    assert settings.nats_url == "nats://nats.internal:4222"
    assert settings.llm_provider == "ollama"
    assert settings.rtsp_encryption_key.get_secret_value() == "argus-secret-key"
    assert settings.keycloak_trusted_realms_base_urls == (
        "http://localhost:8080/realms",
        "https://auth.argus.example/realms",
    )
