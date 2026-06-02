import { useEffect, useState, type ReactNode } from "react";
import { Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  CONFIGURATION_KINDS,
  labelForKind,
} from "@/components/configuration/configuration-copy";
import {
  PROFILE_COMMON_FIELD_GUIDANCE,
  PROFILE_FIELD_GUIDANCE,
  PROFILE_KIND_GUIDANCE,
} from "@/components/configuration/configuration-guidance";
import { RuntimeImpactPanel } from "@/components/configuration/RuntimeImpactPanel";
import {
  supportForField,
  valueCapability,
  type ConfigurationFieldCapability,
} from "@/components/configuration/configuration-capabilities";
import { FieldHelp } from "@/components/guidance/FieldHelp";
import { GuidancePanel } from "@/components/guidance/GuidancePanel";
import type { FieldGuidance } from "@/components/guidance/guidance-types";
import type {
  ConfigurationCatalog,
  OperatorConfigKind,
  OperatorConfigProfile,
  OperatorConfigProfileCreate,
} from "@/hooks/use-configuration";

const TRANSCODE_ROUTE_NORMALIZED_MESSAGE =
  "Transcode route mode was normalized. Use camera live rendition profiles for output size and FPS.";

const DEFAULT_PROFILE_GUIDANCE: FieldGuidance = {
  label: "Default profile",
  hint: "Acts as the tenant fallback when no more specific binding wins.",
  details: [
    "Keep one default profile per configuration kind so unbound targets resolve predictably.",
  ],
};

type ProfileEditorProps = {
  kind: OperatorConfigKind;
  selectedProfile: OperatorConfigProfile | null;
  draftProfile?: OperatorConfigProfile | null;
  catalog?: ConfigurationCatalog;
  onKindChange?: (kind: OperatorConfigKind) => void;
  onSave: (payload: OperatorConfigProfileCreate) => Promise<void> | void;
};

type EditorState = {
  kind: OperatorConfigKind;
  name: string;
  slug: string;
  enabled: boolean;
  isDefault: boolean;
  provider: string;
  storageScope: string;
  localRoot: string;
  endpoint: string;
  region: string;
  bucket: string;
  secure: boolean;
  pathPrefix: string;
  accessKey: string;
  secretKey: string;
  deliveryMode: string;
  publicBaseUrl: string;
  edgeOverrideUrl: string;
  preferredBackend: string;
  artifactPreference: string;
  fallbackAllowed: boolean;
  retentionDays: string;
  storageQuotaBytes: string;
  plaintextPlateStorage: string;
  residency: string;
  llmProvider: string;
  llmModel: string;
  llmBaseUrl: string;
  apiKey: string;
  lifecycleOwner: string;
  supervisorMode: string;
  restartPolicy: string;
};

