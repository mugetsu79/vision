# Prompt 7 Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first real Argus frontend foundation with real Keycloak PKCE auth, a typed OpenAPI-driven client, a dark-first hybrid command-center shell aligned to the Argus visual brief, and working Sites/Cameras CRUD including a stepped camera setup flow with homography editing and browser delivery-profile controls.

**Architecture:** The implementation keeps frontend responsibilities split cleanly: React Router owns navigation, Zustand owns auth/session state, TanStack Query owns server data, and route-level pages compose reusable shell and workflow components. Prompt 7 stays intentionally narrow: it creates a solid app frame and management workflows without pulling in Prompt 8 live-stream concerns, but it must already establish the Argus visual system and the native-ingest versus browser-delivery distinction used by later streaming prompts.

**Tech Stack:** React 19, Vite, TypeScript, React Router, Zustand, oidc-client-ts, openapi-typescript, openapi-fetch, TanStack Query, Tailwind v4, local shadcn-style UI components, Vitest, Testing Library, Playwright.

---

## File Map

### Frontend app bootstrap and routing

- Modify: `frontend/package.json`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Create: `frontend/src/app/providers.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/query-client.ts`
- Create: `frontend/src/pages/SignIn.tsx`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/.env.example`

### Auth and config

- Modify: `infra/keycloak/realm-export.json`
- Modify: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/config.ts`
- Create: `frontend/src/stores/auth-store.ts`
- Create: `frontend/src/components/auth/RequireAuth.tsx`
- Create: `frontend/src/components/auth/RequireRole.tsx`
- Modify: `frontend/src/pages/SignIn.tsx`
- Create: `frontend/src/pages/AuthCallback.tsx`

### Typed API and query hooks

- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/api.generated.ts`
- Create: `frontend/src/hooks/use-sites.ts`
- Create: `frontend/src/hooks/use-cameras.ts`
- Create: `frontend/src/hooks/use-models.ts`
- Create: `frontend/src/test/query-test-utils.tsx`

### Shell and UI primitives

- Modify: `frontend/src/index.css`
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/select.tsx`
- Create: `frontend/src/components/ui/dialog.tsx`
- Create: `frontend/src/components/ui/table.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/TopNav.tsx`
- Create: `frontend/src/components/layout/UserMenu.tsx`
- Create: `frontend/src/components/layout/TenantSwitcher.tsx`

### Pages and workflows

- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Create: `frontend/src/components/sites/SiteDialog.tsx`
- Create: `frontend/src/components/cameras/CameraWizard.tsx`
- Create: `frontend/src/components/cameras/HomographyEditor.tsx`
- Create: `frontend/src/components/cameras/CameraStepSummary.tsx`

### Frontend tests and E2E

- Create: `frontend/src/components/auth/RequireAuth.test.tsx`
- Create: `frontend/src/components/auth/RequireRole.test.tsx`
- Create: `frontend/src/pages/SignIn.test.tsx`
- Create: `frontend/src/pages/Sites.test.tsx`
- Create: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/prompt7-auth-and-camera.spec.ts`

---

### Task 1: Bootstrap Router, Providers, and Frontend Dependencies

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Create: `frontend/src/app/providers.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/query-client.ts`
- Create: `frontend/src/pages/SignIn.tsx`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/.env.example`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing router/bootstrap test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import App from "@/App";

describe("App router bootstrap", () => {
  test("renders the branded sign-in entry point for anonymous users", async () => {
    window.history.pushState({}, "", "/");

    render(<App />);

    expect(
      await screen.findByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/argus \| the omnisight platform/i),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `corepack pnpm test -- src/App.test.tsx`

Expected: FAIL because the current scaffold page does not render a routed sign-in entry point.

- [ ] **Step 3: Install routing/query dependencies and replace the scaffold bootstrap**

Run:

```bash
cd frontend
corepack pnpm add react-router-dom @tanstack/react-query @tanstack/react-query-devtools zustand oidc-client-ts openapi-fetch
corepack pnpm add -D openapi-typescript @playwright/test
```

Replace `frontend/src/App.tsx` with:

```tsx
import { RouterProvider } from "react-router-dom";

import { router } from "@/app/router";

export default function App() {
  return <RouterProvider router={router} />;
}
```

Create `frontend/src/app/query-client.ts`:

```tsx
import { QueryClient } from "@tanstack/react-query";

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
```

Create `frontend/src/app/providers.tsx`:

```tsx
import type { PropsWithChildren } from "react";
import { QueryClientProvider } from "@tanstack/react-query";

import { createQueryClient } from "@/app/query-client";

const queryClient = createQueryClient();

export function AppProviders({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

Create `frontend/src/app/router.tsx`:

```tsx
import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppProviders } from "@/app/providers";
import { SignInPage } from "@/pages/SignIn";

function PlaceholderPage({ title }: { title: string }) {
  return <main className="p-8">{title}</main>;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AppProviders>
        <SignInPage />
      </AppProviders>
    ),
  },
  { path: "/signin", element: <SignInPage /> },
  { path: "/dashboard", element: <PlaceholderPage title="Dashboard" /> },
  { path: "*", element: <Navigate to="/" replace /> },
]);
```

Create `frontend/src/pages/SignIn.tsx`:

```tsx
export function SignInPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(40,110,255,0.16),_transparent_32%),radial-gradient(circle_at_85%_12%,_rgba(133,88,255,0.18),_transparent_28%),linear-gradient(180deg,#05070c_0%,#0a1018_48%,#121927_100%)] px-6 py-10 text-[#eef4ff]">
      <section className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl items-center justify-center rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,20,31,0.92),rgba(8,11,18,0.88))] p-8 shadow-[0_32px_120px_-50px_rgba(26,110,255,0.45)] backdrop-blur-xl">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[#b7c8e6]">Argus | The OmniSight Platform</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[0.01em] text-[#f5f8ff]">Vigilant intelligence for every camera surface.</h1>
          <p className="mt-3 text-sm text-[#a7b4cb]">Sign in to continue.</p>
          <button className="mt-6 rounded-full bg-[linear-gradient(135deg,#3b82f6_0%,#8b5cf6_100%)] px-4 py-2 text-sm font-medium text-white shadow-[0_12px_32px_-18px_rgba(95,118,255,0.95)]">
            Sign in
          </button>
        </div>
      </section>
    </main>
  );
}
```

Update `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Create `frontend/src/vite-env.d.ts`:

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_OIDC_AUTHORITY: string;
  readonly VITE_OIDC_CLIENT_ID: string;
  readonly VITE_OIDC_REDIRECT_URI: string;
  readonly VITE_OIDC_POST_LOGOUT_REDIRECT_URI: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

Create `frontend/.env.example`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_OIDC_AUTHORITY=http://127.0.0.1:8080/realms/argus-dev
VITE_OIDC_CLIENT_ID=argus-frontend
VITE_OIDC_REDIRECT_URI=http://127.0.0.1:3000/auth/callback
VITE_OIDC_POST_LOGOUT_REDIRECT_URI=http://127.0.0.1:3000/signin
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `corepack pnpm test -- src/App.test.tsx`

Expected: PASS with the sign-in route rendered by the new router bootstrap.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/main.tsx frontend/src/app frontend/src/pages/SignIn.tsx frontend/src/vite-env.d.ts frontend/.env.example
git commit -m "feat: bootstrap prompt 7 frontend routing foundation"
```

### Task 2: Implement Real OIDC PKCE Auth, Session Store, and Guards

**Files:**
- Modify: `infra/keycloak/realm-export.json`
- Modify: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/config.ts`
- Create: `frontend/src/stores/auth-store.ts`
- Create: `frontend/src/components/auth/RequireAuth.tsx`
- Create: `frontend/src/components/auth/RequireRole.tsx`
- Modify: `frontend/src/pages/SignIn.tsx`
- Create: `frontend/src/pages/AuthCallback.tsx`
- Create: `frontend/src/components/auth/RequireAuth.test.tsx`
- Create: `frontend/src/components/auth/RequireRole.test.tsx`
- Create: `frontend/src/pages/SignIn.test.tsx`
- Test: `frontend/src/components/auth/RequireAuth.test.tsx`
- Test: `frontend/src/components/auth/RequireRole.test.tsx`
- Test: `frontend/src/pages/SignIn.test.tsx`

