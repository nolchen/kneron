"use client";

import { useState } from "react";
import { Plus, RefreshCw, X, Sparkles } from "lucide-react";
import { api } from "@/lib/api";

interface Props { repos: string[]; onSynced: () => void; }

export default function SetupBanner({ repos, onSynced }: Props) {
  const [repoInput, setRepoInput] = useState("");
  const [repoList, setRepoList]   = useState<string[]>(repos);
  const [syncing, setSyncing]     = useState(false);
  const [demoing, setDemoing]     = useState(false);
  const [error, setError]         = useState("");

  const addRepo = () => {
    const t = repoInput.trim();
    if (!t || repoList.includes(t)) return;
    setRepoList((p) => [...p, t]); setRepoInput("");
  };

  const handleSync = async () => {
    if (!repoList.length) return;
    setSyncing(true); setError("");
    try { await api.setRepos(repoList); await api.sync(); onSynced(); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Sync failed"); }
    finally { setSyncing(false); }
  };

  const handleDemo = async () => {
    setDemoing(true); setError("");
    try { await api.loadMock(); onSynced(); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setDemoing(false); }
  };

  const inp = "flex-1 rounded-lg border border-ui-border bg-surface px-3 py-2 text-sm text-text-1 focus:outline-none focus:ring-2 focus:ring-brand-purple";

  return (
    <div className="mb-6 rounded-xl border border-brand-purple/30 bg-surface p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-ui-border">
        <div>
          <p className="text-sm font-semibold text-text-1">Try a demo first</p>
          <p className="text-xs text-brand-purple mt-0.5">Load realistic mock data — no GitHub needed</p>
        </div>
        <button onClick={handleDemo} disabled={demoing}
          className="flex items-center gap-2 rounded-lg bg-brand-purple px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50">
          <Sparkles className={`h-4 w-4 ${demoing ? "animate-spin" : ""}`} />
          {demoing ? "Loading…" : "Load Demo Data"}
        </button>
      </div>

      <p className="text-sm font-semibold text-text-1 mb-3">
        Or connect GitHub repos (<code className="text-brand-purple">owner/repo</code>)
      </p>

      <div className="flex gap-2 mb-3">
        <input className={inp} placeholder="e.g. facebook/react" value={repoInput}
          onChange={(e) => setRepoInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addRepo()} />
        <button onClick={addRepo} className="flex items-center gap-1 rounded-lg bg-brand-dark px-3 py-2 text-sm text-white hover:opacity-90">
          <Plus className="h-4 w-4" /> Add
        </button>
      </div>

      {repoList.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {repoList.map((r) => (
            <span key={r} className="flex items-center gap-1 rounded-full bg-subtle px-3 py-1 text-xs font-medium text-text-1">
              {r}
              <button onClick={() => setRepoList((p) => p.filter((x) => x !== r))}>
                <X className="h-3 w-3 text-text-2 hover:text-red-500" />
              </button>
            </span>
          ))}
        </div>
      )}

      {error && <p className="text-xs text-red-500 mb-2">{error}</p>}

      <button onClick={handleSync} disabled={!repoList.length || syncing}
        className="flex items-center gap-2 rounded-lg bg-brand-purple px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50">
        <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
        {syncing ? "Syncing…" : "Sync GitHub Data"}
      </button>
    </div>
  );
}
