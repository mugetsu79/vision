import type { components } from "@/lib/api.generated";
import { getHeartbeatStatus } from "@/lib/live";

type FleetOverview = components["schemas"]["FleetOverviewResponse"];
type FleetCameraWorker = components["schemas"]["FleetCameraWorkerSummary"];
type FleetDeliveryDiagnostic = components["schemas"]["FleetDeliveryDiagnostic"];
type FleetRuleRuntime = components["schemas"]["FleetRuleRuntimeSummary"];
type Camera = components["schemas"]["CameraResponse"];
type Site = components["schemas"]["SiteResponse"];
type TelemetryFrame = components["schemas"]["TelemetryFrame"];

export type OperationalHealth = "healthy" | "attention" | "danger" | "unknown";
export type HealthTone = "healthy" | "attention" | "danger" | "muted";

export type HealthSignal = {
  health: OperationalHealth;
  label: string;
  detail?: string;
};

export type FleetHealth = HealthSignal & {
  reasons: string[];
};

export type AttentionItem = {
  id: string;
  health: Exclude<OperationalHealth, "healthy" | "unknown">;
  title: string;
  detail: string;
  href: string;
};

export type SceneHealthRow = {
  cameraId: string;
  cameraName: string;
  siteName: string;
  nodeLabel: string;
  processingMode: Camera["processing_mode"];
  readiness: HealthSignal;
  overall: HealthSignal;
  privacy: HealthSignal;
  worker: HealthSignal;
  rules: HealthSignal;
  delivery: HealthSignal;
  transport: HealthSignal;
  liveRendition: HealthSignal;
  telemetry: HealthSignal;
  actionHref: string;
  actionLabel: string;
};

export type DeploymentPosture = {
  siteCount: number;
  sceneCount: number;
  centralScenes: number;
  edgeScenes: number;
  hybridScenes: number;
  assignedEdgeNodes: number;
  pendingEvidence: number;
  privacyConfiguredScenes: number;
  fleetHealth: FleetHealth;
};

type PendingIncident = {
  id: string;
};

export function healthToTone(health: OperationalHealth): HealthTone {
  if (health === "healthy") return "healthy";
  if (health === "attention") return "attention";
  if (health === "danger") return "danger";
  return "muted";
}

export function deriveFleetHealth(
  fleet: FleetOverview | null | undefined,
): FleetHealth {
  if (!fleet) {
    return {
      health: "unknown",
      label: "Fleet status unknown",
      reasons: ["Fleet overview has not loaded"],
    };
  }

  const missingWorkers = Math.max(
    0,
    fleet.summary.desired_workers - fleet.summary.running_workers,
  );
  const reasons: string[] = [];

  if (fleet.summary.offline_nodes > 0) {
    reasons.push(plural(fleet.summary.offline_nodes, "offline node"));
  }
  if (fleet.summary.stale_nodes > 0) {
    reasons.push(plural(fleet.summary.stale_nodes, "stale node"));
  }
  if (missingWorkers > 0) {
    reasons.push(plural(missingWorkers, "worker missing", "workers missing"));
  }
  if (fleet.summary.native_unavailable_cameras > 0) {
    reasons.push(
      plural(
        fleet.summary.native_unavailable_cameras,
        "direct stream unavailable",
        "direct streams unavailable",
      ),
    );
  }

  if (fleet.summary.offline_nodes > 0) {
    return { health: "danger", label: "Critical attention needed", reasons };
  }
  if (reasons.length > 0) {
    return { health: "attention", label: "Attention needed", reasons };
  }

  return {
    health: "healthy",
    label: "Fleet healthy",
    reasons: ["All desired workers running"],
  };
}

export function deriveAttentionItems({
  fleet,
  cameras,
  pendingIncidents,
}: {
  fleet: FleetOverview | null | undefined;
  cameras: Camera[];
  pendingIncidents: PendingIncident[];
}): AttentionItem[] {
  const items: AttentionItem[] = [];
  const missingWorkers = fleet
    ? Math.max(0, fleet.summary.desired_workers - fleet.summary.running_workers)
    : 0;

  if (pendingIncidents.length > 0) {
    items.push({
      id: "pending-evidence",
      health: "attention",
      title: "Evidence waiting for review",
      detail: plural(pendingIncidents.length, "pending evidence record"),
      href: "/incidents",
    });
  }

  if (fleet && (missingWorkers > 0 || fleet.summary.offline_nodes > 0)) {
    items.push({
      id: "workers",
      health: fleet.summary.offline_nodes > 0 ? "danger" : "attention",
      title: "Edge or central workers need attention",
      detail:
        missingWorkers > 0
          ? plural(
              missingWorkers,
              "worker is not running",
              "workers are not running",
            )
          : plural(
              fleet.summary.offline_nodes,
              "node is offline",
              "nodes are offline",
            ),
      href: "/settings",
    });
  }

  if (fleet && fleet.summary.native_unavailable_cameras > 0) {
    items.push({
      id: "direct-streams",
      health: "attention",
      title: "Direct streams unavailable",
      detail: affectedSceneDetail(
        cameras,
        fleet.delivery_diagnostics
          .filter((diagnostic) => diagnostic.native_status?.available === false)
          .map((diagnostic) => diagnostic.camera_id),
      ),
      href: "/settings",
    });
  }

  if (fleet && fleet.summary.stale_nodes > 0) {
    items.push({
      id: "stale-nodes",
      health: "attention",
      title: "Node heartbeats stale",
      detail: plural(
        fleet.summary.stale_nodes,
        "node heartbeat is stale",
        "node heartbeats are stale",
      ),
      href: "/settings",
    });
  }

  return items.sort((a, b) => severityRank(b.health) - severityRank(a.health));
}

