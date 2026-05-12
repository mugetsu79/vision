from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from argus.api.contracts import (
    EvidenceStorageProfileConfig,
    OperatorConfigBindingRequest,
    OperatorConfigProfileCreate,
    OperatorConfigProfileResponse,
    OperatorConfigProfileUpdate,
    TenantContext,
)
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, decrypt_config_secret
from argus.models.enums import (
    EvidenceStorageProvider,
    EvidenceStorageScope,
    OperatorConfigProfileKind,
    OperatorConfigScope,
    OperatorConfigValidationStatus,
    RoleEnum,
)
from argus.models.tables import (
    OperatorConfigBinding,
    OperatorConfigProfile,
    OperatorConfigSecret,
)
from argus.services.operator_configuration import OperatorConfigurationService


def test_operator_configuration_enums_define_product_profile_surface() -> None:
    assert [kind.value for kind in OperatorConfigProfileKind] == [
        "evidence_storage",
        "stream_delivery",
        "runtime_selection",
        "privacy_policy",
        "llm_provider",
        "operations_mode",
    ]
    assert [scope.value for scope in OperatorConfigScope] == [
        "tenant",
        "site",
        "edge_node",
        "camera",
    ]
    assert [status.value for status in OperatorConfigValidationStatus] == [
        "unvalidated",
        "valid",
        "invalid",
    ]


def test_operator_config_profile_create_accepts_evidence_storage_config() -> None:
    profile = OperatorConfigProfileCreate.model_validate(
        {
            "kind": "evidence_storage",
            "scope": "tenant",
            "name": "Dev MinIO",
            "slug": "dev-minio",
            "is_default": True,
            "config": {
                "provider": "minio",
                "storage_scope": "central",
                "endpoint": "localhost:9000",
                "bucket": "incidents",
                "secure": False,
                "path_prefix": "dev",
            },
            "secrets": {
                "access_key": "argus",
                "secret_key": "argus-dev-secret",
            },
        }
    )

    assert profile.kind is OperatorConfigProfileKind.EVIDENCE_STORAGE
    assert profile.scope is OperatorConfigScope.TENANT
    assert profile.config == {
        "provider": "minio",
        "storage_scope": "central",
        "endpoint": "localhost:9000",
        "bucket": "incidents",
        "secure": False,
        "path_prefix": "dev",
    }
    assert profile.secrets == {
        "access_key": "argus",
        "secret_key": "argus-dev-secret",
    }
    storage_config = EvidenceStorageProfileConfig.model_validate(profile.config)
    assert storage_config.provider is EvidenceStorageProvider.MINIO
    assert storage_config.storage_scope is EvidenceStorageScope.CENTRAL


def test_operator_config_profile_response_redacts_secret_values() -> None:
    profile_id = uuid4()
    tenant_id = uuid4()
    created_at = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)

    response = OperatorConfigProfileResponse(
        id=profile_id,
        tenant_id=tenant_id,
        kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
        scope=OperatorConfigScope.TENANT,
        name="Dev MinIO",
        slug="dev-minio",
        enabled=True,
        is_default=True,
        config={
            "provider": "minio",
            "storage_scope": "central",
            "endpoint": "localhost:9000",
            "bucket": "incidents",
            "secure": False,
        },
        secret_state={"access_key": "present", "secret_key": "present"},
        validation_status=OperatorConfigValidationStatus.UNVALIDATED,
        validation_message=None,
        validated_at=None,
        config_hash="a" * 64,
        created_at=created_at,
        updated_at=created_at,
    )

    payload = response.model_dump(mode="json")

    assert payload["secret_state"] == {
        "access_key": "present",
        "secret_key": "present",
    }
    assert "secrets" not in payload
    assert "argus-dev-secret" not in str(payload)


def test_operator_config_binding_request_names_target_scope() -> None:
    profile_id = uuid4()
    camera_id = uuid4()

    binding = OperatorConfigBindingRequest(
        kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
        scope=OperatorConfigScope.CAMERA,
        scope_key=str(camera_id),
        profile_id=profile_id,
    )

    assert binding.kind is OperatorConfigProfileKind.EVIDENCE_STORAGE
    assert binding.scope is OperatorConfigScope.CAMERA
    assert binding.scope_key == str(camera_id)
    assert binding.profile_id == profile_id


