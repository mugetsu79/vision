import type {
  ConfigurationCatalog,
  OperatorConfigKind,
} from "@/hooks/use-configuration";

export type ConfigurationFieldCapability = NonNullable<
  NonNullable<ConfigurationCatalog["kinds"]>[number]["fields"]
>[number];

export function kindCapability(
  catalog: ConfigurationCatalog | undefined,
  kind: OperatorConfigKind,
) {
  return catalog?.kinds?.find((entry) => entry.kind === kind);
}

export function supportForField(
  catalog: ConfigurationCatalog | undefined,
  kind: OperatorConfigKind,
  fieldName: string,
) {
  return kindCapability(catalog, kind)?.fields?.find((field) => field.name === fieldName);
}

export function valueCapability(
  field: ConfigurationFieldCapability | undefined,
  value: string,
) {
  return field?.values?.find((option) => option.value === value);
}

export function isUnsupportedValue(
  field: ConfigurationFieldCapability | undefined,
  value: string,
) {
  return valueCapability(field, value)?.support === "unsupported";
}

export function operatorMessagesForField(
  field: ConfigurationFieldCapability | undefined,
) {
  return [
    field?.operator_message,
    ...(field?.values ?? []).map((value) => value.operator_message),
  ].filter((message): message is string => Boolean(message));
}
