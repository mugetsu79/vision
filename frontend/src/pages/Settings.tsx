export function SettingsPage() {
  return (
    <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.95),rgba(8,11,18,0.92))] shadow-[0_24px_72px_-54px_rgba(0,0,0,0.9)]">
      <div className="border-b border-white/8 px-6 py-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
          Settings
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
          Configuration stays close, but not in the way.
        </h2>
        <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
          The top rail stays operational while the management column keeps Sites and
          Cameras one click away for administrators.
        </p>
      </div>
      <div className="px-6 py-6 text-sm text-[#d8e2f2]">
        Prompt 7 uses this route as a stable anchor before deeper settings surfaces arrive
        in later prompts.
      </div>
    </section>
  );
}
