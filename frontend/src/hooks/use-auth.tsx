import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Types
interface User {
  id: number;
  email: string;
  display_name: string;
  avatar_url: string;
  role: string;
  level: string;
  credit_score: number;
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
  loginWithTokens: (tokens: AuthTokens) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
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

  // Check auth on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredToken();
      if (token) {
        try {
          const response = await api.get('/auth/me');
          setUser(response.data);
        } catch {
          // Token invalid, try refresh
          const refreshed = await refreshToken();
          if (!refreshed) {
            clearStoredTokens();
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

    // Fetch user info
    const userResponse = await api.get('/auth/me');
    setUser(userResponse.data);
  };

  const register = async (email: string, password: string, displayName?: string) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      display_name: displayName,
    });
    const tokens: AuthTokens = response.data;
    setStoredTokens(tokens);

    // Fetch user info
    const userResponse = await api.get('/auth/me');
    setUser(userResponse.data);
  };

  const loginWithTokens = async (tokens: AuthTokens) => {
    setStoredTokens(tokens);
    const userResponse = await api.get('/auth/me');
    setUser(userResponse.data);
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
        loginWithTokens,
        register,
        logout,
        refreshToken,
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
