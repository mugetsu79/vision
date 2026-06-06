import { SupportReadinessPanel } from "./SupportReadinessPanel";
import type {
  JsonRecord,
  SupportBundle,
  SupportDiagnosticsPayload,
} from "./types";

type SupportDiagnosticsPanelProps = {
  bundles?: SupportBundle[] | JsonRecord[];
  diagnostics?: SupportDiagnosticsPayload;
};

export function SupportDiagnosticsPanel({
  bundles = [],
  diagnostics,
}: SupportDiagnosticsPanelProps) {
  return <SupportReadinessPanel bundles={bundles} diagnostics={diagnostics} />;
}
