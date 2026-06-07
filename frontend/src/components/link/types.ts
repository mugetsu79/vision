import type { LinkSiteSummary } from "@/hooks/use-link";

export type LinkSiteSummaryItem = LinkSiteSummary;

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
