from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    OperatorConfigBindingRequest,
    OperatorConfigBindingResponse,
    OperatorConfigProfileCreate,
    OperatorConfigProfileResponse,
    OperatorConfigProfileUpdate,
    OperatorConfigTestResponse,
    ResolvedOperatorConfigEntryResponse,
    ResolvedOperatorConfigResponse,
    TenantContext,
)
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import (
    OperatorConfigProfileKind,
    OperatorConfigScope,
    OperatorConfigValidationStatus,
    RoleEnum,
)


def _tenant_context(role: RoleEnum = RoleEnum.ADMIN) -> TenantContext:
    tenant_id = uuid4()
    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=role,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=str(tenant_id),
            claims={},
        ),
    )


class _FakeTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        return self.user


class _FakeConfigurationService:
    def __init__(self, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id
        self.created_payload: OperatorConfigProfileCreate | None = None
        self.updated_payload: OperatorConfigProfileUpdate | None = None
        self.binding_payload: OperatorConfigBindingRequest | None = None
        self.deleted_profile_id: UUID | None = None
        self.tested_profile_id: UUID | None = None
        self.profile = _profile_response(tenant_id=tenant_id)

    async def list_catalog(self) -> dict[str, object]:
        return {
            "kinds": [
                {
                    "kind": "evidence_storage",
                    "label": "Evidence storage",
                    "secret_keys": ["access_key", "secret_key"],
                }
            ]
        }

    async def list_profiles(
        self,
        tenant_context: TenantContext,
        *,
        kind: OperatorConfigProfileKind | None = None,
    ) -> list[OperatorConfigProfileResponse]:
        if kind is not None and kind is not self.profile.kind:
            return []
        return [self.profile]

    async def create_profile(
        self,
        tenant_context: TenantContext,
        payload: OperatorConfigProfileCreate,
    ) -> OperatorConfigProfileResponse:
        self.created_payload = payload
        return self.profile

    async def update_profile(
        self,
        tenant_context: TenantContext,
        profile_id: UUID,
        payload: OperatorConfigProfileUpdate,
    ) -> OperatorConfigProfileResponse:
        self.updated_payload = payload
        return self.profile.model_copy(update={"id": profile_id})

    async def delete_profile(self, tenant_context: TenantContext, profile_id: UUID) -> None:
        self.deleted_profile_id = profile_id

    async def test_profile(
        self,
        tenant_context: TenantContext,
        profile_id: UUID,
    ) -> OperatorConfigTestResponse:
        self.tested_profile_id = profile_id
        return OperatorConfigTestResponse(
            profile_id=profile_id,
            status=OperatorConfigValidationStatus.VALID,
            message="ok",
            tested_at=datetime(2026, 5, 11, 12, 0, tzinfo=UTC),
        )

    async def upsert_binding(
        self,
        tenant_context: TenantContext,
        payload: OperatorConfigBindingRequest,
    ) -> OperatorConfigBindingResponse:
        self.binding_payload = payload
        return OperatorConfigBindingResponse(
            id=uuid4(),
            tenant_id=tenant_context.tenant_id,
            created_at=datetime(2026, 5, 11, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 11, 12, 0, tzinfo=UTC),
            **payload.model_dump(),
        )

    async def resolve_all_for_camera(
        self,
        tenant_context: TenantContext,
        camera_id: UUID | None = None,
        site_id: UUID | None = None,
        edge_node_id: UUID | None = None,
    ) -> ResolvedOperatorConfigResponse:
        del site_id, edge_node_id
        return ResolvedOperatorConfigResponse(
            profiles={OperatorConfigProfileKind.EVIDENCE_STORAGE: self.profile},
            entries={
                OperatorConfigProfileKind.EVIDENCE_STORAGE: ResolvedOperatorConfigEntryResponse(
                    kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
                    profile_id=self.profile.id,
                    profile_name=self.profile.name,
                    profile_slug=self.profile.slug,
                    profile_hash=self.profile.config_hash,
                    winner_scope=(
                        OperatorConfigScope.CAMERA
                        if camera_id
                        else OperatorConfigScope.TENANT
                    ),
                    winner_scope_key=str(camera_id) if camera_id else str(tenant_context.tenant_id),
                    validation_status=self.profile.validation_status,
                    resolution_status="resolved",
                    applies_to_runtime=True,
                    secret_state=self.profile.secret_state,
                    config=self.profile.config,
                )
            },
        )


def _create_app(context: TenantContext, configuration: _FakeConfigurationService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        configuration=configuration,
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_configuration_routes_expose_catalog_and_profiles() -> None:
    context = _tenant_context()
    configuration = _FakeConfigurationService(context.tenant_id)
    app = _create_app(context, configuration)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        catalog_response = await client.get(
            "/api/v1/configuration/catalog",
            headers={"Authorization": "Bearer token"},
        )
        profiles_response = await client.get(
            "/api/v1/configuration/profiles?kind=evidence_storage",
            headers={"Authorization": "Bearer token"},
        )

    assert catalog_response.status_code == 200
    assert catalog_response.json()["kinds"][0]["kind"] == "evidence_storage"
    assert profiles_response.status_code == 200
    assert profiles_response.json()[0]["secret_state"] == {"secret_key": "present"}
    assert "secrets" not in profiles_response.text


@pytest.mark.asyncio
async def test_configuration_routes_redact_llm_provider_secrets() -> None:
    context = _tenant_context()
    configuration = _FakeConfigurationService(context.tenant_id)
    configuration.profile = _profile_response(
        tenant_id=context.tenant_id,
        kind=OperatorConfigProfileKind.LLM_PROVIDER,
        config={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key_required": True,
        },
        secret_state={"api_key": "present"},
    )
    app = _create_app(context, configuration)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/configuration/profiles?kind=llm_provider",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["kind"] == "llm_provider"
    assert payload["secret_state"] == {"api_key": "present"}
    assert "api_key" not in payload["config"]
    assert "sk-runtime" not in response.text


@pytest.mark.asyncio
async def test_configuration_routes_create_patch_test_bind_and_resolve() -> None:
    context = _tenant_context()
    configuration = _FakeConfigurationService(context.tenant_id)
    app = _create_app(context, configuration)
    profile_id = uuid4()
    camera_id = uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/api/v1/configuration/profiles",
            headers={"Authorization": "Bearer token"},
            json={
                "kind": "evidence_storage",
                "scope": "tenant",
                "name": "Dev MinIO",
                "slug": "dev-minio",
                "config": {
                    "provider": "minio",
                    "storage_scope": "central",
                    "endpoint": "localhost:9000",
                    "bucket": "incidents",
                    "secure": False,
                },
                "secrets": {"secret_key": "argus-dev-secret"},
            },
        )
        patch_response = await client.patch(
            f"/api/v1/configuration/profiles/{profile_id}",
            headers={"Authorization": "Bearer token"},
            json={"name": "Updated MinIO", "secrets": {"secret_key": "rotated"}},
        )
        test_response = await client.post(
            f"/api/v1/configuration/profiles/{profile_id}/test",
            headers={"Authorization": "Bearer token"},
        )
        binding_response = await client.post(
            "/api/v1/configuration/bindings",
            headers={"Authorization": "Bearer token"},
            json={
                "kind": "evidence_storage",
                "scope": "camera",
                "scope_key": str(camera_id),
                "profile_id": str(profile_id),
            },
        )
        resolved_response = await client.get(
            f"/api/v1/configuration/resolved?camera_id={camera_id}",
            headers={"Authorization": "Bearer token"},
        )
        delete_response = await client.delete(
            f"/api/v1/configuration/profiles/{profile_id}",
            headers={"Authorization": "Bearer token"},
        )

    assert create_response.status_code == 201
    assert configuration.created_payload is not None
    assert configuration.created_payload.secrets == {"secret_key": "argus-dev-secret"}
    assert patch_response.status_code == 200
    assert configuration.updated_payload is not None
    assert configuration.updated_payload.secrets == {"secret_key": "rotated"}
    assert test_response.status_code == 200
    assert test_response.json()["status"] == "valid"
    assert binding_response.status_code == 200
    assert configuration.binding_payload is not None
    assert configuration.binding_payload.scope is OperatorConfigScope.CAMERA
    assert resolved_response.status_code == 200
    resolved_payload = resolved_response.json()
    assert resolved_payload["profiles"]["evidence_storage"]["slug"] == "dev-minio"
    assert resolved_payload["entries"]["evidence_storage"] == {
        "kind": "evidence_storage",
        "profile_id": str(configuration.profile.id),
        "profile_name": "Dev MinIO",
        "profile_slug": "dev-minio",
        "profile_hash": "a" * 64,
        "winner_scope": "camera",
        "winner_scope_key": str(camera_id),
        "validation_status": "unvalidated",
        "resolution_status": "resolved",
        "applies_to_runtime": True,
        "secret_state": {"secret_key": "present"},
        "operator_message": None,
        "config": {
            "provider": "minio",
            "storage_scope": "central",
            "endpoint": "localhost:9000",
            "bucket": "incidents",
            "secure": False,
        },
    }
    assert "argus-dev-secret" not in resolved_response.text
    assert delete_response.status_code == 204
    assert configuration.deleted_profile_id == profile_id


def _profile_response(
    tenant_id: UUID,
    *,
    kind: OperatorConfigProfileKind = OperatorConfigProfileKind.EVIDENCE_STORAGE,
    config: dict[str, object] | None = None,
    secret_state: dict[str, str] | None = None,
) -> OperatorConfigProfileResponse:
    created_at = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    resolved_config = config or {
        "provider": "minio",
        "storage_scope": "central",
        "endpoint": "localhost:9000",
        "bucket": "incidents",
        "secure": False,
    }
    return OperatorConfigProfileResponse(
        id=uuid4(),
        tenant_id=tenant_id,
        kind=kind,
        scope=OperatorConfigScope.TENANT,
        name="Dev MinIO",
        slug="dev-minio",
        enabled=True,
        is_default=True,
        config=resolved_config,
        secret_state=secret_state or {"secret_key": "present"},
        validation_status=OperatorConfigValidationStatus.UNVALIDATED,
        validation_message=None,
        validated_at=None,
        config_hash="a" * 64,
        created_at=created_at,
        updated_at=created_at,
    )
