export type GuidanceTone = "info" | "success" | "warning" | "danger";

export type GuidanceExample = {
  label: string;
  value?: string;
  description: string;
};

export type FieldGuidance = {
  label: string;
  hint: string;
  details: string[];
  safeDefault?: string;
  examples?: GuidanceExample[];
  commonMistakes?: string[];
  runtimeEffect?: string;
  required?: boolean;
};

export type SectionGuidance = {
  eyebrow?: string;
  title: string;
  summary: string;
  concepts?: Array<{ term: string; definition: string }>;
  steps?: string[];
  examples?: GuidanceExample[];
  warnings?: string[];
  commonMistakes?: string[];
};

export type ReadinessItem = {
  id: string;
  label: string;
  detail: string;
  tone: GuidanceTone;
};
