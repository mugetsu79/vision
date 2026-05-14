import type { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useBootstrapStatus } from "@/hooks/use-bootstrap";
import { useAuthStore } from "@/stores/auth-store";

export function RequireAuth({ children }: PropsWithChildren) {
  const status = useAuthStore((state) => state.status);
  const location = useLocation();
  const bootstrapStatus = useBootstrapStatus();

  if (status === "loading") {
    return <div className="p-8 text-sm text-slate-300">Restoring session...</div>;
  }

  if (status === "anonymous") {
    if (bootstrapStatus.isLoading) {
      return <div className="p-8 text-sm text-slate-300">Checking setup...</div>;
    }
    if (bootstrapStatus.data?.first_run_required) {
      return <Navigate to="/first-run" replace />;
    }
    return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
