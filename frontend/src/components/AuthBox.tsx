"use client";

import { useState } from "react";
import { LogIn, LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Role } from "@/lib/types";

const ROLE_CLS: Record<Role, string> = {
  L3: "bg-brand-purple/20 text-brand-purple",
  L2: "bg-brand-green/20 text-brand-green",
  L1: "bg-white/10 text-white/60",
};

function initials(s: string) {
  const parts = s.replace(/@.*/, "").split(/[.\s_]+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || s[0]?.toUpperCase() || "?";
}

export default function AuthBox() {
  const { user, configured, loading, refresh } = useAuth();
  const [busy, setBusy] = useState(false);

  const signOut = async () => {
    setBusy(true);
    try { await api.logout(); await refresh(); } finally { setBusy(false); }
  };

  const devLogin = async (role: Role) => {
    setBusy(true);
    try { await api.devLogin(`${role}@dev.local`, role, `${role} (dev)`); await refresh(); }
    finally { setBusy(false); }
  };

  if (loading) {
    return <div className="px-4 py-3 border-t border-white/10"><div className="h-8 rounded-lg bg-white/5 animate-pulse" /></div>;
  }

  // Signed in
  if (user) {
    return (
      <div className="px-4 py-3 border-t border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-full bg-brand-purple flex items-center justify-center text-xs font-bold text-white shrink-0">
            {initials(user.name || user.email)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-white truncate">{user.name || user.email}</p>
            <span className={`inline-block mt-0.5 text-[10px] font-medium rounded-full px-1.5 py-0.5 capitalize ${ROLE_CLS[user.role]}`}>
              {user.role}
            </span>
          </div>
          <button onClick={signOut} disabled={busy} title="Sign out"
            className="p-1.5 rounded-lg text-white/40 hover:bg-white/10 hover:text-white transition-colors disabled:opacity-50">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    );
  }

  // Signed out — Microsoft SSO available
  if (configured) {
    return (
      <div className="px-4 py-3 border-t border-white/10">
        <button onClick={() => api.login()}
          className="flex items-center justify-center gap-2 w-full rounded-lg bg-white/10 px-3 py-2 text-sm font-medium text-white hover:bg-white/15 transition-colors">
          <LogIn className="h-4 w-4" /> Sign in with Microsoft
        </button>
      </div>
    );
  }

  // Signed out — SSO not configured: dev sign-in for local testing
  return (
    <div className="px-4 py-3 border-t border-white/10">
      <p className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-white/30 mb-2">
        <ShieldCheck className="h-3 w-3" /> Dev sign-in
      </p>
      <div className="grid grid-cols-3 gap-1.5">
        {(["L3", "L2", "L1"] as Role[]).map((r) => (
          <button key={r} onClick={() => devLogin(r)} disabled={busy}
            className="text-[11px] capitalize rounded-lg bg-white/10 py-1.5 text-white/70 hover:bg-white/15 hover:text-white transition-colors disabled:opacity-50">
            {r}
          </button>
        ))}
      </div>
    </div>
  );
}
