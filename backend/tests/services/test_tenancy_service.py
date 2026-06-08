from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException

from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum
from argus.models.tables import Tenant, User
from argus.services.app import TenancyService

TENANT_A = UUID("00000000-0000-4000-8000-0000000000a1")
TENANT_B = UUID("00000000-0000-4000-8000-0000000000b1")


@pytest.mark.asyncio
async def test_claimless_user_resolves_from_local_user_subject_before_realm_fallback() -> None:
    session_factory = _MemorySessionFactory()
    session_factory.session.add(Tenant(id=TENANT_A, name="Argus Dev", slug="argus-dev"))
    session_factory.session.add(Tenant(id=TENANT_B, name="Live Validation", slug="live-validation"))
    session_factory.session.add(
        User(
            tenant_id=TENANT_B,
            email="live-admin@example.test",
            oidc_sub="keycloak-live-admin",
            role=RoleEnum.ADMIN,
        )
    )
    service = TenancyService(session_factory, Settings(_env_file=None, environment="development"))

    context = await service.resolve_context(
        user=_user(subject="keycloak-live-admin", tenant_context=None),
    )

    assert context.tenant_id == TENANT_B
    assert context.tenant_slug == "live-validation"


@pytest.mark.asyncio
async def test_claimless_unknown_user_is_rejected_once_local_users_exist() -> None:
    session_factory = _MemorySessionFactory()
    session_factory.session.add(Tenant(id=TENANT_A, name="Argus Dev", slug="argus-dev"))
    session_factory.session.add(
        User(
            tenant_id=TENANT_A,
            email="admin-dev@argus.local",
            oidc_sub="keycloak-admin-dev",
            role=RoleEnum.ADMIN,
        )
    )
    service = TenancyService(session_factory, Settings(_env_file=None, environment="development"))

    with pytest.raises(HTTPException) as exc_info:
        await service.resolve_context(
            user=_user(subject="unmapped-user", tenant_context=None),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Token does not include a tenant context."


@pytest.mark.asyncio
async def test_tenant_slug_claim_resolves_without_realm_fallback() -> None:
    session_factory = _MemorySessionFactory()
    session_factory.session.add(Tenant(id=TENANT_A, name="Argus Dev", slug="argus-dev"))
    session_factory.session.add(Tenant(id=TENANT_B, name="Live Validation", slug="live-validation"))
    service = TenancyService(session_factory, Settings(_env_file=None, environment="development"))

    context = await service.resolve_context(
        user=_user(subject="keycloak-live-admin", tenant_context="live-validation"),
    )

    assert context.tenant_id == TENANT_B
    assert context.tenant_slug == "live-validation"


def _user(*, subject: str, tenant_context: str | None) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=subject,
        email="admin@example.test",
        role=RoleEnum.ADMIN,
        issuer="http://issuer/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=tenant_context,
        claims={},
    )


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None


class _MemorySession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    async def __aenter__(self) -> _MemorySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _Result:  # noqa: ANN001
        params = statement.compile().params
        slug = params.get("slug_1")
        oidc_sub = params.get("oidc_sub_1")
        tenant_id = params.get("id_1") or params.get("tenant_id_1")
        entities = {description.get("entity") for description in statement.column_descriptions}
        rows = self.rows
        if Tenant in entities:
            rows = [row for row in rows if isinstance(row, Tenant)]
        if User in entities:
            rows = [row for row in rows if isinstance(row, User)]
        if slug is not None:
            rows = [row for row in rows if getattr(row, "slug", None) == slug]
        if oidc_sub is not None:
            rows = [row for row in rows if getattr(row, "oidc_sub", None) == oidc_sub]
        if tenant_id is not None:
            rows = [row for row in rows if getattr(row, "id", None) == tenant_id]
        return _Result(rows)

    async def get(self, entity: type[object], row_id: object) -> object | None:
        return next(
            (
                row
                for row in self.rows
                if isinstance(row, entity) and getattr(row, "id", None) == row_id
            ),
            None,
        )

    def add(self, row: object) -> None:
        self.rows.append(row)

    async def commit(self) -> None:
        return None


class _MemorySessionFactory:
    def __init__(self) -> None:
        self.session = _MemorySession()

    def __call__(self) -> _MemorySession:
        return self.session
