import { useState } from "react";
import { Info } from "lucide-react";

import type { FieldGuidance } from "@/components/guidance/guidance-types";

type FieldHelpProps = {
  id: string;
  guidance: FieldGuidance;
};

export function FieldHelp({ id, guidance }: FieldHelpProps) {
  const [open, setOpen] = useState(false);
  const hintId = id;
  const detailsId = `${id}-details`;

  return (
    <div className="space-y-2 text-xs text-[#9fb2cf]">
      <div className="flex items-start gap-2">
        <p id={hintId} className="leading-5">{guidance.hint}</p>
        <button
          type="button"
          className="inline-flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-full border border-white/10 text-[#8fd3ff] transition hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8fd3ff]"
          aria-controls={detailsId}
          aria-expanded={open}
          aria-label={`${open ? "Hide" : "Show"} details for ${guidance.label}`}
          onClick={() => setOpen((current) => !current)}
        >
          <Info className="size-3.5" aria-hidden="true" />
        </button>
      </div>
      {open ? (
        <div id={detailsId} className="rounded-lg border border-white/10 bg-[#07101b] p-3">
          {guidance.details.length > 0 ? (
            <ul className="grid gap-1">
              {guidance.details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          ) : null}
          {guidance.safeDefault ? (
            <p className="mt-2 text-[#d8e2f2]">
              <span className="font-semibold">Safe default:</span>{" "}
              {guidance.safeDefault}
            </p>
          ) : null}
          {guidance.runtimeEffect ? (
            <p className="mt-2">
              <span className="font-semibold text-[#d8e2f2]">Runtime effect:</span>{" "}
              {guidance.runtimeEffect}
            </p>
          ) : null}
          {guidance.examples?.length ? (
            <div className="mt-3">
              <p className="font-semibold text-[#d8e2f2]">Examples</p>
              <ul className="mt-1 grid gap-1">
                {guidance.examples.map((example) => (
                  <li key={example.label}>
                    <span className="font-semibold text-[#d8e2f2]">{example.label}:</span>{" "}
                    {example.description}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {guidance.commonMistakes?.length ? (
            <div className="mt-3 rounded-md border border-amber-300/20 bg-amber-950/20 p-2 text-amber-100">
              <p className="font-semibold">Common mistakes</p>
              <ul className="mt-1 grid gap-1">
                {guidance.commonMistakes.map((mistake) => (
                  <li key={mistake}>{mistake}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
