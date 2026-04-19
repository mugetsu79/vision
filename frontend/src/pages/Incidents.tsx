export function IncidentsPage() {
  return (
    <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.95),rgba(8,11,18,0.92))] shadow-[0_24px_72px_-54px_rgba(0,0,0,0.9)]">
      <div className="border-b border-white/8 px-6 py-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
          Incidents
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
          Rule-triggered events will surface here next.
        </h2>
        <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
          Prompt 9 will bring incident lists, snapshots, and review details into this
          workspace without changing the shell layout.
        </p>
      </div>
      <div className="px-6 py-6 text-sm text-[#d8e2f2]">
        The navigation is already positioned for operators who need to pivot quickly from
        live surveillance into forensic review.
      </div>
    </section>
  );
}
