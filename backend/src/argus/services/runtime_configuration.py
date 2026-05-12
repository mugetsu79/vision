from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    OperatorConfigProfileResponse,
    ResolvedOperatorConfigEntryResponse,
    ResolvedOperatorConfigResponse,
    TenantContext,
)
from argus.compat import UTC
from argus.core.config import Settings
from argus.core.security import decrypt_config_secret
from argus.models.enums import (
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

BootstrapDefaults = Callable[
    [TenantContext],
    Awaitable[list[OperatorConfigProfileResponse]],
]

_RUNTIME_DEFERRED_MESSAGE = "Runtime-wired in Task 20."


@dataclass(frozen=True, slots=True)
class RuntimeOperatorConfig:
    kind: OperatorConfigProfileKind
    profile_id: UUID | None
    profile_name: str | None
    profile_slug: str | None
    profile_hash: str | None
    config: dict[str, object]
    secrets: dict[str, str]


class RuntimeConfigurationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        *,
        bootstrap_defaults: BootstrapDefaults | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.bootstrap_defaults = bootstrap_defaults

    async def resolve_all_for_camera(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID | None = None,
        site_id: UUID | None = None,
        edge_node_id: UUID | None = None,
    ) -> ResolvedOperatorConfigResponse:
        async with self.session_factory() as session:
            camera_site_id, camera_edge_node_id = await self._camera_scope(
                session,
                tenant_context.tenant_id,
                camera_id,
            )
            resolved_site_id = camera_site_id or site_id
            resolved_edge_node_id = camera_edge_node_id or edge_node_id
            await self._seed_if_empty(session, tenant_context)
            entries: dict[OperatorConfigProfileKind, ResolvedOperatorConfigEntryResponse] = {}
            profiles: dict[OperatorConfigProfileKind, OperatorConfigProfileResponse] = {}
            for kind in OperatorConfigProfileKind:
                resolution = await self._resolve_entry(
                    session,
                    tenant_id=tenant_context.tenant_id,
                    kind=kind,
                    camera_id=camera_id,
                    site_id=resolved_site_id,
                    edge_node_id=resolved_edge_node_id,
                )
                entries[kind] = resolution
                if resolution.resolution_status == "resolved" and resolution.profile_id:
                    profile = await session.get(OperatorConfigProfile, resolution.profile_id)
                    if profile is not None:
                        secrets = await self._load_secrets(session, profile.id)
                        profiles[kind] = _profile_to_response(profile, secrets)
        return ResolvedOperatorConfigResponse(entries=entries, profiles=profiles)

    async def resolve_profile_for_runtime(
        self,
        tenant_context: TenantContext,
        kind: OperatorConfigProfileKind,
        *,
        camera_id: UUID | None = None,
        site_id: UUID | None = None,
        edge_node_id: UUID | None = None,
        profile_id: UUID | None = None,
    ) -> RuntimeOperatorConfig:
        async with self.session_factory() as session:
            if profile_id is not None:
                profile = await session.get(OperatorConfigProfile, profile_id)
                if (
                    profile is None
                    or profile.tenant_id != tenant_context.tenant_id
                    or profile.kind != kind
                    or not profile.enabled
                    or profile.validation_status is OperatorConfigValidationStatus.INVALID
                ):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Runtime configuration profile could not be resolved.",
                    )
            else:
                camera_site_id, camera_edge_node_id = await self._camera_scope(
                    session,
                    tenant_context.tenant_id,
                    camera_id,
                )
                resolved_site_id = camera_site_id or site_id
                resolved_edge_node_id = camera_edge_node_id or edge_node_id
                await self._seed_if_empty(session, tenant_context)
                entry = await self._resolve_entry(
                    session,
                    tenant_id=tenant_context.tenant_id,
                    kind=kind,
                    camera_id=camera_id,
                    site_id=resolved_site_id,
                    edge_node_id=resolved_edge_node_id,
                )
                if entry.resolution_status != "resolved" or entry.profile_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=(
                            entry.operator_message
                            or "Runtime configuration profile could not be resolved."
                        ),
                    )
                profile = await session.get(OperatorConfigProfile, entry.profile_id)
                if profile is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Runtime configuration profile could not be resolved.",
                    )
            secrets = await self._load_decrypted_secrets(session, profile.id)
        return RuntimeOperatorConfig(
            kind=profile.kind,
            profile_id=profile.id,
            profile_name=profile.name,
            profile_slug=profile.slug,
            profile_hash=profile.config_hash,
            config=dict(profile.config),
            secrets=secrets,
        )

    async def _resolve_entry(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        kind: OperatorConfigProfileKind,
        camera_id: UUID | None,
        site_id: UUID | None,
        edge_node_id: UUID | None,
    ) -> ResolvedOperatorConfigEntryResponse:
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
            if binding is None:
                continue
            profile = profile_by_id.get(binding.profile_id)
            if profile is None:
                return _unresolved_entry(
                    kind,
                    scope=scope,
                    scope_key=str(scope_id),
                    message=f"Bound {scope.value} profile was not found.",
                )
            return await self._entry_for_profile(
                session,
                profile,
                winner_scope=scope,
                winner_scope_key=str(scope_id),
            )

        default_profile = next((profile for profile in profiles if profile.is_default), None)
        if default_profile is None:
            return _unresolved_entry(kind, message="No enabled default profile is configured.")
        return await self._entry_for_profile(
            session,
            default_profile,
            winner_scope=OperatorConfigScope.TENANT,
            winner_scope_key=str(tenant_id),
        )

    async def _entry_for_profile(
        self,
        session: AsyncSession,
        profile: OperatorConfigProfile,
        *,
        winner_scope: OperatorConfigScope,
        winner_scope_key: str,
    ) -> ResolvedOperatorConfigEntryResponse:
        secrets = await self._load_secrets(session, profile.id)
        base = {
            "kind": profile.kind,
            "profile_id": profile.id,
            "profile_name": profile.name,
            "profile_slug": profile.slug,
            "profile_hash": profile.config_hash,
            "winner_scope": winner_scope,
            "winner_scope_key": winner_scope_key,
            "validation_status": profile.validation_status,
            "secret_state": {secret.key: "present" for secret in secrets},
            "config": dict(profile.config),
        }
        if not profile.enabled:
            return ResolvedOperatorConfigEntryResponse(
                **base,
                resolution_status="unresolved",
                applies_to_runtime=False,
                operator_message=f"Selected {winner_scope.value} profile is disabled.",
            )
        if profile.validation_status is OperatorConfigValidationStatus.INVALID:
            message = profile.validation_message or "Profile validation failed."
            return ResolvedOperatorConfigEntryResponse(
                **base,
                resolution_status="unresolved",
                applies_to_runtime=False,
                operator_message=f"Selected {winner_scope.value} profile is invalid: {message}",
            )
        applies_to_runtime = profile.kind is not OperatorConfigProfileKind.OPERATIONS_MODE
        return ResolvedOperatorConfigEntryResponse(
            **base,
            resolution_status="resolved",
            applies_to_runtime=applies_to_runtime,
            operator_message=None if applies_to_runtime else _RUNTIME_DEFERRED_MESSAGE,
        )

    async def _seed_if_empty(
        self,
        session: AsyncSession,
        tenant_context: TenantContext,
    ) -> None:
        if self.bootstrap_defaults is None:
            return
        if await self._load_profiles(session, tenant_context.tenant_id):
            return
        await self.bootstrap_defaults(tenant_context)

    async def _camera_scope(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        camera_id: UUID | None,
    ) -> tuple[UUID | None, UUID | None]:
        if camera_id is None:
            return None, None
        result = await session.execute(select(Camera).where(Camera.id == camera_id))
        camera = next(
            (candidate for candidate in result.scalars().all() if candidate.id == camera_id),
            None,
        )
        if camera is None:
            return None, None
        site_result = await session.execute(select(Site).where(Site.id == camera.site_id))
        site = next(
            (
                candidate
                for candidate in site_result.scalars().all()
                if isinstance(candidate, Site) and candidate.id == camera.site_id
            ),
            None,
        )
        if site is not None and site.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
        return camera.site_id, camera.edge_node_id

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
        return [
            profile
            for profile in result.scalars().all()
            if profile.tenant_id == tenant_id and (kind is None or profile.kind == kind)
        ]

    async def _load_bindings(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        *,
        kind: OperatorConfigProfileKind,
    ) -> list[OperatorConfigBinding]:
        statement = select(OperatorConfigBinding).where(
            OperatorConfigBinding.tenant_id == tenant_id
        )
        statement = statement.where(OperatorConfigBinding.kind == kind)
        result = await session.execute(statement)
        return [
            binding
            for binding in result.scalars().all()
            if binding.tenant_id == tenant_id and binding.kind == kind
        ]

    async def _load_secrets(
        self,
        session: AsyncSession,
        profile_id: UUID,
    ) -> list[OperatorConfigSecret]:
        statement = select(OperatorConfigSecret).where(
            OperatorConfigSecret.profile_id == profile_id
        )
        result = await session.execute(statement)
        return [
            secret
            for secret in result.scalars().all()
            if secret.profile_id == profile_id
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


def _unresolved_entry(
    kind: OperatorConfigProfileKind,
    *,
    scope: OperatorConfigScope | None = None,
    scope_key: str | None = None,
    message: str,
) -> ResolvedOperatorConfigEntryResponse:
    return ResolvedOperatorConfigEntryResponse(
        kind=kind,
        winner_scope=scope,
        winner_scope_key=scope_key,
        resolution_status="unresolved",
        applies_to_runtime=False,
        operator_message=message,
    )


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


def _created_at(row: object) -> datetime:
    value = getattr(row, "created_at", None)
    return value if isinstance(value, datetime) else datetime.now(tz=UTC)


def _updated_at(row: object) -> datetime:
    value = getattr(row, "updated_at", None)
    return value if isinstance(value, datetime) else _created_at(row)
