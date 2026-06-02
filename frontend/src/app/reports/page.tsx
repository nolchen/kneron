"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Note } from "@/lib/types";
import { RefreshCw, FileText, Trash2, Plus, Bot, BookOpen, Download, FolderSync } from "lucide-react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TYPE_CFG = {
  report:  { label: "Report",  cls: "bg-brand-purple/15 text-brand-purple border-brand-purple/20" },
  summary: { label: "Summary", cls: "bg-brand-green/15 text-brand-green border-brand-green/20" },
  note:    { label: "Note",    cls: "bg-subtle text-text-2 border-ui-border" },
} as const;

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function ReportsPage() {
  const [notes, setNotes]         = useState<Note[]>([]);
  const [selected, setSelected]   = useState<Note | null>(null);
  const [loading, setLoading]     = useState(true);
  const [generating, setGenerating]   = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [syncing, setSyncing]         = useState(false);
  const [syncResult, setSyncResult] = useState<string>("");
  const [deleting, setDeleting]     = useState<string | null>(null);
  const [showForm, setShowForm]     = useState(false);
  const [form, setForm]             = useState({ title: "", content: "", note_type: "note" });

  const reload = () => api.getNotes().then((r) => setNotes(r.notes));

  useEffect(() => { reload().finally(() => setLoading(false)); }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setStreamContent("");
    setSelected(null);

    try {
      const res = await fetch(`${BASE}/api/notes/generate/stream`, { method: "POST" });
      if (!res.ok || !res.body) throw new Error("Stream failed");

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of decoder.decode(value, { stream: true }).split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.chunk) {
              full += payload.chunk;
              setStreamContent(full);
            }
            if (payload.done) {
              // Refresh note list and select the new one
              const updated = await api.getNotes();
              setNotes(updated.notes);
              setSelected(updated.notes[0] ?? null);
              setStreamContent("");
            }
          } catch { /* partial */ }
        }
      }
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed to generate report");
    } finally { setGenerating(false); }
  };

  const handleSave = async () => {
    if (!form.title.trim() || !form.content.trim()) return;
    const note = await api.saveNote(form.title, form.content, form.note_type);
    setNotes((prev) => [note, ...prev]);
    setSelected(note);
    setShowForm(false);
    setForm({ title: "", content: "", note_type: "note" });
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await api.deleteNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
      if (selected?.id === id) setSelected(null);
    } finally { setDeleting(null); }
  };

  const handleVaultSync = async () => {
    setSyncing(true); setSyncResult("");
    try {
      const res = await fetch(`${BASE}/api/vault/sync`, { method: "POST" });
      const data = await res.json();
      setSyncResult(`Synced ${data.indexed} new notes from vault (${data.skipped} already indexed)`);
      await reload();
    } catch { setSyncResult("Sync failed — is the backend running?"); }
    finally { setSyncing(false); }
  };

  const handleDownload = (note: Note) => {
    const blob = new Blob([`# ${note.title}\n\n${note.content}`], { type: "text/markdown" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `${note.title.replace(/[^a-z0-9]/gi, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="flex h-full items-center justify-center"><RefreshCw className="h-6 w-6 animate-spin text-brand-purple" /></div>;

  const inp = "w-full rounded-lg border border-ui-border bg-surface px-3 py-2 text-sm text-text-1 focus:outline-none focus:ring-2 focus:ring-brand-purple";

  return (
    <div className="flex h-full">
      {/* ── Left: note list ── */}
      <div className="w-72 shrink-0 border-r border-ui-border flex flex-col">
        <div className="p-4 border-b border-ui-border">
          <h1 className="text-lg font-bold text-text-1 mb-3">Reports & Notes</h1>
          <div className="flex flex-col gap-2">
            <button onClick={handleGenerate} disabled={generating}
              className="flex items-center gap-2 rounded-lg bg-brand-purple px-3 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50">
              {generating
                ? <><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Generating…</>
                : <><Bot className="h-3.5 w-3.5" /> Generate AI Report</>}
            </button>
            <button onClick={() => setShowForm(true)}
              className="flex items-center gap-2 rounded-lg border border-ui-border bg-surface px-3 py-2 text-xs font-medium text-text-2 hover:bg-subtle">
              <Plus className="h-3.5 w-3.5" /> Add Note Manually
            </button>
            <button onClick={handleVaultSync} disabled={syncing}
              className="flex items-center gap-2 rounded-lg border border-brand-green/40 bg-brand-green/10 px-3 py-2 text-xs font-medium text-brand-green hover:bg-brand-green/20 disabled:opacity-50">
              {syncing ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <FolderSync className="h-3.5 w-3.5" />}
              Sync Obsidian Vault
            </button>
            {syncResult && <p className="text-[10px] text-text-3 leading-snug">{syncResult}</p>}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-ui-border">
          {notes.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-text-3 p-6 text-center">
              <BookOpen className="h-8 w-8" />
              <p className="text-xs">No reports yet. Generate one or add a note.</p>
            </div>
          )}
          {notes.map((n) => {
            const tc = TYPE_CFG[n.type as keyof typeof TYPE_CFG] ?? TYPE_CFG.note;
            return (
              <button key={n.id} onClick={() => setSelected(n)}
                className={`w-full text-left px-4 py-3 hover:bg-subtle transition-colors ${selected?.id === n.id ? "bg-subtle" : ""}`}>
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-semibold text-text-1 leading-snug line-clamp-2">{n.title}</p>
                  <span className={`shrink-0 text-[10px] border rounded-full px-1.5 py-0.5 ${tc.cls}`}>{tc.label}</span>
                </div>
                <p className="text-[10px] text-text-3 mt-1">{formatDate(n.created_at)}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Right: note detail / form ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {streamContent ? (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="flex items-center gap-2 mb-4">
              <RefreshCw className="h-4 w-4 animate-spin text-brand-purple" />
              <span className="text-sm font-semibold text-text-1">Generating report…</span>
            </div>
            <div className="bg-surface border border-ui-border rounded-xl p-6">
              <p className="text-sm text-text-1 whitespace-pre-line leading-relaxed">
                {streamContent}
                <span className="inline-block w-0.5 h-3.5 bg-brand-purple ml-0.5 animate-pulse align-middle" />
              </p>
            </div>
          </div>
        ) : showForm ? (
          <div className="p-6 flex flex-col gap-4 max-w-2xl">
            <h2 className="font-bold text-text-1">Add Note</h2>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-text-2 mb-1 block">Title</label>
              <input className={inp} placeholder="Note title…" value={form.title} onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-text-2 mb-1 block">Type</label>
              <select className={inp} value={form.note_type} onChange={(e) => setForm((p) => ({ ...p, note_type: e.target.value }))}>
                <option value="note">Note</option>
                <option value="report">Report</option>
                <option value="summary">Summary</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-text-2 mb-1 block">Content</label>
              <textarea className={`${inp} resize-none`} rows={10}
                placeholder="Write your note here… The AI chatbot will be able to reference this."
                value={form.content} onChange={(e) => setForm((p) => ({ ...p, content: e.target.value }))} />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-lg border border-ui-border py-2 text-sm text-text-2 hover:bg-subtle">Cancel</button>
              <button onClick={handleSave} className="flex-1 rounded-lg bg-brand-purple py-2 text-sm font-semibold text-white hover:opacity-90">Save Note</button>
            </div>
          </div>
        ) : selected ? (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="flex items-start justify-between gap-4 mb-6">
              <div>
                <h2 className="text-lg font-bold text-text-1">{selected.title}</h2>
                <p className="text-xs text-text-3 mt-1">{formatDate(selected.created_at)}</p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => handleDownload(selected)}
                  className="flex items-center gap-1.5 rounded-lg border border-ui-border px-3 py-1.5 text-xs text-text-2 hover:bg-subtle">
                  <Download className="h-3.5 w-3.5" /> Download
                </button>
                <button onClick={() => handleDelete(selected.id)} disabled={deleting === selected.id}
                  className="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50">
                  {deleting === selected.id ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                  Delete
                </button>
              </div>
            </div>
            <div className="bg-surface border border-ui-border rounded-xl p-6">
              <p className="text-sm text-text-1 whitespace-pre-line leading-relaxed">{selected.content}</p>
            </div>
            <div className="flex flex-col gap-1.5 mt-4">
              <p className="text-xs text-text-3 flex items-center gap-1.5">
                <Bot className="h-3.5 w-3.5 text-brand-purple" />
                Searchable by the AI chatbot — referenced automatically when relevant.
              </p>
              <p className="text-xs text-text-3 flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-brand-green" />
                AI-generated reports are also saved to your Obsidian vault at <code className="text-[10px] bg-subtle px-1 rounded">PM-Vault/PM-Agent/</code>
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-text-3">
            <FileText className="h-10 w-10" />
            <p className="text-sm">Select a report or generate a new one</p>
          </div>
        )}
      </div>
    </div>
  );
}
