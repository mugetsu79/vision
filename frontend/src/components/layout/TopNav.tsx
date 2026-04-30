import { useEffect } from "react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  Clock3,
  LayoutDashboard,
  type LucideIcon,
  MapPinned,
  Radio,
  Settings2,
  ShieldAlert,
  Video,
} from "lucide-react";

import { omniNavGroups } from "@/copy/omnisight";
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

export const workspaceNavGroups = omniNavGroups.map((group) => ({
  label: group.label,
  items: group.items.map((item) => ({
    ...item,
    icon:
      item.to === "/dashboard"
        ? LayoutDashboard
        : item.to === "/live"
        ? Radio
        : item.to === "/history"
          ? Clock3
          : item.to === "/incidents"
            ? ShieldAlert
            : item.to === "/sites"
              ? MapPinned
              : item.to === "/cameras"
                ? Video
                : Settings2,
  })),
})) as readonly WorkspaceNavGroup[];

async function prefetchHistoryQuery(queryClient: QueryClient) {
  const { createDefaultHistoryFilters, historySeriesQueryOptions } = await import(
    "@/hooks/use-history"
  );

  await queryClient.prefetchQuery(
    historySeriesQueryOptions(createDefaultHistoryFilters()),
  );
}

export function prefetchWorkspaceRoute(route: string, queryClient?: QueryClient) {
  if (route === "/dashboard") {
    void import("@/pages/Dashboard");
  }

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
