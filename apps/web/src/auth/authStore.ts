import { create } from "zustand";
import type { AuthSession, Profile } from "./types";

interface AuthState {
  profile: Profile | null;
  accessToken: string | null;
  refreshToken: string | null;
  initialized: boolean;
  isAuthenticated: () => boolean;
  isAdmin: () => boolean;
  isApproved: () => boolean;
  setSession: (session: AuthSession) => void;
  clearSession: () => void;
  loadFromStorage: () => void;
}

const PROFILE_KEY = "qcm_profile";
const ACCESS_KEY = "qcm_access_token";
const REFRESH_KEY = "qcm_refresh_token";

export const useAuthStore = create<AuthState>((set, get) => ({
  profile: null,
  accessToken: null,
  refreshToken: null,
  initialized: false,

  isAuthenticated: () => get().accessToken !== null,
  isAdmin: () => get().profile?.role === "admin",
  isApproved: () => get().profile?.status === "active",

  setSession: (session) => {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(session.profile));
    localStorage.setItem(ACCESS_KEY, session.tokens.access_token);
    if (session.tokens.refresh_token) {
      localStorage.setItem(REFRESH_KEY, session.tokens.refresh_token);
    }
    set({
      profile: session.profile,
      accessToken: session.tokens.access_token,
      refreshToken: session.tokens.refresh_token ?? null,
      initialized: true
    });
  },

  clearSession: () => {
    localStorage.removeItem(PROFILE_KEY);
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    set({ profile: null, accessToken: null, refreshToken: null, initialized: true });
  },

  loadFromStorage: () => {
    const rawProfile = localStorage.getItem(PROFILE_KEY);
    const accessToken = localStorage.getItem(ACCESS_KEY);
    const refreshToken = localStorage.getItem(REFRESH_KEY);

    if (rawProfile && accessToken) {
      try {
        set({
          profile: JSON.parse(rawProfile) as Profile,
          accessToken,
          refreshToken,
          initialized: true
        });
        return;
      } catch {
        // Fall through to clear invalid local session state.
      }
    }

    get().clearSession();
  }
}));
