"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Assignment } from "@/lib/types";
import { formatName, initials } from "@/lib/utils";
import { RefreshCw, Circle, Clock, CheckCircle2, Calendar, AlertTriangle } from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const COLORS = ["bg-brand-purple","bg-brand-dark","bg-brand-green","bg-[#6B7FD4]","bg-[#9B7FD4]","bg-[#5B8FA8]"];

function Avatar({ login }: { login: string }) {
  const c = COLORS[login.charCodeAt(0) % COLORS.length];
  return (
    <div className={`h-6 w-6 ${c} rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0`} title={formatName(login)}>
      {initials(login)}
    </div>
  );
}

function AvatarStack({ logins }: { logins: string[] }) {
  return (
    <div className="flex -space-x-1">
      {logins.slice(0, 3).map((l) => (
        <div key={l} className="ring-2 ring-white rounded-full"><Avatar login={l} /></div>
      ))}
      {logins.length > 3 && (
        <div className="h-6 w-6 rounded-full bg-brand-light ring-2 ring-white flex items-center justify-center text-[9px] font-bold text-text-2">
          +{logins.length - 3}
        </div>
      )}
    </div>
  );
}

const PRIORITY_CFG = {
  high:   { cls: "bg-red-100 text-red-600 border-red-200",                     bar: "bg-red-400"     },
  medium: { cls: "bg-brand-purple/15 text-brand-purple border-brand-purple/20", bar: "bg-brand-purple" },
  low:    { cls: "bg-brand-green/15 text-brand-green border-brand-green/20",    bar: "bg-brand-green"  },
} as const;

const STATUS_ICON = {
  "todo":        { icon: Circle,        cls: "text-text-3" },
  "in-progress": { icon: Clock,         cls: "text-brand-purple"  },
  "done":        { icon: CheckCircle2,  cls: "text-brand-green"   },
} as const;

function daysLeft(dateStr: string) {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000);
}

