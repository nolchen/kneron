import { TeamMember, Project, Task, Milestone, ChatMessage, SyncResult, Assignment, Note, EmailAccount, User, ProposedEvent, GraphData } from "./types";

// Same-origin by default: the browser calls /api/* on THIS host, and Next
// rewrites (next.config.ts) proxy it to the backend. Keeps the session cookie
// first-party so auth works in browsers that block third-party cookies.
// (NEXT_PUBLIC_API_URL can still force a direct cross-origin base if needed.)
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const BASE = API_BASE;

// credentials: "include" sends/receives the session cookie cross-origin (Vercel↔Render).
async function loadMock() {
  await fetch(`${BASE}/api/mock`, { method: "POST", credentials: "include" });
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...opts,
  });

  // Auto-seed mock data for demo — then retry once
  if (res.status === 400) {
    const err = await res.json().catch(() => ({ detail: "" }));
    if ((err.detail as string)?.includes("No data synced")) {
      await loadMock();
      const retry = await fetch(`${BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        credentials: "include",
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
  health: () => req<{ status: string; cached_repos: string[]; github_configured: boolean }>("/api/health"),

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
  getGraph:      () => req<GraphData>("/api/graph"),

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

  // --- Auth + users ---
  authMe: () => req<{ user: User | null; configured: boolean; enforced: boolean }>("/api/auth/me"),
  // Microsoft sign-in is a full-page redirect (OAuth), not a fetch.
  login: () => { window.location.href = `${BASE}/api/auth/login`; },
  logout: () => req<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  devLogin: (email: string, role: string = "L3", name = "") =>
    req<{ user: User }>("/api/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ email, name, role }),
    }),
  listUsers: () => req<{ users: User[] }>("/api/users"),
  setUserRole: (email: string, role: string) =>
    req<User>(`/api/users/${encodeURIComponent(email)}/role`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    }),
  setUserManager: (email: string, manager_email: string) =>
    req<User>(`/api/users/${encodeURIComponent(email)}/manager`, {
      method: "PUT",
      body: JSON.stringify({ manager_email }),
    }),

  // --- Personal email → tasks → calendar ---
  inboxStatus: () => req<{ connected: boolean; email: string; last_synced: string }>("/api/me/inbox"),
  scanInbox: () => req<{ proposals: ProposedEvent[]; scanned: number }>("/api/me/scan", { method: "POST" }),
  confirmEvents: (events: ProposedEvent[]) =>
    req<{ results: { title: string; ok: boolean; webLink?: string; error?: string }[] }>(
      "/api/me/calendar/confirm",
      { method: "POST", body: JSON.stringify({ events }) },
    ),
};
