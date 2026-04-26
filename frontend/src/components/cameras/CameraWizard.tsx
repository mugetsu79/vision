import { useEffect, useMemo, useState } from "react";

import { productBrand } from "@/brand/product";
import { BoundaryAuthoringCanvas } from "@/components/cameras/BoundaryAuthoringCanvas";
import { CameraStepSummary } from "@/components/cameras/CameraStepSummary";
import { HomographyEditor } from "@/components/cameras/HomographyEditor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useCameraSetupPreview } from "@/hooks/use-camera-setup-preview";
import type {
  Camera,
  CreateCameraInput,
  UpdateCameraInput,
} from "@/hooks/use-cameras";
import type { FrameSize } from "@/components/cameras/boundary-geometry";
import { denormalizePointList, normalizePointList } from "@/components/cameras/boundary-geometry";

type Point = [number, number];
type BrowserDeliveryProfile = "native" | "1080p15" | "720p10" | "540p5";
type BoundaryType = "line" | "polygon";

type BoundaryDraft = {
  id: string;
  type: BoundaryType;
  classNames: string;
  points: Point[];
  frameSize: FrameSize | null;
};

const DEFAULT_ANALYTICS_FRAME_SIZE: FrameSize = {
  width: 1280,
  height: 720,
};

export type SiteOption = { id: string; name: string };
export type ModelOption = { id: string; name: string; version: string; classes: string[] };