function formatDue(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ---------------------------------------------------------------------------
// Single assignment row
// ---------------------------------------------------------------------------
function AssignmentRow({ a, dim }: { a: Assignment; dim?: boolean }) {
  const pc = PRIORITY_CFG[a.priority] ?? PRIORITY_CFG.medium;
  const sc = STATUS_ICON[a.status]     ?? STATUS_ICON["todo"];
  const StatusIcon = sc.icon;
  const d = daysLeft(a.due_date);

  let dueText = "";
  let dueCls  = "text-text-2";
  if (d < 0)       { dueText = `${Math.abs(d)}d overdue`; dueCls = "text-red-500 font-semibold"; }
  else if (d === 0){ dueText = "Due today";                dueCls = "text-brand-purple font-semibold"; }
  else if (d <= 3) { dueText = `${d}d left`;              dueCls = "text-brand-purple"; }
  else             { dueText = formatDue(a.due_date);      dueCls = "text-text-2"; }

  return (
    <div className={`flex items-center gap-4 bg-surface border border-ui-border rounded-xl px-4 py-3 shadow-sm transition-opacity ${dim ? "opacity-50" : ""}`}>
      {/* Priority bar */}
      <div className={`w-1 h-8 rounded-full shrink-0 ${pc.bar}`} />

      {/* Status icon */}
      <StatusIcon className={`h-4 w-4 shrink-0 ${sc.cls}`} />

      {/* Title */}
      <p className={`flex-1 text-sm font-medium text-text-1 min-w-0 truncate ${a.status === "done" ? "line-through opacity-50" : ""}`}>
        {a.title}
      </p>

      {/* Assignees */}
      {a.assignees?.length > 0
        ? <AvatarStack logins={a.assignees} />
        : <span className="text-xs text-text-3 italic">Unassigned</span>
      }

      {/* Priority badge */}
      <span className={`text-xs border rounded-full px-2 py-0.5 shrink-0 ${pc.cls}`}>
        {a.priority.charAt(0).toUpperCase() + a.priority.slice(1)}
      </span>

      {/* Due */}
      <span className={`text-xs shrink-0 flex items-center gap-1 ${dueCls}`}>
        <Calendar className="h-3 w-3" />{dueText}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Group section
// ---------------------------------------------------------------------------
function Group({ label, sublabel, accent, icon, items, dim }: {
  label: string; sublabel?: string; accent: string; icon: React.ReactNode;
  items: Assignment[]; dim?: boolean;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mb-6">
      <div className={`flex items-center gap-2 mb-3 pb-2 border-b-2 ${accent}`}>
        {icon}
        <span className="font-bold text-text-1 text-sm">{label}</span>
        {sublabel && <span className="text-xs text-text-2">{sublabel}</span>}
        <span className="ml-auto text-xs font-semibold text-text-2 bg-brand-light rounded-full px-2 py-0.5">{items.length}</span>
      </div>
      <div className="flex flex-col gap-2">
        {items.map((a) => <AssignmentRow key={a.id} a={a} dim={dim} />)}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function TimelinePage() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading]         = useState(true);

  useEffect(() => {
    api.getAssignments()
      .then((r) => setAssignments(r.assignments))
      .finally(() => setLoading(false));
  }, []);

  const now     = Date.now();
  const DAY     = 86_400_000;

  const active  = assignments.filter((a) => a.status !== "done" && a.due_date);
  const done    = assignments.filter((a) => a.status === "done");

  const overdue  = active.filter((a) => new Date(a.due_date).getTime() < now).sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime());
  const thisWeek = active.filter((a) => { const t = new Date(a.due_date).getTime(); return t >= now && t <= now + 7 * DAY; });
  const nextWeek = active.filter((a) => { const t = new Date(a.due_date).getTime(); return t > now + 7 * DAY && t <= now + 14 * DAY; });
  const later    = active.filter((a) => new Date(a.due_date).getTime() > now + 14 * DAY);
  const noDue    = assignments.filter((a) => a.status !== "done" && !a.due_date);

  // Stats
  const total     = assignments.length;
  const doneCount = done.length;
  const inProg    = assignments.filter((a) => a.status === "in-progress").length;
  const pct       = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  if (loading) return (
    <div className="flex h-full items-center justify-center">
      <RefreshCw className="h-6 w-6 animate-spin text-brand-purple" />
    </div>
  );

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-text-1 mb-1">Timeline</h1>
      <p className="text-sm text-text-2 mb-6">Assignment progress grouped by due date</p>

      {/* Summary bar */}
      {total > 0 && (
        <div className="bg-surface border border-ui-border rounded-xl p-5 shadow-sm mb-8">
          <div className="flex items-center justify-between mb-3">
            <div className="flex gap-6 text-sm">
              <span><span className="font-bold text-text-1">{total}</span> <span className="text-text-2">total</span></span>
              <span><span className="font-bold text-brand-purple">{inProg}</span> <span className="text-text-2">in progress</span></span>
              <span><span className="font-bold text-brand-green">{doneCount}</span> <span className="text-text-2">done</span></span>
              {overdue.length > 0 && <span><span className="font-bold text-red-500">{overdue.length}</span> <span className="text-text-2">overdue</span></span>}
            </div>
            <span className="text-sm font-bold text-text-1">{pct}%</span>
          </div>
          <div className="h-2.5 rounded-full bg-brand-light">
            <div className="h-2.5 rounded-full bg-brand-green transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {total === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-text-3 gap-2">
          <Calendar className="h-10 w-10" />
          <p className="text-sm">No assignments yet. Create some in the Assignments tab.</p>
        </div>
      )}

      <Group
        label="Overdue" accent="border-red-400"
        icon={<AlertTriangle className="h-4 w-4 text-red-400" />}
        items={overdue}
      />
      <Group
        label="This Week"
        sublabel={`Jun ${new Date().getDate()}–${new Date(now + 7 * DAY).getDate()}`}
        accent="border-brand-purple"
        icon={<Clock className="h-4 w-4 text-brand-purple" />}
        items={thisWeek}
      />
      <Group
        label="Next Week"
        sublabel={`Jun ${new Date(now + 8 * DAY).getDate()}–${new Date(now + 14 * DAY).getDate()}`}
        accent="border-brand-dark/30"
        icon={<Calendar className="h-4 w-4 text-text-2" />}
        items={nextWeek}
      />
      <Group
        label="Later" accent="border-brand-dark/20"
        icon={<Calendar className="h-4 w-4 text-text-3" />}
        items={later}
      />
      <Group
        label="No Due Date" accent="border-ui-border"
        icon={<Circle className="h-4 w-4 text-brand-dark/20" />}
        items={noDue}
      />

      {done.length > 0 && (
        <details className="mt-2">
          <summary className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-text-2 uppercase tracking-wider select-none hover:text-text-2 mb-3">
            <CheckCircle2 className="h-4 w-4 text-brand-green" /> Completed ({done.length})
          </summary>
          <div className="flex flex-col gap-2 mt-3">
            {done.map((a) => <AssignmentRow key={a.id} a={a} dim />)}
          </div>
        </details>
      )}
    </div>
  );
}