@pytest.mark.asyncio
async def test_operator_config_service_create_encrypts_secrets_and_redacts_response(
    tmp_path: Path,
) -> None:
    session_factory = _OperatorConfigSessionFactory()
    audit_logger = _FakeAuditLogger()
    settings = _settings(tmp_path)
    service = OperatorConfigurationService(
        session_factory=session_factory,
        settings=settings,
        audit_logger=audit_logger,
    )
    context = _tenant_context()

    response = await service.create_profile(
        context,
        OperatorConfigProfileCreate.model_validate(
            {
                "kind": "evidence_storage",
                "scope": "tenant",
                "name": "Dev MinIO",
                "slug": "dev-minio",
                "is_default": True,
                "config": {
                    "provider": "minio",
                    "storage_scope": "central",
                    "endpoint": "localhost:9000",
                    "bucket": "incidents",
                    "secure": False,
                },
                "secrets": {
                    "access_key": "argus",
                    "secret_key": "argus-dev-secret",
                },
            }
        ),
    )

    assert response.secret_state == {"access_key": "present", "secret_key": "present"}
    assert "secrets" not in response.model_dump(mode="json")
    profile = session_factory.state["profiles"][0]
    assert isinstance(profile, OperatorConfigProfile)
    assert profile.config == {
        "provider": "minio",
        "storage_scope": "central",
        "endpoint": "localhost:9000",
        "bucket": "incidents",
        "secure": False,
    }
    assert len(profile.config_hash) == 64
    secrets = session_factory.state["secrets"]
    assert len(secrets) == 2
    encrypted_values = {secret.key: secret.encrypted_value for secret in secrets}
    assert encrypted_values["secret_key"] != "argus-dev-secret"
    assert decrypt_config_secret(encrypted_values["secret_key"], settings) == "argus-dev-secret"
    assert audit_logger.actions == ["configuration.profile.create"]


@pytest.mark.asyncio
async def test_operator_config_service_update_rotates_one_secret_and_preserves_others(
    tmp_path: Path,
) -> None:
    session_factory = _OperatorConfigSessionFactory()
    service = OperatorConfigurationService(
        session_factory=session_factory,
        settings=_settings(tmp_path),
        audit_logger=_FakeAuditLogger(),
    )
    context = _tenant_context()
    profile = await service.create_profile(
        context,
        _storage_profile_create(
            slug="dev-minio",
            secrets={"access_key": "argus", "secret_key": "first-secret"},
        ),
    )

    await service.update_profile(
        context,
        profile.id,
        OperatorConfigProfileUpdate(secrets={"secret_key": "rotated-secret"}),
    )

    secrets = {
        secret.key: decrypt_config_secret(secret.encrypted_value, service.settings)
        for secret in session_factory.state["secrets"]
    }
    assert secrets == {
        "access_key": "argus",
        "secret_key": "rotated-secret",
    }


@pytest.mark.asyncio
async def test_operator_config_service_default_clears_previous_default_for_kind(
    tmp_path: Path,
) -> None:
    session_factory = _OperatorConfigSessionFactory()
    service = OperatorConfigurationService(
        session_factory=session_factory,
        settings=_settings(tmp_path),
        audit_logger=_FakeAuditLogger(),
    )
    context = _tenant_context()

    first = await service.create_profile(
        context,
        _storage_profile_create(slug="central-minio", is_default=True),
    )
    second = await service.create_profile(
        context,
        _storage_profile_create(slug="edge-local", is_default=True),
    )

    stored = {profile.id: profile for profile in session_factory.state["profiles"]}
    assert stored[first.id].is_default is False
    assert stored[second.id].is_default is True


@pytest.mark.asyncio
async def test_operator_config_service_resolution_order_and_bootstrap_default(
    tmp_path: Path,
) -> None:
    session_factory = _OperatorConfigSessionFactory()
    service = OperatorConfigurationService(
        session_factory=session_factory,
        settings=_settings(tmp_path),
        audit_logger=_FakeAuditLogger(),
    )
    context = _tenant_context()
    camera_id = uuid4()
    site_id = uuid4()
    edge_node_id = uuid4()
    session_factory.state["cameras"].append(
        SimpleNamespace(id=camera_id, site_id=site_id, edge_node_id=edge_node_id)
    )
    tenant_profile = await service.create_profile(
        context,
        _storage_profile_create(slug="tenant-default", is_default=True),
    )
    site_profile = await service.create_profile(
        context,
        _storage_profile_create(slug="site-profile", is_default=False),
    )
    edge_profile = await service.create_profile(
        context,
        _storage_profile_create(slug="edge-profile", is_default=False),
    )
    camera_profile = await service.create_profile(
        context,
        _storage_profile_create(slug="camera-profile", is_default=False),
    )
    await service.upsert_binding(
        context,
        OperatorConfigBindingRequest(
            kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
            scope=OperatorConfigScope.SITE,
            scope_key=str(site_id),
            profile_id=site_profile.id,
        ),
    )
    await service.upsert_binding(
        context,
        OperatorConfigBindingRequest(
            kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
            scope=OperatorConfigScope.EDGE_NODE,
            scope_key=str(edge_node_id),
            profile_id=edge_profile.id,
        ),
    )
    camera_binding = await service.upsert_binding(
        context,
        OperatorConfigBindingRequest(
            kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
            scope=OperatorConfigScope.CAMERA,
            scope_key=str(camera_id),
            profile_id=camera_profile.id,
        ),
    )

    resolved = await service.resolve_profile(
        context,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        camera_id=camera_id,
    )
    assert resolved.id == camera_profile.id

    session_factory.state["bindings"].remove(
        next(
            binding
            for binding in session_factory.state["bindings"]
            if binding.id == camera_binding.id
        )
    )
    resolved = await service.resolve_profile(
        context,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        camera_id=camera_id,
    )
    assert resolved.id == edge_profile.id

    session_factory.state["bindings"] = [
        binding
        for binding in session_factory.state["bindings"]
        if binding.profile_id != edge_profile.id
    ]
    resolved = await service.resolve_profile(
        context,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        camera_id=camera_id,
    )
    assert resolved.id == site_profile.id

    session_factory.state["bindings"] = []
    resolved = await service.resolve_profile(
        context,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        camera_id=camera_id,
    )
    assert resolved.id == tenant_profile.id

    session_factory.state["profiles"] = []
    seeded = await service.resolve_profile(
        context,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        camera_id=camera_id,
    )
    assert seeded.slug == "dev-minio"


