import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";

import { AppProviders } from "@/app/providers";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { AuthCallbackPage } from "@/pages/AuthCallback";
import { FirstRunPage } from "@/pages/FirstRun";
import { SignInPage } from "@/pages/SignIn";

const shellLayoutElement = (
  <RequireAuth>
    <AppShell>
      <Outlet />
    </AppShell>
  </RequireAuth>
);

export const router = createBrowserRouter(
  [
    {
      path: "/signin",
      element: (
        <AppProviders>
          <SignInPage />
        </AppProviders>
      ),
    },
    {
      path: "/first-run",
      element: (
        <AppProviders>
          <FirstRunPage />
        </AppProviders>
      ),
    },
    {
      path: "/auth/callback",
      element: (
        <AppProviders>
          <AuthCallbackPage />
        </AppProviders>
      ),
    },
    {
      path: "/",
      element: <AppProviders>{shellLayoutElement}</AppProviders>,
      children: [
        { index: true, element: <Navigate to="dashboard" replace /> },
        {
          path: "dashboard",
          lazy: async () => ({
            Component: (await import("@/pages/Dashboard")).DashboardPage,
          }),
        },
        {
          path: "live",
          lazy: async () => ({
            Component: (await import("@/pages/Live")).LivePage,
          }),
        },
        {
          path: "history",
          lazy: async () => ({
            Component: (await import("@/pages/History")).HistoryPage,
          }),
        },
        {
          path: "links",
          lazy: async () => ({
            Component: (await import("@/pages/Links")).LinksPage,
          }),
        },
        {
          path: "incidents",
          lazy: async () => ({
            Component: (await import("@/pages/Incidents")).IncidentsPage,
          }),
        },
        {
          path: "settings",
          lazy: async () => ({
            Component: (await import("@/pages/Settings")).SettingsPage,
          }),
        },
        {
          path: "deployment",
          lazy: async () => ({
            Component: (await import("@/pages/Deployment")).DeploymentPage,
          }),
        },
        {
          path: "models",
          lazy: async () => ({
            Component: (await import("@/pages/Models")).ModelsPage,
          }),
        },
        {
          path: "sites",
          lazy: async () => ({
            Component: (await import("@/pages/Sites")).SitesPage,
          }),
        },
        {
          path: "users",
          lazy: async () => ({
            Component: (await import("@/pages/Users")).UsersPage,
          }),
        },
        {
          path: "cameras",
          lazy: async () => ({
            Component: (await import("@/pages/Cameras")).CamerasPage,
          }),
        },
        {
          path: "fleetops",
          lazy: async () => ({
            Component: (await import("@/pages/FleetOps")).FleetOpsPage,
          }),
        },
        {
          path: "fleetops/vessels",
          lazy: async () => ({
            Component: (await import("@/pages/FleetOpsVessels"))
              .FleetOpsVesselsPage,
          }),
        },
        {
          path: "fleetops/vessels/:vesselId",
          lazy: async () => ({
            Component: (await import("@/pages/FleetOpsVesselDetail"))
              .FleetOpsVesselDetailPage,
          }),
        },
        {
          path: "fleetops/evidence",
          lazy: async () => ({
            Component: (await import("@/pages/FleetOpsEvidence"))
              .FleetOpsEvidencePage,
          }),
        },
        {
          path: "fleetops/billing",
          lazy: async () => ({
            Component: (await import("@/pages/FleetOpsBilling"))
              .FleetOpsBillingPage,
          }),
        },
        {
          path: "fleetops/support",
          lazy: async () => ({
            Component: (await import("@/pages/FleetOpsSupport"))
              .FleetOpsSupportPage,
          }),
        },
        {
          path: "fleetops/onboarding",
          lazy: async () => ({
            Component: (await import("@/pages/FleetOpsOnboarding"))
              .FleetOpsOnboardingPage,
          }),
        },
      ],
    },
    { path: "*", element: <Navigate to="/signin" replace /> },
  ],
  {
    future: {
      v7_relativeSplatPath: true,
    },
  },
);
