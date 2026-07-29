import { useAuthStore } from '@/store/authStore';

const API_BASE = import.meta.env.VITE_API_BASE_URL;

// Endpoints that should NOT trigger 401 redirect
const AUTH_ENDPOINTS = ['/api/auth/login', '/api/auth/signup'];

interface ApiOptions extends RequestInit {
  skipAuth?: boolean;
  skip401Redirect?: boolean;
}

export async function apiFetch(
  url: string,
  options: ApiOptions = {}
): Promise<Response> {
  const { skipAuth = false, skip401Redirect = false, ...fetchOptions } = options;

  // Add auth headers unless skipped
  let headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((fetchOptions.headers as Record<string, string>) || {}),
  };

  if (!skipAuth) {
    const authHeaders = useAuthStore.getState().getAuthHeaders();
    headers = { ...headers, ...authHeaders };
  }

  const response = await fetch(`${API_BASE}${url}`, {
    ...fetchOptions,
    headers,
  });

  // Handle 401 responses
  if (response.status === 401 && !skip401Redirect) {
    const isAuthEndpoint = AUTH_ENDPOINTS.some((endpoint) =>
      url.startsWith(endpoint)
    );

    if (!isAuthEndpoint) {
      // Clear auth state WITHOUT redirecting — manually clear so we can read redirect field
      localStorage.removeItem('auth');
      useAuthStore.setState({ token: null, user: null, expiresAt: null, isAuthenticated: false, isLoading: false });

      // Read redirect field from response and navigate there
      try {
        const body = await response.clone().json();
        if (body.redirect) {
          window.location.href = body.redirect;
          return response;
        }
      } catch {
        // Ignore parse errors
      }

      // Fallback: redirect to login
      window.location.href = '/login';
      return response;
    }
  }

  return response;
}

// Convenience methods
export const api = {
  get: (url: string, options?: ApiOptions) =>
    apiFetch(url, { method: 'GET', ...options }),

  post: (url: string, body?: unknown, options?: ApiOptions) =>
    apiFetch(url, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    }),

  put: (url: string, body?: unknown, options?: ApiOptions) =>
    apiFetch(url, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    }),

  delete: (url: string, options?: ApiOptions) =>
    apiFetch(url, { method: 'DELETE', ...options }),
};
