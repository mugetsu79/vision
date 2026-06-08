import { useEffect, useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";

import {
  asRecord,
  linkModelLabel,
  linkModels,
  linkPathMetadata,
  linkVisibilities,
  linkVisibilityLabel,
  linkProbeLossMethods,
  monitoringSourceTypeLabel,
  monitoringSourceTypes,
  monitoringProbeTypes,
  monitoringPurposes,
  numberValue,
  probeLossMethodLabel,
  textValue,
  type LinkProbeLossMethod,
  type LinkModel,
  type LinkPathMetadata,
  type LinkTargetSiteOption,
  type LinkVisibility,
  type MonitoringSourceType,
  type MonitoringProbeType,
  type MonitoringPurpose,
  type MonitoringTarget,
} from "@/components/link/types";
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

type MonitoringTargetFormState = {
  id: string;
  label: string;
  address: string;
  probeType: MonitoringProbeType;
  port: string;
  purpose: MonitoringPurpose;
  targetSiteId: string;
  expectedLatencyMs: string;
  monitoringEnabled: boolean;
  monitoringSourceType: MonitoringSourceType;
  monitoringIntervalSeconds: string;
  lossMethod: LinkProbeLossMethod;
  lossPacketCount: string;
  lossPacketSpacingMs: string;
  lossTimeoutMs: string;
  lossDscp: string;
  reflectorProfileId: string;
  reflectorAddress: string;
  reflectorPort: string;
  reflectorMode: string;
  reflectorKeyId: string;
  throughputTestUrl: string;
  throughputTestMaxBytes: string;
};

type ConnectionFormState = {
  label: string;
  linkModel: LinkModel;
  visibility: LinkVisibility;
  externalReference: string;
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
  targets: MonitoringTargetFormState[];
};

type LinkConnectionDialogProps = {
  open: boolean;
  mode: ConnectionMode;
  connection?: unknown;
  targetSiteOptions?: LinkTargetSiteOption[];
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (
    payload: LinkConnectionCreateInput | LinkConnectionPatchInput,
  ) => Promise<void>;
};

type LinkProbeDialogProps = {
  open: boolean;
  connections: unknown[];
  targets: ProbeTargetOption[];
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: LinkProbeCreateInput) => Promise<void>;
};

export type ProbeTargetOption = MonitoringTarget & {
  connection_id?: string | null;
  connection_label?: string | null;
};

const defaultConnectionForm: ConnectionFormState = {
  label: "",
  linkModel: "direct",
  visibility: "full",
  externalReference: "",
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
  targets: [],
};

function defaultTargetForm(): MonitoringTargetFormState {
  return {
    address: "",
    expectedLatencyMs: "",
    id: createTargetId(),
    label: "",
    lossDscp: "",
    lossMethod: "icmp_sequence",
    lossPacketCount: "20",
    lossPacketSpacingMs: "100",
    lossTimeoutMs: "1000",
    monitoringEnabled: false,
    monitoringIntervalSeconds: "300",
    monitoringSourceType: "manual",
    port: "443",
    probeType: "https",
    purpose: "vezor_control",
    reflectorAddress: "",
    reflectorKeyId: "",
    reflectorMode: "reply",
    reflectorPort: "8622",
    reflectorProfileId: "master-reflector-default",
    targetSiteId: "",
    throughputTestMaxBytes: "1048576",
    throughputTestUrl: "",
  };
}

