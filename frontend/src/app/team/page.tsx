"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TeamMember, Assignment } from "@/lib/types";
import { formatName, initials } from "@/lib/utils";
import { RefreshCw, ClipboardList, Zap, Plus, Trash2 } from "lucide-react";

function WorkloadBadge({ score }: { score: number }) {
  if (score >= 10) return <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-600">Overloaded</span>;
  if (score >= 5)  return <span className="rounded-full bg-brand-purple/15 px-2 py-0.5 text-xs font-semibold text-brand-purple">Busy</span>;
  return <span className="rounded-full bg-brand-green/15 px-2 py-0.5 text-xs font-semibold text-brand-green">Available</span>;
}

const AVATAR_COLORS = ["bg-brand-purple","bg-brand-dark","bg-brand-green","bg-[#6B7FD4]","bg-[#9B7FD4]","bg-[#5B8FA8]","bg-[#7A8FA6]"];

function Avatar({ login }: { login: string }) {
  const color = AVATAR_COLORS[login.charCodeAt(0) % AVATAR_COLORS.length];
  return (
    <div className={`h-10 w-10 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0 ${color}`}>
      {initials(login)}
    </div>
  );
}

function AddMemberModal({ onAdd, onClose }: { onAdd: (m: TeamMember) => void; onClose: () => void }) {
  const [name, setName]   = useState("");
  const [role, setRole]   = useState("");
  const [repos, setRepos] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr]     = useState("");

  const submit = async () => {
    if (!name.trim()) { setErr("Name is required"); return; }
    setSaving(true); setErr("");
    try {
      const m = await api.addMember(name.trim(), role.trim(), repos.trim());
      onAdd(m); onClose();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-brand-dark/40 backdrop-blur-sm">
      <div className="bg-surface rounded-2xl shadow-xl w-full max-w-md p-6 mx-4">
        <h2 className="font-bold text-text-1 text-lg mb-5">Add Team Member</h2>
        <div className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-text-2 mb-1 block">Full Name *</label>
            <input autoFocus className="w-full rounded-lg border border-ui-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-purple" placeholder="e.g. Jordan Smith" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()} />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-text-2 mb-1 block">Title / Role</label>
            <input className="w-full rounded-lg border border-ui-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-purple" placeholder="e.g. Account Executive, CEO, Designer…" value={role} onChange={(e) => setRole(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-text-2 mb-1 block">Department / Projects</label>
            <input className="w-full rounded-lg border border-ui-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-purple" placeholder="e.g. Sales, Engineering, Marketing" value={repos} onChange={(e) => setRepos(e.target.value)} />
          </div>
        </div>
        {err && <p className="mt-3 text-xs text-red-500">{err}</p>}
        <div className="flex gap-2 mt-6">
          <button onClick={onClose} className="flex-1 rounded-lg border border-ui-border py-2 text-sm font-medium text-text-2 hover:bg-brand-light">Cancel</button>
          <button onClick={submit} disabled={saving} className="flex-1 rounded-lg bg-brand-purple py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50">
            {saving ? "Adding…" : "Add Member"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function TeamPage() {
  const [team, setTeam]             = useState<TeamMember[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading]       = useState(true);
  const [showAdd, setShowAdd]       = useState(false);
  const [removing, setRemoving]     = useState<string | null>(null);
  const [error, setError]           = useState("");

  useEffect(() => {
    Promise.all([api.getTeam(), api.getAssignments()])
      .then(([t, a]) => { setTeam(t.team_members); setAssignments(a.assignments); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // Active assignments per person
  const activeTasks = (login: string) =>
    assignments.filter((a) => a.assignees.includes(login) && a.status !== "done").length;

  const handleAdd = (m: TeamMember) => setTeam((prev) => [...prev, m]);

  const handleRemove = async (login: string) => {
    setRemoving(login);
    try { await api.removeMember(login); setTeam((prev) => prev.filter((m) => m.login !== login)); }
    catch (e: unknown) { alert(e instanceof Error ? e.message : "Failed"); }
    finally { setRemoving(null); }
  };

  if (loading) return <div className="flex h-full items-center justify-center"><RefreshCw className="h-6 w-6 animate-spin text-brand-purple" /></div>;
  if (error)   return <div className="p-8"><p className="text-sm text-red-500">{error}</p></div>;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {showAdd && <AddMemberModal onAdd={handleAdd} onClose={() => setShowAdd(false)} />}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-1">Team</h1>
          <p className="text-sm text-text-2 mt-1">{team.length} members</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 rounded-lg bg-brand-purple px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
          <Plus className="h-4 w-4" /> Add Member
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {team.map((member) => {
          const maxScore = Math.max(...team.map((m) => m.workload_score), 1);
          const pct      = Math.min((member.workload_score / maxScore) * 100, 100);
          const tasks    = activeTasks(member.login);

          return (
            <div key={member.login} className="group relative rounded-xl bg-surface border border-ui-border p-5 shadow-sm">
              <button
                onClick={() => handleRemove(member.login)}
                disabled={removing === member.login}
                className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-red-50"
              >
                {removing === member.login ? <RefreshCw className="h-3.5 w-3.5 animate-spin text-red-400" /> : <Trash2 className="h-3.5 w-3.5 text-red-400" />}
              </button>

              <div className="flex items-center gap-3 mb-4">
                <Avatar login={member.login} />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-text-1 truncate">{formatName(member.login)}</p>
                  {member.role && <p className="text-xs text-text-2 truncate">{member.role}</p>}
                  {member.email && <p className="text-xs text-text-3 truncate">{member.email}</p>}
                  <div className="mt-1"><WorkloadBadge score={member.workload_score} /></div>
                </div>
              </div>

              {/* Stats — business-neutral */}
              <div className="grid grid-cols-2 gap-2 text-center mb-4">
                <div className="rounded-lg bg-subtle p-2">
                  <ClipboardList className="h-3.5 w-3.5 mx-auto text-brand-purple mb-0.5" />
                  <p className="text-lg font-bold text-text-1">{tasks}</p>
                  <p className="text-xs text-text-2">Active Tasks</p>
                </div>
                <div className="rounded-lg bg-subtle p-2">
                  <Zap className="h-3.5 w-3.5 mx-auto text-brand-green mb-0.5" />
                  <p className="text-lg font-bold text-text-1">{pct.toFixed(0)}%</p>
                  <p className="text-xs text-text-2">Workload</p>
                </div>
              </div>

              {/* Workload bar */}
              <div className="h-2 rounded-full bg-brand-light">
                <div className="h-2 rounded-full transition-all" style={{
                  width: `${pct}%`,
                  backgroundColor: pct >= 80 ? "#e05555" : pct >= 50 ? "#8380B6" : "#57A773",
                }} />
              </div>

              {member.repos_active?.length > 0 && (
                <p className="text-xs text-text-3 mt-3 truncate">{member.repos_active.join(", ")}</p>
              )}
            </div>
          );
        })}
      </div>

      {team.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 gap-3 text-text-3">
          <p className="text-sm">No team members yet.</p>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-1.5 text-sm text-brand-purple hover:underline">
            <Plus className="h-4 w-4" /> Add your first member
          </button>
        </div>
      )}
    </div>
  );
}
