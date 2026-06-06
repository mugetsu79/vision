import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import {
  asRecord,
  humanizeKey,
  scalarText,
  textValue,
  type JsonRecord,
  type MaritimeVesselLinkStatus,
} from "./types";

const transportLabels: Record<string, string> = {
  satellite: "Satellite",
  lte: "LTE",
  "5g": "5G",
  wifi: "Wi-Fi",
  fiber: "Fiber",
  ethernet: "Ethernet",
  other: "Other",
};

type LinkConnectionPanelProps = {
  linkStatus?: MaritimeVesselLinkStatus | JsonRecord | null;
};

export function LinkConnectionPanel({ linkStatus }: LinkConnectionPanelProps) {
  const status = asRecord(linkStatus);
  const activeConnection = asRecord(status.active_connection);
  const budget = asRecord(status.budget);
  const latestProbe = asRecord(status.latest_probe);
  const queueDepth = asRecord(status.queue_depth);
  const connections = Array.isArray(status.connections)
    ? status.connections.map(asRecord)
    : [];
  const activeTransport = textValue(activeConnection.transport_kind, "");

  return (
    <WorkspaceSurface className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
            Connectivity
          </p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--vz-text-primary)]">
            Active connection
          </h2>
        </div>
        <StatusToneBadge tone={connectionTone(textValue(activeConnection.status, ""))}>
          {humanizeKey(textValue(activeConnection.status, textValue(status.link_state)))}
        </StatusToneBadge>
      </div>

      <div className="mt-4 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-4 py-3">
        <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
          {textValue(activeConnection.label, "No active connection")}
        </p>
        <p className="mt-2 text-xs text-[var(--vz-text-muted)]">
          {transportLabels[activeTransport] ?? "No transport selected"} ·{" "}
          {humanizeKey(textValue(activeConnection.availability_scope, "always"))}
        </p>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {Object.entries(transportLabels).map(([transport, label]) => (
          <span
            className={`rounded-full border px-3 py-1 text-xs ${
              transport === activeTransport
                ? "border-[rgba(118,224,255,0.38)] bg-[rgba(23,52,70,0.56)] text-[var(--vz-lens-cerulean)]"
                : "border-[color:var(--vz-hair)] bg-white/[0.025] text-[var(--vz-text-secondary)]"
            }`}
            key={transport}
          >
            {label}
          </span>
        ))}
      </div>

      <dl className="mt-5 grid gap-3 sm:grid-cols-3">
        <Metric
          label="Budget"
          value={`${formatBytes(budget.monthly_bytes)} monthly`}
          detail={`${formatBytes(budget.bulk_daily_bytes)} bulk daily`}
        />
        <Metric
          label="Latest probe"
          value={`${scalarText(latestProbe.latency_ms, "0")} ms`}
          detail={`${scalarText(latestProbe.throughput_mbps, "0")} Mbps · ${scalarText(latestProbe.packet_loss_percent, "0")}% loss`}
        />
        <Metric
          label="Evidence queue"
          value={scalarText(queueDepth.evidence)}
          detail={`${scalarText(queueDepth.bulk)} bulk / ${scalarText(queueDepth.safety)} safety`}
        />
      </dl>

      {connections.length ? (
        <div className="mt-4 grid gap-2">
          {connections.slice(0, 4).map((connection) => (
            <div
              className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.02] px-3 py-2 text-sm"
              key={textValue(connection.id, textValue(connection.label))}
            >
              <span className="font-medium text-[var(--vz-text-primary)]">
                {textValue(connection.label, "Connection")}
              </span>
              <span className="text-xs text-[var(--vz-text-muted)]">
                {transportLabels[textValue(connection.transport_kind, "")] ??
                  textValue(connection.transport_kind, "other")}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </WorkspaceSurface>
  );
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3">
      <dt className="text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
        {label}
      </dt>
      <dd className="mt-2 text-sm font-semibold text-[var(--vz-text-primary)]">
        {value}
      </dd>
      <dd className="mt-1 text-xs text-[var(--vz-text-muted)]">{detail}</dd>
    </div>
  );
}

function connectionTone(status: string) {
  if (status === "online") {
    return "healthy";
  }
  if (status === "offline" || status === "blocked") {
    return "danger";
  }
  if (status === "degraded" || status === "recovering") {
    return "attention";
  }
  return "muted";
}

function formatBytes(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "0 GB";
  }
  return `${(value / 1_000_000_000).toFixed(value >= 1_000_000_000 ? 1 : 2)} GB`;
}
