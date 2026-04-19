import { create } from "zustand";

import { mapOidcUser, oidcManager, type SessionUser } from "@/lib/auth";

export type AuthStatus = "anonymous" | "loading" | "authenticated";

interface AuthState {
  status: AuthStatus;
  user: SessionUser | null;
  accessToken: string | null;
  signIn: () => Promise<void>;
  completeSignIn: () => Promise<void>;
  restoreSession: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  status: "anonymous",
  user: null,
  accessToken: null,
  async signIn() {
    await oidcManager.signinRedirect();
  },
  async completeSignIn() {
    set({ status: "loading" });
    try {
      const user = await oidcManager.signinRedirectCallback();
      set({
        status: "authenticated",
        user: mapOidcUser(user),
        accessToken: user.access_token ?? null,
      });
    } catch (error) {
      set({ status: "anonymous", user: null, accessToken: null });
      throw error;
    }
  },
  async restoreSession() {
    set({ status: "loading" });
    try {
      const user = await oidcManager.getUser();

      if (!user || user.expired) {
        set({ status: "anonymous", user: null, accessToken: null });
        return;
      }

      set({
        status: "authenticated",
        user: mapOidcUser(user),
        accessToken: user.access_token ?? null,
      });
    } catch {
      set({ status: "anonymous", user: null, accessToken: null });
    }
  },
  async signOut() {
    set({ status: "anonymous", user: null, accessToken: null });
    await oidcManager.signoutRedirect();
  },
}));
