import { useQueryClient } from "@tanstack/react-query";
import { ChevronsLeft, ChevronsRight } from "lucide-react";
import { NavLink } from "react-router-dom";

import { ProductLockup } from "@/components/layout/ProductLockup";
import {
  prefetchWorkspaceRoute,
  workspaceNavGroups,
} from "@/components/layout/TopNav";
import { cn } from "@/lib/utils";

interface AppIconRailProps {
  contextRailExpanded: boolean;
  onToggleContextRail: () => void;
}

export function AppIconRail({
  contextRailExpanded,
  onToggleContextRail,
}: AppIconRailProps) {
  const queryClient = useQueryClient();

  return (
    <aside className="sticky top-0 z-10 flex h-screen w-[4.75rem] shrink-0 flex-col border-r border-white/[0.06] bg-[linear-gradient(180deg,rgba(7,10,15,0.98),rgba(10,14,20,0.96))] px-2 py-4">
      <div className="flex h-full flex-col items-center gap-4">
        <ProductLockup symbolOnly className="size-11 rounded-[1rem]" />
        <button
          aria-label={contextRailExpanded ? "Hide section rail" : "Show section rail"}
          className="grid size-9 place-items-center rounded-[0.95rem] border border-white/[0.06] bg-white/[0.03] text-[#9fb0c9] transition duration-200 hover:border-[#35598d] hover:bg-white/[0.06] hover:text-[#eef4ff]"
          type="button"
          onClick={onToggleContextRail}
        >
          {contextRailExpanded ? (
            <ChevronsLeft className="size-4" aria-hidden="true" />
          ) : (
            <ChevronsRight className="size-4" aria-hidden="true" />
          )}
        </button>

        <nav
          aria-label="Primary workspace"
          className="flex flex-1 flex-col items-center justify-center gap-5"
        >
          {workspaceNavGroups.map((group) => (
            <div key={group.label} className="flex flex-col items-center gap-2">
              {group.items.map((item) => (
                <NavLink
                  key={item.label}
                  to={item.to}
                  aria-label={item.label}
                  title={item.label}
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
                      "grid size-10 place-items-center rounded-[1rem] border transition duration-200",
                      isActive
                        ? "border-[#35598d] bg-[rgba(43,71,110,0.34)] text-[#eef4ff] shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
                        : "border-white/[0.06] bg-white/[0.03] text-[#9fb0c9] hover:border-[#35598d] hover:bg-white/[0.06] hover:text-[#eef4ff]",
                    )
                  }
                >
                  <item.icon className="size-4" aria-hidden="true" />
                </NavLink>
              ))}
              {group.label === "Operations" ? (
                <div className="mt-2 h-px w-6 bg-white/[0.06]" />
              ) : null}
            </div>
          ))}
        </nav>
      </div>
    </aside>
  );
}
