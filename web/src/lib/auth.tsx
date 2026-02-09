"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { api, ApiError } from "./api";
import type { User } from "./types";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, email: string) => Promise<void>;
  logout: () => void;
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
    const token = localStorage.getItem("jarvis_token");
    const savedUser = localStorage.getItem("jarvis_user");
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem("jarvis_token");
        localStorage.removeItem("jarvis_user");
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.post<AuthResponse>("/api/auth/login", { username, password });
    localStorage.setItem("jarvis_token", res.access_token);
    localStorage.setItem("jarvis_user", JSON.stringify(res.user));
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
      setUser(res.user);
    },
    [],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("jarvis_token");
    localStorage.removeItem("jarvis_user");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
