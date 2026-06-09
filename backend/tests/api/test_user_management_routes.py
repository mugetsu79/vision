from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum

TENANT_A = UUID("00000000-0000-4000-8000-000000000101")
TENANT_B = UUID("00000000-0000-4000-8000-000000000102")


def _user(role: RoleEnum, *, superadmin: bool = False) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=f"{role.value}-1",
        email=f"{role.value}@example.com",
        role=role,
        issuer="http://issuer/realms/platform-admin" if superadmin else "http://issuer/realms/acme",
        realm="platform-admin" if superadmin else "acme",
        is_superadmin=superadmin,
        tenant_context=None if superadmin else str(TENANT_A),
        claims={},
    )


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request):  # noqa: ANN001
        authorization = request.headers.get("authorization")
        if not authorization:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return self.user


class _FakeTenancy:
    async def resolve_context(self, *, user, explicit_tenant_id=None):  # noqa: ANN001
        if explicit_tenant_id is not None and explicit_tenant_id != TENANT_A:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return SimpleNamespace(tenant_id=TENANT_A, tenant_slug="acme", user=user)


class _FakeUsers:
    def __init__(self) -> None:
        self.created_tenants: list[dict[str, object]] = []
        self.created_users: list[dict[str, object]] = []
        self.updated_users: list[dict[str, object]] = []
        self.password_resets: list[dict[str, object]] = []

    async def list_tenants(self):
        return [
            SimpleNamespace(
                id=TENANT_A,
                name="Acme",
                slug="acme",
                created_at="2026-06-09T12:00:00Z",
            ),
            SimpleNamespace(
                id=TENANT_B,
                name="Beta",
                slug="beta",
                created_at="2026-06-09T12:01:00Z",
            ),
        ]

    async def create_tenant(self, **kwargs):  # noqa: ANN003
        self.created_tenants.append(dict(kwargs))
        return SimpleNamespace(
            id=TENANT_B,
            name=kwargs["name"],
            slug=kwargs["slug"] or "beta",
            created_at="2026-06-09T12:02:00Z",
        )

    async def list_users(self, *, tenant_id):  # noqa: ANN001
        users = [
            SimpleNamespace(
                id=UUID("00000000-0000-4000-8000-000000000201"),
                tenant_id=TENANT_A,
                email="admin@acme.example",
                first_name="Acme",
                last_name="Admin",
                oidc_sub="acme-admin",
                role=RoleEnum.ADMIN,
                enabled=True,
                created_at="2026-06-09T12:00:00Z",
            ),
            SimpleNamespace(
                id=UUID("00000000-0000-4000-8000-000000000202"),
                tenant_id=TENANT_B,
                email="admin@beta.example",
                first_name="Beta",
                last_name="Admin",
                oidc_sub="beta-admin",
                role=RoleEnum.ADMIN,
                enabled=True,
                created_at="2026-06-09T12:01:00Z",
            ),
        ]
        return users if tenant_id is None else [
            user for user in users if user.tenant_id == tenant_id
        ]

    async def create_user(self, **kwargs):  # noqa: ANN003
        self.created_users.append(dict(kwargs))
        return SimpleNamespace(
            id=UUID("00000000-0000-4000-8000-000000000203"),
            tenant_id=kwargs["tenant_id"],
            email=kwargs["email"],
            first_name=kwargs["first_name"],
            last_name=kwargs["last_name"],
            oidc_sub=f"keycloak:{kwargs['email']}",
            role=kwargs["role"],
            enabled=True,
            created_at="2026-06-09T12:03:00Z",
        )

    async def update_user(self, **kwargs):  # noqa: ANN003
        self.updated_users.append(dict(kwargs))
        return SimpleNamespace(
            id=kwargs["user_id"],
            tenant_id=kwargs["tenant_id"] or TENANT_B,
            email="ops@beta.example",
            first_name=kwargs["first_name"] or "Ops",
            last_name=kwargs["last_name"] or "Lead",
            oidc_sub="keycloak:ops@beta.example",
            role=kwargs["role"] or RoleEnum.OPERATOR,
            enabled=kwargs["enabled"],
            created_at="2026-06-09T12:04:00Z",
        )

    async def reset_user_password(self, **kwargs):  # noqa: ANN003
        self.password_resets.append(dict(kwargs))
        return SimpleNamespace(
            id=kwargs["user_id"],
            tenant_id=kwargs["tenant_id"] or TENANT_B,
            email="ops@beta.example",
            first_name="Ops",
            last_name="Lead",
            oidc_sub="keycloak:ops@beta.example",
            role=RoleEnum.OPERATOR,
            enabled=True,
            created_at="2026-06-09T12:04:00Z",
        )