export type CameraWizardData = {
  name: string;
  siteId: string;
  processingMode: "central" | "edge" | "hybrid";
  rtspUrl: string;
  primaryModelId: string;
  secondaryModelId: string;
  activeClasses: string[];
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
  zones: BoundaryDraft[];
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
    activeClasses: initialCamera?.active_classes ? [...initialCamera.active_classes] : [],
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
    zones: boundaryDraftsFromZones(initialCamera?.zones),
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

function createLineBoundaryDraft(): BoundaryDraft {
  return {
    id: "",
    type: "line",
    classNames: "",
    points: [],
    frameSize: null,
  };
}

function createPolygonBoundaryDraft(): BoundaryDraft {
  return {
    id: "",
    type: "polygon",
    classNames: "",
    points: [],
    frameSize: null,
  };
}

function boundaryDraftsFromZones(
  zones: Array<Record<string, unknown>> | undefined,
  fallbackFrameSize: FrameSize = DEFAULT_ANALYTICS_FRAME_SIZE,
): BoundaryDraft[] {
  if (!zones) {
    return [];
  }

  return zones.reduce<BoundaryDraft[]>((drafts, zone) => {
    const zoneId = typeof zone.id === "string" ? zone.id : "";
    const boundaryType = typeof zone.type === "string" ? zone.type.toLowerCase() : undefined;
    const frameSize = parseFrameSize(zone.frame_size) ?? fallbackFrameSize;
    const normalizedGeometry = parseNormalizedPoints(zone.points_normalized);

    if (boundaryType === "line" && Array.isArray(zone.points) && zone.points.length === 2) {
      const parsedPoints = toPointTupleArray(zone.points as number[][] | undefined);
      const points =
        normalizedGeometry.length === 2
          ? denormalizePointList(normalizedGeometry, frameSize)
          : parsedPoints;
      if (points.length === 2) {
        drafts.push({
          id: zoneId,
          type: "line",
          classNames: Array.isArray(zone.class_names)
            ? zone.class_names
                .filter((value): value is string => typeof value === "string")
                .join(",")
            : "",
          points,
          frameSize,
        });
        return drafts;
      }
    }

    if (Array.isArray(zone.polygon)) {
      const parsedPolygon = toPointTupleArray(zone.polygon as number[][] | undefined);
      const polygon =
        normalizedGeometry.length >= 3
          ? denormalizePointList(normalizedGeometry, frameSize)
          : parsedPolygon;
      if (polygon.length >= 3) {
        drafts.push({
          id: zoneId,
          type: "polygon",
          classNames: Array.isArray(zone.class_names)
            ? zone.class_names
                .filter((value): value is string => typeof value === "string")
                .join(",")
            : "",
          points: polygon,
          frameSize,
        });
      }
    }

    return drafts;
  }, []);
}

function parseBoundaryClassNames(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function formatPolygonText(points: Point[]): string {
  return points.map((point) => `${point[0]},${point[1]}`).join("\n");
}

function parseFrameSize(value: unknown): FrameSize | null {
  if (
    typeof value !== "object" ||
    value === null ||
    !("width" in value) ||
    !("height" in value)
  ) {
    return null;
  }

  const width = Number((value as { width: unknown }).width);
  const height = Number((value as { height: unknown }).height);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return null;
  }

  return {
    width,
    height,
  };
}

function parseNormalizedPoints(value: unknown): ReadonlyArray<readonly [number, number]> {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(
      (point): point is [number, number] =>
        Array.isArray(point) &&
        point.length === 2 &&
        typeof point[0] === "number" &&
        typeof point[1] === "number",
    )
    .map((point) => [point[0], point[1]] as const);
}

function boundaryPointsForFrame(boundary: BoundaryDraft, frameSize: FrameSize): Point[] {
  const sourceFrameSize = boundary.frameSize ?? frameSize;
  const normalizedPoints = normalizePointList(boundary.points, sourceFrameSize);
  return denormalizePointList(normalizedPoints, frameSize);
}

function serializeZones(
  boundaries: BoundaryDraft[],
  setupFrameSize: FrameSize,
): Array<Record<string, unknown>> {
  return boundaries.map((boundary, index) => {
    const zoneId = boundary.id.trim();
    if (!zoneId) {
      throw new Error(`Boundary ${index + 1} requires an id.`);
    }

    const points = boundaryPointsForFrame(boundary, setupFrameSize);

    if (boundary.type === "line") {
      if (boundary.points.length !== 2) {
        throw new Error(`Boundary ${index + 1} requires two numeric points.`);
      }
      return {
        id: zoneId,
        type: "line",
        points,
        class_names: parseBoundaryClassNames(boundary.classNames),
        frame_size: setupFrameSize,
      };
    }

    if (boundary.points.length < 3) {
      throw new Error(`Boundary ${index + 1} requires at least three polygon points.`);
    }
    return {
      id: zoneId,
      type: "polygon",
      polygon: points,
      frame_size: setupFrameSize,
    };
  });
}

function validateZoneBoundaries(boundaries: BoundaryDraft[]): string | null {
  for (const [index, boundary] of boundaries.entries()) {
    if (!boundary.id.trim()) {
      return `Boundary ${index + 1} requires an id.`;
    }
    if (boundary.type === "line") {
      if (boundary.points.length !== 2) {
        return `Boundary ${index + 1} requires two numeric points.`;
      }
      continue;
    }
    if (boundary.points.length < 3) {
      return `Boundary ${index + 1} requires at least three polygon points in x,y format.`;
    }
  }
  return null;
}

function summarizeBoundaries(boundaries: BoundaryDraft[]): string {
  if (boundaries.length === 0) {
    return "None configured";
  }
  return boundaries
    .map((boundary, index) => {
      const boundaryName = boundary.id.trim() || `Boundary ${index + 1}`;
      const classScope =
        boundary.type === "line"
          ? boundary.classNames.trim() || "all tracked classes"
          : "all tracked classes";
      return `${boundaryName} · ${boundary.type} · ${classScope}`;
    })
    .join(" | ");
}

function pruneActiveClasses(activeClasses: string[], allowedClasses: string[]) {
  if (allowedClasses.length === 0) {
    return [];
  }

  const allowed = new Set(allowedClasses);

  return activeClasses.filter((className) => allowed.has(className));
}

function areStringArraysEqual(left: string[], right: string[]) {
  if (left.length !== right.length) {
    return false;
  }

  return left.every((item, index) => item === right[index]);
}

function toCreatePayload(
  data: CameraWizardData,
  setupFrameSize: FrameSize,
): CreateCameraInput {
  return {
    site_id: data.siteId,
    name: data.name.trim(),
    rtsp_url: data.rtspUrl.trim(),
    processing_mode: data.processingMode,
    primary_model_id: data.primaryModelId,
    secondary_model_id: data.secondaryModelId || null,
    tracker_type: data.trackerType,
    active_classes: data.activeClasses,
    attribute_rules: [],
    zones: serializeZones(data.zones, setupFrameSize),
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

function toUpdatePayload(
  data: CameraWizardData,
  setupFrameSize: FrameSize,
): UpdateCameraInput {
  const payload: UpdateCameraInput = {
    site_id: data.siteId,
    name: data.name.trim(),
    processing_mode: data.processingMode,
    primary_model_id: data.primaryModelId,
    secondary_model_id: data.secondaryModelId || null,
    tracker_type: data.trackerType,
    active_classes: data.activeClasses,
    zones: serializeZones(data.zones, setupFrameSize),
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
  modelsLoading = false,
  modelsError = null,
  onRetryModels,
  onSubmit,
  initialCamera = null,
  rtspUrlPlaceholder,
}: {
  sites: SiteOption[];
  models: ModelOption[];
  modelsLoading?: boolean;
  modelsError?: string | null;
  onRetryModels?: () => void;
  onSubmit?: (payload: CreateCameraInput | UpdateCameraInput) => Promise<void>;
  initialCamera?: Camera | null;
  rtspUrlPlaceholder?: string;
}) {
  const brandName = productBrand.name;
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showBoundaryAdvanced, setShowBoundaryAdvanced] = useState(false);
  const [data, setData] = useState<CameraWizardData>(() => createDefaultData(initialCamera));

  const isEditMode = initialCamera !== null;
  const maskedRtspPlaceholder = rtspUrlPlaceholder ?? initialCamera?.rtsp_url_masked ?? "";
  const stepTitle = steps[stepIndex];
  const setupPreviewQuery = useCameraSetupPreview(
    initialCamera?.id,
    isEditMode && stepTitle === "Calibration",
  );
  const selectedPrimaryModel = useMemo(
    () => models.find((model) => model.id === data.primaryModelId) ?? null,
    [data.primaryModelId, models],
  );
  const selectedPrimaryModelClasses = useMemo(
    () => selectedPrimaryModel?.classes ?? [],
    [selectedPrimaryModel],
  );
  const selectedPrimaryModelClassesKey = selectedPrimaryModelClasses.join("\u0000");

  useEffect(() => {
    setData(createDefaultData(initialCamera));
    setStepIndex(0);
    setError(null);
    setSubmitError(null);
    setIsSubmitting(false);
    setShowBoundaryAdvanced(false);
  }, [initialCamera]);

  useEffect(() => {
    setData((current) => {
      if (!selectedPrimaryModel) {
        if (modelsLoading || modelsError || models.length === 0) {
          return current;
        }

        if (current.activeClasses.length === 0) {
          return current;
        }

        return {
          ...current,
          activeClasses: [],
        };
      }

      const nextActiveClasses = pruneActiveClasses(
        current.activeClasses,
        selectedPrimaryModelClasses,
      );

      if (areStringArraysEqual(current.activeClasses, nextActiveClasses)) {
        return current;
      }

      return {
        ...current,
        activeClasses: nextActiveClasses,
      };
    });
  }, [
    models.length,
    modelsError,
    modelsLoading,
    selectedPrimaryModel,
    selectedPrimaryModelClasses,
    selectedPrimaryModelClassesKey,
  ]);

  const siteName = useMemo(
    () => sites.find((site) => site.id === data.siteId)?.name ?? "Unassigned site",
    [data.siteId, sites],
  );
  const fallbackSetupFrameSize = useMemo(
    () => data.zones.find((boundary) => boundary.frameSize)?.frameSize ?? DEFAULT_ANALYTICS_FRAME_SIZE,
    [data.zones],
  );
  const setupFrameSize = setupPreviewQuery.data?.frame_size ?? fallbackSetupFrameSize;
  const setupPreviewSrc = setupPreviewQuery.data?.preview_src ?? null;
  const setupFrameStatus = useMemo(() => {
    if (setupPreviewQuery.data) {
      const capturedAt = new Date(setupPreviewQuery.data.captured_at);
      const capturedLabel = Number.isNaN(capturedAt.getTime())
        ? setupPreviewQuery.data.captured_at
        : capturedAt.toLocaleString();
      return `Analytics frame: ${setupFrameSize.width}×${setupFrameSize.height} · Still captured ${capturedLabel}`;
    }
    if (isEditMode && stepTitle === "Calibration" && setupPreviewQuery.isPending) {
      return "Loading analytics frame metadata…";
    }
    if (isEditMode && stepTitle === "Calibration" && setupPreviewQuery.isError) {
      return `Using fallback authoring plane ${setupFrameSize.width}×${setupFrameSize.height} while preview metadata is unavailable.`;
    }
    if (isEditMode) {
      return `Analytics frame: ${setupFrameSize.width}×${setupFrameSize.height}`;
    }
    return `Using a provisional ${setupFrameSize.width}×${setupFrameSize.height} authoring plane until the camera is saved and preview metadata is available.`;
  }, [
    isEditMode,
    setupFrameSize.height,
    setupFrameSize.width,
    setupPreviewQuery.data,
    setupPreviewQuery.isError,
    setupPreviewQuery.isPending,
    stepTitle,
  ]);

  const contextPanel = useMemo(() => {
    switch (stepTitle) {
      case "Identity":
        return `Choose the fleet location, processing posture, and ingest stream ${brandName} should bind to this camera.`;
      case "Models & Tracking":
        return "Primary and secondary models shape what the camera observes, while the tracker stabilizes entity identity across frames.";
      case "Privacy, Processing & Delivery":
        return "Analytics ingest remains native. Lower browser delivery profiles may activate an optional preview/transcode path to reduce bandwidth without changing inference quality.";
      case "Calibration":
        return `Calibrate four source points, four destination points, a real-world distance, and any line or polygon boundaries so ${brandName} can map motion and count events inside the physical scene.`;
      case "Review":
        return `Confirm the camera configuration before ${brandName} saves it. RTSP stays masked unless you explicitly replace it.`;
      default:
        return "Configuration guidance appears here.";
    }
  }, [brandName, stepTitle]);

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
      if (modelsLoading) {
        return "Models are still loading. Wait for the list to finish updating.";
      }
      if (modelsError) {
        return "Models failed to load. Retry the model lookup and try again.";
      }
      if (models.length === 0) {
        return "No models are available yet. Register or refresh models before continuing.";
      }
      if (!data.primaryModelId) {
        return "Primary model is required.";
      }
      if (!selectedPrimaryModel) {
        return "Primary model must be selected from the current inventory.";
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
      const boundaryError = validateZoneBoundaries(data.zones);
      if (boundaryError) {
        return boundaryError;
      }
    }

    return null;
  }

  function toggleActiveClass(className: string, checked: boolean) {
    setData((current) => {
      const nextActiveClasses = checked
        ? current.activeClasses.includes(className)
          ? current.activeClasses
          : [...current.activeClasses, className]
        : current.activeClasses.filter((item) => item !== className);

      return {
        ...current,
        activeClasses: nextActiveClasses,
      };
    });
  }

  function addBoundary(type: BoundaryType) {
    setData((current) => ({
      ...current,
      zones: [...current.zones, type === "line" ? createLineBoundaryDraft() : createPolygonBoundaryDraft()],
    }));
  }

  function updateBoundary(index: number, patch: Partial<BoundaryDraft>) {
    setData((current) => ({
      ...current,
      zones: current.zones.map((boundary, boundaryIndex) =>
        boundaryIndex === index ? { ...boundary, ...patch } : boundary,
      ),
    }));
  }

  function removeBoundary(index: number) {
    setData((current) => ({
      ...current,
      zones: current.zones.filter((_, boundaryIndex) => boundaryIndex !== index),
    }));
  }

  function clearBoundaryPoints(index: number) {
    updateBoundary(index, { points: [] });
  }

  function updateBoundaryFromCanvas(
    index: number,
    pointsNormalized: ReadonlyArray<readonly [number, number]>,
  ) {
    updateBoundary(index, {
      points: denormalizePointList(pointsNormalized, setupFrameSize),
      frameSize: setupFrameSize,
    });
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
        await onSubmit(toUpdatePayload(data, setupFrameSize));
      } else {
        await onSubmit(toCreatePayload(data, setupFrameSize));
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
                  {brandName} keeps the stored RTSP address masked. Leave this field empty to
                  retain the current stream, or enter a new URL to replace it.
                </p>
              ) : null}
            </>
          ) : null}

          {stepTitle === "Models & Tracking" ? (
            <>
              {modelsLoading ? (
                <div className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                  Loading the latest registered models...
                </div>
              ) : null}

              {modelsError ? (
                <div className="rounded-[1.15rem] border border-[#5a2330] bg-[#241118] px-4 py-3 text-sm text-[#ffc2cd]">
                  <p>{modelsError}</p>
                  {onRetryModels ? (
                    <button
                      className="mt-3 rounded-full border border-[#7b3142] bg-[#311722] px-3 py-1.5 text-xs font-medium text-[#ffe1e7] transition hover:bg-[#3b1b28]"
                      type="button"
                      onClick={onRetryModels}
                    >
                      Retry model lookup
                    </button>
                  ) : null}
                </div>
              ) : null}

              {!modelsLoading && !modelsError && models.length === 0 ? (
                <div className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                  <p>No models are available yet. Register a model, then refresh this step.</p>
                  {onRetryModels ? (
                    <button
                      className="mt-3 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                      type="button"
                      onClick={onRetryModels}
                    >
                      Refresh models
                    </button>
                  ) : null}
                </div>
              ) : null}

              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Primary model</span>
                <Select
                  aria-label="Primary model"
                  disabled={modelsLoading || Boolean(modelsError) || models.length === 0}
                  value={data.primaryModelId}
                  onChange={(event) => {
                    const nextPrimaryModelId = event.target.value;
                    const nextPrimaryModel =
                      models.find((model) => model.id === nextPrimaryModelId) ?? null;

                    setData((current) => ({
                      ...current,
                      primaryModelId: nextPrimaryModelId,
                      activeClasses: pruneActiveClasses(
                        current.activeClasses,
                        nextPrimaryModel?.classes ?? [],
                      ),
                    }));
                  }}
                >
                  <option value="">Select a model</option>
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} {model.version}
                    </option>
                  ))}
                </Select>
              </label>
              {selectedPrimaryModel ? (
                <div className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-[#eef4ff]">Active class scope</p>
                      <p className="mt-1 text-sm text-[#9eb2cf]">
                        Leave every class unchecked to keep the full primary model inventory
                        active for this camera.
                      </p>
                    </div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8ea4c7]">
                      {selectedPrimaryModelClasses.length} classes
                    </p>
                  </div>

                  {selectedPrimaryModelClasses.length > 0 ? (
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      {selectedPrimaryModelClasses.map((className) => (
                        <label
                          key={className}
                          className="flex items-start gap-3 rounded-[1rem] border border-white/8 bg-white/[0.03] px-3 py-2 text-sm text-[#d8e2f2]"
                        >
                          <input
                            checked={data.activeClasses.includes(className)}
                            type="checkbox"
                            onChange={(event) =>
                              toggleActiveClass(className, event.target.checked)
                            }
                          />
                          <span>{className}</span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-[#9eb2cf]">
                      This model does not expose class metadata, so there is nothing to narrow.
                    </p>
                  )}
                </div>
              ) : (
                <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                  Select a primary model to choose the persistent class scope for this camera.
                </p>
              )}
              <label className="grid gap-2 text-sm text-[#d8e2f2]">
                <span>Secondary model</span>
                <Select
                  aria-label="Secondary model"
                  disabled={modelsLoading || Boolean(modelsError) || models.length === 0}
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
            <div className="space-y-5">
              <HomographyEditor
                destinationFrameSize={DEFAULT_ANALYTICS_FRAME_SIZE}
                src={data.homography.src}
                dst={data.homography.dst}
                refDistanceM={data.homography.refDistanceM}
                sourceFrameSize={setupFrameSize}
                sourcePreviewSrc={setupPreviewSrc}
                onChange={(homography) => updateData("homography", homography)}
              />
              <section className="rounded-[1.5rem] border border-[#243853] bg-[#09121c] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
                      Count boundaries
                    </p>
                    <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">
                      Lines and zones
                    </h3>
                    <p className="mt-2 max-w-2xl text-sm text-[#9eb2cf]">
                      Freeze the analytics frame mentally around the live scene and draw
                      count boundaries directly on that plane. Lines emit crossings,
                      while polygons emit entry and exit events.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      className="bg-[#0d1717] text-[#dffbf3] shadow-none ring-1 ring-[#24594f] hover:bg-[#11201e]"
                      type="button"
                      onClick={() => setShowBoundaryAdvanced((current) => !current)}
                    >
                      {showBoundaryAdvanced ? "Hide advanced" : "Advanced"}
                    </Button>
                    {isEditMode ? (
                      <Button
                        className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
                        disabled={setupPreviewQuery.isPending}
                        type="button"
                        onClick={() => {
                          void setupPreviewQuery.refetch();
                        }}
                      >
                        {setupPreviewQuery.isPending ? "Refreshing still…" : "Refresh still"}
                      </Button>
                    ) : null}
                    <Button
                      className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
                      type="button"
                      onClick={() => addBoundary("line")}
                    >
                      Add line boundary
                    </Button>
                    <Button
                      className="bg-white/[0.06] text-[#eef4ff] shadow-none hover:bg-white/[0.1]"
                      type="button"
                      onClick={() => addBoundary("polygon")}
                    >
                      Add polygon zone
                    </Button>
                  </div>
                </div>
                <div className="mt-4 rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                  {setupFrameStatus}
                </div>

                {data.zones.length === 0 ? (
                  <p className="mt-4 rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                    No boundaries configured yet. Add a line for pass-by counting or a
                    polygon for entry/exit counting, then click directly on the setup
                    plane instead of typing raw coordinates.
                  </p>
                ) : (
                  <div className="mt-5 space-y-4">
                    {data.zones.map((boundary, index) => (
                      <section
                        key={`${boundary.type}-${index}`}
                        className="rounded-[1.2rem] border border-white/8 bg-white/[0.03] p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8ea4c7]">
                              Boundary {index + 1}
                            </p>
                            <p className="mt-2 text-sm text-[#d8e2f2]">
                              {boundary.type === "line" ? "Line crossing" : "Polygon zone"}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <button
                              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                              type="button"
                              onClick={() => clearBoundaryPoints(index)}
                            >
                              Clear shape
                            </button>
                            <button
                              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                              type="button"
                              onClick={() => removeBoundary(index)}
                            >
                              Remove
                            </button>
                          </div>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2">
                          <label className="grid gap-2 text-sm text-[#d8e2f2]">
                            <span>Boundary {index + 1} ID</span>
                            <Input
                              aria-label={`Boundary ${index + 1} ID`}
                              value={boundary.id}
                              onChange={(event) => updateBoundary(index, { id: event.target.value })}
                            />
                          </label>

                          {boundary.type === "line" ? (
                            <label className="grid gap-2 text-sm text-[#d8e2f2]">
                              <span>Boundary {index + 1} classes</span>
                              <Input
                                aria-label={`Boundary ${index + 1} classes`}
                                placeholder="person,car"
                                value={boundary.classNames}
                                onChange={(event) =>
                                  updateBoundary(index, { classNames: event.target.value })
                                }
                              />
                            </label>
                          ) : (
                            <div className="rounded-[1rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                              Polygon zones currently count all tracked classes that enter or exit them.
                            </div>
                          )}
                        </div>

                        <div className="mt-4">
                          <BoundaryAuthoringCanvas
                            ariaLabel={`Boundary ${index + 1} canvas`}
                            backgroundContent={
                              <p className="max-w-sm text-sm text-[#bcefe3]">
                                Click to place {boundary.type === "line" ? "two points" : "polygon vertices"}, then drag handles to refine them on the analytics plane.
                              </p>
                            }
                            frameSize={setupFrameSize}
                            helperText={
                              boundary.type === "line"
                                ? "Lines count side-to-side crossings. Start on one side of the path and end on the other."
                                : "Polygons count entries and exits whenever the tracked footpoint crosses the zone edge."
                            }
                            mode={boundary.type === "line" ? "line" : "polygon"}
                            pointLabelPrefix={`Boundary ${index + 1}`}
                            previewSrc={setupPreviewSrc}
                            value={normalizePointList(
                              boundaryPointsForFrame(boundary, setupFrameSize),
                              setupFrameSize,
                            )}
                            onChange={(pointsNormalized) =>
                              updateBoundaryFromCanvas(index, pointsNormalized)
                            }
                          />
                        </div>

                        {showBoundaryAdvanced ? (
                          boundary.type === "line" ? (
                            <div className="mt-4 grid gap-3 md:grid-cols-4">
                              {(() => {
                                const points = boundaryPointsForFrame(boundary, setupFrameSize);
                                const [first = [0, 0], second = [0, 0]] = points;
                                return [
                                  ["x1", first[0]],
                                  ["y1", first[1]],
                                  ["x2", second[0]],
                                  ["y2", second[1]],
                                ].map(([field, value]) => (
                                  <label key={field} className="grid gap-2 text-sm text-[#d8e2f2]">
                                    <span>Boundary {index + 1} {field}</span>
                                    <Input
                                      aria-label={`Boundary ${index + 1} ${field}`}
                                      readOnly
                                      value={String(value)}
                                    />
                                  </label>
                                ));
                              })()}
                            </div>
                          ) : (
                            <label className="mt-4 grid gap-2 text-sm text-[#d8e2f2]">
                              <span>Boundary {index + 1} polygon points</span>
                              <textarea
                                aria-label={`Boundary ${index + 1} polygon points`}
                                readOnly
                                className="min-h-32 w-full rounded-2xl border border-[color:var(--argus-border)] bg-[color:var(--argus-surface)] px-4 py-3 text-sm text-[var(--argus-text)] outline-none placeholder:text-[var(--argus-text-subtle)]"
                                value={formatPolygonText(boundaryPointsForFrame(boundary, setupFrameSize))}
                              />
                            </label>
                          )
                        ) : null}
                      </section>
                    ))}
                  </div>
                )}
              </section>
            </div>
          ) : null}

          {stepTitle === "Review" ? (
            <CameraStepSummary
              data={{
                name: data.name || "Pending name",
                siteName,
                processingMode: data.processingMode,
                activeClasses: data.activeClasses,
                trackerType: data.trackerType,
                blurFaces: data.blurFaces,
                blurPlates: data.blurPlates,
                browserDeliveryProfile: data.browserDeliveryProfile,
                frameSkip: data.frameSkip,
                fpsCap: data.fpsCap,
                boundarySummary: summarizeBoundaries(data.zones),
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
