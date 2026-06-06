import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import {
  asRecord,
  humanizeKey,
  scalarText,
  textValue,
  type FleetOpsVessel,
  type JsonRecord,
  type MaritimeVesselLinkStatus,
} from "./types";

type VoyageTimelineProps = {
  vessel?: FleetOpsVessel | null;
  telemetry?: JsonRecord | null;
  linkStatus?: MaritimeVesselLinkStatus | JsonRecord | null;
  evidenceContext?: JsonRecord | null;
};

export function VoyageTimeline({
  vessel,
  telemetry,
  linkStatus,
  evidenceContext,
}: VoyageTimelineProps) {
  const vesselMetadata = asRecord(vessel?.metadata);
  const templates = getStringList(vesselMetadata.templates);
  const ais = asRecord(asRecord(telemetry).latest_ais_position);
  const context = asRecord(evidenceContext);
  const link = asRecord(linkStatus);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
      <WorkspaceSurface className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
              Voyage timeline
            </p>
            <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
              {textValue(vessel?.name, "Selected vessel")}
            </h2>
          </div>
          <StatusToneBadge tone="attention">
            {humanizeKey(textValue(link.link_state, "recovering"))}
          </StatusToneBadge>
        </div>
        <ol className="mt-5 grid gap-3">
          {["Departure window", "Port call", "Evidence handover"].map((item) => (
            <li
              className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-4 py-3"
              key={item}
            >
              <p className="text-sm font-medium text-[var(--vz-text-primary)]">
                {item}
              </p>
              <p className="mt-1 text-xs text-[var(--vz-text-muted)]">
                Maritime context remains attached to the incident record.
              </p>
            </li>
          ))}
        </ol>
        <div className="mt-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
            Templates
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(templates.length ? templates : ["Gangway access"]).map((template) => (
              <span
                className="rounded-full border border-[color:var(--vz-hair)] bg-white/[0.035] px-3 py-1 text-xs text-[var(--vz-text-secondary)]"
                key={template}
              >
                {template}
              </span>
            ))}
          </div>
        </div>
      </WorkspaceSurface>
      <div className="grid gap-4">
        <WorkspaceSurface className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Latest AIS
          </p>
          <p className="mt-3 text-lg font-semibold text-[var(--vz-text-primary)]">
            {textValue(ais.navigational_status, "under way")}
          </p>
          <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
            {scalarText(ais.latitude, "0.00")}, {scalarText(ais.longitude, "0.00")}{" "}
            at {scalarText(ais.speed_over_ground)} kn
          </p>
        </WorkspaceSurface>
        <WorkspaceSurface className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Evidence context
          </p>
          <p className="mt-3 text-lg font-semibold text-[var(--vz-text-primary)]">
            {textValue(context.vessel_name, textValue(vessel?.name, "Vessel"))}
          </p>
          <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
            {textValue(context.port_name, "Open water")} /{" "}
            {humanizeKey(textValue(context.resolution_source, "runtime context"))}
          </p>
        </WorkspaceSurface>
      </div>
    </div>
  );
}

function getStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}
