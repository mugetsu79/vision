import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
import type { FieldGuidance } from "@/components/guidance/guidance-types";

type FieldHelpProps = {
  id: string;
  guidance: FieldGuidance;
};

export function FieldHelp({ id, guidance }: FieldHelpProps) {
  return (
    <GuidanceDisclosure
      id={id}
      label={guidance.label}
      guidance={guidance}
    />
  );
}
