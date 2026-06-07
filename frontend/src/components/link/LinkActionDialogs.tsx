import { useEffect, useState, type FormEvent } from "react";

import { asRecord, numberValue, textValue } from "@/components/link/types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogCloseButton, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type {
  LinkConnectionCreateInput,
  LinkConnectionPatchInput,
  LinkProbeCreateInput,
} from "@/hooks/use-link";

type ConnectionMode = "create" | "edit";

type ConnectionFormState = {
  label: string;
  transportKind: LinkConnectionCreateInput["transport_kind"];
  provider: string;
  status: LinkConnectionCreateInput["status"];
  priorityRank: string;
  availabilityScope: LinkConnectionCreateInput["availability_scope"];
  metered: boolean;
  monthlyBytes: string;
  bulkDailyBytes: string;
  expectedDownlinkMbps: string;
  expectedUplinkMbps: string;
  expectedLatencyMs: string;
  packetLossPercent: string;
};

type LinkConnectionDialogProps = {
  open: boolean;
  mode: ConnectionMode;
  connection?: unknown;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (
    payload: LinkConnectionCreateInput | LinkConnectionPatchInput,
  ) => Promise<void>;
};

type LinkProbeDialogProps = {
  open: boolean;
  connections: unknown[];
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: LinkProbeCreateInput) => Promise<void>;
};

const defaultConnectionForm: ConnectionFormState = {
  label: "",
  transportKind: "other",
  provider: "",
  status: "unknown",
  priorityRank: "100",
  availabilityScope: "always",
  metered: false,
  monthlyBytes: "",
  bulkDailyBytes: "",
  expectedDownlinkMbps: "",
  expectedUplinkMbps: "",
  expectedLatencyMs: "",
  packetLossPercent: "",
};

