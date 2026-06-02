"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Assignment, TeamMember } from "@/lib/types";
import { formatName, initials } from "@/lib/utils";
import {
  Plus, Trash2, Pencil, X, RefreshCw,
  Calendar, Zap, CheckCircle2, Clock, Circle, UserPlus, UserMinus, Check,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const PRIORITY_CFG = {
  high:   { label: "High",   cls: "bg-red-100 text-red-600 border-red-200" },
  medium: { label: "Medium", cls: "bg-brand-purple/15 text-brand-purple border-brand-purple/20" },
  low:    { label: "Low",    cls: "bg-brand-green/15 text-brand-green border-brand-green/20" },
} as const;

function daysLeft(dateStr: string) {
  const d = Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000);
  if (d < 0)   return { text: `${Math.abs(d)}d overdue`, cls: "text-red-500 font-semibold" };
  if (d === 0) return { text: "Due today",               cls: "text-brand-purple font-semibold" };
  if (d <= 3)  return { text: `${d}d left`,              cls: "text-brand-purple" };
  return              { text: `${d}d left`,               cls: "text-text-2" };
}

const COLORS = ["bg-brand-purple","bg-brand-dark","bg-brand-green","bg-[#6B7FD4]","bg-[#9B7FD4]","bg-[#5B8FA8]"];

function Avatar({ login, size = "sm" }: { login: string; size?: "sm" | "md" }) {
  const c = COLORS[login.charCodeAt(0) % COLORS.length];
  const d = size === "md" ? "h-10 w-10 text-sm" : "h-6 w-6 text-[10px]";
  return <div className={`${d} ${c} rounded-full flex items-center justify-center font-bold text-white shrink-0`}>{initials(login)}</div>;
}

