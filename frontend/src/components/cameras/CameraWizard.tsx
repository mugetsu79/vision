import { useEffect, useMemo, useState } from "react";

import { CameraStepSummary } from "@/components/cameras/CameraStepSummary";
import { HomographyEditor } from "@/components/cameras/HomographyEditor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type {
  Camera,
  CreateCameraInput,
  UpdateCameraInput,
} from "@/hooks/use-cameras";

type Point = [number, number];
type BrowserDeliveryProfile = "native" | "1080p15" | "720p10" | "540p5";

export type SiteOption = { id: string; name: string };
export type ModelOption = { id: string; name: string; version: string };

export type CameraWizardData = {
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
  browserDeliveryProfile: BrowserDeliveryProfile;
  homography: {
    src: Point[];
    dst: Point[];
    refDistanceM: number;
  };
};

const steps = [
  "Identity",
  "Models & Tracking",
  "Privacy, Processing & Delivery",
  "Calibration",
  "Review",
] as const;

function toPointTupleArray(points: number[][] | undefined): Point[] {
  if (!points) {
    return [];
  }

  return points
    .filter((point): point is [number, number] => point.length === 2)
    .map((point) => [point[0], point[1]]);
}

function createDefaultData(initialCamera?: Camera | null): CameraWizardData {
  return {
    name: initialCamera?.name ?? "",
    siteId: initialCamera?.site_id ?? "",
    processingMode: initialCamera?.processing_mode ?? "central",
    rtspUrl: "",
    primaryModelId: initialCamera?.primary_model_id ?? "",
    secondaryModelId: initialCamera?.secondary_model_id ?? "",
    trackerType: initialCamera?.tracker_type ?? "botsort",
    blurFaces: initialCamera?.privacy.blur_faces ?? true,
    blurPlates: initialCamera?.privacy.blur_plates ?? true,
    method: initialCamera?.privacy.method ?? "gaussian",
    strength: initialCamera?.privacy.strength ?? 7,
    frameSkip: initialCamera?.frame_skip ?? 1,
    fpsCap: initialCamera?.fps_cap ?? 25,
    browserDeliveryProfile:
      initialCamera?.browser_delivery?.default_profile ?? "720p10",
    homography: {
      src: toPointTupleArray(initialCamera?.homography.src),
      dst: toPointTupleArray(initialCamera?.homography.dst),
      refDistanceM: initialCamera?.homography.ref_distance_m ?? 0,
    },
  };
}

function buildBrowserDelivery(defaultProfile: BrowserDeliveryProfile) {
  return {
    default_profile: defaultProfile,
    allow_native_on_demand: true,
    profiles: [
      { id: "native", kind: "passthrough" },
      { id: "1080p15", kind: "transcode", w: 1920, h: 1080, fps: 15 },
      { id: "720p10", kind: "transcode", w: 1280, h: 720, fps: 10 },
      { id: "540p5", kind: "transcode", w: 960, h: 540, fps: 5 },
    ],
  };
}

function toCreatePayload(data: CameraWizardData): CreateCameraInput {
  return {
    site_id: data.siteId,
    name: data.name.trim(),
    rtsp_url: data.rtspUrl.trim(),
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
    browser_delivery: buildBrowserDelivery(data.browserDeliveryProfile),
    frame_skip: data.frameSkip,
    fps_cap: data.fpsCap,
  };
}

function toUpdatePayload(data: CameraWizardData): UpdateCameraInput {
  const payload: UpdateCameraInput = {
    site_id: data.siteId,
    name: data.name.trim(),
    processing_mode: data.processingMode,
    primary_model_id: data.primaryModelId,
    secondary_model_id: data.secondaryModelId || null,
    tracker_type: data.trackerType,
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
    browser_delivery: buildBrowserDelivery(data.browserDeliveryProfile),
    frame_skip: data.frameSkip,
    fps_cap: data.fpsCap,
  };

  if (data.rtspUrl.trim()) {
    payload.rtsp_url = data.rtspUrl.trim();
  }

  return payload;
}

