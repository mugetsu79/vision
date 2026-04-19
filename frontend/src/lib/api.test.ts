import { act } from "@testing-library/react";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/config", () => ({
  frontendConfig: {
    apiBaseUrl: "http://127.0.0.1:8000",
    oidcAuthority: "http://127.0.0.1:8080/realms/argus-dev",
    oidcClientId: "argus-frontend",
    oidcRedirectUri: "http://127.0.0.1:3000/auth/callback",
    oidcPostLogoutRedirectUri: "http://127.0.0.1:3000/signin",
  },
}));

import { useSites } from "@/hooks/use-sites";
import { useAuthStore } from "@/stores/auth-store";
import { createTestQueryWrapper } from "@/test/query-test-utils";

const initialAuthState = useAuthStore.getState();

afterEach(() => {
  vi.restoreAllMocks();
  act(() => {
    useAuthStore.setState(initialAuthState, true);
  });
});

beforeEach(() => {
  act(() => {
    useAuthStore.setState(initialAuthState, true);
  });
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

    act(() => {
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
    });

    const { result } = renderHook(() => useSites(), {
      wrapper: createTestQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [input, init] = fetchMock.mock.calls[0] as [
      RequestInfo | URL,
      RequestInit | undefined,
    ];
    const requestUrl = input instanceof Request ? input.url : String(input);
    const mergedHeaders = new Headers(input instanceof Request ? input.headers : undefined);
    const initHeaders = new Headers(init?.headers);

    initHeaders.forEach((value, key) => {
      mergedHeaders.set(key, value);
    });

    expect(requestUrl).toContain("/api/v1/sites");
    expect(mergedHeaders.get("Authorization")).toBe("Bearer test-token");
  });
});
