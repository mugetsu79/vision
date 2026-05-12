import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
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
import { IncidentRulesPanel } from "@/components/cameras/IncidentRulesPanel";
import type { Camera } from "@/hooks/use-cameras";
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
  active_classes: ["person", "forklift"],
  runtime_vocabulary: {
    terms: ["hi_vis_worker"],
    source: "manual",
    version: 2,
    updated_at: null,
  },
  attribute_rules: [{ attribute: "hi_vis" }],
  zones: [
    {
      id: "restricted",
      type: "polygon",
      polygon: [
        [0, 0],
        [1, 0],
        [1, 1],
      ],
    },
  ],
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
    blur_faces: false,
    blur_plates: false,
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
  created_at: "2026-05-12T10:00:00Z",
  updated_at: "2026-05-12T10:00:00Z",
};

const existingRule = {
  id: "rule-1",
  camera_id: "camera-1",
  enabled: true,
  name: "Restricted person",
  incident_type: "restricted_person",
  severity: "critical",
  description: "Person in restricted area.",
  predicate: {
    class_names: ["person"],
    zone_ids: ["restricted"],
    min_confidence: 0.7,
    attributes: { hi_vis: false },
  },
  action: "record_clip",
  cooldown_seconds: 60,
  webhook_url_present: false,
  rule_hash: "c".repeat(64),
  created_at: "2026-05-12T10:00:00Z",
  updated_at: "2026-05-12T10:00:00Z",
};

function renderPanel() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <IncidentRulesPanel camera={camera} />
    </QueryClientProvider>,
  );
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("IncidentRulesPanel", () => {
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

  test("lists rules and creates a validated rule from scene classes and zones", async () => {
    const user = userEvent.setup();
    let createPayload: Record<string, unknown> | null = null;
    let ruleReads = 0;

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (
        url.pathname === "/api/v1/cameras/camera-1/incident-rules" &&
        request.method === "GET"
      ) {
        ruleReads += 1;
        return jsonResponse([existingRule]);
      }

      if (
        url.pathname === "/api/v1/cameras/camera-1/incident-rules/validate" &&
        request.method === "POST"
      ) {
        return jsonResponse({
          valid: true,
          matches: true,
          errors: [],
          normalized_incident_type: "forklift_in_restricted",
          rule_hash: "d".repeat(64),
        });
      }

      if (
        url.pathname === "/api/v1/cameras/camera-1/incident-rules" &&
        request.method === "POST"
      ) {
        createPayload = (await request.json()) as Record<string, unknown>;
        return jsonResponse(
          {
            ...existingRule,
            id: "rule-2",
            name: "Forklift restricted",
            incident_type: "forklift_in_restricted",
            rule_hash: "d".repeat(64),
          },
          201,
        );
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPanel();

    expect(
      await screen.findByRole("heading", {
        name: /incident rules for dock camera/i,
      }),
    ).toBeInTheDocument();
    await screen.findByText("Restricted person");
    const ruleList = screen.getByTestId("incident-rule-list");
    expect(within(ruleList).getByText("Restricted person")).toBeInTheDocument();
    expect(within(ruleList).getByText("restricted_person")).toBeInTheDocument();
    expect(within(ruleList).getByText("critical")).toBeInTheDocument();
    expect(within(ruleList).getByText("cccccccc")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /new rule/i }));
    await user.clear(screen.getByLabelText(/rule name/i));
    await user.type(screen.getByLabelText(/rule name/i), "Forklift restricted");
    await user.clear(screen.getByLabelText(/incident type/i));
    await user.type(
      screen.getByLabelText(/incident type/i),
      "forklift_in_restricted",
    );
    await user.click(screen.getByLabelText(/class forklift/i));
    await user.click(screen.getByLabelText(/zone restricted/i));
    await user.clear(screen.getByLabelText(/minimum confidence/i));
    await user.type(screen.getByLabelText(/minimum confidence/i), "0.82");
    await user.type(
      screen.getByLabelText(/required attributes/i),
      "hi_vis=false",
    );
    await user.selectOptions(screen.getByLabelText(/severity/i), "critical");
    await user.click(screen.getByRole("radio", { name: /record clip/i }));
    await user.clear(screen.getByLabelText(/cooldown seconds/i));
    await user.type(screen.getByLabelText(/cooldown seconds/i), "90");

    await user.click(screen.getByRole("button", { name: /validate rule/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      /sample matches/i,
    );

    await user.click(screen.getByRole("button", { name: /create rule/i }));

    await waitFor(() => expect(createPayload).not.toBeNull());
    expect(createPayload).toMatchObject({
      enabled: true,
      name: "Forklift restricted",
      incident_type: "forklift_in_restricted",
      severity: "critical",
      action: "record_clip",
      cooldown_seconds: 90,
      predicate: {
        class_names: ["forklift"],
        zone_ids: ["restricted"],
        min_confidence: 0.82,
        attributes: { hi_vis: false },
      },
    });
    await waitFor(() => expect(ruleReads).toBeGreaterThanOrEqual(2));
  });

  test("edits rules and exposes validation errors with an alert", async () => {
    const user = userEvent.setup();
    let updatePayload: Record<string, unknown> | null = null;

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (
        url.pathname === "/api/v1/cameras/camera-1/incident-rules" &&
        request.method === "GET"
      ) {
        return jsonResponse([existingRule]);
      }

      if (
        url.pathname === "/api/v1/cameras/camera-1/incident-rules/validate" &&
        request.method === "POST"
      ) {
        return jsonResponse({
          valid: false,
          matches: false,
          errors: ["Unknown class names: forklift"],
          normalized_incident_type: null,
          rule_hash: null,
        });
      }

      if (
        url.pathname === "/api/v1/cameras/camera-1/incident-rules/rule-1" &&
        request.method === "PATCH"
      ) {
        updatePayload = (await request.json()) as Record<string, unknown>;
        return jsonResponse({
          ...existingRule,
          enabled: false,
          cooldown_seconds: 45,
        });
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPanel();

    await screen.findByText("Restricted person");
    await user.click(screen.getByRole("button", { name: /validate rule/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /unknown class names/i,
    );

    await user.click(screen.getByLabelText(/enabled/i));
    await user.clear(screen.getByLabelText(/cooldown seconds/i));
    await user.type(screen.getByLabelText(/cooldown seconds/i), "45");
    await user.click(screen.getByRole("button", { name: /save rule/i }));

    await waitFor(() => expect(updatePayload).not.toBeNull());
    expect(updatePayload).toMatchObject({
      enabled: false,
      cooldown_seconds: 45,
    });
  });
});
