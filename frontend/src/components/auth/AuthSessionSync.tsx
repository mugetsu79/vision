import { useEffect } from "react";

import { oidcManager } from "@/lib/auth";
import { useAuthStore } from "@/stores/auth-store";

export function AuthSessionSync() {
  const applyOidcUser = useAuthStore((state) => state.applyOidcUser);
  const clearSession = useAuthStore((state) => state.clearSession);
  const restoreSession = useAuthStore((state) => state.restoreSession);

  useEffect(() => {
    void restoreSession();

    const removeUserLoaded = oidcManager.events?.addUserLoaded?.((user) => {
      applyOidcUser(user);
    });
    const removeAccessTokenExpired = oidcManager.events?.addAccessTokenExpired?.(() => {
      void restoreSession();
    });
    const removeSilentRenewError = oidcManager.events?.addSilentRenewError?.(() => {
      void restoreSession();
    });
    const removeUserSignedOut = oidcManager.events?.addUserSignedOut?.(() => {
      clearSession();
    });

    return () => {
      removeUserLoaded?.();
      removeAccessTokenExpired?.();
      removeSilentRenewError?.();
      removeUserSignedOut?.();
    };
  }, [applyOidcUser, clearSession, restoreSession]);

  return null;
}
