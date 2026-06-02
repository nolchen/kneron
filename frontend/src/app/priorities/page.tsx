"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Task } from "@/lib/types";
import { RefreshCw, ExternalLink, Clock } from "lucide-react";

const LABEL_COLORS: Record<string, string> = {
  bug:              "bg-red-100 text-red-600",
  blocker:          "bg-red-200 text-red-700 font-bold",
  "priority-high":  "bg-brand-purple/15 text-brand-purple font-semibold",
  "priority-medium":"bg-brand-dark/10 text-text-2",
  enhancement:      "bg-brand-green/15 text-brand-green",
  documentation:    "bg-subtle text-text-2",
  performance:      "bg-brand-dark/10 text-text-2",
};
const labelClass = (l: string) => LABEL_COLORS[l.toLowerCase()] ?? "bg-subtle text-text-2";

function timeAgo(dateStr: string) {
  const d = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86_400_000);
  return d === 0 ? "today" : `${d}d ago`;
}

export default function PrioritiesPage() {
  const [tasks, setTasks]     = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  useEffect(() => {
    api.getPriorities()
      .then((r) => setTasks(r.priorities))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex h-full items-center justify-center"><RefreshCw className="h-6 w-6 animate-spin text-brand-purple" /></div>;
  if (error)   return <div className="p-8"><p className="text-sm text-red-500">{error}</p></div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-text-1 mb-1">Priorities</h1>
      <p className="text-sm text-text-2 mb-6">{tasks.length} open tasks ranked by priority</p>

      <div className="flex flex-col gap-2">
        {tasks.map((task, i) => (
          <a key={`${task.repo}-${task.number}`} href={task.url} target="_blank" rel="noopener noreferrer"
            className="flex items-start gap-4 rounded-xl bg-surface border border-ui-border p-4 shadow-sm hover:border-brand-purple/40 hover:shadow transition-all group">
            <span className="shrink-0 w-6 text-center text-xs font-bold text-text-3 mt-0.5">{i + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-text-1 truncate">{task.title}</p>
                <ExternalLink className="h-3.5 w-3.5 text-text-3 group-hover:text-brand-purple shrink-0 mt-0.5" />
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-1.5">
                <span className="text-xs text-text-3">#{task.number} · {task.repo}</span>
                {task.labels.map((lb) => (
                  <span key={lb} className={`rounded-full px-2 py-0.5 text-xs ${labelClass(lb)}`}>{lb}</span>
                ))}
                {task.assignees.length > 0 && <span className="text-xs text-text-3">→ {task.assignees.join(", ")}</span>}
                <span className="flex items-center gap-0.5 text-xs text-text-3 ml-auto">
                  <Clock className="h-3 w-3" />{timeAgo(task.updated_at)}
                </span>
              </div>
            </div>
          </a>
        ))}
        {tasks.length === 0 && <p className="text-sm text-text-3 text-center py-20">No open tasks found.</p>}
      </div>
    </div>
  );
}