export function ProfileEditor({
  kind,
  selectedProfile,
  draftProfile = null,
  catalog,
  onKindChange,
  onSave,
}: ProfileEditorProps) {
  const [state, setState] = useState<EditorState>(() =>
    stateFromProfile(kind, selectedProfile ?? draftProfile),
  );

  useEffect(() => {
    setState(stateFromProfile(kind, selectedProfile ?? draftProfile));
  }, [kind, selectedProfile, draftProfile]);

  const storedSecrets = selectedProfile?.secret_state ?? {};
  const title = selectedProfile ? "Edit profile" : "New profile";
  const kindLabel =
    state.kind === "stream_delivery"
      ? "Transport profile"
      : labelForKind(state.kind);

  function update(patch: Partial<EditorState>) {
    setState((current) => ({ ...current, ...patch }));
  }

  async function handleSave() {
    await onSave(buildPayload(state));
    update({ accessKey: "", secretKey: "", apiKey: "" });
  }

  function normalizeLegacyTransport() {
    void onSave(buildPayload({ ...state, deliveryMode: "native" }));
  }

  return (
    <section className="space-y-4" data-testid="configuration-profile-editor">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--vz-text-primary)]">
            {title}
          </h3>
          <p className="mt-1 text-xs text-[var(--vz-text-muted)]">
            {kindLabel}
          </p>
        </div>
        <Button type="button" onClick={() => void handleSave()}>
          <Save className="mr-2 size-4" />
          Save profile
        </Button>
      </div>

      <GuidancePanel guidance={PROFILE_KIND_GUIDANCE[state.kind]} />

      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Configuration kind" help={PROFILE_COMMON_FIELD_GUIDANCE.kind}>
          {(helpId) => (
            <Select
              aria-describedby={helpId}
              aria-label="Configuration kind"
              value={state.kind}
              onChange={(event) => {
                const nextKind = event.target.value as OperatorConfigKind;
                update({ kind: nextKind });
                onKindChange?.(nextKind);
              }}
            >
              {CONFIGURATION_KINDS.map((option) => (
                <option key={option} value={option}>
                  {labelForKind(option)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Profile name" help={PROFILE_COMMON_FIELD_GUIDANCE.name}>
          {(helpId) => (
            <Input
              aria-describedby={helpId}
              aria-label="Profile name"
              value={state.name}
              onChange={(event) => update({ name: event.target.value })}
            />
          )}
        </Field>
        <Field label="Slug" help={PROFILE_COMMON_FIELD_GUIDANCE.slug}>
          {(helpId) => (
            <Input
              aria-describedby={helpId}
              aria-label="Slug"
              value={state.slug}
              onChange={(event) => update({ slug: event.target.value })}
            />
          )}
        </Field>
        <CheckboxField
          label="Default profile"
          checked={state.isDefault}
          help={DEFAULT_PROFILE_GUIDANCE}
          onChange={(checked) => update({ isDefault: checked })}
        />
      </div>

      {state.kind === "evidence_storage" ? (
        <EvidenceStorageFields
          state={state}
          storedSecrets={storedSecrets}
          update={update}
        />
      ) : null}
      {state.kind === "stream_delivery" ? (
        <StreamFields
          state={state}
          catalog={catalog}
          onNormalizeLegacyTransport={normalizeLegacyTransport}
          update={update}
        />
      ) : null}
      {state.kind === "runtime_selection" ? (
        <RuntimeFields state={state} update={update} />
      ) : null}
      {state.kind === "privacy_policy" ? (
        <PrivacyFields state={state} update={update} />
      ) : null}
      {state.kind === "llm_provider" ? (
        <LlmFields state={state} storedSecrets={storedSecrets} update={update} />
      ) : null}
      {state.kind === "operations_mode" ? (
        <OperationsFields state={state} catalog={catalog} update={update} />
      ) : null}
      <RuntimeImpactPanel catalog={catalog} kind={state.kind} />
    </section>
  );
}

function EvidenceStorageFields({
  state,
  storedSecrets,
  update,
}: {
  state: EditorState;
  storedSecrets: Record<string, "missing" | "present">;
  update: (patch: Partial<EditorState>) => void;
}) {
  const guidance = PROFILE_FIELD_GUIDANCE.evidence_storage;
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Field label="Provider" help={guidance.provider}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Provider"
            value={state.provider}
            onChange={(event) => update({ provider: event.target.value })}
          >
            <option value="local_filesystem">Local filesystem</option>
            <option value="minio">MinIO</option>
            <option value="s3_compatible">S3-compatible</option>
            <option value="local_first">Local first</option>
          </Select>
        )}
      </Field>
      <Field label="Storage scope" help={guidance.storage_scope}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Storage scope"
            value={state.storageScope}
            onChange={(event) => update({ storageScope: event.target.value })}
          >
            <option value="edge">Edge</option>
            <option value="central">Central</option>
            <option value="cloud">Cloud</option>
          </Select>
        )}
      </Field>
      <TextInput
        label="Local root"
        value={state.localRoot}
        update={update}
        field="localRoot"
        help={guidance.local_root}
      />
      <TextInput
        label="Endpoint"
        value={state.endpoint}
        update={update}
        field="endpoint"
        help={guidance.endpoint}
      />
      <TextInput
        label="Region"
        value={state.region}
        update={update}
        field="region"
        help={guidance.region}
      />
      <TextInput
        label="Bucket"
        value={state.bucket}
        update={update}
        field="bucket"
        help={guidance.bucket}
      />
      <CheckboxField
        label="Secure TLS"
        checked={state.secure}
        help={guidance.secure}
        onChange={(checked) => update({ secure: checked })}
      />
      <TextInput
        label="Path prefix"
        value={state.pathPrefix}
        update={update}
        field="pathPrefix"
        help={guidance.path_prefix}
      />
      <SecretInput
        label="Access key"
        field="accessKey"
        value={state.accessKey}
        stored={storedSecrets.access_key === "present"}
        update={update}
        help={guidance.access_key}
      />
      <SecretInput
        label="Secret key"
        field="secretKey"
        value={state.secretKey}
        stored={storedSecrets.secret_key === "present"}
        update={update}
        help={guidance.secret_key}
      />
    </div>
  );
}

