import type { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuthStore } from "@/stores/auth-store";

export function RequireAuth({ children }: PropsWithChildren) {
  const status = useAuthStore((state) => state.status);
  const location = useLocation();

  if (status === "loading") {
    return <div className="p-8 text-sm text-slate-300">Restoring session...</div>;
  }

  if (status === "anonymous") {
    return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
