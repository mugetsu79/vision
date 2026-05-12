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
import { PolicyDraftReview } from "@/components/policy/PolicyDraftReview";
import type { Camera } from "@/hooks/use-cameras";
import type { PolicyDraft } from "@/hooks/use-policy-drafts";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

const camera: Camera = {
  id: "camera-1",
  site_id: "site-1",
  edge_node_id: null,
  name: "Dock Camera",
  rtsp_url_masked: "rtsp://***",
  processing_mode: "edge",
  primary_model_id: "model-1",
  secondary_model_id: null,
  tracker_type: "botsort",
  active_classes: ["person"],
  runtime_vocabulary: {
    terms: ["person"],
    source: "manual",
    version: 1,
    updated_at: null,
  },
  attribute_rules: [],
  zones: [],
  vision_profile: {
    compute_tier: "edge_standard",
    accuracy_mode: "balanced",
    scene_difficulty: "cluttered",
    object_domain: "mixed",
    motion_metrics: { speed_enabled: false },
  },
  detection_regions: [],
  homography: null,
  privacy: {
    blur_faces: true,
    blur_plates: true,
    method: "gaussian",
    strength: 7,
  },
  browser_delivery: {
    default_profile: "720p10",
    allow_native_on_demand: true,
    profiles: [],
    unsupported_profiles: [],
    native_status: { available: true, reason: null },
  },
  source_capability: null,
  frame_skip: 1,
  fps_cap: 10,
  recording_policy: {
    enabled: false,
    mode: "event_clip",
    pre_seconds: 4,
    post_seconds: 8,
    fps: 10,
    max_duration_seconds: 15,
    storage_profile: "edge_local",
    storage_profile_id: null,
    snapshot_enabled: false,
    snapshot_offset_seconds: 0,
    snapshot_quality: 85,
  },
  created_at: "2026-05-12T10:00:00Z",
  updated_at: "2026-05-12T10:00:00Z",
};

function renderPanel() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <PolicyDraftReview camera={camera} />
    </QueryClientProvider>,
  );
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function draft(status: PolicyDraft["status"] = "draft"): PolicyDraft {
  return {
    id: "draft-1",
    tenant_id: "tenant-1",
    camera_id: "camera-1",
    site_id: "site-1",
    status,
    prompt: "Watch forklifts in the dock zone and record clips",
    structured_diff: {
      scene_contract: {
        after: {
          runtime_vocabulary: ["person", "forklift"],
        },
      },
      privacy_manifest: {
        after: {
          blur_faces: true,
        },
      },
      recording_policy: {
        after: {
          enabled: true,
          mode: "event_clip",
        },
      },
      runtime_vocabulary: {
        add: ["forklift"],
        after: ["person", "forklift"],
      },
      detection_regions: {
        add: [{ id: "dock", mode: "include" }],
      },
      incident_rules: {
        add: [{ incident_type: "forklift_activity", action: "record_clip" }],
      },
    },
    metadata: {
      llm_provider: "openai",
      llm_model: "gpt-4.1-mini",
      llm_profile_hash: "c".repeat(64),
    },
    created_by_subject: "admin-1",
    approved_by_subject:
      status === "approved" || status === "applied" ? "admin-1" : null,
    rejected_by_subject: status === "rejected" ? "admin-1" : null,
    applied_by_subject: status === "applied" ? "admin-1" : null,
    created_at: "2026-05-12T10:00:00Z",
    updated_at: "2026-05-12T10:00:00Z",
    decided_at:
      status === "draft" ? null : "2026-05-12T10:05:00Z",
    applied_at: status === "applied" ? "2026-05-12T10:10:00Z" : null,
  };
}

