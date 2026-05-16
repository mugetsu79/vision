from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    EvidenceStorageConfigProvider,
    LLMProviderProfileConfig,
    OperationsModeProfileConfig,
    OperatorConfigBindingRequest,
    OperatorConfigBindingResponse,
    OperatorConfigProfileCreate,
    OperatorConfigProfileResponse,
    OperatorConfigProfileUpdate,
    OperatorConfigTestResponse,
    PrivacyPolicyProfileConfig,
    ResolvedOperatorConfigResponse,
    RuntimeSelectionProfileConfig,
    StreamDeliveryProfileConfig,
    TenantContext,
    WorkerEvidenceStorageSettings,
    WorkerPrivacyPolicySettings,
    WorkerRuntimeSelectionSettings,
    WorkerStreamDeliverySettings,
    _normalize_operator_config,
)
from argus.compat import UTC
from argus.core.config import Settings
from argus.core.security import decrypt_config_secret, encrypt_config_secret
from argus.models.enums import (
    EvidenceStorageProvider,
    EvidenceStorageScope,
    OperatorConfigProfileKind,
    OperatorConfigScope,
    OperatorConfigValidationStatus,
)
from argus.models.tables import (
    Camera,
    OperatorConfigBinding,
    OperatorConfigProfile,
    OperatorConfigSecret,
    Site,
)
from argus.services.llm_provider_runtime import (
    LLMProviderRuntimeService,
    ResolvedLLMProviderSettings,
    resolved_llm_provider_from_runtime_config,
)
from argus.services.object_store import MinioObjectStore
from argus.services.privacy_policy_runtime import worker_privacy_policy_from_runtime_config
from argus.services.runtime_configuration import RuntimeConfigurationService

RemoteStorageValidator = Callable[
    [dict[str, Any], dict[str, str]],
    Awaitable[tuple[OperatorConfigValidationStatus, str | None]],
]


class AuditLogger(Protocol):
    async def record(
        self,
        *,
        tenant_context: TenantContext,
        action: str,
        target: str,
        meta: dict[str, Any] | None = None,
    ) -> None: ...


class OperatorConfigurationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        audit_logger: AuditLogger | None = None,
        *,
        remote_storage_validator: RemoteStorageValidator | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.audit_logger = audit_logger
        self.remote_storage_validator = remote_storage_validator
        self.runtime_configuration = RuntimeConfigurationService(
            session_factory,
            settings,
            bootstrap_defaults=self.seed_bootstrap_defaults,
        )
        self.llm_provider_runtime = LLMProviderRuntimeService(self.runtime_configuration)

    async def list_catalog(self) -> dict[str, object]:
        return {
            "kinds": [
                {
                    "kind": OperatorConfigProfileKind.EVIDENCE_STORAGE.value,
                    "label": "Evidence storage",
                    "secret_keys": ["access_key", "secret_key"],
                },
                {
                    "kind": OperatorConfigProfileKind.STREAM_DELIVERY.value,
                    "label": "Transport profile",
                    "secret_keys": [],
                },
                {
                    "kind": OperatorConfigProfileKind.RUNTIME_SELECTION.value,
                    "label": "Runtime selection",
                    "secret_keys": [],
                },
                {
                    "kind": OperatorConfigProfileKind.PRIVACY_POLICY.value,
                    "label": "Privacy policy",
                    "secret_keys": [],
                },
                {
                    "kind": OperatorConfigProfileKind.LLM_PROVIDER.value,
                    "label": "LLM provider",
                    "secret_keys": ["api_key"],
                },
                {
                    "kind": OperatorConfigProfileKind.OPERATIONS_MODE.value,
                    "label": "Operations mode",
                    "secret_keys": [],
                },
            ]
        }

    async def list_profiles(
        self,
        tenant_context: TenantContext,
        *,
        kind: OperatorConfigProfileKind | None = None,
    ) -> list[OperatorConfigProfileResponse]:
        async with self.session_factory() as session:
            profiles = await self._load_profiles(session, tenant_context.tenant_id, kind=kind)
            secrets = await self._load_secrets(session)
        return [
            _profile_to_response(profile, _secrets_for_profile(secrets, profile.id))
            for profile in sorted(profiles, key=lambda item: (item.kind.value, item.name))
        ]

    async def create_profile(
        self,
        tenant_context: TenantContext,
        payload: OperatorConfigProfileCreate,
    ) -> OperatorConfigProfileResponse:
        if payload.is_default and not payload.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Disabled configuration profiles cannot be defaults.",
            )

        async with self.session_factory() as session:
            existing = await self._load_profiles(
                session,
                tenant_context.tenant_id,
                kind=payload.kind,
            )
            if any(profile.slug == payload.slug for profile in existing):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A configuration profile with this slug already exists.",
                )
            if payload.is_default:
                _clear_default(existing)

            profile = OperatorConfigProfile(
                id=uuid4(),
                tenant_id=tenant_context.tenant_id,
                site_id=payload.site_id,
                edge_node_id=payload.edge_node_id,
                camera_id=payload.camera_id,
                kind=payload.kind,
                scope=payload.scope,
                name=payload.name,
                slug=payload.slug,
                enabled=payload.enabled,
                is_default=payload.is_default,
                config=payload.config,
                validation_status=OperatorConfigValidationStatus.UNVALIDATED,
                validation_message=None,
                validated_at=None,
                config_hash=hash_config(payload.config),
            )
            session.add(profile)
            for key, value in payload.secrets.items():
                session.add(
                    _secret_row(
                        tenant_context.tenant_id,
                        profile.id,
                        key,
                        value,
                        self.settings,
                    )
                )

            await session.commit()
            await session.refresh(profile)
            secrets = await self._load_secrets(session, profile.id)

        await self._record(
            tenant_context,
            action="configuration.profile.create",
            target=f"configuration-profile:{profile.id}",
            meta={"kind": profile.kind.value, "slug": profile.slug},
        )
        return _profile_to_response(profile, secrets)

    async def update_profile(
        self,
        tenant_context: TenantContext,
        profile_id: UUID,
        payload: OperatorConfigProfileUpdate,
    ) -> OperatorConfigProfileResponse:
        async with self.session_factory() as session:
            profile = await self._get_profile(session, tenant_context.tenant_id, profile_id)
            update_data = payload.model_dump(exclude_unset=True)
            secrets_payload = update_data.pop("secrets", None)

            if "config" in update_data and update_data["config"] is not None:
                update_data["config"] = _normalize_operator_config(
                    profile.kind,
                    update_data["config"],
                )
                update_data["config_hash"] = hash_config(update_data["config"])

            enabled_value = update_data.get("enabled", profile.enabled)
            default_value = update_data.get("is_default", profile.is_default)
            if default_value and not enabled_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Disabled configuration profiles cannot be defaults.",
                )

            if update_data.get("is_default") is True:
                profiles = await self._load_profiles(
                    session,
                    tenant_context.tenant_id,
                    kind=profile.kind,
                )
                _clear_default(profiles, except_profile_id=profile.id)

            for field_name, value in update_data.items():
                setattr(profile, field_name, value)

            if secrets_payload is not None:
                existing_secrets = await self._load_secrets(session, profile.id)
                by_key = {secret.key: secret for secret in existing_secrets}
                for key, value in secrets_payload.items():
                    secret = by_key.get(key)
                    encrypted_value = encrypt_config_secret(value, self.settings)
                    if secret is None:
                        session.add(
                            OperatorConfigSecret(
                                id=uuid4(),
                                tenant_id=tenant_context.tenant_id,
                                profile_id=profile.id,
                                key=key,
                                encrypted_value=encrypted_value,
                                value_fingerprint=_secret_fingerprint(value),
                            )
                        )
                    else:
                        secret.encrypted_value = encrypted_value
                        secret.value_fingerprint = _secret_fingerprint(value)

            await session.commit()
            await session.refresh(profile)
            secrets = await self._load_secrets(session, profile.id)

        await self._record(
            tenant_context,
            action="configuration.profile.update",
            target=f"configuration-profile:{profile.id}",
            meta={"kind": profile.kind.value, "slug": profile.slug},
        )
        return _profile_to_response(profile, secrets)

    async def delete_profile(self, tenant_context: TenantContext, profile_id: UUID) -> None:
        async with self.session_factory() as session:
            profile = await self._get_profile(session, tenant_context.tenant_id, profile_id)
            secrets = await self._load_secrets(session, profile.id)
            bindings = await self._load_bindings(session, tenant_context.tenant_id)
            for secret in secrets:
                await session.delete(secret)
            for binding in bindings:
                if binding.profile_id == profile.id:
                    await session.delete(binding)
            await session.delete(profile)
            await session.commit()

        await self._record(
            tenant_context,
            action="configuration.profile.delete",
            target=f"configuration-profile:{profile_id}",
            meta={"kind": profile.kind.value, "slug": profile.slug},
        )

    async def test_profile(
        self,
        tenant_context: TenantContext,
        profile_id: UUID,
    ) -> OperatorConfigTestResponse:
        tested_at = datetime.now(tz=UTC)
        async with self.session_factory() as session:
            profile = await self._get_profile(session, tenant_context.tenant_id, profile_id)
            secrets = await self._load_decrypted_secrets(session, profile.id)
            validation_status, message = await self._validate_profile(profile, secrets)
            profile.validation_status = validation_status
            profile.validation_message = message
            profile.validated_at = tested_at
            await session.commit()
            await session.refresh(profile)

        await self._record(
            tenant_context,
            action="configuration.profile.test",
            target=f"configuration-profile:{profile_id}",
            meta={"kind": profile.kind.value, "status": validation_status.value},
        )
        return OperatorConfigTestResponse(
            profile_id=profile_id,
            status=validation_status,
            message=message,
            tested_at=tested_at,
        )

    async def upsert_binding(
        self,
        tenant_context: TenantContext,
        payload: OperatorConfigBindingRequest,
    ) -> OperatorConfigBindingResponse:
        async with self.session_factory() as session:
            profile = await self._get_profile(session, tenant_context.tenant_id, payload.profile_id)
            if profile.kind != payload.kind:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Configuration profile kind does not match binding kind.",
                )
            if not profile.enabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Disabled configuration profiles cannot be bound.",
                )

            bindings = await self._load_bindings(session, tenant_context.tenant_id)
            binding = next(
                (
                    item
                    for item in bindings
                    if item.kind == payload.kind
                    and item.scope == payload.scope
                    and item.scope_key == payload.scope_key
                ),
                None,
            )
            if binding is None:
                binding = OperatorConfigBinding(
                    id=uuid4(),
                    tenant_id=tenant_context.tenant_id,
                    kind=payload.kind,
                    scope=payload.scope,
                    scope_key=payload.scope_key,
                    profile_id=payload.profile_id,
                )
                session.add(binding)
            else:
                binding.profile_id = payload.profile_id

            await session.commit()
            await session.refresh(binding)

        await self._record(
            tenant_context,
            action="configuration.binding.upsert",
            target=f"configuration-binding:{binding.id}",
            meta={
                "kind": binding.kind.value,
                "scope": binding.scope.value,
                "scope_key": binding.scope_key,
                "profile_id": str(binding.profile_id),
            },
        )
        return OperatorConfigBindingResponse(
            id=binding.id,
            tenant_id=binding.tenant_id,
            kind=binding.kind,
            scope=binding.scope,
            scope_key=binding.scope_key,
            profile_id=binding.profile_id,
            created_at=_created_at(binding),
            updated_at=_updated_at(binding),
        )

    async def resolve_profile(
        self,
        tenant_context: TenantContext,
        kind: OperatorConfigProfileKind,
        *,
        camera_id: UUID | None = None,
        site_id: UUID | None = None,
        edge_node_id: UUID | None = None,
    ) -> OperatorConfigProfileResponse:
        async with self.session_factory() as session:
            camera_scope = await self._camera_scope(
                session,
                tenant_context.tenant_id,
                camera_id,
            )
            resolved_site_id = site_id or camera_scope[0]
            resolved_edge_node_id = edge_node_id or camera_scope[1]
            resolved_camera_id = camera_id

            profile = await self._resolve_profile_row(
                session,
                tenant_context.tenant_id,
                kind,
                camera_id=resolved_camera_id,
                site_id=resolved_site_id,
                edge_node_id=resolved_edge_node_id,
            )
            if profile is None:
                await self.seed_bootstrap_defaults(tenant_context, session=session)
                profile = await self._resolve_profile_row(
                    session,
                    tenant_context.tenant_id,
                    kind,
                    camera_id=resolved_camera_id,
                    site_id=resolved_site_id,
                    edge_node_id=resolved_edge_node_id,
                )
            if profile is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Configuration profile could not be resolved.",
                )
            secrets = await self._load_secrets(session, profile.id)
        return _profile_to_response(profile, secrets)

    async def resolve_all_for_camera(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID | None = None,
        site_id: UUID | None = None,
        edge_node_id: UUID | None = None,
    ) -> ResolvedOperatorConfigResponse:
        return await self.runtime_configuration.resolve_all_for_camera(
            tenant_context,
            camera_id=camera_id,
            site_id=site_id,
            edge_node_id=edge_node_id,
        )

    async def resolve_worker_evidence_storage(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID,
        profile_id: UUID | None = None,
    ) -> WorkerEvidenceStorageSettings:
        async with self.session_factory() as session:
            profile: OperatorConfigProfile | None
            if profile_id is not None:
                profile = await self._get_profile(session, tenant_context.tenant_id, profile_id)
                if (
                    profile.kind != OperatorConfigProfileKind.EVIDENCE_STORAGE
                    or not profile.enabled
                ):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Evidence storage profile not found.",
                    )
            else:
                site_id, edge_node_id = await self._camera_scope(
                    session,
                    tenant_context.tenant_id,
                    camera_id,
                )
                profile = await self._resolve_profile_row(
                    session,
                    tenant_context.tenant_id,
                    OperatorConfigProfileKind.EVIDENCE_STORAGE,
                    camera_id=camera_id,
                    site_id=site_id,
                    edge_node_id=edge_node_id,
                )
                if profile is None:
                    await self.seed_bootstrap_defaults(tenant_context, session=session)
                    profile = await self._resolve_profile_row(
                        session,
                        tenant_context.tenant_id,
                        OperatorConfigProfileKind.EVIDENCE_STORAGE,
                        camera_id=camera_id,
                        site_id=site_id,
                        edge_node_id=edge_node_id,
                    )
                if profile is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Evidence storage profile could not be resolved.",
                    )
            assert profile is not None
            secrets = await self._load_decrypted_secrets(session, profile.id)
        config = dict(profile.config)
        provider_raw = str(config.get("provider", EvidenceStorageProvider.MINIO.value))
        provider: EvidenceStorageConfigProvider = (
            "local_first"
            if provider_raw == "local_first"
            else EvidenceStorageProvider(provider_raw)
        )
        return WorkerEvidenceStorageSettings(
            profile_id=profile.id,
            profile_name=profile.name,
            profile_hash=profile.config_hash,
            provider=provider,
            storage_scope=EvidenceStorageScope(
                str(config.get("storage_scope", EvidenceStorageScope.CENTRAL.value))
            ),
            config=config,
            secrets=secrets,
        )

    async def resolve_worker_stream_delivery(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID,
        profile_id: UUID | None = None,
    ) -> WorkerStreamDeliverySettings:
        runtime_config = await self.runtime_configuration.resolve_profile_for_runtime(
            tenant_context,
            OperatorConfigProfileKind.STREAM_DELIVERY,
            camera_id=camera_id,
            profile_id=profile_id,
        )
        config = StreamDeliveryProfileConfig.model_validate(runtime_config.config)
        return WorkerStreamDeliverySettings(
            profile_id=runtime_config.profile_id,
            profile_name=runtime_config.profile_name,
            profile_hash=runtime_config.profile_hash,
            delivery_mode=config.delivery_mode,
            public_base_url=config.public_base_url,
            edge_override_url=config.edge_override_url,
        )

    async def resolve_worker_runtime_selection(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID,
        profile_id: UUID | None = None,
    ) -> WorkerRuntimeSelectionSettings:
        runtime_config = await self.runtime_configuration.resolve_profile_for_runtime(
            tenant_context,
            OperatorConfigProfileKind.RUNTIME_SELECTION,
            camera_id=camera_id,
            profile_id=profile_id,
        )
        config = RuntimeSelectionProfileConfig.model_validate(runtime_config.config)
        return WorkerRuntimeSelectionSettings(
            profile_id=runtime_config.profile_id,
            profile_name=runtime_config.profile_name,
            profile_hash=runtime_config.profile_hash,
            preferred_backend=config.preferred_backend,
            artifact_preference=config.artifact_preference,
            fallback_allowed=config.fallback_allowed,
        )

    async def resolve_worker_privacy_policy(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID,
        profile_id: UUID | None = None,
    ) -> WorkerPrivacyPolicySettings:
        runtime_config = await self.runtime_configuration.resolve_profile_for_runtime(
            tenant_context,
            OperatorConfigProfileKind.PRIVACY_POLICY,
            camera_id=camera_id,
            profile_id=profile_id,
        )
        return worker_privacy_policy_from_runtime_config(runtime_config)

    async def resolve_llm_provider_for_runtime(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID | None = None,
    ) -> ResolvedLLMProviderSettings:
        return await self.llm_provider_runtime.resolve_for_prompt(
            tenant_context=tenant_context,
            camera_id=camera_id,
        )

    async def resolve_llm_provider_profile(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID | None = None,
        profile_id: UUID | None = None,
    ) -> ResolvedLLMProviderSettings:
        runtime_config = await self.runtime_configuration.resolve_profile_for_runtime(
            tenant_context,
            OperatorConfigProfileKind.LLM_PROVIDER,
            camera_id=camera_id,
            profile_id=profile_id,
        )
        return resolved_llm_provider_from_runtime_config(runtime_config)

    async def seed_bootstrap_defaults(
        self,
        tenant_context: TenantContext,
        *,
        session: AsyncSession | None = None,
    ) -> list[OperatorConfigProfileResponse]:
        owns_session = session is None
        if session is None:
            session = self.session_factory()
            await session.__aenter__()
        try:
            seeded: list[OperatorConfigProfile] = []
            existing = await self._load_profiles(session, tenant_context.tenant_id)
            for payload in self._bootstrap_profiles():
                same_slug = [
                    profile
                    for profile in existing
                    if profile.kind == payload.kind and profile.slug == payload.slug
                ]
                if same_slug:
                    continue
                if payload.is_default:
                    _clear_default(
                        [
                            profile
                            for profile in existing + seeded
                            if profile.kind == payload.kind
                        ]
                    )
                profile = OperatorConfigProfile(
                    id=uuid4(),
                    tenant_id=tenant_context.tenant_id,
                    site_id=None,
                    edge_node_id=None,
                    camera_id=None,
                    kind=payload.kind,
                    scope=payload.scope,
                    name=payload.name,
                    slug=payload.slug,
                    enabled=payload.enabled,
                    is_default=payload.is_default,
                    config=payload.config,
                    validation_status=OperatorConfigValidationStatus.UNVALIDATED,
                    validation_message=None,
                    validated_at=None,
                    config_hash=hash_config(payload.config),
                )
                session.add(profile)
                for key, value in payload.secrets.items():
                    session.add(
                        _secret_row(tenant_context.tenant_id, profile.id, key, value, self.settings)
                    )
                seeded.append(profile)
            if seeded:
                await session.commit()
                for profile in seeded:
                    await session.refresh(profile)
            secrets = await self._load_secrets(session)
            return [
                _profile_to_response(profile, _secrets_for_profile(secrets, profile.id))
                for profile in seeded
            ]
        finally:
            if owns_session:
                await session.__aexit__(None, None, None)

    async def _resolve_profile_row(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        kind: OperatorConfigProfileKind,
        *,
        camera_id: UUID | None,
        site_id: UUID | None,
        edge_node_id: UUID | None,
    ) -> OperatorConfigProfile | None:
        profiles = await self._load_profiles(session, tenant_id, kind=kind)
        profile_by_id = {profile.id: profile for profile in profiles}
        bindings = await self._load_bindings(session, tenant_id, kind=kind)
        candidates = [
            (OperatorConfigScope.CAMERA, camera_id),
            (OperatorConfigScope.EDGE_NODE, edge_node_id),
            (OperatorConfigScope.SITE, site_id),
        ]
        for scope, scope_id in candidates:
            if scope_id is None:
                continue
            binding = next(
                (
                    item
                    for item in bindings
                    if item.scope == scope and item.scope_key == str(scope_id)
                ),
                None,
            )
            profile = profile_by_id.get(binding.profile_id) if binding is not None else None
            if profile is not None and profile.enabled:
                return profile

        return next(
            (profile for profile in profiles if profile.enabled and profile.is_default),
            None,
        )

    async def _get_profile(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
    ) -> OperatorConfigProfile:
        profile = await session.get(OperatorConfigProfile, profile_id)
        if profile is None or profile.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration profile not found.",
            )
        return profile

    async def _load_profiles(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        *,
        kind: OperatorConfigProfileKind | None = None,
    ) -> list[OperatorConfigProfile]:
        statement = select(OperatorConfigProfile).where(
            OperatorConfigProfile.tenant_id == tenant_id
        )
        if kind is not None:
            statement = statement.where(OperatorConfigProfile.kind == kind)
        result = await session.execute(statement)
        profiles = list(result.scalars().all())
        return [
            profile
            for profile in profiles
            if profile.tenant_id == tenant_id and (kind is None or profile.kind == kind)
        ]

    async def _load_secrets(
        self,
        session: AsyncSession,
        profile_id: UUID | None = None,
    ) -> list[OperatorConfigSecret]:
        statement = select(OperatorConfigSecret)
        if profile_id is not None:
            statement = statement.where(OperatorConfigSecret.profile_id == profile_id)
        result = await session.execute(statement)
        secrets = list(result.scalars().all())
        return [
            secret
            for secret in secrets
            if profile_id is None or secret.profile_id == profile_id
        ]

    async def _load_decrypted_secrets(
        self,
        session: AsyncSession,
        profile_id: UUID,
    ) -> dict[str, str]:
        return {
            secret.key: decrypt_config_secret(secret.encrypted_value, self.settings)
            for secret in await self._load_secrets(session, profile_id)
        }

    async def _load_bindings(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        *,
        kind: OperatorConfigProfileKind | None = None,
    ) -> list[OperatorConfigBinding]:
        statement = select(OperatorConfigBinding).where(
            OperatorConfigBinding.tenant_id == tenant_id
        )
        if kind is not None:
            statement = statement.where(OperatorConfigBinding.kind == kind)
        result = await session.execute(statement)
        bindings = list(result.scalars().all())
        return [
            binding
            for binding in bindings
            if binding.tenant_id == tenant_id and (kind is None or binding.kind == kind)
        ]

    async def _camera_scope(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        camera_id: UUID | None,
    ) -> tuple[UUID | None, UUID | None]:
        if camera_id is None:
            return None, None

        result = await session.execute(select(Camera).where(Camera.id == camera_id))
        cameras = [candidate for candidate in result.scalars().all() if candidate.id == camera_id]
        if not cameras:
            return None, None
        camera = cameras[0]

        site_result = await session.execute(select(Site).where(Site.id == camera.site_id))
        sites = [
            candidate
            for candidate in site_result.scalars().all()
            if isinstance(candidate, Site) and candidate.id == camera.site_id
        ]
        if sites and sites[0].tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found.",
            )
        return camera.site_id, camera.edge_node_id

    async def _validate_profile(
        self,
        profile: OperatorConfigProfile,
        secrets: dict[str, str],
    ) -> tuple[OperatorConfigValidationStatus, str | None]:
        if profile.kind == OperatorConfigProfileKind.EVIDENCE_STORAGE:
            return await self._validate_evidence_storage(profile.config, secrets)
        if profile.kind == OperatorConfigProfileKind.STREAM_DELIVERY:
            StreamDeliveryProfileConfig.model_validate(profile.config)
            return OperatorConfigValidationStatus.VALID, "Transport profile is valid."
        if profile.kind == OperatorConfigProfileKind.RUNTIME_SELECTION:
            RuntimeSelectionProfileConfig.model_validate(profile.config)
            return OperatorConfigValidationStatus.VALID, "Runtime selection profile is valid."
        if profile.kind == OperatorConfigProfileKind.PRIVACY_POLICY:
            PrivacyPolicyProfileConfig.model_validate(profile.config)
            return OperatorConfigValidationStatus.VALID, "Privacy policy profile is valid."
        if profile.kind == OperatorConfigProfileKind.LLM_PROVIDER:
            LLMProviderProfileConfig.model_validate(profile.config)
            return OperatorConfigValidationStatus.VALID, "LLM provider profile is valid."
        OperationsModeProfileConfig.model_validate(profile.config)
        return OperatorConfigValidationStatus.VALID, "Operations mode profile is valid."

    async def _validate_evidence_storage(
        self,
        config: dict[str, Any],
        secrets: dict[str, str],
    ) -> tuple[OperatorConfigValidationStatus, str | None]:
        provider = str(config.get("provider", EvidenceStorageProvider.MINIO.value))
        if provider in {EvidenceStorageProvider.LOCAL_FILESYSTEM.value, "local_first"}:
            return self._validate_local_storage(config)
        missing = [
            key
            for key, value in {
                "endpoint": config.get("endpoint"),
                "bucket": config.get("bucket"),
                "access_key": secrets.get("access_key"),
                "secret_key": secrets.get("secret_key"),
            }.items()
            if not value
        ]
        if missing:
            return (
                OperatorConfigValidationStatus.INVALID,
                f"Missing required storage settings: {', '.join(missing)}.",
            )
        if self.remote_storage_validator is not None:
            return await self.remote_storage_validator(config, secrets)
        return await _default_remote_storage_validator(config, secrets, self.settings)

    def _validate_local_storage(
        self,
        config: dict[str, Any],
    ) -> tuple[OperatorConfigValidationStatus, str | None]:
        raw_root = config.get("local_root")
        if not raw_root:
            return OperatorConfigValidationStatus.INVALID, "local_root is required."
        configured_root = Path(self.settings.incident_local_storage_root).expanduser().resolve()
        requested_root = Path(str(raw_root)).expanduser()
        root = requested_root.resolve() if requested_root.is_absolute() else (
            configured_root / requested_root
        ).resolve()
        if (
            not requested_root.is_absolute()
            and root != configured_root
            and configured_root not in root.parents
        ):
            return (
                OperatorConfigValidationStatus.INVALID,
                "local_root must stay under the configured evidence storage root.",
            )
        try:
            root.mkdir(parents=True, exist_ok=True)
            marker = root / ".argus-write-test"
            marker.write_bytes(b"ok")
            marker.unlink(missing_ok=True)
        except OSError as exc:
            return OperatorConfigValidationStatus.INVALID, f"Local storage is not writable: {exc}."
        return OperatorConfigValidationStatus.VALID, "Local evidence storage is writable."

    def _bootstrap_profiles(self) -> list[OperatorConfigProfileCreate]:
        return [
            OperatorConfigProfileCreate(
                kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
                scope=OperatorConfigScope.TENANT,
                name="Dev MinIO",
                slug="dev-minio",
                is_default=True,
                config={
                    "provider": EvidenceStorageProvider.MINIO.value,
                    "storage_scope": self.settings.incident_storage_scope,
                    "endpoint": self.settings.minio_endpoint,
                    "bucket": self.settings.minio_incidents_bucket,
                    "secure": self.settings.minio_secure,
                },
                secrets={
                    "access_key": self.settings.minio_access_key,
                    "secret_key": self.settings.minio_secret_key.get_secret_value(),
                },
            ),
            OperatorConfigProfileCreate(
                kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
                scope=OperatorConfigScope.TENANT,
                name="Dev local evidence",
                slug="dev-local-evidence",
                config={
                    "provider": EvidenceStorageProvider.LOCAL_FILESYSTEM.value,
                    "storage_scope": EvidenceStorageScope.EDGE.value,
                    "local_root": self.settings.incident_local_storage_root,
                },
            ),
            OperatorConfigProfileCreate(
                kind=OperatorConfigProfileKind.STREAM_DELIVERY,
                scope=OperatorConfigScope.TENANT,
                name="Default native stream delivery",
                slug="default-native-stream-delivery",
                is_default=True,
                config={
                    "delivery_mode": "native",
                    "public_base_url": self.settings.mediamtx_webrtc_base_url,
                },
            ),
            OperatorConfigProfileCreate(
                kind=OperatorConfigProfileKind.RUNTIME_SELECTION,
                scope=OperatorConfigScope.TENANT,
                name="Default runtime selection",
                slug="default-runtime-selection",
                is_default=True,
                config={
                    "preferred_backend": "onnxruntime",
                    "artifact_preference": "tensorrt_first",
                    "fallback_allowed": True,
                },
            ),
            OperatorConfigProfileCreate(
                kind=OperatorConfigProfileKind.PRIVACY_POLICY,
                scope=OperatorConfigScope.TENANT,
                name="Default privacy policy",
                slug="default-privacy-policy",
                is_default=True,
                config={},
            ),
            OperatorConfigProfileCreate(
                kind=OperatorConfigProfileKind.LLM_PROVIDER,
                scope=OperatorConfigScope.TENANT,
                name="Default LLM provider",
                slug="default-llm-provider",
                is_default=True,
                config={
                    "provider": self.settings.llm_provider,
                    "model": self.settings.llm_model,
                    "base_url": self.settings.llm_ollama_base_url,
                    "api_key_required": True,
                },
            ),
            OperatorConfigProfileCreate(
                kind=OperatorConfigProfileKind.OPERATIONS_MODE,
                scope=OperatorConfigScope.TENANT,
                name="Default operations mode",
                slug="default-operations-mode",
                is_default=True,
                config={},
            ),
        ]

    async def _record(
        self,
        tenant_context: TenantContext,
        *,
        action: str,
        target: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if self.audit_logger is None:
            return
        await self.audit_logger.record(
            tenant_context=tenant_context,
            action=action,
            target=target,
            meta=meta,
        )


def hash_config(config: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(config).encode("utf-8")).hexdigest()


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _profile_to_response(
    profile: OperatorConfigProfile,
    secrets: list[OperatorConfigSecret],
) -> OperatorConfigProfileResponse:
    return OperatorConfigProfileResponse(
        id=profile.id,
        tenant_id=profile.tenant_id,
        site_id=profile.site_id,
        edge_node_id=profile.edge_node_id,
        camera_id=profile.camera_id,
        kind=profile.kind,
        scope=profile.scope,
        name=profile.name,
        slug=profile.slug,
        enabled=profile.enabled,
        is_default=profile.is_default,
        config=dict(profile.config),
        secret_state={secret.key: "present" for secret in secrets},
        validation_status=profile.validation_status,
        validation_message=profile.validation_message,
        validated_at=profile.validated_at,
        config_hash=profile.config_hash,
        created_at=_created_at(profile),
        updated_at=_updated_at(profile),
    )


def _secret_row(
    tenant_id: UUID,
    profile_id: UUID,
    key: str,
    value: str,
    settings: Settings,
) -> OperatorConfigSecret:
    return OperatorConfigSecret(
        id=uuid4(),
        tenant_id=tenant_id,
        profile_id=profile_id,
        key=key,
        encrypted_value=encrypt_config_secret(value, settings),
        value_fingerprint=_secret_fingerprint(value),
    )


def _secret_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _secrets_for_profile(
    secrets: list[OperatorConfigSecret],
    profile_id: UUID,
) -> list[OperatorConfigSecret]:
    return [secret for secret in secrets if secret.profile_id == profile_id]


def _clear_default(
    profiles: list[OperatorConfigProfile],
    *,
    except_profile_id: UUID | None = None,
) -> None:
    for profile in profiles:
        if profile.id != except_profile_id:
            profile.is_default = False


def _created_at(row: Any) -> datetime:
    value = getattr(row, "created_at", None)
    return value if isinstance(value, datetime) else datetime.now(tz=UTC)


def _updated_at(row: Any) -> datetime:
    value = getattr(row, "updated_at", None)
    return value if isinstance(value, datetime) else _created_at(row)


async def _default_remote_storage_validator(
    config: dict[str, Any],
    secrets: dict[str, str],
    settings: Settings,
) -> tuple[OperatorConfigValidationStatus, str | None]:
    provider = EvidenceStorageProvider(config.get("provider", EvidenceStorageProvider.MINIO))
    storage_settings = settings.model_copy(
        update={
            "minio_endpoint": config["endpoint"],
            "minio_access_key": secrets["access_key"],
            "minio_secret_key": SecretStr(secrets["secret_key"]),
            "minio_secure": bool(config.get("secure", False)),
            "minio_incidents_bucket": config["bucket"],
            "incident_storage_provider": provider.value,
            "incident_storage_scope": config.get("storage_scope", settings.incident_storage_scope),
        }
    )
    try:
        store = MinioObjectStore(storage_settings)
        await store.put_object(
            key=f"validation/operator-config-{uuid4()}.txt",
            data=b"argus operator configuration validation",
            content_type="text/plain",
        )
    except Exception as exc:  # noqa: BLE001
        return (
            OperatorConfigValidationStatus.INVALID,
            f"S3-compatible storage validation failed: {type(exc).__name__}.",
        )
    return OperatorConfigValidationStatus.VALID, "S3-compatible evidence storage is reachable."
