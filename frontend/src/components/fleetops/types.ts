import type { components } from "@/lib/api.generated";

export type JsonRecord = Record<string, unknown>;

export type FleetOpsVessel = JsonRecord & {
  id?: string;
  name?: string;
  site_id?: string;
  active?: boolean;
  metadata?: JsonRecord;
};

export type BillingUsageItem = JsonRecord & {
  meter_key?: string;
  label?: string;
  quantity?: string;
};

export type BillingUsagePayload = JsonRecord & {
  items?: BillingUsageItem[];
};

export type SupportReadinessCheck = JsonRecord & {
  key?: string;
  label?: string;
  status?: string;
  source?: string;
};

export type DiagnosticsGroup = JsonRecord & {
  id?: string;
  label?: string;
  status?: string;
  source?: string;
  checks?: Array<SupportReadinessCheck | string>;
  next_action?: string;
};

export type SupportDiagnosticsPayload = JsonRecord & {
  label?: string;
  groups?: DiagnosticsGroup[] | Record<string, DiagnosticsGroup>;
};

export type OnboardingCheck = JsonRecord & {
  key?: string;
  label?: string;
  status?: string;
};

export type OnboardingChecksPayload = JsonRecord & {
  checks?: OnboardingCheck[];
};

export type InvoiceRun = components["schemas"]["InvoiceRunResponse"];
export type SupportBundle = components["schemas"]["SupportBundleResponse"];
export type MaritimeVesselLinkStatus =
  components["schemas"]["MaritimeVesselLinkStatusResponse"];

export function asRecord(value: unknown): JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as JsonRecord)
    : {};
}

export function textValue(value: unknown, fallback = "Unknown"): string {
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}

export function scalarText(value: unknown, fallback = "0"): string {
  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

export function humanizeKey(value: string): string {
  return value.replaceAll("_", " ");
}

export function firstFleetOpsSiteId(vessels: FleetOpsVessel[]): string | null {
  return (
    vessels.find(
      (vessel) =>
        typeof vessel.site_id === "string" && vessel.site_id.trim().length > 0,
    )?.site_id ?? null
  );
}
