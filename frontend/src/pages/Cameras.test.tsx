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

vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: {
      mode: "manual_dev",
      generated_at: "2026-05-09T08:00:00Z",
      summary: {
        desired_workers: 1,
        running_workers: 1,
        stale_nodes: 0,
        offline_nodes: 0,
        native_unavailable_cameras: 1,
      },
      nodes: [],
      camera_workers: [
        {
          camera_id: "camera-1",
          camera_name: "Dock Camera",
          site_id: "site-1",
          node_id: null,
          node_hostname: null,
          processing_mode: "central",
          desired_state: "manual",
          runtime_status: "running",
          lifecycle_owner: "manual_dev",
          dev_run_command: null,
          detail: null,
        },
      ],
      delivery_diagnostics: [
        {
          camera_id: "camera-1",
          camera_name: "Dock Camera",
          processing_mode: "central",
          assigned_node_id: null,
          source_capability: { width: 1920, height: 1080, fps: 15 },
          default_profile: "native",
          available_profiles: [],
          native_status: { available: false, reason: "source_unavailable" },
          selected_stream_mode: "passthrough",
        },
      ],
    },
  }),
}));

import { createQueryClient } from "@/app/query-client";
import { CamerasPage } from "@/pages/Cameras";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

function renderPage() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <CamerasPage />
    </QueryClientProvider>,
  );
}

