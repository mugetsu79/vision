# Tenant User and Admin Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build tenant-scoped user and admin management so additional admins, operators, and viewers can be created after first-run without using the Keycloak console.

**Architecture:** Keep Keycloak as the authentication system and Vezor as the tenant authorization mirror. Add a backend user-management service that provisions Keycloak users and keeps the local `users` table synchronized, then expose admin-only APIs and a compact Users view.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, Keycloak Admin REST via `httpx`, React, openapi-fetch, Vitest, pytest.

---

## File Structure

- Modify: `backend/src/argus/services/identity_bootstrap.py`
  - Extract reusable Keycloak user create/update, role assignment, and attribute mapper helpers.
- Create: `backend/src/argus/services/user_management.py`
  - Tenant-scoped user orchestration against Keycloak plus local `User` rows.
- Modify: `backend/src/argus/services/app.py`
  - Add `users` service to `AppServices`.
- Modify: `backend/src/argus/api/contracts.py`
  - Add request/response contracts for user management.
- Create: `backend/src/argus/api/v1/users.py`
  - Add admin-only user routes.
- Modify: `backend/src/argus/api/v1/__init__.py`
  - Include the users router.
- Create: `backend/tests/services/test_user_management.py`
  - Unit tests for tenant scoping, Keycloak calls, role rules, and last-admin protection.
- Create: `backend/tests/api/test_users_routes.py`
  - Route tests for RBAC, tenant isolation, and response redaction.
- Create: `frontend/src/hooks/use-users.ts`
  - Query/mutation hooks for `/api/v1/users`.
- Create: `frontend/src/pages/Users.tsx`
  - Admin-facing user table and dialogs.
- Modify: `frontend/src/app/router.tsx`
  - Add route for the users page.
- Modify: `frontend/src/components/layout/AppShell.tsx`
  - Add admin-visible navigation entry if the shell has role-aware navigation.
- Create: `frontend/src/pages/Users.test.tsx`
  - UI tests for create, role change, disable, and reset flows.

## Task 1: Backend Contracts and Service

- [ ] **Step 1: Write failing service tests**

Create `backend/tests/services/test_user_management.py`:

```python
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.compat import UTC
from argus.models.enums import RoleEnum
from argus.models.tables import Tenant, User
from argus.services.user_management import UserManagementService


class FakeIdentityProvisioner:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.roles: list[tuple[str, RoleEnum]] = []

    async def provision_tenant_user(self, **kwargs):
        self.created.append(kwargs)
        return f"keycloak:{kwargs['email']}"

    async def set_user_role(self, *, user_id: str, role: RoleEnum) -> None:
        self.roles.append((user_id, role))


@pytest.mark.asyncio
async def test_create_user_provisions_keycloak_and_local_row(fake_session_factory):
    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    provisioner = FakeIdentityProvisioner()
    service = UserManagementService(
        session_factory=fake_session_factory(tenants=[tenant], users=[]),
        identity_provisioner=provisioner,
        now_factory=lambda: datetime(2026, 6, 9, tzinfo=UTC),
    )

    created = await service.create_user(
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        email="ops@example.com",
        first_name="Ops",
        last_name="Lead",
        role=RoleEnum.ADMIN,
        temporary_password="change-me",
        actor_subject="admin-1",
    )

    assert created.email == "ops@example.com"
    assert created.role is RoleEnum.ADMIN
    assert provisioner.created[0]["tenant_id"] == tenant.id
    assert provisioner.created[0]["tenant_slug"] == "acme"


@pytest.mark.asyncio
async def test_create_user_rejects_superadmin(fake_session_factory):
    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    service = UserManagementService(
        session_factory=fake_session_factory(tenants=[tenant], users=[]),
        identity_provisioner=FakeIdentityProvisioner(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.create_user(
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            email="platform@example.com",
            first_name="Platform",
            last_name="Admin",
            role=RoleEnum.SUPERADMIN,
            temporary_password="change-me",
            actor_subject="admin-1",
        )

    assert exc_info.value.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_user_management.py -q
```

Expected: failure because `argus.services.user_management` does not exist.

- [ ] **Step 3: Add contracts**

Modify `backend/src/argus/api/contracts.py`:

```python
class ManagedUserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    oidc_sub: str
    role: RoleEnum
    enabled: bool = True
    created_at: datetime
    updated_at: datetime | None = None


class ManagedUserCreate(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    role: RoleEnum
    temporary_password: str = Field(min_length=12, max_length=256)


class ManagedUserPatch(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    role: RoleEnum | None = None
    enabled: bool | None = None


class ManagedUserResetPassword(BaseModel):
    temporary_password: str = Field(min_length=12, max_length=256)
```

- [ ] **Step 4: Implement service**

Create `backend/src/argus/services/user_management.py` with:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.models.enums import RoleEnum
from argus.models.tables import Tenant, User
from argus.services.identity_bootstrap import KeycloakBootstrapProvisioner

TENANT_ASSIGNABLE_ROLES = {RoleEnum.VIEWER, RoleEnum.OPERATOR, RoleEnum.ADMIN}


