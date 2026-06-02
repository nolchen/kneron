"use client";

import { useEffect, useState, useCallback } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { AlertCircle, ClipboardList, Users, FolderGit2, RefreshCw, Bot, AlertTriangle, XCircle, Info } from "lucide-react";
import { api } from "@/lib/api";
import { TeamMember, Project, Assignment } from "@/lib/types";
import { formatName } from "@/lib/utils";
import SetupBanner from "@/components/SetupBanner";

interface Alert { type: "error" | "warning" | "info"; msg: string; }

function AlertBanner({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) return null;
  const cfg = {
    error:   { bg: "bg-red-50 border-red-200",           icon: <XCircle      className="h-4 w-4 text-red-500 shrink-0" />,    text: "text-red-700" },
    warning: { bg: "bg-orange-50 border-orange-200",      icon: <AlertTriangle className="h-4 w-4 text-orange-500 shrink-0" />, text: "text-orange-700" },
    info:    { bg: "bg-brand-purple/10 border-brand-purple/20", icon: <Info    className="h-4 w-4 text-brand-purple shrink-0" />, text: "text-brand-purple" },
  };
  return (
    <div className="flex flex-col gap-2 mb-6">
      {alerts.map((a, i) => {
        const c = cfg[a.type];
        return (
          <div key={i} className={`flex items-center gap-3 rounded-xl border px-4 py-3 ${c.bg}`}>
            {c.icon}
            <p className={`text-sm font-medium ${c.text}`}>{a.msg}</p>
          </div>
        );
      })}
    </div>
  );
}

function StatCard({ label, value, icon, accent }: {
  label: string; value: number | string; icon: React.ReactNode; accent: string;
}) {
  return (
    <div className="flex items-center gap-4 rounded-xl bg-surface border border-ui-border p-5 shadow-sm">
      <div className={`rounded-lg p-3 ${accent}`}>{icon}</div>
      <div>
        <p className="text-2xl font-bold text-text-1">{value}</p>
        <p className="text-sm text-text-2">{label}</p>
      </div>
    </div>
  );
}

const CHART_COLORS = ["#8380B6","#3C3744","#57A773","#8380B6","#3C3744","#57A773","#8380B6","#3C3744"];