export function deriveDeploymentPosture({
  sites,
  cameras,
  fleet,
  pendingIncidents,
}: {
  sites: Pick<Site, "id">[];
  cameras: Camera[];
  fleet: FleetOverview | null | undefined;
  pendingIncidents: PendingIncident[];
}): DeploymentPosture {
  return {
    siteCount: sites.length,
    sceneCount: cameras.length,
    centralScenes: cameras.filter(
      (camera) => camera.processing_mode === "central",
    ).length,
    edgeScenes: cameras.filter((camera) => camera.processing_mode === "edge")
      .length,
    hybridScenes: cameras.filter(
      (camera) => camera.processing_mode === "hybrid",
    ).length,
    assignedEdgeNodes: new Set(
      cameras
        .map((camera) => camera.edge_node_id)
        .filter((nodeId): nodeId is string => Boolean(nodeId)),
    ).size,
    pendingEvidence: pendingIncidents.length,
    privacyConfiguredScenes: cameras.filter(
      (camera) => derivePrivacyPosture(camera).health === "healthy",
    ).length,
    fleetHealth: deriveFleetHealth(fleet),
  };
}

export function derivePrivacyPosture(camera: Camera): HealthSignal {
  if (camera.privacy.blur_faces && camera.privacy.blur_plates) {
    return { health: "healthy", label: "Face/plate filtering configured" };
  }
  if (camera.privacy.blur_faces || camera.privacy.blur_plates) {
    return { health: "attention", label: "Partial privacy controls" };
  }
  if (
    camera.processing_mode === "edge" ||
    camera.processing_mode === "hybrid"
  ) {
    return { health: "attention", label: "Edge processing configured" };
  }
  if (camera.browser_delivery.native_status?.available) {
    return { health: "unknown", label: "Direct/native delivery available" };
  }
  return { health: "unknown", label: "Privacy posture not reported" };
}

export function deriveSceneReadinessRows({
  cameras,
  sites = [],
  fleet,
  framesByCamera = {},
}: {
  cameras: Camera[];
  sites?: Pick<Site, "id" | "name">[];
  fleet: FleetOverview | null | undefined;
  framesByCamera?: Record<string, TelemetryFrame | undefined>;
}): SceneHealthRow[] {
  const workersByCamera = new Map(
    fleet?.camera_workers.map((worker) => [worker.camera_id, worker]) ?? [],
  );
  const diagnosticsByCamera = new Map(
    fleet?.delivery_diagnostics.map((diagnostic) => [
      diagnostic.camera_id,
      diagnostic,
    ]) ?? [],
  );
  const sitesById = new Map(sites.map((site) => [site.id, site.name]));

  return cameras.map((camera) => {
    const worker = workersByCamera.get(camera.id);
    const diagnostic = diagnosticsByCamera.get(camera.id);
    const privacy = derivePrivacyPosture(camera);
    const delivery = deriveDeliverySignal(camera, diagnostic);
    const transport = deriveTransportSignal(camera);
    const liveRendition = deriveLiveRenditionSignal(camera, diagnostic);
    const telemetry = deriveTelemetrySignal(framesByCamera[camera.id]);
    const workerSignal = deriveWorkerSignal(worker);
    const rules = deriveRuleRuntimeSignal(worker?.rule_runtime);
    const readiness = deriveReadinessSignal({
      camera,
      worker: workerSignal,
      delivery,
      privacy,
      telemetry,
    });
    const overall = mostSevere([
      readiness,
      privacy,
      workerSignal,
      delivery,
      telemetry,
    ]);
    const action = deriveAction({
      readiness,
      worker: workerSignal,
      delivery,
      telemetry,
    });

    return {
      cameraId: camera.id,
      cameraName: camera.name,
      siteName: sitesById.get(camera.site_id) ?? "Unassigned site",
      nodeLabel:
        worker?.node_hostname ?? diagnostic?.assigned_node_id ?? "Central",
      processingMode: camera.processing_mode,
      readiness,
      overall,
      privacy,
      worker: workerSignal,
      rules,
      delivery,
      transport,
      liveRendition,
      telemetry,
      actionHref: action.href,
      actionLabel: action.label,
    };
  });
}