class UserManagementService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        identity_provisioner: KeycloakBootstrapProvisioner | None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.identity_provisioner = identity_provisioner
        self.now_factory = now_factory or (lambda: datetime.now(tz=UTC))

    async def list_users(self, *, tenant_id: UUID) -> list[User]:
        async with self.session_factory() as session:
            rows = list(
                (
                    await session.execute(
                        select(User).where(User.tenant_id == tenant_id).order_by(User.email.asc())
                    )
                )
                .scalars()
                .all()
            )
        return [row for row in rows if isinstance(row, User)]

    async def create_user(
        self,
        *,
        tenant_id: UUID,
        tenant_slug: str,
        email: str,
        first_name: str,
        last_name: str,
        role: RoleEnum,
        temporary_password: str,
        actor_subject: str,
    ) -> User:
        del actor_subject
        self._ensure_assignable_role(role)
        if self.identity_provisioner is None:
            raise HTTPException(status_code=503, detail="Identity provider is not configured.")
        async with self.session_factory() as session:
            tenant = await session.get(Tenant, tenant_id)
            if not isinstance(tenant, Tenant):
                raise HTTPException(status_code=404, detail="Tenant not found.")
            existing = await self._user_by_email(session, tenant_id=tenant_id, email=email)
            if existing is not None:
                raise HTTPException(status_code=409, detail="User already exists.")
            oidc_sub = await self.identity_provisioner.provision_tenant_user(
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                email=email,
                temporary_password=temporary_password,
                first_name=first_name,
                last_name=last_name,
                role=role,
            )
            now = self.now_factory()
            user = User(tenant_id=tenant_id, email=email, oidc_sub=oidc_sub, role=role)
            user.created_at = now
            user.updated_at = now
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

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

    def _ensure_assignable_role(self, role: RoleEnum) -> None:
        if role not in TENANT_ASSIGNABLE_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Role cannot be assigned by a tenant admin.",
            )
```

- [ ] **Step 5: Run service tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_user_management.py -q
```

Expected: service tests pass after adapting the fake session fixture to the
project's existing test helpers.

## Task 2: Keycloak Reusable User Provisioning

- [ ] **Step 1: Write failing identity tests**

Add tests in `backend/tests/services/test_identity_bootstrap.py` that call
`KeycloakBootstrapProvisioner.provision_tenant_user(...)` with `RoleEnum.OPERATOR`
and assert these Keycloak Admin API requests are made:

```python
assert post_user_payload["attributes"]["tenant"] == ["acme"]
assert post_user_payload["attributes"]["tenant_id"] == [str(tenant_id)]
assert role_mapping_payload[0]["name"] == "operator"
```

- [ ] **Step 2: Run identity test to verify failure**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_identity_bootstrap.py -q
```

Expected: failure because `provision_tenant_user` is not implemented.

- [ ] **Step 3: Extract and implement reusable provisioner method**

Modify `backend/src/argus/services/identity_bootstrap.py`:

```python
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
) -> str:
    if role is RoleEnum.SUPERADMIN:
        raise KeycloakBootstrapError("Tenant users cannot be assigned superadmin.")
    token = await self._admin_token()
    for required_role in (RoleEnum.VIEWER, RoleEnum.OPERATOR, RoleEnum.ADMIN):
        await self._ensure_realm_role(token, required_role.value)
    user_id = await self._ensure_admin_user(
        token,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        admin_email=email,
        admin_password=temporary_password,
        admin_first_name=first_name,
        admin_last_name=last_name,
    )
    await self._ensure_realm_role_assignment(token, user_id, role.value)
    return user_id
```

Then update `provision_tenant_admin(...)` to call `provision_tenant_user(...)`
with `role=RoleEnum.ADMIN` after it ensures the realm, clients, and mappers.

- [ ] **Step 4: Run identity tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_identity_bootstrap.py -q
```

Expected: all identity bootstrap tests pass.

## Task 3: Admin API Routes

- [ ] **Step 1: Write failing route tests**

Create `backend/tests/api/test_users_routes.py`:

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_admin_can_create_tenant_user(app_with_admin_user):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_admin_user),
        base_url="http://test",
        headers={"Authorization": "Bearer admin-token"},
    ) as client:
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "ops@example.com",
                "first_name": "Ops",
                "last_name": "Lead",
                "role": "operator",
                "temporary_password": "change-me-now",
            },
        )

    assert response.status_code == 201
    assert response.json()["email"] == "ops@example.com"
    assert "temporary_password" not in response.json()
```

- [ ] **Step 2: Run route test to verify failure**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_users_routes.py -q
```

Expected: failure because `/api/v1/users` is not registered.

- [ ] **Step 3: Add router**