@pytest.mark.asyncio
async def test_operator_config_service_tests_local_and_remote_storage_profiles(
    tmp_path: Path,
) -> None:
    async def remote_validator(
        config: dict[str, Any],
        secrets: dict[str, str],
    ) -> tuple[OperatorConfigValidationStatus, str | None]:
        assert config["endpoint"] == "s3.local:9000"
        assert secrets["access_key"] == "argus"
        assert secrets["secret_key"] == "argus-dev-secret"
        return OperatorConfigValidationStatus.VALID, "bucket reachable"

    session_factory = _OperatorConfigSessionFactory()
    audit_logger = _FakeAuditLogger()
    service = OperatorConfigurationService(
        session_factory=session_factory,
        settings=_settings(tmp_path),
        audit_logger=audit_logger,
        remote_storage_validator=remote_validator,
    )
    context = _tenant_context()
    local_root = tmp_path / "edge-evidence"
    local_profile = await service.create_profile(
        context,
        OperatorConfigProfileCreate.model_validate(
            {
                "kind": "evidence_storage",
                "scope": "tenant",
                "name": "Edge local",
                "slug": "edge-local",
                "config": {
                    "provider": "local_filesystem",
                    "storage_scope": "edge",
                    "local_root": str(local_root),
                },
            }
        ),
    )
    remote_profile = await service.create_profile(
        context,
        _storage_profile_create(
            slug="remote-s3",
            endpoint="s3.local:9000",
            provider=EvidenceStorageProvider.S3_COMPATIBLE,
            secrets={"access_key": "argus", "secret_key": "argus-dev-secret"},
        ),
    )

    local_result = await service.test_profile(context, local_profile.id)
    remote_result = await service.test_profile(context, remote_profile.id)

    assert local_result.status is OperatorConfigValidationStatus.VALID
    assert (local_root / ".argus-write-test").exists() is False
    assert remote_result.status is OperatorConfigValidationStatus.VALID
    assert audit_logger.actions.count("configuration.profile.test") == 2


@pytest.mark.asyncio
async def test_operator_config_service_resolves_worker_privacy_policy_profile(
    tmp_path: Path,
) -> None:
    session_factory = _OperatorConfigSessionFactory()
    service = OperatorConfigurationService(
        session_factory=session_factory,
        settings=_settings(tmp_path),
        audit_logger=_FakeAuditLogger(),
    )
    context = _tenant_context()
    camera_id = uuid4()
    session_factory.state["cameras"].append(
        SimpleNamespace(id=camera_id, site_id=uuid4(), edge_node_id=None)
    )
    profile = await service.create_profile(
        context,
        OperatorConfigProfileCreate.model_validate(
            {
                "kind": "privacy_policy",
                "scope": "tenant",
                "name": "Strict Edge Privacy",
                "slug": "strict-edge-privacy",
                "is_default": True,
                "config": {
                    "retention_days": 7,
                    "storage_quota_bytes": 4096,
                    "plaintext_plate_storage": "blocked",
                    "residency": "edge",
                },
            }
        ),
    )

    resolved = await service.resolve_worker_privacy_policy(context, camera_id=camera_id)

    assert resolved.profile_id == profile.id
    assert resolved.profile_name == "Strict Edge Privacy"
    assert resolved.profile_hash == profile.config_hash
    assert resolved.retention_days == 7
    assert resolved.storage_quota_bytes == 4096
    assert resolved.plaintext_plate_storage == "blocked"
    assert resolved.residency == "edge"