describe("PolicyDraftReview", () => {
  beforeEach(() => {
    act(() => {
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
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("creates a draft and renders the review diff without applying it", async () => {
    const user = userEvent.setup();
    const requests: string[] = [];
    let createPayload: Record<string, unknown> | null = null;

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const request = input as Request;
      const url = new URL(request.url);
      requests.push(`${request.method} ${url.pathname}`);

      if (url.pathname === "/api/v1/policy-drafts" && request.method === "POST") {
        createPayload = (await request.json()) as Record<string, unknown>;
        return jsonResponse(draft(), 201);
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPanel();

    await user.type(
      screen.getByLabelText(/policy intent/i),
      "Watch forklifts in the dock zone and record clips",
    );
    await user.click(screen.getByRole("button", { name: /create draft/i }));

    expect(await screen.findByText("Scene contract")).toBeInTheDocument();
    expect(screen.getByText("Privacy manifest")).toBeInTheDocument();
    expect(screen.getByText("Recording policy")).toBeInTheDocument();
    expect(screen.getByText("Vocabulary")).toBeInTheDocument();
    expect(screen.getByText("Detection regions")).toBeInTheDocument();
    expect(screen.getByText("Incident rules")).toBeInTheDocument();
    expect(screen.getAllByText(/forklift/).length).toBeGreaterThan(0);
    expect(createPayload).toMatchObject({
      camera_id: "camera-1",
      prompt: "Watch forklifts in the dock zone and record clips",
      use_llm: true,
    });
    expect(requests).toEqual(["POST /api/v1/policy-drafts"]);
    expect(
      screen.getByRole("button", { name: /apply approved draft/i }),
    ).toBeDisabled();
  });

  test("approves and applies only through policy draft endpoints", async () => {
    const user = userEvent.setup();
    const requests: string[] = [];

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const request = input as Request;
      const url = new URL(request.url);
      requests.push(`${request.method} ${url.pathname}`);

      if (url.pathname === "/api/v1/policy-drafts" && request.method === "POST") {
        return jsonResponse(draft(), 201);
      }
      if (
        url.pathname === "/api/v1/policy-drafts/draft-1/approve" &&
        request.method === "POST"
      ) {
        return jsonResponse(draft("approved"));
      }
      if (
        url.pathname === "/api/v1/policy-drafts/draft-1/apply" &&
        request.method === "POST"
      ) {
        return jsonResponse(draft("applied"));
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPanel();

    await user.type(screen.getByLabelText(/policy intent/i), "Watch forklifts");
    await user.click(screen.getByRole("button", { name: /create draft/i }));
    await screen.findByText("Scene contract");
    await user.click(screen.getByRole("button", { name: /approve draft/i }));

    await waitFor(() => {
      expect(screen.getByText("approved")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /apply approved draft/i }));

    await waitFor(() => {
      expect(screen.getByText("applied")).toBeInTheDocument();
    });
    expect(requests).toEqual([
      "POST /api/v1/policy-drafts",
      "POST /api/v1/policy-drafts/draft-1/approve",
      "POST /api/v1/policy-drafts/draft-1/apply",
    ]);
  });

  test("rejects a draft and disables decision buttons", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/policy-drafts" && request.method === "POST") {
        return jsonResponse(draft(), 201);
      }
      if (
        url.pathname === "/api/v1/policy-drafts/draft-1/reject" &&
        request.method === "POST"
      ) {
        return jsonResponse(draft("rejected"));
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPanel();

    await user.type(screen.getByLabelText(/policy intent/i), "Watch forklifts");
    await user.click(screen.getByRole("button", { name: /create draft/i }));
    await screen.findByText("Scene contract");
    await user.click(screen.getByRole("button", { name: /reject draft/i }));

    await waitFor(() => {
      expect(screen.getByText("rejected")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /approve draft/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /reject draft/i })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /apply approved draft/i }),
    ).toBeDisabled();
  });

  test("clears the loaded draft when the selected camera changes", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/policy-drafts" && request.method === "POST") {
        return jsonResponse(draft(), 201);
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    const { rerender } = render(
      <QueryClientProvider client={createQueryClient()}>
        <PolicyDraftReview camera={camera} />
      </QueryClientProvider>,
    );

    await user.type(screen.getByLabelText(/policy intent/i), "Watch forklifts");
    await user.click(screen.getByRole("button", { name: /create draft/i }));
    await screen.findByText("Scene contract");

    rerender(
      <QueryClientProvider client={createQueryClient()}>
        <PolicyDraftReview
          camera={{
            ...camera,
            id: "camera-2",
            name: "Warehouse Camera",
          }}
        />
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", { name: /policy drafts for warehouse camera/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("No policy draft selected")).toBeInTheDocument();
    expect(screen.queryByText("Scene contract")).not.toBeInTheDocument();
  });
});
