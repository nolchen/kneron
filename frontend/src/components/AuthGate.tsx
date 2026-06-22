"use client";

import { useState } from "react";
import { Bot, LogIn, RefreshCw, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Role } from "@/lib/types";

/**
 * Login wall. When the backend enforces auth (AUTH_ENFORCED=true), nobody sees
 * the app until they sign in. In open/demo mode (enforced=false) this is a
 * passthrough, so the public demo is unchanged.
 */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, enforced, configured, loading, refresh } = useAuth();
  const [busy, setBusy] = useState(false);

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-page">
        <RefreshCw className="h-6 w-6 animate-spin text-brand-purple" />
      </div>
    );
  }

  // Open/demo mode, or already signed in → show the app.
  if (!enforced || user) return <>{children}</>;

  const devLogin = async (role: Role) => {
    setBusy(true);
    try { await api.devLogin(`${role}@dev.local`, role, `${role} (dev)`); await refresh(); }
    finally { setBusy(false); }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-page px-6">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-1.5">
          <Bot className="h-7 w-7 text-brand-purple" />
          <span className="text-2xl font-bold text-text-1">PM Agent</span>
        </div>
        <p className="text-center text-sm text-text-2 mb-8">AI Program Manager — sign in to continue</p>

        <div className="bg-surface border border-ui-border rounded-2xl p-6 shadow-sm">
          {configured ? (
            <button
              onClick={() => api.login()}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-purple px-4 py-3 text-sm font-semibold text-white hover:opacity-90"
            >
              <LogIn className="h-4 w-4" /> Sign in with Microsoft
            </button>
          ) : (
            <>
              <p className="flex items-center justify-center gap-1.5 text-[10px] uppercase tracking-wide text-text-3 mb-3">
                <ShieldCheck className="h-3 w-3" /> Dev sign-in (Microsoft not configured)
              </p>
              <div className="grid grid-cols-3 gap-2">
                {(["L3", "L2", "L1"] as Role[]).map((r) => (
                  <button
                    key={r}
                    onClick={() => devLogin(r)}
                    disabled={busy}
                    className="capitalize rounded-lg border border-ui-border bg-surface py-2 text-xs font-medium text-text-2 hover:bg-brand-light hover:text-text-1 disabled:opacity-50"
                  >
                    {r}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <p className="text-center text-[11px] text-text-3 mt-4">You&apos;ll only see what your role allows.</p>
      </div>
    </div>
  );
}
