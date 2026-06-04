import type { ReactNode } from "react";

import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
import type { FieldGuidance } from "@/components/guidance/guidance-types";

type FieldHelpProps = {
  id: string;
  guidance: FieldGuidance;
  children?: ReactNode;
};

export function FieldHelp({ id, guidance, children }: FieldHelpProps) {
  return (
    <GuidanceDisclosure id={id} label={guidance.label} guidance={guidance}>
      {children}
    </GuidanceDisclosure>
  );
}