Create `backend/src/argus/api/v1/users.py`:

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from argus.api.contracts import (
    ManagedUserCreate,
    ManagedUserResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import require
from argus.models.enums import RoleEnum
from argus.models.tables import User
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/users", tags=["users"])
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
AdminUser = Annotated[object, Depends(require(RoleEnum.ADMIN))]


@router.get("", response_model=list[ManagedUserResponse])
async def list_users(
    _current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> list[ManagedUserResponse]:
    rows = await services.users.list_users(tenant_id=tenant_context.tenant_id)
    return [_user_response(row) for row in rows]


@router.post("", response_model=ManagedUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: ManagedUserCreate,
    _current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> ManagedUserResponse:
    user = await services.users.create_user(
        tenant_id=tenant_context.tenant_id,
        tenant_slug=tenant_context.tenant_slug,
        email=str(payload.email),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        temporary_password=payload.temporary_password,
        actor_subject=tenant_context.user.subject,
    )
    return _user_response(user)


def _user_response(row: User) -> ManagedUserResponse:
    return ManagedUserResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        email=row.email,
        oidc_sub=row.oidc_sub,
        role=row.role,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
```

Modify `backend/src/argus/api/v1/__init__.py` to import `users` and include
`router.include_router(users.router)` with the other v1 routers.

- [ ] **Step 4: Wire service into `AppServices`**

Modify `backend/src/argus/services/app.py` so `build_app_services(...)` creates
`UserManagementService(session_factory=db.session_factory, identity_provisioner=...)`
and stores it as `services.users`.

- [ ] **Step 5: Run route tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_users_routes.py -q
```

Expected: route tests pass and no response contains password fields.

## Task 4: Frontend Users View

- [ ] **Step 1: Write failing hook and page tests**

Create `frontend/src/pages/Users.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { UsersPage } from "@/pages/Users";

describe("UsersPage", () => {
  test("creates a tenant operator without rendering the password after submit", async () => {
    const user = userEvent.setup();
    render(<UsersPage />);

    await user.click(screen.getByRole("button", { name: /create user/i }));
    await user.type(screen.getByLabelText(/email/i), "ops@example.com");
    await user.type(screen.getByLabelText(/first name/i), "Ops");
    await user.type(screen.getByLabelText(/last name/i), "Lead");
    await user.selectOptions(screen.getByLabelText(/role/i), "operator");
    await user.type(screen.getByLabelText(/temporary password/i), "change-me-now");
    await user.click(screen.getByRole("button", { name: /create/i }));

    expect(await screen.findByText("ops@example.com")).toBeInTheDocument();
    expect(screen.queryByText("change-me-now")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run frontend test to verify failure**

Run:

```bash
npm --prefix frontend test -- Users.test.tsx --run
```

Expected: failure because `UsersPage` does not exist.

- [ ] **Step 3: Add hooks**

Create `frontend/src/hooks/use-users.ts` with `useQuery` for
`GET /api/v1/users` and `useMutation` for `POST /api/v1/users`, using the same
`apiClient` and `toApiError` pattern as `frontend/src/hooks/use-bootstrap.ts`.

- [ ] **Step 4: Add page**

Create `frontend/src/pages/Users.tsx` with:

```tsx
export function UsersPage() {
  const users = useUsers();
  const createUser = useCreateUser();

  return (
    <WorkspacePage title="Users">
      <Toolbar>
        <Button type="button" onClick={() => setCreateOpen(true)}>
          <UserPlus className="size-4" aria-hidden="true" />
          Create user
        </Button>
      </Toolbar>
      <DataTable rows={users.data ?? []} columns={userColumns} />
      <CreateUserDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={(payload) => createUser.mutate(payload)}
      />
    </WorkspacePage>
  );
}
```

Use the existing app table/dialog primitives if present; otherwise use the
smallest existing settings/deployment page pattern. Keep the first screen an
operational table, not a marketing page.

- [ ] **Step 5: Route the page**

Modify `frontend/src/app/router.tsx` to add `/users`, and modify the app shell
navigation to show it only to `admin` and `superadmin` roles.

- [ ] **Step 6: Run frontend tests**

Run:

```bash
npm --prefix frontend test -- Users.test.tsx --run
```

Expected: user-management page tests pass.

## Task 5: End-to-End Verification

- [ ] **Step 1: Regenerate OpenAPI client**

Run:

```bash
python3 -m uv run --project backend python - <<'PY' > frontend/src/lib/openapi.json
import json

from argus.main import create_app

print(json.dumps(create_app().openapi()))
PY
corepack pnpm --dir frontend generate:api
```

Expected: `frontend/src/lib/openapi.json` and
`frontend/src/lib/api.generated.ts` include `/api/v1/users`.

- [ ] **Step 2: Backend verification**

Run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/services/test_identity_bootstrap.py \
  backend/tests/services/test_user_management.py \
  backend/tests/api/test_users_routes.py \
  -q
```

Expected: all selected backend tests pass.

- [ ] **Step 3: Frontend verification**

Run:

```bash
npm --prefix frontend test -- Users.test.tsx --run
npm --prefix frontend run typecheck
```

Expected: page test and typecheck pass.

- [ ] **Step 4: Manual installed smoke**

On a disposable installed master:

```bash
curl -fsS -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/v1/users
curl -fsS -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/users \
  -d '{"email":"ops@example.com","first_name":"Ops","last_name":"Lead","role":"admin","temporary_password":"change-me-now"}'
```

Expected: the created user can sign in, receives `tenant` and `tenant_id`
claims, and can perform an admin-only action inside the same tenant.
