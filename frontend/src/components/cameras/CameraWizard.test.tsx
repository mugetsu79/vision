import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { createQueryClient } from "@/app/query-client";
import { CameraWizard } from "@/components/cameras/CameraWizard";
import type { CreateCameraInput, UpdateCameraInput } from "@/hooks/use-cameras";

function renderWizard(props?: Partial<Parameters<typeof CameraWizard>[0]>) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <CameraWizard
        sites={[{ id: "site-1", name: "HQ" }]}
        models={[
          { id: "model-1", name: "Argus YOLO", version: "1.0.0" },
          { id: "model-2", name: "Argus PPE", version: "1.0.0" },
        ]}
        {...props}
      />
    </QueryClientProvider>,
  );
}

describe("CameraWizard", () => {
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

    await user.selectOptions(browserDeliveryProfile, "540p5");
    expect(browserDeliveryProfile).toHaveValue("540p5");

    await user.click(screen.getByRole("button", { name: /back/i }));
    expect(
      screen.getByRole("heading", { name: /models & tracking/i, level: 2 }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByLabelText(/browser delivery profile/i)).toHaveValue("540p5");
  });

  test("requires four source points, four destination points, and a reference distance before save", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWizard({ onSubmit });

    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText(/4 source points are required/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
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
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.selectOptions(
      screen.getByLabelText(/browser delivery profile/i),
      "540p5",
    );
    await user.click(screen.getByRole("button", { name: /next/i }));

    for (let count = 0; count < 4; count += 1) {
      await user.click(screen.getByRole("button", { name: /add source point/i }));
      await user.click(
        screen.getByRole("button", { name: /add destination point/i }),
      );
    }
    await user.clear(screen.getByLabelText(/reference distance \(m\)/i));
    await user.type(screen.getByLabelText(/reference distance \(m\)/i), "12.5");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create camera/i }));

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as CreateCameraInput | undefined;

    expect(submittedPayload).toBeDefined();
    expect(submittedPayload?.site_id).toBe("site-1");
    expect(submittedPayload?.name).toBe("Dock Camera");
    expect(submittedPayload?.rtsp_url).toBe("rtsp://camera.local/live");
    expect(submittedPayload?.browser_delivery?.default_profile).toBe("540p5");
    expect(submittedPayload?.homography.ref_distance_m).toBe(12.5);
    expect(submittedPayload?.homography.src).toEqual([
      [0, 0],
      [10, 10],
      [20, 20],
      [30, 30],
    ]);
    expect(submittedPayload?.homography.dst).toEqual([
      [0, 0],
      [5, 5],
      [10, 10],
      [15, 15],
    ]);
  });

  test("keeps RTSP masked in edit mode unless the operator explicitly replaces it", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

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

    expect(screen.getByLabelText(/rtsp url/i)).toHaveAttribute(
      "placeholder",
      "rtsp://***",
    );

    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /save camera/i }));

    const submittedPayload = onSubmit.mock.calls[0]?.[0] as UpdateCameraInput | undefined;

    expect(submittedPayload).toBeDefined();
    expect(submittedPayload).not.toHaveProperty("rtsp_url");
  });
});
