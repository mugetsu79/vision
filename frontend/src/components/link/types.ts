import type { LinkSiteSummary } from "@/hooks/use-link";

export type LinkSiteSummaryItem = LinkSiteSummary;
export type LinkModel =
  | "direct"
  | "provider_managed"
  | "logical_overlay"
  | "inventory_only";
export type LinkVisibility = "full" | "handoff_only" | "overlay_only" | "none";
export type MonitoringProbeType = "icmp" | "tcp" | "http" | "https";
export type MonitoringSourceType =
  | "manual"
  | "backend_synthetic"
  | "edge_agent"
  | "provider_api"
  | "import";
export type LinkProbeSampleKind = "manual" | "automated" | "imported";
export type MonitoringPurpose =
  | "vezor_control"
  | "gateway"
  | "provider_edge"
  | "partner_endpoint"
  | "custom";
export type MonitoringConfig = {
  enabled: boolean;
  source_type: MonitoringSourceType;
  interval_seconds?: number | null;
};
export type MonitoringTarget = {
  id: string;
  label: string;
  address: string;
  probe_type: MonitoringProbeType;
  port?: number | null;
  purpose: MonitoringPurpose;
  expected_latency_ms?: number | null;
  monitoring: MonitoringConfig;
};
export type LinkPathMetadata = {
  link_model: LinkModel;
  visibility: LinkVisibility;
  external_reference?: string | null;
  monitoring_targets: MonitoringTarget[];
};
export type LinkPriorityLane = (typeof linkPriorityLanes)[number];
export type LinkPolicyFormState = {
  priorityOrder: LinkPriorityLane[];
  degradedPauses: LinkPriorityLane[];
  darkAllows: LinkPriorityLane[];
  pauseBulkWhenDailyBudgetExhausted: boolean;
  avoidMeteredForBulkWhenBudgetExhausted: boolean;
};

export const linkModels = [
  "direct",
  "provider_managed",
  "logical_overlay",
  "inventory_only",
] as const;
export const linkVisibilities = [
  "full",
  "handoff_only",
  "overlay_only",
  "none",
] as const;
export const monitoringProbeTypes = ["icmp", "tcp", "http", "https"] as const;
export const monitoringSourceTypes = [
  "manual",
  "backend_synthetic",
  "edge_agent",
  "provider_api",
  "import",
] as const;
export const monitoringPurposes = [
  "vezor_control",
  "gateway",
  "provider_edge",
  "partner_endpoint",
  "custom",
] as const;
export const linkPriorityLanes = [
  "safety",
  "evidence",
  "telemetry",
  "bulk",
] as const;

