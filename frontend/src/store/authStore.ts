import { create } from 'zustand';

const STORAGE_KEY = 'auth';

export interface AuthUser {
  id: number;
  username: string;
}

export interface LoginResponse {
  status: string;
  token: string;
  user: AuthUser;
  expires_at: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  expiresAt: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  login: (response: LoginResponse) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  validateToken: () => Promise<boolean>;
  getAuthHeaders: () => Record<string, string>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  expiresAt: null,
  isLoading: true,
  isAuthenticated: false,

  login: (response) => {
    const authData = {
      token: response.token,
      user: response.user,
      expiresAt: response.expires_at,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(authData));
    set({
      token: response.token,
      user: response.user,
      expiresAt: response.expires_at,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEY);
    set({
      token: null,
      user: null,
      expiresAt: null,
      isAuthenticated: false,
      isLoading: false,
    });
    window.location.href = '/';
  },

  setLoading: (loading) => set({ isLoading: loading }),

  validateToken: async () => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      set({ isAuthenticated: false, isLoading: false });
      return false;
    }

    try {
      const auth = JSON.parse(stored);

      // Client-side expiry check
      if (new Date(auth.expiresAt) < new Date()) {
        localStorage.removeItem(STORAGE_KEY);
        set({ isAuthenticated: false, isLoading: false });
        return false;
      }

      // Server validation
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/auth/me`,
        { headers: { Authorization: `Bearer ${auth.token}` } }
      );

      if (response.ok) {
        set({
          token: auth.token,
          user: auth.user,
          expiresAt: auth.expiresAt,
          isAuthenticated: true,
          isLoading: false,
        });
        return true;
      } else {
        localStorage.removeItem(STORAGE_KEY);
        set({ isAuthenticated: false, isLoading: false });
        return false;
      }
    } catch {
      // Server unreachable — still allow (show error banner)
      set({ isLoading: false });
      return false;
    }
  },

  getAuthHeaders: (): Record<string, string> => {
    const { token } = get();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },
}));
