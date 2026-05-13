import { useState, type PropsWithChildren } from "react";

import { OmniSightField } from "@/components/brand/OmniSightField";
import { AppContextRail } from "@/components/layout/AppContextRail";
import { AppIconRail } from "@/components/layout/AppIconRail";
import { useWorkspaceRouteWarmup } from "@/components/layout/workspace-nav";
import { WorkspaceTransition } from "@/components/layout/WorkspaceTransition";
import { cn } from "@/lib/utils";

const contextRailStorageKey = "vezor.context-rail-expanded";

function readStoredContextRailPreference() {
  if (typeof window === "undefined") {
    return true;
  }

  return window.localStorage.getItem(contextRailStorageKey) !== "false";
}

export function AppShell({ children }: PropsWithChildren) {
  useWorkspaceRouteWarmup();
  const [isContextRailExpanded, setIsContextRailExpanded] = useState(
    readStoredContextRailPreference,
  );

  function toggleContextRail() {
    const nextValue = !isContextRailExpanded;
    setIsContextRailExpanded(nextValue);
    window.localStorage.setItem(contextRailStorageKey, String(nextValue));
  }

  return (
    <main
      data-testid="spatial-cockpit-shell"
      className="relative min-h-screen overflow-hidden bg-[radial-gradient(60%_60%_at_70%_0%,rgba(110,189,255,0.10),transparent_60%),linear-gradient(180deg,var(--vz-canvas-void)_0%,var(--vz-canvas-obsidian)_60%,var(--vz-canvas-void)_100%)] text-[var(--vz-text-primary)]"
    >
      <OmniSightField variant="shell" className="opacity-50" />
      <div
        className={cn(
          "relative z-10 grid min-h-screen grid-cols-[4.75rem_minmax(0,1fr)]",
          isContextRailExpanded &&
            "lg:grid-cols-[4.75rem_16.5rem_minmax(0,1fr)] xl:grid-cols-[4.75rem_17.5rem_minmax(0,1fr)]",
        )}
      >
        <AppIconRail
          contextRailExpanded={isContextRailExpanded}
          onToggleContextRail={toggleContextRail}
        />
        {isContextRailExpanded ? <AppContextRail /> : null}
        <section
          data-testid="spatial-workspace-stage"
          className="min-w-0 px-4 py-4 sm:px-6 lg:px-8 lg:py-6"
        >
          <WorkspaceTransition>{children}</WorkspaceTransition>
        </section>
      </div>
    </main>
  );
}