function deriveRuleRuntimeSignal(
  ruleRuntime: FleetRuleRuntime | undefined,
): HealthSignal {
  if (!ruleRuntime || ruleRuntime.load_status === "not_configured") {
    return {
      health: "unknown",
      label: "No active rules",
      detail: "not configured",
    };
  }

  const countLabel = plural(
    ruleRuntime.configured_rule_count,
    "active rule",
    "active rules",
  );
  const detailParts = [
    formatReason(ruleRuntime.load_status),
    ruleRuntime.effective_rule_hash?.slice(0, 12),
    ruleRuntime.latest_rule_event_at
      ? formatRuleEventTime(ruleRuntime.latest_rule_event_at)
      : null,
  ].filter((part): part is string => Boolean(part));

  if (ruleRuntime.load_status === "loaded") {
    return {
      health: "healthy",
      label: countLabel,
      detail: detailParts.join(" - "),
    };
  }
  if (ruleRuntime.load_status === "stale") {
    return {
      health: "attention",
      label: countLabel,
      detail: detailParts.join(" - "),
    };
  }
  return {
    health: "unknown",
    label: countLabel,
    detail: detailParts.join(" - "),
  };
}

function deriveWorkerSignal(
  worker: FleetCameraWorker | undefined,
): HealthSignal {
  if (!worker) {
    return { health: "unknown", label: "Worker not reported" };
  }
  if (worker.runtime_status === "running") {
    return { health: "healthy", label: "Worker running" };
  }
  if (worker.runtime_status === "stale") {
    return {
      health: "attention",
      label: "Worker stale",
      detail: worker.detail ?? undefined,
    };
  }
  if (worker.runtime_status === "offline") {
    return {
      health: "danger",
      label: "Worker offline",
      detail: worker.detail ?? undefined,
    };
  }
  if (worker.runtime_status === "not_reported") {
    return {
      health: "unknown",
      label: "Worker not reported",
      detail: worker.detail ?? undefined,
    };
  }
  return {
    health: "unknown",
    label: "Worker not reported",
    detail: worker.detail ?? undefined,
  };
}

function deriveDeliverySignal(
  camera: Camera,
  diagnostic: FleetDeliveryDiagnostic | undefined,
): HealthSignal {
  const nativeStatus =
    diagnostic?.native_status ?? camera.browser_delivery.native_status;
  const defaultProfile =
    diagnostic?.default_profile ?? camera.browser_delivery.default_profile;

  if (nativeStatus?.available === true) {
    return { health: "healthy", label: "Native stream available" };
  }
  if (nativeStatus?.available === false) {
    return {
      health: defaultProfile === "native" ? "danger" : "attention",
      label: "Direct stream unavailable",
      detail: formatReason(nativeStatus.reason),
    };
  }
  if (camera.browser_delivery.default_profile) {
    return { health: "attention", label: "Delivery profile selected" };
  }
  return { health: "unknown", label: "Delivery not reported" };
}

function deriveTransportSignal(camera: Camera): HealthSignal {
  const delivery = camera.browser_delivery;
  const profileName = delivery.delivery_profile_name;
  const mode = delivery.delivery_mode;
  if (profileName) {
    return {
      health: "healthy",
      label: profileName,
      detail: mode ? `${formatReason(mode)} transport` : undefined,
    };
  }
  if (mode) {
    return {
      health: "healthy",
      label: `${formatReason(mode)} transport`,
    };
  }
  return { health: "unknown", label: "Inherited transport" };
}

function deriveLiveRenditionSignal(
  camera: Camera,
  diagnostic: FleetDeliveryDiagnostic | undefined,
): HealthSignal {
  const defaultProfile =
    diagnostic?.default_profile ?? camera.browser_delivery.default_profile;
  const profile =
    diagnostic?.available_profiles?.find(
      (candidate) => candidate.id === defaultProfile,
    ) ??
    camera.browser_delivery.profiles?.find(
      (candidate) => candidate.id === defaultProfile,
    );
  const nativeStatus =
    diagnostic?.native_status ?? camera.browser_delivery.native_status;
  const label =
    typeof profile?.label === "string" && profile.label.length > 0
      ? profile.label
      : formatBrowserDeliveryProfileId(defaultProfile);

  if (defaultProfile === "native" && nativeStatus?.available === false) {
    return {
      health: "danger",
      label,
      detail: formatReason(nativeStatus.reason),
    };
  }

  return {
    health: "healthy",
    label,
    detail: diagnostic?.selected_stream_mode
      ? `${formatReason(diagnostic.selected_stream_mode)} stream`
      : undefined,
  };
}