export function CameraWizard({
  sites,
  models,
  onSubmit,
  initialCamera = null,
  rtspUrlPlaceholder,
}: {
  sites: SiteOption[];
  models: ModelOption[];
  onSubmit?: (payload: CreateCameraInput | UpdateCameraInput) => Promise<void>;
  initialCamera?: Camera | null;
  rtspUrlPlaceholder?: string;
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [data, setData] = useState<CameraWizardData>(() => createDefaultData(initialCamera));

  const isEditMode = initialCamera !== null;
  const maskedRtspPlaceholder = rtspUrlPlaceholder ?? initialCamera?.rtsp_url_masked ?? "";
  const stepTitle = steps[stepIndex];

  useEffect(() => {
    setData(createDefaultData(initialCamera));
    setStepIndex(0);
    setError(null);
    setSubmitError(null);
    setIsSubmitting(false);
  }, [initialCamera]);

  const siteName = useMemo(
    () => sites.find((site) => site.id === data.siteId)?.name ?? "Unassigned site",
    [data.siteId, sites],
  );

  const contextPanel = useMemo(() => {
    switch (stepTitle) {
      case "Identity":
        return "Choose the fleet location, processing posture, and ingest stream Argus should bind to this camera.";
      case "Models & Tracking":
        return "Primary and secondary models shape what the camera observes, while the tracker stabilizes entity identity across frames.";
      case "Privacy, Processing & Delivery":
        return "Analytics ingest remains native. Lower browser delivery profiles may activate an optional preview/transcode path to reduce bandwidth without changing inference quality.";
      case "Calibration":
        return "Calibrate four source points, four destination points, and a real-world distance so Argus can map image motion into the physical scene.";
      case "Review":
        return "Confirm the camera configuration before Argus saves it. RTSP stays masked unless you explicitly replace it.";
      default:
        return "Configuration guidance appears here.";
    }
  }, [stepTitle]);

  function updateData<Key extends keyof CameraWizardData>(
    key: Key,
    value: CameraWizardData[Key],
  ) {
    setData((current) => ({ ...current, [key]: value }));
  }

  function updateNumericField<Key extends "strength" | "frameSkip" | "fpsCap">(
    key: Key,
    value: string,
  ) {
    const parsed = Number(value);
    updateData(key, Number.isFinite(parsed) ? parsed : 0);
  }

  function validateCurrentStep() {
    if (stepTitle === "Identity") {
      if (!data.name.trim()) {
        return "Camera name is required.";
      }
      if (!data.siteId) {
        return "Site is required.";
      }
      if (!isEditMode || !maskedRtspPlaceholder) {
        if (!data.rtspUrl.trim()) {
          return "RTSP URL is required.";
        }
      }
    }

    if (stepTitle === "Models & Tracking") {
      if (!data.primaryModelId) {
        return "Primary model is required.";
      }
      if (!data.trackerType) {
        return "Tracker type is required.";
      }
    }

    if (stepTitle === "Privacy, Processing & Delivery") {
      if (!data.browserDeliveryProfile) {
        return "Browser delivery profile is required.";
      }
      if (data.strength < 1 || data.strength > 100) {
        return "Strength must be between 1 and 100.";
      }
      if (data.frameSkip < 1) {
        return "Frame skip must be at least 1.";
      }
      if (data.fpsCap < 1) {
        return "FPS cap must be at least 1.";
      }
    }

    if (stepTitle === "Calibration") {
      if (data.homography.src.length !== 4) {
        return "4 source points are required.";
      }
      if (data.homography.dst.length !== 4) {
        return "4 destination points are required.";
      }
      if (data.homography.refDistanceM <= 0) {
        return "Reference distance is required.";
      }
    }

    return null;
  }

  async function handlePrimaryAction() {
    const validationError = validateCurrentStep();

    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setSubmitError(null);

    if (stepIndex < steps.length - 1) {
      setStepIndex((current) => current + 1);
      return;
    }

    if (!onSubmit) {
      return;
    }

    setIsSubmitting(true);

    try {
      if (isEditMode) {
        await onSubmit(toUpdatePayload(data));
      } else {
        await onSubmit(toCreatePayload(data));
      }
    } catch (submitFailure) {
      const fallback = isEditMode
        ? "Unable to update camera. Check the values and try again."
        : "Unable to create camera. Check the values and try again.";
      setSubmitError(
        submitFailure instanceof Error && submitFailure.message
          ? submitFailure.message
          : fallback,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleBack() {
    setError(null);
    setSubmitError(null);
    setStepIndex((current) => Math.max(0, current - 1));
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="overflow-hidden rounded-[1.85rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.95),rgba(8,11,18,0.92))] shadow-[0_24px_72px_-54px_rgba(0,0,0,0.9)]">
        <div className="border-b border-white/8 px-6 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
            {isEditMode ? "Edit camera" : "Camera setup"}
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
            {stepTitle}
          </h2>
          <p className="mt-2 text-sm text-[#8ea4c7]">
            Step {stepIndex + 1} of {steps.length}
          </p>
        </div>

        <div className="space-y-4 px-6 py-6">
          {stepTitle === "Identity" ? (
            <>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Camera name</span>
                <Input
                  aria-label="Camera name"
                  value={data.name}
                  onChange={(event) => updateData("name", event.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Site</span>
                <Select
                  aria-label="Site"
                  value={data.siteId}
                  onChange={(event) => updateData("siteId", event.target.value)}
                >
                  <option value="">Select a site</option>
                  {sites.map((site) => (
                    <option key={site.id} value={site.id}>
                      {site.name}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Processing mode</span>
                <Select
                  aria-label="Processing mode"
                  value={data.processingMode}
                  onChange={(event) =>
                    updateData(
                      "processingMode",
                      event.target.value as CameraWizardData["processingMode"],
                    )
                  }
                >
                  <option value="central">central</option>
                  <option value="edge">edge</option>
                  <option value="hybrid">hybrid</option>
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>RTSP URL</span>
                <Input
                  aria-label="RTSP URL"
                  placeholder={maskedRtspPlaceholder || "rtsp://camera.local/live"}
                  value={data.rtspUrl}
                  onChange={(event) => updateData("rtspUrl", event.target.value)}
                />
              </label>
              {isEditMode ? (
                <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                  Argus keeps the stored RTSP address masked. Leave this field empty to
                  retain the current stream, or enter a new URL to replace it.
                </p>
              ) : null}
            </>
          ) : null}

          {stepTitle === "Models & Tracking" ? (
            <>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Primary model</span>
                <Select
                  aria-label="Primary model"
                  value={data.primaryModelId}
                  onChange={(event) => updateData("primaryModelId", event.target.value)}
                >
                  <option value="">Select a model</option>
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} {model.version}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Secondary model</span>
                <Select
                  aria-label="Secondary model"
                  value={data.secondaryModelId}
                  onChange={(event) => updateData("secondaryModelId", event.target.value)}
                >
                  <option value="">None</option>
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} {model.version}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Tracker type</span>
                <Select
                  aria-label="Tracker type"
                  value={data.trackerType}
                  onChange={(event) =>
                    updateData(
                      "trackerType",
                      event.target.value as CameraWizardData["trackerType"],
                    )
                  }
                >
                  <option value="botsort">botsort</option>
                  <option value="bytetrack">bytetrack</option>
                  <option value="ocsort">ocsort</option>
                </Select>
              </label>
            </>
          ) : null}

          {stepTitle === "Privacy, Processing & Delivery" ? (
            <>
              <label className="flex items-center gap-3 text-sm text-[#d8e2f2]">
                <input
                  checked={data.blurFaces}
                  type="checkbox"
                  onChange={(event) => updateData("blurFaces", event.target.checked)}
                />
                <span>Blur faces</span>
              </label>
              <label className="flex items-center gap-3 text-sm text-[#d8e2f2]">
                <input
                  checked={data.blurPlates}
                  type="checkbox"
                  onChange={(event) => updateData("blurPlates", event.target.checked)}
                />
                <span>Blur plates</span>
              </label>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Method</span>
                <Select
                  aria-label="Method"
                  value={data.method}
                  onChange={(event) =>
                    updateData("method", event.target.value as CameraWizardData["method"])
                  }
                >
                  <option value="gaussian">gaussian</option>
                  <option value="pixelate">pixelate</option>
                </Select>
              </label>
              <div className="grid gap-4 sm:grid-cols-3">
                <label className="grid gap-2 text-sm text-[#d8e2f2]">
                  <span>Strength</span>
                  <Input
                    aria-label="Strength"
                    min={1}
                    type="number"
                    value={data.strength}
                    onChange={(event) => updateNumericField("strength", event.target.value)}
                  />
                </label>
                <label className="grid gap-2 text-sm text-[#d8e2f2]">
                  <span>Frame skip</span>
                  <Input
                    aria-label="Frame skip"
                    min={1}
                    type="number"
                    value={data.frameSkip}
                    onChange={(event) => updateNumericField("frameSkip", event.target.value)}
                  />
                </label>
                <label className="grid gap-2 text-sm text-[#d8e2f2]">
                  <span>FPS cap</span>
                  <Input
                    aria-label="FPS cap"
                    min={1}
                    type="number"
                    value={data.fpsCap}
                    onChange={(event) => updateNumericField("fpsCap", event.target.value)}
                  />
                </label>
              </div>
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Browser delivery profile</span>
                <Select
                  aria-label="Browser delivery profile"
                  value={data.browserDeliveryProfile}
                  onChange={(event) =>
                    updateData(
                      "browserDeliveryProfile",
                      event.target.value as BrowserDeliveryProfile,
                    )
                  }
                >
                  <option value="native">native</option>
                  <option value="1080p15">1080p15</option>
                  <option value="720p10">720p10</option>
                  <option value="540p5">540p5</option>
                </Select>
              </label>
              <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                Analytics ingest stays native. Lower browser delivery profiles may use
                an optional preview/transcode path to reduce bandwidth while operator
                playback remains smooth.
              </p>
            </>
          ) : null}

          {stepTitle === "Calibration" ? (
            <HomographyEditor
              src={data.homography.src}
              dst={data.homography.dst}
              refDistanceM={data.homography.refDistanceM}
              onChange={(homography) => updateData("homography", homography)}
            />
          ) : null}

          {stepTitle === "Review" ? (
            <CameraStepSummary
              data={{
                name: data.name || "Pending name",
                siteName,
                processingMode: data.processingMode,
                trackerType: data.trackerType,
                blurFaces: data.blurFaces,
                blurPlates: data.blurPlates,
                browserDeliveryProfile: data.browserDeliveryProfile,
                frameSkip: data.frameSkip,
                fpsCap: data.fpsCap,
                rtspUrlMasked: data.rtspUrl.trim()
                  ? "rtsp://replacement configured"
                  : maskedRtspPlaceholder || "not set",
              }}
            />
          ) : null}

          {error ? <p className="text-sm font-medium text-[#ff9ca6]">{error}</p> : null}
          {submitError ? (
            <p className="text-sm font-medium text-[#ff9ca6]">{submitError}</p>
          ) : null}
          <div className="flex justify-between gap-3 pt-4">
            <Button
              className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
              disabled={stepIndex === 0 || isSubmitting}
              onClick={handleBack}
            >
              Back
            </Button>
            <Button disabled={isSubmitting} onClick={() => void handlePrimaryAction()}>
              {isSubmitting
                ? isEditMode
                  ? "Saving..."
                  : "Creating..."
                : stepIndex === steps.length - 1
                  ? isEditMode
                    ? "Save camera"
                    : "Create camera"
                  : "Next"}
            </Button>
          </div>
        </div>
      </div>

      <aside className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(11,16,26,0.96),rgba(7,10,17,0.94))] shadow-[0_24px_70px_-48px_rgba(0,0,0,0.92)]">
        <div className="border-b border-white/8 px-5 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8ea4c7]">
            Step context
          </p>
          <h3 className="mt-3 text-xl font-semibold text-[#f4f8ff]">{stepTitle}</h3>
        </div>
        <div className="space-y-4 px-5 py-5 text-sm text-[#d8e2f2]">
          <p>{contextPanel}</p>
          <div className="space-y-2">
            {steps.map((step, index) => (
              <div
                key={step}
                className={`rounded-[1.1rem] border px-4 py-3 ${
                  index === stepIndex
                    ? "border-[#36507d] bg-[#0f1827] text-[#f4f8ff]"
                    : "border-white/8 bg-white/[0.03] text-[#9eb2cf]"
                }`}
              >
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em]">
                  Step {index + 1}
                </span>
                <p className="mt-2 text-sm">{step}</p>
              </div>
            ))}
          </div>
          {stepTitle === "Review" ? (
            <p className="rounded-[1.15rem] border border-[#2a456d] bg-[#0d1725] px-4 py-3 text-sm text-[#a7b8d4]">
              Native ingest stays untouched for inference quality. The selected browser
              delivery profile becomes the operator-facing default for later live views.
            </p>
          ) : null}
        </div>
      </aside>
    </section>
  );
}