function AvatarStack({ logins }: { logins: string[] }) {
  return (
    <div className="flex -space-x-1">
      {logins.slice(0, 4).map((l) => (
        <div key={l} title={formatName(l)} className="ring-2 ring-white rounded-full">
          <Avatar login={l} />
        </div>
      ))}
      {logins.length > 4 && (
        <div className="h-6 w-6 rounded-full bg-brand-light ring-2 ring-white flex items-center justify-center text-[9px] font-bold text-text-2">
          +{logins.length - 4}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Multi-worker picker dropdown
// ---------------------------------------------------------------------------
function WorkerPicker({
  team, selected, onDone, onClose,
}: { team: TeamMember[]; selected: string[]; onDone: (logins: string[]) => void; onClose: () => void }) {
  const [picked, setPicked] = useState<string[]>(selected);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [onClose]);

  const toggle = (login: string) =>
    setPicked((prev) => prev.includes(login) ? prev.filter((l) => l !== login) : [...prev, login]);

  return (
    <div ref={ref} className="absolute z-50 top-full left-0 mt-1 w-64 bg-surface border border-ui-border rounded-xl shadow-xl overflow-hidden">
      <div className="max-h-52 overflow-y-auto divide-y divide-brand-light">
        {team.map((m) => {
          const checked = picked.includes(m.login);
          return (
            <button key={m.login} onClick={() => toggle(m.login)}
              className="flex items-center gap-2 w-full px-3 py-2 hover:bg-brand-light text-left transition-colors">
              <div className={`h-4 w-4 rounded border flex items-center justify-center shrink-0 ${checked ? "bg-brand-purple border-brand-purple" : "border-brand-dark/30"}`}>
                {checked && <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />}
              </div>
              <Avatar login={m.login} />
              <div>
                <p className="text-xs font-medium text-text-1">{formatName(m.login)}</p>
                {m.role && <p className="text-[10px] text-text-2">{m.role}</p>}
              </div>
            </button>
          );
        })}
      </div>
      <div className="flex gap-2 p-2 border-t border-ui-border">
        <button onClick={onClose} className="flex-1 text-xs py-1.5 rounded-lg border border-ui-border text-text-2 hover:bg-brand-light">Cancel</button>
        <button onClick={() => { onDone(picked); onClose(); }}
          className="flex-1 text-xs py-1.5 rounded-lg bg-brand-purple text-white font-semibold hover:opacity-90">
          Assign ({picked.length})
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Unassigned card
// ---------------------------------------------------------------------------
function UnassignedCard({ a, team, onAssign, onEdit, onDelete, deleting }: {
  a: Assignment; team: TeamMember[];
  onAssign: (l: string[]) => void; onEdit: () => void; onDelete: () => void; deleting: boolean;
}) {
  const [picker, setPicker] = useState(false);
  const pc = PRIORITY_CFG[a.priority] ?? PRIORITY_CFG.medium;
  const dl = a.due_date ? daysLeft(a.due_date) : null;

  return (
    <div className="group relative bg-surface border border-ui-border rounded-xl p-4 shadow-sm hover:border-brand-purple/30 transition-all">
      <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={onEdit} className="p-1 rounded hover:bg-brand-light"><Pencil className="h-3 w-3 text-text-2" /></button>
        <button onClick={onDelete} disabled={deleting} className="p-1 rounded hover:bg-red-50">
          {deleting ? <RefreshCw className="h-3 w-3 animate-spin text-red-400" /> : <Trash2 className="h-3 w-3 text-red-400" />}
        </button>
      </div>
      <p className="text-sm font-semibold text-text-1 pr-14 mb-2 leading-snug">{a.title}</p>
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-xs border rounded-full px-2 py-0.5 ${pc.cls}`}>{pc.label}</span>
        {dl && <span className={`text-xs flex items-center gap-0.5 ${dl.cls}`}><Calendar className="h-3 w-3" />{dl.text}</span>}
      </div>
      {a.notes && <p className="text-xs text-text-3 mb-3 truncate">{a.notes}</p>}
      <div className="relative">
        <button onClick={() => setPicker((p) => !p)}
          className="flex items-center gap-1.5 text-xs font-semibold text-brand-purple border border-brand-purple/30 rounded-lg px-3 py-1.5 hover:bg-brand-purple/5 w-full justify-center">
          <UserPlus className="h-3.5 w-3.5" /> Assign People
        </button>
        {picker && <WorkerPicker team={team} selected={[]} onDone={onAssign} onClose={() => setPicker(false)} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Assigned card
// ---------------------------------------------------------------------------
function AssignedCard({ a, team, onUpdateAssignees, onEdit, onDelete, deleting }: {
  a: Assignment; team: TeamMember[];
  onUpdateAssignees: (l: string[]) => void; onEdit: () => void; onDelete: () => void; deleting: boolean;
}) {
  const [picker, setPicker] = useState(false);
  const pc = PRIORITY_CFG[a.priority] ?? PRIORITY_CFG.medium;
  const dl = a.due_date ? daysLeft(a.due_date) : null;

  return (
    <div className="group relative bg-surface border border-brand-purple/20 rounded-xl p-4 shadow-sm hover:border-brand-purple/50 transition-all">
      <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={onEdit} className="p-1 rounded hover:bg-brand-light"><Pencil className="h-3 w-3 text-text-2" /></button>
        <button onClick={onDelete} disabled={deleting} className="p-1 rounded hover:bg-red-50">
          {deleting ? <RefreshCw className="h-3 w-3 animate-spin text-red-400" /> : <Trash2 className="h-3 w-3 text-red-400" />}
        </button>
      </div>
      <p className="text-sm font-semibold text-text-1 pr-14 mb-2 leading-snug">{a.title}</p>
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-xs border rounded-full px-2 py-0.5 ${pc.cls}`}>{pc.label}</span>
        {dl && <span className={`text-xs flex items-center gap-0.5 ${dl.cls}`}><Calendar className="h-3 w-3" />{dl.text}</span>}
      </div>

      {/* Assigned people */}
      <div className="relative flex items-center justify-between bg-brand-purple/5 rounded-lg px-3 py-2">
        <AvatarStack logins={a.assignees} />
        <div className="flex items-center gap-1 ml-2">
          <button onClick={() => setPicker((p) => !p)} className="p-1 rounded hover:bg-brand-purple/10 text-brand-purple/60 hover:text-brand-purple" title="Edit assignees">
            <UserPlus className="h-3.5 w-3.5" />
          </button>
          <button onClick={() => onUpdateAssignees([])} className="p-1 rounded hover:bg-red-50 text-brand-purple/40 hover:text-red-400" title="Remove all">
            <UserMinus className="h-3.5 w-3.5" />
          </button>
        </div>
        {picker && <WorkerPicker team={team} selected={a.assignees} onDone={onUpdateAssignees} onClose={() => setPicker(false)} />}
      </div>
      {a.assignees.length > 0 && (
        <p className="text-xs text-text-2 mt-1.5 truncate">{a.assignees.map(formatName).join(", ")}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Worker availability card
// ---------------------------------------------------------------------------
function WorkerCard({ member, pct }: { member: TeamMember; pct: number }) {
  return (
    <div className="bg-surface border border-ui-border rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        <Avatar login={member.login} size="md" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-text-1 truncate">{formatName(member.login)}</p>
          {member.role && <p className="text-xs text-text-2 truncate">{member.role}</p>}
        </div>
      </div>
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="flex items-center gap-1 text-text-2"><Zap className="h-3 w-3" /> Workload</span>
          <span className={`font-semibold ${pct < 50 ? "text-brand-green" : pct < 80 ? "text-brand-purple" : "text-red-500"}`}>{pct.toFixed(0)}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-brand-light">
          <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, backgroundColor: pct >= 80 ? "#e05555" : pct >= 50 ? "#8380B6" : "#57A773" }} />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Form
// ---------------------------------------------------------------------------
const BLANK = { title: "", assignees: [] as string[], due_date: "", priority: "medium" as const, status: "todo" as const, notes: "" };

function AssignmentForm({ initial, onSave, onCancel }: {
  initial?: Assignment;
  onSave: (a: Omit<Assignment, "id" | "created_at">) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState(initial
    ? { title: initial.title, assignees: initial.assignees, due_date: initial.due_date, priority: initial.priority, status: initial.status, notes: initial.notes }
    : { ...BLANK });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const set = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const submit = async () => {
    if (!form.title.trim()) { setErr("Title is required"); return; }
    if (!form.due_date)     { setErr("Due date is required"); return; }
    setSaving(true); setErr("");
    try { await onSave(form as Omit<Assignment, "id" | "created_at">); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : "Save failed"); setSaving(false); }
  };

  const inp = "w-full rounded-lg border border-ui-border px-3 py-2 text-sm text-text-1 focus:outline-none focus:ring-2 focus:ring-brand-purple bg-surface";

  return (
    <div className="flex flex-col gap-4 h-full">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wide text-text-2 mb-1">Title *</label>
        <input className={inp} placeholder="What needs to be done?" value={form.title} onChange={(e) => set("title", e.target.value)} autoFocus />
      </div>
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wide text-text-2 mb-1">Due Date *</label>
        <input type="date" className={inp} value={form.due_date} onChange={(e) => set("due_date", e.target.value)} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wide text-text-2 mb-1">Priority</label>
          <select className={inp} value={form.priority} onChange={(e) => set("priority", e.target.value)}>
            <option value="high">High (+5 workload)</option>
            <option value="medium">Medium (+3 workload)</option>
            <option value="low">Low (+1 workload)</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wide text-text-2 mb-1">Status</label>
          <select className={inp} value={form.status} onChange={(e) => set("status", e.target.value)}>
            <option value="todo">To Do</option>
            <option value="in-progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>
      </div>
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wide text-text-2 mb-1">Notes</label>
        <textarea className={`${inp} resize-none`} rows={4} placeholder="Context, links, deadlines, info…" value={form.notes} onChange={(e) => set("notes", e.target.value)} />
      </div>
      {err && <p className="text-xs text-red-500">{err}</p>}
      <div className="flex gap-2 pt-2">
        <button onClick={onCancel} className="flex-1 rounded-lg border border-ui-border py-2 text-sm font-medium text-text-2 hover:bg-brand-light">Cancel</button>
        <button onClick={submit} disabled={saving} className="flex-1 rounded-lg bg-brand-purple py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50">
          {saving ? "Saving…" : initial ? "Save Changes" : "Create"}
        </button>
      </div>
    </div>
  );
}

function ColHeader({ icon, label, count, border }: { icon: React.ReactNode; label: string; count: number; border: string }) {
  return (
    <div className={`flex items-center gap-2 mb-4 pb-3 border-b-2 ${border}`}>
      {icon}
      <span className="font-bold text-text-1 text-sm">{label}</span>
      <span className="ml-auto text-xs font-semibold text-text-2 bg-brand-light rounded-full px-2 py-0.5">{count}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [team, setTeam]               = useState<TeamMember[]>([]);
  const [panel, setPanel]             = useState<"new" | Assignment | null>(null);
  const [loading, setLoading]         = useState(true);
  const [deleting, setDeleting]       = useState<string | null>(null);

  const reload = async () => {
    const [a, t] = await Promise.all([api.getAssignments(), api.getTeam()]);
    setAssignments(a.assignments);
    setTeam(t.team_members);
  };

  useEffect(() => { reload().finally(() => setLoading(false)); }, []);

  const unassigned = assignments.filter((a) => (!a.assignees || a.assignees.length === 0) && a.status !== "done");
  const inProgress = assignments.filter((a) => a.assignees?.length > 0 && a.status !== "done");
  const done       = assignments.filter((a) => a.status === "done");

  const busyLogins = new Set(inProgress.flatMap((a) => a.assignees));
  const maxScore   = Math.max(...team.map((m) => m.workload_score), 1);
  const available  = team.filter((m) => !busyLogins.has(m.login)).sort((a, b) => a.workload_score - b.workload_score);

  const handleCreate = async (body: Omit<Assignment, "id" | "created_at">) => {
    const a = await api.createAssignment({ ...body, assignees: [], status: "todo" });
    setAssignments((prev) => [a, ...prev]);
    setPanel(null);
  };

  const handleUpdate = async (body: Omit<Assignment, "id" | "created_at">) => {
    const editing = panel as Assignment;
    const a = await api.updateAssignment(editing.id, body);
    setAssignments((prev) => prev.map((x) => (x.id === a.id ? a : x)));
    setPanel(null);
  };

  const handleAssign = async (id: string, assignees: string[]) => {
    const a = await api.assignWorkers(id, assignees);
    setAssignments((prev) => prev.map((x) => (x.id === a.id ? a : x)));
    await reload();
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await api.deleteAssignment(id);
      setAssignments((prev) => prev.filter((a) => a.id !== id));
      if ((panel as Assignment)?.id === id) setPanel(null);
      await reload();
    } finally { setDeleting(null); }
  };

  if (loading) return <div className="flex h-full items-center justify-center"><RefreshCw className="h-6 w-6 animate-spin text-brand-purple" /></div>;

  return (
    <div className="flex h-full">
      <div className="flex-1 p-8 overflow-y-auto min-w-0">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-text-1">Assignments</h1>
            <p className="text-sm text-text-2 mt-1">{unassigned.length} unassigned · {inProgress.length} in progress · {available.length} available</p>
          </div>
          <button onClick={() => setPanel("new")} className="flex items-center gap-2 rounded-lg bg-brand-purple px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
            <Plus className="h-4 w-4" /> New Assignment
          </button>
        </div>

        <div className="grid grid-cols-3 gap-5">
          {/* Col 1 */}
          <div className="flex flex-col gap-3">
            <ColHeader icon={<Circle className="h-4 w-4 text-text-2" />} label="Needs to Start" count={unassigned.length} border="border-brand-dark/20" />
            {unassigned.map((a) => (
              <UnassignedCard key={a.id} a={a} team={team}
                onAssign={(l) => handleAssign(a.id, l)}
                onEdit={() => setPanel(a)} onDelete={() => handleDelete(a.id)} deleting={deleting === a.id} />
            ))}
            <button onClick={() => setPanel("new")} className="flex items-center justify-center gap-1.5 rounded-xl border-2 border-dashed border-ui-border py-3 text-xs font-medium text-text-3 hover:border-brand-purple/30 hover:text-brand-purple transition-colors">
              <Plus className="h-3.5 w-3.5" /> Add assignment
            </button>
          </div>

          {/* Col 2 */}
          <div className="flex flex-col gap-3">
            <ColHeader icon={<Zap className="h-4 w-4 text-brand-green" />} label="Available" count={available.length} border="border-brand-green" />
            {available.map((m) => <WorkerCard key={m.login} member={m} pct={(m.workload_score / maxScore) * 100} />)}
            {available.length === 0 && <p className="text-xs text-text-3 text-center py-8">Everyone is busy 🔥</p>}
          </div>

          {/* Col 3 */}
          <div className="flex flex-col gap-3">
            <ColHeader icon={<Clock className="h-4 w-4 text-brand-purple" />} label="Being Worked On" count={inProgress.length} border="border-brand-purple" />
            {inProgress.map((a) => (
              <AssignedCard key={a.id} a={a} team={team}
                onUpdateAssignees={(l) => handleAssign(a.id, l)}
                onEdit={() => setPanel(a)} onDelete={() => handleDelete(a.id)} deleting={deleting === a.id} />
            ))}
            {inProgress.length === 0 && <p className="text-xs text-text-3 text-center py-8">Nothing in progress yet</p>}
          </div>
        </div>

        {done.length > 0 && (
          <details className="mt-8">
            <summary className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-text-2 uppercase tracking-wider select-none hover:text-text-2">
              <CheckCircle2 className="h-4 w-4 text-brand-green" /> Completed ({done.length})
            </summary>
            <div className="grid grid-cols-3 gap-3 mt-4">
              {done.map((a) => (
                <div key={a.id} className="bg-surface border border-ui-border rounded-xl p-4 opacity-50">
                  <p className="text-sm font-medium text-text-1 line-through">{a.title}</p>
                  {a.assignees?.length > 0 && <p className="text-xs text-text-2 mt-1">{a.assignees.map(formatName).join(", ")}</p>}
                </div>
              ))}
            </div>
          </details>
        )}
      </div>

      {panel && (
        <div className="shrink-0 border-l border-ui-border bg-surface p-6 overflow-y-auto flex flex-col" style={{ width: 360 }}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold text-text-1">{panel === "new" ? "New Assignment" : "Edit Assignment"}</h2>
            <button onClick={() => setPanel(null)}><X className="h-5 w-5 text-text-2 hover:text-text-1" /></button>
          </div>
          <AssignmentForm
            initial={panel === "new" ? undefined : panel as Assignment}
            onSave={panel === "new" ? handleCreate : handleUpdate}
            onCancel={() => setPanel(null)}
          />
        </div>
      )}
    </div>
  );
}
