import { useQueryClient } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";

import { TenantSwitcher } from "@/components/layout/TenantSwitcher";
import { UserMenu } from "@/components/layout/UserMenu";
import {
  prefetchWorkspaceRoute,
  workspaceNavGroups,
} from "@/components/layout/TopNav";
import { cn } from "@/lib/utils";

export function AppContextRail() {
  const queryClient = useQueryClient();

  return (
    <aside className="sticky top-0 z-10 hidden h-screen w-[16.5rem] shrink-0 flex-col border-r border-white/[0.06] bg-[linear-gradient(180deg,rgba(8,12,18,0.98),rgba(12,16,23,0.95))] px-4 py-4 lg:flex xl:w-[17.5rem]">
      <div className="flex flex-1 flex-col gap-5">
        {workspaceNavGroups.map((group) => (
          <nav key={group.label} aria-label={group.label}>
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8fa2be]">
              {group.label}
            </p>
            <div className="mt-3 space-y-1.5">
              {group.items.map((item) => (
                <NavLink
                  key={item.label}
                  to={item.to}
                  onFocus={() => {
                    prefetchWorkspaceRoute(item.to, queryClient);
                  }}
                  onMouseEnter={() => {
                    prefetchWorkspaceRoute(item.to, queryClient);
                  }}
                  onPointerDown={() => {
                    prefetchWorkspaceRoute(item.to, queryClient);
                  }}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-[1.15rem] border px-3 py-2.5 text-sm font-medium transition duration-200",
                      isActive
                        ? "border-[#35598d] bg-[rgba(30,46,71,0.56)] text-[#eef4ff] shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
                        : "border-white/[0.05] bg-white/[0.025] text-[#bfd0e6] hover:border-[#35598d] hover:bg-white/[0.05] hover:text-[#eef4ff]",
                    )
                  }
                >
                  <item.icon className="size-4 shrink-0 opacity-80" aria-hidden="true" />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          </nav>
        ))}
      </div>

      <div className="mt-4 space-y-3 border-t border-white/[0.06] pt-4">
        <TenantSwitcher />
        <UserMenu />
      </div>
    </aside>
  );
}
