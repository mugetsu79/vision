import { useState, type PropsWithChildren } from "react";

import { AppContextRail } from "@/components/layout/AppContextRail";
import { AppIconRail } from "@/components/layout/AppIconRail";
import { useWorkspaceRouteWarmup } from "@/components/layout/TopNav";
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
    <main className="min-h-screen bg-[#0a0d12] text-[#eef4ff]">
      <div
        className={cn(
          "grid min-h-screen grid-cols-[4.75rem_minmax(0,1fr)]",
          isContextRailExpanded &&
            "lg:grid-cols-[4.75rem_16.5rem_minmax(0,1fr)] xl:grid-cols-[4.75rem_17.5rem_minmax(0,1fr)]",
        )}
      >
        <AppIconRail
          contextRailExpanded={isContextRailExpanded}
          onToggleContextRail={toggleContextRail}
        />
        {isContextRailExpanded ? <AppContextRail /> : null}
        <section className="min-w-0 bg-[radial-gradient(circle_at_top,rgba(52,77,115,0.15),transparent_42%),linear-gradient(180deg,rgba(10,13,18,0.8),rgba(10,13,18,0.72))] px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
          <div className="min-h-[calc(100vh-2rem)] rounded-[1.8rem] border border-white/[0.06] bg-[rgba(8,12,18,0.78)] shadow-[0_24px_72px_-54px_rgba(0,0,0,0.92)]">
            {children}
          </div>
        </section>
      </div>
    </main>
  );
}