- [ ] **Step 1: Write failing auth and guard tests**

Create `frontend/src/components/auth/RequireAuth.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test } from "vitest";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuthStore } from "@/stores/auth-store";

describe("RequireAuth", () => {
  beforeEach(() => {
    useAuthStore.setState({
      status: "anonymous",
      user: null,
      accessToken: null,
    });
  });

  test("redirects anonymous users to the sign-in page", async () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route path="/signin" element={<div>Sign in page</div>} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <div>Private dashboard</div>
              </RequireAuth>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Sign in page")).toBeInTheDocument();
  });
});
```

Create `frontend/src/components/auth/RequireRole.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { RequireRole } from "@/components/auth/RequireRole";
import { useAuthStore } from "@/stores/auth-store";

describe("RequireRole", () => {
  test("renders an access denied state when the user lacks the required role", () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "token",
      user: {
        sub: "viewer-1",
        email: "viewer@argus.local",
        role: "viewer",
        realm: "argus-dev",
        isSuperadmin: false,
        tenantId: "tenant-1",
      },
    });

    render(
      <RequireRole role="admin">
        <div>Admin content</div>
      </RequireRole>,
    );

    expect(screen.getByText(/you do not have access to this page/i)).toBeInTheDocument();
    expect(screen.queryByText("Admin content")).not.toBeInTheDocument();
  });
});
```

Create `frontend/src/pages/SignIn.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { SignInPage } from "@/pages/SignIn";
import { useAuthStore } from "@/stores/auth-store";

describe("SignInPage", () => {
  test("starts the OIDC login flow when the user clicks sign in", async () => {
    const signIn = vi.fn().mockResolvedValue(undefined);
    useAuthStore.setState({
      status: "anonymous",
      user: null,
      accessToken: null,
      signIn,
    });

    render(<SignInPage />);
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(signIn).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run the auth tests to verify they fail**

Run:

```bash
cd frontend
corepack pnpm test -- src/components/auth/RequireAuth.test.tsx src/components/auth/RequireRole.test.tsx src/pages/SignIn.test.tsx
```

Expected: FAIL because the auth store, guards, and sign-in page do not exist yet.

- [ ] **Step 3: Implement config, auth client, seeded admin user, store, sign-in page, and guards**

Modify `infra/keycloak/realm-export.json` to add an admin test user alongside the existing viewer:

```json
{
  "username": "admin-dev",
  "firstName": "Admin",
  "lastName": "Dev",
  "enabled": true,
  "email": "admin-dev@argus.local",
  "emailVerified": true,
  "requiredActions": [],
  "credentials": [
    {
      "type": "password",
      "value": "argus-admin-pass",
      "temporary": false
    }
  ],
  "realmRoles": ["admin"]
}
```

Create `frontend/src/lib/config.ts`:

```ts
function requireEnv(key: keyof ImportMetaEnv) {
  const value = import.meta.env[key];
  if (!value) {
    throw new Error(`Missing required frontend env var: ${key}`);
  }
  return value;
}

export const frontendConfig = {
  apiBaseUrl: requireEnv("VITE_API_BASE_URL"),
  oidcAuthority: requireEnv("VITE_OIDC_AUTHORITY"),
  oidcClientId: requireEnv("VITE_OIDC_CLIENT_ID"),
  oidcRedirectUri: requireEnv("VITE_OIDC_REDIRECT_URI"),
  oidcPostLogoutRedirectUri: requireEnv("VITE_OIDC_POST_LOGOUT_REDIRECT_URI"),
} as const;
```

Replace `frontend/src/lib/auth.ts` with:

```ts
import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";

import { frontendConfig } from "@/lib/config";

export type ArgusRole = "viewer" | "operator" | "admin" | "superadmin";

export interface SessionUser {
  sub: string;
  email: string | null;
  role: ArgusRole;
  realm: string;
  tenantId: string | null;
  isSuperadmin: boolean;
}

export const oidcManager = new UserManager({
  authority: frontendConfig.oidcAuthority,
  client_id: frontendConfig.oidcClientId,
  redirect_uri: frontendConfig.oidcRedirectUri,
  post_logout_redirect_uri: frontendConfig.oidcPostLogoutRedirectUri,
  response_type: "code",
  scope: "openid profile email",
  userStore: new WebStorageStateStore({ store: window.localStorage }),
});

export function mapOidcUser(user: User): SessionUser {
  const roles = Array.isArray(user.profile.realm_access?.roles)
    ? user.profile.realm_access.roles
    : [];
  const highestRole =
    ["superadmin", "admin", "operator", "viewer"].find((role) => roles.includes(role)) as ArgusRole | undefined;
  const realm = String(user.profile.iss ?? "").split("/").at(-1) ?? "argus-dev";

  if (!highestRole) {
    throw new Error("OIDC user is missing a recognized Argus role.");
  }

  return {
    sub: String(user.profile.sub),
    email: typeof user.profile.email === "string" ? user.profile.email : null,
    role: highestRole,
    realm,
    tenantId:
      typeof user.profile.tenant_id === "string"
        ? user.profile.tenant_id
        : typeof user.profile.tenant === "string"
          ? user.profile.tenant
          : null,
    isSuperadmin: realm === "platform-admin" && highestRole === "superadmin",
  };
}
```

Create `frontend/src/stores/auth-store.ts`:

```ts
import { create } from "zustand";

import { mapOidcUser, oidcManager, type SessionUser } from "@/lib/auth";

type AuthStatus = "anonymous" | "loading" | "authenticated";

interface AuthState {
  status: AuthStatus;
  user: SessionUser | null;
  accessToken: string | null;
  signIn: () => Promise<void>;
  completeSignIn: () => Promise<void>;
  restoreSession: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  status: "anonymous",
  user: null,
  accessToken: null,
  async signIn() {
    await oidcManager.signinRedirect();
  },
  async completeSignIn() {
    set({ status: "loading" });
    try {
      const user = await oidcManager.signinRedirectCallback();
      set({
        status: "authenticated",
        user: mapOidcUser(user),
        accessToken: user.access_token,
      });
    } catch (error) {
      set({ status: "anonymous", user: null, accessToken: null });
      throw error;
    }
  },
  async restoreSession() {
    set({ status: "loading" });
    try {
      const user = await oidcManager.getUser();
      if (!user || user.expired) {
        set({ status: "anonymous", user: null, accessToken: null });
        return;
      }
      set({
        status: "authenticated",
        user: mapOidcUser(user),
        accessToken: user.access_token,
      });
    } catch {
      set({ status: "anonymous", user: null, accessToken: null });
    }
  },
  async signOut() {
    set({ status: "anonymous", user: null, accessToken: null });
    await oidcManager.signoutRedirect();
  },
}));
```

Create `frontend/src/components/auth/RequireAuth.tsx`:

```tsx
import type { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuthStore } from "@/stores/auth-store";

