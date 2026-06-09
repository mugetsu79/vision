from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    PlatformBootstrapComplete,
    PlatformBootstrapCompleteResponse,
    PlatformBootstrapRotateResponse,
    PlatformBootstrapStatusResponse,
)
from argus.compat import UTC
from argus.models.tables import PlatformBootstrapSession


class PlatformIdentityProvisioner(Protocol):
    async def has_platform_superadmin(self, *, platform_realm: str) -> bool: ...

    async def provision_platform_superadmin(
        self,
        *,
        email: str,
        temporary_password: str,
        first_name: str,
        last_name: str,
        platform_realm: str,
    ) -> str: ...


class PlatformBootstrapService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        identity_provisioner: PlatformIdentityProvisioner | None,
        token_hasher: Callable[[str], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
        platform_realm: str = "platform-admin",
    ) -> None:
        self.session_factory = session_factory
        self.identity_provisioner = identity_provisioner
        self.token_hasher = token_hasher or _hash_secret
        self.now_factory = now_factory or (lambda: datetime.now(tz=UTC))
        self.platform_realm = platform_realm

    async def ensure_session(self, *, raw_token: str) -> PlatformBootstrapSession:
        token_hash = self.token_hasher(raw_token)
        async with self.session_factory() as session:
            existing = (
                await session.execute(
                    select(PlatformBootstrapSession).where(
                        PlatformBootstrapSession.token_hash == token_hash
                    )
                )
            ).scalar_one_or_none()
            if isinstance(existing, PlatformBootstrapSession):
                return existing
            now = self.now_factory()
            row = PlatformBootstrapSession(
                token_hash=token_hash,
                consumed_at=None,
                consumed_by_subject=None,
            )
            _set_timestamps(row, now)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def rotate_local_bootstrap_token(
        self,
        *,
        actor_subject: str | None,
    ) -> PlatformBootstrapRotateResponse:
        raw_token = _new_platform_bootstrap_token()
        token_hash = self.token_hasher(raw_token)
        now = self.now_factory()
        async with self.session_factory() as session:
            rows = (
                await session.execute(select(PlatformBootstrapSession))
            ).scalars().all()
            for row in rows:
                if not isinstance(row, PlatformBootstrapSession):
                    continue
                if row.consumed_at is None:
                    row.consumed_at = now
                    row.consumed_by_subject = actor_subject
                    _set_updated_at(row, now)
            row = PlatformBootstrapSession(
                token_hash=token_hash,
                consumed_at=None,
                consumed_by_subject=None,
            )
            _set_timestamps(row, now)
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return PlatformBootstrapRotateResponse(bootstrap_token=raw_token)

    async def status(self) -> PlatformBootstrapStatusResponse:
        async with self.session_factory() as session:
            rows = (
                await session.execute(
                    select(PlatformBootstrapSession).order_by(
                        PlatformBootstrapSession.created_at.desc()
                    )
                )
            ).scalars().all()
        row = next(
            (
                session_row
                for session_row in rows
                if isinstance(session_row, PlatformBootstrapSession)
                and session_row.consumed_at is None
            ),
            rows[0] if rows else None,
        )
        return PlatformBootstrapStatusResponse(
            available=isinstance(row, PlatformBootstrapSession) and row.consumed_at is None,
            consumed_at=row.consumed_at if isinstance(row, PlatformBootstrapSession) else None,
        )

    async def complete(
        self,
        payload: PlatformBootstrapComplete,
    ) -> PlatformBootstrapCompleteResponse:
        if self.identity_provisioner is None:
            raise ValueError("Platform identity provisioner is not configured.")

        token_hash = self.token_hasher(payload.bootstrap_token)
        now = self.now_factory()
        async with self.session_factory() as session:
            row = (
                await session.execute(
                    select(PlatformBootstrapSession).where(
                        PlatformBootstrapSession.token_hash == token_hash
                    )
                )
            ).scalar_one_or_none()
            if not isinstance(row, PlatformBootstrapSession):
                raise ValueError("Invalid platform bootstrap token.")
            if row.consumed_at is not None:
                raise ValueError("Platform bootstrap token is already consumed.")
            if await self.identity_provisioner.has_platform_superadmin(
                platform_realm=self.platform_realm
            ):
                raise ValueError("A platform superadmin already exists.")

            subject = await self.identity_provisioner.provision_platform_superadmin(
                email=payload.email,
                temporary_password=payload.password,
                first_name=payload.first_name,
                last_name=payload.last_name,
                platform_realm=self.platform_realm,
            )
            row.consumed_at = now
            row.consumed_by_subject = subject
            _set_updated_at(row, now)
            await session.commit()
        return PlatformBootstrapCompleteResponse(
            email=payload.email,
            realm=self.platform_realm,
            role="superadmin",
            completed_at=now,
        )


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _new_platform_bootstrap_token() -> str:
    return f"vzplat_{secrets.token_urlsafe(24)}"


def _set_timestamps(row: object, now: datetime) -> None:
    if hasattr(row, "created_at"):
        setattr(row, "created_at", now)
    _set_updated_at(row, now)


def _set_updated_at(row: object, now: datetime) -> None:
    if hasattr(row, "updated_at"):
        setattr(row, "updated_at", now)
