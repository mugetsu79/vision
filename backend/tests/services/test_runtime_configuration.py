from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, encrypt_config_secret
from argus.models.enums import (
    OperatorConfigProfileKind,
    OperatorConfigScope,
    OperatorConfigValidationStatus,
    RoleEnum,
)
from argus.models.tables import OperatorConfigBinding, OperatorConfigProfile, OperatorConfigSecret
from argus.services.runtime_configuration import RuntimeConfigurationService


@pytest.mark.asyncio
async def test_runtime_configuration_reports_effective_profiles_and_secret_state() -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    edge_node_id = uuid4()
    camera_id = uuid4()
    settings = _settings()
    session_factory = _RuntimeConfigSessionFactory()
    session_factory.state["cameras"].append(
        SimpleNamespace(id=camera_id, site_id=site_id, edge_node_id=edge_node_id)
    )
    session_factory.state["sites"].append(SimpleNamespace(id=site_id, tenant_id=tenant_id))

    defaults = [
        _profile(tenant_id, kind, slug=f"default-{kind.value}", is_default=True)
        for kind in OperatorConfigProfileKind
    ]
    session_factory.state["profiles"].extend(defaults)
    site_profile = _profile(
        tenant_id,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        slug="site-storage",
    )
    edge_profile = _profile(
        tenant_id,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        slug="edge-storage",
    )
    camera_profile = _profile(
        tenant_id,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        slug="camera-storage",
        config={"provider": "minio", "bucket": "incidents"},
    )
    session_factory.state["profiles"].extend([site_profile, edge_profile, camera_profile])
    session_factory.state["bindings"].extend(
        [
            _binding(tenant_id, site_profile, OperatorConfigScope.SITE, str(site_id)),
            _binding(tenant_id, edge_profile, OperatorConfigScope.EDGE_NODE, str(edge_node_id)),
            _binding(tenant_id, camera_profile, OperatorConfigScope.CAMERA, str(camera_id)),
        ]
    )
    session_factory.state["secrets"].append(
        _secret(tenant_id, camera_profile.id, "secret_key", "camera-secret", settings)
    )
    service = RuntimeConfigurationService(session_factory, settings)

    resolved = await service.resolve_all_for_camera(
        _tenant_context(tenant_id),
        camera_id=camera_id,
    )

    assert set(resolved.entries) == set(OperatorConfigProfileKind)
    storage = resolved.entries[OperatorConfigProfileKind.EVIDENCE_STORAGE]
    assert storage.profile_id == camera_profile.id
    assert storage.profile_name == "Camera Storage"
    assert storage.profile_slug == "camera-storage"
    assert storage.profile_hash == camera_profile.config_hash
    assert storage.winner_scope is OperatorConfigScope.CAMERA
    assert storage.winner_scope_key == str(camera_id)
    assert storage.validation_status is OperatorConfigValidationStatus.VALID
    assert storage.resolution_status == "resolved"
    assert storage.applies_to_runtime is True
    assert storage.secret_state == {"secret_key": "present"}
    assert "camera-secret" not in resolved.model_dump_json()

    operations = resolved.entries[OperatorConfigProfileKind.OPERATIONS_MODE]
    assert operations.applies_to_runtime is True
    assert operations.operator_message is None


@pytest.mark.asyncio
async def test_runtime_configuration_reports_disabled_or_invalid_winners_as_unresolved() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    settings = _settings()
    session_factory = _RuntimeConfigSessionFactory()
    session_factory.state["cameras"].append(
        SimpleNamespace(id=camera_id, site_id=None, edge_node_id=None)
    )
    valid_default = _profile(
        tenant_id,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        slug="tenant-storage",
        is_default=True,
    )
    disabled_camera = _profile(
        tenant_id,
        OperatorConfigProfileKind.EVIDENCE_STORAGE,
        slug="disabled-camera-storage",
        enabled=False,
    )
    invalid_runtime = _profile(
        tenant_id,
        OperatorConfigProfileKind.RUNTIME_SELECTION,
        slug="invalid-runtime",
        is_default=True,
        validation_status=OperatorConfigValidationStatus.INVALID,
        validation_message="TensorRT artifact missing.",
    )
    session_factory.state["profiles"].extend([valid_default, disabled_camera, invalid_runtime])
    session_factory.state["bindings"].append(
        _binding(tenant_id, disabled_camera, OperatorConfigScope.CAMERA, str(camera_id))
    )
    service = RuntimeConfigurationService(session_factory, settings)

    resolved = await service.resolve_all_for_camera(
        _tenant_context(tenant_id),
        camera_id=camera_id,
    )

    storage = resolved.entries[OperatorConfigProfileKind.EVIDENCE_STORAGE]
    assert storage.resolution_status == "unresolved"
    assert storage.profile_id == disabled_camera.id
    assert storage.profile_slug == "disabled-camera-storage"
    assert "disabled" in (storage.operator_message or "")

    runtime = resolved.entries[OperatorConfigProfileKind.RUNTIME_SELECTION]
    assert runtime.resolution_status == "unresolved"
    assert runtime.profile_id == invalid_runtime.id
    assert runtime.profile_slug == "invalid-runtime"
    assert "TensorRT artifact missing" in (runtime.operator_message or "")


