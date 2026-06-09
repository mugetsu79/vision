import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/config", () => ({
  frontendConfig: {
    apiBaseUrl: "http://127.0.0.1:8000",
    oidcAuthority: "http://127.0.0.1:8080/realms/platform-admin",
    oidcClientId: "argus-frontend",
    oidcRedirectUri: "http://127.0.0.1:3000/auth/callback",
    oidcPostLogoutRedirectUri: "http://127.0.0.1:3000/signin",
  },
}));

vi.mock("@/lib/auth", () => ({
  mapOidcUser: vi.fn(),
  oidcManager: {
    getUser: vi.fn(),
    signinRedirect: vi.fn(),
    signinRedirectCallback: vi.fn(),
    signoutRedirect: vi.fn(),
  },
}));

import { createQueryClient } from "@/app/query-client";
import { UsersPage } from "@/pages/Users";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

const tenantA = {
  id: "00000000-0000-4000-8000-000000000101",
  name: "Acme",
  slug: "acme",
  created_at: "2026-06-09T12:00:00Z",
};

const tenantB = {
  id: "00000000-0000-4000-8000-000000000102",
  name: "Beta",
  slug: "beta",
  created_at: "2026-06-09T12:01:00Z",
};

const adminUser = {
  id: "00000000-0000-4000-8000-000000000201",
  tenant_id: tenantA.id,
  email: "admin@acme.example",
  first_name: "Acme",
  last_name: "Admin",
  oidc_sub: "kc-admin-1",
  role: "admin",
  enabled: true,
  created_at: "2026-06-09T12:00:00Z",
};

type MockManagedUser = typeof adminUser;

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function mockUsersApi() {
  let tenants = [tenantA];
  let users: MockManagedUser[] = [adminUser];

  return vi.spyOn(global, "fetch").mockImplementation(async (input) => {
    const request = input as Request;
    const url = new URL(request.url);

    if (url.pathname === "/api/v1/tenants" && request.method === "GET") {
      return jsonResponse(tenants);
    }

    if (url.pathname === "/api/v1/tenants" && request.method === "POST") {
      const payload = (await request.clone().json()) as Record<string, unknown>;
      const createdTenant = { ...tenantB, ...payload };
      tenants = [...tenants, createdTenant];
      return jsonResponse(createdTenant, 201);
    }

    if (url.pathname === "/api/v1/users" && request.method === "GET") {
      return jsonResponse(users);
    }

    if (url.pathname === "/api/v1/users" && request.method === "POST") {
      const payload = (await request.clone().json()) as Record<string, unknown>;
      const createdUser = {
        id: "00000000-0000-4000-8000-000000000202",
        tenant_id: String(payload.tenant_id),
        email: String(payload.email),
        first_name: String(payload.first_name),
        last_name: String(payload.last_name),
        oidc_sub: "kc-ops-1",
        role: String(payload.role),
        enabled: true,
        created_at: "2026-06-09T12:04:00Z",
      };
      users = [...users, createdUser];
      return jsonResponse(createdUser, 201);
    }

    if (
      url.pathname.startsWith("/api/v1/users/") &&
      url.pathname.endsWith("/reset-password") &&
      request.method === "POST"
    ) {
      return jsonResponse(users[1] ?? adminUser);
    }

    if (
      url.pathname.startsWith("/api/v1/users/") &&
      request.method === "PATCH"
    ) {
      const payload = (await request.clone().json()) as Record<string, unknown>;
      const userId = url.pathname.split("/").pop();
      users = users.map((row) =>
        row.id === userId ? { ...row, ...payload } : row,
      );
      return jsonResponse(users.find((row) => row.id === userId) ?? adminUser);
    }

    return Promise.resolve(new Response("Not found", { status: 404 }));
  });
}

function renderUsersPage() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <UsersPage />
    </QueryClientProvider>,
  );
}

describe("UsersPage", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "platform-token",
        user: {
          sub: "superadmin-1",
          email: "platform@vezor.local",
          role: "superadmin",
          realm: "platform-admin",
          tenantId: null,
          isSuperadmin: true,
        },
      });
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("superadmin creates tenants and tenant users without rendering passwords", async () => {
    const user = userEvent.setup();
    mockUsersApi();

    renderUsersPage();

    expect(await screen.findByTestId("users-workspace")).toBeInTheDocument();
    expect(await screen.findByText("admin@acme.example")).toBeInTheDocument();

    const tenantForm = screen.getByTestId("create-tenant-form");
    await user.type(within(tenantForm).getByLabelText("Tenant name"), "Beta");
    await user.type(within(tenantForm).getByLabelText("Tenant slug"), "beta");
    await user.click(within(tenantForm).getByRole("button", { name: /create tenant/i }));

    expect(await screen.findAllByText("Beta")).toHaveLength(2);

    const userForm = screen.getByTestId("create-user-form");
    await user.selectOptions(within(userForm).getByLabelText("Tenant"), tenantB.id);
    await user.type(within(userForm).getByLabelText("Email"), "ops@beta.example");
    await user.type(within(userForm).getByLabelText("First name"), "Ops");
    await user.type(within(userForm).getByLabelText("Last name"), "Lead");
    await user.selectOptions(within(userForm).getByLabelText("Role"), "operator");
    await user.type(within(userForm).getByLabelText("Temporary password"), "change-me-now");
    await user.click(within(userForm).getByRole("button", { name: /create user/i }));

    expect(await screen.findByText("ops@beta.example")).toBeInTheDocument();
    expect(screen.queryByText("change-me-now")).not.toBeInTheDocument();
  });

  test("admin can update role, disable, and reset a tenant user", async () => {
    const user = userEvent.setup();
    mockUsersApi();

    renderUsersPage();

    await screen.findByText("admin@acme.example");
    const adminRow = screen
      .getByText("admin@acme.example")
      .closest("tr") as HTMLTableRowElement;

    await user.selectOptions(within(adminRow).getByLabelText("Role"), "operator");
    await user.click(within(adminRow).getByRole("button", { name: /save/i }));
    await waitFor(() =>
      expect(within(adminRow).getByLabelText("Role")).toHaveValue("operator"),
    );

    await user.click(within(adminRow).getByLabelText("Enabled"));
    await user.click(within(adminRow).getByRole("button", { name: /save/i }));
    await waitFor(() =>
      expect(within(adminRow).getByLabelText("Enabled")).not.toBeChecked(),
    );

    await user.click(within(adminRow).getByRole("button", { name: /reset/i }));
    await user.type(screen.getByLabelText("New temporary password"), "change-me-again");
    await user.click(screen.getByRole("button", { name: /reset password/i }));
    expect(screen.queryByText("change-me-again")).not.toBeInTheDocument();
  });
});