function formatBrowserDeliveryProfileId(profileId: string): string {
  if (profileId === "native") {
    return "Native clean";
  }
  if (profileId === "annotated") {
    return "Annotated source";
  }
  const match = /^(\d+p)(\d+)$/.exec(profileId);
  if (match) {
    return `${match[1]} / ${match[2]} fps`;
  }
  return profileId;
}

function deriveTelemetrySignal(
  frame: TelemetryFrame | undefined,
): HealthSignal {
  const status = getHeartbeatStatus(frame);

  if (status === "fresh") {
    return { health: "healthy", label: "Telemetry live" };
  }
  if (status === "stale") {
    return { health: "attention", label: "Telemetry stale" };
  }
  return { health: "unknown", label: "Awaiting telemetry" };
}

function deriveReadinessSignal({
  camera,
  worker,
  delivery,
  privacy,
  telemetry,
}: {
  camera: Camera;
  worker: HealthSignal;
  delivery: HealthSignal;
  privacy: HealthSignal;
  telemetry: HealthSignal;
}): HealthSignal {
  const missingSetup: string[] = [];

  if (!camera.source_capability) {
    missingSetup.push("source capability");
  }
  if (!camera.processing_mode) {
    missingSetup.push("processing mode");
  }
  if (privacy.health === "unknown") {
    missingSetup.push("privacy posture");
  }
  if (camera.zones.length === 0 && camera.attribute_rules.length === 0) {
    missingSetup.push("zones or rules");
  }
  if (camera.active_classes.length === 0 && !camera.runtime_vocabulary) {
    missingSetup.push("model classes");
  }
  if (!camera.browser_delivery.default_profile) {
    missingSetup.push("delivery profile");
  }

  if (missingSetup.length > 0) {
    return {
      health: "attention",
      label: "Needs setup",
      detail: `Missing ${missingSetup.join(", ")}`,
    };
  }
  if (worker.health === "danger" || delivery.health === "danger") {
    return { health: "danger", label: "Needs attention" };
  }
  if (worker.health === "attention" || delivery.health === "attention") {
    return { health: "attention", label: "Needs attention" };
  }
  if (telemetry.health === "attention") {
    return { health: "attention", label: "Needs attention" };
  }
  if (worker.health === "unknown" || delivery.health === "unknown") {
    return { health: "unknown", label: "Unknown" };
  }
  return { health: "healthy", label: "Ready" };
}

function deriveAction({
  readiness,
  worker,
  delivery,
  telemetry,
}: {
  readiness: HealthSignal;
  worker: HealthSignal;
  delivery: HealthSignal;
  telemetry: HealthSignal;
}): { href: string; label: string } {
  if (readiness.label === "Needs setup") {
    return { href: "/cameras", label: "Review setup" };
  }
  if (delivery.health === "danger" || delivery.health === "attention") {
    return { href: "/settings", label: "Inspect delivery" };
  }
  if (
    worker.health === "danger" ||
    worker.health === "attention" ||
    worker.health === "unknown"
  ) {
    return { href: "/settings", label: "Inspect operations" };
  }
  if (telemetry.health === "attention") {
    return { href: "/live", label: "Inspect telemetry" };
  }
  return { href: "/live", label: "Open live" };
}

function mostSevere(signals: HealthSignal[]): HealthSignal {
  return signals.reduce<HealthSignal>(
    (current, signal) =>
      severityRank(signal.health) > severityRank(current.health)
        ? signal
        : current,
    { health: "healthy", label: "Ready" },
  );
}

function severityRank(health: OperationalHealth): number {
  if (health === "danger") return 3;
  if (health === "attention") return 2;
  if (health === "unknown") return 1;
  return 0;
}

function affectedSceneDetail(cameras: Camera[], cameraIds: string[]): string {
  const names = cameraIds
    .map((cameraId) => cameras.find((camera) => camera.id === cameraId)?.name)
    .filter((name): name is string => Boolean(name));

  if (names.length === 0) {
    return plural(
      cameraIds.length,
      "scene needs delivery review",
      "scenes need delivery review",
    );
  }

  if (names.length <= 2) {
    return names.join(", ");
  }

  return `${names.slice(0, 2).join(", ")} and ${names.length - 2} more`;
}

function formatReason(reason: string | null | undefined): string | undefined {
  return reason ? reason.replaceAll("_", " ") : undefined;
}

function formatRuleEventTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function plural(
  count: number,
  singular: string,
  pluralLabel = `${singular}s`,
): string {
  return `${count} ${count === 1 ? singular : pluralLabel}`;
}
