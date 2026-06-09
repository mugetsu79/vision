# Platform Superadmin UI Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a product UI flow that creates the first platform superadmin and lets that user sign in through the platform realm.

**Architecture:** Reuse the installer-local bootstrap pattern already used for first-run, but keep platform bootstrap separate from tenant bootstrap. Add backend provisioning for the `platform-admin` realm and a frontend platform OIDC manager so the existing Users UI can run in true platform-superadmin mode.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, Alembic, Keycloak Admin REST via `httpx`, React, oidc-client-ts, Vitest, pytest, Playwright.

---

## File Structure

- Modify: `backend/src/argus/models/tables.py`
  - Add a `PlatformBootstrapSession` table or equivalent persisted bootstrap state.
- Create: `backend/src/argus/migrations/versions/0045_platform_superadmin_bootstrap.py`
  - Persist hashed platform bootstrap tokens and consumption metadata.
- Modify: `backend/src/argus/services/identity_bootstrap.py`
  - Add platform realm/client/role/user provisioning helpers.
- Create: `backend/src/argus/services/platform_bootstrap.py`
  - Own status checks, token validation, bootstrap completion, and replay protection.
- Modify: `backend/src/argus/services/app.py`
  - Wire the platform bootstrap service into `AppServices`.
- Create: `backend/src/argus/api/v1/platform_bootstrap.py`
  - Expose status and complete routes.
- Modify: `backend/src/argus/api/v1/__init__.py`
  - Include the platform bootstrap router.
- Modify: `backend/src/argus/api/contracts.py`
  - Add request/response contracts.
- Create: `backend/tests/services/test_platform_bootstrap.py`
  - Test status, completion, replay rejection, and Keycloak provisioning calls.
- Create: `backend/tests/api/test_platform_bootstrap_routes.py`
  - Test route auth, local bootstrap token use, and redaction.
- Modify: `installer/macos/install-master.sh`
  - Generate and preserve the platform bootstrap token file.
- Modify: `installer/linux/install-master.sh`
  - Generate and preserve the platform bootstrap token file.
- Modify: `infra/install/compose/compose.master.yml`
  - Pass platform OIDC authority to frontend and backend.
- Modify: `frontend/src/lib/config.ts`
  - Add `platformOidcAuthority`.
- Modify: `frontend/src/lib/auth.ts`
  - Add platform OIDC manager and realm-aware sign-in.
- Modify: `frontend/src/stores/auth-store.ts`
  - Track the selected sign-in realm.
- Modify: `frontend/src/pages/SignIn.tsx`
  - Add a platform sign-in command.
- Create: `frontend/src/pages/PlatformBootstrap.tsx`
  - Add the first platform-superadmin bootstrap UI.
- Modify: `frontend/src/app/router.tsx`
  - Add `/platform-bootstrap`.
- Create: `frontend/src/pages/PlatformBootstrap.test.tsx`
  - Test bootstrap form behavior and secret redaction.
- Modify: `docs/product-installer-and-first-run-guide.md`
  - Document platform bootstrap and platform sign-in.

## Task 1: Backend Bootstrap State

- [ ] **Step 1: Write the failing model/service test**

Add `backend/tests/services/test_platform_bootstrap.py`:

```python
from __future__ import annotations

from datetime import datetime

import pytest

from argus.compat import UTC
from argus.services.platform_bootstrap import PlatformBootstrapService


@pytest.mark.asyncio
async def test_status_reports_available_before_consumption(fake_session_factory):
    service = PlatformBootstrapService(
        session_factory=fake_session_factory(platform_bootstrap_sessions=[]),
        token_hasher=lambda token: f"hash:{token}",
        now_factory=lambda: datetime(2026, 6, 9, tzinfo=UTC),
    )

    await service.ensure_session(raw_token="vzplat_local_once")
    status = await service.status()

    assert status.available is True
    assert status.consumed_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_platform_bootstrap.py -q
```

Expected: FAIL because `argus.services.platform_bootstrap` does not exist.

- [ ] **Step 3: Add table and migration**

Add a table with columns:

```python
class PlatformBootstrapSession(Base):
    __tablename__ = "platform_bootstrap_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

Create Alembic revision `0045_platform_superadmin_bootstrap` that creates the
table and a unique index on `token_hash`.

- [ ] **Step 4: Implement `PlatformBootstrapService.ensure_session` and `status`**

Create `backend/src/argus/services/platform_bootstrap.py` with:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.models.tables import PlatformBootstrapSession


@dataclass(frozen=True)
class PlatformBootstrapStatus:
    available: bool
    consumed_at: datetime | None


class PlatformBootstrapService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        token_hasher: Callable[[str], str],
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.token_hasher = token_hasher
        self.now_factory = now_factory or (lambda: datetime.now(tz=UTC))

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
            if existing is not None:
                return existing
            row = PlatformBootstrapSession(
                token_hash=token_hash,
                created_at=self.now_factory(),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def status(self) -> PlatformBootstrapStatus:
        async with self.session_factory() as session:
            row = (
                await session.execute(
                    select(PlatformBootstrapSession).order_by(
                        PlatformBootstrapSession.created_at.desc()
                    )
                )
            ).scalars().first()
        return PlatformBootstrapStatus(
            available=row is not None and row.consumed_at is None,
            consumed_at=row.consumed_at if row is not None else None,
        )
```