def _app(user: AuthenticatedUser) -> tuple[FastAPI, _FakeUsers]:
    app = FastAPI()
    app.include_router(router)
    users = _FakeUsers()
    app.state.security = _FakeSecurity(user)
    app.state.services = SimpleNamespace(tenancy=_FakeTenancy(), users=users)
    return app, users


@pytest.mark.asyncio
async def test_superadmin_lists_all_tenants_and_users_without_tenant_context() -> None:
    app, _users = _app(_user(RoleEnum.SUPERADMIN, superadmin=True))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer platform-token"},
    ) as client:
        tenants = await client.get("/api/v1/tenants")
        users = await client.get("/api/v1/users")

    assert tenants.status_code == 200
    assert [tenant["slug"] for tenant in tenants.json()] == ["acme", "beta"]
    assert users.status_code == 200
    assert {user["email"] for user in users.json()} == {
        "admin@acme.example",
        "admin@beta.example",
    }


@pytest.mark.asyncio
async def test_superadmin_creates_tenant_and_tenant_admin() -> None:
    app, users = _app(_user(RoleEnum.SUPERADMIN, superadmin=True))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer platform-token"},
    ) as client:
        tenant = await client.post(
            "/api/v1/tenants",
            json={"name": "Beta", "slug": "beta"},
        )
        created_user = await client.post(
            "/api/v1/users",
            json={
                "tenant_id": str(TENANT_B),
                "email": "admin@beta.example",
                "first_name": "Beta",
                "last_name": "Admin",
                "role": "admin",
                "temporary_password": "change-me-now",
            },
        )

    assert tenant.status_code == 201
    assert tenant.json()["slug"] == "beta"
    assert users.created_tenants[0]["actor_subject"] == "superadmin-1"
    assert created_user.status_code == 201
    assert created_user.json()["tenant_id"] == str(TENANT_B)
    assert "temporary_password" not in created_user.json()
    assert users.created_users[0]["tenant_id"] == TENANT_B


@pytest.mark.asyncio
async def test_tenant_admin_cannot_create_user_in_other_tenant() -> None:
    app, _users = _app(_user(RoleEnum.ADMIN))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer tenant-token"},
    ) as client:
        response = await client.post(
            "/api/v1/users",
            json={
                "tenant_id": str(TENANT_B),
                "email": "admin@beta.example",
                "first_name": "Beta",
                "last_name": "Admin",
                "role": "admin",
                "temporary_password": "change-me-now",
            },
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_superadmin_updates_and_resets_user_across_tenants() -> None:
    app, users = _app(_user(RoleEnum.SUPERADMIN, superadmin=True))
    user_id = "00000000-0000-4000-8000-000000000301"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer platform-token"},
    ) as client:
        updated = await client.patch(
            f"/api/v1/users/{user_id}",
            json={
                "first_name": "Operations",
                "role": "admin",
                "enabled": False,
            },
        )
        reset = await client.post(
            f"/api/v1/users/{user_id}/reset-password",
            json={"temporary_password": "change-me-now"},
        )

    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Operations"
    assert updated.json()["role"] == "admin"
    assert reset.status_code == 200
    assert "temporary_password" not in reset.json()
    assert users.updated_users[0]["tenant_id"] is None
    assert users.password_resets[0]["temporary_password"] == "change-me-now"