export function RequireAuth({ children }: PropsWithChildren) {
  const { status } = useAuthStore();
  const location = useLocation();

  if (status === "loading") {
    return <div className="p-8 text-sm text-slate-600">Restoring session...</div>;
  }

  if (status === "anonymous") {
    return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
```

Create `frontend/src/components/auth/RequireRole.tsx`:

```tsx
import type { PropsWithChildren } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/stores/auth-store";
import type { ArgusRole } from "@/lib/auth";

const roleRank: Record<ArgusRole, number> = {
  viewer: 10,
  operator: 20,
  admin: 30,
  superadmin: 40,
};

export function RequireRole({
  role,
  children,
}: PropsWithChildren<{ role: ArgusRole }>) {
  const user = useAuthStore((state) => state.user);

  if (!user || roleRank[user.role] < roleRank[role]) {
    return (
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Access denied</CardTitle>
          <CardDescription>You do not have access to this page.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          Ask an administrator for the required role if this is unexpected.
        </CardContent>
      </Card>
    );
  }

  return <>{children}</>;
}
```

Replace `frontend/src/pages/SignIn.tsx` with:

```tsx
import { useAuthStore } from "@/stores/auth-store";

export function SignInPage() {
  const signIn = useAuthStore((state) => state.signIn);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(43,117,255,0.18),_transparent_32%),radial-gradient(circle_at_85%_15%,_rgba(136,92,255,0.18),_transparent_28%),linear-gradient(180deg,#05070c_0%,#0b1018_46%,#121927_100%)] px-6 py-10 text-[#eef4ff]">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center justify-between gap-8 rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,20,31,0.94),rgba(8,11,18,0.9))] p-8 shadow-[0_36px_120px_-48px_rgba(31,111,255,0.55)] backdrop-blur-xl">
        <section className="max-w-2xl space-y-5">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[#b7c8e6]">
            Argus | The OmniSight Platform
          </p>
          <h1 className="text-5xl font-semibold tracking-[0.01em] text-[#f7f9ff]">
            Vigilant intelligence, fleet-wide.
          </h1>
          <p className="text-lg text-[#a8b5cc]">
            Monitor cameras, manage configuration, and operate Argus from a premium command center built for continuous observation.
          </p>
        </section>
        <section className="w-full max-w-sm rounded-[1.75rem] border border-[#1f2d46] bg-[linear-gradient(180deg,rgba(10,15,24,0.98),rgba(19,26,40,0.96))] p-6 text-[#eef4ff] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
          <h2 className="text-2xl font-semibold text-[#f7f9ff]">Sign in</h2>
          <p className="mt-2 text-sm text-[#96a7c2]">
            Use your Argus identity provider account to continue.
          </p>
          <button
            className="mt-6 w-full rounded-full bg-[linear-gradient(135deg,#3b82f6_0%,#8b5cf6_100%)] px-4 py-3 text-sm font-medium text-white shadow-[0_18px_42px_-22px_rgba(92,111,255,0.95)] transition hover:brightness-110"
            onClick={() => void signIn()}
          >
            Sign in
          </button>
        </section>
      </div>
    </main>
  );
}
```

Create `frontend/src/pages/AuthCallback.tsx`:

```tsx
import { useEffect } from "react";
import { useRef } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "@/stores/auth-store";

export function AuthCallbackPage() {
  const completeSignIn = useAuthStore((state) => state.completeSignIn);
  const navigate = useNavigate();
  const hasHandledCallback = useRef(false);

  useEffect(() => {
    if (hasHandledCallback.current) {
      return;
    }

    hasHandledCallback.current = true;
    void completeSignIn().then(
      () => navigate("/dashboard", { replace: true }),
      () => navigate("/signin", { replace: true }),
    );
  }, [completeSignIn, navigate]);

  return <main className="p-8 text-sm text-slate-600">Completing sign-in...</main>;
}
```

- [ ] **Step 4: Run the auth tests to verify they pass**

Run:

```bash
cd frontend
corepack pnpm test -- src/components/auth/RequireAuth.test.tsx src/components/auth/RequireRole.test.tsx src/pages/SignIn.test.tsx
```

Expected: PASS with guards and the real sign-in entry point in place.

- [ ] **Step 5: Commit**

```bash
git add infra/keycloak/realm-export.json frontend/src/lib/auth.ts frontend/src/lib/config.ts frontend/src/stores/auth-store.ts frontend/src/components/auth frontend/src/pages/SignIn.tsx frontend/src/pages/AuthCallback.tsx
git commit -m "feat: add prompt 7 auth foundation"
```

### Task 3: Generate OpenAPI Types and Build Typed Query Hooks

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/api.generated.ts`
- Create: `frontend/src/hooks/use-sites.ts`
- Create: `frontend/src/hooks/use-cameras.ts`
- Create: `frontend/src/hooks/use-models.ts`
- Create: `frontend/src/test/query-test-utils.tsx`
- Create: `frontend/src/lib/api.test.ts`
- Test: `frontend/src/lib/api.test.ts`

- [ ] **Step 1: Write the failing typed API test**

Create `frontend/src/lib/api.test.ts`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { PropsWithChildren } from "react";

import { useSites } from "@/hooks/use-sites";
import { useAuthStore } from "@/stores/auth-store";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("typed API hooks", () => {
  test("useSites sends the bearer token from the auth store", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: "11111111-1111-1111-1111-111111111111",
            tenant_id: "22222222-2222-2222-2222-222222222222",
            name: "HQ",
            description: "Main site",
            tz: "Europe/Zurich",
            geo_point: null,
            created_at: "2026-04-18T10:00:00Z",
          },
        ]),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    useAuthStore.setState({
      status: "authenticated",
      accessToken: "test-token",
      user: {
        sub: "admin-1",
        email: "admin@argus.local",
        role: "admin",
        realm: "argus-dev",
        tenantId: "tenant-1",
        isSuperadmin: false,
      },
    });

    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useSites(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/sites"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
        }),
      }),
    );
  });
});
```

- [ ] **Step 2: Run the API test to verify it fails**

Run: `corepack pnpm test -- src/lib/api.test.ts`

Expected: FAIL because the typed client and hooks do not exist yet.

- [ ] **Step 3: Generate API types and implement the client/hooks**

Add scripts to `frontend/package.json`:

```json
{
  "scripts": {
    "generate:api": "openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/api.generated.ts",
    "test:e2e": "playwright test"
  }
}
```

Run:

```bash
cd frontend
corepack pnpm generate:api
```

Replace `frontend/src/lib/api.ts` with:

```ts
import createClient from "openapi-fetch";

import type { paths } from "@/lib/api.generated";
import { frontendConfig } from "@/lib/config";
import { useAuthStore } from "@/stores/auth-store";

export const apiClient = createClient<paths>({
  baseUrl: frontendConfig.apiBaseUrl,
  fetch: async (input, init) => {
    const accessToken = useAuthStore.getState().accessToken;
    const headers = new Headers(init?.headers);
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
    return fetch(input, { ...init, headers });
  },
});
```

Create `frontend/src/hooks/use-sites.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api";

export function useSites() {
  return useQuery({
    queryKey: ["sites"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/sites");
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function useCreateSite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      description: string | null;
      tz: string;
      geo_point: { lat: number; lon: number } | null;
    }) => {
      const { data, error } = await apiClient.POST("/api/v1/sites", {
        body: payload,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sites"] });
    },
  });
}
```

Create `frontend/src/hooks/use-cameras.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api";

export function useCameras(siteId?: string) {
  return useQuery({
    queryKey: ["cameras", siteId ?? "all"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/cameras", {
        params: { query: siteId ? { site_id: siteId } : {} },
      });
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function useCreateCamera() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data, error } = await apiClient.POST("/api/v1/cameras", {
        body: payload,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
    },
  });
}
```

Create `frontend/src/hooks/use-models.ts`:

```ts
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api";

export function useModels() {
  return useQuery({
    queryKey: ["models"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/models");
      if (error) throw error;
      return data ?? [];
    },
  });
}
```

Create `frontend/src/test/query-test-utils.tsx`:

```tsx
import type { PropsWithChildren } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function createTestQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}
```

- [ ] **Step 4: Run the API test to verify it passes**

Run: `corepack pnpm test -- src/lib/api.test.ts`

Expected: PASS with typed hooks using the auth token automatically.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/src/lib/api.ts frontend/src/lib/api.generated.ts frontend/src/hooks frontend/src/test/query-test-utils.tsx frontend/src/lib/api.test.ts
git commit -m "feat: add prompt 7 typed API client and query hooks"
```

### Task 4: Build the Hybrid Command-Center Shell, Argus Visual System, and Secondary Admin Navigation

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/TopNav.tsx`
- Create: `frontend/src/components/layout/UserMenu.tsx`
- Create: `frontend/src/components/layout/TenantSwitcher.tsx`
- Create: `frontend/src/components/layout/AppShell.test.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: Write the failing shell test**

