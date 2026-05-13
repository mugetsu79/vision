import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";

import { AppProviders } from "@/app/providers";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { AuthCallbackPage } from "@/pages/AuthCallback";
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
          path: "sites",
          lazy: async () => ({
            Component: (await import("@/pages/Sites")).SitesPage,
          }),
        },
        {
          path: "cameras",
          lazy: async () => ({
            Component: (await import("@/pages/Cameras")).CamerasPage,
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