function StreamFields({
  state,
  catalog,
  onNormalizeLegacyTransport,
  update,
}: {
  state: EditorState;
  catalog?: ConfigurationCatalog;
  onNormalizeLegacyTransport: () => void;
  update: (patch: Partial<EditorState>) => void;
}) {
  const deliveryModeCapability = supportForField(
    catalog,
    "stream_delivery",
    "delivery_mode",
  );
  const guidance = PROFILE_FIELD_GUIDANCE.stream_delivery;
  const isLegacyTranscode = state.deliveryMode === "transcode";
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <p className="md:col-span-3 text-xs text-[var(--vz-text-muted)]">
        Reusable relay and browser transport settings. Live rendition resolution,
        FPS, and overlays are selected per camera.
      </p>
      {isLegacyTranscode ? (
        <div className="md:col-span-3 rounded-[0.75rem] border border-[#6a4b1c] bg-[#24180d] p-3 text-sm text-[#ffd9a9]">
          <p>{TRANSCODE_ROUTE_NORMALIZED_MESSAGE}</p>
          <Button
            className="mt-3"
            type="button"
            variant="secondary"
            onClick={onNormalizeLegacyTransport}
          >
            Normalize transport
          </Button>
        </div>
      ) : null}
      <Field label="Transport mode" help={guidance.delivery_mode}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Transport mode"
            value={isLegacyTranscode ? "native" : state.deliveryMode}
            onChange={(event) => update({ deliveryMode: event.target.value })}
          >
            <CapabilityOption field={deliveryModeCapability} value="native">
              Native/direct
            </CapabilityOption>
            <CapabilityOption field={deliveryModeCapability} value="webrtc">
              WebRTC
            </CapabilityOption>
            <CapabilityOption field={deliveryModeCapability} value="hls">
              HLS
            </CapabilityOption>
            <CapabilityOption field={deliveryModeCapability} value="mjpeg">
              MJPEG
            </CapabilityOption>
          </Select>
        )}
      </Field>
      <TextInput
        label="Public base URL"
        value={state.publicBaseUrl}
        update={update}
        field="publicBaseUrl"
        help={guidance.public_base_url}
      />
      <TextInput
        label="Edge override URL"
        value={state.edgeOverrideUrl}
        update={update}
        field="edgeOverrideUrl"
        help={guidance.edge_override_url}
      />
    </div>
  );
}

function RuntimeFields({
  state,
  update,
}: {
  state: EditorState;
  update: (patch: Partial<EditorState>) => void;
}) {
  const guidance = PROFILE_FIELD_GUIDANCE.runtime_selection;
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <Field label="Preferred backend" help={guidance.preferred_backend}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Preferred backend"
            value={state.preferredBackend}
            onChange={(event) => update({ preferredBackend: event.target.value })}
          >
            <option value="">Auto</option>
            <option value="onnxruntime">ONNX Runtime</option>
            <option value="tensorrt_engine">TensorRT engine</option>
            <option value="ultralytics_yolo_world">YOLO World</option>
            <option value="ultralytics_yoloe">YOLOE</option>
          </Select>
        )}
      </Field>
      <Field label="Artifact preference" help={guidance.artifact_preference}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Artifact preference"
            value={state.artifactPreference}
            onChange={(event) => update({ artifactPreference: event.target.value })}
          >
            <option value="tensorrt_first">TensorRT first</option>
            <option value="onnx_first">ONNX first</option>
            <option value="dynamic_first">Dynamic first</option>
          </Select>
        )}
      </Field>
      <CheckboxField
        label="Allow fallback"
        checked={state.fallbackAllowed}
        help={guidance.fallback_allowed}
        onChange={(checked) => update({ fallbackAllowed: checked })}
      />
    </div>
  );
}

