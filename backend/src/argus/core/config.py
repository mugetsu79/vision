from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from argus.vision.runtime import ExecutionProfile, ExecutionProvider


class Settings(BaseSettings):
    app_name: str = "Vezor | The OmniSight Platform"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    db_url: str = "postgresql+asyncpg://argus:argus@localhost:5432/argus"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://127.0.0.1:4222"
    nats_nkey_seed: SecretStr | None = None
    nats_connect_timeout_seconds: float = 5.0

    api_base_url: str = "http://localhost:8000"
    api_bearer_token: SecretStr | None = None
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    mediamtx_url: str = "http://localhost:8889"
    mediamtx_api_url: str = "http://localhost:9997"
    mediamtx_rtsp_base_url: str = "rtsp://localhost:8554"
    mediamtx_webrtc_base_url: str = "http://localhost:8889"
    mediamtx_hls_base_url: str = "http://localhost:8888"
    mediamtx_mjpeg_base_url: str = "http://localhost:8888"
    mediamtx_mjpeg_path_template: str = "{base}/{path}/mjpeg"
    mediamtx_whip_base_url: str = "http://localhost:8889"
    edge_mediamtx_rtsp_base_urls: dict[str, str] = Field(default_factory=dict)
    mediamtx_username: str | None = None
    mediamtx_password: SecretStr | None = None
    mediamtx_jwt_issuer: str = "argus-mediamtx"
    mediamtx_jwt_audience: str = "mediamtx"
    mediamtx_jwt_ttl_seconds: int = 60
    mediamtx_jwt_worker_ttl_seconds: int = 86_400
    mediamtx_jwt_key_id: str = "argus-mediamtx-dev"
    mediamtx_jwt_private_key_pem: SecretStr | None = None

    keycloak_server_url: str = "http://localhost:8080"
    keycloak_public_server_url: str | None = None
    keycloak_issuer: str = "http://localhost:8080/realms/argus-dev"
    keycloak_platform_realm: str = "platform-admin"
    keycloak_jwks_cache_ttl_seconds: int = 3600

    rtsp_encryption_key: SecretStr = SecretStr("argus-dev-rtsp-key")
    config_encryption_key: SecretStr = SecretStr("argus-dev-config-key")

    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    llm_ollama_base_url: str = "http://localhost:11434"
    llm_vllm_base_url: str = "http://localhost:8001"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "argus"
    minio_secret_key: SecretStr = SecretStr("argus-dev-secret")
    minio_secure: bool = False
    minio_incidents_bucket: str = "incidents"
    incident_storage_provider: Literal[
        "local_filesystem",
        "minio",
        "s3_compatible",
    ] = "minio"
    incident_storage_scope: Literal["edge", "central", "cloud"] = "central"
    incident_local_storage_root: str = "./var/evidence"
    incident_clip_pre_seconds: int = 10
    incident_clip_post_seconds: int = 10
    incident_clip_fps: int = 10

    otel_service_name: str = "argus-backend"
    otlp_endpoint: str = "http://localhost:4318"
    metrics_namespace: str = "argus"
    enable_worker_metrics_server: bool = False
    worker_metrics_port: int = 9108
    worker_diagnostics_enabled: bool = False
    publish_profile: str | None = None
    inference_execution_provider_override: ExecutionProvider | None = None
    inference_execution_profile_override: ExecutionProfile | None = None
    inference_session_inter_op_threads: int | None = Field(default=None, ge=1)
    inference_session_intra_op_threads: int | None = Field(default=None, ge=1)
    tracking_persistence_queue_size: int = Field(default=256, ge=1)
    tracking_persistence_batch_size: int = Field(default=16, ge=1)
    tracking_persistence_batch_flush_interval_seconds: float = Field(default=0.1, gt=0)
    tracking_persistence_shutdown_timeout_seconds: float = Field(default=5.0, gt=0)
    telemetry_publish_queue_size: int = Field(default=64, ge=1)
    telemetry_publish_shutdown_timeout_seconds: float = Field(default=2.0, gt=0)
    websocket_telemetry_buffer_size: int = 32
    video_feed_max_concurrent_per_user: int = 10

    enable_startup_services: bool = True
    enable_nats: bool = True
    enable_tracing: bool = True
    tenant_privacy_policies: dict[str, dict[str, object]] = Field(default_factory=dict)
    local_bootstrap_allowed_client_hosts: tuple[str, ...] = (
        "127.0.0.1",
        "::1",
        "localhost",
        "testclient",
        "test",
        "192.168.65.1",
        "172.17.0.1",
        "172.18.0.1",
    )

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
        trusted_urls = _loopback_aliases(self.keycloak_realms_base_url)
        if self.keycloak_public_server_url is not None:
            trusted_urls.extend(
                _loopback_aliases(f"{self.keycloak_public_server_url.rstrip('/')}/realms")
            )
        return tuple(dict.fromkeys(trusted_urls))

    @property
    def platform_admin_issuer(self) -> str:
        return f"{self.keycloak_realms_base_url}/{self.keycloak_platform_realm}"


settings = Settings()


def _loopback_aliases(url: str) -> list[str]:
    parsed = urlsplit(url)
    hostname = parsed.hostname

    if hostname not in {"localhost", "127.0.0.1"}:
        return [url]

    aliases: list[str] = []
    for candidate_host in ("localhost", "127.0.0.1"):
        netloc = candidate_host
        if parsed.port is not None:
            netloc = f"{netloc}:{parsed.port}"
        aliases.append(
            urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
        )
    return aliases
