import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";

import { createQueryClient } from "@/app/query-client";
import { CameraWizard } from "@/components/cameras/CameraWizard";
import type { CreateCameraInput, UpdateCameraInput } from "@/hooks/use-cameras";

function renderWizard(props?: Partial<Parameters<typeof CameraWizard>[0]>) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <CameraWizard
        sites={[{ id: "site-1", name: "HQ" }]}
        models={[
          {
            id: "model-1",
            name: "Vezor YOLO",
            version: "1.0.0",
            classes: ["person", "car", "bike"],
          },
          {
            id: "model-2",
            name: "Vezor PPE",
            version: "1.0.0",
            classes: ["helmet", "vest"],
          },
        ]}
        {...props}
      />
    </QueryClientProvider>,
  );
}

function stubRect(element: HTMLElement, width: number, height: number) {
  Object.defineProperty(element, "getBoundingClientRect", {
    configurable: true,
    value: () => ({
      width,
      height,
      top: 0,
      left: 0,
      right: width,
      bottom: height,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    }),
  });
}

async function completeRequiredCreateSteps(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
  await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
  await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
  await user.click(screen.getByRole("button", { name: /next/i }));
}

async function submitCreateWithoutCalibration(user: ReturnType<typeof userEvent.setup>) {
  await completeRequiredCreateSteps(user);
  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.click(screen.getByRole("button", { name: /create camera/i }));
}

