import { useEffect, useState, type FormEvent } from "react";

import { asRecord, textValue, type FleetOpsVessel, type JsonRecord } from "./types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogCloseButton, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type {
  MaritimeVesselCreateInput,
  MaritimeVesselUpdateInput,
} from "@/hooks/use-maritime";
import type { Site } from "@/hooks/use-sites";
import { cn } from "@/lib/utils";

type VesselFormMode = "create" | "edit";
type VesselSiteMode = "create" | "existing";

type VesselFormState = {
  name: string;
  siteMode: VesselSiteMode;
  siteId: string;
  siteName: string;
  siteTimezone: string;
  imoNumber: string;
  mmsi: string;
  callSign: string;
  flagState: string;
  vesselType: string;
  ownerLabel: string;
  managerLabel: string;
  chartererLabel: string;
  homePort: string;
  notes: string;
};

type VesselFormPayload = MaritimeVesselCreateInput | MaritimeVesselUpdateInput;

type VesselFormDialogProps = {
  mode?: VesselFormMode;
  open: boolean;
  vessel?: FleetOpsVessel | null;
  sites?: Site[];
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: VesselFormPayload) => Promise<void>;
};

const defaultForm: VesselFormState = {
  name: "",
  siteMode: "create",
  siteId: "",
  siteName: "",
  siteTimezone: "UTC",
  imoNumber: "",
  mmsi: "",
  callSign: "",
  flagState: "",
  vesselType: "",
  ownerLabel: "",
  managerLabel: "",
  chartererLabel: "",
  homePort: "",
  notes: "",
};

