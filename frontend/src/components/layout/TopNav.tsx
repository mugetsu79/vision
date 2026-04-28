import { useEffect } from "react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  Clock3,
  type LucideIcon,
  MapPinned,
  Radio,
  Settings2,
  ShieldAlert,
  Video,
} from "lucide-react";

import { getStreamRuntimeHints } from "@/lib/stream-playback";

export type WorkspaceNavItem = {
  label: string;
  to: string;
  icon: LucideIcon;
};

export type WorkspaceNavGroup = {
  label: string;
  items: readonly WorkspaceNavItem[];
};

export const workspaceNavGroups = [
  {
    label: "Operations",
    items: [
      { label: "Live", to: "/live", icon: Radio },
      { label: "History", to: "/history", icon: Clock3 },
      { label: "Incidents", to: "/incidents", icon: ShieldAlert },
    ],
  },
  {
    label: "Configuration",
    items: [
      { label: "Sites", to: "/sites", icon: MapPinned },
      { label: "Cameras", to: "/cameras", icon: Video },
      { label: "Operations", to: "/settings", icon: Settings2 },
    ],
  },
] as const satisfies readonly WorkspaceNavGroup[];

async function prefetchHistoryQuery(queryClient: QueryClient) {
  const { createDefaultHistoryFilters, historySeriesQueryOptions } = await import(
    "@/hooks/use-history"
  );

  await queryClient.prefetchQuery(
    historySeriesQueryOptions(createDefaultHistoryFilters()),
  );
}

export function prefetchWorkspaceRoute(route: string, queryClient?: QueryClient) {
  if (route === "/history") {
    void import("@/pages/History");
    void import("@/components/history/HistoryTrendChart");

    if (queryClient) {
      void prefetchHistoryQuery(queryClient);
    }
  }

  if (route === "/incidents") {
    void import("@/pages/Incidents");
  }
}

export function useWorkspaceRouteWarmup() {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (getStreamRuntimeHints().lowPower) {
      return;
    }

    prefetchWorkspaceRoute("/history", queryClient);
    prefetchWorkspaceRoute("/incidents", queryClient);
  }, [queryClient]);
}

export function TopNav() {
  return null;
}
