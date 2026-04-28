import { useState, type PropsWithChildren } from "react";

import { OmniSightField } from "@/components/brand/OmniSightField";
import { AppContextRail } from "@/components/layout/AppContextRail";
import { AppIconRail } from "@/components/layout/AppIconRail";
import { useWorkspaceRouteWarmup } from "@/components/layout/TopNav";
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
    <main className="relative min-h-screen overflow-hidden bg-[#080c12] text-[#eef4ff]">
      <OmniSightField variant="shell" className="opacity-80" />
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
        <section className="min-w-0 px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
          <div className="min-h-[calc(100vh-2rem)] rounded-[1.25rem] border border-white/[0.07] bg-[rgba(8,12,18,0.74)] shadow-[0_28px_86px_-60px_rgba(0,0,0,0.94)] backdrop-blur-xl">
            <WorkspaceTransition>{children}</WorkspaceTransition>
          </div>
        </section>
      </div>
    </main>
  );
}