function PrivacyFields({
  state,
  update,
}: {
  state: EditorState;
  update: (patch: Partial<EditorState>) => void;
}) {
  const guidance = PROFILE_FIELD_GUIDANCE.privacy_policy;
  return (
    <div className="grid gap-3 md:grid-cols-4">
      <TextInput
        label="Retention days"
        value={state.retentionDays}
        update={update}
        field="retentionDays"
        type="number"
        help={guidance.retention_days}
      />
      <TextInput
        label="Storage quota bytes"
        value={state.storageQuotaBytes}
        update={update}
        field="storageQuotaBytes"
        type="number"
        help={guidance.storage_quota_bytes}
      />
      <Field label="Plaintext plate posture" help={guidance.plaintext_plate_storage}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Plaintext plate posture"
            value={state.plaintextPlateStorage}
            onChange={(event) => update({ plaintextPlateStorage: event.target.value })}
          >
            <option value="blocked">Blocked</option>
            <option value="allowed">Allowed</option>
          </Select>
        )}
      </Field>
      <Field label="Residency guardrail" help={guidance.residency}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Residency guardrail"
            value={state.residency}
            onChange={(event) => update({ residency: event.target.value })}
          >
            <option value="edge">Edge</option>
            <option value="central">Central</option>
            <option value="cloud">Cloud</option>
            <option value="local_first">Local first</option>
          </Select>
        )}
      </Field>
    </div>
  );
}

function LlmFields({
  state,
  storedSecrets,
  update,
}: {
  state: EditorState;
  storedSecrets: Record<string, "missing" | "present">;
  update: (patch: Partial<EditorState>) => void;
}) {
  const guidance = PROFILE_FIELD_GUIDANCE.llm_provider;
  return (
    <div className="grid gap-3 md:grid-cols-4">
      <TextInput
        label="Provider"
        value={state.llmProvider}
        update={update}
        field="llmProvider"
        help={guidance.provider}
      />
      <TextInput
        label="Model"
        value={state.llmModel}
        update={update}
        field="llmModel"
        help={guidance.model}
      />
      <TextInput
        label="Base URL"
        value={state.llmBaseUrl}
        update={update}
        field="llmBaseUrl"
        help={guidance.base_url}
      />
      <SecretInput
        label="API key"
        field="apiKey"
        value={state.apiKey}
        stored={storedSecrets.api_key === "present"}
        update={update}
        help={guidance.api_key}
      />
    </div>
  );
}

function OperationsFields({
  state,
  catalog,
  update,
}: {
  state: EditorState;
  catalog?: ConfigurationCatalog;
  update: (patch: Partial<EditorState>) => void;
}) {
  const supervisorModeCapability = supportForField(
    catalog,
    "operations_mode",
    "supervisor_mode",
  );
  const guidance = PROFILE_FIELD_GUIDANCE.operations_mode;
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <Field label="Lifecycle owner" help={guidance.lifecycle_owner}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Lifecycle owner"
            value={state.lifecycleOwner}
            onChange={(event) => update({ lifecycleOwner: event.target.value })}
          >
            <option value="manual">Manual</option>
            <option value="edge_supervisor">Edge supervisor</option>
            <option value="central_supervisor">Central supervisor</option>
          </Select>
        )}
      </Field>
      <Field label="Supervisor mode" help={guidance.supervisor_mode}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Supervisor mode"
            value={state.supervisorMode}
            onChange={(event) => update({ supervisorMode: event.target.value })}
          >
            <CapabilityOption field={supervisorModeCapability} value="disabled">
              Disabled
            </CapabilityOption>
            <CapabilityOption field={supervisorModeCapability} value="polling">
              Polling
            </CapabilityOption>
            <CapabilityOption field={supervisorModeCapability} value="push">
              Push
            </CapabilityOption>
          </Select>
        )}
      </Field>
      <Field label="Restart policy" help={guidance.restart_policy}>
        {(helpId) => (
          <Select
            aria-describedby={helpId}
            aria-label="Restart policy"
            value={state.restartPolicy}
            onChange={(event) => update({ restartPolicy: event.target.value })}
          >
            <option value="never">Never</option>
            <option value="on_failure">On failure</option>
            <option value="always">Always</option>
          </Select>
        )}
      </Field>
    </div>
  );
}

