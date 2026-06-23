"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth, canManage } from "@/lib/auth";
import { EmailAccount } from "@/lib/types";
import { Mail, RefreshCw, Plus, Trash2, CheckCircle2, AlertTriangle, Inbox } from "lucide-react";

function EmailInner() {
  const params = useSearchParams();
  const { user, enforced } = useAuth();
  const manage = canManage(user, enforced);   // L2+ run the shared inbox pool
  const [configured, setConfigured] = useState(false);
  const [accounts, setAccounts]     = useState<EmailAccount[]>([]);
  const [loading, setLoading]       = useState(true);
  const [syncing, setSyncing]       = useState(false);
  const [banner, setBanner]         = useState<{ type: "ok" | "err"; msg: string } | null>(null);

  const reload = () =>
    api.emailStatus()
      .then((r) => { setConfigured(r.configured); setAccounts(r.accounts); })
      .catch(() => { /* not signed in / no access — leave defaults, don't crash */ });

  useEffect(() => {
    // Show result of an OAuth redirect (?connected=... or ?error=...)
    const connected = params.get("connected");
    const error     = params.get("error");
    if (connected) setBanner({ type: "ok",  msg: `Connected ${connected}` });
    if (error)     setBanner({ type: "err", msg: `Connection failed: ${error}` });
    reload().finally(() => setLoading(false));
  }, [params]);

  const handleConnect = async () => {
    try {
      const { auth_url } = await api.emailConnect();
      window.location.href = auth_url; // off to Microsoft sign-in
    } catch (e: unknown) {
      setBanner({ type: "err", msg: e instanceof Error ? e.message : "Could not start sign-in" });
    }
  };

  const handleSync = async () => {
    setSyncing(true); setBanner(null);
    try {
      const r = await api.emailSync();
      setBanner({ type: "ok", msg: `Synced ${r.synced_emails} emails from ${r.accounts} inbox(es). The AI can now reference them.` });
      await reload();
    } catch (e: unknown) {
      setBanner({ type: "err", msg: e instanceof Error ? e.message : "Sync failed" });
    } finally { setSyncing(false); }
  };

  const handleDisconnect = async (email: string) => {
    await api.emailDisconnect(email);
    await reload();
  };

  if (loading) return (
    <div className="flex h-full items-center justify-center">
      <RefreshCw className="h-6 w-6 animate-spin text-brand-purple" />
    </div>
  );

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-text-1 mb-1">Email</h1>
      <p className="text-sm text-text-2 mb-6">
        Connect your inbox so the AI can read your emails and pull out tasks, updates, and context.
      </p>

      {banner && (
        <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 mb-6 ${
          banner.type === "ok" ? "bg-brand-green/10 border-brand-green/20 text-brand-green"
                               : "bg-red-50 border-red-200 text-red-600"}`}>
          {banner.type === "ok" ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
          <p className="text-sm font-medium">{banner.msg}</p>
        </div>
      )}

      {!configured ? (
        <div className="rounded-xl bg-surface border border-ui-border p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-text-1 font-semibold"><AlertTriangle className="h-4 w-4 text-orange-500" /> Email not configured yet</div>
          <p className="text-sm text-text-2 leading-relaxed">
            An admin needs to set the Microsoft app credentials (<code className="text-brand-purple">MS_CLIENT_ID</code> / <code className="text-brand-purple">MS_CLIENT_SECRET</code>) in the backend <code>.env</code>.
            See the setup steps in the project README. Once configured, each person can connect their own inbox here.
          </p>
        </div>
      ) : (
        <>
          {manage && (
            <div className="flex gap-2 mb-6">
              <button onClick={handleConnect}
                className="flex items-center gap-2 rounded-lg bg-brand-purple px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
                <Plus className="h-4 w-4" /> Connect an inbox
              </button>
              {accounts.length > 0 && (
                <button onClick={handleSync} disabled={syncing}
                  className="flex items-center gap-2 rounded-lg border border-ui-border bg-surface px-4 py-2 text-sm font-medium text-text-1 hover:bg-subtle disabled:opacity-50">
                  {syncing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Inbox className="h-4 w-4" />}
                  Sync emails now
                </button>
              )}
            </div>
          )}

          <h2 className="text-sm font-semibold text-text-1 mb-3">Connected inboxes ({accounts.length})</h2>
          <div className="flex flex-col gap-2">
            {accounts.map((a) => (
              <div key={a.email} className="group flex items-center gap-3 rounded-xl bg-surface border border-ui-border p-4 shadow-sm">
                <div className="h-9 w-9 rounded-full bg-brand-purple/15 flex items-center justify-center shrink-0">
                  <Mail className="h-4 w-4 text-brand-purple" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-1 truncate">{a.name || a.email}</p>
                  <p className="text-xs text-text-3 truncate">
                    {a.email}{a.last_synced ? ` · last synced ${new Date(a.last_synced).toLocaleDateString()}` : " · not synced yet"}
                  </p>
                </div>
                {manage && (
                  <button onClick={() => handleDisconnect(a.email)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-red-50">
                    <Trash2 className="h-3.5 w-3.5 text-red-400" />
                  </button>
                )}
              </div>
            ))}
            {accounts.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 gap-2 text-text-3">
                <Inbox className="h-8 w-8" />
                <p className="text-sm">{manage ? "No inboxes connected. Click “Connect an inbox” to start." : "Your inbox isn’t connected yet — sign in with Microsoft to connect it."}</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function EmailPage() {
  return (
    <Suspense fallback={<div className="flex h-full items-center justify-center"><RefreshCw className="h-6 w-6 animate-spin text-brand-purple" /></div>}>
      <EmailInner />
    </Suspense>
  );
}
