"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Assignment } from "@/lib/types";
import { formatName, initials } from "@/lib/utils";
import { RefreshCw, Calendar, Circle, Clock, CheckCircle2 } from "lucide-react";

const PRIORITY_RANK = { high: 3, medium: 2, low: 1 } as const;
const PRIORITY_CFG = {
  high:   { label: "High",   cls: "bg-red-100 text-red-600 border-red-200",                       bar: "bg-red-400" },
  medium: { label: "Medium", cls: "bg-brand-purple/15 text-brand-purple border-brand-purple/20",  bar: "bg-brand-purple" },
  low:    { label: "Low",    cls: "bg-brand-green/15 text-brand-green border-brand-green/20",      bar: "bg-brand-green" },
} as const;

const STATUS_CFG = {
  "todo":        { icon: Circle,       cls: "text-text-3",      label: "To do" },
  "in-progress": { icon: Clock,        cls: "text-brand-purple", label: "In progress" },
  "done":        { icon: CheckCircle2, cls: "text-brand-green",  label: "Done" },
} as const;

const COLORS = ["bg-brand-purple","bg-brand-dark","bg-brand-green","bg-[#6B7FD4]","bg-[#9B7FD4]","bg-[#5B8FA8]"];
function Avatar({ login }: { login: string }) {
  const c = COLORS[login.charCodeAt(0) % COLORS.length];
  return <div className={`h-6 w-6 ${c} rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0`} title={formatName(login)}>{initials(login)}</div>;
}

function dueInfo(dateStr: string) {
  if (!dateStr) return null;
  const d = Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000);
  if (d < 0)   return { text: `${Math.abs(d)}d overdue`, cls: "text-red-500 font-semibold" };
  if (d === 0) return { text: "Due today",               cls: "text-brand-purple font-semibold" };
  if (d <= 3)  return { text: `${d}d left`,              cls: "text-brand-purple" };
  return              { text: `${d}d left`,               cls: "text-text-3" };
}

export default function PrioritiesPage() {
  const [items, setItems]     = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  useEffect(() => {
    api.getAssignments()
      .then((r) => setItems(r.assignments))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex h-full items-center justify-center"><RefreshCw className="h-6 w-6 animate-spin text-brand-purple" /></div>;
  if (error)   return <div className="p-8"><p className="text-sm text-red-500">{error}</p></div>;

  // Rank: priority desc, then soonest due date, done items sink to the bottom
  const ranked = [...items].sort((a, b) => {
    if ((a.status === "done") !== (b.status === "done")) return a.status === "done" ? 1 : -1;
    const pr = PRIORITY_RANK[b.priority] - PRIORITY_RANK[a.priority];
    if (pr !== 0) return pr;
    return (a.due_date || "9999").localeCompare(b.due_date || "9999");
  });

  const active = ranked.filter((a) => a.status !== "done");

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-text-1 mb-1">Priorities</h1>
      <p className="text-sm text-text-2 mb-6">{active.length} active assignments, ranked by priority and deadline</p>

      <div className="flex flex-col gap-2">
        {ranked.map((a, i) => {
          const pc = PRIORITY_CFG[a.priority] ?? PRIORITY_CFG.medium;
          const sc = STATUS_CFG[a.status] ?? STATUS_CFG["todo"];
          const StatusIcon = sc.icon;
          const due = dueInfo(a.due_date);
          const isDone = a.status === "done";

          return (
            <div key={a.id} className={`flex items-center gap-4 rounded-xl bg-surface border border-ui-border p-4 shadow-sm ${isDone ? "opacity-50" : ""}`}>
              <span className="shrink-0 w-6 text-center text-xs font-bold text-text-3">{i + 1}</span>
              <div className={`w-1 h-9 rounded-full shrink-0 ${pc.bar}`} />
              <StatusIcon className={`h-4 w-4 shrink-0 ${sc.cls}`} />

              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium text-text-1 truncate ${isDone ? "line-through" : ""}`}>{a.title}</p>
                <div className="flex flex-wrap items-center gap-2 mt-1.5">
                  <span className={`rounded-full border px-2 py-0.5 text-xs ${pc.cls}`}>{pc.label}</span>
                  {a.assignees.length > 0
                    ? <span className="flex items-center gap-1">{a.assignees.slice(0,3).map((l) => <Avatar key={l} login={l} />)}</span>
                    : <span className="text-xs text-text-3 italic">Unassigned</span>}
                  {due && <span className={`flex items-center gap-0.5 text-xs ${due.cls}`}><Calendar className="h-3 w-3" />{due.text}</span>}
                </div>
              </div>
            </div>
          );
        })}

        {ranked.length === 0 && (
          <p className="text-sm text-text-3 text-center py-20">No assignments yet. Create some on the Assignments tab.</p>
        )}
      </div>
    </div>
  );
}
