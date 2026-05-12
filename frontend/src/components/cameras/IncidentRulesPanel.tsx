import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Plus, RefreshCw, Save, ShieldCheck, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { Camera } from "@/hooks/use-cameras";
import {
  useCreateIncidentRule,
  useDeleteIncidentRule,
  useIncidentRules,
  useUpdateIncidentRule,
  useValidateIncidentRule,
  type IncidentRule,
  type IncidentRuleCreate,
} from "@/hooks/use-incident-rules";
import { cn } from "@/lib/utils";

type RuleAction = IncidentRuleCreate["action"];
type RuleSeverity = IncidentRuleCreate["severity"];

type RuleFormState = {
  enabled: boolean;
  name: string;
  incidentType: string;
  severity: RuleSeverity;
  description: string;
  classNames: string[];
  zoneIds: string[];
  minConfidence: number;
  attributesText: string;
  action: RuleAction;
  cooldownSeconds: number;
  webhookUrl: string;
};

type ValidationState =
  | { kind: "idle"; message: string }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

export function IncidentRulesPanel({
  camera,
  onClose,
}: {
  camera: Camera;
  onClose?: () => void;
}) {
  const rulesQuery = useIncidentRules(camera.id);
  const createRule = useCreateIncidentRule(camera.id);
  const updateRule = useUpdateIncidentRule(camera.id);
  const deleteRule = useDeleteIncidentRule(camera.id);
  const validateRule = useValidateIncidentRule(camera.id);
  const rules = useMemo(() => rulesQuery.data ?? [], [rulesQuery.data]);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [form, setForm] = useState<RuleFormState>(() => defaultRuleForm());
  const [validationState, setValidationState] = useState<ValidationState>({
    kind: "idle",
    message: "",
  });
  const [saveError, setSaveError] = useState<string | null>(null);
  const initializedRuleId = useRef<string | null>(null);

  const selectedRule = rules.find((rule) => rule.id === selectedRuleId) ?? null;
  const classOptions = useMemo(
    () => sceneClassOptions(camera, rules),
    [camera, rules],
  );
  const zoneOptions = useMemo(
    () => sceneZoneOptions(camera, rules),
    [camera, rules],
  );
  const isEditing = selectedRule !== null;
  const mutationPending =
    createRule.isPending ||
    updateRule.isPending ||
    deleteRule.isPending ||
    validateRule.isPending;

  useEffect(() => {
    if (rules.length === 0 || initializedRuleId.current !== null) {
      return;
    }
    initializedRuleId.current = rules[0].id;
    setSelectedRuleId(rules[0].id);
    setForm(ruleToForm(rules[0]));
  }, [rules]);

  function selectRule(rule: IncidentRule) {
    initializedRuleId.current = rule.id;
    setSelectedRuleId(rule.id);
    setForm(ruleToForm(rule));
    setValidationState({ kind: "idle", message: "" });
    setSaveError(null);
  }

  function newRule() {
    initializedRuleId.current = "new";
    setSelectedRuleId(null);
    setForm(defaultRuleForm());
    setValidationState({ kind: "idle", message: "" });
    setSaveError(null);
  }

  async function handleValidate() {
    setSaveError(null);
    const payload = formToCreatePayload(form);
    const sampleDetection = sampleDetectionFromPayload(payload);
    try {
      const result = await validateRule.mutateAsync({
        rule: payload,
        sample_detection: sampleDetection,
      });
      if (!result.valid) {
        setValidationState({
          kind: "error",
          message:
            (result.errors ?? []).join("; ") || "Rule validation failed.",
        });
        return;
      }
      setValidationState({
        kind: "success",
        message: result.matches
          ? `Sample matches ${result.normalized_incident_type ?? payload.name}.`
          : `Sample does not match ${result.normalized_incident_type ?? payload.name}.`,
      });
    } catch (error) {
      setValidationState({
        kind: "error",
        message:
          error instanceof Error ? error.message : "Rule validation failed.",
      });
    }
  }

  async function handleSave() {
    setSaveError(null);
    const payload = formToCreatePayload(form);
    if (payload.name.trim() === "") {
      setSaveError("Rule name is required.");
      return;
    }

    try {
      if (selectedRule) {
        const updated = await updateRule.mutateAsync({
          ruleId: selectedRule.id,
          payload,
        });
        initializedRuleId.current = updated?.id ?? selectedRule.id;
        setSelectedRuleId(updated?.id ?? selectedRule.id);
      } else {
        const created = await createRule.mutateAsync(payload);
        if (created?.id) {
          initializedRuleId.current = created.id;
          setSelectedRuleId(created.id);
        }
      }
      setValidationState({ kind: "success", message: "Rule saved." });
    } catch (error) {
      setSaveError(
        error instanceof Error ? error.message : "Failed to save rule.",
      );
    }
  }

  async function handleDelete() {
    if (!selectedRule) {
      return;
    }
    await deleteRule.mutateAsync(selectedRule.id);
    newRule();
  }

  return (
    <section
      aria-labelledby="incident-rules-heading"
      className="rounded-[0.9rem] border border-white/8 bg-[#0b1320] p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
            Incident rules
          </p>
          <h3
            id="incident-rules-heading"
            className="mt-2 text-xl font-semibold text-[#f4f8ff]"
          >
            Incident rules for {camera.name}
          </h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={newRule}>
            <Plus aria-hidden="true" className="mr-2 h-4 w-4" />
            New rule
          </Button>
          {onClose ? (
            <Button variant="ghost" onClick={onClose}>
              <X aria-hidden="true" className="mr-2 h-4 w-4" />
              Close rules
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(18rem,0.9fr)_minmax(32rem,1.4fr)]">
        <div
          data-testid="incident-rule-list"
          className="space-y-2"
          aria-label="Incident rule list"
        >
          {rulesQuery.isLoading ? (
            <p className="text-sm text-[#9eb2cf]">Loading incident rules...</p>
          ) : rules.length === 0 ? (
            <p className="rounded-[0.75rem] border border-white/8 bg-white/[0.03] px-3 py-3 text-sm text-[#9eb2cf]">
              No incident rules
            </p>
          ) : (
            rules.map((rule) => (
              <button
                key={rule.id}
                type="button"
                aria-label={`Edit ${rule.name}`}
                onClick={() => selectRule(rule)}
                className={cn(
                  "w-full rounded-[0.75rem] border px-3 py-3 text-left transition",
                  selectedRuleId === rule.id
                    ? "border-[#5fb7ff] bg-[#0f2438]"
                    : "border-white/8 bg-white/[0.03] hover:border-white/20",
                )}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-[#eef4ff]">
                    {rule.name}
                  </span>
                  <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] uppercase tracking-[0.12em] text-[#9eb2cf]">
                    {rule.enabled ? "enabled" : "disabled"}
                  </span>
                </div>
                <div className="mt-2 grid gap-1 text-xs text-[#93a7c5] sm:grid-cols-2">
                  <span>{rule.incident_type}</span>
                  <span>{rule.severity}</span>
                  <span>{rule.action}</span>
                  <span>{rule.cooldown_seconds}s cooldown</span>
                  <span>{rule.rule_hash.slice(0, 8)}</span>
                  <span>
                    {rule.webhook_url_present
                      ? "Webhook configured"
                      : "No webhook"}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>

        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void handleSave();
          }}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <LabeledField label="Rule name" htmlFor="incident-rule-name">
              <Input
                id="incident-rule-name"
                value={form.name}
                onChange={(event) => setFormValue("name", event.target.value)}
              />
            </LabeledField>
            <LabeledField label="Incident type" htmlFor="incident-rule-type">
              <Input
                id="incident-rule-type"
                value={form.incidentType}
                onChange={(event) =>
                  setFormValue("incidentType", event.target.value)
                }
              />
            </LabeledField>
            <LabeledField label="Severity" htmlFor="incident-rule-severity">
              <Select
                id="incident-rule-severity"
                value={form.severity}
                onChange={(event) =>
                  setFormValue("severity", event.target.value as RuleSeverity)
                }
              >
                <option value="info">info</option>
                <option value="warning">warning</option>
                <option value="critical">critical</option>
              </Select>
            </LabeledField>
            <LabeledField
              label="Cooldown seconds"
              htmlFor="incident-rule-cooldown"
            >
              <Input
                id="incident-rule-cooldown"
                type="number"
                min={0}
                value={form.cooldownSeconds}
                onChange={(event) =>
                  setFormValue("cooldownSeconds", Number(event.target.value))
                }
              />
            </LabeledField>
          </div>

          <fieldset className="rounded-[0.75rem] border border-white/8 bg-black/15 p-3">
            <legend className="px-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#8ea4c7]">
              Classes
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {classOptions.length === 0 ? (
                <span className="text-sm text-[#9eb2cf]">No classes saved</span>
              ) : (
                classOptions.map((className) => (
                  <CheckboxPill
                    key={className}
                    label={`Class ${className}`}
                    checked={form.classNames.includes(className)}
                    onChange={() => toggleArrayValue("classNames", className)}
                  />
                ))
              )}
            </div>
          </fieldset>

          <fieldset className="rounded-[0.75rem] border border-white/8 bg-black/15 p-3">
            <legend className="px-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#8ea4c7]">
              Zones
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {zoneOptions.length === 0 ? (
                <span className="text-sm text-[#9eb2cf]">No zones saved</span>
              ) : (
                zoneOptions.map((zoneId) => (
                  <CheckboxPill
                    key={zoneId}
                    label={`Zone ${zoneId}`}
                    checked={form.zoneIds.includes(zoneId)}
                    onChange={() => toggleArrayValue("zoneIds", zoneId)}
                  />
                ))
              )}
            </div>
          </fieldset>

          <div className="grid gap-3 md:grid-cols-[minmax(12rem,0.8fr)_minmax(16rem,1fr)]">
            <LabeledField
              label="Minimum confidence"
              htmlFor="incident-rule-confidence"
            >
              <div className="grid gap-2">
                <Input
                  id="incident-rule-confidence"
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={form.minConfidence}
                  onChange={(event) =>
                    setFormValue("minConfidence", Number(event.target.value))
                  }
                />
                <input
                  aria-label="Confidence threshold slider"
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={form.minConfidence}
                  onChange={(event) =>
                    setFormValue("minConfidence", Number(event.target.value))
                  }
                  className="h-2 w-full accent-[#5fb7ff]"
                />
              </div>
            </LabeledField>
            <LabeledField
              label="Required attributes"
              htmlFor="incident-rule-attributes"
            >
              <Input
                id="incident-rule-attributes"
                value={form.attributesText}
                placeholder="hi_vis=false"
                onChange={(event) =>
                  setFormValue("attributesText", event.target.value)
                }
              />
            </LabeledField>
          </div>

          <fieldset className="rounded-[0.75rem] border border-white/8 bg-black/15 p-3">
            <legend className="px-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#8ea4c7]">
              Action
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {[
                ["alert", "Alert"],
                ["record_clip", "Record clip"],
                ["webhook", "Webhook"],
              ].map(([value, label]) => (
                <label
                  key={value}
                  className={cn(
                    "inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm transition",
                    form.action === value
                      ? "border-[#5fb7ff] bg-[#0f2438] text-[#eef4ff]"
                      : "border-white/10 bg-white/[0.03] text-[#9eb2cf]",
                  )}
                >
                  <input
                    type="radio"
                    name="incident-rule-action"
                    value={value}
                    checked={form.action === value}
                    onChange={() => setFormValue("action", value as RuleAction)}
                    className="h-3.5 w-3.5 accent-[#5fb7ff]"
                  />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>

          {form.action === "webhook" ? (
            <LabeledField label="Webhook URL" htmlFor="incident-rule-webhook">
              <Input
                id="incident-rule-webhook"
                value={form.webhookUrl}
                onChange={(event) =>
                  setFormValue("webhookUrl", event.target.value)
                }
              />
            </LabeledField>
          ) : null}

          <label className="inline-flex w-fit cursor-pointer items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-[#d8e2f2]">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) =>
                setFormValue("enabled", event.target.checked)
              }
              className="h-4 w-4 accent-[#5fb7ff]"
            />
            Enabled
          </label>

          {validationState.kind === "error" ? (
            <div
              role="alert"
              className="rounded-[0.75rem] border border-[#5a2330] bg-[#241118] px-3 py-2 text-sm text-[#ffc2cd]"
            >
              {validationState.message}
            </div>
          ) : validationState.kind === "success" ? (
            <div
              role="status"
              className="rounded-[0.75rem] border border-[#315f49] bg-[#10231a] px-3 py-2 text-sm text-[#a9dfc0]"
            >
              {validationState.message}
            </div>
          ) : null}

          {saveError ? (
            <div
              role="alert"
              className="rounded-[0.75rem] border border-[#5a2330] bg-[#241118] px-3 py-2 text-sm text-[#ffc2cd]"
            >
              {saveError}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="ghost"
                disabled={mutationPending}
                onClick={() => void handleValidate()}
              >
                <ShieldCheck aria-hidden="true" className="mr-2 h-4 w-4" />
                Validate rule
              </Button>
              <Button type="submit" disabled={mutationPending}>
                {isEditing ? (
                  <Save aria-hidden="true" className="mr-2 h-4 w-4" />
                ) : (
                  <Plus aria-hidden="true" className="mr-2 h-4 w-4" />
                )}
                {isEditing ? "Save rule" : "Create rule"}
              </Button>
            </div>
            {isEditing ? (
              <Button
                type="button"
                variant="ghost"
                disabled={mutationPending}
                className="border-[#5a2330] text-[#ffc2cd] hover:border-[#81404d]"
                onClick={() => void handleDelete()}
              >
                <Trash2 aria-hidden="true" className="mr-2 h-4 w-4" />
                Delete rule
              </Button>
            ) : null}
          </div>

          {rulesQuery.isFetching ? (
            <p className="inline-flex items-center gap-2 text-xs text-[#93a7c5]">
              <RefreshCw aria-hidden="true" className="h-3.5 w-3.5" />
              Refreshing rules
            </p>
          ) : null}
        </form>
      </div>
    </section>
  );

  function setFormValue<Key extends keyof RuleFormState>(
    key: Key,
    value: RuleFormState[Key],
  ) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function toggleArrayValue(key: "classNames" | "zoneIds", value: string) {
    setForm((current) => {
      const values = current[key];
      return {
        ...current,
        [key]: values.includes(value)
          ? values.filter((item) => item !== value)
          : [...values, value],
      };
    });
  }
}

function LabeledField({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <label
      className="grid gap-1.5 text-sm font-medium text-[#d8e2f2]"
      htmlFor={htmlFor}
    >
      <span>{label}</span>
      {children}
    </label>
  );
}

function CheckboxPill({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label
      className={cn(
        "inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm transition",
        checked
          ? "border-[#5fb7ff] bg-[#0f2438] text-[#eef4ff]"
          : "border-white/10 bg-white/[0.03] text-[#9eb2cf]",
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="h-3.5 w-3.5 accent-[#5fb7ff]"
      />
      {label}
    </label>
  );
}

function defaultRuleForm(): RuleFormState {
  return {
    enabled: true,
    name: "",
    incidentType: "",
    severity: "warning",
    description: "",
    classNames: [],
    zoneIds: [],
    minConfidence: 0.5,
    attributesText: "",
    action: "record_clip",
    cooldownSeconds: 0,
    webhookUrl: "",
  };
}

function ruleToForm(rule: IncidentRule): RuleFormState {
  return {
    enabled: rule.enabled,
    name: rule.name,
    incidentType: rule.incident_type,
    severity: rule.severity,
    description: rule.description ?? "",
    classNames: rule.predicate.class_names ?? [],
    zoneIds: rule.predicate.zone_ids ?? [],
    minConfidence: rule.predicate.min_confidence,
    attributesText: attributesToText(rule.predicate.attributes ?? {}),
    action: rule.action,
    cooldownSeconds: rule.cooldown_seconds,
    webhookUrl: "",
  };
}

function formToCreatePayload(form: RuleFormState): IncidentRuleCreate {
  return {
    enabled: form.enabled,
    name: form.name.trim(),
    incident_type: form.incidentType.trim() || null,
    severity: form.severity,
    description: form.description.trim() || null,
    predicate: {
      class_names: form.classNames,
      zone_ids: form.zoneIds,
      min_confidence: clampConfidence(form.minConfidence),
      attributes: parseAttributes(form.attributesText),
    },
    action: form.action,
    cooldown_seconds: Math.max(0, Math.trunc(form.cooldownSeconds || 0)),
    webhook_url:
      form.action === "webhook" && form.webhookUrl.trim()
        ? form.webhookUrl.trim()
        : null,
  };
}

function sampleDetectionFromPayload(payload: IncidentRuleCreate) {
  return {
    class_name: payload.predicate?.class_names?.[0] ?? null,
    zone_id: payload.predicate?.zone_ids?.[0] ?? null,
    confidence: payload.predicate?.min_confidence ?? 0.5,
    attributes: payload.predicate?.attributes ?? {},
  };
}

function sceneClassOptions(camera: Camera, rules: IncidentRule[]) {
  const values = new Set<string>();
  for (const className of camera.active_classes ?? []) {
    if (className.trim()) {
      values.add(className.trim());
    }
  }
  for (const term of camera.runtime_vocabulary?.terms ?? []) {
    if (term.trim()) {
      values.add(term.trim());
    }
  }
  for (const rule of rules) {
    for (const className of rule.predicate.class_names ?? []) {
      if (className.trim()) {
        values.add(className.trim());
      }
    }
  }
  return Array.from(values).sort((left, right) => left.localeCompare(right));
}

function sceneZoneOptions(camera: Camera, rules: IncidentRule[]) {
  const values = new Set<string>();
  for (const zone of camera.zones ?? []) {
    if ("id" in zone && typeof zone.id === "string" && zone.id.trim()) {
      values.add(zone.id.trim());
    }
  }
  for (const rule of rules) {
    for (const zoneId of rule.predicate.zone_ids ?? []) {
      if (zoneId.trim()) {
        values.add(zoneId.trim());
      }
    }
  }
  return Array.from(values).sort((left, right) => left.localeCompare(right));
}

function attributesToText(attributes: Record<string, unknown>) {
  return Object.entries(attributes)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join(", ");
}

function parseAttributes(value: string): Record<string, unknown> {
  const attributes: Record<string, unknown> = {};
  for (const part of value.split(",")) {
    const [rawKey, ...rawValue] = part.split("=");
    const key = rawKey.trim();
    if (!key || rawValue.length === 0) {
      continue;
    }
    attributes[key] = parseAttributeValue(rawValue.join("=").trim());
  }
  return attributes;
}

function parseAttributeValue(value: string): unknown {
  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }
  const numberValue = Number(value);
  if (Number.isFinite(numberValue) && value !== "") {
    return numberValue;
  }
  return value;
}

function clampConfidence(value: number) {
  if (!Number.isFinite(value)) {
    return 0.5;
  }
  return Math.min(1, Math.max(0, value));
}
