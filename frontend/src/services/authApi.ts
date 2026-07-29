import { api } from './api';

export interface LoginResponse {
  status: string;
  token: string;
  user: {
    id: number;
    username: string;
  };
  expires_at: string;
}

export interface SignupResponse {
  status: string;
  message: string;
  user_id: number;
}

export interface UserResponse {
  id: number;
  username: string;
  created_at: string;
}

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await api.post(
      '/api/auth/login',
      { username, password },
      {
        skipAuth: true,
        skip401Redirect: true, // Don't redirect on invalid credentials
      }
    );

    if (!response.ok) {
      const error = await response.json();
      // FastAPI 422 returns detail as an array of field errors
      const message = Array.isArray(error.detail)
        ? error.detail.map((e: any) => e.msg).join(', ')
        : error.detail || 'Login failed';
      throw new Error(message);
    }

    return response.json();
  },

  async signup(username: string, password: string): Promise<SignupResponse> {
    const response = await api.post(
      '/api/auth/signup',
      { username, password },
      {
        skipAuth: true,
        skip401Redirect: true,
      }
    );

    if (!response.ok) {
      const error = await response.json();
      const message = Array.isArray(error.detail)
        ? error.detail.map((e: any) => e.msg).join(', ')
        : error.detail || 'Signup failed';
      throw new Error(message);
    }

    return response.json();
  },

  async validateToken(): Promise<UserResponse | null> {
    const response = await api.get('/api/auth/me');

    if (response.ok) {
      return response.json();
    }

    return null;
  },
};