export function textValue(value: unknown, fallback = "Not recorded") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function numberValue(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

export function linkPathMetadata(value: unknown): LinkPathMetadata {
  const candidate = asRecord(value);
  const metadata = "metadata" in candidate ? asRecord(candidate.metadata) : candidate;

  return {
    external_reference: nullableTextValue(metadata.external_reference),
    link_model: enumValue(metadata.link_model, linkModels, "direct"),
    monitoring_targets: monitoringTargets(metadata.monitoring_targets),
    visibility: enumValue(metadata.visibility, linkVisibilities, "full"),
  };
}

export function normalizeLinkPolicy(policies: unknown): LinkPolicyFormState {
  const policyRoot = asRecord(policies);
  const policy = asRecord(policyRoot.policy ?? policies);
  const backpressure = asRecord(policy.backpressure);

  return {
    avoidMeteredForBulkWhenBudgetExhausted: booleanValue(
      backpressure.avoid_metered_for_bulk_when_budget_exhausted,
      true,
    ),
    darkAllows: laneList(backpressure.dark_allows, ["safety"]),
    degradedPauses: laneList(backpressure.degraded_pauses, [
      "telemetry",
      "bulk",
    ]),
    pauseBulkWhenDailyBudgetExhausted: booleanValue(
      backpressure.pause_bulk_when_daily_budget_exhausted,
      true,
    ),
    priorityOrder: priorityOrder(policy.priority_order),
  };
}

export function buildLinkPolicy(form: LinkPolicyFormState) {
  return {
    backpressure: {
      avoid_metered_for_bulk_when_budget_exhausted:
        form.avoidMeteredForBulkWhenBudgetExhausted,
      dark_allows: laneList(form.darkAllows, ["safety"]),
      degraded_pauses: laneList(form.degradedPauses, ["telemetry", "bulk"]),
      pause_bulk_when_daily_budget_exhausted:
        form.pauseBulkWhenDailyBudgetExhausted,
    },
    priority_order: priorityOrder(form.priorityOrder),
  };
}

export function linkModelLabel(value: LinkModel) {
  const labels: Record<LinkModel, string> = {
    direct: "Direct",
    inventory_only: "Inventory only",
    logical_overlay: "Logical overlay",
    provider_managed: "Provider managed",
  };
  return labels[value];
}

export function linkVisibilityLabel(value: LinkVisibility) {
  const labels: Record<LinkVisibility, string> = {
    full: "Full visibility",
    handoff_only: "Handoff only",
    none: "No visibility",
    overlay_only: "Overlay only",
  };
  return labels[value];
}

export function laneLabel(value: LinkPriorityLane) {
  const labels: Record<LinkPriorityLane, string> = {
    bulk: "Bulk",
    evidence: "Evidence",
    safety: "Safety",
    telemetry: "Telemetry",
  };
  return labels[value];
}

export function monitoringSourceTypeLabel(value: MonitoringSourceType) {
  const labels: Record<MonitoringSourceType, string> = {
    backend_synthetic: "Backend synthetic",
    edge_agent: "Edge agent",
    import: "Imported samples",
    manual: "Manual samples",
    provider_api: "Provider/API",
  };
  return labels[value];
}

export function monitoringSourceLabel(
  value: MonitoringSourceType,
  intervalSeconds?: number | null,
) {
  if (value === "backend_synthetic" && intervalSeconds) {
    return `Backend synthetic every ${formatInterval(intervalSeconds)}`;
  }
  const labels: Record<MonitoringSourceType, string> = {
    backend_synthetic: "Backend synthetic",
    edge_agent: "Awaiting edge agent",
    import: "External import",
    manual: "Manual samples only",
    provider_api: "Provider/API import",
  };
  return labels[value];
}

export function probeSampleSourceLabel(probe: unknown) {
  const item = asRecord(probe);
  const sourceType = enumValue(
    item.source_type,
    monitoringSourceTypes,
    "manual",
  );
  const sourceLabel = textValue(item.source_label, "");
  const source = textValue(item.source, "");
  if (sourceLabel) {
    return `${monitoringSourceTypeLabel(sourceType)} from ${sourceLabel}`;
  }
  if (source) {
    return `${monitoringSourceTypeLabel(sourceType)} from ${source}`;
  }
  return monitoringSourceTypeLabel(sourceType);
}

export function probeSampleTargetLabel(probe: unknown) {
  const item = asRecord(probe);
  const targetLabel = textValue(item.target_label, "");
  const targetAddress = textValue(item.target_address, "");
  if (targetLabel && targetAddress) {
    return `${targetLabel} (${targetAddress})`;
  }
  return targetLabel || targetAddress || "No target";
}

function monitoringTargets(value: unknown): MonitoringTarget[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const targets: MonitoringTarget[] = [];
  for (const [index, target] of value.entries()) {
    const item = asRecord(target);
    const address = textValue(item.address, "");
    const label = textValue(item.label, "");
    if (!address && !label) {
      continue;
    }
    targets.push({
      address,
      expected_latency_ms: optionalNumericValue(item.expected_latency_ms),
      id: textValue(item.id, `target-${index + 1}`),
      label,
      monitoring: monitoringConfig(item.monitoring),
      port: optionalNumericValue(item.port),
      probe_type: enumValue(item.probe_type, monitoringProbeTypes, "icmp"),
      purpose: enumValue(item.purpose, monitoringPurposes, "custom"),
    });
  }
  return targets;
}

function monitoringConfig(value: unknown): MonitoringConfig {
  const config = asRecord(value);
  const sourceType = enumValue(
    config.source_type,
    monitoringSourceTypes,
    "manual",
  );
  return {
    enabled: booleanValue(config.enabled, sourceType !== "manual"),
    interval_seconds: optionalNumericValue(config.interval_seconds),
    source_type: sourceType,
  };
}

function formatInterval(seconds: number) {
  if (seconds >= 3600 && seconds % 3600 === 0) {
    return `${seconds / 3600} hr`;
  }
  if (seconds >= 60 && seconds % 60 === 0) {
    return `${seconds / 60} min`;
  }
  return `${seconds} sec`;
}

function priorityOrder(value: unknown): LinkPriorityLane[] {
  const normalized = laneList(value, [...linkPriorityLanes]);
  const missing = linkPriorityLanes.filter((lane) => !normalized.includes(lane));
  return [...normalized, ...missing];
}

function laneList(
  value: unknown,
  fallback: LinkPriorityLane[],
): LinkPriorityLane[] {
  if (!Array.isArray(value)) {
    return [...fallback];
  }

  const lanes: LinkPriorityLane[] = [];
  for (const lane of value) {
    if (isLane(lane) && !lanes.includes(lane)) {
      lanes.push(lane);
    }
  }
  return lanes.length > 0 ? lanes : [...fallback];
}

function isLane(value: unknown): value is LinkPriorityLane {
  return linkPriorityLanes.some((lane) => lane === value);
}

function enumValue<T extends string>(
  value: unknown,
  allowed: readonly T[],
  fallback: T,
): T {
  return allowed.find((item) => item === value) ?? fallback;
}

function booleanValue(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

function nullableTextValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function optionalNumericValue(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