@pytest.mark.asyncio
async def test_operator_config_service_audits_binding_and_delete(
    tmp_path: Path,
) -> None:
    session_factory = _OperatorConfigSessionFactory()
    audit_logger = _FakeAuditLogger()
    service = OperatorConfigurationService(
        session_factory=session_factory,
        settings=_settings(tmp_path),
        audit_logger=audit_logger,
    )
    context = _tenant_context()
    profile = await service.create_profile(context, _storage_profile_create(slug="dev-minio"))

    binding = await service.upsert_binding(
        context,
        OperatorConfigBindingRequest(
            kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
            scope=OperatorConfigScope.CAMERA,
            scope_key=str(uuid4()),
            profile_id=profile.id,
        ),
    )
    await service.delete_profile(context, profile.id)

    assert binding.profile_id == profile.id
    assert "configuration.binding.upsert" in audit_logger.actions
    assert "configuration.profile.delete" in audit_logger.actions


def _tenant_context() -> TenantContext:
    tenant_id = uuid4()
    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=str(tenant_id),
            claims={},
        ),
    )


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        config_encryption_key="argus-dev-config-key",
        incident_local_storage_root=str(tmp_path / "evidence"),
    )


def _storage_profile_create(
    *,
    slug: str,
    is_default: bool = False,
    endpoint: str = "localhost:9000",
    provider: EvidenceStorageProvider = EvidenceStorageProvider.MINIO,
    secrets: dict[str, str] | None = None,
) -> OperatorConfigProfileCreate:
    return OperatorConfigProfileCreate.model_validate(
        {
            "kind": "evidence_storage",
            "scope": "tenant",
            "name": slug.replace("-", " ").title(),
            "slug": slug,
            "is_default": is_default,
            "config": {
                "provider": provider.value,
                "storage_scope": "central",
                "endpoint": endpoint,
                "bucket": "incidents",
                "secure": False,
            },
            "secrets": secrets or {},
        }
    )


class _FakeAuditLogger:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @property
    def actions(self) -> list[str]:
        return [call["action"] for call in self.calls]

    async def record(
        self,
        *,
        tenant_context: TenantContext,
        action: str,
        target: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.calls.append(
            {
                "tenant_id": tenant_context.tenant_id,
                "action": action,
                "target": target,
                "meta": meta,
            }
        )


class _OperatorConfigResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def scalar_one_or_none(self) -> Any | None:
        return self.values[0] if self.values else None

    def scalars(self) -> _OperatorConfigResult:
        return self

    def all(self) -> list[Any]:
        return self.values


class _OperatorConfigSession:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state

    async def __aenter__(self) -> _OperatorConfigSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement):  # noqa: ANN001
        sql = str(statement)
        if "operator_config_secrets" in sql:
            return _OperatorConfigResult(list(self.state["secrets"]))
        if "operator_config_bindings" in sql:
            return _OperatorConfigResult(list(self.state["bindings"]))
        if "cameras" in sql:
            return _OperatorConfigResult(list(self.state["cameras"]))
        return _OperatorConfigResult(list(self.state["profiles"]))

    async def get(self, model, identifier):  # noqa: ANN001
        key = {
            OperatorConfigProfile: "profiles",
            OperatorConfigSecret: "secrets",
            OperatorConfigBinding: "bindings",
        }.get(model)
        if key is None:
            return None
        return next((item for item in self.state[key] if item.id == identifier), None)

    def add(self, item: Any) -> None:
        item.id = item.id or uuid4()
        if isinstance(item, OperatorConfigProfile):
            self.state["profiles"].append(item)
            return
        if isinstance(item, OperatorConfigSecret):
            self.state["secrets"].append(item)
            return
        if isinstance(item, OperatorConfigBinding):
            self.state["bindings"].append(item)

    async def delete(self, item: Any) -> None:
        for key in ("profiles", "secrets", "bindings"):
            values = self.state[key]
            if item in values:
                values.remove(item)

    async def commit(self) -> None:
        self.state["commits"] += 1

    async def rollback(self) -> None:
        self.state["rollbacks"] += 1

    async def refresh(self, item: Any) -> None:
        item.created_at = item.created_at or datetime.now(tz=UTC)
        if hasattr(item, "updated_at"):
            item.updated_at = item.updated_at or item.created_at


class _OperatorConfigSessionFactory:
    def __init__(self) -> None:
        self.state: dict[str, Any] = {
            "profiles": [],
            "secrets": [],
            "bindings": [],
            "cameras": [],
            "commits": 0,
            "rollbacks": 0,
        }

    def __call__(self) -> _OperatorConfigSession:
        return _OperatorConfigSession(self.state)
