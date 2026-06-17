"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";
import { User } from "./types";

interface AuthState {
  user: User | null;
  configured: boolean;   // is Microsoft SSO set up on the backend?
  enforced: boolean;     // does the backend require login + check roles?
  loading: boolean;
  refresh: () => Promise<void>;
}

const AuthCtx = createContext<AuthState>({
  user: null, configured: false, enforced: false, loading: true,
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [configured, setConfigured] = useState(false);
  const [enforced, setEnforced] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const r = await api.authMe();
      setUser(r.user);
      setConfigured(r.configured);
      setEnforced(r.enforced);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return (
    <AuthCtx.Provider value={{ user, configured, enforced, loading, refresh }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);

/**
 * Can the current viewer manage tasks (create / assign / edit / delete)?
 * When auth isn't enforced the app is open (demo mode) so everyone can — this
 * mirrors the backend, which treats unenforced requests as admin. When enforced,
 * only managers and admins can; interns get a read-only board.
 */
export function canManage(user: User | null, enforced: boolean): boolean {
  if (!enforced) return true;
  return !!user && (user.role === "admin" || user.role === "manager");
}
