from __future__ import annotations

import json
import os
from ipaddress import ip_network
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import Field, SecretStr, field_validator
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
    central_supervisor_credential: SecretStr | None = None
    edge_node_id: UUID | None = None
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
    keycloak_admin_username: str | None = None
    keycloak_admin_password: SecretStr | None = None
    keycloak_frontend_client_id: str = "argus-frontend"
    keycloak_cli_client_id: str = "argus-cli"
    keycloak_frontend_url: str = "http://localhost:3000"
    keycloak_frontend_disable_pkce: bool = False

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
    worker_config_poll_interval_seconds: float = Field(default=2.0, gt=0)
    worker_runtime_report_interval_seconds: float = Field(default=10.0, gt=0)
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

    link_reflector_enabled: bool = False
    link_reflector_bind_address: str = "0.0.0.0"
    link_reflector_public_address: str | None = None
    link_reflector_port: int = Field(default=8622, ge=0, le=65_535)
    link_reflector_key_id: str = "master-reflector-default"
    link_reflector_secret: SecretStr | None = None
    link_reflector_rate_limit_pps: int = Field(default=100, ge=0)
    link_reflector_allowed_source_cidrs: str = ""
    link_throughput_payload_path: str = (
        "/var/lib/vezor/link-throughput/vezor-speed-test-64MiB.bin"
    )
    link_throughput_payload_max_bytes: int = Field(default=67_108_864, gt=0)
    link_throughput_payload_public_url: str | None = None

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
        extra="ignore",
    )

    def __init__(self, **values: Any) -> None:
        if "_secrets_dir" not in values:
            values["_secrets_dir"] = _settings_secrets_dir()
        super().__init__(**values)

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

    @property
    def keycloak_bootstrap_realm(self) -> str:
        return self.keycloak_issuer.rstrip("/").rsplit("/", 1)[-1]

    @property
    def link_reflector_allowed_source_cidr_list(self) -> tuple[str, ...]:
        return _parse_link_reflector_allowed_source_cidrs(
            self.link_reflector_allowed_source_cidrs
        )

    @field_validator("link_reflector_allowed_source_cidrs")
    @classmethod
    def _validate_link_reflector_allowed_source_cidrs(cls, value: str) -> str:
        _parse_link_reflector_allowed_source_cidrs(value)
        return value


def _settings_secrets_dir() -> str | None:
    configured = os.getenv("ARGUS_SECRETS_DIR")
    if configured:
        return configured
    default_path = Path("/run/secrets")
    return str(default_path) if default_path.is_dir() else None


def _parse_link_reflector_allowed_source_cidrs(raw_value: str) -> tuple[str, ...]:
    normalized_value = raw_value.strip()
    if not normalized_value:
        return ()
    if normalized_value.startswith("["):
        try:
            decoded = json.loads(normalized_value)
        except json.JSONDecodeError as exc:
            msg = (
                "ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS must be a valid JSON array "
                "or comma-separated CIDR list."
            )
            raise ValueError(msg) from exc
        if not isinstance(decoded, list):
            msg = "ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS must be a valid JSON array."
            raise ValueError(msg)
        candidates = [str(item).strip() for item in decoded if str(item).strip()]
    else:
        candidates = [part.strip() for part in normalized_value.split(",") if part.strip()]
    for candidate in candidates:
        try:
            ip_network(candidate, strict=False)
        except ValueError as exc:
            msg = (
                "ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS entries must be valid CIDR "
                f"networks: {candidate}"
            )
            raise ValueError(msg) from exc
    return tuple(candidates)


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
