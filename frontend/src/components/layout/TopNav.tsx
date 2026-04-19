import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";

import {
  createDefaultHistoryFilters,
  historySeriesQueryOptions,
} from "@/hooks/use-history";
import { getStreamRuntimeHints } from "@/lib/stream-playback";
import { cn } from "@/lib/utils";

const primaryNav = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Live", to: "/live" },
  { label: "History", to: "/history" },
  { label: "Incidents", to: "/incidents" },
  { label: "Settings", to: "/settings" },
] as const;

function prefetchRoute(route: string) {
  if (route === "/history") {
    void import("@/pages/History");
    void import("@/components/history/HistoryTrendChart");
  }

  if (route === "/incidents") {
    void import("@/pages/Incidents");
  }
}

export function TopNav() {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (getStreamRuntimeHints().lowPower) {
      return;
    }

    prefetchRoute("/history");
    prefetchRoute("/incidents");
    void queryClient.prefetchQuery(
      historySeriesQueryOptions(createDefaultHistoryFilters()),
    );
  }, [queryClient]);

  return (
    <nav className="flex flex-wrap items-center gap-2" aria-label="Primary">
      {primaryNav.map((item) => (
        <NavLink
          key={item.label}
          to={item.to}
          onFocus={() => {
            prefetchRoute(item.to);
            if (item.to === "/history") {
              void queryClient.prefetchQuery(
                historySeriesQueryOptions(createDefaultHistoryFilters()),
              );
            }
          }}
          onMouseEnter={() => {
            prefetchRoute(item.to);
            if (item.to === "/history") {
              void queryClient.prefetchQuery(
                historySeriesQueryOptions(createDefaultHistoryFilters()),
              );
            }
          }}
          onPointerDown={() => {
            prefetchRoute(item.to);
            if (item.to === "/history") {
              void queryClient.prefetchQuery(
                historySeriesQueryOptions(createDefaultHistoryFilters()),
              );
            }
          }}
          className={({ isActive }) =>
            cn(
              "rounded-full px-4 py-2 text-sm font-medium transition duration-200",
              isActive
                ? "bg-[linear-gradient(135deg,rgba(47,124,255,0.95),rgba(128,92,255,0.95))] text-white shadow-[0_14px_32px_-18px_rgba(84,109,255,0.95)]"
                : "border border-white/10 bg-white/[0.04] text-[#a8bbd7] hover:border-[#37507a] hover:bg-[#0f1826] hover:text-[#eef4ff]",
            )
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
