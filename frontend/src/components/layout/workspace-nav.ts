import { useEffect } from "react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  Clock3,
  LayoutDashboard,
  type LucideIcon,
  MapPinned,
  Network,
  Radio,
  ServerCog,
  Settings2,
  ShieldAlert,
  Ship,
  Video,
} from "lucide-react";

import { omniNavGroups } from "@/copy/omnisight";
import { getStreamRuntimeHints } from "@/lib/stream-playback";

export type WorkspaceNavItem = {
  label: string;
  to: string;
  icon: LucideIcon;
  children?: readonly WorkspaceNavChildItem[];
};

export type WorkspaceNavChildItem = {
  label: string;
  to: string;
};

export type WorkspaceNavGroup = {
  label: string;
  items: readonly WorkspaceNavItem[];
};

const baseWorkspaceNavGroups = omniNavGroups.map((group) => ({
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
              : item.to === "/deployment"
                ? ServerCog
                : item.to === "/sites"
                  ? MapPinned
                  : item.to === "/cameras"
                    ? Video
                    : Settings2,
  })),
})) as readonly WorkspaceNavGroup[];

const controlLinks = [
  { label: "Links", to: "/links", icon: Network },
] as const satisfies readonly WorkspaceNavItem[];

const workspaceNavGroupsWithLinks: readonly WorkspaceNavGroup[] =
  baseWorkspaceNavGroups.map(
    (group): WorkspaceNavGroup =>
      group.label === "Control"
        ? { label: group.label, items: [...controlLinks, ...group.items] }
        : group,
  );

const fleetOpsChildren = [
  { label: "Vessels", to: "/fleetops/vessels" },
  { label: "Evidence", to: "/fleetops/evidence" },
  { label: "Billing", to: "/fleetops/billing" },
  { label: "Support", to: "/fleetops/support" },
  { label: "Onboarding", to: "/fleetops/onboarding" },
] as const satisfies readonly WorkspaceNavChildItem[];

export const workspaceNavGroups = [
  ...workspaceNavGroupsWithLinks,
  {
    label: "Packs",
    items: [
      {
        label: "FleetOps",
        to: "/fleetops",
        icon: Ship,
        children: fleetOpsChildren,
      },
    ],
  },
] as const satisfies readonly WorkspaceNavGroup[];

export const workspaceNavItems = workspaceNavGroups.flatMap(
  (group) => group.items,
);

async function prefetchHistoryQuery(queryClient: QueryClient) {
  const { createDefaultHistoryFilters, historySeriesQueryOptions } =
    await import("@/hooks/use-history");

  await queryClient.prefetchQuery(
    historySeriesQueryOptions(createDefaultHistoryFilters()),
  );
}

export function prefetchWorkspaceRoute(
  route: string,
  queryClient?: QueryClient,
) {
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

  if (route === "/deployment") {
    void import("@/pages/Deployment");
  }

  if (route === "/links") {
    void import("@/pages/Links");
  }

  if (route === "/fleetops") {
    void import("@/pages/FleetOps");
  }

  if (route === "/fleetops/vessels") {
    void import("@/pages/FleetOpsVessels");
  }

  if (route === "/fleetops/evidence") {
    void import("@/pages/FleetOpsEvidence");
  }

  if (route === "/fleetops/billing") {
    void import("@/pages/FleetOpsBilling");
  }

  if (route === "/fleetops/support") {
    void import("@/pages/FleetOpsSupport");
  }

  if (route === "/fleetops/onboarding") {
    void import("@/pages/FleetOpsOnboarding");
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