export function LinkConnectionDialog({
  open,
  mode,
  connection,
  isSubmitting = false,
  onClose,
  onSubmit,
}: LinkConnectionDialogProps) {
  const [form, setForm] = useState<ConnectionFormState>(defaultConnectionForm);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const isEdit = mode === "edit";

  useEffect(() => {
    if (!open) {
      setForm(defaultConnectionForm);
      setSubmitError(null);
      return;
    }

    const item = asRecord(connection);
    setForm({
      label: textValue(item.label, ""),
      transportKind: transportKindValue(item.transport_kind),
      provider: textValue(item.provider, ""),
      status: statusValue(item.status),
      priorityRank: String(numberValue(item.priority_rank, 100)),
      availabilityScope: availabilityScopeValue(item.availability_scope),
      metered: item.metered === true,
      monthlyBytes: optionalNumberText(item.monthly_bytes),
      bulkDailyBytes: optionalNumberText(item.bulk_daily_bytes),
      expectedDownlinkMbps: optionalNumberText(item.expected_downlink_mbps),
      expectedUplinkMbps: optionalNumberText(item.expected_uplink_mbps),
      expectedLatencyMs: optionalNumberText(item.expected_latency_ms),
      packetLossPercent: optionalNumberText(item.packet_loss_percent),
    });
    setSubmitError(null);
  }, [connection, open]);

  function updateField<K extends keyof ConnectionFormState>(
    field: K,
    value: ConnectionFormState[K],
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    try {
      await onSubmit(buildConnectionPayload(form, isEdit));
      onClose();
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Unable to save link connection.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      title={isEdit ? "Edit connection" : "Add connection"}
      description="Configure a site link path and expected performance envelope."
    >
      <form
        className="max-h-[calc(100vh-12rem)] space-y-5 overflow-y-auto pr-1"
        onSubmit={(event) => void handleSubmit(event)}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <LabeledInput
            label="Connection label"
            value={form.label}
            required
            onChange={(value) => updateField("label", value)}
            placeholder="Primary fiber"
          />
          <LabeledSelect
            label="Transport kind"
            value={form.transportKind}
            onChange={(value) =>
              updateField("transportKind", transportKindValue(value))
            }
          >
            {transportKinds.map((kind) => (
              <option key={kind} value={kind}>
                {transportLabel(kind)}
              </option>
            ))}
          </LabeledSelect>
          <LabeledInput
            label="Provider"
            value={form.provider}
            onChange={(value) => updateField("provider", value)}
            placeholder="Provider"
          />
          <LabeledSelect
            label="Connection status"
            value={form.status}
            onChange={(value) => updateField("status", statusValue(value))}
          >
            {connectionStatuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </LabeledSelect>
          <LabeledInput
            label="Priority rank"
            type="number"
            min="0"
            value={form.priorityRank}
            onChange={(value) => updateField("priorityRank", value)}
          />
          <LabeledSelect
            label="Availability scope"
            value={form.availabilityScope}
            onChange={(value) =>
              updateField("availabilityScope", availabilityScopeValue(value))
            }
          >
            {availabilityScopes.map((scope) => (
              <option key={scope} value={scope}>
                {scope}
              </option>
            ))}
          </LabeledSelect>
        </div>
        <label className="flex items-center gap-3 text-sm text-[var(--vz-text-secondary)]">
          <input
            type="checkbox"
            checked={form.metered}
            onChange={(event) => updateField("metered", event.target.checked)}
          />
          <span>Metered connection</span>
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <LabeledInput
            label="Monthly bytes"
            type="number"
            min="0"
            value={form.monthlyBytes}
            onChange={(value) => updateField("monthlyBytes", value)}
          />
          <LabeledInput
            label="Bulk daily bytes"
            type="number"
            min="0"
            value={form.bulkDailyBytes}
            onChange={(value) => updateField("bulkDailyBytes", value)}
          />
          <LabeledInput
            label="Expected downlink Mbps"
            type="number"
            min="0"
            step="0.1"
            value={form.expectedDownlinkMbps}
            onChange={(value) => updateField("expectedDownlinkMbps", value)}
          />
          <LabeledInput
            label="Expected uplink Mbps"
            type="number"
            min="0"
            step="0.1"
            value={form.expectedUplinkMbps}
            onChange={(value) => updateField("expectedUplinkMbps", value)}
          />
          <LabeledInput
            label="Expected latency ms"
            type="number"
            min="0"
            value={form.expectedLatencyMs}
            onChange={(value) => updateField("expectedLatencyMs", value)}
          />
          <LabeledInput
            label="Packet loss percent"
            type="number"
            min="0"
            step="0.01"
            value={form.packetLossPercent}
            onChange={(value) => updateField("packetLossPercent", value)}
          />
        </div>
        {submitError ? (
          <p role="alert" className="text-sm font-medium text-[#ff9ca6]">
            {submitError}
          </p>
        ) : null}
        <DialogFooter>
          <DialogCloseButton onClick={onClose}>Cancel</DialogCloseButton>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save connection"}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}

export function LinkProbeDialog({
  open,
  connections,
  isSubmitting = false,
  onClose,
  onSubmit,
}: LinkProbeDialogProps) {
  const [connectionId, setConnectionId] = useState("");
  const [latencyMs, setLatencyMs] = useState("0");
  const [throughputMbps, setThroughputMbps] = useState("0");
  const [packetLossPercent, setPacketLossPercent] = useState("0");
  const [reachable, setReachable] = useState(true);
  const [source, setSource] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setConnectionId("");
      setLatencyMs("0");
      setThroughputMbps("0");
      setPacketLossPercent("0");
      setReachable(true);
      setSource("");
      setSubmitError(null);
    }
  }, [open]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    try {
      await onSubmit({
        connection_id: connectionId || null,
        latency_ms: requiredNumber(latencyMs),
        throughput_mbps: requiredNumber(throughputMbps),
        packet_loss_percent: requiredNumber(packetLossPercent),
        reachable,
        source,
      });
      onClose();
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Unable to record probe.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      title="Record probe"
      description="Capture observed link health for the selected site."
    >
      <form className="space-y-5" onSubmit={(event) => void handleSubmit(event)}>
        <LabeledSelect
          label="Probe connection"
          value={connectionId}
          onChange={setConnectionId}
        >
          <option value="">No specific connection</option>
          {connections.map((connection, index) => {
            const item = asRecord(connection);
            const id = textValue(item.id, `connection-${index}`);
            return (
              <option key={id} value={id}>
                {textValue(item.label, id)}
              </option>
            );
          })}
        </LabeledSelect>
        <div className="grid gap-4 sm:grid-cols-2">
          <LabeledInput
            label="Latency ms"
            type="number"
            min="0"
            value={latencyMs}
            onChange={setLatencyMs}
          />
          <LabeledInput
            label="Throughput Mbps"
            type="number"
            min="0"
            step="0.1"
            value={throughputMbps}
            onChange={setThroughputMbps}
          />
          <LabeledInput
            label="Packet loss percent"
            type="number"
            min="0"
            step="0.01"
            value={packetLossPercent}
            onChange={setPacketLossPercent}
          />
          <LabeledInput
            label="Probe source"
            value={source}
            required
            onChange={setSource}
            placeholder="packless-lab"
          />
        </div>
        <label className="flex items-center gap-3 text-sm text-[var(--vz-text-secondary)]">
          <input
            type="checkbox"
            checked={reachable}
            onChange={(event) => setReachable(event.target.checked)}
          />
          <span>Reachable</span>
        </label>
        {submitError ? (
          <p role="alert" className="text-sm font-medium text-[#ff9ca6]">
            {submitError}
          </p>
        ) : null}
        <DialogFooter>
          <DialogCloseButton onClick={onClose}>Cancel</DialogCloseButton>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save probe"}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}

type LabeledInputProps = {
  label: string;
  value: string;
  placeholder?: string;
  required?: boolean;
  type?: string;
  min?: string;
  step?: string;
  onChange: (value: string) => void;
};

function LabeledInput({
  label,
  value,
  placeholder,
  required = false,
  type = "text",
  min,
  step,
  onChange,
}: LabeledInputProps) {
  return (
    <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
      <span>{label}</span>
      <Input
        aria-label={label}
        type={type}
        min={min}
        step={step}
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}

type LabeledSelectProps = {
  label: string;
  value: string;
  children: React.ReactNode;
  onChange: (value: string) => void;
};

function LabeledSelect({
  label,
  value,
  children,
  onChange,
}: LabeledSelectProps) {
  return (
    <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
      <span>{label}</span>
      <Select
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </Select>
    </label>
  );
}

function buildConnectionPayload(
  form: ConnectionFormState,
  isEdit: boolean,
): LinkConnectionCreateInput | LinkConnectionPatchInput {
  const payload = {
    label: form.label,
    transport_kind: form.transportKind,
    provider: nullableText(form.provider),
    status: form.status,
    priority_rank: requiredNumber(form.priorityRank, 100),
    availability_scope: form.availabilityScope,
    metered: form.metered,
    monthly_bytes: optionalNumber(form.monthlyBytes),
    bulk_daily_bytes: optionalNumber(form.bulkDailyBytes),
    expected_downlink_mbps: optionalNumber(form.expectedDownlinkMbps),
    expected_uplink_mbps: optionalNumber(form.expectedUplinkMbps),
    expected_latency_ms: optionalNumber(form.expectedLatencyMs),
    packet_loss_percent: optionalNumber(form.packetLossPercent),
  };

  return isEdit ? payload : (payload satisfies LinkConnectionCreateInput);
}

function nullableText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function optionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return requiredNumber(trimmed);
}

function requiredNumber(value: string, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function optionalNumberText(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "";
}

const transportKinds = [
  "satellite",
  "lte",
  "5g",
  "wifi",
  "fiber",
  "ethernet",
  "other",
] as const;

const connectionStatuses = [
  "unknown",
  "online",
  "degraded",
  "offline",
  "blocked",
  "recovering",
] as const;

const availabilityScopes = [
  "always",
  "remote",
  "nearby",
  "local",
  "maintenance",
] as const;

function transportKindValue(value: unknown): LinkConnectionCreateInput["transport_kind"] {
  return transportKinds.find((kind) => kind === value) ?? "other";
}

function statusValue(value: unknown): LinkConnectionCreateInput["status"] {
  return connectionStatuses.find((status) => status === value) ?? "unknown";
}

function availabilityScopeValue(
  value: unknown,
): LinkConnectionCreateInput["availability_scope"] {
  return availabilityScopes.find((scope) => scope === value) ?? "always";
}

function transportLabel(kind: LinkConnectionCreateInput["transport_kind"]) {
  if (kind === "lte") {
    return "LTE";
  }
  if (kind === "wifi") {
    return "Wi-Fi";
  }
  return kind;
}
