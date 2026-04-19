import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

import { createQueryClient } from "@/app/query-client";
import { AgentInput } from "@/components/live/AgentInput";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("AgentInput", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "prompt-8-token",
        user: {
          sub: "operator-1",
          email: "operator@argus.local",
          role: "operator",
          realm: "argus-dev",
          tenantId: "tenant-1",
          isSuperadmin: false,
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

  test("submits a global NL query and surfaces the resolved classes inline", async () => {
    const user = userEvent.setup();
    const onResolved = vi.fn();

    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          resolved_classes: ["car", "truck"],
          provider: "deterministic",
          model: "query-rules-v1",
          latency_ms: 18,
          camera_ids: [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
          ],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(
      <QueryClientProvider client={createQueryClient()}>
        <AgentInput
          cameras={[
            {
              id: "11111111-1111-1111-1111-111111111111",
              name: "North Gate",
            },
            {
              id: "22222222-2222-2222-2222-222222222222",
              name: "Depot Yard",
            },
          ]}
          onResolved={onResolved}
        />
      </QueryClientProvider>,
    );

    await user.type(screen.getByLabelText(/query argus/i), "only watch cars and trucks");
    await user.click(screen.getByRole("button", { name: /apply query/i }));

    await waitFor(() =>
      expect(screen.getByText(/car, truck/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/query-rules-v1/i)).toBeInTheDocument();
    expect(screen.getByText(/18 ms/i)).toBeInTheDocument();

    expect(onResolved).toHaveBeenCalledWith(
      expect.objectContaining({
        resolved_classes: ["car", "truck"],
      }),
      expect.objectContaining({
        scope: "all",
      }),
    );

    const request = fetchMock.mock.calls[0]?.[0];
    expect(request).toBeInstanceOf(Request);
    expect((request as Request).headers.get("Authorization")).toBe("Bearer prompt-8-token");
    await expect((request as Request).clone().json()).resolves.toMatchObject({
      prompt: "only watch cars and trucks",
      camera_ids: [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
      ],
    });
  });
});