function emptyModelCatalogResponse() {
  return new Response(JSON.stringify([]), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("CamerasPage", () => {
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

  test("refetches models when the create wizard opens so newly registered models appear", async () => {
    const user = userEvent.setup();
    let modelRequests = 0;

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      await Promise.resolve();
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        modelRequests += 1;
        return new Response(
          JSON.stringify(
            modelRequests === 1
              ? []
              : [
                  {
                    id: "model-1",
                    name: "Vezor Radar",
                    version: "1.0.0",
                    task: "detect",
                    path: "/models/radar.onnx",
                    format: "onnx",
                    classes: ["person", "car"],
                    input_shape: { width: 640, height: 640 },
                    sha256: "a".repeat(64),
                    size_bytes: 1024,
                    license: "Apache-2.0",
                  },
                ],
          ),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/model-catalog") {
        return emptyModelCatalogResponse();
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    expect(
      await screen.findByRole("heading", { name: /scene setup/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("scene-setup-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("scene-setup-sequence")).toBeInTheDocument();
    expect(screen.getByTestId("scene-inventory-table")).toBeInTheDocument();
    expect(screen.getByText(/^Scenes$/i)).toBeInTheDocument();
    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByText("Model")).toBeInTheDocument();
    expect(screen.getByText("Privacy")).toBeInTheDocument();
    expect(screen.getByText("Boundaries")).toBeInTheDocument();
    expect(screen.getByText("Calibration")).toBeInTheDocument();
    expect(screen.queryByText(/^Cameras$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no cameras yet/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /add camera/i }),
    ).not.toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /add scene/i }));
    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(
      screen.getByLabelText(/rtsp url/i),
      "rtsp://camera.local/live",
    );
    await user.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() =>
      expect(screen.getByLabelText(/primary model/i)).toHaveValue(""),
    );
    expect(
      within(screen.getByLabelText(/primary model/i)).getByRole("option", {
        name: /vezor radar 1\.0\.0/i,
      }),
    ).toBeInTheDocument();
    expect(modelRequests).toBeGreaterThanOrEqual(2);
  });

  test("hides catalog hints once registered models are available", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      await Promise.resolve();
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        return new Response(
          JSON.stringify([
            {
              id: "open-model",
              name: "YOLOE-26N",
              version: "2026.1",
              task: "detect",
              path: "/models/yoloe-26n-seg.pt",
              format: "pt",
              capability: "open_vocab",
              capability_config: {
                supports_runtime_vocabulary_updates: true,
                max_runtime_terms: 32,
                runtime_backend: "ultralytics_yoloe",
                readiness: "experimental",
                requires_gpu: true,
                supports_masks: true,
              },
              classes: [],
              input_shape: { width: 640, height: 640 },
              sha256: "b".repeat(64),
              size_bytes: 2048,
              license: "AGPL-3.0",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/model-catalog") {
        return new Response(
          JSON.stringify([
            {
              id: "yoloe-26n-open-vocab-pt",
              name: "YOLOE-26N Open Vocab",
              version: "2026.1",
              task: "detect",
              path_hint: "models/yoloe-26n-seg.pt",
              format: "pt",
              capability: "open_vocab",
              capability_config: {
                supports_runtime_vocabulary_updates: true,
                max_runtime_terms: 32,
                runtime_backend: "ultralytics_yoloe",
                readiness: "experimental",
                requires_gpu: true,
                supports_masks: true,
              },
              classes: [],
              input_shape: { width: 640, height: 640 },
              registration_state: "unregistered",
              registered_model_id: null,
              artifact_exists: false,
              note: "Preferred experimental open-vocab lab path.",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/model-catalog") {
        return emptyModelCatalogResponse();
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    await user.click(await screen.findByRole("button", { name: /add scene/i }));
    await waitFor(() =>
      expect(screen.queryByTestId("model-catalog-hints")).not.toBeInTheDocument(),
    );

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(
      within(screen.getByLabelText(/primary model/i)).getByRole("option", {
        name: /open vocab - ultralytics_yoloe - experimental/i,
      }),
    ).toBeInTheDocument();
  });

  test("shows catalog hints only when no registered models are available", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      await Promise.resolve();
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/model-catalog") {
        return new Response(
          JSON.stringify([
            {
              id: "yolo26n-coco-onnx",
              name: "YOLO26n COCO",
              version: "2026.1",
              task: "detect",
              path_hint: "models/yolo26n.onnx",
              format: "onnx",
              capability: "fixed_vocab",
              capability_config: {
                supports_runtime_vocabulary_updates: false,
                runtime_backend: "onnxruntime",
                readiness: "ready",
                requires_gpu: false,
                supports_masks: false,
              },
              classes: [],
              input_shape: { width: 640, height: 640 },
              registration_state: "unregistered",
              registered_model_id: null,
              artifact_exists: true,
              note: "Default fast detector.",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    await user.click(await screen.findByRole("button", { name: /add scene/i }));
    expect(await screen.findByTestId("model-catalog-hints")).toHaveTextContent(
      /YOLO26n COCO/,
    );
  });

  test("deduplicates repeated registered model options", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      await Promise.resolve();
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        const duplicate = {
          name: "YOLO12n COCO iMac",
          version: "lab-imac",
          task: "detect",
          path: "/models/yolo12n.onnx",
          format: "onnx",
          capability: "fixed_vocab",
          capability_config: {
            supports_runtime_vocabulary_updates: false,
            runtime_backend: "onnxruntime",
            requires_gpu: false,
            supports_masks: false,
          },
          classes: ["person", "car"],
          input_shape: { width: 640, height: 640 },
          sha256: "a".repeat(64),
          size_bytes: 1024,
          license: "AGPL-3.0",
        };
        return new Response(
          JSON.stringify([
            { ...duplicate, id: "model-1" },
            { ...duplicate, id: "model-2" },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/model-catalog") {
        return emptyModelCatalogResponse();
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    await user.click(await screen.findByRole("button", { name: /add scene/i }));
    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() =>
      expect(screen.getByLabelText(/primary model/i)).not.toBeDisabled(),
    );
    expect(
      within(screen.getByLabelText(/primary model/i)).getAllByRole("option", {
        name: /YOLO12n COCO iMac lab-imac - fixed vocab - onnxruntime/i,
      }),
    ).toHaveLength(1);
  });

  test("shows a models loading failure inside the wizard instead of an empty silent select", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      await Promise.resolve();
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        return new Response(
          JSON.stringify({ detail: "Failed to load models." }),
          {
            status: 500,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/model-catalog") {
        return emptyModelCatalogResponse();
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    await user.click(await screen.findByRole("button", { name: /add scene/i }));
    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(
      screen.getByLabelText(/rtsp url/i),
      "rtsp://camera.local/live",
    );
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(
      await screen.findByText(/failed to load models\./i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /retry model lookup/i }),
    ).toBeInTheDocument();
  });

  test("shows source capability next to the browser delivery profile", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      await Promise.resolve();
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return new Response(
          JSON.stringify([
            {
              id: "camera-1",
              site_id: "site-1",
              edge_node_id: null,
              name: "Dock Camera",
              rtsp_url_masked: "rtsp://***",
              processing_mode: "central",
              primary_model_id: "model-1",
              secondary_model_id: null,
              tracker_type: "botsort",
              active_classes: ["person"],
              attribute_rules: [],
              zones: [],
              homography: {
                src: [
                  [0, 0],
                  [100, 0],
                  [100, 100],
                  [0, 100],
                ],
                dst: [
                  [0, 0],
                  [10, 0],
                  [10, 10],
                  [0, 10],
                ],
                ref_distance_m: 12.5,
              },
              privacy: {
                blur_faces: false,
                blur_plates: false,
                method: "gaussian",
                strength: 7,
              },
              browser_delivery: {
                default_profile: "720p10",
                allow_native_on_demand: true,
                profiles: [
                  { id: "native", kind: "passthrough" },
                  { id: "720p10", kind: "transcode", w: 1280, h: 720, fps: 10 },
                  { id: "540p5", kind: "transcode", w: 960, h: 540, fps: 5 },
                ],
                unsupported_profiles: [
                  {
                    id: "1080p15",
                    kind: "transcode",
                    w: 1920,
                    h: 1080,
                    fps: 15,
                    reason: "source_resolution_too_small",
                  },
                ],
                native_status: { available: true, reason: null },
              },
              source_capability: {
                width: 1280,
                height: 720,
                fps: 20,
                codec: "h264",
                aspect_ratio: "16:9",
              },
              frame_skip: 1,
              fps_cap: 25,
              created_at: "2026-04-20T10:00:00Z",
              updated_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/model-catalog") {
        return emptyModelCatalogResponse();
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    expect(await screen.findByText("Dock Camera")).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: /readiness/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("720p10")).toBeInTheDocument();
    expect(screen.getByText(/source 1280×720/i)).toBeInTheDocument();
    expect(screen.getByText(/needs setup/i)).toBeInTheDocument();
  });

  test("creates a camera with active classes after refetching class-bearing models", async () => {
    const user = userEvent.setup();
    let modelRequests = 0;

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras" && request.method === "GET") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/cameras" && request.method === "POST") {
        const body = (await request.json()) as { active_classes?: string[] };

        expect(body.active_classes).toEqual(["person"]);

        return new Response(JSON.stringify({ id: "camera-1" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        modelRequests += 1;
        return new Response(
          JSON.stringify(
            modelRequests === 1
              ? []
              : [
                  {
                    id: "model-1",
                    name: "Vezor Radar",
                    version: "1.0.0",
                    task: "detect",
                    path: "/models/radar.onnx",
                    format: "onnx",
                    classes: ["person", "car"],
                    input_shape: { width: 640, height: 640 },
                    sha256: "a".repeat(64),
                    size_bytes: 1024,
                    license: "Apache-2.0",
                  },
                ],
          ),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/model-catalog") {
        return emptyModelCatalogResponse();
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    await user.click(await screen.findByRole("button", { name: /add scene/i }));
    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(
      screen.getByLabelText(/rtsp url/i),
      "rtsp://camera.local/live",
    );
    await user.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() =>
      expect(screen.getByLabelText(/primary model/i)).toHaveValue(""),
    );
    await user.selectOptions(
      screen.getByLabelText(/primary model/i),
      "model-1",
    );
    await user.click(screen.getByLabelText("person"));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));

    for (let count = 0; count < 4; count += 1) {
      await user.click(
        screen.getByRole("button", { name: /add source point/i }),
      );
      await user.click(
        screen.getByRole("button", { name: /add destination point/i }),
      );
    }

    await user.clear(screen.getByLabelText(/reference distance \(m\)/i));
    await user.type(screen.getByLabelText(/reference distance \(m\)/i), "12.5");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create camera/i }));

    expect(modelRequests).toBeGreaterThanOrEqual(2);
  });
});