export function LinkConnectionDialog({
  open,
  mode,
  connection,
  targetSiteOptions = [],
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
    const metadata = linkPathMetadata(item.metadata);
    setForm({
      label: textValue(item.label, ""),
      linkModel: metadata.link_model,
      visibility: metadata.visibility,
      externalReference: textValue(metadata.external_reference, ""),
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
      targets: metadata.monitoring_targets.map((target) => ({
        id: target.id,
        label: target.label,
        address: target.address,
        probeType: target.probe_type,
        port: optionalNumberText(target.port),
        purpose: target.purpose,
        targetSiteId: textValue(target.target_site_id, ""),
        expectedLatencyMs: optionalNumberText(target.expected_latency_ms),
        lossDscp: optionalNumberText(target.loss_dscp),
        lossMethod: lossMethodValue(target.loss_method),
        lossPacketCount: optionalNumberText(target.loss_packet_count, "20"),
        lossPacketSpacingMs: optionalNumberText(
          target.loss_packet_spacing_ms,
          "100",
        ),
        lossTimeoutMs: optionalNumberText(target.loss_timeout_ms, "1000"),
        monitoringEnabled: target.monitoring.enabled,
        monitoringSourceType: target.monitoring.source_type,
        monitoringIntervalSeconds: optionalNumberText(
          target.monitoring.interval_seconds,
          "300",
        ),
        reflectorAddress: textValue(target.reflector_address, ""),
        reflectorKeyId: textValue(target.reflector_key_id, ""),
        reflectorMode: textValue(target.reflector_mode, "reply"),
        reflectorPort: optionalNumberText(target.reflector_port, "8622"),
        reflectorProfileId: textValue(
          target.reflector_profile_id,
          "master-reflector-default",
        ),
        throughputTestMaxBytes: optionalNumberText(
          target.throughput_test_max_bytes,
          "1048576",
        ),
        throughputTestUrl: textValue(target.throughput_test_url, ""),
      })),
    });
    setSubmitError(null);
  }, [connection, open]);

  function updateField<K extends keyof ConnectionFormState>(
    field: K,
    value: ConnectionFormState[K],
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateTargetField<K extends keyof MonitoringTargetFormState>(
    index: number,
    field: K,
    value: MonitoringTargetFormState[K],
  ) {
    setForm((current) => ({
      ...current,
      targets: current.targets.map((target, targetIndex) => {
        if (targetIndex !== index) {
          return target;
        }
        if (field === "probeType") {
          const probeType = value as MonitoringProbeType;
          return {
            ...target,
            [field]: value,
            lossMethod:
              probeType === "udp" && target.lossMethod === "icmp_sequence"
                ? "udp_sequence"
                : probeType !== "udp" && target.lossMethod === "udp_sequence"
                  ? "icmp_sequence"
                  : target.lossMethod,
            port:
              target.port === "" || target.port === defaultPort(target.probeType)
                ? defaultPort(probeType)
                : target.port,
          };
        }
        if (field === "lossMethod") {
          const lossMethod = value as LinkProbeLossMethod;
          return {
            ...target,
            lossMethod,
            port:
              target.port === "" || target.port === defaultPort(target.probeType)
                ? defaultPort(lossMethod === "udp_sequence" ? "udp" : "icmp")
                : target.port,
            probeType: lossMethod === "udp_sequence" ? "udp" : "icmp",
          };
        }
        return { ...target, [field]: value };
      }),
    }));
  }

  function addTarget() {
    setForm((current) => ({
      ...current,
      targets: [...current.targets, defaultTargetForm()],
    }));
  }

  function applyTargetPreset(index: number, targetSiteId: string) {
    const targetSite = targetSiteOptions.find(
      (option) => option.site_id === targetSiteId,
    );
    setForm((current) => ({
      ...current,
      targets: current.targets.map((target, targetIndex) => {
        if (targetIndex !== index) {
          return target;
        }
        if (!targetSite) {
          return { ...target, targetSiteId: "" };
        }
        return {
          ...target,
          label: targetSite.site_name,
          lossMethod: "udp_sequence",
          lossPacketCount: "50",
          lossPacketSpacingMs: "100",
          lossTimeoutMs: "1000",
          monitoringEnabled: true,
          monitoringSourceType: "edge_agent",
          port: "",
          probeType: "udp",
          purpose: "vezor_control",
          reflectorAddress: target.address,
          reflectorKeyId: "master-reflector-default",
          reflectorMode: "reply",
          reflectorPort: "8622",
          reflectorProfileId: "master-reflector-default",
          targetSiteId: targetSite.site_id,
        };
      }),
    }));
  }

  function removeTarget(index: number) {
    setForm((current) => ({
      ...current,
      targets: current.targets.filter((_, targetIndex) => targetIndex !== index),
    }));
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
          : "Unable to save link path.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      title={isEdit ? "Edit link path" : "Add link path"}
      description="Configure the logical path, monitoring target, and expected performance envelope."
    >
      <form
        className="max-h-[calc(100vh-12rem)] space-y-5 overflow-y-auto pr-1"
        onSubmit={(event) => void handleSubmit(event)}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <LabeledInput
            label="Link path label"
            value={form.label}
            required
            onChange={(value) => updateField("label", value)}
            placeholder="Managed SD-WAN overlay"
          />
          <LabeledSelect
            label="Link model"
            value={form.linkModel}
            onChange={(value) => updateField("linkModel", linkModelValue(value))}
          >
            {linkModels.map((model) => (
              <option key={model} value={model}>
                {linkModelLabel(model)}
              </option>
            ))}
          </LabeledSelect>
          <LabeledInput
            label="Provider"
            value={form.provider}
            onChange={(value) => updateField("provider", value)}
            placeholder="Provider or MSP"
          />
          <LabeledInput
            label="External reference"
            value={form.externalReference}
            onChange={(value) => updateField("externalReference", value)}
            placeholder="Circuit, tenant, tunnel, or ticket ID"
          />
          <LabeledSelect
            label="Visibility"
            value={form.visibility}
            onChange={(value) =>
              updateField("visibility", linkVisibilityValue(value))
            }
          >
            {linkVisibilities.map((visibility) => (
              <option key={visibility} value={visibility}>
                {linkVisibilityLabel(visibility)}
              </option>
            ))}
          </LabeledSelect>
          <LabeledSelect
            label="Transport visible to Vezor"
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
          <LabeledSelect
            label="Link status"
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
          <span>Metered path</span>
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
        <div className="space-y-3 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-[family-name:var(--vz-font-display)] text-sm font-semibold text-[var(--vz-text-primary)]">
              Monitoring targets
            </h3>
            <Button type="button" variant="ghost" onClick={addTarget}>
              <Plus className="mr-2 size-4" aria-hidden="true" />
              Add monitoring target
            </Button>
          </div>
          {form.targets.length === 0 ? (
            <p className="text-xs text-[var(--vz-text-muted)]">
              No monitoring targets recorded.
            </p>
          ) : (
            form.targets.map((target, index) => (
              <div
                key={target.id || index}
                className="grid gap-4 rounded-[var(--vz-r-sm)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite-up)] p-3 sm:grid-cols-2"
              >
                {targetSiteOptions.length > 0 ? (
                  <LabeledSelect
                    label="Target preset"
                    value={target.targetSiteId}
                    onChange={(value) => applyTargetPreset(index, value)}
                  >
                    <option value="">Custom target</option>
                    {targetSiteOptions.map((option) => (
                      <option key={option.site_id} value={option.site_id}>
                        {option.site_name}
                      </option>
                    ))}
                  </LabeledSelect>
                ) : null}
                <LabeledInput
                  label="Target label"
                  value={target.label}
                  required
                  onChange={(value) => updateTargetField(index, "label", value)}
                  placeholder="Vezor ingest"
                />
                <LabeledInput
                  label="Target address"
                  value={target.address}
                  required
                  onChange={(value) => updateTargetField(index, "address", value)}
                  placeholder="fqdn.example.com or 203.0.113.10"
                />
                <LabeledSelect
                  label="Probe type"
                  value={target.probeType}
                  onChange={(value) =>
                    updateTargetField(index, "probeType", probeTypeValue(value))
                  }
                >
                  {monitoringProbeTypes.map((probeType) => (
                    <option key={probeType} value={probeType}>
                      {probeType.toUpperCase()}
                    </option>
                  ))}
                </LabeledSelect>
                <LabeledInput
                  label="Target port"
                  type="number"
                  min="1"
                  value={target.port}
                  onChange={(value) => updateTargetField(index, "port", value)}
                />
                <LabeledSelect
                  label="Target purpose"
                  value={target.purpose}
                  onChange={(value) =>
                    updateTargetField(index, "purpose", purposeValue(value))
                  }
                >
                  {monitoringPurposes.map((purpose) => (
                    <option key={purpose} value={purpose}>
                      {purposeLabel(purpose)}
                    </option>
                  ))}
                </LabeledSelect>
                <LabeledInput
                  label="Target expected latency ms"
                  type="number"
                  min="0"
                  value={target.expectedLatencyMs}
                  onChange={(value) =>
                    updateTargetField(index, "expectedLatencyMs", value)
                  }
                />
                <label className="flex items-center gap-3 self-end text-sm text-[var(--vz-text-secondary)]">
                  <input
                    type="checkbox"
                    checked={target.monitoringEnabled}
                    onChange={(event) =>
                      updateTargetField(
                        index,
                        "monitoringEnabled",
                        event.target.checked,
                      )
                    }
                  />
                  <span>Monitoring enabled</span>
                </label>
                <LabeledSelect
                  label="Monitoring source"
                  value={target.monitoringSourceType}
                  onChange={(value) =>
                    updateTargetField(
                      index,
                      "monitoringSourceType",
                      monitoringSourceTypeValue(value),
                    )
                  }
                >
                  {monitoringSourceTypes.map((sourceType) => (
                    <option key={sourceType} value={sourceType}>
                      {monitoringSourceTypeLabel(sourceType)}
                    </option>
                  ))}
                </LabeledSelect>
                <LabeledInput
                  label="Monitoring interval seconds"
                  type="number"
                  min="30"
                  value={target.monitoringIntervalSeconds}
                  onChange={(value) =>
                    updateTargetField(
                      index,
                      "monitoringIntervalSeconds",
                      value,
                    )
                  }
                />
                <LabeledInput
                  label="Manual throughput URL"
                  value={target.throughputTestUrl}
                  onChange={(value) =>
                    updateTargetField(index, "throughputTestUrl", value)
                  }
                  placeholder="https://example.com/speed.bin"
                />
                <LabeledInput
                  label="Manual throughput byte cap"
                  type="number"
                  min="1"
                  value={target.throughputTestMaxBytes}
                  onChange={(value) =>
                    updateTargetField(index, "throughputTestMaxBytes", value)
                  }
                />
                {target.monitoringSourceType === "edge_agent" ? (
                  <>
                    <LabeledSelect
                      label="Loss method"
                      value={target.lossMethod}
                      onChange={(value) =>
                        updateTargetField(index, "lossMethod", lossMethodValue(value))
                      }
                    >
                      {linkProbeLossMethods.map((method) => (
                        <option key={method} value={method}>
                          {probeLossMethodLabel(method)}
                        </option>
                      ))}
                    </LabeledSelect>
                    <LabeledInput
                      label="Loss packet count"
                      type="number"
                      min="1"
                      max="10000"
                      value={target.lossPacketCount}
                      onChange={(value) =>
                        updateTargetField(index, "lossPacketCount", value)
                      }
                    />
                    <LabeledInput
                      label="Loss DSCP"
                      type="number"
                      min="0"
                      max="63"
                      value={target.lossDscp}
                      onChange={(value) => updateTargetField(index, "lossDscp", value)}
                    />
                    {target.lossMethod === "udp_sequence" ? (
                      <>
                        <LabeledInput
                          label="Packet spacing ms"
                          type="number"
                          min="1"
                          value={target.lossPacketSpacingMs}
                          onChange={(value) =>
                            updateTargetField(
                              index,
                              "lossPacketSpacingMs",
                              value,
                            )
                          }
                        />
                        <LabeledInput
                          label="Reply timeout ms"
                          type="number"
                          min="1"
                          value={target.lossTimeoutMs}
                          onChange={(value) =>
                            updateTargetField(index, "lossTimeoutMs", value)
                          }
                        />
                        <LabeledInput
                          label="Reflector address"
                          value={target.reflectorAddress}
                          onChange={(value) =>
                            updateTargetField(index, "reflectorAddress", value)
                          }
                          placeholder="master.vezor.example"
                        />
                        <LabeledInput
                          label="Reflector UDP port"
                          type="number"
                          min="1"
                          max="65535"
                          value={target.reflectorPort}
                          onChange={(value) =>
                            updateTargetField(index, "reflectorPort", value)
                          }
                        />
                        <LabeledSelect
                          label="Reflector mode"
                          value={target.reflectorMode}
                          onChange={(value) =>
                            updateTargetField(index, "reflectorMode", value)
                          }
                        >
                          <option value="reply">Reply to edge agent</option>
                        </LabeledSelect>
                        <LabeledInput
                          label="Reflector key ID"
                          value={target.reflectorKeyId}
                          onChange={(value) =>
                            updateTargetField(index, "reflectorKeyId", value)
                          }
                          placeholder="master-reflector-default"
                        />
                        <LabeledInput
                          label="Reflector profile ID"
                          value={target.reflectorProfileId}
                          onChange={(value) =>
                            updateTargetField(index, "reflectorProfileId", value)
                          }
                          placeholder="master-reflector-default"
                        />
                      </>
                    ) : null}
                  </>
                ) : null}
                <div className="sm:col-span-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => removeTarget(index)}
                    aria-label={`Remove ${target.label || "monitoring target"}`}
                  >
                    <Trash2 className="mr-2 size-4" aria-hidden="true" />
                    Remove target
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
        {submitError ? (
          <p role="alert" className="text-sm font-medium text-[#ff9ca6]">
            {submitError}
          </p>
        ) : null}
        <DialogFooter>
          <DialogCloseButton onClick={onClose}>Cancel</DialogCloseButton>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save link path"}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}

export function LinkProbeDialog({
  open,
  connections,
  targets,
  isSubmitting = false,
  onClose,
  onSubmit,
}: LinkProbeDialogProps) {
  const [targetId, setTargetId] = useState("");
  const [connectionId, setConnectionId] = useState("");
  const [latencyMs, setLatencyMs] = useState("0");
  const [throughputMbps, setThroughputMbps] = useState("0");
  const [packetLossPercent, setPacketLossPercent] = useState("0");
  const [reachable, setReachable] = useState(true);
  const [source, setSource] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setTargetId("");
      setConnectionId("");
      setLatencyMs("0");
      setThroughputMbps("0");
      setPacketLossPercent("0");
      setReachable(true);
      setSource("");
      setSubmitError(null);
    }
  }, [open]);

  function handleTargetChange(value: string) {
    setTargetId(value);
    const target = targets.find((item) => item.id === value);
    if (target?.connection_id) {
      setConnectionId(target.connection_id);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);
    const target = targets.find((item) => item.id === targetId);
    const sourceLabel = source.trim();

    try {
      await onSubmit({
        connection_id: target?.connection_id ?? (connectionId || null),
        latency_ms: requiredNumber(latencyMs),
        throughput_mbps: requiredNumber(throughputMbps),
        packet_loss_percent: requiredNumber(packetLossPercent),
        probe_type: target?.probe_type ?? "manual",
        reachable,
        sample_kind: "manual",
        source: sourceLabel ? `manual:${sourceLabel}` : "manual:operator",
        source_label: sourceLabel || null,
        source_type: "manual",
        target_address: target?.address ?? null,
        target_id: target?.id ?? null,
        target_label: target?.label ?? null,
        target_site_id: target?.target_site_id ?? null,
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
      title="Add manual sample"
      description="Capture an operator-observed measurement for one monitoring target or the link path as a whole."
    >
      <form className="space-y-5" onSubmit={(event) => void handleSubmit(event)}>
        <LabeledSelect
          label="Sample target"
          value={targetId}
          onChange={handleTargetChange}
        >
          <option value="">No specific target</option>
          {targets.map((target) => (
            <option key={target.id} value={target.id}>
              {target.label} - {target.address}
            </option>
          ))}
        </LabeledSelect>
        <LabeledSelect
          label="Sample connection"
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
            label="Sample source label"
            value={source}
            required
            onChange={setSource}
            placeholder="operator-console"
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
            {isSubmitting ? "Saving..." : "Save sample"}
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
  max?: string;
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
  max,
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
        max={max}
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
    metadata: buildConnectionMetadata(form),
  };

  return isEdit ? payload : (payload satisfies LinkConnectionCreateInput);
}

function buildConnectionMetadata(form: ConnectionFormState): LinkPathMetadata {
  return {
    external_reference: nullableText(form.externalReference),
    link_model: form.linkModel,
    monitoring_targets: form.targets.map((target) => {
      const usesUdpSequence = target.lossMethod === "udp_sequence";
      return {
        address: target.address.trim(),
        expected_latency_ms: optionalNumber(target.expectedLatencyMs),
        id: target.id,
        label: target.label.trim(),
        loss_dscp: optionalNumber(target.lossDscp),
        loss_method: target.lossMethod,
        loss_packet_count: optionalNumber(target.lossPacketCount),
        loss_packet_spacing_ms: usesUdpSequence
          ? optionalNumber(target.lossPacketSpacingMs)
          : null,
        loss_timeout_ms: usesUdpSequence
          ? optionalNumber(target.lossTimeoutMs)
          : null,
        monitoring: {
          enabled: target.monitoringEnabled,
          interval_seconds: optionalNumber(target.monitoringIntervalSeconds),
          source_type: target.monitoringSourceType,
        },
        port: optionalNumber(target.port),
        probe_type: target.probeType,
        purpose: target.purpose,
        reflector_address: usesUdpSequence
          ? nullableText(target.reflectorAddress) ?? nullableText(target.address)
          : null,
        reflector_key_id: usesUdpSequence ? nullableText(target.reflectorKeyId) : null,
        reflector_mode: usesUdpSequence ? nullableText(target.reflectorMode) : null,
        reflector_port: usesUdpSequence ? optionalNumber(target.reflectorPort) : null,
        reflector_profile_id: usesUdpSequence
          ? nullableText(target.reflectorProfileId)
          : null,
        target_site_id: nullableText(target.targetSiteId),
        throughput_test_max_bytes: optionalNumber(target.throughputTestMaxBytes),
        throughput_test_url: nullableText(target.throughputTestUrl),
      };
    }),
    visibility: form.visibility,
  };
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

function optionalNumberText(value: unknown, fallback = "") {
  return typeof value === "number" && Number.isFinite(value)
    ? String(value)
    : fallback;
}

function defaultPort(probeType: MonitoringProbeType) {
  const ports: Record<MonitoringProbeType, string> = {
    http: "80",
    https: "443",
    icmp: "",
    tcp: "",
    udp: "",
  };
  return ports[probeType];
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

function linkModelValue(value: unknown): LinkModel {
  return linkModels.find((model) => model === value) ?? "direct";
}

function linkVisibilityValue(value: unknown): LinkVisibility {
  return linkVisibilities.find((visibility) => visibility === value) ?? "full";
}

function probeTypeValue(value: unknown): MonitoringProbeType {
  return monitoringProbeTypes.find((probeType) => probeType === value) ?? "icmp";
}

function lossMethodValue(value: unknown): LinkProbeLossMethod {
  return (
    linkProbeLossMethods.find((method) => method === value) ?? "icmp_sequence"
  );
}

function monitoringSourceTypeValue(value: unknown): MonitoringSourceType {
  return (
    monitoringSourceTypes.find((sourceType) => sourceType === value) ?? "manual"
  );
}

function purposeValue(value: unknown): MonitoringPurpose {
  return monitoringPurposes.find((purpose) => purpose === value) ?? "custom";
}

function transportLabel(kind: LinkConnectionCreateInput["transport_kind"]) {
  if (kind === "lte") {
    return "LTE";
  }
  if (kind === "5g") {
    return "5G";
  }
  if (kind === "wifi") {
    return "Wi-Fi";
  }
  return kind;
}

function purposeLabel(value: MonitoringPurpose) {
  const labels: Record<MonitoringPurpose, string> = {
    custom: "Custom",
    gateway: "Gateway",
    partner_endpoint: "Partner endpoint",
    provider_edge: "Provider edge",
    vezor_control: "Vezor control",
  };
  return labels[value];
}

function createTargetId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `target-${crypto.randomUUID()}`;
  }
  return `target-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}
