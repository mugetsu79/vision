import type { User } from "oidc-client-ts";
import { create } from "zustand";

import {
  mapOidcUser,
  oidcManager,
  type AuthRealm,
  type SessionUser,
} from "@/lib/auth";

export type AuthStatus = "anonymous" | "loading" | "authenticated";

interface AuthState {
  status: AuthStatus;
  user: SessionUser | null;
  accessToken: string | null;
  applyOidcUser: (user: User | null) => void;
  clearSession: () => void;
  signIn: (realm?: AuthRealm) => Promise<void>;
  completeSignIn: () => Promise<void>;
  restoreSession: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AUTH_REALM_STORAGE_KEY = "vezor:auth-realm";

function readAuthRealmHint(): AuthRealm {
  if (typeof window === "undefined") {
    return "tenant";
  }

  return window.sessionStorage.getItem(AUTH_REALM_STORAGE_KEY) === "platform"
    ? "platform"
    : "tenant";
}

function writeAuthRealmHint(realm: AuthRealm) {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(AUTH_REALM_STORAGE_KEY, realm);
  }
}

function clearAuthRealmHint() {
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(AUTH_REALM_STORAGE_KEY);
  }
}

async function resolveManager(realm: AuthRealm) {
  if (realm === "tenant") {
    return oidcManager;
  }

  const { platformOidcManager } = await import("@/lib/auth");
  return platformOidcManager;
}

export const useAuthStore = create<AuthState>((set) => ({
  status: "anonymous",
  user: null,
  accessToken: null,
  applyOidcUser(user) {
    if (!user || user.expired) {
      set({ status: "anonymous", user: null, accessToken: null });
      return;
    }

    set({
      status: "authenticated",
      user: mapOidcUser(user),
      accessToken: user.access_token ?? null,
    });
  },
  clearSession() {
    set({ status: "anonymous", user: null, accessToken: null });
  },
  async signIn(realm = "tenant") {
    writeAuthRealmHint(realm);
    await (await resolveManager(realm)).signinRedirect();
  },
  async completeSignIn() {
    set({ status: "loading" });
    try {
      const user = await (
        await resolveManager(readAuthRealmHint())
      ).signinRedirectCallback();
      useAuthStore.getState().applyOidcUser(user);
      clearAuthRealmHint();
    } catch (error) {
      useAuthStore.getState().clearSession();
      clearAuthRealmHint();
      throw error;
    }
  },
  async restoreSession() {
    set({ status: "loading" });
    try {
      const user = await oidcManager.getUser();
      if (user && !user.expired) {
        useAuthStore.getState().applyOidcUser(user);
        return;
      }

      const platformUser = await (await resolveManager("platform")).getUser();
      useAuthStore.getState().applyOidcUser(platformUser);
    } catch {
      useAuthStore.getState().clearSession();
    }
  },
  async signOut() {
    const realm = useAuthStore.getState().user?.isSuperadmin
      ? "platform"
      : "tenant";
    useAuthStore.getState().clearSession();
    await (await resolveManager(realm)).signoutRedirect();
  },
}));
