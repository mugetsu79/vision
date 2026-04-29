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
    <main
      data-testid="spatial-cockpit-shell"
      className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_55%_36%,rgba(74,121,211,0.16),transparent_30%),linear-gradient(180deg,#05080d_0%,#08101a_48%,#03050a_100%)] text-[#eef4ff]"
    >
      <OmniSightField variant="shell" className="opacity-85" />
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