describe("CameraWizard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("moves through the first three steps and preserves browser delivery profile selection", async () => {
    const user = userEvent.setup();

    renderWizard();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText(/camera name is required/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.selectOptions(screen.getByLabelText(/processing mode/i), "central");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(
      screen.getByRole("heading", { name: /models & tracking/i, level: 2 }),
    ).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    expect(screen.getByText(/active class scope/i)).toBeInTheDocument();
    await user.click(screen.getByLabelText("person"));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-2");
    expect(screen.queryByLabelText("person")).not.toBeInTheDocument();
    expect(screen.getByLabelText("helmet")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText(/tracker type/i), "botsort");
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(
      screen.getByRole("heading", {
        name: /privacy, processing & delivery/i,
        level: 2,
      }),
    ).toBeInTheDocument();

    const browserDeliveryProfile = screen.getByLabelText(
      /browser delivery profile/i,
    );
    expect(
      within(browserDeliveryProfile).getByRole("option", {
        name: "720p10 viewer preview",
      }),
    ).toBeInTheDocument();

    await user.selectOptions(browserDeliveryProfile, "540p5");
    expect(browserDeliveryProfile).toHaveValue("540p5");

    await user.click(screen.getByRole("button", { name: /back/i }));
    expect(
      screen.getByRole("heading", { name: /models & tracking/i, level: 2 }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByLabelText(/browser delivery profile/i)).toHaveValue("540p5");
  });

  test("labels edge delivery profiles as edge-built bandwidth savers", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation((_input, init) => {
      const rawBody = init?.body;
      if (typeof rawBody !== "string") {
        throw new Error("Expected source probe request body.");
      }
      const body = JSON.parse(rawBody) as {
        processing_mode?: string;
      };
      expect(body.processing_mode).toBe("edge");

      return Promise.resolve(
        new Response(
          JSON.stringify({
            source_capability: {
              width: 1280,
              height: 720,
              fps: 20,
              codec: "h264",
              aspect_ratio: "16:9",
            },
            browser_delivery: {
              default_profile: "720p10",
              allow_native_on_demand: true,
              profiles: [
                { id: "native", kind: "passthrough" },
                { id: "annotated", kind: "transcode" },
                { id: "720p10", kind: "transcode", w: 1280, h: 720, fps: 10 },
                { id: "540p5", kind: "transcode", w: 960, h: 540, fps: 5 },
              ],
              unsupported_profiles: [],
              native_status: { available: true, reason: null },
            },
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );
    });

    renderWizard();

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.selectOptions(screen.getByLabelText(/processing mode/i), "edge");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    await user.click(screen.getByRole("button", { name: /next/i }));

    const browserDeliveryProfile = await screen.findByLabelText(
      /browser delivery profile/i,
    );
    expect(
      within(browserDeliveryProfile).getByRole("option", {
        name: "720p10 edge bandwidth saver",
      }),
    ).toBeInTheDocument();
  });

  test("shows runtime vocabulary editor for open-vocab models", async () => {
    const user = userEvent.setup();

    renderWizard({
      models: [
        {
          id: "open-model",
          name: "YOLO World",
          version: "1",
          classes: [],
          capability: "open_vocab",
          capability_config: {
            max_runtime_terms: 32,
            supports_runtime_vocabulary_updates: true,
            requires_gpu: false,
            supports_masks: false,
          },
        },
      ],
    });

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "open-model");

    expect(screen.getByLabelText(/runtime vocabulary/i)).toBeInTheDocument();
    expect(screen.queryByText(/active class scope/i)).not.toBeInTheDocument();
  });

  test("summarizes dynamic fallback when no compiled artifact is available", async () => {
    const user = userEvent.setup();

    renderWizard();

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");

    expect(screen.getByText(/Dynamic\/fallback runtime/i)).toBeInTheDocument();
    expect(screen.getByText(/No compiled artifact registered/i)).toBeInTheDocument();
  });

  test("marks compiled open-vocab artifacts stale when the vocabulary version differs", async () => {
    const user = userEvent.setup();

    renderWizard({
      models: [
        {
          id: "open-model",
          name: "YOLOE-26N",
          version: "2026.1",
          classes: [],
          capability: "open_vocab",
          capability_config: {
            supports_runtime_vocabulary_updates: true,
            max_runtime_terms: 32,
            runtime_backend: "ultralytics_yoloe",
            readiness: "experimental",
            requires_gpu: true,
            supports_masks: true,
          },
          runtime_artifacts: [
            {
              id: "artifact-1",
              model_id: "open-model",
              camera_id: "camera-1",
              scope: "scene",
              kind: "tensorrt_engine",
              capability: "open_vocab",
              runtime_backend: "tensorrt_engine",
              path: "/models/camera-1/yoloe.engine",
              target_profile: "linux-aarch64-nvidia-jetson",
              precision: "fp16",
              input_shape: { width: 640, height: 640 },
              classes: ["forklift"],
              vocabulary_hash: "b".repeat(64),
              vocabulary_version: 4,
              source_model_sha256: "a".repeat(64),
              sha256: "c".repeat(64),
              size_bytes: 2048,
              builder: {},
              runtime_versions: {},
              validation_status: "valid",
              validation_error: null,
              build_duration_seconds: 3.2,
              validation_duration_seconds: null,
              validated_at: "2026-05-10T08:00:00Z",
              created_at: "2026-05-10T08:00:00Z",
              updated_at: "2026-05-10T08:00:00Z",
            },
          ],
        },
      ],
    });

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "open-model");

    expect(screen.getByText(/Compiled stale/i)).toBeInTheDocument();
    expect(screen.getByText(/vocabulary changed/i)).toBeInTheDocument();
  });

  test("labels model options with capability and backend", async () => {
    const user = userEvent.setup();

    renderWizard({
      models: [
        {
          id: "open-model",
          name: "YOLOE-26N",
          version: "2026.1",
          classes: [],
          capability: "open_vocab",
          capability_config: {
            supports_runtime_vocabulary_updates: true,
            max_runtime_terms: 32,
            runtime_backend: "ultralytics_yoloe",
            readiness: "experimental",
            requires_gpu: true,
            supports_masks: true,
          },
        },
      ],
    });

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

  test("probes a new RTSP source before showing browser delivery profiles", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          source_capability: {
            width: 1280,
            height: 720,
            fps: 20,
            codec: "h264",
            aspect_ratio: "16:9",
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
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    renderWizard();

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(await screen.findByText(/source is 1280×720/i)).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "1080p15 viewer preview" })).not.toBeInTheDocument();
  });

  test("uses probed source size for new-camera calibration authoring", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          source_capability: {
            width: 1920,
            height: 1080,
            fps: 20,
            codec: "h264",
            aspect_ratio: "16:9",
          },
          browser_delivery: {
            default_profile: "720p10",
            allow_native_on_demand: true,
            profiles: [
              { id: "native", kind: "passthrough" },
              { id: "1080p15", kind: "transcode", w: 1920, h: 1080, fps: 15 },
              { id: "720p10", kind: "transcode", w: 1280, h: 720, fps: 10 },
              { id: "540p5", kind: "transcode", w: 960, h: 540, fps: 5 },
            ],
            unsupported_profiles: [],
            native_status: { available: true, reason: null },
          },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    renderWizard();

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(await screen.findByRole("option", { name: "1080p15 viewer preview" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText(/analytics frame 1920×1080/i)).toBeInTheDocument();
  });

  test("reprobes an existing camera before showing stale stored browser profiles", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation((_input, init) => {
      const rawBody = init?.body;
      if (typeof rawBody !== "string") {
        throw new Error("Expected source probe request body.");
      }
      const body = JSON.parse(rawBody) as {
        camera_id?: string | null;
        rtsp_url?: string | null;
      };
      expect(body.camera_id).toBe("camera-1");
      expect(body.rtsp_url).toBeNull();

      return Promise.resolve(new Response(
        JSON.stringify({
          source_capability: {
            width: 1280,
            height: 720,
            fps: 20,
            codec: "h264",
            aspect_ratio: "16:9",
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
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ));
    });

    renderWizard({
      initialCamera: {
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
          default_profile: "1080p15",
          allow_native_on_demand: true,
          profiles: [
            { id: "native", kind: "passthrough" },
            { id: "1080p15", kind: "transcode", w: 1920, h: 1080, fps: 15 },
            { id: "720p10", kind: "transcode", w: 1280, h: 720, fps: 10 },
            { id: "540p5", kind: "transcode", w: 960, h: 540, fps: 5 },
          ],
          unsupported_profiles: [],
          native_status: { available: true, reason: null },
        },
        source_capability: null,
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-04-19T00:00:00Z",
        updated_at: "2026-04-19T00:00:00Z",
      },
    });

    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(await screen.findByText(/source is 1280×720/i)).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "1080p15 viewer preview" })).not.toBeInTheDocument();
  });

  test("hides unsupported browser profiles for the detected source size", async () => {
    const user = userEvent.setup();

    renderWizard({
      initialCamera: {
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
        created_at: "2026-04-19T00:00:00Z",
        updated_at: "2026-04-19T00:00:00Z",
      },
    });

    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.queryByRole("option", { name: "1080p15 viewer preview" })).not.toBeInTheDocument();
    expect(
      screen.getByText(/source is 1280×720, so 1080p15 is unavailable/i),
    ).toBeInTheDocument();
  });

  test("default create payload sends balanced profile, speed disabled, and no homography when calibration is untouched", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWizard({ onSubmit });

    await submitCreateWithoutCalibration(user);

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as CreateCameraInput | undefined;

    expect(submittedPayload).toBeDefined();
    expect(submittedPayload?.vision_profile).toMatchObject({
      compute_tier: "edge_standard",
      accuracy_mode: "balanced",
      scene_difficulty: "cluttered",
      object_domain: "mixed",
      motion_metrics: { speed_enabled: false },
    });
    expect(submittedPayload?.homography).toBeNull();
  });

  test("enabling speed requires four source points, four destination points, and a reference distance before save", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWizard({ onSubmit });

    await completeRequiredCreateSteps(user);
    await user.click(screen.getByLabelText(/speed metrics/i));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText(/4 source points are required/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();

    for (let count = 0; count < 4; count += 1) {
      await user.click(screen.getByRole("button", { name: /add source point/i }));
    }
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText(/4 destination points are required/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();

    for (let count = 0; count < 4; count += 1) {
      await user.click(
        screen.getByRole("button", { name: /add destination point/i }),
      );
    }
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText(/reference distance is required/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("selecting Maximum Accuracy and Advanced Edge submits the edge advanced Jetson compute tier", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWizard({ onSubmit });

    await completeRequiredCreateSteps(user);
    await user.selectOptions(screen.getByLabelText(/vision profile/i), "maximum_accuracy");
    await user.selectOptions(screen.getByLabelText(/compute target/i), "edge_advanced_jetson");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create camera/i }));

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as CreateCameraInput | undefined;

    expect(submittedPayload?.vision_profile?.accuracy_mode).toBe("maximum_accuracy");
    expect(submittedPayload?.vision_profile?.compute_tier).toBe("edge_advanced_jetson");
  });

  test("adding an include detection region submits it separately from event boundaries", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWizard({ onSubmit });

    await completeRequiredCreateSteps(user);
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /add include region/i }));
    const regionCanvas = screen.getByLabelText(/detection region 1 canvas/i);
    stubRect(regionCanvas, 640, 360);
    fireEvent.click(regionCanvas, { clientX: 0, clientY: 0 });
    fireEvent.click(regionCanvas, { clientX: 50, clientY: 0 });
    fireEvent.click(regionCanvas, { clientX: 50, clientY: 50 });
    fireEvent.click(regionCanvas, { clientX: 0, clientY: 50 });
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create camera/i }));

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as CreateCameraInput | undefined;

    expect(submittedPayload?.zones).toEqual([]);
    expect(submittedPayload?.detection_regions?.[0]?.mode).toBe("include");
  });

  test("adding an exclusion detection region submits it separately from event boundaries", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWizard({ onSubmit });

    await completeRequiredCreateSteps(user);
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /add exclusion region/i }));
    const regionCanvas = screen.getByLabelText(/detection region 1 canvas/i);
    stubRect(regionCanvas, 640, 360);
    fireEvent.click(regionCanvas, { clientX: 0, clientY: 0 });
    fireEvent.click(regionCanvas, { clientX: 50, clientY: 0 });
    fireEvent.click(regionCanvas, { clientX: 50, clientY: 50 });
    fireEvent.click(regionCanvas, { clientX: 0, clientY: 50 });
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create camera/i }));

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as CreateCameraInput | undefined;

    expect(submittedPayload?.zones).toEqual([]);
    expect(submittedPayload?.detection_regions?.[0]?.mode).toBe("exclude");
  });

  test("event boundaries still submit to zones instead of detection regions", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWizard({ onSubmit });

    await completeRequiredCreateSteps(user);
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /add line boundary/i }));
    await user.type(screen.getByLabelText(/boundary 1 id/i), "door-line");
    const lineCanvas = screen.getByLabelText(/boundary 1 canvas/i);
    stubRect(lineCanvas, 640, 360);
    fireEvent.click(lineCanvas, { clientX: 5, clientY: 10 });
    fireEvent.click(lineCanvas, { clientX: 55, clientY: 110 });
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create camera/i }));

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as CreateCameraInput | undefined;

    expect(submittedPayload?.zones).toHaveLength(1);
    expect(submittedPayload?.zones?.[0]?.id).toBe("door-line");
    expect(submittedPayload?.detection_regions).toEqual([]);
  });

  test("submits the completed create payload with homography and browser delivery settings", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWizard({ onSubmit });

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    await user.click(screen.getByLabelText("person"));
    await user.click(screen.getByLabelText("car"));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(
      screen.getByLabelText(/browser delivery profile/i),
      "540p5",
    );
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getAllByText(/event boundaries/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/count boundaries/i)).not.toBeInTheDocument();
    for (let count = 0; count < 4; count += 1) {
      await user.click(screen.getByRole("button", { name: /add source point/i }));
      await user.click(
        screen.getByRole("button", { name: /add destination point/i }),
      );
    }
    await user.clear(screen.getByLabelText(/reference distance \(m\)/i));
    await user.type(screen.getByLabelText(/reference distance \(m\)/i), "12.5");
    await user.click(screen.getByRole("button", { name: /add line boundary/i }));
    await user.type(screen.getByLabelText(/boundary 1 id/i), "door-line");
    await user.type(screen.getByLabelText(/boundary 1 classes/i), "person,car");
    expect(screen.queryByLabelText(/boundary 1 x1/i)).not.toBeInTheDocument();
    const lineCanvas = screen.getByLabelText(/boundary 1 canvas/i);
    stubRect(lineCanvas, 640, 360);
    fireEvent.click(lineCanvas, { clientX: 5, clientY: 10 });
    fireEvent.click(lineCanvas, { clientX: 55, clientY: 110 });
    await user.click(screen.getByRole("button", { name: /add polygon zone/i }));
    await user.type(screen.getByLabelText(/boundary 2 id/i), "desk-zone");
    const polygonCanvas = screen.getByLabelText(/boundary 2 canvas/i);
    stubRect(polygonCanvas, 640, 360);
    fireEvent.click(polygonCanvas, { clientX: 0, clientY: 0 });
    fireEvent.click(polygonCanvas, { clientX: 50, clientY: 0 });
    fireEvent.click(polygonCanvas, { clientX: 50, clientY: 50 });
    fireEvent.click(polygonCanvas, { clientX: 0, clientY: 50 });
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText(/class scope/i)).toBeInTheDocument();
    expect(screen.getByText(/event boundaries/i)).toBeInTheDocument();
    expect(screen.queryByText(/count boundaries/i)).not.toBeInTheDocument();
    expect(screen.getByText(/person, car/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /create camera/i }));

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as CreateCameraInput | undefined;

    expect(submittedPayload).toBeDefined();
    expect(submittedPayload?.site_id).toBe("site-1");
    expect(submittedPayload?.name).toBe("Dock Camera");
    expect(submittedPayload?.rtsp_url).toBe("rtsp://camera.local/live");
    expect(submittedPayload?.browser_delivery?.default_profile).toBe("540p5");
    expect(submittedPayload?.active_classes).toEqual(["person", "car"]);
    expect(submittedPayload?.homography).not.toBeNull();
    expect(submittedPayload?.homography?.ref_distance_m).toBe(12.5);
    expect(submittedPayload?.homography?.src).toEqual([
      [0, 0],
      [10, 10],
      [20, 20],
      [30, 30],
    ]);
    expect(submittedPayload?.homography?.dst).toEqual([
      [0, 0],
      [5, 5],
      [10, 10],
      [15, 15],
    ]);
    expect(submittedPayload?.zones).toEqual([
      {
        id: "door-line",
        type: "line",
        points: [
          [10, 20],
          [110, 220],
        ],
        class_names: ["person", "car"],
        frame_size: { width: 1280, height: 720 },
      },
      {
        id: "desk-zone",
        type: "polygon",
        polygon: [
          [0, 0],
          [100, 0],
          [100, 100],
          [0, 100],
        ],
        frame_size: { width: 1280, height: 720 },
      },
    ]);
  });

  test("keeps RTSP masked in edit mode unless the operator explicitly replaces it", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    const createObjectURL = vi.fn(() => "blob:camera-preview");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url.endsWith("/api/v1/cameras/camera-1/setup-preview")) {
        return Promise.resolve(new Response(
          JSON.stringify({
            camera_id: "camera-1",
            preview_url: "/api/v1/cameras/camera-1/setup-preview/image?rev=12345",
            frame_size: { width: 1280, height: 720 },
            captured_at: "2026-04-19T00:00:00Z",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ));
      }

      return Promise.resolve(new Response(new Uint8Array([0xff, 0xd8, 0xff, 0xdb]), {
        status: 200,
        headers: { "Content-Type": "image/jpeg" },
      }));
    });

    renderWizard({
      onSubmit,
      initialCamera: {
        id: "camera-1",
        site_id: "site-1",
        edge_node_id: null,
        name: "Dock Camera",
        rtsp_url_masked: "rtsp://***",
        processing_mode: "hybrid",
        primary_model_id: "model-1",
        secondary_model_id: null,
        tracker_type: "botsort",
        active_classes: [],
        attribute_rules: [],
        zones: [
          {
            id: "entry-line",
            type: "line",
            points: [
              [10, 10],
              [20, 20],
            ],
            class_names: ["person"],
          },
          {
            id: "workspace",
            polygon: [
              [0, 0],
              [50, 0],
              [50, 50],
              [0, 50],
            ],
          },
        ],
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
        vision_profile: {
          compute_tier: "central_gpu",
          accuracy_mode: "maximum_accuracy",
          scene_difficulty: "occluded",
          object_domain: "people",
          motion_metrics: { speed_enabled: false },
          candidate_quality: { new_track_min_confidence: { person: 0.6 } },
          tracker_profile: { track_buffer_seconds: 2.5 },
          verifier_profile: { enabled: true },
        },
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
        },
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-04-19T00:00:00Z",
        updated_at: "2026-04-19T00:00:00Z",
      },
    });

    expect(screen.getByLabelText(/rtsp url/i)).toHaveAttribute(
      "placeholder",
      "rtsp://***",
    );

    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(await screen.findByText(/analytics still ready/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refresh still/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /save camera/i }));

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as UpdateCameraInput | undefined;

    expect(submittedPayload).toBeDefined();
    expect(submittedPayload).not.toHaveProperty("rtsp_url");
    expect(submittedPayload?.zones).toEqual([
      {
        id: "entry-line",
        type: "line",
        points: [
          [10, 10],
          [20, 20],
        ],
        class_names: ["person"],
        frame_size: { width: 1280, height: 720 },
      },
      {
        id: "workspace",
        type: "polygon",
        polygon: [
          [0, 0],
          [50, 0],
          [50, 50],
          [0, 50],
        ],
        frame_size: { width: 1280, height: 720 },
      },
    ]);
    expect(submittedPayload?.vision_profile).toMatchObject({
      compute_tier: "central_gpu",
      accuracy_mode: "maximum_accuracy",
      scene_difficulty: "occluded",
      object_domain: "people",
      motion_metrics: { speed_enabled: false },
      candidate_quality: { new_track_min_confidence: { person: 0.6 } },
      tracker_profile: { track_buffer_seconds: 2.5 },
      verifier_profile: { enabled: true },
    });
  });

  test("surfaces a step-level calibration error when the analytics still cannot be captured", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url.endsWith("/api/v1/cameras/camera-1/setup-preview")) {
        return Promise.resolve(new Response(
          JSON.stringify({
            detail:
              "Unable to capture an analytics still from the camera source right now. Retry the capture after confirming the camera stream is reachable.",
          }),
          {
            status: 503,
            headers: { "Content-Type": "application/json" },
          },
        ));
      }

      throw new Error(`Unexpected fetch to ${url}`);
    });

    renderWizard({
      initialCamera: {
        id: "camera-1",
        site_id: "site-1",
        edge_node_id: null,
        name: "Dock Camera",
        rtsp_url_masked: "rtsp://***",
        processing_mode: "hybrid",
        primary_model_id: "model-1",
        secondary_model_id: null,
        tracker_type: "botsort",
        active_classes: [],
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
          blur_faces: true,
          blur_plates: true,
          method: "gaussian",
          strength: 7,
        },
        browser_delivery: {
          default_profile: "720p10",
          allow_native_on_demand: true,
          profiles: [],
        },
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-04-19T00:00:00Z",
        updated_at: "2026-04-19T00:00:00Z",
      },
    });

    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(await screen.findByText(/unable to capture analytics still/i)).toBeInTheDocument();
    expect(
      screen.getByText(/source points can still be placed on the 1280×720 fallback analytics plane/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refresh still/i })).toBeInTheDocument();
  });

  test("requires reselecting a primary model when the stored model is no longer in inventory", async () => {
    const user = userEvent.setup();

    renderWizard({
      initialCamera: {
        id: "camera-1",
        site_id: "site-1",
        edge_node_id: null,
        name: "Dock Camera",
        rtsp_url_masked: "rtsp://***",
        processing_mode: "central",
        primary_model_id: "missing-model",
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
          blur_faces: true,
          blur_plates: true,
          method: "gaussian",
          strength: 7,
        },
        browser_delivery: {
          default_profile: "720p10",
          allow_native_on_demand: true,
          profiles: [],
        },
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-04-19T00:00:00Z",
        updated_at: "2026-04-19T00:00:00Z",
      },
    });

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(
      screen.getByText(/select a primary model to choose the persistent class scope/i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(
      screen.getByText(/primary model must be selected from the current inventory/i),
    ).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    expect(screen.getByLabelText("person")).not.toBeChecked();
  });

  test("preserves stored active classes while models are still loading in edit mode", async () => {
    const user = userEvent.setup();
    const initialCamera = {
      id: "camera-1",
      site_id: "site-1",
      edge_node_id: null,
      name: "Dock Camera",
      rtsp_url_masked: "rtsp://***",
      processing_mode: "central" as const,
      primary_model_id: "model-1",
      secondary_model_id: null,
      tracker_type: "botsort" as const,
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
        blur_faces: true,
        blur_plates: true,
        method: "gaussian" as const,
        strength: 7,
      },
      browser_delivery: {
        default_profile: "720p10" as const,
        allow_native_on_demand: true,
        profiles: [],
      },
      frame_skip: 1,
      fps_cap: 25,
      created_at: "2026-04-19T00:00:00Z",
      updated_at: "2026-04-19T00:00:00Z",
    };

    const view = renderWizard({
      initialCamera,
      models: [],
      modelsLoading: true,
    });

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText(/loading the latest registered models/i)).toBeInTheDocument();

    view.rerender(
      <QueryClientProvider client={createQueryClient()}>
        <CameraWizard
          initialCamera={initialCamera}
          sites={[{ id: "site-1", name: "HQ" }]}
          models={[
            {
              id: "model-1",
              name: "Vezor YOLO",
              version: "1.0.0",
              classes: ["person", "car", "bike"],
            },
          ]}
          modelsLoading={false}
        />
      </QueryClientProvider>,
    );

    expect(screen.getByLabelText("person")).toBeChecked();
  });
});
