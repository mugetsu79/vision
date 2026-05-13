import { useQueryClient } from "@tanstack/react-query";
import { LayoutGroup, motion } from "framer-motion";
import { NavLink } from "react-router-dom";

import { TenantSwitcher } from "@/components/layout/TenantSwitcher";
import { UserMenu } from "@/components/layout/UserMenu";
import {
  prefetchWorkspaceRoute,
  workspaceNavGroups,
} from "@/components/layout/workspace-nav";
import { cn } from "@/lib/utils";

export function AppContextRail() {
  const queryClient = useQueryClient();

  return (
    <aside className="sticky top-0 z-10 hidden h-screen w-[16.5rem] shrink-0 flex-col border-r border-[color:var(--vz-hair)] bg-[linear-gradient(180deg,rgba(8,12,18,0.98),rgba(12,16,23,0.95))] px-4 py-4 lg:flex xl:w-[17.5rem]">
      <LayoutGroup id="nav-focus-group">
        <div className="flex flex-1 flex-col gap-5">
          {workspaceNavGroups.map((group) => (
            <nav key={group.label} aria-label={group.label}>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--vz-text-muted)]">
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
                        "relative flex items-center gap-3 rounded-[var(--vz-r-md)] border px-3 py-2.5 text-sm font-medium transition duration-200",
                        isActive
                          ? "border-[color:var(--vz-hair-focus)] bg-[linear-gradient(90deg,rgba(110,189,255,0.16),transparent_80%)] text-[var(--vz-text-primary)]"
                          : "border-[color:var(--vz-hair)] bg-white/[0.025] text-[var(--vz-text-secondary)] hover:border-[color:var(--vz-hair-strong)] hover:text-[var(--vz-text-primary)]",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive ? (
                          <motion.span
                            layoutId="nav-focus"
                            data-testid="nav-focus-indicator"
                            className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-full bg-[var(--vz-lens-cerulean)] shadow-[0_0_18px_rgba(118,224,255,0.55)]"
                            transition={{
                              type: "spring",
                              stiffness: 480,
                              damping: 38,
                            }}
                          />
                        ) : null}
                        <item.icon
                          className="size-4 shrink-0 opacity-80"
                          aria-hidden="true"
                        />
                        <span>{item.label}</span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </nav>
          ))}
        </div>
      </LayoutGroup>

      <div className="mt-4 space-y-3 border-t border-[color:var(--vz-hair)] pt-4">
        <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--vz-text-muted)]">
            Workspace
          </p>
          <p className="mt-2 text-sm font-medium text-[var(--vz-text-secondary)]">
            OmniSight control layer
          </p>
        </div>
        <TenantSwitcher />
        <UserMenu />
      </div>
    </aside>
  );
}