function CapabilityOption({
  field,
  value,
  children,
}: {
  field: ConfigurationFieldCapability | undefined;
  value: string;
  children: ReactNode;
}) {
  const capability = valueCapability(field, value);
  return (
    <option
      value={value}
      disabled={capability?.support === "unsupported"}
      title={capability?.operator_message ?? undefined}
    >
      {children}
    </option>
  );
}

type FieldChildren = ReactNode | ((helpId: string | undefined) => ReactNode);

function Field({
  label,
  help,
  children,
}: {
  label: string;
  help?: FieldGuidance;
  children: FieldChildren;
}) {
  const helpId = help ? helpIdForLabel(label) : undefined;
  return (
    <div className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
      <span>{label}</span>
      {typeof children === "function" ? children(helpId) : children}
      {help && helpId ? <FieldHelp id={helpId} guidance={help} /> : null}
    </div>
  );
}

function TextInput({
  label,
  value,
  field,
  update,
  help,
  type = "text",
}: {
  label: string;
  value: string;
  field: keyof EditorState;
  update: (patch: Partial<EditorState>) => void;
  help?: FieldGuidance;
  type?: string;
}) {
  return (
    <Field label={label} help={help}>
      {(helpId) => (
        <Input
          aria-describedby={helpId}
          aria-label={label}
          type={type}
          value={value}
          onChange={(event) => update({ [field]: event.target.value })}
        />
      )}
    </Field>
  );
}

function SecretInput({
  label,
  field,
  value,
  stored,
  update,
  help,
}: {
  label: string;
  field: keyof EditorState;
  value: string;
  stored: boolean;
  update: (patch: Partial<EditorState>) => void;
  help?: FieldGuidance;
}) {
  return (
    <Field label={label} help={help}>
      {(helpId) => (
        <>
          <div className="flex items-center gap-2">
            <Input
              aria-describedby={helpId}
              aria-label={label}
              type="password"
              value={value}
              placeholder={stored ? "Replace secret" : ""}
              onChange={(event) => update({ [field]: event.target.value })}
            />
            {stored ? (
              <span className="whitespace-nowrap rounded-full border border-white/10 px-2.5 py-1 text-xs font-semibold text-[#8fd3ff]">
                Stored
              </span>
            ) : null}
          </div>
          <span className="text-xs text-[var(--vz-text-muted)]">Replace secret</span>
        </>
      )}
    </Field>
  );
}

function CheckboxField({
  label,
  checked,
  help,
  onChange,
}: {
  label: string;
  checked: boolean;
  help?: FieldGuidance;
  onChange: (checked: boolean) => void;
}) {
  const helpId = help ? helpIdForLabel(label) : undefined;

  return (
    <div className="space-y-1 text-sm font-medium text-[#d8e2f2]">
      <label className="flex items-center gap-2">
        <input
          aria-describedby={helpId}
          aria-label={label}
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
        />
        {label}
      </label>
      {help && helpId ? <FieldHelp id={helpId} guidance={help} /> : null}
    </div>
  );
}

function helpIdForLabel(label: string) {
  return `${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-help-hint`;
}

