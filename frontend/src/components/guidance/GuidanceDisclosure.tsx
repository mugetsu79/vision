import { type ReactNode, useEffect, useRef, useState } from "react";
import { Info, X } from "lucide-react";

import type {
  FieldGuidance,
  SectionGuidance,
} from "@/components/guidance/guidance-types";

type GuidanceDisclosureProps = {
  id: string;
  label: string;
  guidance: FieldGuidance | SectionGuidance;
  children?: ReactNode;
};

function isFieldGuidance(
  guidance: FieldGuidance | SectionGuidance,
): guidance is FieldGuidance {
  return "hint" in guidance;
}

export function GuidanceDisclosure({
  id,
  label,
  guidance,
  children,
}: GuidanceDisclosureProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const rootRef = useRef<HTMLSpanElement | null>(null);
  const panelId = `${id}-panel`;
  const triggerId = `${id}-trigger`;
  const title = isFieldGuidance(guidance) ? guidance.label : guidance.title;
  const summary = isFieldGuidance(guidance) ? guidance.hint : guidance.summary;
  const details = isFieldGuidance(guidance) ? guidance.details : guidance.steps;
  const concepts = isFieldGuidance(guidance) ? [] : guidance.concepts ?? [];
  const examples = guidance.examples ?? [];
  const warnings = isFieldGuidance(guidance) ? [] : guidance.warnings ?? [];
  const commonMistakes = guidance.commonMistakes ?? [];

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };

    const handlePointerDown = (event: PointerEvent) => {
      if (
        event.target instanceof Node
        && rootRef.current
        && !rootRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("pointerdown", handlePointerDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [open]);

  return (
    <span ref={rootRef} className="relative inline-flex align-middle">
      <span id={id} className="sr-only">
        {summary}
      </span>
      <button
        id={triggerId}
        ref={triggerRef}
        type="button"
        className="inline-flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-full border border-white/12 bg-white/[0.03] text-[#8fd3ff] transition hover:bg-white/[0.08] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8fd3ff]"
        aria-controls={panelId}
        aria-expanded={open}
        aria-label={`${open ? "Hide" : "Show"} ${label} help`}
        onClick={() => setOpen((current) => !current)}
      >
        <Info className="size-3.5" aria-hidden="true" />
      </button>
      {open ? (
        <div
          id={panelId}
          className="absolute left-0 top-8 z-30 w-[min(28rem,calc(100vw-2rem))] rounded-lg border border-white/10 bg-[#07101b] p-4 text-left text-xs leading-5 text-[#9fb2cf] shadow-[0_24px_80px_-40px_rgba(0,0,0,0.9)] sm:left-auto sm:right-0"
          role="dialog"
          aria-label={`${label} help`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-[#f4f8ff]">{title}</h4>
              <p className="mt-1">{summary}</p>
            </div>
            <button
              type="button"
              className="inline-flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-full border border-white/10 text-[#d8e2f2] hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8fd3ff]"
              aria-label={`Close ${label} help`}
              onClick={() => {
                setOpen(false);
                triggerRef.current?.focus();
              }}
            >
              <X className="size-3.5" aria-hidden="true" />
            </button>
          </div>
          {children ? <div className="mt-4">{children}</div> : null}
          {concepts.length ? (
            <dl className="mt-3 grid gap-2">
              {concepts.map((concept) => (
                <div key={concept.term}>
                  <dt className="font-semibold text-[#d8e2f2]">{concept.term}</dt>
                  <dd>{concept.definition}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          {details?.length ? (
            <ul className="mt-3 grid gap-1">
              {details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          ) : null}
          {isFieldGuidance(guidance) && guidance.safeDefault ? (
            <p className="mt-3 text-[#d8e2f2]">
              <span className="font-semibold">Safe default:</span>{" "}
              {guidance.safeDefault}
            </p>
          ) : null}
          {isFieldGuidance(guidance) && guidance.runtimeEffect ? (
            <p className="mt-3">
              <span className="font-semibold text-[#d8e2f2]">
                Runtime effect:
              </span>{" "}
              {guidance.runtimeEffect}
            </p>
          ) : null}
          {examples.length ? (
            <div className="mt-3">
              <p className="font-semibold text-[#d8e2f2]">Examples</p>
              <ul className="mt-1 grid gap-1">
                {examples.map((example) => (
                  <li key={example.label}>
                    <span className="font-semibold text-[#d8e2f2]">
                      {example.label}:
                    </span>{" "}
                    {example.description}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {warnings.length ? (
            <div className="mt-3 rounded-md border border-amber-300/20 bg-amber-950/20 p-2 text-amber-100">
              <p className="font-semibold">Watch for</p>
              <ul className="mt-1 grid gap-1">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {commonMistakes.length ? (
            <div className="mt-3 rounded-md border border-amber-300/20 bg-amber-950/20 p-2 text-amber-100">
              <p className="font-semibold">Common mistakes</p>
              <ul className="mt-1 grid gap-1">
                {commonMistakes.map((mistake) => (
                  <li key={mistake}>{mistake}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </span>
  );
}
