"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { Milestone, Assignment } from "@/lib/types";
import { formatName } from "@/lib/utils";

const MONTHS = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"];
const DAYS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

function daysUntil(dateStr: string) {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000);
}

function milestoneColor(ms: Milestone) {
  const d = daysUntil(ms.due_on!);
  if (d < 0)  return { dot: "bg-red-400",     pill: "bg-red-100 text-red-700 border-red-200" };
  if (d <= 7) return { dot: "bg-brand-purple", pill: "bg-brand-purple/15 text-brand-purple border-brand-purple/20" };
  return            { dot: "bg-brand-green",   pill: "bg-brand-green/15 text-brand-green border-brand-green/20" };
}

function assignmentColor(a: Assignment) {
  const d = daysUntil(a.due_date);
  if (d < 0)  return { dot: "bg-red-300",      pill: "bg-red-50 text-red-600 border-red-100" };
  if (d <= 7) return { dot: "bg-brand-dark",   pill: "bg-brand-dark/10 text-text-1 border-brand-dark/20" };
  return            { dot: "bg-brand-dark/40", pill: "bg-brand-light text-brand-dark/70 border-ui-border" };
}

export default function CalendarPage() {
  const today = new Date();
  const [viewed, setViewed]         = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading]       = useState(true);
  const [selected, setSelected]     = useState<number | null>(null);

  useEffect(() => {
    Promise.all([api.getRoadmap(), api.getAssignments()]).then(([r, a]) => {
      setMilestones(r.milestones.filter((m) => m.due_on));
      setAssignments(a.assignments.filter((x) => x.due_date && x.status !== "done"));
    }).finally(() => setLoading(false));
  }, []);

  const year  = viewed.getFullYear();
  const month = viewed.getMonth();
  const firstDay    = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [...Array(firstDay).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];

  const isToday = (d: number) =>
    d === today.getDate() && month === today.getMonth() && year === today.getFullYear();

  const msOnDay = (d: number) => milestones.filter((ms) => {
    const due = new Date(ms.due_on!);
    return due.getDate() === d && due.getMonth() === month && due.getFullYear() === year;
  });

  const asOnDay = (d: number) => assignments.filter((a) => {
    const due = new Date(a.due_date);
    return due.getDate() === d && due.getMonth() === month && due.getFullYear() === year;
  });

  const selectedMs = selected ? msOnDay(selected) : [];
  const selectedAs = selected ? asOnDay(selected) : [];

  // All events this month for side panel default view
  const monthMs = milestones.filter((ms) => {
    const d = new Date(ms.due_on!);
    return d.getMonth() === month && d.getFullYear() === year;
  }).sort((a, b) => new Date(a.due_on!).getTime() - new Date(b.due_on!).getTime());

  const monthAs = assignments.filter((a) => {
    const d = new Date(a.due_date);
    return d.getMonth() === month && d.getFullYear() === year;
  }).sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime());

  if (loading) return (
    <div className="flex h-full items-center justify-center">
      <RefreshCw className="h-6 w-6 animate-spin text-brand-purple" />
    </div>
  );

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-text-1 mb-1">Calendar</h1>
      <p className="text-sm text-text-2 mb-6">Milestones and assignment due dates</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar grid */}
        <div className="lg:col-span-2 rounded-xl bg-surface border border-ui-border p-5 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <button onClick={() => setViewed(new Date(year, month - 1, 1))} className="p-1.5 rounded-lg hover:bg-brand-light">
              <ChevronLeft className="h-4 w-4 text-text-2" />
            </button>
            <h2 className="font-semibold text-text-1">{MONTHS[month]} {year}</h2>
            <button onClick={() => setViewed(new Date(year, month + 1, 1))} className="p-1.5 rounded-lg hover:bg-brand-light">
              <ChevronRight className="h-4 w-4 text-text-2" />
            </button>
          </div>

          <div className="grid grid-cols-7 mb-2">
            {DAYS.map((d) => (
              <div key={d} className="text-center text-xs font-semibold text-text-2 py-1">{d}</div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {cells.map((day, i) => {
              if (!day) return <div key={i} />;
              const ms = msOnDay(day);
              const as = asOnDay(day);
              const active = selected === day;
              const totalDots = ms.length + as.length;

              return (
                <button
                  key={i}
                  onClick={() => setSelected(active ? null : day)}
                  className={`relative flex flex-col items-center rounded-lg p-1 min-h-[52px] transition-colors w-full ${
                    active ? "bg-brand-purple/10 ring-1 ring-brand-purple/40" : "hover:bg-brand-light"
                  }`}
                >
                  <span className={`text-xs font-semibold w-6 h-6 flex items-center justify-center rounded-full mb-1 ${
                    isToday(day) ? "bg-brand-purple text-white" : "text-text-1"
                  }`}>{day}</span>

                  {totalDots > 0 && (
                    <div className="flex flex-wrap gap-0.5 justify-center">
                      {ms.slice(0, 2).map((m, j) => (
                        <span key={`m${j}`} className={`h-1.5 w-1.5 rounded-full ${milestoneColor(m).dot}`} />
                      ))}
                      {as.slice(0, 2).map((a, j) => (
                        <span key={`a${j}`} className={`h-1.5 w-1.5 rounded-sm ${assignmentColor(a).dot}`} />
                      ))}
                      {totalDots > 4 && <span className="text-[8px] text-text-2">+{totalDots - 4}</span>}
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-ui-border">
            {[
              { color: "bg-brand-green rounded-full",  label: "Milestone (on track)" },
              { color: "bg-brand-purple rounded-full", label: "Milestone (due soon)" },
              { color: "bg-red-400 rounded-full",      label: "Overdue" },
              { color: "bg-brand-dark rounded-sm",     label: "Assignment" },
            ].map(({ color, label }) => (
              <span key={label} className="flex items-center gap-1.5 text-xs text-text-2">
                <span className={`h-2 w-2 ${color}`} />{label}
              </span>
            ))}
          </div>
        </div>

        {/* Side panel */}
        <div className="rounded-xl bg-surface border border-ui-border p-5 shadow-sm overflow-y-auto max-h-[600px]">
          {selected ? (
            <>
              <h3 className="font-semibold text-text-1 mb-1">{MONTHS[month]} {selected}</h3>
              <p className="text-xs text-text-2 mb-4">
                {selectedMs.length + selectedAs.length} event{selectedMs.length + selectedAs.length !== 1 ? "s" : ""}
              </p>

              {selectedMs.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-text-2 mb-2">Milestones</p>
                  <div className="flex flex-col gap-2">
                    {selectedMs.map((ms, i) => {
                      const { pill } = milestoneColor(ms);
                      const d = daysUntil(ms.due_on!);
                      return (
                        <div key={i} className={`rounded-lg border p-3 ${pill}`}>
                          <p className="text-sm font-semibold">{ms.title}</p>
                          <p className="text-xs opacity-60 mt-0.5">{ms.repo}</p>
                          <div className="flex justify-between mt-2 text-xs font-medium">
                            <span>{ms.progress.toFixed(0)}% done</span>
                            <span>{d < 0 ? `${Math.abs(d)}d overdue` : d === 0 ? "Due today" : `${d}d left`}</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-surface/50 mt-1"><div className="h-1.5 rounded-full bg-current opacity-50" style={{ width: `${ms.progress}%` }} /></div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {selectedAs.length > 0 && (
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-text-2 mb-2">Assignments</p>
                  <div className="flex flex-col gap-2">
                    {selectedAs.map((a, i) => {
                      const { pill } = assignmentColor(a);
                      const d = daysUntil(a.due_date);
                      return (
                        <div key={i} className={`rounded-lg border p-3 ${pill}`}>
                          <p className="text-sm font-semibold">{a.title}</p>
                          {a.assignees.length > 0 && (
                            <p className="text-xs opacity-60 mt-0.5">{a.assignees.map(formatName).join(", ")}</p>
                          )}
                          <div className="flex justify-between mt-2 text-xs font-medium">
                            <span className="capitalize">{a.priority} priority</span>
                            <span>{d < 0 ? `${Math.abs(d)}d overdue` : d === 0 ? "Due today" : `${d}d left`}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {selectedMs.length === 0 && selectedAs.length === 0 && (
                <p className="text-sm text-text-3 text-center py-8">Nothing due on this day</p>
              )}
            </>
          ) : (
            <>
              <h3 className="font-semibold text-text-1 mb-4">This month</h3>

              {monthMs.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-text-2 mb-2">Milestones</p>
                  <div className="flex flex-col gap-2">
                    {monthMs.map((ms, i) => {
                      const { pill } = milestoneColor(ms);
                      const due = new Date(ms.due_on!);
                      return (
                        <div key={i} className={`rounded-lg border p-3 ${pill}`}>
                          <p className="text-sm font-semibold">{ms.title}</p>
                          <p className="text-xs opacity-60">{MONTHS[due.getMonth()]} {due.getDate()}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {monthAs.length > 0 && (
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-text-2 mb-2">Assignments</p>
                  <div className="flex flex-col gap-2">
                    {monthAs.map((a, i) => {
                      const { pill } = assignmentColor(a);
                      const due = new Date(a.due_date);
                      return (
                        <div key={i} className={`rounded-lg border p-3 ${pill}`}>
                          <p className="text-sm font-semibold">{a.title}</p>
                          <p className="text-xs opacity-60">{MONTHS[due.getMonth()]} {due.getDate()}{a.assignees.length > 0 ? ` · ${a.assignees.map(formatName).join(", ")}` : ""}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {monthMs.length === 0 && monthAs.length === 0 && (
                <p className="text-sm text-text-3 text-center py-8">Nothing due this month</p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
