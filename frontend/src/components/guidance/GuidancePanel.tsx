import type { SectionGuidance } from "@/components/guidance/guidance-types";

type GuidancePanelProps = {
  guidance: SectionGuidance;
};

export function GuidancePanel({ guidance }: GuidancePanelProps) {
  return (
    <section className="rounded-lg border border-white/10 bg-[#07101b] p-4">
      {guidance.eyebrow ? (
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7894bd]">
          {guidance.eyebrow}
        </p>
      ) : null}
      <h3 className="mt-2 text-sm font-semibold text-[#f4f8ff]">{guidance.title}</h3>
      <p className="mt-2 text-xs leading-5 text-[#9fb2cf]">{guidance.summary}</p>
      {guidance.concepts?.length ? (
        <dl className="mt-3 grid gap-2 text-xs leading-5">
          {guidance.concepts.map((concept) => (
            <div key={concept.term}>
              <dt className="font-semibold text-[#d8e2f2]">{concept.term}</dt>
              <dd className="text-[#9fb2cf]">{concept.definition}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {guidance.steps?.length ? (
        <ol className="mt-3 grid gap-1 text-xs leading-5 text-[#d8e2f2]">
          {guidance.steps.map((step, index) => (
            <li key={step}>
              <span className="mr-2 text-[#8fd3ff]">{index + 1}.</span>
              {step}
            </li>
          ))}
        </ol>
      ) : null}
      {guidance.examples?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {guidance.examples.map((example) => (
            <div
              key={example.label}
              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-[#d8e2f2]"
            >
              <span className="font-semibold">{example.label}:</span>{" "}
              {example.description}
            </div>
          ))}
        </div>
      ) : null}
      {guidance.warnings?.length ? (
        <div className="mt-3 rounded-lg border border-amber-300/20 bg-amber-950/20 p-3">
          <p className="text-xs font-semibold text-amber-100">Watch for</p>
          <ul className="mt-2 grid gap-1 text-xs leading-5 text-amber-100/85">
            {guidance.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {guidance.commonMistakes?.length ? (
        <div className="mt-3 rounded-lg border border-amber-300/20 bg-amber-950/20 p-3">
          <p className="text-xs font-semibold text-amber-100">Common mistakes</p>
          <ul className="mt-2 grid gap-1 text-xs leading-5 text-amber-100/85">
            {guidance.commonMistakes.map((mistake) => (
              <li key={mistake}>{mistake}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