Create `frontend/src/components/layout/AppShell.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { AppShell } from "@/components/layout/AppShell";
import { useAuthStore } from "@/stores/auth-store";

describe("AppShell", () => {
  test("renders the fixed top nav and admin secondary links", () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "token",
      user: {
        sub: "admin-1",
        email: "admin@argus.local",
        role: "admin",
        realm: "argus-dev",
        tenantId: "tenant-1",
        isSuperadmin: false,
      },
    });

    render(
      <MemoryRouter>
        <AppShell>
          <div>Page body</div>
        </AppShell>
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "History" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Incidents" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sites" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cameras" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the shell test to verify it fails**

Run: `corepack pnpm test -- src/components/layout/AppShell.test.tsx`

Expected: FAIL because the shell and nav components do not exist yet.

- [ ] **Step 3: Implement the shell, UI primitives, and routed authenticated frame**

Create `frontend/src/components/ui/button.tsx`:

```tsx
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Button({
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
      <button
      className={cn(
        "inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,#3b82f6_0%,#8b5cf6_100%)] px-4 py-2 text-sm font-medium text-white shadow-[0_14px_32px_-18px_rgba(98,102,255,0.95)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
```

Create `frontend/src/components/ui/input.tsx`:

```tsx
import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
      <input
      className={cn(
        "w-full rounded-2xl border border-[#233049] bg-[#09101a] px-4 py-3 text-sm text-[#eef4ff] outline-none ring-0 placeholder:text-[#61718c] focus:border-[#4d7bff]",
        className,
      )}
      {...props}
    />
  );
}
```

Create `frontend/src/components/ui/badge.tsx`:

```tsx
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
      <span
      className={cn(
        "inline-flex items-center rounded-full border border-[#233049] bg-[#0b1220] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[#a9b7cf]",
        className,
      )}
      {...props}
    />
  );
}
```

Create `frontend/src/components/layout/TopNav.tsx`:

```tsx
import { NavLink } from "react-router-dom";

const primaryNav = ["Dashboard", "Live", "History", "Incidents", "Settings"] as const;

export function TopNav() {
  return (
    <nav className="flex flex-wrap items-center gap-2">
      {primaryNav.map((item) => {
        const to = item === "Dashboard" ? "/dashboard" : `/${item.toLowerCase()}`;
        return (
          <NavLink
            key={item}
            to={to}
            className={({ isActive }) =>
              isActive
                ? "rounded-full bg-[linear-gradient(135deg,#2563eb_0%,#8b5cf6_100%)] px-4 py-2 text-sm font-medium text-white shadow-[0_12px_28px_-16px_rgba(95,105,255,0.95)]"
                : "rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-[#a9b7cf]"
            }
          >
            {item}
          </NavLink>
        );
      })}
    </nav>
  );
}
```

Create `frontend/src/components/layout/UserMenu.tsx`:

```tsx
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";

export function UserMenu() {
  const user = useAuthStore((state) => state.user);
  const signOut = useAuthStore((state) => state.signOut);

  return (
    <div className="flex items-center gap-3 rounded-full border border-white/10 bg-white/6 px-3 py-2 backdrop-blur">
      <div className="text-right">
        <div className="text-sm font-medium text-[#eef4ff]">{user?.email ?? "Unknown user"}</div>
        <div className="text-xs uppercase tracking-[0.18em] text-[#8ea4c7]">{user?.role ?? "anonymous"}</div>
      </div>
      <Button className="bg-white/8 text-[#eef4ff] ring-1 ring-white/12 hover:bg-white/12" onClick={() => void signOut()}>
        Logout
      </Button>
    </div>
  );
}
```

Create `frontend/src/components/layout/TenantSwitcher.tsx`:

```tsx
import { useAuthStore } from "@/stores/auth-store";

export function TenantSwitcher() {
  const user = useAuthStore((state) => state.user);

  if (!user?.isSuperadmin) {
    return null;
  }

  return (
    <div className="rounded-full border border-[#334869] bg-[#121b2c] px-4 py-2 text-sm text-[#c9d6eb]">
      Tenant switcher reserved for platform-admin users
    </div>
  );
}
```

Create `frontend/src/components/layout/AppShell.tsx`:

```tsx
import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";

