from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.models.enums import RoleEnum
from argus.models.tables import Tenant, User

TENANT_ASSIGNABLE_ROLES = {RoleEnum.VIEWER, RoleEnum.OPERATOR, RoleEnum.ADMIN}


class TenantUserProvisioner(Protocol):
    async def provision_tenant_user(
        self,
        *,
        tenant_id: UUID,
        tenant_slug: str,
        email: str,
        temporary_password: str,
        first_name: str,
        last_name: str,
        role: RoleEnum,
    ) -> str: ...

    async def update_tenant_user(
        self,
        *,
        user_id: str,
        first_name: str,
        last_name: str,
        enabled: bool,
    ) -> None: ...

    async def set_tenant_user_role(
        self,
        *,
        user_id: str,
        role: RoleEnum,
    ) -> None: ...

    async def reset_tenant_user_password(
        self,
        *,
        user_id: str,
        temporary_password: str,
    ) -> None: ...


class UserManagementService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        identity_provisioner: TenantUserProvisioner | None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.identity_provisioner = identity_provisioner
        self.now_factory = now_factory or (lambda: datetime.now(tz=UTC))

    async def list_tenants(self) -> list[Tenant]:
        async with self.session_factory() as session:
            rows = list(
                (await session.execute(select(Tenant).order_by(Tenant.name.asc())))
                .scalars()
                .all()
            )
        return [row for row in rows if isinstance(row, Tenant)]

    async def create_tenant(
        self,
        *,
        name: str,
        slug: str | None,
        actor_subject: str,
    ) -> Tenant:
        del actor_subject
        tenant_slug = _slugify(slug or name)
        async with self.session_factory() as session:
            existing = await self._tenant_by_slug(session, tenant_slug)
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Tenant slug already exists.",
                )
            now = self.now_factory()
            tenant = Tenant(name=name.strip(), slug=tenant_slug)
            tenant.created_at = now
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            return tenant

    async def list_users(self, *, tenant_id: UUID | None) -> list[User]:
        statement = select(User).order_by(User.email.asc())
        if tenant_id is not None:
            statement = statement.where(User.tenant_id == tenant_id)
        async with self.session_factory() as session:
            rows = list((await session.execute(statement)).scalars().all())
        return [row for row in rows if isinstance(row, User)]

    async def create_user(
        self,
        *,
        tenant_id: UUID,
        email: str,
        first_name: str,
        last_name: str,
        role: RoleEnum,
        temporary_password: str,
        actor_subject: str,
    ) -> User:
        del actor_subject
        _ensure_assignable_role(role)
        if self.identity_provisioner is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Identity provider is not configured.",
            )
        normalized_email = email.strip().lower()
        async with self.session_factory() as session:
            tenant = await session.get(Tenant, tenant_id)
            if not isinstance(tenant, Tenant):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found.",
                )
            existing = await self._user_by_email(
                session,
                tenant_id=tenant_id,
                email=normalized_email,
            )
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already exists.",
                )
            oidc_sub = await self.identity_provisioner.provision_tenant_user(
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                email=normalized_email,
                temporary_password=temporary_password,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                role=role,
            )
            now = self.now_factory()
            user = User(
                tenant_id=tenant.id,
                email=normalized_email,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                oidc_sub=oidc_sub,
                role=role,
                enabled=True,
            )
            user.created_at = now
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def update_user(
        self,
        *,
        tenant_id: UUID | None,
        user_id: UUID,
        first_name: str | None,
        last_name: str | None,
        role: RoleEnum | None,
        enabled: bool | None,
        actor_subject: str,
    ) -> User:
        del actor_subject
        if role is not None:
            _ensure_assignable_role(role)
        identity_provisioner = self._require_identity_provider()
        async with self.session_factory() as session:
            user = await self._user_by_id(session, tenant_id=tenant_id, user_id=user_id)
            final_role = role or user.role
            final_enabled = user.enabled if enabled is None else enabled
            final_first_name = user.first_name if first_name is None else first_name.strip()
            final_last_name = user.last_name if last_name is None else last_name.strip()
            await self._ensure_last_enabled_admin_survives(
                session,
                user=user,
                final_role=final_role,
                final_enabled=final_enabled,
            )
            if (
                final_first_name != user.first_name
                or final_last_name != user.last_name
                or final_enabled != user.enabled
            ):
                await identity_provisioner.update_tenant_user(
                    user_id=user.oidc_sub,
                    first_name=final_first_name or "",
                    last_name=final_last_name or "",
                    enabled=final_enabled,
                )
            if final_role != user.role:
                await identity_provisioner.set_tenant_user_role(
                    user_id=user.oidc_sub,
                    role=final_role,
                )
            user.first_name = final_first_name
            user.last_name = final_last_name
            user.role = final_role
            user.enabled = final_enabled
            await session.commit()
            await session.refresh(user)
            return user

    async def reset_user_password(
        self,
        *,
        tenant_id: UUID | None,
        user_id: UUID,
        temporary_password: str,
        actor_subject: str,
    ) -> User:
        del actor_subject
        identity_provisioner = self._require_identity_provider()
        async with self.session_factory() as session:
            user = await self._user_by_id(session, tenant_id=tenant_id, user_id=user_id)
            await identity_provisioner.reset_tenant_user_password(
                user_id=user.oidc_sub,
                temporary_password=temporary_password,
            )
            return user

    async def _tenant_by_slug(self, session: AsyncSession, slug: str) -> Tenant | None:
        row = (
            await session.execute(select(Tenant).where(Tenant.slug == slug))
        ).scalar_one_or_none()
        return row if isinstance(row, Tenant) else None

    async def _user_by_id(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID | None,
        user_id: UUID,
    ) -> User:
        row = await session.get(User, user_id)
        if not isinstance(row, User) or (tenant_id is not None and row.tenant_id != tenant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return row

    async def _user_by_email(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        email: str,
    ) -> User | None:
        row = (
            await session.execute(
                select(User).where(User.tenant_id == tenant_id, User.email == email)
            )
        ).scalar_one_or_none()
        return row if isinstance(row, User) else None

    async def _ensure_last_enabled_admin_survives(
        self,
        session: AsyncSession,
        *,
        user: User,
        final_role: RoleEnum,
        final_enabled: bool,
    ) -> None:
        if user.role is not RoleEnum.ADMIN or not user.enabled:
            return
        if final_role is RoleEnum.ADMIN and final_enabled:
            return
        tenant_users = list(
            (
                await session.execute(select(User).where(User.tenant_id == user.tenant_id))
            ).scalars().all()
        )
        enabled_admins = [
            row
            for row in tenant_users
            if isinstance(row, User) and row.enabled and row.role is RoleEnum.ADMIN
        ]
        if len(enabled_admins) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove or disable the last enabled tenant admin.",
            )

    def _require_identity_provider(self) -> TenantUserProvisioner:
        if self.identity_provisioner is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Identity provider is not configured.",
            )
        return self.identity_provisioner


def _ensure_assignable_role(role: RoleEnum) -> None:
    if role not in TENANT_ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Role cannot be assigned to a tenant user.",
        )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "vezor"
