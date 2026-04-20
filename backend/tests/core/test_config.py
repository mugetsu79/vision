from __future__ import annotations

from argus.core.config import Settings


def test_settings_default_app_name() -> None:
    assert Settings(_env_file=None).app_name == "Vezor | The OmniSight Platform"


def test_settings_load_environment_and_secrets(monkeypatch, tmp_path) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ARGUS_RTSP_ENCRYPTION_KEY").write_text(
        "argus-secret-key",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "ARGUS_DB_URL",
        "postgresql+asyncpg://argus:argus@db.internal:5432/argus",
    )
    monkeypatch.setenv("ARGUS_NATS_URL", "nats://nats.internal:4222")
    monkeypatch.setenv("ARGUS_LLM_PROVIDER", "ollama")
    monkeypatch.setenv(
        "ARGUS_KEYCLOAK_PUBLIC_SERVER_URL",
        "https://auth.argus.example",
    )

    settings = Settings(_env_file=None, _secrets_dir=secrets_dir)

    assert settings.db_url == "postgresql+asyncpg://argus:argus@db.internal:5432/argus"
    assert settings.nats_url == "nats://nats.internal:4222"
    assert settings.llm_provider == "ollama"
    assert settings.rtsp_encryption_key.get_secret_value() == "argus-secret-key"
    assert settings.keycloak_trusted_realms_base_urls == (
        "http://localhost:8080/realms",
        "http://127.0.0.1:8080/realms",
        "https://auth.argus.example/realms",
    )


def test_loopback_keycloak_public_url_trusts_both_localhost_and_127() -> None:
    settings = Settings(
        _env_file=None,
        keycloak_server_url="http://keycloak:8080",
        keycloak_public_server_url="http://127.0.0.1:8080",
    )

    assert settings.keycloak_trusted_realms_base_urls == (
        "http://keycloak:8080/realms",
        "http://localhost:8080/realms",
        "http://127.0.0.1:8080/realms",
    )
