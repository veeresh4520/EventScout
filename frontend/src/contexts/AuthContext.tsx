"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { User, AuthResponse } from "@/types/user";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "eventscout_token";

// ------------------------------------------------------------------
// Context shape
// ------------------------------------------------------------------

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  signup: (username: string, email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  /** Refresh the user profile from the server or local storage. */
  refreshUser: () => Promise<void>;
  /** Update user state and sync to local storage. */
  updateUser: (updated: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function createDefaultUser(identifier: string, isEmail: boolean): User {
  const username = isEmail ? identifier.split("@")[0] : identifier;
  const email = isEmail ? identifier : `${identifier}@example.com`;
  return {
    id: "usr_" + Math.random().toString(36).substring(2, 9),
    username,
    email,
    interests: ["AI/ML", "Web3", "Cloud & DevOps"],
    skills: ["Python", "React", "TypeScript"],
    preferred_event_types: ["hackathon", "workshop"],
    preferred_modes: ["online", "in-person"],
    saved_event_ids: [],
    notification_preferences: {
      dashboard_enabled: true,
      browser_enabled: true,
      email_enabled: true,
    },
    created_at: new Date().toISOString(),
  };
}

// ------------------------------------------------------------------
// Provider
// ------------------------------------------------------------------

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: restore token & user from localStorage and fetch user profile if available
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedUserStr = localStorage.getItem("eventscout_user");
    let initialUser: User | null = null;

    if (storedUserStr) {
      try {
        initialUser = JSON.parse(storedUserStr);
        setUser(initialUser);
      } catch {
        // ignore parse error
      }
    }

    if (storedToken) {
      setToken(storedToken);
      if (storedToken.startsWith("demo-token-")) {
        setIsLoading(false);
        return;
      }

      fetchMe(storedToken)
        .then((fetchedUser) => {
          setUser(fetchedUser);
          localStorage.setItem("eventscout_user", JSON.stringify(fetchedUser));
        })
        .catch(() => {
          // If offline / network error but we have a stored session, preserve it!
          if (!initialUser) {
            localStorage.removeItem(TOKEN_KEY);
            setToken(null);
          }
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchMe = async (jwt: string): Promise<User> => {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (!res.ok) throw new Error("Unauthorized");
    return res.json();
  };

  const login = useCallback(async (identifier: string, password: string) => {
    const isEmail = identifier.includes("@");
    const cleanId = identifier.trim();
    const payload = isEmail
      ? { email: cleanId, password }
      : { username: cleanId, password };

    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Invalid email/username or password");
      }

      const data: AuthResponse = await res.json();
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem("eventscout_user", JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
    } catch (err: any) {
      const isNetworkError =
        !err.message ||
        err.message === "Failed to fetch" ||
        err.message.includes("NetworkError") ||
        err.message.includes("Load failed") ||
        err.name === "TypeError";

      if (!isNetworkError) {
        throw err;
      }

      // Seamless fallback for production demo when backend is offline
      const storedUserStr = localStorage.getItem("eventscout_user");
      let fallbackUser: User;
      if (storedUserStr) {
        try {
          fallbackUser = JSON.parse(storedUserStr);
          if (isEmail) fallbackUser.email = cleanId;
          else fallbackUser.username = cleanId;
        } catch {
          fallbackUser = createDefaultUser(cleanId, isEmail);
        }
      } else {
        fallbackUser = createDefaultUser(cleanId, isEmail);
      }

      const demoToken = "demo-token-" + Date.now();
      localStorage.setItem(TOKEN_KEY, demoToken);
      localStorage.setItem("eventscout_user", JSON.stringify(fallbackUser));
      setToken(demoToken);
      setUser(fallbackUser);
    }
  }, []);

  const signup = useCallback(
    async (username: string, email: string, password: string) => {
      const cleanUsername = username.trim();
      const cleanEmail = email.trim();

      try {
        const res = await fetch(`${API_URL}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: cleanUsername,
            email: cleanEmail,
            password,
          }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "Signup failed");
        }

        const data: AuthResponse = await res.json();
        localStorage.setItem(TOKEN_KEY, data.access_token);
        localStorage.setItem("eventscout_user", JSON.stringify(data.user));
        setToken(data.access_token);
        setUser(data.user);
      } catch (err: any) {
        const isNetworkError =
          !err.message ||
          err.message === "Failed to fetch" ||
          err.message.includes("NetworkError") ||
          err.message.includes("Load failed") ||
          err.name === "TypeError";

        if (!isNetworkError) {
          throw err;
        }

        // Seamless fallback for production demo when backend is offline
        const fallbackUser: User = {
          id: "usr_" + Math.random().toString(36).substring(2, 9),
          username: cleanUsername,
          email: cleanEmail,
          interests: ["AI/ML", "Web3", "Cloud & DevOps"],
          skills: ["Python", "React", "TypeScript"],
          preferred_event_types: ["hackathon", "workshop"],
          preferred_modes: ["online", "in-person"],
          saved_event_ids: [],
          notification_preferences: {
            dashboard_enabled: true,
            browser_enabled: true,
            email_enabled: true,
          },
          created_at: new Date().toISOString(),
        };

        const demoToken = "demo-token-" + Date.now();
        localStorage.setItem(TOKEN_KEY, demoToken);
        localStorage.setItem("eventscout_user", JSON.stringify(fallbackUser));
        setToken(demoToken);
        setUser(fallbackUser);
      }
    },
    []
  );

  const register = useCallback(
    async (email: string, password: string) => {
      return signup(email.split("@")[0], email, password);
    },
    [signup]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("eventscout_user");
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    if (token.startsWith("demo-token-")) {
      const storedUserStr = localStorage.getItem("eventscout_user");
      if (storedUserStr) {
        try {
          setUser(JSON.parse(storedUserStr));
        } catch {}
      }
      return;
    }

    try {
      const updated = await fetchMe(token);
      setUser(updated);
      localStorage.setItem("eventscout_user", JSON.stringify(updated));
    } catch {
      const storedUserStr = localStorage.getItem("eventscout_user");
      if (storedUserStr) {
        try {
          setUser(JSON.parse(storedUserStr));
          return;
        } catch {}
      }
      logout();
    }
  }, [token, logout]);

  const updateUser = useCallback((updated: Partial<User>) => {
    setUser((prev) => {
      if (!prev) return prev;
      const next = { ...prev, ...updated };
      localStorage.setItem("eventscout_user", JSON.stringify(next));
      return next;
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: !!user,
      isLoading,
      login,
      signup,
      register,
      logout,
      refreshUser,
      updateUser,
    }),
    [user, token, isLoading, login, signup, register, logout, refreshUser, updateUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ------------------------------------------------------------------
// Hook
// ------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
