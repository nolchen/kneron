"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ProposedEvent } from "@/lib/types";
import {
  Mail, RefreshCw, CalendarPlus, Check, Sparkles, LogIn, CheckCircle2, AlertCircle, Inbox,
} from "lucide-react";

function whenLabel(start: string) {
  const d = new Date(start);
  if (isNaN(d.getTime())) return start;
  return d.toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function InboxPage() {
  const [status, setStatus] = useState<{ connected: boolean; email: string; last_synced: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [proposals, setProposals] = useState<ProposedEvent[]>([]);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [scanned, setScanned] = useState<number | null>(null);
  const [results, setResults] = useState<{ title: string; ok: boolean; error?: string }[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.inboxStatus().then(setStatus).catch(() => setStatus({ connected: false, email: "", last_synced: "" })).finally(() => setLoading(false));
  }, []);

  const scan = async () => {
    setScanning(true); setError(""); setResults(null);
    try {
      const r = await api.scanInbox();
      setProposals(r.proposals);
      setScanned(r.scanned);
      setPicked(new Set(r.proposals.map((_, i) => i)));   // default: all selected
    } catch (e) { setError(e instanceof Error ? e.message : "Scan failed"); }
    finally { setScanning(false); }
  };

  const toggle = (i: number) =>
    setPicked((prev) => { const n = new Set(prev); n.has(i) ? n.delete(i) : n.add(i); return n; });

  const confirm = async () => {
    const events = proposals.filter((_, i) => picked.has(i));
    if (events.length === 0) return;
    setConfirming(true); setError("");
    try {
      const r = await api.confirmEvents(events);
      setResults(r.results);
      setProposals((prev) => prev.filter((_, i) => !picked.has(i)));   // clear added ones
      setPicked(new Set());
    } catch (e) { setError(e instanceof Error ? e.message : "Failed to add events"); }
    finally { setConfirming(false); }
  };

  if (loading) return <div className="flex h-full items-center justify-center"><RefreshCw className="h-6 w-6 animate-spin text-brand-purple" /></div>;

  // Not connected → prompt to sign in (which grants mail + calendar)
  if (!status?.connected) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 text-center px-8">
        <div className="h-14 w-14 rounded-2xl bg-brand-purple/15 flex items-center justify-center">
          <Mail className="h-7 w-7 text-brand-purple" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-text-1">Connect your inbox</h1>
          <p className="text-sm text-text-2 mt-1 max-w-md">Sign in with Microsoft to let the AI scan your email for tasks and deadlines, then add them to your calendar — with your approval.</p>
        </div>
        <button onClick={() => api.login()} className="flex items-center gap-2 rounded-lg bg-brand-purple px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">
          <LogIn className="h-4 w-4" /> Sign in with Microsoft
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <Inbox className="h-5 w-5 text-brand-purple" />
            <h1 className="text-2xl font-bold text-text-1">My Tasks from Email</h1>
          </div>
          <p className="text-sm text-text-2 mt-1">{status.email} · the AI reads recent mail and suggests calendar items. Nothing is added until you confirm.</p>
        </div>
        <button onClick={scan} disabled={scanning}
          className="flex items-center gap-2 rounded-lg bg-brand-purple px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 shrink-0">
          {scanning ? <><RefreshCw className="h-4 w-4 animate-spin" /> Scanning…</> : <><Sparkles className="h-4 w-4" /> Scan my inbox</>}
        </button>
      </div>

      {error && <p className="flex items-center gap-1.5 text-sm text-red-500 mb-4"><AlertCircle className="h-4 w-4" />{error}</p>}

      {results && (
        <div className="mb-6 rounded-xl border border-brand-green/30 bg-brand-green/5 p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-brand-green mb-2"><CheckCircle2 className="h-4 w-4" /> Added to your calendar</p>
          {results.map((r, i) => (
            <p key={i} className="text-xs text-text-2">{r.ok ? "✓" : "✗"} {r.title}{r.error ? ` — ${r.error}` : ""}</p>
          ))}
        </div>
      )}

      {scanned !== null && proposals.length === 0 && !results && (
        <p className="text-sm text-text-3 py-12 text-center">Scanned {scanned} emails — nothing calendar-worthy found. 🎉</p>
      )}

      {proposals.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-text-3">Found {proposals.length} in {scanned} emails · {picked.size} selected</p>
            <button onClick={confirm} disabled={confirming || picked.size === 0}
              className="flex items-center gap-2 rounded-lg border border-brand-green/40 bg-brand-green/10 px-3 py-1.5 text-xs font-semibold text-brand-green hover:bg-brand-green/20 disabled:opacity-40">
              {confirming ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CalendarPlus className="h-3.5 w-3.5" />}
              Add {picked.size} to my calendar
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {proposals.map((p, i) => {
              const on = picked.has(i);
              return (
                <button key={i} onClick={() => toggle(i)}
                  className={`flex items-start gap-3 text-left rounded-xl border p-4 transition-colors ${on ? "border-brand-purple/40 bg-brand-purple/5" : "border-ui-border bg-surface hover:border-brand-purple/20"}`}>
                  <div className={`mt-0.5 h-5 w-5 rounded border flex items-center justify-center shrink-0 ${on ? "bg-brand-purple border-brand-purple" : "border-text-3/40"}`}>
                    {on && <Check className="h-3 w-3 text-white" strokeWidth={3} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-text-1">{p.title}</p>
                    <p className="text-xs text-brand-purple mt-0.5">{whenLabel(p.start)}</p>
                    {p.source_subject && <p className="text-xs text-text-3 mt-1 truncate">from: {p.source_subject}</p>}
                  </div>
                  {typeof p.confidence === "number" && (
                    <span className="text-[10px] text-text-3 shrink-0">{Math.round(p.confidence * 100)}%</span>
                  )}
                </button>
              );
            })}
          </div>
        </>
      )}

      {scanned === null && !error && (
        <div className="flex flex-col items-center justify-center gap-2 text-text-3 py-20 text-center">
          <Sparkles className="h-8 w-8" />
          <p className="text-sm">Hit <b>Scan my inbox</b> and the AI will pull out tasks &amp; deadlines for you to review.</p>
        </div>
      )}
    </div>
  );
}
