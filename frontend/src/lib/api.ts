import { TeamMember, Project, Task, Milestone, ChatMessage, SyncResult, Assignment, Note, EmailAccount } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function loadMock() {
  await fetch(`${BASE}/api/mock`, { method: "POST" });
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });

  // Auto-seed mock data for demo — then retry once
  if (res.status === 400) {
    const err = await res.json().catch(() => ({ detail: "" }));
    if ((err.detail as string)?.includes("No data synced")) {
      await loadMock();
      const retry = await fetch(`${BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...opts,
      });
      if (retry.ok) return retry.json();
    }
    throw new Error(err.detail ?? "Bad request");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const api = {
  health: () => req<{ status: string; cached_repos: string[] }>("/api/health"),

  getRepos:  () => req<{ repos: string[] }>("/api/repos"),
  setRepos:  (repos: string[]) => req<{ repos: string[] }>("/api/repos", { method: "POST", body: JSON.stringify({ repos }) }),

  loadMock: () => req<{ loaded: boolean; team_members: number }>("/api/mock", { method: "POST" }),

  sync: (repos?: string[]) =>
    req<SyncResult>("/api/sync", {
      method: "POST",
      body: repos ? JSON.stringify({ repos }) : undefined,
    }),

  getTeam:       () => req<{ team_members: TeamMember[] }>("/api/team"),
  getProjects:   () => req<{ projects: Project[] }>("/api/projects"),
  getRoadmap:    () => req<{ milestones: Milestone[] }>("/api/roadmap"),
  getPriorities: () => req<{ priorities: Task[] }>("/api/priorities"),
  getSummary:    () => req<{ summary: string }>("/api/summary"),

  addMember: (name: string, role: string, repos: string) =>
    req<TeamMember>("/api/team/member", {
      method: "POST",
      body: JSON.stringify({ name, role, repos }),
    }),
  removeMember: (login: string) =>
    req<{ deleted: string }>(`/api/team/member/${login}`, { method: "DELETE" }),

  getAssignments: () => req<{ assignments: Assignment[] }>("/api/assignments"),
  createAssignment: (body: Omit<Assignment, "id" | "created_at">) =>
    req<Assignment>("/api/assignments", { method: "POST", body: JSON.stringify(body) }),
  updateAssignment: (id: string, body: Omit<Assignment, "id" | "created_at">) =>
    req<Assignment>(`/api/assignments/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteAssignment: (id: string) =>
    req<{ deleted: string }>(`/api/assignments/${id}`, { method: "DELETE" }),
  assignWorkers: (id: string, assignees: string[]) =>
    req<Assignment>(`/api/assignments/${id}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ assignees }),
    }),

  emailStatus:    () => req<{ configured: boolean; accounts: EmailAccount[] }>("/api/email/status"),
  emailConnect:   () => req<{ auth_url: string }>("/api/email/connect"),
  emailSync:      () => req<{ synced_emails: number; accounts: number; errors: string[] }>("/api/email/sync", { method: "POST" }),
  emailDisconnect: (email: string) => req<{ disconnected: string }>(`/api/email/accounts/${encodeURIComponent(email)}`, { method: "DELETE" }),

  getNotes:       () => req<{ notes: Note[] }>("/api/notes"),
  saveNote:       (title: string, content: string, note_type: string) =>
    req<Note>("/api/notes", { method: "POST", body: JSON.stringify({ title, content, note_type }) }),
  generateReport: () => req<Note>("/api/notes/generate", { method: "POST" }),
  deleteNote:     (id: string) => req<{ deleted: string }>(`/api/notes/${id}`, { method: "DELETE" }),

  chat: (message: string, history: ChatMessage[], includeGithub = true) =>
    req<{ response: string }>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, history, include_github: includeGithub }),
    }),
};