import { TopNav } from "@/components/layout/TopNav";
import { TenantSwitcher } from "@/components/layout/TenantSwitcher";
import { UserMenu } from "@/components/layout/UserMenu";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <main className="min-h-screen px-6 py-8 text-[#eef4ff] sm:px-10 lg:px-16">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col gap-6">
        <header className="rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(16,21,33,0.94),rgba(10,13,22,0.9))] px-6 py-6 shadow-[0_28px_90px_-46px_rgba(30,112,255,0.42)] backdrop-blur-xl">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[#aab9d2]">
                Argus | The OmniSight Platform
              </p>
              <TopNav />
            </div>
            <div className="flex flex-wrap items-center justify-end gap-3">
              <TenantSwitcher />
              <UserMenu />
            </div>
          </div>
        </header>
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
          <section>{children}</section>
          <aside className="rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.96),rgba(8,11,18,0.92))] p-5 backdrop-blur-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[#8ea4c7]">
              Management
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <NavLink className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-[#d8e2f4]" to="/sites">
                Sites
              </NavLink>
              <NavLink className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-[#d8e2f4]" to="/cameras">
                Cameras
              </NavLink>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
```

Replace `frontend/src/pages/Dashboard.tsx` with:

```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function DashboardPage() {
  return (
    <Card className="border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.94),rgba(8,11,18,0.9))] text-[#eef4ff]">
      <CardHeader>
        <CardTitle>Dashboard</CardTitle>
        <CardDescription className="text-[#96a7c2]">Prompt 8 will turn this into the live fleet grid.</CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-[#b5c2d8]">
        Frontend foundation is now responsible for routing, auth, and shell readiness.
      </CardContent>
    </Card>
  );
}
```

Replace `frontend/src/pages/History.tsx` with:

```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function HistoryPage() {
  return (
    <Card className="border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.94),rgba(8,11,18,0.9))] text-[#eef4ff]">
      <CardHeader>
        <CardTitle>History</CardTitle>
        <CardDescription className="text-[#96a7c2]">Prompt 9 will add range queries, charts, and exports here.</CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-[#b5c2d8]">History foundation route is ready.</CardContent>
    </Card>
  );
}
```

Replace `frontend/src/pages/Incidents.tsx` with:

```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function IncidentsPage() {
  return (
    <Card className="border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.94),rgba(8,11,18,0.9))] text-[#eef4ff]">
      <CardHeader>
        <CardTitle>Incidents</CardTitle>
        <CardDescription className="text-[#96a7c2]">Prompt 9 will add incident lists and snapshots here.</CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-[#b5c2d8]">Incidents foundation route is ready.</CardContent>
    </Card>
  );
}
```

Replace `frontend/src/pages/Settings.tsx` with:

```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function SettingsPage() {
  return (
    <Card className="border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.94),rgba(8,11,18,0.9))] text-[#eef4ff]">
      <CardHeader>
        <CardTitle>Settings</CardTitle>
        <CardDescription className="text-[#96a7c2]">Use the management rail to reach Sites and Cameras.</CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-[#b5c2d8]">
        Settings stays in the fixed top nav while management routes remain secondary.
      </CardContent>
    </Card>
  );
}
```

Update `frontend/src/app/router.tsx` to wrap authenticated routes:

```tsx
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";

import { AppProviders } from "@/app/providers";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { AuthCallbackPage } from "@/pages/AuthCallback";
import { CamerasPage } from "@/pages/Cameras";
import { DashboardPage } from "@/pages/Dashboard";
import { HistoryPage } from "@/pages/History";
import { IncidentsPage } from "@/pages/Incidents";
import { SettingsPage } from "@/pages/Settings";
import { SignInPage } from "@/pages/SignIn";
import { SitesPage } from "@/pages/Sites";

function ShellLayout() {
  return (
    <RequireAuth>
      <AppShell>
        <Outlet />
      </AppShell>
    </RequireAuth>
  );
}

export const router = createBrowserRouter([
  {
    path: "/signin",
    element: (
      <AppProviders>
        <SignInPage />
      </AppProviders>
    ),
  },
  {
    path: "/auth/callback",
    element: (
      <AppProviders>
        <AuthCallbackPage />
      </AppProviders>
    ),
  },
  {
    path: "/",
    element: (
      <AppProviders>
        <ShellLayout />
      </AppProviders>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/live", element: <DashboardPage /> },
      { path: "/history", element: <HistoryPage /> },
      { path: "/incidents", element: <IncidentsPage /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "/sites", element: <SitesPage /> },
      { path: "/cameras", element: <CamerasPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/signin" replace /> },
]);
```

Update `frontend/src/index.css` to establish the Argus dark-first visual system:

```css
@import "tailwindcss";

:root {
  color: #eef4ff;
  background:
    radial-gradient(circle at top, rgba(42, 108, 255, 0.18), transparent 34%),
    radial-gradient(circle at 84% 14%, rgba(132, 88, 255, 0.16), transparent 28%),
    linear-gradient(180deg, #05070c 0%, #0a1018 48%, #121927 100%);
  font-family: "Avenir Next", "Suisse Intl", "Poppins", "Segoe UI", sans-serif;
  line-height: 1.5;
  font-weight: 400;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  min-height: 100vh;
  background: transparent;
}
```

- [ ] **Step 4: Run the shell test to verify it passes**

Run: `corepack pnpm test -- src/components/layout/AppShell.test.tsx`

Expected: PASS with fixed top nav plus admin secondary navigation present.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/index.css frontend/src/app/router.tsx frontend/src/components/ui frontend/src/components/layout frontend/src/pages/Dashboard.tsx frontend/src/pages/History.tsx frontend/src/pages/Incidents.tsx frontend/src/pages/Settings.tsx
git commit -m "feat: add prompt 7 command center shell"
```

### Task 5: Implement Sites Page CRUD as the First Vertical Slice

**Files:**
- Modify: `frontend/src/pages/Sites.tsx`
- Create: `frontend/src/components/ui/dialog.tsx`
- Create: `frontend/src/components/ui/table.tsx`
- Create: `frontend/src/components/sites/SiteDialog.tsx`
- Create: `frontend/src/pages/Sites.test.tsx`
- Test: `frontend/src/pages/Sites.test.tsx`

- [ ] **Step 1: Write the failing Sites page test**

Create `frontend/src/pages/Sites.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { createQueryClient } from "@/app/query-client";
import { SitesPage } from "@/pages/Sites";
import { useAuthStore } from "@/stores/auth-store";

describe("SitesPage", () => {
  test("loads sites and creates a new site through the dialog", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([]),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "11111111-1111-1111-1111-111111111111",
            tenant_id: "22222222-2222-2222-2222-222222222222",
            name: "HQ",
            description: "Main site",
            tz: "Europe/Zurich",
            geo_point: null,
            created_at: "2026-04-18T10:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: "11111111-1111-1111-1111-111111111111",
              tenant_id: "22222222-2222-2222-2222-222222222222",
              name: "HQ",
              description: "Main site",
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-18T10:00:00Z",
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    useAuthStore.setState({
      status: "authenticated",
      accessToken: "token",
      user: {
        sub: "admin-1",
        email: "admin@argus.local",
        role: "admin",
        realm: "argus-dev",
        tenantId: "tenant-1",
        isSuperadmin: false,
      },
    });

    render(
      <QueryClientProvider client={createQueryClient()}>
        <SitesPage />
      </QueryClientProvider>,
    );

    await userEvent.click(await screen.findByRole("button", { name: /add site/i }));
    await userEvent.type(screen.getByLabelText(/site name/i), "HQ");
    await userEvent.type(screen.getByLabelText(/time zone/i), "Europe/Zurich");
    await userEvent.click(screen.getByRole("button", { name: /save site/i }));

    await waitFor(() => expect(screen.getByText("HQ")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
```

- [ ] **Step 2: Run the Sites test to verify it fails**

Run: `corepack pnpm test -- src/pages/Sites.test.tsx`

Expected: FAIL because the Sites page still contains placeholder content.

- [ ] **Step 3: Implement local dialog/table primitives and the Sites page**

Create `frontend/src/components/ui/dialog.tsx`:

```tsx
import type { HTMLAttributes, PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

export function Dialog({
  open,
  title,
  description,
  children,
}: PropsWithChildren<{
  open: boolean;
  title: string;
  description?: string;
}>) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/30 p-6">
      <div className="w-full max-w-3xl rounded-[1.75rem] border border-white/70 bg-white p-6 shadow-[0_32px_100px_-48px_rgba(15,23,42,0.65)]">
        <div className="mb-4">
          <h2 className="text-2xl font-semibold text-slate-950">{title}</h2>
          {description ? <p className="mt-1 text-sm text-slate-600">{description}</p> : null}
        </div>
        {children}
      </div>
    </div>
  );
}

export function DialogFooter({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mt-6 flex justify-end gap-3", className)} {...props} />;
}
```

Create `frontend/src/components/ui/table.tsx`:

```tsx
import type { HTMLAttributes, TableHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Table({ className, ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return <table className={cn("min-w-full border-separate border-spacing-0", className)} {...props} />;
}

export function THead(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} />;
}

export function TBody(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} />;
}

export function TR({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("border-b border-slate-100", className)} {...props} />;
}

export function TH({ className, ...props }: HTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-500", className)}
      {...props}
    />
  );
}

export function TD({ className, ...props }: HTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-4 text-sm text-slate-700", className)} {...props} />;
}
```

Create `frontend/src/components/sites/SiteDialog.tsx`:

```tsx
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export function SiteDialog({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    description: string | null;
    tz: string;
    geo_point: null;
  }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tz, setTz] = useState("UTC");

  return (
    <Dialog open={open} title="Create site" description="Add a new site to the Argus fleet.">
      <div className="grid gap-4">
        <label className="grid gap-2 text-sm text-slate-700">
          <span>Site name</span>
          <Input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="grid gap-2 text-sm text-slate-700">
          <span>Description</span>
          <Input value={description} onChange={(event) => setDescription(event.target.value)} />
        </label>
        <label className="grid gap-2 text-sm text-slate-700">
          <span>Time zone</span>
          <Input value={tz} onChange={(event) => setTz(event.target.value)} />
        </label>
      </div>
      <DialogFooter>
        <Button className="bg-white text-slate-950 ring-1 ring-black/10 hover:bg-slate-100" onClick={onClose}>
          Cancel
        </Button>
        <Button
          onClick={() =>
            void onSubmit({
              name,
              description: description || null,
              tz,
              geo_point: null,
            })
          }
        >
          Save site
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
```

Replace `frontend/src/pages/Sites.tsx` with:

```tsx
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { SiteDialog } from "@/components/sites/SiteDialog";
import { useCreateSite, useSites } from "@/hooks/use-sites";
import { RequireRole } from "@/components/auth/RequireRole";

export function SitesPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data: sites = [], isLoading } = useSites();
  const createSite = useCreateSite();

  return (
    <RequireRole role="admin">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Sites</CardTitle>
            <CardDescription>Manage Argus deployment locations and their fleet context.</CardDescription>
          </div>
          <Button onClick={() => setDialogOpen(true)}>Add site</Button>
        </CardHeader>
        <CardContent>
          <Table>
            <THead>
              <TR>
                <TH>Name</TH>
                <TH>Time zone</TH>
                <TH>Description</TH>
              </TR>
            </THead>
            <TBody>
              {isLoading ? (
                <TR>
                  <TD colSpan={3}>Loading sites...</TD>
                </TR>
              ) : sites.length === 0 ? (
                <TR>
                  <TD colSpan={3}>No sites yet.</TD>
                </TR>
              ) : (
                sites.map((site) => (
                  <TR key={site.id}>
                    <TD>{site.name}</TD>
                    <TD>{site.tz}</TD>
                    <TD>{site.description ?? "—"}</TD>
                  </TR>
                ))
              )}
            </TBody>
          </Table>
        </CardContent>
      </Card>
      <SiteDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={async (payload) => {
          await createSite.mutateAsync(payload);
          setDialogOpen(false);
        }}
      />
    </RequireRole>
  );
}
```

- [ ] **Step 4: Run the Sites test to verify it passes**

Run: `corepack pnpm test -- src/pages/Sites.test.tsx`

Expected: PASS with the page loading and creating a site through the dialog.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/dialog.tsx frontend/src/components/ui/table.tsx frontend/src/components/sites/SiteDialog.tsx frontend/src/pages/Sites.tsx frontend/src/pages/Sites.test.tsx
git commit -m "feat: add prompt 7 sites management page"
```

### Task 6: Implement the Cameras Page, the Guided Wizard Shell, and Delivery-Profile Controls

**Files:**
- Modify: `frontend/src/pages/Cameras.tsx`
- Create: `frontend/src/components/ui/select.tsx`
- Create: `frontend/src/components/cameras/CameraWizard.tsx`
- Create: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Write the failing camera wizard test**

Create `frontend/src/components/cameras/CameraWizard.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import { createQueryClient } from "@/app/query-client";
import { CameraWizard } from "@/components/cameras/CameraWizard";

describe("CameraWizard", () => {
  test("moves through the first three steps and blocks progress when required fields are empty", async () => {
    render(
      <QueryClientProvider client={createQueryClient()}>
        <CameraWizard
          sites={[{ id: "site-1", name: "HQ" }]}
          models={[
            { id: "model-1", name: "Argus YOLO", version: "1.0.0" },
            { id: "model-2", name: "Argus PPE", version: "1.0.0" },
          ]}
          onSubmit={async () => undefined}
        />
      </QueryClientProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText(/camera name is required/i)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await userEvent.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await userEvent.selectOptions(screen.getByLabelText(/processing mode/i), "central");
    await userEvent.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await userEvent.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText(/models & tracking/i)).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    await userEvent.selectOptions(screen.getByLabelText(/tracker type/i), "botsort");
    await userEvent.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText(/privacy, processing & delivery/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/browser delivery profile/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the camera wizard test to verify it fails**

Run: `corepack pnpm test -- src/components/cameras/CameraWizard.test.tsx`

Expected: FAIL because the guided wizard and select input do not exist yet.

- [ ] **Step 3: Implement the wizard scaffold and Cameras page**

Create `frontend/src/components/ui/select.tsx`:

```tsx
import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Select({
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
      <select
      className={cn(
        "w-full rounded-2xl border border-[#233049] bg-[#09101a] px-4 py-3 text-sm text-[#eef4ff] outline-none focus:border-[#4d7bff]",
        className,
      )}
      {...props}
    />
  );
}
```

Create `frontend/src/components/cameras/CameraWizard.tsx`:

```tsx
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

type SiteOption = { id: string; name: string };
type ModelOption = { id: string; name: string; version: string };

type WizardData = {
  name: string;
  siteId: string;
  processingMode: "central" | "edge" | "hybrid";
  rtspUrl: string;
  primaryModelId: string;
  secondaryModelId: string;
  trackerType: "botsort" | "bytetrack" | "ocsort";
  blurFaces: boolean;
  blurPlates: boolean;
  method: "gaussian" | "pixelate";
  strength: number;
  frameSkip: number;
  fpsCap: number;
  browserDeliveryProfile: "native" | "1080p15" | "720p10" | "540p5";
};

const steps = ["Identity", "Models & Tracking", "Privacy, Processing & Delivery", "Calibration", "Review"] as const;

export function CameraWizard({
  sites,
  models,
  onSubmit,
}: {
  sites: SiteOption[];
  models: ModelOption[];
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<WizardData>({
    name: "",
    siteId: "",
    processingMode: "central",
    rtspUrl: "",
    primaryModelId: "",
    secondaryModelId: "",
    trackerType: "botsort",
    blurFaces: true,
    blurPlates: true,
    method: "gaussian",
    strength: 7,
    frameSkip: 1,
    fpsCap: 25,
    browserDeliveryProfile: "720p10",
  });

  const stepTitle = steps[stepIndex];

  const contextPanel = useMemo(() => {
    if (stepTitle === "Calibration") {
      return "Homography editor appears here.";
    }
    return "Configuration guidance and summary appear here.";
  }, [stepTitle]);

  function validateCurrentStep() {
    if (stepTitle === "Identity") {
      if (!data.name.trim()) return "Camera name is required.";
      if (!data.siteId) return "Site is required.";
      if (!data.rtspUrl.trim()) return "RTSP URL is required.";
    }
    if (stepTitle === "Models & Tracking") {
      if (!data.primaryModelId) return "Primary model is required.";
      if (!data.trackerType) return "Tracker type is required.";
    }
    if (stepTitle === "Privacy, Processing & Delivery" && !data.browserDeliveryProfile) {
      return "Browser delivery profile is required.";
    }
    return null;
  }

  async function handleNext() {
    const nextError = validateCurrentStep();
    if (nextError) {
      setError(nextError);
      return;
    }
    setError(null);
    if (stepIndex === steps.length - 1) {
      await onSubmit(data);
      return;
    }
    setStepIndex((value) => value + 1);
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <Card>
        <CardHeader>
          <CardTitle>{stepTitle}</CardTitle>
          <CardDescription>Step {stepIndex + 1} of {steps.length}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {stepTitle === "Identity" ? (
            <>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>Camera name</span>
                <Input value={data.name} onChange={(event) => setData((current) => ({ ...current, name: event.target.value }))} />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>Site</span>
                <Select value={data.siteId} onChange={(event) => setData((current) => ({ ...current, siteId: event.target.value }))}>
                  <option value="">Select a site</option>
                  {sites.map((site) => (
                    <option key={site.id} value={site.id}>{site.name}</option>
                  ))}
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>Processing mode</span>
                <Select value={data.processingMode} onChange={(event) => setData((current) => ({ ...current, processingMode: event.target.value as WizardData["processingMode"] }))}>
                  <option value="central">central</option>
                  <option value="edge">edge</option>
                  <option value="hybrid">hybrid</option>
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>RTSP URL</span>
                <Input value={data.rtspUrl} onChange={(event) => setData((current) => ({ ...current, rtspUrl: event.target.value }))} />
              </label>
            </>
          ) : null}
          {stepTitle === "Models & Tracking" ? (
            <>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>Primary model</span>
                <Select value={data.primaryModelId} onChange={(event) => setData((current) => ({ ...current, primaryModelId: event.target.value }))}>
                  <option value="">Select a model</option>
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>{model.name} {model.version}</option>
                  ))}
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>Secondary model</span>
                <Select value={data.secondaryModelId} onChange={(event) => setData((current) => ({ ...current, secondaryModelId: event.target.value }))}>
                  <option value="">None</option>
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>{model.name} {model.version}</option>
                  ))}
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>Tracker type</span>
                <Select value={data.trackerType} onChange={(event) => setData((current) => ({ ...current, trackerType: event.target.value as WizardData["trackerType"] }))}>
                  <option value="botsort">botsort</option>
                  <option value="bytetrack">bytetrack</option>
                  <option value="ocsort">ocsort</option>
                </Select>
              </label>
            </>
          ) : null}
          {stepTitle === "Privacy, Processing & Delivery" ? (
            <>
              <label className="flex items-center gap-3 text-sm text-slate-700">
                <input type="checkbox" checked={data.blurFaces} onChange={(event) => setData((current) => ({ ...current, blurFaces: event.target.checked }))} />
                <span>Blur faces</span>
              </label>
              <label className="flex items-center gap-3 text-sm text-slate-700">
                <input type="checkbox" checked={data.blurPlates} onChange={(event) => setData((current) => ({ ...current, blurPlates: event.target.checked }))} />
                <span>Blur plates</span>
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>Method</span>
                <Select value={data.method} onChange={(event) => setData((current) => ({ ...current, method: event.target.value as WizardData["method"] }))}>
                  <option value="gaussian">gaussian</option>
                  <option value="pixelate">pixelate</option>
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                <span>Browser delivery profile</span>
                <Select value={data.browserDeliveryProfile} onChange={(event) => setData((current) => ({ ...current, browserDeliveryProfile: event.target.value as WizardData["browserDeliveryProfile"] }))}>
                  <option value="native">native</option>
                  <option value="1080p15">1080p15</option>
                  <option value="720p10">720p10</option>
                  <option value="540p5">540p5</option>
                </Select>
              </label>
              <p className="text-sm text-slate-500">
                Analytics ingest stays native. Non-native browser delivery profiles may use an optional preview/transcode path to reduce bandwidth.
              </p>
            </>
          ) : null}
          {error ? <p className="text-sm font-medium text-rose-600">{error}</p> : null}
          <div className="flex justify-between gap-3 pt-4">
            <Button
              className="bg-white text-slate-950 ring-1 ring-black/10 hover:bg-slate-100"
              onClick={() => setStepIndex((value) => Math.max(0, value - 1))}
              disabled={stepIndex === 0}
            >
              Back
            </Button>
            <Button onClick={() => void handleNext()}>
              {stepIndex === steps.length - 1 ? "Save camera" : "Next"}
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card className="bg-slate-950 text-white">
        <CardHeader>
          <CardTitle className="text-white">Step context</CardTitle>
          <CardDescription className="text-slate-300">
            Guided setup keeps camera configuration manageable, bandwidth-aware, and ready for Prompt 8.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-200">{contextPanel}</CardContent>
      </Card>
    </div>
  );
}
```

Replace `frontend/src/pages/Cameras.tsx` with:

```tsx
import { useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { CameraWizard } from "@/components/cameras/CameraWizard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { useCameras, useCreateCamera } from "@/hooks/use-cameras";
import { useModels } from "@/hooks/use-models";
import { useSites } from "@/hooks/use-sites";

export function CamerasPage() {
  const [wizardOpen, setWizardOpen] = useState(false);
  const { data: cameras = [] } = useCameras();
  const { data: sites = [] } = useSites();
  const { data: models = [] } = useModels();
  const createCamera = useCreateCamera();

  return (
    <RequireRole role="admin">
      <div className="space-y-6">
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div>
              <CardTitle>Cameras</CardTitle>
              <CardDescription>Manage camera ingest, privacy, browser delivery profiles, and model configuration.</CardDescription>
            </div>
            <Button onClick={() => setWizardOpen(true)}>Add camera</Button>
          </CardHeader>
          <CardContent>
            <Table>
              <THead>
                <TR>
                  <TH>Name</TH>
                  <TH>Mode</TH>
                  <TH>Tracker</TH>
                </TR>
              </THead>
              <TBody>
                {cameras.length === 0 ? (
                  <TR>
                    <TD colSpan={3}>No cameras yet.</TD>
                  </TR>
                ) : (
                  cameras.map((camera) => (
                    <TR key={camera.id}>
                      <TD>{camera.name}</TD>
                      <TD>{camera.processing_mode}</TD>
                      <TD>{camera.tracker_type}</TD>
                    </TR>
                  ))
                )}
              </TBody>
            </Table>
          </CardContent>
        </Card>
        {wizardOpen ? (
          <CameraWizard
            sites={sites.map((site) => ({ id: site.id, name: site.name }))}
            models={models.map((model) => ({
              id: model.id,
              name: model.name,
              version: model.version,
            }))}
            onSubmit={async (payload) => {
              await createCamera.mutateAsync(payload);
              setWizardOpen(false);
            }}
          />
        ) : null}
      </div>
    </RequireRole>
  );
}
```

- [ ] **Step 4: Run the camera wizard test to verify it passes**

Run: `corepack pnpm test -- src/components/cameras/CameraWizard.test.tsx`

Expected: PASS with step gating working through the first three steps.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/select.tsx frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/pages/Cameras.tsx
git commit -m "feat: add prompt 7 camera wizard foundation"
```

### Task 7: Add Homography Editing, Review Step, and Masked RTSP Edit Behavior

**Files:**
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Create: `frontend/src/components/cameras/HomographyEditor.tsx`
- Create: `frontend/src/components/cameras/CameraStepSummary.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Extend the failing camera wizard test for calibration and review**

Append to `frontend/src/components/cameras/CameraWizard.test.tsx`:

```tsx
test("requires four source points, four destination points, and a reference distance before save", async () => {
  const onSubmit = vi.fn().mockResolvedValue(undefined);

  render(
    <QueryClientProvider client={createQueryClient()}>
      <CameraWizard
        sites={[{ id: "site-1", name: "HQ" }]}
        models={[{ id: "model-1", name: "Argus YOLO", version: "1.0.0" }]}
        onSubmit={onSubmit}
      />
    </QueryClientProvider>,
  );

  await userEvent.type(screen.getByLabelText(/camera name/i), "Dock Camera");
  await userEvent.selectOptions(screen.getByLabelText(/site/i), "site-1");
  await userEvent.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
  await userEvent.click(screen.getByRole("button", { name: /next/i }));
  await userEvent.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
  await userEvent.click(screen.getByRole("button", { name: /next/i }));
  await userEvent.click(screen.getByRole("button", { name: /next/i }));
  await userEvent.click(screen.getByRole("button", { name: /next/i }));

  expect(screen.getByText(/4 source points are required/i)).toBeInTheDocument();
  expect(onSubmit).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Run the camera wizard test to verify it fails**

Run: `corepack pnpm test -- src/components/cameras/CameraWizard.test.tsx`

Expected: FAIL because calibration and review validation are not implemented yet.

- [ ] **Step 3: Implement the HomographyEditor, review step, and edit masking rules**

Create `frontend/src/components/cameras/HomographyEditor.tsx`:

```tsx
import { Button } from "@/components/ui/button";

type Point = [number, number];

export function HomographyEditor({
  src,
  dst,
  refDistanceM,
  onChange,
}: {
  src: Point[];
  dst: Point[];
  refDistanceM: number;
  onChange: (value: { src: Point[]; dst: Point[]; refDistanceM: number }) => void;
}) {
  return (
    <div className="space-y-4 rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 p-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Frame snapshot placeholder
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Button
          className="bg-white text-slate-950 ring-1 ring-black/10 hover:bg-slate-100"
          onClick={() =>
            onChange({
              src: [...src, [src.length * 10, src.length * 10]],
              dst,
              refDistanceM,
            })
          }
        >
          Add source point
        </Button>
        <Button
          className="bg-white text-slate-950 ring-1 ring-black/10 hover:bg-slate-100"
          onClick={() =>
            onChange({
              src,
              dst: [...dst, [dst.length * 5, dst.length * 5]],
              refDistanceM,
            })
          }
        >
          Add destination point
        </Button>
        <label className="grid gap-2 text-sm text-slate-700">
          <span>Reference distance (m)</span>
          <input
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3"
            type="number"
            min={0}
            step="0.1"
            value={refDistanceM}
            onChange={(event) =>
              onChange({
                src,
                dst,
                refDistanceM: Number(event.target.value),
              })
            }
          />
        </label>
      </div>
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
        Source points: {src.length} / 4 | Destination points: {dst.length} / 4
      </p>
    </div>
  );
}
```

Create `frontend/src/components/cameras/CameraStepSummary.tsx`:

```tsx
export function CameraStepSummary({
  data,
}: {
  data: {
    name: string;
    processingMode: string;
    trackerType: string;
    blurFaces: boolean;
    blurPlates: boolean;
    browserDeliveryProfile: string;
    rtspUrlMasked: string;
  };
}) {
  return (
    <div className="space-y-3 rounded-[1.5rem] border border-slate-200 bg-white p-4 text-sm text-slate-700">
      <div><strong>Name:</strong> {data.name}</div>
      <div><strong>Mode:</strong> {data.processingMode}</div>
      <div><strong>Tracker:</strong> {data.trackerType}</div>
      <div><strong>Browser delivery:</strong> {data.browserDeliveryProfile}</div>
      <div><strong>Privacy:</strong> faces {String(data.blurFaces)}, plates {String(data.blurPlates)}</div>
      <div><strong>RTSP:</strong> {data.rtspUrlMasked}</div>
    </div>
  );
}
```

Update `frontend/src/components/cameras/CameraWizard.tsx`:

```tsx
import { CameraStepSummary } from "@/components/cameras/CameraStepSummary";
import { HomographyEditor } from "@/components/cameras/HomographyEditor";
```

Extend `WizardData`:

```tsx
homography: {
  src: [number, number][];
  dst: [number, number][];
  refDistanceM: number;
};
```

Initialize it:

```tsx
homography: { src: [], dst: [], refDistanceM: 0 },
```

Extend validation:

```tsx
if (stepTitle === "Calibration") {
  if (data.homography.src.length !== 4) return "4 source points are required.";
  if (data.homography.dst.length !== 4) return "4 destination points are required.";
  if (data.homography.refDistanceM <= 0) return "Reference distance is required.";
}
```

Render calibration step:

```tsx
{stepTitle === "Calibration" ? (
  <HomographyEditor
    src={data.homography.src}
    dst={data.homography.dst}
    refDistanceM={data.homography.refDistanceM}
    onChange={(homography) => setData((current) => ({ ...current, homography }))}
  />
) : null}
```

Render review step:

```tsx
{stepTitle === "Review" ? (
  <CameraStepSummary
    data={{
      name: data.name,
      processingMode: data.processingMode,
      trackerType: data.trackerType,
      blurFaces: data.blurFaces,
      blurPlates: data.blurPlates,
      browserDeliveryProfile: data.browserDeliveryProfile,
      rtspUrlMasked: data.rtspUrl ? "rtsp://***" : "not set",
    }}
  />
) : null}
```

Shape the submit payload:

```tsx
await onSubmit({
  site_id: data.siteId,
  name: data.name,
  rtsp_url: data.rtspUrl,
  processing_mode: data.processingMode,
  primary_model_id: data.primaryModelId,
  secondary_model_id: data.secondaryModelId || null,
  tracker_type: data.trackerType,
  active_classes: [],
  attribute_rules: [],
  zones: [],
  homography: {
    src: data.homography.src,
    dst: data.homography.dst,
    ref_distance_m: data.homography.refDistanceM,
  },
  privacy: {
    blur_faces: data.blurFaces,
    blur_plates: data.blurPlates,
    method: data.method,
    strength: data.strength,
  },
  browser_delivery: {
    default_profile: data.browserDeliveryProfile,
  },
  frame_skip: data.frameSkip,
  fps_cap: data.fpsCap,
});
```

For edit mode, define this rule in the component props and UI:

```tsx
rtspUrlPlaceholder?: string;
```

Render:

```tsx
<Input
  value={data.rtspUrl}
  placeholder={props.rtspUrlPlaceholder ?? "rtsp://camera.local/live"}
  onChange={(event) => setData((current) => ({ ...current, rtspUrl: event.target.value }))}
/>
```

Use `rtspUrlPlaceholder="rtsp://***"` when editing an existing camera and keep the field blank unless explicitly replaced.

- [ ] **Step 4: Run the camera wizard test to verify it passes**

Run: `corepack pnpm test -- src/components/cameras/CameraWizard.test.tsx`

Expected: PASS with calibration and review validation enforced before save.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/cameras/HomographyEditor.tsx frontend/src/components/cameras/CameraStepSummary.tsx frontend/src/components/cameras/CameraWizard.tsx frontend/src/pages/Cameras.tsx
git commit -m "feat: add prompt 7 camera calibration workflow"
```

### Task 8: Add Real-Auth Playwright Coverage and Final Verification Scripts

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/prompt7-auth-and-camera.spec.ts`
- Test: `frontend/e2e/prompt7-auth-and-camera.spec.ts`

- [ ] **Step 1: Write the failing Playwright E2E spec**

Create `frontend/e2e/prompt7-auth-and-camera.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test("real login creates a site and camera through the prompt 7 flows", async ({ page }) => {
  await page.goto("http://127.0.0.1:3000/signin");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/dashboard/);
  await page.getByRole("link", { name: "Sites" }).click();
  await page.getByRole("button", { name: "Add site" }).click();
  await page.getByLabel("Site name").fill("Prompt 7 Site");
  await page.getByLabel("Time zone").fill("Europe/Zurich");
  await page.getByRole("button", { name: "Save site" }).click();
  await expect(page.getByText("Prompt 7 Site")).toBeVisible();

  await page.getByRole("link", { name: "Cameras" }).click();
  await page.getByRole("button", { name: "Add camera" }).click();
  await page.getByLabel("Camera name").fill("Prompt 7 Camera");
  await page.getByLabel("Site").selectOption({ label: "Prompt 7 Site" });
  await page.getByLabel("RTSP URL").fill("rtsp://camera.local/live");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("Primary model").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("Browser delivery profile").selectOption("720p10");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Add source point" }).click();
  await page.getByRole("button", { name: "Add source point" }).click();
  await page.getByRole("button", { name: "Add source point" }).click();
  await page.getByRole("button", { name: "Add source point" }).click();
  await page.getByRole("button", { name: "Add destination point" }).click();
  await page.getByRole("button", { name: "Add destination point" }).click();
  await page.getByRole("button", { name: "Add destination point" }).click();
  await page.getByRole("button", { name: "Add destination point" }).click();
  await page.getByLabel("Reference distance (m)").fill("12.5");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Save camera" }).click();

  await expect(page.getByText("Prompt 7 Camera")).toBeVisible();
});
```

- [ ] **Step 2: Run the Playwright spec to verify it fails**

Run:

```bash
cd frontend
corepack pnpm exec playwright test e2e/prompt7-auth-and-camera.spec.ts
```

Expected: FAIL because the routed shell, role handling, and CRUD flows are not complete yet.

- [ ] **Step 3: Add Playwright config and final package scripts**

Update `frontend/package.json` scripts:

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

Run:

```bash
cd frontend
corepack pnpm exec playwright install chromium
```

Create `frontend/playwright.config.ts`:

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: "docker compose -f ../infra/docker-compose.dev.yml up -d --force-recreate keycloak backend",
      url: "http://127.0.0.1:8000/healthz",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "corepack pnpm dev --host 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
```

- [ ] **Step 4: Run the full Prompt 7 verification stack**

Run:

```bash
cd frontend
corepack pnpm test
corepack pnpm exec eslint .
corepack pnpm exec tsc -b
corepack pnpm exec playwright test e2e/prompt7-auth-and-camera.spec.ts
```

Expected:

- Vitest PASS
- ESLint PASS
- TypeScript build PASS
- Playwright PASS through real Keycloak login and site/camera creation

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/playwright.config.ts frontend/e2e/prompt7-auth-and-camera.spec.ts
git commit -m "test: add prompt 7 real-auth e2e coverage"
```

## Final Cross-Check Against the Spec

### Spec coverage

- Real Keycloak PKCE auth: Tasks 1-2
- Typed OpenAPI client and TanStack Query hooks: Task 3
- Hybrid command-center shell: Task 4
- Branded sign-in route: Task 2
- Secondary admin navigation for `Sites` and `Cameras`: Task 4
- Sites CRUD: Task 5
- Stepped split camera workflow: Tasks 6-7
- Homography editor and calibration: Task 7
- Masked RTSP edit behavior: Task 7
- Real Playwright login and CRUD flow: Task 8

No spec gaps found.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” markers remain in the task steps.
- Every code-changing step includes concrete file paths, commands, and code.

### Type consistency

- Auth roles use the same `viewer` / `operator` / `admin` / `superadmin` names throughout.
- Camera payload field names in the wizard match backend API contract names where they cross the wire.
- The primary shell navigation stays fixed to `Dashboard`, `Live`, `History`, `Incidents`, `Settings`, while `Sites` and `Cameras` remain secondary admin routes as required by the approved spec.
