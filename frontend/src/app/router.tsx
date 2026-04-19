import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";

import { AppProviders } from "@/app/providers";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { AuthCallbackPage } from "@/pages/AuthCallback";
import { CamerasPage } from "@/pages/Cameras";
import { DashboardPage } from "@/pages/Dashboard";
import { HistoryPage } from "@/pages/History";
import { IncidentsPage } from "@/pages/Incidents";
import { SettingsPage } from "@/pages/Settings";
import { SignInPage } from "@/pages/SignIn";
import { SitesPage } from "@/pages/Sites";

const shellLayoutElement = (
  <RequireAuth>
    <AppShell>
      <Outlet />
    </AppShell>
  </RequireAuth>
);

export const router = createBrowserRouter([
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
    element: (
      <AppProviders>
        {shellLayoutElement}
      </AppProviders>
    ),
    children: [
      { index: true, element: <Navigate to="dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "live", element: <DashboardPage /> },
      { path: "history", element: <HistoryPage /> },
      { path: "incidents", element: <IncidentsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "sites", element: <SitesPage /> },
      { path: "cameras", element: <CamerasPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/signin" replace /> },
], {
  future: {
    v7_relativeSplatPath: true,
  },
});
