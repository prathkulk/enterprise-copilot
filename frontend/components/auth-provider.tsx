"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { fetchSession, logoutUser } from "@/lib/api";
import type { AuthSession } from "@/lib/types";

interface AuthContextValue {
  ready: boolean;
  session: AuthSession | null;
  saveAuth: (payload: AuthSession) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    let cancelled = false;

    void fetchSession()
      .then((nextSession) => {
        if (!cancelled) {
          setSession(nextSession);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSession(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setReady(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const value: AuthContextValue = {
    ready,
    session,
    saveAuth: (payload) => {
      setSession(payload);
    },
    logout: async () => {
      await logoutUser();
      setSession(null);
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
