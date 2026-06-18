export interface TeamMember {
  login: string;
  role?: string;
  email?: string;
  workload_score: number;
  repos_active: string[];
  // GitHub-specific (optional — only present when synced from GitHub)
  open_issues?: number;
  open_prs?: number;
  recent_commits?: number;
}

export interface Milestone {
  id: number;
  title: string;
  description?: string;
  due_on?: string;
  open_issues: number;
  closed_issues: number;
  progress: number;
  repo: string;
}

export interface Task {
  number: number;
  title: string;
  url: string;
  state: string;
  labels: string[];
  assignees: string[];
  created_at: string;
  updated_at: string;
  repo: string;
}

export interface Project {
  repo: string;
  full_name: string;
  description?: string;
  open_issues_count: number;
  open_prs_count: number;
  milestones: Milestone[];
}

export interface Assignment {
  id: string;
  title: string;
  assignees: string[];   // multiple workers
  due_date: string;
  priority: "low" | "medium" | "high";
  status: "todo" | "in-progress" | "done";
  notes: string;
  created_at: string;
}

export interface EmailAccount {
  email: string;
  name: string;
  connected_at: string;
  last_synced: string;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  type: string;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ProposedEvent {
  title: string;
  start: string;          // 'YYYY-MM-DDTHH:MM:SS'
  end?: string;
  attendees?: string[];
  source_subject?: string;
  confidence?: number;
  add_to_board?: boolean;
}

export type Role = "admin" | "manager" | "intern";

export interface User {
  email: string;
  name: string;
  role: Role;
  manager_email?: string;
  created_at?: string;
  last_login?: string;
}

export interface SyncResult {
  synced_repos: string[];
  team_members: number;
  open_issues: number;
  open_prs: number;
}
