import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Types
interface User {
  id: number;
  username: string;
  email: string;
  display_name: string;
  avatar_url: string;
  role: string;
  level: string;
  credit_score: number;
  email_verified?: boolean;
}

interface AuthTokens {
  access: string;
  refresh: string;
  expires_in: number;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string, inviteCode?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  refreshUser: () => Promise<User | null>;
  requestPasswordReset: (email: string) => Promise<void>;
  resetPassword: (uid: string, token: string, newPassword: string) => Promise<void>;
  verifyEmail: (key: string) => Promise<void>;
  getSocialAuthorizationUrl: (provider: 'github' | 'google') => Promise<string>;
  completeSocialLogin: (code: string) => Promise<void>;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Storage helpers
const getStoredToken = (): string | null => localStorage.getItem('access_token');
const getStoredRefreshToken = (): string | null => localStorage.getItem('refresh_token');
const setStoredTokens = (tokens: AuthTokens) => {
  localStorage.setItem('access_token', tokens.access);
  localStorage.setItem('refresh_token', tokens.refresh);
};
const clearStoredTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

// Axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth header
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = async (): Promise<User | null> => {
    const response = await api.get('/auth/me');
    setUser(response.data);
    return response.data;
  };

  // Check auth on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredToken();
      if (token) {
        try {
          await refreshUser();
        } catch {
          // Token invalid, try refresh
          const refreshed = await refreshToken();
          if (!refreshed) {
            clearStoredTokens();
          } else {
            try {
              await refreshUser();
            } catch {
              clearStoredTokens();
              setUser(null);
            }
          }
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    const tokens: AuthTokens = response.data;
    setStoredTokens(tokens);
    await refreshUser();
  };

  const register = async (email: string, password: string, displayName?: string, inviteCode?: string) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      display_name: displayName,
      invite_code: inviteCode,
    });
    const tokens: AuthTokens = response.data;
    setStoredTokens(tokens);
    await refreshUser();
  };

  const logout = async () => {
    const refresh = getStoredRefreshToken();
    if (refresh) {
      try {
        await api.post('/auth/logout', { refresh });
      } catch {
        // Ignore error
      }
    }
    clearStoredTokens();
    setUser(null);
  };

  const refreshToken = async (): Promise<boolean> => {
    const refresh = getStoredRefreshToken();
    if (!refresh) return false;

    try {
      const response = await api.post('/auth/refresh', { refresh });
      const tokens: AuthTokens = response.data;
      setStoredTokens(tokens);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshToken,
        refreshUser,
        requestPasswordReset: async (email: string) => {
          await api.post('/auth/forgot-password', { email });
        },
        resetPassword: async (uid: string, token: string, newPassword: string) => {
          await api.post('/auth/reset-password', {
            uid,
            token,
            new_password: newPassword,
          });
        },
        verifyEmail: async (key: string) => {
          await api.post('/auth/verify-email', { key });
          if (getStoredToken()) {
            try {
              await refreshUser();
            } catch {
              // ignore refresh failure
            }
          }
        },
        getSocialAuthorizationUrl: async (provider: 'github' | 'google') => {
          const response = await api.get(`/auth/social/${provider}/authorize`);
          return response.data.authorization_url;
        },
        completeSocialLogin: async (code: string) => {
          const response = await api.post('/auth/social/exchange', { code });
          const tokens: AuthTokens = response.data;
          setStoredTokens(tokens);
          await refreshUser();
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Hook
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export { api };
export type { User, AuthTokens };
