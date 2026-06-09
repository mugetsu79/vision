from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.models.enums import RoleEnum
from argus.models.tables import Tenant, User
from argus.services.user_management import UserManagementService


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[object]:
        return self._rows

    def scalar_one_or_none(self) -> object | None:
        return self._rows[0] if self._rows else None


class _MemorySession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    async def __aenter__(self) -> _MemorySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _Result:  # noqa: ANN001
        params = statement.compile().params
        entities = {description.get("entity") for description in statement.column_descriptions}
        rows = self.rows
        if Tenant in entities:
            rows = [row for row in rows if isinstance(row, Tenant)]
            slug = params.get("slug_1")
            if slug is not None:
                rows = [row for row in rows if row.slug == slug]
        if User in entities:
            rows = [row for row in rows if isinstance(row, User)]
            tenant_id = params.get("tenant_id_1")
            email = params.get("email_1")
            if tenant_id is not None:
                rows = [row for row in rows if row.tenant_id == tenant_id]
            if email is not None:
                rows = [row for row in rows if row.email == email]
        return _Result(rows)

    def add(self, row: object) -> None:
        self.rows.append(row)

    async def flush(self) -> None:
        return None

    async def get(self, entity: type[object], row_id: object) -> object | None:
        return next(
            (
                row
                for row in self.rows
                if isinstance(row, entity) and getattr(row, "id", None) == row_id
            ),
            None,
        )

    async def commit(self) -> None:
        return None

    async def refresh(self, row: object) -> None:
        return None


class _MemorySessionFactory:
    def __init__(self) -> None:
        self.session = _MemorySession()

    def __call__(self) -> _MemorySession:
        return self.session


class _RecordingIdentityProvisioner:
    def __init__(self) -> None:
        self.provisioned_users: list[dict[str, object]] = []
        self.updated_users: list[dict[str, object]] = []
        self.role_updates: list[dict[str, object]] = []
        self.password_resets: list[dict[str, object]] = []

    async def provision_tenant_user(self, **kwargs):  # noqa: ANN003
        self.provisioned_users.append(dict(kwargs))
        return f"keycloak:{kwargs['email']}"

    async def update_tenant_user(self, **kwargs) -> None:  # noqa: ANN003
        self.updated_users.append(dict(kwargs))

    async def set_tenant_user_role(self, **kwargs) -> None:  # noqa: ANN003
        self.role_updates.append(dict(kwargs))

    async def reset_tenant_user_password(self, **kwargs) -> None:  # noqa: ANN003
        self.password_resets.append(dict(kwargs))


