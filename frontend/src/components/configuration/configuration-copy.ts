import type { OperatorConfigKind } from "@/hooks/use-configuration";

export const CONFIGURATION_KIND_LABELS: Record<OperatorConfigKind, string> = {
  evidence_storage: "Evidence storage",
  stream_delivery: "Transport",
  runtime_selection: "Runtime",
  privacy_policy: "Privacy and retention",
  llm_provider: "LLM and policy",
  operations_mode: "Operations",
};

export const CONFIGURATION_KINDS = Object.keys(
  CONFIGURATION_KIND_LABELS,
) as OperatorConfigKind[];

export function labelForKind(kind: OperatorConfigKind) {
  return CONFIGURATION_KIND_LABELS[kind];
}
