import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";

import { TopNav } from "@/components/layout/TopNav";
import { TenantSwitcher } from "@/components/layout/TenantSwitcher";
import { UserMenu } from "@/components/layout/UserMenu";
import { cn } from "@/lib/utils";

const managementNav = [
  { label: "Sites", to: "/sites" },
  { label: "Cameras", to: "/cameras" },
] as const;

export function AppShell({ children }: PropsWithChildren) {
  return (
    <main className="min-h-screen px-4 pb-8 pt-5 text-[#eef4ff] sm:px-8 lg:px-10">
      <div className="fixed inset-x-4 top-5 z-20 sm:inset-x-8 lg:inset-x-10">
        <header className="mx-auto max-w-[1500px] overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.94),rgba(7,11,18,0.92))] shadow-[0_30px_80px_-44px_rgba(44,112,255,0.52)] backdrop-blur-xl">
          <div className="absolute inset-x-12 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(93,145,255,0.7),rgba(150,111,255,0.55),transparent)]" />
          <div className="flex flex-col gap-5 px-6 py-6 xl:flex-row xl:items-center xl:justify-between">
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.34em] text-[#aab9d2]">
                  Argus | The OmniSight Platform
                </p>
                <h1 className="text-2xl font-semibold tracking-[0.01em] text-[#f5f8ff]">
                  Hybrid command center
                </h1>
                <p className="max-w-2xl text-sm text-[#8ea4c7]">
                  Operate the fleet, stage camera configuration, and move across live,
                  history, and incident workflows from one persistent workspace.
                </p>
              </div>
              <TopNav />
            </div>
            <div className="flex flex-wrap items-center justify-end gap-3">
              <TenantSwitcher />
              <UserMenu />
            </div>
          </div>
        </header>
      </div>

      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-[1500px] flex-col gap-6 pt-[17rem] xl:pt-[13.25rem]">
        <div className="grid flex-1 gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
          <section className="min-w-0">{children}</section>
          <aside className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(11,16,26,0.96),rgba(7,10,17,0.94))] shadow-[0_24px_70px_-48px_rgba(0,0,0,0.92)] backdrop-blur-xl xl:sticky xl:top-32 xl:h-fit">
            <div className="border-b border-white/8 px-5 py-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8ea4c7]">
                Management
              </p>
              <p className="mt-2 text-sm text-[#6f84a6]">
                Configuration surfaces stay one step away from the operational rail.
              </p>
            </div>
            <div className="flex flex-col gap-2 p-4">
              {managementNav.map((item) => (
                <NavLink
                  key={item.label}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "rounded-[1.25rem] px-4 py-3 text-sm font-medium transition duration-200",
                      isActive
                        ? "border border-[#35507f] bg-[linear-gradient(180deg,rgba(24,38,61,0.98),rgba(16,25,40,0.96))] text-[#eef4ff] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                        : "border border-white/8 bg-white/[0.03] text-[#c3d2e6] hover:border-[#37507a] hover:bg-[#111b2b] hover:text-[#eef4ff]",
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
