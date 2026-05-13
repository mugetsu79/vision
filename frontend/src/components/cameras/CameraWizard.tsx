import { useEffect, useMemo, useState } from "react";

import { useQuery } from "@tanstack/react-query";

import { productBrand } from "@/brand/product";
import { BoundaryAuthoringCanvas } from "@/components/cameras/BoundaryAuthoringCanvas";
import { CameraStepSummary } from "@/components/cameras/CameraStepSummary";
import { HomographyEditor } from "@/components/cameras/HomographyEditor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { omniPlaceExamples } from "@/copy/omnisight";
import { useCameraSetupPreview } from "@/hooks/use-camera-setup-preview";
import type {
  Camera,
  CreateCameraInput,
  UpdateCameraInput,
} from "@/hooks/use-cameras";
import {
  useConfigurationProfiles,
  type OperatorConfigProfile,
} from "@/hooks/use-configuration";
import type { components } from "@/lib/api.generated";
import { resolveAccessToken, toApiError } from "@/lib/api";
import { frontendConfig } from "@/lib/config";
import type { FrameSize } from "@/components/cameras/boundary-geometry";
import { denormalizePointList, normalizePointList } from "@/components/cameras/boundary-geometry";

type Point = [number, number];
type SerializedZone = NonNullable<CreateCameraInput["zones"]>[number];
type SerializedDetectionRegion = NonNullable<CreateCameraInput["detection_regions"]>[number];
type DetectorCapability = components["schemas"]["DetectorCapability"];
type ModelCapabilityConfig = components["schemas"]["ModelCapabilityConfig"];
type RuntimeArtifact = components["schemas"]["RuntimeArtifactResponse"];
type SceneVisionProfile = components["schemas"]["SceneVisionProfile"];
type VisionComputeTier = SceneVisionProfile["compute_tier"];
type VisionAccuracyMode = SceneVisionProfile["accuracy_mode"];
type SceneDifficulty = SceneVisionProfile["scene_difficulty"];
type ObjectDomain = SceneVisionProfile["object_domain"];
type BrowserDeliveryProfile = "native" | "annotated" | "1080p15" | "720p10" | "540p5";
type CameraSourceKind = components["schemas"]["CameraSourceKind"];
type EvidenceRecordingPolicy = components["schemas"]["EvidenceRecordingPolicy"];
type EvidenceStorageProfile = EvidenceRecordingPolicy["storage_profile"];
type StreamDeliveryMode = NonNullable<
  NonNullable<CreateCameraInput["browser_delivery"]>["delivery_mode"]
>;
type BoundaryType = "line" | "polygon";
type DetectionRegionMode = SerializedDetectionRegion["mode"];
type BrowserDeliveryProfilePayload = {
  id: BrowserDeliveryProfile;
  kind: "passthrough" | "transcode";
  w?: number;
  h?: number;
  fps?: number;
  label?: string | null;
  description?: string | null;
  reason?: string | null;
  [key: string]: unknown;
};
type NativeDeliveryStatus = {
  available: boolean;
  reason?: string | null;
};
type SourceCapability = {
  width: number;
  height: number;
  fps?: number | null;
  codec?: string | null;
  aspect_ratio?: string | null;
};
type CameraSourceProbeResponse = {
  source_capability: SourceCapability | null;
  browser_delivery: {
    default_profile: BrowserDeliveryProfile;
    allow_native_on_demand: boolean;
    profiles?: { [key: string]: unknown }[];
    unsupported_profiles?: { [key: string]: unknown }[];
    native_status?: NativeDeliveryStatus;
  };
};

type BoundaryDraft = {
  id: string;
  type: BoundaryType;
  classNames: string;
  points: Point[];
  frameSize: FrameSize | null;
};

type DetectionRegionDraft = {
  id: string;
  mode: DetectionRegionMode;
  classNames: string;
  points: Point[];
  frameSize: FrameSize | null;
};

type VisionProfileDraft = {
  computeTier: VisionComputeTier;
  accuracyMode: VisionAccuracyMode;
  sceneDifficulty: SceneDifficulty;
  objectDomain: ObjectDomain;
  speedEnabled: boolean;
  candidateQuality: SceneVisionProfile["candidate_quality"];
  trackerProfile: SceneVisionProfile["tracker_profile"];
  verifierProfile: SceneVisionProfile["verifier_profile"];
};

const DEFAULT_ANALYTICS_FRAME_SIZE: FrameSize = {
  width: 1280,
  height: 720,
};

const DEFAULT_BROWSER_DELIVERY_PROFILES: BrowserDeliveryProfilePayload[] = [
  { id: "native", kind: "passthrough" },
  { id: "annotated", kind: "transcode" },
  { id: "1080p15", kind: "transcode", w: 1920, h: 1080, fps: 15 },
  { id: "720p10", kind: "transcode", w: 1280, h: 720, fps: 10 },
  { id: "540p5", kind: "transcode", w: 960, h: 540, fps: 5 },
];

export type SiteOption = { id: string; name: string };
export type ModelOption = {
  id: string;
  name: string;
  version: string;
  classes: string[];
  capability?: DetectorCapability;
  capability_config?: ModelCapabilityConfig;
  runtime_artifacts?: RuntimeArtifact[];
};

