"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import { api, ApiError, resetTokenExpiryWarning } from "./api";
import type { User } from "./types";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (username: string, password: string, email: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const token = localStorage.getItem("jarvis_token");
    const savedUser = localStorage.getItem("jarvis_user");
    if (token && savedUser) {
      try {
        const parsed = JSON.parse(savedUser);
        setUser(parsed);
        // Validate token with server in background
        api.get<{ user: User }>("/api/auth/me", { signal: controller.signal }).then((res) => {
          if (cancelled) return;
          if (res?.user) {
            setUser(res.user);
            localStorage.setItem("jarvis_user", JSON.stringify(res.user));
          }
        }).catch((err) => {
          if (cancelled) return;
          // Only clear on 401 (expired/invalid token), not on network errors
          if (err instanceof ApiError && err.status === 401) {
            localStorage.removeItem("jarvis_token");
            localStorage.removeItem("jarvis_user");
            setUser(null);
          }
        });
      } catch {
        localStorage.removeItem("jarvis_token");
        localStorage.removeItem("jarvis_user");
      }
    }
    setIsLoading(false);
    return () => { cancelled = true; controller.abort(); };
  }, []);

  const login = useCallback(async (username: string, password: string, rememberMe?: boolean) => {
    const res = await api.post<AuthResponse>("/api/auth/login", { username, password, remember_me: !!rememberMe });
    localStorage.setItem("jarvis_token", res.access_token);
    localStorage.setItem("jarvis_user", JSON.stringify(res.user));
    resetTokenExpiryWarning();
    setUser(res.user);
  }, []);

  const register = useCallback(
    async (username: string, password: string, email: string) => {
      const res = await api.post<AuthResponse>("/api/auth/register", {
        username,
        password,
        email,
      });
      localStorage.setItem("jarvis_token", res.access_token);
      localStorage.setItem("jarvis_user", JSON.stringify(res.user));
      resetTokenExpiryWarning();
      setUser(res.user);
    },
    [],
  );

  const logout = useCallback(async () => {
    // Blacklist the token server-side, then clear local state
    try {
      await api.post("/api/auth/logout", {});
    } catch {
      // Network failure shouldn't block local logout
    }
    localStorage.removeItem("jarvis_token");
    localStorage.removeItem("jarvis_user");
    api.invalidateAll();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextType>(() => ({
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
  }), [user, isLoading, login, register, logout]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
