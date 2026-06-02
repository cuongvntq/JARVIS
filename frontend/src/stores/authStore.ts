import { create } from "zustand";
import type { UserOut } from "@/lib/types/api";

interface AuthState {
  user: UserOut | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: UserOut, token: string) => void;
  clearAuth: () => void;
  setLoading: (v: boolean) => void;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: true,

  setAuth: (user, token) =>
    set({ user, accessToken: token, isAuthenticated: true, isLoading: false }),

  clearAuth: () =>
    set({ user: null, accessToken: null, isAuthenticated: false, isLoading: false }),

  setLoading: (v) => set({ isLoading: v }),

  logout: async () => {
    const { api } = await import("@/lib/api");
    try {
      await api.logout();
    } catch {
      // ignore errors — clear local state regardless
    }
    get().clearAuth();
  },
}));