export type CameraWizardData = {
  name: string;
  siteId: string;
  edgeNodeId: string;
  sourceKind: Extract<CameraSourceKind, "rtsp" | "usb">;
  processingMode: "central" | "edge" | "hybrid";
  rtspUrl: string;
  usbUri: string;
  primaryModelId: string;
  secondaryModelId: string;
  activeClasses: string[];
  runtimeVocabulary: string[];
  runtimeVocabularyVersion: number;
  trackerType: "botsort" | "bytetrack" | "ocsort";
  blurFaces: boolean;
  blurPlates: boolean;
  method: "gaussian" | "pixelate";
  strength: number;
  frameSkip: number;
  fpsCap: number;
  browserDeliveryProfile: BrowserDeliveryProfile;
  browserDeliveryProfiles: BrowserDeliveryProfilePayload[];
  unsupportedBrowserDeliveryProfiles: BrowserDeliveryProfilePayload[];
  browserDeliveryNativeStatus: NativeDeliveryStatus;
  streamDeliveryProfileId: string;
  streamDeliveryMode: StreamDeliveryMode | null;
  streamDeliveryPublicBaseUrl: string | null;
  streamDeliveryEdgeOverrideUrl: string | null;
  sourceCapability: SourceCapability | null;
  recordingEnabled: boolean;
  recordingPreSeconds: number;
  recordingPostSeconds: number;
  recordingFps: number;
  recordingMaxDurationSeconds: number;
  recordingStorageProfile: EvidenceStorageProfile;
  recordingStorageProfileId: string;
  recordingSnapshotEnabled: boolean;
  recordingSnapshotOffsetSeconds: number;
  recordingSnapshotQuality: number;
  homography: {
    src: Point[];
    dst: Point[];
    refDistanceM: number;
  };
  visionProfile: VisionProfileDraft;
  zones: BoundaryDraft[];
  detectionRegions: DetectionRegionDraft[];
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

function isBrowserDeliveryProfile(value: unknown): value is BrowserDeliveryProfile {
  return (
    value === "native" ||
    value === "annotated" ||
    value === "1080p15" ||
    value === "720p10" ||
    value === "540p5"
  );
}

function normalizeBrowserDeliveryProfiles(
  profiles: { [key: string]: unknown }[] | undefined,
  fallback: BrowserDeliveryProfilePayload[] = DEFAULT_BROWSER_DELIVERY_PROFILES,
): BrowserDeliveryProfilePayload[] {
  if (!profiles || profiles.length === 0) {
    return fallback;
  }

  const normalized = profiles.flatMap((profile) => {
    if (!isBrowserDeliveryProfile(profile.id)) {
      return [];
    }
    return [
      {
        ...profile,
        id: profile.id,
        kind: profile.kind === "transcode" ? "transcode" : "passthrough",
      } satisfies BrowserDeliveryProfilePayload,
    ];
  });

  return normalized.length > 0 ? normalized : fallback;
}

function resolveBrowserDeliveryProfile(
  requestedProfile: BrowserDeliveryProfile,
  profiles: BrowserDeliveryProfilePayload[],
): BrowserDeliveryProfile {
  if (profiles.some((profile) => profile.id === requestedProfile)) {
    return requestedProfile;
  }
  return profiles.find((profile) => profile.id === "720p10")?.id ?? profiles[0]?.id ?? "native";
}

function nativeOnlyBrowserDeliveryProfiles(
  profiles: BrowserDeliveryProfilePayload[],
): BrowserDeliveryProfilePayload[] {
  const nativeProfile = profiles.find((profile) => profile.id === "native");
  return nativeProfile ? [nativeProfile] : [{ id: "native", kind: "passthrough" }];
}

function formatBrowserDeliveryProfileLabel(
  profile: BrowserDeliveryProfilePayload,
  processingMode: CameraWizardData["processingMode"],
) {
  if (profile.label) {
    return profile.label;
  }
  const isEdge = processingMode === "edge";
  if (profile.id === "native") {
    return isEdge ? "Native edge passthrough" : "Native camera";
  }
  if (profile.id === "annotated") {
    return isEdge ? "Annotated edge stream" : "Annotated";
  }
  return isEdge ? `${profile.id} edge bandwidth saver` : `${profile.id} viewer preview`;
}

function formatSourceSize(sourceCapability: SourceCapability | null) {
  if (!sourceCapability) {
    return null;
  }
  return `${sourceCapability.width}×${sourceCapability.height}`;
}

function createDefaultData(initialCamera?: Camera | null): CameraWizardData {
  const browserDeliveryProfiles = normalizeBrowserDeliveryProfiles(
    initialCamera?.browser_delivery?.profiles,
  );
  const unsupportedBrowserDeliveryProfiles = normalizeBrowserDeliveryProfiles(
    initialCamera?.browser_delivery?.unsupported_profiles,
    [],
  );
  const browserDeliveryProfile = resolveBrowserDeliveryProfile(
    initialCamera?.browser_delivery?.default_profile ?? "720p10",
    browserDeliveryProfiles,
  );
  const cameraSource = initialCamera?.camera_source;
  const sourceKind = cameraSource?.kind === "usb" ? "usb" : "rtsp";
  const recordingPolicy = initialCamera?.recording_policy;

  return {
    name: initialCamera?.name ?? "",
    siteId: initialCamera?.site_id ?? "",
    edgeNodeId: initialCamera?.edge_node_id ?? "",
    sourceKind,
    processingMode:
      sourceKind === "usb" ? "edge" : initialCamera?.processing_mode ?? "central",
    rtspUrl: "",
    usbUri: sourceKind === "usb" ? cameraSource?.uri ?? "usb:///dev/video0" : "usb:///dev/video0",
    primaryModelId: initialCamera?.primary_model_id ?? "",
    secondaryModelId: initialCamera?.secondary_model_id ?? "",
    activeClasses: initialCamera?.active_classes ? [...initialCamera.active_classes] : [],
    runtimeVocabulary: initialCamera?.runtime_vocabulary?.terms
      ? [...initialCamera.runtime_vocabulary.terms]
      : [],
    runtimeVocabularyVersion: initialCamera?.runtime_vocabulary?.version ?? 0,
    trackerType: initialCamera?.tracker_type ?? "botsort",
    blurFaces: initialCamera?.privacy.blur_faces ?? true,
    blurPlates: initialCamera?.privacy.blur_plates ?? true,
    method: initialCamera?.privacy.method ?? "gaussian",
    strength: initialCamera?.privacy.strength ?? 7,
    frameSkip: initialCamera?.frame_skip ?? 1,
    fpsCap: initialCamera?.fps_cap ?? 25,
    browserDeliveryProfile,
    browserDeliveryProfiles,
    unsupportedBrowserDeliveryProfiles,
    browserDeliveryNativeStatus:
      initialCamera?.browser_delivery?.native_status ?? { available: true, reason: null },
    streamDeliveryProfileId: initialCamera?.browser_delivery?.delivery_profile_id ?? "",
    streamDeliveryMode: initialCamera?.browser_delivery?.delivery_mode ?? null,
    streamDeliveryPublicBaseUrl: initialCamera?.browser_delivery?.public_base_url ?? null,
    streamDeliveryEdgeOverrideUrl: initialCamera?.browser_delivery?.edge_override_url ?? null,
    sourceCapability: initialCamera?.source_capability ?? null,
    recordingEnabled: recordingPolicy?.enabled ?? true,
    recordingPreSeconds: recordingPolicy?.pre_seconds ?? 4,
    recordingPostSeconds: recordingPolicy?.post_seconds ?? 8,
    recordingFps: recordingPolicy?.fps ?? 10,
    recordingMaxDurationSeconds: recordingPolicy?.max_duration_seconds ?? 15,
    recordingStorageProfile: recordingPolicy?.storage_profile ?? "central",
    recordingStorageProfileId: recordingPolicy?.storage_profile_id ?? "",
    recordingSnapshotEnabled: recordingPolicy?.snapshot_enabled ?? false,
    recordingSnapshotOffsetSeconds: recordingPolicy?.snapshot_offset_seconds ?? 0,
    recordingSnapshotQuality: recordingPolicy?.snapshot_quality ?? 85,
    homography: {
      src: toPointTupleArray(initialCamera?.homography?.src),
      dst: toPointTupleArray(initialCamera?.homography?.dst),
      refDistanceM: initialCamera?.homography?.ref_distance_m ?? 0,
    },
    visionProfile: visionProfileFromCamera(initialCamera?.vision_profile),
    zones: boundaryDraftsFromZones(initialCamera?.zones),
    detectionRegions: detectionRegionDraftsFromRegions(initialCamera?.detection_regions),
  };
}

function buildBrowserDelivery(data: CameraWizardData) {
  const nativeStream = data.streamDeliveryMode === "native";

  return {
    default_profile: nativeStream ? "native" : data.browserDeliveryProfile,
    allow_native_on_demand: true,
    delivery_profile_id: data.streamDeliveryProfileId || null,
    delivery_mode: data.streamDeliveryMode,
    public_base_url: data.streamDeliveryPublicBaseUrl,
    edge_override_url: data.streamDeliveryEdgeOverrideUrl,
    profiles: nativeStream
      ? nativeOnlyBrowserDeliveryProfiles(data.browserDeliveryProfiles)
      : data.browserDeliveryProfiles,
    unsupported_profiles: nativeStream
      ? []
      : data.unsupportedBrowserDeliveryProfiles,
    native_status: data.browserDeliveryNativeStatus,
  };
}

function buildCameraSource(data: CameraWizardData) {
  if (data.sourceKind === "usb") {
    return {
      kind: "usb" as const,
      uri: data.usbUri.trim(),
    };
  }

  return {
    kind: "rtsp" as const,
    uri: data.rtspUrl.trim(),
  };
}

function edgeNodeIdForSource(data: CameraWizardData) {
  return data.sourceKind === "usb" ? data.edgeNodeId.trim() || null : null;
}

function buildRecordingPolicy(data: CameraWizardData): EvidenceRecordingPolicy {
  return {
    enabled: data.recordingEnabled,
    mode: "event_clip",
    pre_seconds: data.recordingPreSeconds,
    post_seconds: data.recordingPostSeconds,
    fps: data.recordingFps,
    max_duration_seconds: Math.max(
      data.recordingMaxDurationSeconds,
      data.recordingPreSeconds + data.recordingPostSeconds,
    ),
    storage_profile: data.recordingStorageProfile,
    storage_profile_id: data.recordingStorageProfileId || null,
    snapshot_enabled: data.recordingSnapshotEnabled,
    snapshot_offset_seconds: data.recordingSnapshotOffsetSeconds,
    snapshot_quality: data.recordingSnapshotQuality,
  };
}

type EvidenceStorageProfileOption = {
  id: string;
  label: string;
  storageProfile: EvidenceStorageProfile;
  profileId: string | null;
};

type StreamDeliveryProfileOption = {
  id: string;
  label: string;
  deliveryMode: StreamDeliveryMode | null;
  publicBaseUrl: string | null;
  edgeOverrideUrl: string | null;
};

const LEGACY_STORAGE_PROFILE_OPTIONS: EvidenceStorageProfileOption[] = [
  {
    id: "edge_local",
    label: "Edge local",
    storageProfile: "edge_local",
    profileId: null,
  },
  { id: "central", label: "Central", storageProfile: "central", profileId: null },
  { id: "cloud", label: "Cloud", storageProfile: "cloud", profileId: null },
  {
    id: "local_first",
    label: "Local first",
    storageProfile: "local_first",
    profileId: null,
  },
];

function evidenceStorageProfileOptions(
  profiles: OperatorConfigProfile[] | undefined,
): EvidenceStorageProfileOption[] {
  const options: EvidenceStorageProfileOption[] = [];
  for (const profile of profiles ?? []) {
    if (!profile.enabled) {
      continue;
    }
    const storageProfile = storageProfileForEvidenceConfig(profile.config ?? {});
    if (storageProfile === null) {
      continue;
    }
    options.push({
      id: profile.id,
      label: `${profile.name} (${formatEvidenceStorageProfile(storageProfile)})`,
      storageProfile,
      profileId: profile.id,
    });
  }
  return options.length > 0 ? options : LEGACY_STORAGE_PROFILE_OPTIONS;
}

function streamDeliveryProfileOptions(
  profiles: OperatorConfigProfile[] | undefined,
): StreamDeliveryProfileOption[] {
  const isStreamDeliveryMode = (value: unknown): value is StreamDeliveryMode =>
    value === "native" ||
    value === "webrtc" ||
    value === "hls" ||
    value === "mjpeg" ||
    value === "transcode";

  return (profiles ?? [])
    .filter((profile) => profile.enabled)
    .map((profile) => {
      const config = profile.config ?? {};
      const deliveryMode = isStreamDeliveryMode(config.delivery_mode)
        ? config.delivery_mode
        : null;
      const publicBaseUrl =
        typeof config.public_base_url === "string" ? config.public_base_url : null;
      const edgeOverrideUrl =
        typeof config.edge_override_url === "string" ? config.edge_override_url : null;
      return {
        id: profile.id,
        label: `${profile.name}${deliveryMode ? ` (${deliveryMode})` : ""}`,
        deliveryMode,
        publicBaseUrl,
        edgeOverrideUrl,
      };
    });
}

function storageProfileForEvidenceConfig(
  config: NonNullable<OperatorConfigProfile["config"]>,
): EvidenceStorageProfile | null {
  const provider = typeof config.provider === "string" ? config.provider : "";
  const scope = typeof config.storage_scope === "string" ? config.storage_scope : "";
  if (provider === "local_first") {
    return "local_first";
  }
  if (provider === "local_filesystem" && scope === "edge") {
    return "edge_local";
  }
  if (provider === "minio" && scope === "central") {
    return "central";
  }
  if (provider === "s3_compatible" && scope === "cloud") {
    return "cloud";
  }
  return null;
}

function formatEvidenceStorageProfile(profile: EvidenceStorageProfile): string {
  if (profile === "edge_local") {
    return "Edge local";
  }
  if (profile === "local_first") {
    return "Local first";
  }
  return profile[0].toUpperCase() + profile.slice(1);
}

function visionProfileFromCamera(
  visionProfile: Camera["vision_profile"] | undefined,
): VisionProfileDraft {
  return {
    computeTier: visionProfile?.compute_tier ?? "edge_standard",
    accuracyMode: visionProfile?.accuracy_mode ?? "balanced",
    sceneDifficulty: visionProfile?.scene_difficulty ?? "cluttered",
    objectDomain: visionProfile?.object_domain ?? "mixed",
    speedEnabled: visionProfile?.motion_metrics?.speed_enabled ?? false,
    candidateQuality: visionProfile?.candidate_quality ?? {},
    trackerProfile: visionProfile?.tracker_profile ?? {},
    verifierProfile: visionProfile?.verifier_profile ?? {},
  };
}

function buildVisionProfile(data: CameraWizardData): SceneVisionProfile {
  return {
    compute_tier: data.visionProfile.computeTier,
    accuracy_mode: data.visionProfile.accuracyMode,
    scene_difficulty: data.visionProfile.sceneDifficulty,
    object_domain: data.visionProfile.objectDomain,
    motion_metrics: {
      speed_enabled: data.visionProfile.speedEnabled,
    },
    candidate_quality: data.visionProfile.candidateQuality ?? {},
    tracker_profile: data.visionProfile.trackerProfile ?? {},
    verifier_profile: data.visionProfile.verifierProfile ?? {},
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

function createDetectionRegionDraft(
  mode: DetectionRegionMode,
  ordinal = 1,
): DetectionRegionDraft {
  return {
    id: `${mode}-region-${ordinal}`,
    mode,
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

function detectionRegionDraftsFromRegions(
  regions: SerializedDetectionRegion[] | undefined,
  fallbackFrameSize: FrameSize = DEFAULT_ANALYTICS_FRAME_SIZE,
): DetectionRegionDraft[] {
  if (!regions) {
    return [];
  }

  return regions.reduce<DetectionRegionDraft[]>((drafts, region) => {
    const frameSize = parseFrameSize(region.frame_size) ?? fallbackFrameSize;
    const normalizedGeometry = parseNormalizedPoints(region.points_normalized);
    const parsedPolygon = toPointTupleArray(region.polygon);
    const points =
      normalizedGeometry.length >= 3
        ? denormalizePointList(normalizedGeometry, frameSize)
        : parsedPolygon;

    if (points.length < 3) {
      return drafts;
    }

    drafts.push({
      id: region.id,
      mode: region.mode,
      classNames: Array.isArray(region.class_names)
        ? region.class_names
            .filter((value): value is string => typeof value === "string")
            .join(",")
        : "",
      points,
      frameSize,
    });

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

function detectionRegionPointsForFrame(
  region: DetectionRegionDraft,
  frameSize: FrameSize,
): Point[] {
  const sourceFrameSize = region.frameSize ?? frameSize;
  const normalizedPoints = normalizePointList(region.points, sourceFrameSize);
  return denormalizePointList(normalizedPoints, frameSize);
}

function isHomographyComplete(data: CameraWizardData["homography"]) {
  return data.src.length === 4 && data.dst.length === 4 && data.refDistanceM > 0;
}

function serializeHomography(data: CameraWizardData["homography"]) {
  if (!isHomographyComplete(data)) {
    return null;
  }

  return {
    src: data.src,
    dst: data.dst,
    ref_distance_m: data.refDistanceM,
  };
}

function serializeZones(
  boundaries: BoundaryDraft[],
  setupFrameSize: FrameSize,
): SerializedZone[] {
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

function serializeDetectionRegions(
  regions: DetectionRegionDraft[],
  setupFrameSize: FrameSize,
): SerializedDetectionRegion[] {
  return regions.map((region, index) => {
    const regionId = region.id.trim();
    if (!regionId) {
      throw new Error(`Detection region ${index + 1} requires an id.`);
    }

    if (region.points.length < 3) {
      throw new Error(`Detection region ${index + 1} requires at least three polygon points.`);
    }

    return {
      id: regionId,
      mode: region.mode,
      polygon: detectionRegionPointsForFrame(region, setupFrameSize),
      class_names: parseBoundaryClassNames(region.classNames),
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

function validateDetectionRegions(regions: DetectionRegionDraft[]): string | null {
  for (const [index, region] of regions.entries()) {
    if (!region.id.trim()) {
      return `Detection region ${index + 1} requires an id.`;
    }
    if (region.points.length < 3) {
      return `Detection region ${index + 1} requires at least three polygon points.`;
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

function parseRuntimeVocabulary(value: string) {
  return value
    .split(",")
    .map((term) => term.trim())
    .filter(Boolean);
}

function runtimeVocabularyPayload(data: CameraWizardData, incrementVersion = false) {
  const baseVersion =
    data.runtimeVocabulary.length > 0
      ? Math.max(1, data.runtimeVocabularyVersion)
      : data.runtimeVocabularyVersion;

  return {
    terms: data.runtimeVocabulary,
    source: "manual" as const,
    version: incrementVersion ? baseVersion + 1 : baseVersion,
  };
}

function formatModelOptionLabel(model: ModelOption) {
  const capability = model.capability === "open_vocab" ? "open vocab" : "fixed vocab";
  const backend = model.capability_config?.runtime_backend ?? "onnxruntime";
  const readiness = model.capability_config?.readiness;
  return `${model.name} ${model.version} - ${capability} - ${backend}${
    readiness ? ` - ${readiness}` : ""
  }`;
}

function summarizeSelectedModelRuntime(
  model: ModelOption,
  runtimeVocabularyVersion: number,
) {
  const artifacts = model.runtime_artifacts ?? [];
  if (artifacts.length === 0) {
    return {
      label: "Dynamic/fallback runtime",
      detail: "No compiled artifact registered; worker will use the canonical model runtime.",
      tone: "muted" as const,
    };
  }

  if (artifacts.some((artifact) => artifact.validation_status === "stale")) {
    return {
      label: "Compiled stale",
      detail: "Rebuild the compiled artifact before production selection.",
      tone: "attention" as const,
    };
  }

  const validArtifacts = artifacts.filter(
    (artifact) => artifact.validation_status === "valid",
  );
  const matchingVocabularyArtifacts =
    model.capability === "open_vocab"
      ? validArtifacts.filter(
          (artifact) =>
            artifact.vocabulary_version == null ||
            artifact.vocabulary_version === runtimeVocabularyVersion,
        )
      : validArtifacts;

  if (
    model.capability === "open_vocab" &&
    validArtifacts.length > 0 &&
    matchingVocabularyArtifacts.length === 0
  ) {
    return {
      label: "Compiled stale",
      detail: "The runtime vocabulary changed since this artifact build.",
      tone: "attention" as const,
    };
  }

  const bestArtifact =
    matchingVocabularyArtifacts.find((artifact) => artifact.kind === "tensorrt_engine") ??
    matchingVocabularyArtifacts.find((artifact) => artifact.kind === "onnx_export");

  if (bestArtifact?.kind === "tensorrt_engine") {
    return {
      label: "TensorRT artifact: valid",
      detail: `${bestArtifact.target_profile} - ${bestArtifact.precision}`,
      tone: "healthy" as const,
    };
  }

  if (bestArtifact?.kind === "onnx_export") {
    return {
      label: "ONNX artifact: valid",
      detail: `${bestArtifact.target_profile} - ${bestArtifact.precision}`,
      tone: "accent" as const,
    };
  }

  return {
    label: "Dynamic/fallback runtime",
    detail: "No valid compiled artifact is ready; worker will use the canonical model runtime.",
    tone: "muted" as const,
  };
}

function toCreatePayload(
  data: CameraWizardData,
  setupFrameSize: FrameSize,
  primaryModelCapability: DetectorCapability,
): CreateCameraInput {
  const payload: CreateCameraInput = {
    site_id: data.siteId,
    edge_node_id: edgeNodeIdForSource(data),
    name: data.name.trim(),
    rtsp_url: data.sourceKind === "rtsp" ? data.rtspUrl.trim() : null,
    camera_source: buildCameraSource(data),
    processing_mode: data.processingMode,
    primary_model_id: data.primaryModelId,
    secondary_model_id: data.secondaryModelId || null,
    tracker_type: data.trackerType,
    active_classes: data.activeClasses,
    attribute_rules: [],
    zones: serializeZones(data.zones, setupFrameSize),
    vision_profile: buildVisionProfile(data),
    detection_regions: serializeDetectionRegions(data.detectionRegions, setupFrameSize),
    homography: serializeHomography(data.homography),
    privacy: {
      blur_faces: data.blurFaces,
      blur_plates: data.blurPlates,
      method: data.method,
      strength: data.strength,
    },
    browser_delivery: buildBrowserDelivery(data),
    frame_skip: data.frameSkip,
    fps_cap: data.fpsCap,
    recording_policy: buildRecordingPolicy(data),
  };

  if (primaryModelCapability === "open_vocab") {
    payload.runtime_vocabulary = runtimeVocabularyPayload(data);
  }

  return payload;
}

function toUpdatePayload(
  data: CameraWizardData,
  setupFrameSize: FrameSize,
  primaryModelCapability: DetectorCapability,
): UpdateCameraInput {
  const payload: UpdateCameraInput = {
    site_id: data.siteId,
    edge_node_id: edgeNodeIdForSource(data),
    name: data.name.trim(),
    processing_mode: data.processingMode,
    primary_model_id: data.primaryModelId,
    secondary_model_id: data.secondaryModelId || null,
    tracker_type: data.trackerType,
    active_classes: data.activeClasses,
    zones: serializeZones(data.zones, setupFrameSize),
    vision_profile: buildVisionProfile(data),
    detection_regions: serializeDetectionRegions(data.detectionRegions, setupFrameSize),
    homography: serializeHomography(data.homography),
    privacy: {
      blur_faces: data.blurFaces,
      blur_plates: data.blurPlates,
      method: data.method,
      strength: data.strength,
    },
    browser_delivery: buildBrowserDelivery(data),
    frame_skip: data.frameSkip,
    fps_cap: data.fpsCap,
    recording_policy: buildRecordingPolicy(data),
  };

  if (data.sourceKind === "rtsp" && data.rtspUrl.trim()) {
    payload.rtsp_url = data.rtspUrl.trim();
    payload.camera_source = buildCameraSource(data);
  } else if (data.sourceKind === "usb") {
    payload.rtsp_url = null;
    payload.camera_source = buildCameraSource(data);
  }

  if (primaryModelCapability === "open_vocab") {
    payload.runtime_vocabulary = runtimeVocabularyPayload(data, true);
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
  const trimmedRtspUrl = data.rtspUrl.trim();
  const trimmedUsbUri = data.usbUri.trim();
  const activeSourceUri = data.sourceKind === "usb" ? trimmedUsbUri : trimmedRtspUrl;
  const sourceSizeLabel = formatSourceSize(data.sourceCapability);
  const setupPreviewQuery = useCameraSetupPreview(
    initialCamera?.id,
    isEditMode && stepTitle === "Calibration",
  );
  const evidenceStorageProfilesQuery = useConfigurationProfiles("evidence_storage");
  const streamDeliveryProfilesQuery = useConfigurationProfiles("stream_delivery");
  const sourceProbeQuery = useQuery<CameraSourceProbeResponse>({
    enabled:
      stepTitle === "Privacy, Processing & Delivery" &&
      (data.sourceKind === "usb"
        ? trimmedUsbUri.length > 0 && data.edgeNodeId.trim().length > 0
        : isEditMode
          ? Boolean(initialCamera?.id)
          : trimmedRtspUrl.length > 0),
    queryKey: [
      "camera-source-probe",
      initialCamera?.id ?? "new",
      data.sourceKind,
      isEditMode && activeSourceUri.length === 0 ? "stored" : activeSourceUri,
      data.edgeNodeId,
      data.processingMode,
      data.blurFaces,
      data.blurPlates,
      data.method,
      data.strength,
    ],
    queryFn: async () => {
      const accessToken = await resolveAccessToken();
      const headers = new Headers({ "Content-Type": "application/json" });
      if (accessToken) {
        headers.set("Authorization", `Bearer ${accessToken}`);
      }

      const response = await fetch(`${frontendConfig.apiBaseUrl}/api/v1/cameras/source-probe`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          camera_id: initialCamera?.id ?? null,
          rtsp_url:
            data.sourceKind === "rtsp"
              ? isEditMode
                ? trimmedRtspUrl || null
                : trimmedRtspUrl
              : null,
          camera_source:
            data.sourceKind === "usb" || trimmedRtspUrl
              ? buildCameraSource(data)
              : null,
          processing_mode: data.processingMode,
          edge_node_id: edgeNodeIdForSource(data),
          browser_delivery: buildBrowserDelivery(data),
          privacy: {
            blur_faces: data.blurFaces,
            blur_plates: data.blurPlates,
            method: data.method,
            strength: data.strength,
          },
        }),
      });

      if (!response.ok) {
        let detail: unknown;
        try {
          detail = await response.json();
        } catch {
          detail = await response.text();
        }
        throw toApiError(detail, "Failed to inspect camera source capability.");
      }

      return (await response.json()) as CameraSourceProbeResponse;
    },
    retry: false,
  });
  const selectedPrimaryModel = useMemo(
    () => models.find((model) => model.id === data.primaryModelId) ?? null,
    [data.primaryModelId, models],
  );
  const selectedPrimaryModelCapability =
    selectedPrimaryModel?.capability ?? "fixed_vocab";
  const showsRuntimeVocabulary = selectedPrimaryModelCapability === "open_vocab";
  const selectedPrimaryModelClasses = useMemo(
    () => selectedPrimaryModel?.classes ?? [],
    [selectedPrimaryModel],
  );
  const selectedPrimaryModelClassesKey = selectedPrimaryModelClasses.join("\u0000");
  const selectedRuntimeSummary = useMemo(
    () =>
      selectedPrimaryModel
        ? summarizeSelectedModelRuntime(
            selectedPrimaryModel,
            data.runtimeVocabularyVersion,
          )
        : null,
    [data.runtimeVocabularyVersion, selectedPrimaryModel],
  );
  const storageProfileOptions = useMemo(
    () => evidenceStorageProfileOptions(evidenceStorageProfilesQuery.data),
    [evidenceStorageProfilesQuery.data],
  );
  const storageProfileSelectValue =
    data.recordingStorageProfileId ||
    (storageProfileOptions.some((option) => option.id === data.recordingStorageProfile)
      ? data.recordingStorageProfile
      : "");
  const selectedStorageProfileLabel =
    storageProfileOptions.find((option) => option.id === storageProfileSelectValue)?.label ??
    formatEvidenceStorageProfile(data.recordingStorageProfile);
  const streamProfileOptions = useMemo(
    () => streamDeliveryProfileOptions(streamDeliveryProfilesQuery.data),
    [streamDeliveryProfilesQuery.data],
  );
  const browserDeliveryProfileOptions = useMemo(
    () =>
      data.streamDeliveryMode === "native"
        ? nativeOnlyBrowserDeliveryProfiles(data.browserDeliveryProfiles)
        : data.browserDeliveryProfiles,
    [data.browserDeliveryProfiles, data.streamDeliveryMode],
  );

  useEffect(() => {
    setData(createDefaultData(initialCamera));
    setStepIndex(0);
    setError(null);
    setSubmitError(null);
    setIsSubmitting(false);
    setShowBoundaryAdvanced(false);
  }, [initialCamera]);

  useEffect(() => {
    if (!sourceProbeQuery.data) {
      return;
    }

    const probeBrowserDelivery = sourceProbeQuery.data.browser_delivery;
    const probedProfiles = normalizeBrowserDeliveryProfiles(probeBrowserDelivery.profiles);
    const unsupportedProfiles = normalizeBrowserDeliveryProfiles(
      probeBrowserDelivery.unsupported_profiles,
      [],
    );
    const serverDefaultProfile = isBrowserDeliveryProfile(probeBrowserDelivery.default_profile)
      ? probeBrowserDelivery.default_profile
      : "720p10";

    setData((current) => {
      const requestedProfile = probedProfiles.some(
        (profile) => profile.id === current.browserDeliveryProfile,
      )
        ? current.browserDeliveryProfile
        : serverDefaultProfile;

      return {
        ...current,
        browserDeliveryProfile: resolveBrowserDeliveryProfile(
          requestedProfile,
          probedProfiles,
        ),
        browserDeliveryProfiles: probedProfiles,
        unsupportedBrowserDeliveryProfiles: unsupportedProfiles,
        browserDeliveryNativeStatus: probeBrowserDelivery.native_status ?? {
          available: true,
          reason: null,
        },
        sourceCapability: sourceProbeQuery.data.source_capability,
      };
    });
  }, [sourceProbeQuery.data]);

  useEffect(() => {
    if (data.streamDeliveryMode !== "native" || data.browserDeliveryProfile === "native") {
      return;
    }

    setData((current) => ({ ...current, browserDeliveryProfile: "native" }));
  }, [data.browserDeliveryProfile, data.streamDeliveryMode]);

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

      if (selectedPrimaryModelCapability === "open_vocab") {
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
    selectedPrimaryModelCapability,
    selectedPrimaryModelClasses,
    selectedPrimaryModelClassesKey,
  ]);

  const siteName = useMemo(
    () => sites.find((site) => site.id === data.siteId)?.name ?? "Unassigned site",
    [data.siteId, sites],
  );
  const fallbackSetupFrameSize = useMemo(
    () =>
      data.zones.find((boundary) => boundary.frameSize)?.frameSize ??
      data.detectionRegions.find((region) => region.frameSize)?.frameSize ??
      (data.sourceCapability
        ? { width: data.sourceCapability.width, height: data.sourceCapability.height }
        : DEFAULT_ANALYTICS_FRAME_SIZE),
    [data.detectionRegions, data.sourceCapability, data.zones],
  );
  const setupFrameSize = setupPreviewQuery.data?.frame_size ?? fallbackSetupFrameSize;
  const setupPreviewSrc = setupPreviewQuery.data?.preview_src ?? null;
  const calibrationPreviewState = useMemo(() => {
    const defaultFrameLabel = `${setupFrameSize.width}×${setupFrameSize.height}`;
    const capturedLabel = setupPreviewQuery.data
      ? (() => {
          const capturedAt = new Date(setupPreviewQuery.data.captured_at);
          return Number.isNaN(capturedAt.getTime())
            ? setupPreviewQuery.data.captured_at
            : capturedAt.toLocaleString();
        })()
      : null;
    const errorDetail =
      setupPreviewQuery.error instanceof Error && setupPreviewQuery.error.message
        ? setupPreviewQuery.error.message
        : "Retry the analytics still capture after confirming the camera stream is reachable.";

    if (!isEditMode) {
      return {
        tone: "neutral" as const,
        title: "Analytics still becomes available after the camera is saved",
        body: `Use the provisional ${defaultFrameLabel} authoring plane for now. Once the camera exists, ${brandName} can capture a real analytics still for source points and event boundaries.`,
        frameLabel: defaultFrameLabel,
      };
    }

    if (setupPreviewQuery.isPending) {
      return {
        tone: "neutral" as const,
        title: "Capturing analytics still",
        body: `Source points and event boundaries will attach to the ${defaultFrameLabel} analytics frame as soon as the captured still is ready.`,
        frameLabel: defaultFrameLabel,
      };
    }

    if (setupPreviewQuery.isError) {
      return {
        tone: "error" as const,
        title: "Unable to capture analytics still",
        body: `${errorDetail} Source points can still be placed on the ${defaultFrameLabel} fallback analytics plane, but review alignment once the still is available.`,
        frameLabel: defaultFrameLabel,
      };
    }

    if (setupPreviewQuery.data && setupPreviewSrc) {
      return {
        tone: "success" as const,
        title: "Analytics still ready",
        body: `Source points and event boundaries are drawing on a captured ${defaultFrameLabel} analytics frame from the configured camera source. Captured ${capturedLabel}.`,
        frameLabel: defaultFrameLabel,
      };
    }

    if (setupPreviewQuery.data) {
      return {
        tone: "warning" as const,
        title: "Analytics frame ready, still unavailable",
        body: `Frame metadata was loaded for ${defaultFrameLabel}, but the still image could not be displayed. Source points and event boundaries are using the analytics frame bounds until you refresh the still.`,
        frameLabel: defaultFrameLabel,
      };
    }

    return {
      tone: "neutral" as const,
      title: "Analytics frame pending",
      body: `Preparing the ${defaultFrameLabel} analytics frame for source-point and boundary authoring.`,
      frameLabel: defaultFrameLabel,
    };
  }, [
    brandName,
    isEditMode,
    setupFrameSize.height,
    setupFrameSize.width,
    setupPreviewQuery.data,
    setupPreviewQuery.error,
    setupPreviewQuery.isError,
    setupPreviewQuery.isPending,
    setupPreviewSrc,
  ]);

  const contextPanel = useMemo(() => {
    switch (stepTitle) {
      case "Identity":
        return `Choose the fleet location, processing posture, and ingest stream ${brandName} should bind to this camera.`;
      case "Models & Tracking":
        return "Primary and secondary models shape what the camera observes, while the tracker stabilizes entity identity across frames.";
      case "Privacy, Processing & Delivery":
        return data.processingMode === "edge"
          ? "Native is clean passthrough. Processed profiles are built on the edge before browser delivery."
          : "Native is clean passthrough. Processed preview profiles reduce master-to-browser viewing bandwidth only.";
      case "Calibration":
        return `Calibrate four source points, four destination points, a real-world distance, and any line or polygon boundaries so ${brandName} can map motion and count events inside the physical scene.`;
      case "Review":
        return `Confirm the camera configuration before ${brandName} saves it. RTSP stays masked unless you explicitly replace it.`;
      default:
        return "Configuration guidance appears here.";
    }
  }, [brandName, data.processingMode, stepTitle]);

  function updateData<Key extends keyof CameraWizardData>(
    key: Key,
    value: CameraWizardData[Key],
  ) {
    setData((current) => ({ ...current, [key]: value }));
  }

  function updateRecordingStorageProfile(optionId: string) {
    const option = storageProfileOptions.find((candidate) => candidate.id === optionId);
    if (!option) {
      return;
    }
    setData((current) => ({
      ...current,
      recordingStorageProfile: option.storageProfile,
      recordingStorageProfileId: option.profileId ?? "",
    }));
  }

  function updateStreamDeliveryProfile(optionId: string) {
    if (optionId === "") {
      setData((current) => ({
        ...current,
        streamDeliveryProfileId: "",
        streamDeliveryMode: null,
        streamDeliveryPublicBaseUrl: null,
        streamDeliveryEdgeOverrideUrl: null,
      }));
      return;
    }
    const option = streamProfileOptions.find((candidate) => candidate.id === optionId);
    if (!option) {
      return;
    }
    setData((current) => ({
      ...current,
      streamDeliveryProfileId: option.id,
      streamDeliveryMode: option.deliveryMode,
      streamDeliveryPublicBaseUrl: option.publicBaseUrl,
      streamDeliveryEdgeOverrideUrl: option.edgeOverrideUrl,
      browserDeliveryProfile:
        option.deliveryMode === "native"
          ? "native"
          : option.deliveryMode
            ? "annotated"
            : current.browserDeliveryProfile,
    }));
  }

  function updateVisionProfile(patch: Partial<VisionProfileDraft>) {
    setData((current) => ({
      ...current,
      visionProfile: {
        ...current.visionProfile,
        ...patch,
      },
    }));
  }

  function updateNumericField<
    Key extends
      | "strength"
      | "frameSkip"
      | "fpsCap"
      | "recordingPreSeconds"
      | "recordingPostSeconds"
      | "recordingFps",
  >(
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
      if (data.sourceKind === "rtsp") {
        if ((!isEditMode || !maskedRtspPlaceholder) && !data.rtspUrl.trim()) {
          return "RTSP URL is required.";
        }
      } else {
        if (!data.usbUri.trim()) {
          return "USB device URI is required.";
        }
        if (!data.edgeNodeId.trim()) {
          return "Edge node ID is required for USB sources.";
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
      if (data.recordingPreSeconds < 0) {
        return "Pre seconds must be at least 0.";
      }
      if (data.recordingPostSeconds < 1) {
        return "Post seconds must be at least 1.";
      }
      if (data.recordingFps < 1) {
        return "Recording FPS must be at least 1.";
      }
    }

    if (stepTitle === "Calibration") {
      if (data.visionProfile.speedEnabled) {
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
      const boundaryError = validateZoneBoundaries(data.zones);
      if (boundaryError) {
        return boundaryError;
      }
      const detectionRegionError = validateDetectionRegions(data.detectionRegions);
      if (detectionRegionError) {
        return detectionRegionError;
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

  function addDetectionRegion(mode: DetectionRegionMode) {
    setData((current) => {
      const ordinal =
        current.detectionRegions.filter((region) => region.mode === mode).length + 1;
      return {
        ...current,
        detectionRegions: [
          ...current.detectionRegions,
          createDetectionRegionDraft(mode, ordinal),
        ],
      };
    });
  }

  function updateDetectionRegion(index: number, patch: Partial<DetectionRegionDraft>) {
    setData((current) => ({
      ...current,
      detectionRegions: current.detectionRegions.map((region, regionIndex) =>
        regionIndex === index ? { ...region, ...patch } : region,
      ),
    }));
  }

  function removeDetectionRegion(index: number) {
    setData((current) => ({
      ...current,
      detectionRegions: current.detectionRegions.filter((_, regionIndex) => regionIndex !== index),
    }));
  }

  function clearDetectionRegionPoints(index: number) {
    updateDetectionRegion(index, { points: [] });
  }

  function updateDetectionRegionFromCanvas(
    index: number,
    pointsNormalized: ReadonlyArray<readonly [number, number]>,
  ) {
    updateDetectionRegion(index, {
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
        await onSubmit(toUpdatePayload(data, setupFrameSize, selectedPrimaryModelCapability));
      } else {
        await onSubmit(toCreatePayload(data, setupFrameSize, selectedPrimaryModelCapability));
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
                  disabled={data.sourceKind === "usb"}
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
                <span>Source type</span>
                <Select
                  aria-label="Source type"
                  value={data.sourceKind}
                  onChange={(event) => {
                    const sourceKind = event.target.value as CameraWizardData["sourceKind"];
                    setData((current) => ({
                      ...current,
                      sourceKind,
                      processingMode:
                        sourceKind === "usb" ? "edge" : current.processingMode,
                    }));
                  }}
                >
                  <option value="rtsp">RTSP</option>
                  <option value="usb">USB edge camera</option>
                </Select>
              </label>
              {data.sourceKind === "usb" ? (
                <>
                  <label className="grid gap-2 text-sm text-[#d8e2f2]">
                    <span>USB device URI</span>
                    <Input
                      aria-label="USB device URI"
                      placeholder="usb:///dev/video0"
                      value={data.usbUri}
                      onChange={(event) => updateData("usbUri", event.target.value)}
                    />
                  </label>
                  <label className="grid gap-2 text-sm text-[#d8e2f2]">
                    <span>Edge node ID</span>
                    <Input
                      aria-label="Edge node ID"
                      placeholder="22222222-2222-2222-2222-222222222222"
                      value={data.edgeNodeId}
                      onChange={(event) => updateData("edgeNodeId", event.target.value)}
                    />
                  </label>
                  <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                    USB sources run on an assigned edge node. Central processing is not
                    available for USB/UVC capture.
                  </p>
                </>
              ) : null}
              {data.sourceKind === "rtsp" ? (
                <label className="grid gap-2 text-sm text-[#d8e2f2]">
                  <span>RTSP URL</span>
                  <Input
                    aria-label="RTSP URL"
                    placeholder={maskedRtspPlaceholder || "rtsp://camera.local/live"}
                    value={data.rtspUrl}
                    onChange={(event) => updateData("rtspUrl", event.target.value)}
                  />
                </label>
              ) : null}
              {isEditMode && data.sourceKind === "rtsp" ? (
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
                      activeClasses:
                        nextPrimaryModel?.capability === "open_vocab"
                          ? []
                          : pruneActiveClasses(
                              current.activeClasses,
                              nextPrimaryModel?.classes ?? [],
                            ),
                    }));
                  }}
                >
                  <option value="">Select a model</option>
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {formatModelOptionLabel(model)}
                    </option>
                  ))}
                </Select>
              </label>
              {selectedRuntimeSummary ? (
                <div
                  data-testid="model-runtime-summary"
                  className={`rounded-[1.15rem] border px-4 py-3 text-sm ${
                    selectedRuntimeSummary.tone === "healthy"
                      ? "border-emerald-300/30 bg-emerald-950/20 text-emerald-100"
                      : selectedRuntimeSummary.tone === "attention"
                        ? "border-amber-300/30 bg-amber-950/20 text-amber-100"
                        : selectedRuntimeSummary.tone === "accent"
                          ? "border-sky-300/30 bg-sky-950/20 text-sky-100"
                          : "border-[#284066] bg-[#0c1522] text-[#9eb2cf]"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="font-medium text-[#eef4ff]">Runtime</p>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em]">
                      {selectedRuntimeSummary.label}
                    </p>
                  </div>
                  <p className="mt-2">{selectedRuntimeSummary.detail}</p>
                </div>
              ) : null}
              {selectedPrimaryModel ? (
                showsRuntimeVocabulary ? (
                  <label className="grid gap-2 rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-4 text-sm text-[#d8e2f2]">
                    <span className="text-sm font-medium text-[#eef4ff]">
                      Runtime vocabulary
                    </span>
                    <Input
                      aria-label="Runtime vocabulary"
                      placeholder="forklift, pallet jack"
                      value={data.runtimeVocabulary.join(", ")}
                      onChange={(event) =>
                        setData((current) => ({
                          ...current,
                          runtimeVocabulary: parseRuntimeVocabulary(event.target.value),
                        }))
                      }
                    />
                    <span className="text-xs text-[#8ea4c7]">
                      {data.runtimeVocabulary.length}
                      {selectedPrimaryModel.capability_config?.max_runtime_terms
                        ? ` / ${selectedPrimaryModel.capability_config.max_runtime_terms}`
                        : ""}{" "}
                      terms
                    </span>
                  </label>
                ) : (
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
                )
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
                      {formatModelOptionLabel(model)}
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
              <section className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-4">
                <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] md:items-end">
                  <label className="grid gap-2 text-sm text-[#d8e2f2]">
                    <span>Vision profile</span>
                    <Select
                      aria-label="Vision profile"
                      value={data.visionProfile.accuracyMode}
                      onChange={(event) => {
                        const accuracyMode = event.target.value as VisionAccuracyMode;
                        updateVisionProfile({
                          accuracyMode,
                          objectDomain:
                            accuracyMode === "open_vocabulary"
                              ? "open_vocab"
                              : data.visionProfile.objectDomain === "open_vocab"
                                ? "mixed"
                                : data.visionProfile.objectDomain,
                        });
                      }}
                    >
                      <option value="fast">Fast</option>
                      <option value="balanced">Balanced</option>
                      <option value="maximum_accuracy">Maximum Accuracy</option>
                      <option value="open_vocabulary">Open Vocabulary</option>
                    </Select>
                  </label>
                  <label className="grid gap-2 text-sm text-[#d8e2f2]">
                    <span>Compute target</span>
                    <Select
                      aria-label="Compute target"
                      value={data.visionProfile.computeTier}
                      onChange={(event) =>
                        updateVisionProfile({
                          computeTier: event.target.value as VisionComputeTier,
                        })
                      }
                    >
                      <option value="cpu_low">Low CPU</option>
                      <option value="edge_standard">Standard Edge</option>
                      <option value="edge_advanced_jetson">Advanced Edge</option>
                      <option value="central_gpu">Central GPU</option>
                    </Select>
                  </label>
                  <label className="flex items-center gap-3 rounded-[0.95rem] border border-white/8 bg-white/[0.03] px-3 py-2 text-sm text-[#d8e2f2]">
                    <input
                      aria-label="Speed metrics"
                      checked={data.visionProfile.speedEnabled}
                      type="checkbox"
                      onChange={(event) =>
                        updateVisionProfile({ speedEnabled: event.target.checked })
                      }
                    />
                    <span>Speed metrics</span>
                  </label>
                </div>
              </section>
              <section className="rounded-[1.3rem] border border-[#284066] bg-[#0c1522] px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-[#eef4ff]">
                      Event clip recording
                    </p>
                    <p className="mt-1 text-sm text-[#9eb2cf]">
                      Capture short clips around incidents. This does not enable continuous
                      recording.
                    </p>
                  </div>
                  <label className="flex items-center gap-2 text-sm text-[#d8e2f2]">
                    <input
                      aria-label="Event clip recording"
                      checked={data.recordingEnabled}
                      type="checkbox"
                      onChange={(event) =>
                        updateData("recordingEnabled", event.target.checked)
                      }
                    />
                    <span>Enabled</span>
                  </label>
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                  <label className="grid gap-2 text-sm text-[#d8e2f2]">
                    <span>Pre seconds</span>
                    <Input
                      aria-label="Pre seconds"
                      min={0}
                      type="number"
                      value={data.recordingPreSeconds}
                      onChange={(event) =>
                        updateNumericField("recordingPreSeconds", event.target.value)
                      }
                    />
                  </label>
                  <label className="grid gap-2 text-sm text-[#d8e2f2]">
                    <span>Post seconds</span>
                    <Input
                      aria-label="Post seconds"
                      min={1}
                      type="number"
                      value={data.recordingPostSeconds}
                      onChange={(event) =>
                        updateNumericField("recordingPostSeconds", event.target.value)
                      }
                    />
                  </label>
                  <label className="grid gap-2 text-sm text-[#d8e2f2]">
                    <span>Recording FPS</span>
                    <Input
                      aria-label="Recording FPS"
                      min={1}
                      type="number"
                      value={data.recordingFps}
                      onChange={(event) =>
                        updateNumericField("recordingFps", event.target.value)
                      }
                    />
                  </label>
                  <label className="grid gap-2 text-sm text-[#d8e2f2]">
                    <span>Storage profile</span>
                    <Select
                      aria-label="Storage profile"
                      value={storageProfileSelectValue}
                      onChange={(event) =>
                        updateRecordingStorageProfile(event.target.value)
                      }
                    >
                      {storageProfileSelectValue ? null : (
                        <option value="">Choose profile</option>
                      )}
                      {storageProfileOptions.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </label>
                </div>
              </section>
              {streamProfileOptions.length > 0 ? (
                <label className="grid gap-2 text-sm text-[#d8e2f2]">
                  <span>Stream delivery profile</span>
                  <Select
                    aria-label="Stream delivery profile"
                    value={data.streamDeliveryProfileId}
                    onChange={(event) =>
                      updateStreamDeliveryProfile(event.target.value)
                    }
                  >
                    <option value="">Use default binding</option>
                    {streamProfileOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </label>
              ) : null}
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
                  {browserDeliveryProfileOptions.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {formatBrowserDeliveryProfileLabel(
                        profile,
                        data.processingMode,
                      )}
                    </option>
                  ))}
                </Select>
              </label>
              {sourceProbeQuery.isFetching ? (
                <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                  Inspecting source capability...
                </p>
              ) : null}
              {sourceProbeQuery.isError ? (
                <p className="rounded-[1.15rem] border border-[#5b4b28] bg-[#19150c] px-4 py-3 text-sm text-[#ffd9a1]">
                  Source capability could not be inspected. Profiles are based on saved settings until
                  the stream responds.
                </p>
              ) : null}
              {sourceSizeLabel && data.unsupportedBrowserDeliveryProfiles.length > 0 ? (
                <div className="space-y-1 rounded-[1.15rem] border border-[#4a3a26] bg-[#18120b] px-4 py-3 text-sm text-[#ffd9a1]">
                  {data.unsupportedBrowserDeliveryProfiles.map((profile) => (
                    <p key={profile.id}>
                      Source is {sourceSizeLabel}, so {profile.id} is unavailable.
                    </p>
                  ))}
                </div>
              ) : null}
              <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                {data.processingMode === "edge"
                  ? "Native stays clean passthrough. Processed profiles are published by the edge worker for annotated or reduced remote viewing."
                  : "Native stays clean passthrough. Processed profiles are published by the central worker for annotated or reduced browser viewing."}
              </p>
            </>
          ) : null}

          {stepTitle === "Calibration" ? (
            <div className="space-y-5">
              <section
                className={`rounded-[1.5rem] border p-4 ${
                  calibrationPreviewState.tone === "error"
                    ? "border-[#6a2735] bg-[#231118]"
                    : calibrationPreviewState.tone === "success"
                      ? "border-[#24594f] bg-[#0d1717]"
                      : calibrationPreviewState.tone === "warning"
                        ? "border-[#5b4b28] bg-[#19150c]"
                        : "border-[#243853] bg-[#09121c]"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
                      Calibration still
                    </p>
                    <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">
                      {calibrationPreviewState.title}
                    </h3>
                    <p className="mt-2 max-w-3xl text-sm text-[#d8e2f2]">
                      {calibrationPreviewState.body}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2]">
                      Analytics frame {calibrationPreviewState.frameLabel}
                    </span>
                    {isEditMode ? (
                      <Button
                        className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
                        disabled={setupPreviewQuery.isFetching}
                        type="button"
                        onClick={() => {
                          setupPreviewQuery.refreshPreview();
                        }}
                      >
                        {setupPreviewQuery.isFetching ? "Refreshing still…" : "Refresh still"}
                      </Button>
                    ) : null}
                  </div>
                </div>
              </section>
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
                      Event boundaries
                    </p>
                    <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">
                      Lines and zones
                    </h3>
                    <p className="mt-2 max-w-2xl text-sm text-[#9eb2cf]">
                      Reuse the same analytics still from source-point setup to draw event
                      boundaries directly on the analyzed frame. Lines emit crossings,
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

                {data.zones.length === 0 ? (
                  <p className="mt-4 rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                    No event boundaries configured yet. Add a line for crossing events or a zone for enter and exit events.
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
                                placeholder={omniPlaceExamples.eventClasses}
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
                                : "Zones create enter and exit events whenever the tracked footpoint crosses the boundary."
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
              <section className="rounded-[1.5rem] border border-[#243853] bg-[#09121c] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
                      Detection regions
                    </p>
                    <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">
                      Include and exclusion polygons
                    </h3>
                    <p className="mt-2 max-w-2xl text-sm text-[#9eb2cf]">
                      Limit detector attention with include polygons or mask operational dead zones
                      with exclusion polygons. Event boundaries above still publish count events.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
                      type="button"
                      onClick={() => addDetectionRegion("include")}
                    >
                      Add include region
                    </Button>
                    <Button
                      className="bg-white/[0.06] text-[#eef4ff] shadow-none hover:bg-white/[0.1]"
                      type="button"
                      onClick={() => addDetectionRegion("exclude")}
                    >
                      Add exclusion region
                    </Button>
                  </div>
                </div>

                {data.detectionRegions.length === 0 ? (
                  <p className="mt-4 rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
                    No detection regions configured.
                  </p>
                ) : (
                  <div className="mt-5 space-y-4">
                    {data.detectionRegions.map((region, index) => (
                      <section
                        key={`${region.mode}-${index}`}
                        className="rounded-[1.2rem] border border-white/8 bg-white/[0.03] p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8ea4c7]">
                              Detection region {index + 1}
                            </p>
                            <p className="mt-2 text-sm text-[#d8e2f2]">
                              {region.mode === "include" ? "Include polygon" : "Exclusion polygon"}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <button
                              aria-label={`Clear detection region ${index + 1} shape`}
                              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                              type="button"
                              onClick={() => clearDetectionRegionPoints(index)}
                            >
                              Clear shape
                            </button>
                            <button
                              aria-label={`Remove detection region ${index + 1}`}
                              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                              type="button"
                              onClick={() => removeDetectionRegion(index)}
                            >
                              Remove
                            </button>
                          </div>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2">
                          <label className="grid gap-2 text-sm text-[#d8e2f2]">
                            <span>Detection region {index + 1} ID</span>
                            <Input
                              aria-label={`Detection region ${index + 1} ID`}
                              value={region.id}
                              onChange={(event) =>
                                updateDetectionRegion(index, { id: event.target.value })
                              }
                            />
                          </label>
                          <label className="grid gap-2 text-sm text-[#d8e2f2]">
                            <span>Detection region {index + 1} classes</span>
                            <Input
                              aria-label={`Detection region ${index + 1} classes`}
                              placeholder={omniPlaceExamples.eventClasses}
                              value={region.classNames}
                              onChange={(event) =>
                                updateDetectionRegion(index, {
                                  classNames: event.target.value,
                                })
                              }
                            />
                          </label>
                        </div>

                        <div className="mt-4">
                          <BoundaryAuthoringCanvas
                            ariaLabel={`Detection region ${index + 1} canvas`}
                            backgroundContent={
                              <p className="max-w-sm text-sm text-[#bcefe3]">
                                Click to place polygon vertices, then drag handles to refine the detection region.
                              </p>
                            }
                            frameSize={setupFrameSize}
                            helperText={
                              region.mode === "include"
                                ? "Only detections inside include regions stay eligible when at least one include region exists."
                                : "Detections inside exclusion regions are ignored before event boundaries are evaluated."
                            }
                            mode="polygon"
                            pointLabelPrefix={`Detection region ${index + 1}`}
                            previewSrc={setupPreviewSrc}
                            value={normalizePointList(
                              detectionRegionPointsForFrame(region, setupFrameSize),
                              setupFrameSize,
                            )}
                            onChange={(pointsNormalized) =>
                              updateDetectionRegionFromCanvas(index, pointsNormalized)
                            }
                          />
                        </div>
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
                sourceLabel:
                  data.sourceKind === "usb"
                    ? `USB ${data.usbUri.trim() || "not set"}`
                    : `RTSP ${
                        data.rtspUrl.trim()
                          ? "replacement configured"
                          : maskedRtspPlaceholder || "not set"
                      }`,
                recordingLabel: data.recordingEnabled
                  ? `${data.recordingPreSeconds}s pre, ${data.recordingPostSeconds}s post, ${data.recordingFps} FPS, ${selectedStorageProfileLabel}`
                  : "Disabled",
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
