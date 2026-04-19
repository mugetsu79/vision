export function HistoryPage() {
  return (
    <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.95),rgba(8,11,18,0.92))] shadow-[0_24px_72px_-54px_rgba(0,0,0,0.9)]">
      <div className="border-b border-white/8 px-6 py-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
          History
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
          Time-range queries arrive in Prompt 9.
        </h2>
        <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
          This surface is reserved for bucketed history, trend exploration, and export
          workflows once the analytics views are wired into the frontend.
        </p>
      </div>
      <div className="px-6 py-6 text-sm text-[#d8e2f2]">
        Operators will be able to move from live activity into historical context without
        leaving the same command center shell.
      </div>
    </section>
  );
}