export function VesselFormDialog({
  mode = "create",
  open,
  vessel,
  sites = [],
  isSubmitting = false,
  onClose,
  onSubmit,
}: VesselFormDialogProps) {
  const [form, setForm] = useState<VesselFormState>(defaultForm);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const isEdit = mode === "edit";

  useEffect(() => {
    if (!open) {
      setForm(defaultForm);
      setSubmitError(null);
      return;
    }

    if (isEdit && vessel) {
      const metadata = asRecord(vessel.metadata);
      setForm({
        ...defaultForm,
        name: textValue(vessel.name, ""),
        homePort: textValue(metadata.home_port, ""),
        notes: textValue(metadata.notes, ""),
      });
    } else {
      setForm(defaultForm);
    }
    setSubmitError(null);
  }, [isEdit, open, vessel]);

  function updateField<K extends keyof VesselFormState>(
    field: K,
    value: VesselFormState[K],
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    try {
      await onSubmit(
        isEdit ? buildUpdatePayload(form, vessel) : buildCreatePayload(form),
      );
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Unable to save vessel.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      title={isEdit ? "Edit vessel" : "Add vessel"}
      description={
        isEdit
          ? "Update operator-facing vessel details and metadata."
          : "Create a FleetOps vessel and bind it to a core site."
      }
    >
      <form
        className="max-h-[calc(100vh-12rem)] space-y-5 overflow-y-auto pr-1"
        onSubmit={(event) => void handleSubmit(event)}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <LabeledInput
            label="Vessel name"
            value={form.name}
            required
            onChange={(value) => updateField("name", value)}
            placeholder="MV Resolute"
          />
          {!isEdit ? (
            <LabeledInput
              label="IMO number"
              value={form.imoNumber}
              onChange={(value) => updateField("imoNumber", value)}
              placeholder="9876543"
            />
          ) : null}
        </div>

        {!isEdit ? (
          <>
            <fieldset className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] p-4">
              <legend className="px-1 text-xs font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
                Site binding
              </legend>
              <div className="mt-2 grid gap-3 sm:grid-cols-2">
                <label className={siteModeClass(form.siteMode === "create")}>
                  <input
                    className="mt-1"
                    type="radio"
                    name="site-mode"
                    value="create"
                    checked={form.siteMode === "create"}
                    onChange={() => updateField("siteMode", "create")}
                  />
                  <span>
                    <span className="block font-medium text-[var(--vz-text-primary)]">
                      Create a site
                    </span>
                    <span className="mt-1 block text-xs text-[var(--vz-text-muted)]">
                      Default for a new vessel.
                    </span>
                  </span>
                </label>
                <label className={siteModeClass(form.siteMode === "existing")}>
                  <input
                    className="mt-1"
                    type="radio"
                    name="site-mode"
                    value="existing"
                    checked={form.siteMode === "existing"}
                    onChange={() => updateField("siteMode", "existing")}
                  />
                  <span>
                    <span className="block font-medium text-[var(--vz-text-primary)]">
                      Bind existing site
                    </span>
                    <span className="mt-1 block text-xs text-[var(--vz-text-muted)]">
                      Advanced option for prepared sites.
                    </span>
                  </span>
                </label>
              </div>
            </fieldset>

            {form.siteMode === "create" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <LabeledInput
                  label="Site name"
                  value={form.siteName}
                  onChange={(value) => updateField("siteName", value)}
                  placeholder={form.name || "MV Resolute"}
                />
                <LabeledInput
                  label="Site time zone"
                  value={form.siteTimezone}
                  required
                  onChange={(value) => updateField("siteTimezone", value)}
                  placeholder="UTC"
                />
              </div>
            ) : (
              <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
                <span>Existing site</span>
                <select
                  aria-label="Existing site"
                  className="w-full rounded-[0.85rem] border border-[color:var(--argus-border)] bg-[color:var(--argus-surface)] px-4 py-3 text-sm text-[var(--argus-text)] outline-none transition duration-200 focus:border-[color:var(--argus-border-highlight)] focus:shadow-[0_0_0_4px_var(--argus-accent-soft)]"
                  value={form.siteId}
                  required
                  onChange={(event) => updateField("siteId", event.target.value)}
                >
                  <option value="">Select a site</option>
                  {sites.map((site) => (
                    <option key={site.id} value={site.id}>
                      {site.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <LabeledInput
                label="MMSI"
                value={form.mmsi}
                onChange={(value) => updateField("mmsi", value)}
                placeholder="235012345"
              />
              <LabeledInput
                label="Call sign"
                value={form.callSign}
                onChange={(value) => updateField("callSign", value)}
                placeholder="MRES"
              />
              <LabeledInput
                label="Flag state"
                value={form.flagState}
                onChange={(value) => updateField("flagState", value)}
                placeholder="NL"
              />
              <LabeledInput
                label="Vessel type"
                value={form.vesselType}
                onChange={(value) => updateField("vesselType", value)}
                placeholder="Offshore support"
              />
              <LabeledInput
                label="Owner label"
                value={form.ownerLabel}
                onChange={(value) => updateField("ownerLabel", value)}
                placeholder="Owner"
              />
              <LabeledInput
                label="Manager label"
                value={form.managerLabel}
                onChange={(value) => updateField("managerLabel", value)}
                placeholder="Manager"
              />
              <LabeledInput
                label="Charterer label"
                value={form.chartererLabel}
                onChange={(value) => updateField("chartererLabel", value)}
                placeholder="Charterer"
              />
              <LabeledInput
                label="Home port"
                value={form.homePort}
                onChange={(value) => updateField("homePort", value)}
                placeholder="Rotterdam"
              />
            </div>
          </>
        ) : (
          <LabeledInput
            label="Home port"
            value={form.homePort}
            onChange={(value) => updateField("homePort", value)}
            placeholder="Rotterdam"
          />
        )}

        <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
          <span>Notes</span>
          <textarea
            aria-label="Notes"
            className="min-h-24 w-full rounded-[0.85rem] border border-[color:var(--argus-border)] bg-[color:var(--argus-surface)] px-4 py-3 text-sm text-[var(--argus-text)] outline-none placeholder:text-[var(--argus-text-subtle)] transition duration-200 focus:border-[color:var(--argus-border-highlight)] focus:shadow-[0_0_0_4px_var(--argus-accent-soft)]"
            value={form.notes}
            onChange={(event) => updateField("notes", event.target.value)}
            placeholder="Operational notes"
          />
        </label>

        {submitError ? (
          <p role="alert" className="text-sm font-medium text-[#ff9ca6]">
            {submitError}
          </p>
        ) : null}

        <DialogFooter>
          <DialogCloseButton type="button" onClick={onClose}>
            Cancel
          </DialogCloseButton>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting
              ? "Saving..."
              : isEdit
                ? "Save vessel"
                : "Create vessel"}
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
  onChange: (value: string) => void;
};

function LabeledInput({
  label,
  value,
  placeholder,
  required = false,
  onChange,
}: LabeledInputProps) {
  return (
    <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
      <span>{label}</span>
      <Input
        aria-label={label}
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}

function siteModeClass(active: boolean) {
  return cn(
    "flex gap-3 rounded-[var(--vz-r-md)] border p-3 text-sm transition duration-200",
    active
      ? "border-[color:var(--vz-hair-focus)] bg-white/[0.06]"
      : "border-[color:var(--vz-hair)] bg-white/[0.025]",
  );
}

function buildCreatePayload(form: VesselFormState): MaritimeVesselCreateInput {
  const name = form.name.trim();
  const payload: MaritimeVesselCreateInput = {
    name,
    metadata: buildMetadata(form),
  };

  assignOptional(payload, "imo_number", form.imoNumber);
  assignOptional(payload, "mmsi", form.mmsi);
  assignOptional(payload, "call_sign", form.callSign);
  assignOptional(payload, "flag_state", form.flagState);
  assignOptional(payload, "vessel_type", form.vesselType);
  assignOptional(payload, "owner_label", form.ownerLabel);
  assignOptional(payload, "manager_label", form.managerLabel);
  assignOptional(payload, "charterer_label", form.chartererLabel);

  if (form.siteMode === "existing") {
    payload.site_id = form.siteId.trim();
  } else {
    payload.create_site = {
      name: form.siteName.trim() || name,
      description: `FleetOps vessel site for ${name}`,
      tz: form.siteTimezone.trim() || "UTC",
    };
  }

  if (Object.keys(payload.metadata ?? {}).length === 0) {
    delete payload.metadata;
  }

  return payload;
}

function buildUpdatePayload(
  form: VesselFormState,
  vessel?: FleetOpsVessel | null,
): MaritimeVesselUpdateInput {
  const initialMetadata = asRecord(vessel?.metadata);
  const metadata = { ...initialMetadata };
  const homePort = form.homePort.trim();
  const notes = form.notes.trim();
  if (homePort) {
    metadata.home_port = homePort;
  } else {
    delete metadata.home_port;
  }
  if (notes) {
    metadata.notes = notes;
  } else {
    delete metadata.notes;
  }

  return {
    name: form.name.trim(),
    metadata:
      Object.keys(metadata).length > 0
        ? metadata
        : Object.keys(initialMetadata).length > 0
          ? {}
          : null,
  };
}

function buildMetadata(form: VesselFormState): JsonRecord {
  const metadata: JsonRecord = {};
  const homePort = form.homePort.trim();
  const notes = form.notes.trim();
  if (homePort) {
    metadata.home_port = homePort;
  }
  if (notes) {
    metadata.notes = notes;
  }
  return metadata;
}

function assignOptional(
  payload: MaritimeVesselCreateInput,
  key:
    | "imo_number"
    | "mmsi"
    | "call_sign"
    | "flag_state"
    | "vessel_type"
    | "owner_label"
    | "manager_label"
    | "charterer_label",
  value: string,
) {
  const normalized = value.trim();
  if (normalized) {
    payload[key] = normalized;
  }
}
