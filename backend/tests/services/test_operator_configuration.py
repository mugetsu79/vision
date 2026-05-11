from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from argus.api.contracts import (
    EvidenceStorageProfileConfig,
    OperatorConfigBindingRequest,
    OperatorConfigProfileCreate,
    OperatorConfigProfileResponse,
)
from argus.models.enums import (
    EvidenceStorageProvider,
    EvidenceStorageScope,
    OperatorConfigProfileKind,
    OperatorConfigScope,
    OperatorConfigValidationStatus,
)


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