@pytest.mark.asyncio
async def test_runtime_configuration_service_only_resolver_can_decrypt_secrets() -> None:
    tenant_id = uuid4()
    settings = _settings()
    session_factory = _RuntimeConfigSessionFactory()
    profile = _profile(
        tenant_id,
        OperatorConfigProfileKind.LLM_PROVIDER,
        slug="tenant-llm",
        is_default=True,
    )
    session_factory.state["profiles"].append(profile)
    session_factory.state["secrets"].append(
        _secret(tenant_id, profile.id, "api_key", "sk-runtime-secret", settings)
    )
    service = RuntimeConfigurationService(session_factory, settings)

    runtime = await service.resolve_profile_for_runtime(
        _tenant_context(tenant_id),
        OperatorConfigProfileKind.LLM_PROVIDER,
    )
    browser = await service.resolve_all_for_camera(_tenant_context(tenant_id))

    assert runtime.profile_id == profile.id
    assert runtime.secrets == {"api_key": "sk-runtime-secret"}
    assert browser.entries[OperatorConfigProfileKind.LLM_PROVIDER].secret_state == {
        "api_key": "present"
    }
    assert "sk-runtime-secret" not in browser.model_dump_json()


def _tenant_context(tenant_id: UUID) -> TenantContext:
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


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        config_encryption_key="argus-dev-config-key",
    )


def _profile(
    tenant_id: UUID,
    kind: OperatorConfigProfileKind,
    *,
    slug: str,
    is_default: bool = False,
    enabled: bool = True,
    validation_status: OperatorConfigValidationStatus = OperatorConfigValidationStatus.VALID,
    validation_message: str | None = None,
    config: dict[str, object] | None = None,
) -> OperatorConfigProfile:
    created_at = datetime(2026, 5, 12, 12, 0, tzinfo=UTC)
    return OperatorConfigProfile(
        id=uuid4(),
        tenant_id=tenant_id,
        site_id=None,
        edge_node_id=None,
        camera_id=None,
        kind=kind,
        scope=OperatorConfigScope.TENANT,
        name=slug.replace("-", " ").title(),
        slug=slug,
        enabled=enabled,
        is_default=is_default,
        config=config or {},
        validation_status=validation_status,
        validation_message=validation_message,
        validated_at=(
            created_at
            if validation_status is not OperatorConfigValidationStatus.UNVALIDATED
            else None
        ),
        config_hash=kind.value[0] * 64,
        created_at=created_at,
        updated_at=created_at,
    )


def _binding(
    tenant_id: UUID,
    profile: OperatorConfigProfile,
    scope: OperatorConfigScope,
    scope_key: str,
) -> OperatorConfigBinding:
    created_at = datetime(2026, 5, 12, 12, 0, tzinfo=UTC)
    return OperatorConfigBinding(
        id=uuid4(),
        tenant_id=tenant_id,
        kind=profile.kind,
        scope=scope,
        scope_key=scope_key,
        profile_id=profile.id,
        created_at=created_at,
        updated_at=created_at,
    )


def _secret(
    tenant_id: UUID,
    profile_id: UUID,
    key: str,
    value: str,
    settings: Settings,
) -> OperatorConfigSecret:
    created_at = datetime(2026, 5, 12, 12, 0, tzinfo=UTC)
    return OperatorConfigSecret(
        id=uuid4(),
        tenant_id=tenant_id,
        profile_id=profile_id,
        key=key,
        encrypted_value=encrypt_config_secret(value, settings),
        value_fingerprint="f" * 64,
        created_at=created_at,
        updated_at=created_at,
    )


class _RuntimeConfigResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def scalars(self) -> _RuntimeConfigResult:
        return self

    def all(self) -> list[Any]:
        return self.values


class _RuntimeConfigSession:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state

    async def __aenter__(self) -> _RuntimeConfigSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement):  # noqa: ANN001
        sql = str(statement)
        if "operator_config_secrets" in sql:
            return _RuntimeConfigResult(list(self.state["secrets"]))
        if "operator_config_bindings" in sql:
            return _RuntimeConfigResult(list(self.state["bindings"]))
        if "sites" in sql:
            return _RuntimeConfigResult(list(self.state["sites"]))
        if "cameras" in sql:
            return _RuntimeConfigResult(list(self.state["cameras"]))
        return _RuntimeConfigResult(list(self.state["profiles"]))

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
        if isinstance(item, OperatorConfigProfile):
            self.state["profiles"].append(item)
        elif isinstance(item, OperatorConfigSecret):
            self.state["secrets"].append(item)
        elif isinstance(item, OperatorConfigBinding):
            self.state["bindings"].append(item)

    async def commit(self) -> None:
        return None

    async def refresh(self, item: Any) -> None:
        return None


class _RuntimeConfigSessionFactory:
    def __init__(self) -> None:
        self.state: dict[str, Any] = {
            "profiles": [],
            "secrets": [],
            "bindings": [],
            "cameras": [],
            "sites": [],
        }

    def __call__(self) -> _RuntimeConfigSession:
        return _RuntimeConfigSession(self.state)
