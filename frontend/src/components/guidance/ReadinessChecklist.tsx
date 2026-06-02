import {
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
  Info,
  type LucideIcon,
} from "lucide-react";

import type {
  GuidanceTone,
  ReadinessItem,
} from "@/components/guidance/guidance-types";

const TONE_CLASS: Record<GuidanceTone, string> = {
  info: "border-sky-300/20 bg-sky-950/20 text-sky-100",
  success: "border-emerald-300/20 bg-emerald-950/20 text-emerald-100",
  warning: "border-amber-300/20 bg-amber-950/20 text-amber-100",
  danger: "border-rose-300/20 bg-rose-950/20 text-rose-100",
};

const TONE_ICON: Record<GuidanceTone, LucideIcon> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: CircleAlert,
};

export function ReadinessChecklist({ items }: { items: ReadinessItem[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <ul aria-label="Readiness checklist" className="grid gap-2">
      {items.map((item) => {
        const Icon = TONE_ICON[item.tone];
        return (
          <li
            key={item.id}
            className={`rounded-lg border px-3 py-2 ${TONE_CLASS[item.tone]}`}
          >
            <div className="flex gap-2">
              <Icon className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
              <div>
                <p className="text-xs font-semibold">{item.label}</p>
                <p className="mt-1 text-xs leading-5 opacity-85">{item.detail}</p>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