def _service(
    session_factory: _MemorySessionFactory,
    provisioner: _RecordingIdentityProvisioner | None = None,
) -> UserManagementService:
    return UserManagementService(
        session_factory=session_factory,
        identity_provisioner=provisioner,
        now_factory=lambda: datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_superadmin_creates_and_lists_tenants() -> None:
    session_factory = _MemorySessionFactory()
    service = _service(session_factory)

    created = await service.create_tenant(
        name="Acme Operations",
        slug=None,
        actor_subject="platform-root",
    )
    tenants = await service.list_tenants()

    assert created.name == "Acme Operations"
    assert created.slug == "acme-operations"
    assert [tenant.id for tenant in tenants] == [created.id]


@pytest.mark.asyncio
async def test_create_user_provisions_keycloak_and_local_row() -> None:
    session_factory = _MemorySessionFactory()
    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    session_factory.session.add(tenant)
    provisioner = _RecordingIdentityProvisioner()
    service = _service(session_factory, provisioner)

    created = await service.create_user(
        tenant_id=tenant.id,
        email="ops@example.com",
        first_name="Ops",
        last_name="Lead",
        role=RoleEnum.ADMIN,
        temporary_password="change-me-now",
        actor_subject="admin-1",
    )

    assert created.email == "ops@example.com"
    assert created.first_name == "Ops"
    assert created.last_name == "Lead"
    assert created.enabled is True
    assert created.role is RoleEnum.ADMIN
    assert provisioner.provisioned_users == [
        {
            "tenant_id": tenant.id,
            "tenant_slug": "acme",
            "email": "ops@example.com",
            "temporary_password": "change-me-now",
            "first_name": "Ops",
            "last_name": "Lead",
            "role": RoleEnum.ADMIN,
        }
    ]


@pytest.mark.asyncio
async def test_create_user_rejects_superadmin_role() -> None:
    session_factory = _MemorySessionFactory()
    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    session_factory.session.add(tenant)
    service = _service(session_factory, _RecordingIdentityProvisioner())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_user(
            tenant_id=tenant.id,
            email="platform@example.com",
            first_name="Platform",
            last_name="Admin",
            role=RoleEnum.SUPERADMIN,
            temporary_password="change-me-now",
            actor_subject="admin-1",
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_list_users_can_scope_to_tenant_or_return_all_for_superadmin() -> None:
    session_factory = _MemorySessionFactory()
    tenant_a = Tenant(id=uuid4(), name="Acme", slug="acme")
    tenant_b = Tenant(id=uuid4(), name="Beta", slug="beta")
    user_a = User(
        id=uuid4(),
        tenant_id=tenant_a.id,
        email="admin@acme.example",
        oidc_sub="acme-admin",
        role=RoleEnum.ADMIN,
    )
    user_b = User(
        id=uuid4(),
        tenant_id=tenant_b.id,
        email="admin@beta.example",
        oidc_sub="beta-admin",
        role=RoleEnum.ADMIN,
    )
    session_factory.session.rows.extend([tenant_a, tenant_b, user_a, user_b])
    service = _service(session_factory)

    assert [user.email for user in await service.list_users(tenant_id=tenant_a.id)] == [
        "admin@acme.example"
    ]
    assert {user.email for user in await service.list_users(tenant_id=None)} == {
        "admin@acme.example",
        "admin@beta.example",
    }


@pytest.mark.asyncio
async def test_update_user_syncs_keycloak_and_local_role_state() -> None:
    session_factory = _MemorySessionFactory()
    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="ops@acme.example",
        first_name="Ops",
        last_name="Lead",
        oidc_sub="kc-ops-1",
        role=RoleEnum.OPERATOR,
        enabled=True,
    )
    session_factory.session.rows.extend([tenant, user])
    provisioner = _RecordingIdentityProvisioner()
    service = _service(session_factory, provisioner)

    updated = await service.update_user(
        tenant_id=tenant.id,
        user_id=user.id,
        first_name="Operations",
        last_name=None,
        role=RoleEnum.ADMIN,
        enabled=True,
        actor_subject="admin-1",
    )

    assert updated.first_name == "Operations"
    assert updated.last_name == "Lead"
    assert updated.role is RoleEnum.ADMIN
    assert updated.enabled is True
    assert provisioner.updated_users == [
        {
            "user_id": "kc-ops-1",
            "first_name": "Operations",
            "last_name": "Lead",
            "enabled": True,
        }
    ]
    assert provisioner.role_updates == [{"user_id": "kc-ops-1", "role": RoleEnum.ADMIN}]


@pytest.mark.asyncio
async def test_update_user_protects_last_enabled_tenant_admin() -> None:
    session_factory = _MemorySessionFactory()
    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    admin = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="admin@acme.example",
        oidc_sub="kc-admin-1",
        role=RoleEnum.ADMIN,
        enabled=True,
    )
    session_factory.session.rows.extend([tenant, admin])
    service = _service(session_factory, _RecordingIdentityProvisioner())

    with pytest.raises(HTTPException) as exc_info:
        await service.update_user(
            tenant_id=tenant.id,
            user_id=admin.id,
            first_name=None,
            last_name=None,
            role=RoleEnum.OPERATOR,
            enabled=True,
            actor_subject="admin-1",
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_reset_user_password_uses_identity_provider_without_storing_secret() -> None:
    session_factory = _MemorySessionFactory()
    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="ops@acme.example",
        oidc_sub="kc-ops-1",
        role=RoleEnum.OPERATOR,
        enabled=True,
    )
    session_factory.session.rows.extend([tenant, user])
    provisioner = _RecordingIdentityProvisioner()
    service = _service(session_factory, provisioner)

    reset = await service.reset_user_password(
        tenant_id=tenant.id,
        user_id=user.id,
        temporary_password="change-me-now",
        actor_subject="admin-1",
    )

    assert reset.id == user.id
    assert provisioner.password_resets == [
        {"user_id": "kc-ops-1", "temporary_password": "change-me-now"}
    ]