- [ ] **Step 5: Run backend service test**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_platform_bootstrap.py -q
```

Expected: PASS for the new status test.

## Task 2: Platform Realm Provisioning

- [ ] **Step 1: Write failing provisioning tests**

Extend `backend/tests/services/test_identity_bootstrap.py` with:

```python
@pytest.mark.asyncio
async def test_provision_platform_superadmin_creates_realm_clients_role_and_user():
    transport = RecordingKeycloakTransport()
    provisioner = KeycloakBootstrapProvisioner(
        base_url="http://keycloak.local",
        admin_username="admin",
        admin_password="secret",
        client=httpx.AsyncClient(transport=transport),
    )

    await provisioner.provision_platform_superadmin(
        email="owner@example.com",
        temporary_password="change-me-123456",
        first_name="Owner",
        last_name="One",
        platform_realm="platform-admin",
    )

    assert transport.saw("PUT", "/admin/realms/platform-admin")
    assert transport.saw("POST", "/admin/realms/platform-admin/roles")
    assert transport.saw("POST", "/admin/realms/platform-admin/users")
    assert transport.saw("POST", "/admin/realms/platform-admin/users/platform-user-id/role-mappings/realm")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_identity_bootstrap.py::test_provision_platform_superadmin_creates_realm_clients_role_and_user -q
```

Expected: FAIL because `provision_platform_superadmin` does not exist.

- [ ] **Step 3: Implement platform provisioning**

Add `KeycloakBootstrapProvisioner.provision_platform_superadmin` that:

- obtains the master admin token with `_admin_token`;
- creates or updates realm `platform-admin`;
- creates realm role `superadmin` when absent;
- creates or repairs public clients `argus-frontend` and `argus-cli`;
- creates or updates the user with first name, last name, email, enabled state,
  and temporary password;
- assigns the `superadmin` realm role.

- [ ] **Step 4: Run provisioning tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_identity_bootstrap.py backend/tests/services/test_platform_bootstrap.py -q
```

Expected: PASS.

## Task 3: Bootstrap Completion API

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/api/test_platform_bootstrap_routes.py`:

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_platform_bootstrap_complete_consumes_token_and_redacts_response(app_with_platform_bootstrap):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_platform_bootstrap),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/platform/bootstrap/complete",
            json={
                "bootstrap_token": "vzplat_local_once",
                "email": "owner@example.com",
                "first_name": "Owner",
                "last_name": "One",
                "password": "change-me-123456",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "owner@example.com"
    assert "password" not in body
    assert "bootstrap_token" not in body
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_platform_bootstrap_routes.py -q
```

Expected: FAIL because the route does not exist.

- [ ] **Step 3: Add contracts and router**

Add contracts:

```python
class PlatformBootstrapStatusResponse(BaseModel):
    available: bool
    consumed_at: datetime | None = None


class PlatformBootstrapComplete(BaseModel):
    bootstrap_token: str = Field(min_length=16, max_length=256)
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=256)


class PlatformBootstrapCompleteResponse(BaseModel):
    email: EmailStr
    realm: str
    role: Literal["superadmin"] = "superadmin"
```

Expose:

- `GET /api/v1/platform/bootstrap/status`
- `POST /api/v1/platform/bootstrap/complete`

- [ ] **Step 4: Run API tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_platform_bootstrap_routes.py backend/tests/services/test_platform_bootstrap.py -q
```

Expected: PASS.

## Task 4: Frontend Platform Sign-In

- [ ] **Step 1: Write failing auth/config tests**

Update `frontend/src/lib/auth.test.ts`:

```ts
test("platform sign-in uses the platform authority", async () => {
  const manager = createOidcManager("platform");

  expect(manager.settings.authority).toBe("http://127.0.0.1:8080/realms/platform-admin");
});
```

Update `frontend/src/lib/config.test.ts`:

```ts
expect(config.platformOidcAuthority).toBe("http://127.0.0.1:8080/realms/platform-admin");
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
corepack pnpm --dir frontend test src/lib/auth.test.ts src/lib/config.test.ts
```

Expected: FAIL because platform OIDC config is missing.

- [ ] **Step 3: Implement platform OIDC config and manager**

Add `VITE_PLATFORM_OIDC_AUTHORITY` to config parsing. Export:

```ts
export type AuthRealm = "tenant" | "platform";