export default function DashboardPage() {
  const [repos, setRepos]       = useState<string[]>([]);
  const [team, setTeam]         = useState<TeamMember[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [summary, setSummary]   = useState("");
  const [summaryError, setSummaryError] = useState("");
  const [loading, setLoading]   = useState(true);
  const [syncing, setSyncing]   = useState(false);
  const [hasData, setHasData]   = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [teamRes, projRes] = await Promise.all([api.getTeam(), api.getProjects()]);
      setTeam(teamRes.team_members);
      setProjects(projRes.projects);
      setHasData(true);
    } catch { setHasData(false); }
  }, []);

  useEffect(() => {
    const init = async () => {
      try {
        const health = await api.health();
        setRepos(health.cached_repos);
        if (health.cached_repos.length) await loadData();
      } finally { setLoading(false); }
    };
    init();
  }, [loadData]);

  const handleSynced = async () => {
    const health = await api.health();
    setRepos(health.cached_repos);
    await loadData();
  };

  const handleResync = async () => {
    setSyncing(true);
    try { await api.sync(); await loadData(); setSummary(""); }
    finally { setSyncing(false); }
  };

  const handleSummary = async () => {
    setSummary("Loading…"); setSummaryError("");
    try {
      const res = await api.getSummary();
      setSummary(res.summary || "No summary returned.");
    } catch (e: unknown) {
      setSummary(""); setSummaryError(e instanceof Error ? e.message : "Failed");
    }
  };

  const totalTasks = projects.reduce((s, p) => s + p.open_issues_count, 0);
  const maxScore   = Math.max(...team.map((m) => m.workload_score), 1);
  const chartData  = team.slice(0, 10).map((m) => ({
    name: formatName(m.login),
    pct: Math.round((m.workload_score / maxScore) * 100),
  }));

  if (loading) return (
    <div className="flex h-full items-center justify-center">
      <RefreshCw className="h-6 w-6 animate-spin text-brand-purple" />
    </div>
  );

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-1">Dashboard</h1>
          <p className="text-sm text-text-2 mt-1">AI Program Manager — Powered by Hermes Agent</p>
        </div>
        {hasData && (
          <button onClick={handleResync} disabled={syncing}
            className="flex items-center gap-2 rounded-lg border border-ui-border bg-surface px-4 py-2 text-sm font-medium text-text-1 hover:bg-subtle shadow-sm disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} /> Resync
          </button>
        )}
      </div>

      {!hasData && <SetupBanner repos={repos} onSynced={handleSynced} />}

      {hasData && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            <StatCard label="Open Tasks"      value={totalTasks}       icon={<AlertCircle  className="h-5 w-5 text-brand-purple" />} accent="bg-brand-purple/10" />
            <StatCard label="Team Members"    value={team.length}      icon={<Users         className="h-5 w-5 text-brand-green"  />} accent="bg-brand-green/10"  />
            <StatCard label="Active Projects" value={projects.length}  icon={<FolderGit2    className="h-5 w-5 text-brand-dark"   />} accent="bg-brand-dark/10"   />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="rounded-xl bg-surface border border-ui-border p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-text-1 mb-4">
                Team Workload <span className="text-text-2 font-normal">(% of max)</span>
              </h2>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={chartData} margin={{ bottom: 20 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--text-1)" }} angle={-30} textAnchor="end" />
                    <YAxis tick={{ fontSize: 11, fill: "var(--text-1)" }} domain={[0,100]} tickFormatter={(v) => `${v}%`} />
                    <Tooltip formatter={(v) => [`${v}%`, "Workload"]} contentStyle={{ borderRadius: 8, borderColor: "var(--ui-border)", backgroundColor: "var(--surface)", color: "var(--text-1)" }} />
                    <Bar dataKey="pct" radius={[4,4,0,0]}>
                      {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-text-3 text-center py-12">No team data yet</p>
              )}
            </div>

            <div className="rounded-xl bg-surface border border-ui-border p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-text-1">AI Executive Summary</h2>
                <button onClick={handleSummary} className="flex items-center gap-1 rounded-lg bg-brand-purple px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90">
                  <Bot className="h-3 w-3" /> Generate
                </button>
              </div>
              {summary === "Loading…" ? (
                <div className="flex flex-col items-center justify-center h-40 gap-3 text-text-3">
                  <RefreshCw className="h-6 w-6 animate-spin text-brand-purple" />
                  <p className="text-xs">Asking the AI… this takes ~15s</p>
                </div>
              ) : summaryError ? (
                <p className="text-sm text-red-500">{summaryError}</p>
              ) : summary ? (
                <p className="text-sm text-text-2 whitespace-pre-line leading-relaxed">{summary}</p>
              ) : (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-text-3">
                  <Bot className="h-8 w-8" />
                  <p className="text-sm">Click Generate to get an AI summary</p>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl bg-surface border border-ui-border p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-text-1 mb-4">Projects</h2>
            <div className="divide-y divide-ui-border">
              {projects.map((p) => (
                <div key={p.repo} className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-text-1">{p.full_name}</p>
                    {p.description && <p className="text-xs text-text-3 mt-0.5 truncate max-w-xs">{p.description}</p>}
                  </div>
                  <div className="flex gap-4 text-xs text-text-2">
                    <span className="flex items-center gap-1"><AlertCircle className="h-3 w-3 text-brand-purple" />{p.open_issues_count} tasks</span>
                    <span className="flex items-center gap-1"><ClipboardList className="h-3 w-3 text-text-3" />{p.open_prs_count} in review</span>
                    <span>{p.milestones.length} milestones</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