function stateFromProfile(
  kind: OperatorConfigKind,
  profile: OperatorConfigProfile | null,
): EditorState {
  const config = profile?.config ?? {};
  return {
    kind: profile?.kind ?? kind,
    name: profile?.name ?? "New profile",
    slug: profile?.slug ?? "new-profile",
    enabled: profile?.enabled ?? true,
    isDefault: profile?.is_default ?? false,
    provider: stringValue(config.provider, "minio"),
    storageScope: stringValue(config.storage_scope, "central"),
    localRoot: stringValue(config.local_root),
    endpoint: stringValue(config.endpoint),
    region: stringValue(config.region),
    bucket: stringValue(config.bucket),
    secure: Boolean(config.secure),
    pathPrefix: stringValue(config.path_prefix),
    accessKey: "",
    secretKey: "",
    deliveryMode: stringValue(config.delivery_mode, "native"),
    publicBaseUrl: stringValue(config.public_base_url),
    edgeOverrideUrl: stringValue(config.edge_override_url),
    preferredBackend: stringValue(config.preferred_backend),
    artifactPreference: stringValue(config.artifact_preference, "tensorrt_first"),
    fallbackAllowed: config.fallback_allowed !== false,
    retentionDays: stringValue(config.retention_days, "30"),
    storageQuotaBytes: stringValue(config.storage_quota_bytes, "10737418240"),
    plaintextPlateStorage: stringValue(config.plaintext_plate_storage, "blocked"),
    residency: stringValue(config.residency, "central"),
    llmProvider: stringValue(config.provider, "openai"),
    llmModel: stringValue(config.model, "gpt-4.1-mini"),
    llmBaseUrl: stringValue(config.base_url),
    apiKey: "",
    lifecycleOwner: stringValue(config.lifecycle_owner, "manual"),
    supervisorMode: stringValue(config.supervisor_mode, "disabled"),
    restartPolicy: stringValue(config.restart_policy, "on_failure"),
  };
}

function buildPayload(state: EditorState): OperatorConfigProfileCreate {
  return {
    kind: state.kind,
    scope: "tenant",
    name: state.name,
    slug: state.slug,
    enabled: state.enabled,
    is_default: state.isDefault,
    config: buildConfig(state),
    secrets: buildSecrets(state),
  };
}

function buildConfig(state: EditorState): Record<string, unknown> {
  if (state.kind === "evidence_storage") {
    return compact({
      provider: state.provider,
      storage_scope: state.storageScope,
      local_root: state.localRoot,
      endpoint: state.endpoint,
      region: state.region,
      bucket: state.bucket,
      secure: state.secure,
      path_prefix: state.pathPrefix,
    });
  }
  if (state.kind === "stream_delivery") {
    return compact({
      delivery_mode: state.deliveryMode,
      public_base_url: state.publicBaseUrl,
      edge_override_url: state.edgeOverrideUrl,
    });
  }
  if (state.kind === "runtime_selection") {
    return compact({
      preferred_backend: state.preferredBackend,
      artifact_preference: state.artifactPreference,
      fallback_allowed: state.fallbackAllowed,
    });
  }
  if (state.kind === "privacy_policy") {
    return compact({
      retention_days: Number(state.retentionDays),
      storage_quota_bytes: Number(state.storageQuotaBytes),
      plaintext_plate_storage: state.plaintextPlateStorage,
      residency: state.residency,
    });
  }
  if (state.kind === "llm_provider") {
    return compact({
      provider: state.llmProvider,
      model: state.llmModel,
      base_url: state.llmBaseUrl,
      api_key_required: true,
    });
  }
  return compact({
    lifecycle_owner: state.lifecycleOwner,
    supervisor_mode: state.supervisorMode,
    restart_policy: state.restartPolicy,
  });
}

function buildSecrets(state: EditorState): Record<string, string> {
  const secrets: Record<string, string> = {};
  if (state.kind === "evidence_storage") {
    if (state.accessKey.trim()) {
      secrets.access_key = state.accessKey.trim();
    }
    if (state.secretKey.trim()) {
      secrets.secret_key = state.secretKey.trim();
    }
  }
  if (state.kind === "llm_provider" && state.apiKey.trim()) {
    secrets.api_key = state.apiKey.trim();
  }
  return secrets;
}

function compact(values: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(values).filter(([, value]) => value !== "" && value !== undefined),
  );
}

function stringValue(value: unknown, fallback = "") {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    return String(value);
  }
  return fallback;
}