export function createOidcManager(realm: AuthRealm) {
  return new UserManager({
    authority: realm === "platform" ? frontendConfig.platformOidcAuthority : frontendConfig.oidcAuthority,
    client_id: frontendConfig.oidcClientId,
    redirect_uri: frontendConfig.oidcRedirectUri,
    post_logout_redirect_uri: frontendConfig.oidcPostLogoutRedirectUri,
    response_type: "code",
    scope: "openid profile email",
    disablePKCE: frontendConfig.oidcDisablePkce,
    userStore: new WebStorageStateStore({ store: window.localStorage }),
  });
}
```

- [ ] **Step 4: Run frontend auth/config tests**

Run:

```bash
corepack pnpm --dir frontend test src/lib/auth.test.ts src/lib/config.test.ts
```

Expected: PASS.

## Task 5: Platform Bootstrap UI

- [ ] **Step 1: Write failing UI test**

Create `frontend/src/pages/PlatformBootstrap.test.tsx`:

```tsx
test("submits bootstrap form without rendering secrets", async () => {
  renderWithProviders(<PlatformBootstrapPage />);

  await userEvent.type(screen.getByLabelText("Bootstrap token"), "vzplat_local_once");
  await userEvent.type(screen.getByLabelText("Email"), "owner@example.com");
  await userEvent.type(screen.getByLabelText("First name"), "Owner");
  await userEvent.type(screen.getByLabelText("Last name"), "One");
  await userEvent.type(screen.getByLabelText("Password"), "change-me-123456");
  await userEvent.click(screen.getByRole("button", { name: "Create platform admin" }));

  expect(await screen.findByText("Platform admin created")).toBeInTheDocument();
  expect(screen.queryByText("change-me-123456")).not.toBeInTheDocument();
  expect(screen.queryByText("vzplat_local_once")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend test src/pages/PlatformBootstrap.test.tsx
```

Expected: FAIL because the page does not exist.

- [ ] **Step 3: Implement page and route**

Create `PlatformBootstrapPage` with fields:

- Bootstrap token
- Email
- First name
- Last name
- Password

Submit `POST /api/v1/platform/bootstrap/complete`, clear all secret fields on
success and failure, and navigate to `/signin` after success.

- [ ] **Step 4: Add platform sign-in command**

Update `SignIn.tsx` to render two commands:

- `Sign in`
- `Platform sign in`

The platform command calls `signIn("platform")`.

- [ ] **Step 5: Run frontend tests**

Run:

```bash
corepack pnpm --dir frontend test src/pages/PlatformBootstrap.test.tsx src/pages/SignIn.test.tsx src/lib/auth.test.ts
```

Expected: PASS.

## Task 6: Installer, Docs, And Live Smoke

- [ ] **Step 1: Update installers**

Modify macOS and Linux master installers to write:

```bash
VEZOR_PLATFORM_OIDC_AUTHORITY=$PUBLIC_KEYCLOAK_URL/realms/platform-admin
VITE_PLATFORM_OIDC_AUTHORITY=$PUBLIC_KEYCLOAK_URL/realms/platform-admin
```

Generate a local bootstrap token file:

```bash
$CONFIG_DIR/secrets/platform_bootstrap_token
```

with mode `0640` and Docker Desktop-readable group ownership on macOS.

- [ ] **Step 2: Validate installers**

Run:

```bash
scripts/validate-installers.sh
```

Expected: PASS and product secret scan does not print the token.

- [ ] **Step 3: Run full automated suites**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests -q
corepack pnpm --dir frontend test
corepack pnpm --dir frontend exec tsc -b
```

Expected: all PASS.

- [ ] **Step 4: Installed live smoke**

On a fresh installed master:

1. Complete first-run and sign in as the tenant admin.
2. Open `/platform-bootstrap`.
3. Create the first platform superadmin using the local platform bootstrap token.
4. Sign out.
5. Use `Platform sign in`.
6. Open `/users`.
7. Create a new tenant.
8. Create a tenant admin in that new tenant.

Expected: `/users` shows platform-superadmin controls, the new tenant exists,
and the new tenant admin can sign in through the tenant realm.

## Self-Review

- Spec coverage: Covers initial platform-superadmin creation from Vezor UI,
  platform sign-in, tenant creation, tenant-user creation, and secret handling.
- Placeholder scan: No placeholder implementation steps remain.
- Type consistency: `PlatformBootstrapService`, `PlatformBootstrapStatus`, and
  route contract names are consistent across tasks.
