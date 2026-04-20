import type { User } from "oidc-client-ts";
import { create } from "zustand";

import { mapOidcUser, oidcManager, type SessionUser } from "@/lib/auth";

export type AuthStatus = "anonymous" | "loading" | "authenticated";

interface AuthState {
  status: AuthStatus;
  user: SessionUser | null;
  accessToken: string | null;
  applyOidcUser: (user: User | null) => void;
  clearSession: () => void;
  signIn: () => Promise<void>;
  completeSignIn: () => Promise<void>;
  restoreSession: () => Promise<void>;
  signOut: () => Promise<void>;
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
  async signIn() {
    await oidcManager.signinRedirect();
  },
  async completeSignIn() {
    set({ status: "loading" });
    try {
      const user = await oidcManager.signinRedirectCallback();
      useAuthStore.getState().applyOidcUser(user);
    } catch (error) {
      useAuthStore.getState().clearSession();
      throw error;
    }
  },
  async restoreSession() {
    set({ status: "loading" });
    try {
      const user = await oidcManager.getUser();
      useAuthStore.getState().applyOidcUser(user);
    } catch {
      useAuthStore.getState().clearSession();
    }
  },
  async signOut() {
    useAuthStore.getState().clearSession();
    await oidcManager.signoutRedirect();
  },
}));
