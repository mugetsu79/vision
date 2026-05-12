import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import type { components } from "@/lib/api.generated";

type TriggerRuleSummary = components["schemas"]["TriggerRuleSummary"];

type DetectionContext = {
  class_name?: unknown;
  zone_id?: unknown;
  confidence?: unknown;
};

type IncidentRuleSummaryProps = {
  triggerRule?: TriggerRuleSummary | null;
  detection?: DetectionContext | null;
};

export function IncidentRuleSummary({
  triggerRule,
  detection,
}: IncidentRuleSummaryProps) {
  if (!triggerRule) {
    return null;
  }

  const predicate = triggerRule.predicate;
  const className =
    stringValue(detection?.class_name) ??
    predicate?.class_names?.[0] ??
    "Any class";
  const zoneId =
    stringValue(detection?.zone_id) ?? predicate?.zone_ids?.[0] ?? "Any zone";
  const confidence = confidenceLabel(detection?.confidence);

  return (
    <section
      aria-label="Trigger rule"
      className="rounded-md border border-white/8 px-3 py-3"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
            Trigger rule
          </h4>
          <p className="mt-1 break-words text-sm font-semibold text-[#eef4ff]">
            {triggerRule.name}
          </p>
        </div>
        <StatusToneBadge tone={severityTone(triggerRule.severity)}>
          {triggerRule.severity}
        </StatusToneBadge>
      </div>

      <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
        <RuleFact label="Type" value={triggerRule.incident_type} />
        <RuleFact label="Action" value={triggerRule.action} />
        <RuleFact label="Cooldown" value={`${triggerRule.cooldown_seconds}s`} />
        <RuleFact label="Rule hash" value={shortHash(triggerRule.rule_hash)} />
        <RuleFact label="Detection class" value={className} />
        <RuleFact label="Zone" value={zoneId} />
        <RuleFact
          label="Confidence"
          value={confidence ?? thresholdLabel(predicate?.min_confidence)}
        />
      </dl>
    </section>
  );
}

function RuleFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7894bd]">
        {label}
      </dt>
      <dd className="mt-1 truncate text-[#d8e2f2]" title={value}>
        {value}
      </dd>
    </div>
  );
}

function severityTone(
  severity: TriggerRuleSummary["severity"],
): "healthy" | "attention" | "danger" | "muted" {
  if (severity === "critical") {
    return "danger";
  }
  if (severity === "warning") {
    return "attention";
  }
  return "muted";
}

function shortHash(value: string | null | undefined) {
  return value ? value.slice(0, 12) : "Not captured";
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function confidenceLabel(value: unknown) {
  return typeof value === "number" && Number.isFinite(value)
    ? `${Math.round(value * 100)}%`
    : null;
}

function thresholdLabel(value: number | undefined) {
  return typeof value === "number"
    ? `${Math.round(value * 100)}% threshold`
    : "Unknown";
}
