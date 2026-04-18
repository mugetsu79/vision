from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Argus | The OmniSight Platform"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    db_url: str = "postgresql+asyncpg://argus:argus@localhost:5432/argus"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://127.0.0.1:4222"
    nats_nkey_seed: SecretStr | None = None
    nats_connect_timeout_seconds: float = 5.0

    api_base_url: str = "http://localhost:8000"

    mediamtx_url: str = "http://localhost:8889"
    mediamtx_api_url: str = "http://localhost:9997"
    mediamtx_rtsp_base_url: str = "rtsp://localhost:8554"
    mediamtx_whip_base_url: str = "http://localhost:8889"
    mediamtx_username: str | None = None
    mediamtx_password: SecretStr | None = None

    keycloak_server_url: str = "http://localhost:8080"
    keycloak_public_server_url: str | None = None
    keycloak_issuer: str = "http://localhost:8080/realms/argus-dev"
    keycloak_platform_realm: str = "platform-admin"
    keycloak_jwks_cache_ttl_seconds: int = 3600

    rtsp_encryption_key: SecretStr = SecretStr("argus-dev-rtsp-key")

    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    llm_ollama_base_url: str = "http://localhost:11434"
    llm_vllm_base_url: str = "http://localhost:8001"

    otel_service_name: str = "argus-backend"
    otlp_endpoint: str = "http://localhost:4318"
    metrics_namespace: str = "argus"
    publish_profile: str | None = None
    websocket_telemetry_buffer_size: int = 32

    enable_startup_services: bool = True
    enable_nats: bool = True
    enable_tracing: bool = True
    tenant_privacy_policies: dict[str, dict[str, object]] = Field(default_factory=dict)

    edge_api_keys: dict[str, list[str]] = Field(
        default_factory=lambda: {"dev-edge-key": ["/api/v1/edge/*"]}
    )
    edge_api_key_header: str = "X-Edge-Key"

    model_config = SettingsConfigDict(
        env_prefix="ARGUS_",
        env_file=(".env", ".env.local"),
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    @property
    def keycloak_realms_base_url(self) -> str:
        return f"{self.keycloak_server_url.rstrip('/')}/realms"

    @property
    def keycloak_trusted_realms_base_urls(self) -> tuple[str, ...]:
        trusted_urls = [self.keycloak_realms_base_url]
        if self.keycloak_public_server_url is not None:
            trusted_urls.append(f"{self.keycloak_public_server_url.rstrip('/')}/realms")
        return tuple(dict.fromkeys(trusted_urls))

    @property
    def platform_admin_issuer(self) -> str:
        return f"{self.keycloak_realms_base_url}/{self.keycloak_platform_realm}"


settings = Settings()
