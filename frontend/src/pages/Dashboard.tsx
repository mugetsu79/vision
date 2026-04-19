export function DashboardPage() {
  return (
    <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.95),rgba(8,11,18,0.92))] shadow-[0_28px_84px_-52px_rgba(39,110,255,0.58)]">
      <div className="border-b border-white/8 px-6 py-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
          Dashboard
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
          Fleet overview becomes live in Prompt 8.
        </h2>
        <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
          The shell is ready for the upcoming camera wall, live tiles, and stream-state
          controls. For now, this page anchors the command center and keeps navigation
          stable.
        </p>
      </div>
      <div className="grid gap-4 px-6 py-6 lg:grid-cols-3">
        <div className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#89a0c3]">
            Operations rail
          </p>
          <p className="mt-3 text-sm text-[#d8e2f2]">
            Primary routes stay persistent so operators can jump between live, history,
            incidents, and configuration without losing orientation.
          </p>
        </div>
        <div className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#89a0c3]">
            Delivery-aware
          </p>
          <p className="mt-3 text-sm text-[#d8e2f2]">
            Prompt 8 will attach native ingest versus browser delivery decisions to the
            live workspace without changing the shell structure.
          </p>
        </div>
        <div className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#89a0c3]">
            Ready next
          </p>
          <p className="mt-3 text-sm text-[#d8e2f2]">
            The management rail already reserves space for the Sites and Cameras flows
            that land in the next tasks.
          </p>
        </div>
      </div>
    </section>
  );
}
