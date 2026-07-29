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
export declare const useAuthStore: import("zustand").UseBoundStore<import("zustand").StoreApi<AuthState>>;
export {};
