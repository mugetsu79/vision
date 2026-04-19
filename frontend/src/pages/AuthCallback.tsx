import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "@/stores/auth-store";

export function AuthCallbackPage() {
  const completeSignIn = useAuthStore((state) => state.completeSignIn);
  const navigate = useNavigate();
  const hasHandledCallback = useRef(false);

  useEffect(() => {
    if (hasHandledCallback.current) {
      return;
    }

    hasHandledCallback.current = true;
    void completeSignIn().then(
      () => navigate("/dashboard", { replace: true }),
      () => navigate("/signin", { replace: true }),
    );
  }, [completeSignIn, navigate]);

  return <main className="p-8 text-sm text-slate-300">Completing sign-in...</main>;
}
