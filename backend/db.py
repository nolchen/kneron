"""
SQLite persistence layer.
Stores team members, assignments, and the current data snapshot (projects/issues/PRs)
in a single file (pm_data.db) so everything survives restarts and can be shared.

Uses Python's built-in sqlite3 — no extra dependencies. JSON columns hold nested
fields (lists/dicts). A thread lock keeps concurrent FastAPI requests safe.
"""

import json
import os
import sqlite3
import threading
from pathlib import Path

# DATA_DIR lets a host mount a persistent volume (so data survives redeploys).
# Defaults to the backend folder for local dev.
_DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent))
_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _DATA_DIR / "pm_data.db"
_lock   = threading.Lock()


def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _lock, _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                login          TEXT PRIMARY KEY,
                role           TEXT    DEFAULT '',
                email          TEXT    DEFAULT '',
                workload_score REAL    DEFAULT 0,
                repos_active   TEXT    DEFAULT '[]',
                open_issues    INTEGER DEFAULT 0,
                open_prs       INTEGER DEFAULT 0,
                recent_commits INTEGER DEFAULT 0
            )
        """)
        # Migration: add email column to pre-existing tables (no-op if present)
        try:
            c.execute("ALTER TABLE team_members ADD COLUMN email TEXT DEFAULT ''")
        except Exception:
            pass
        c.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id         TEXT PRIMARY KEY,
                title      TEXT,
                assignees  TEXT DEFAULT '[]',
                due_date   TEXT,
                priority   TEXT DEFAULT 'medium',
                status     TEXT DEFAULT 'todo',
                notes      TEXT DEFAULT '',
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS email_accounts (
                email         TEXT PRIMARY KEY,
                name          TEXT DEFAULT '',
                refresh_token TEXT,
                connected_at  TEXT,
                last_synced   TEXT DEFAULT ''
            )
        """)


# ---------------------------------------------------------------------------
# Team members
# ---------------------------------------------------------------------------

def _row_to_member(r: sqlite3.Row) -> dict:
    keys = r.keys()
    return {
        "login":          r["login"],
        "role":           r["role"],
        "email":          r["email"] if "email" in keys else "",
        "workload_score": r["workload_score"],
        "repos_active":   json.loads(r["repos_active"] or "[]"),
        "open_issues":    r["open_issues"],
        "open_prs":       r["open_prs"],
        "recent_commits": r["recent_commits"],
    }


def get_team_members() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM team_members").fetchall()
    return [_row_to_member(r) for r in rows]


def member_exists(login: str) -> bool:
    with _lock, _conn() as c:
        return c.execute("SELECT 1 FROM team_members WHERE login = ?", (login,)).fetchone() is not None


def add_team_member(m: dict) -> dict:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO team_members (login, role, email, workload_score, repos_active, open_issues, open_prs, recent_commits) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (m["login"], m.get("role", ""), m.get("email", ""), m.get("workload_score", 0),
             json.dumps(m.get("repos_active", [])),
             m.get("open_issues", 0), m.get("open_prs", 0), m.get("recent_commits", 0)),
        )
    return m


def delete_team_member(login: str) -> bool:
    with _lock, _conn() as c:
        cur = c.execute("DELETE FROM team_members WHERE login = ?", (login,))
        return cur.rowcount > 0


def replace_team_members(members: list[dict]):
    """Wipe and reseed the whole team table (used by mock load / GitHub sync)."""
    with _lock, _conn() as c:
        c.execute("DELETE FROM team_members")
        for m in members:
            c.execute(
                "INSERT OR REPLACE INTO team_members (login, role, email, workload_score, repos_active, open_issues, open_prs, recent_commits) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (m["login"], m.get("role", ""), m.get("email", ""), m.get("workload_score", 0),
                 json.dumps(m.get("repos_active", [])),
                 m.get("open_issues", 0), m.get("open_prs", 0), m.get("recent_commits", 0)),
            )


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

def _row_to_assignment(r: sqlite3.Row) -> dict:
    return {
        "id":         r["id"],
        "title":      r["title"],
        "assignees":  json.loads(r["assignees"] or "[]"),
        "due_date":   r["due_date"],
        "priority":   r["priority"],
        "status":     r["status"],
        "notes":      r["notes"],
        "created_at": r["created_at"],
    }


def get_assignments() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM assignments ORDER BY created_at DESC").fetchall()
    return [_row_to_assignment(r) for r in rows]


def get_assignment(aid: str) -> dict | None:
    with _lock, _conn() as c:
        r = c.execute("SELECT * FROM assignments WHERE id = ?", (aid,)).fetchone()
    return _row_to_assignment(r) if r else None


def add_assignment(a: dict) -> dict:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO assignments (id, title, assignees, due_date, priority, status, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (a["id"], a["title"], json.dumps(a.get("assignees", [])),
             a.get("due_date", ""), a.get("priority", "medium"),
             a.get("status", "todo"), a.get("notes", ""), a["created_at"]),
        )
    return a


def update_assignment(aid: str, fields: dict) -> dict | None:
    existing = get_assignment(aid)
    if not existing:
        return None
    merged = {**existing, **fields}
    with _lock, _conn() as c:
        c.execute(
            "UPDATE assignments SET title=?, assignees=?, due_date=?, priority=?, status=?, notes=? WHERE id=?",
            (merged["title"], json.dumps(merged.get("assignees", [])),
             merged.get("due_date", ""), merged.get("priority", "medium"),
             merged.get("status", "todo"), merged.get("notes", ""), aid),
        )
    return merged


def delete_assignment(aid: str) -> bool:
    with _lock, _conn() as c:
        cur = c.execute("DELETE FROM assignments WHERE id = ?", (aid,))
        return cur.rowcount > 0


def clear_assignments():
    with _lock, _conn() as c:
        c.execute("DELETE FROM assignments")


# ---------------------------------------------------------------------------
# Meta (key/value JSON store) — for the GitHub/mock data snapshot + repos
# ---------------------------------------------------------------------------

def set_meta(key: str, value):
    with _lock, _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )


def get_meta(key: str, default=None):
    with _lock, _conn() as c:
        r = c.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


# ---------------------------------------------------------------------------
# Connected email accounts
# ---------------------------------------------------------------------------

def save_email_account(email: str, name: str, refresh_token: str, connected_at: str):
    with _lock, _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO email_accounts (email, name, refresh_token, connected_at, last_synced) "
            "VALUES (?, ?, ?, ?, COALESCE((SELECT last_synced FROM email_accounts WHERE email = ?), ''))",
            (email, name, refresh_token, connected_at, email),
        )


def list_email_accounts() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT email, name, connected_at, last_synced FROM email_accounts").fetchall()
    return [dict(r) for r in rows]


def get_email_account(email: str) -> dict | None:
    with _lock, _conn() as c:
        r = c.execute("SELECT * FROM email_accounts WHERE email = ?", (email,)).fetchone()
    return dict(r) if r else None


def get_all_email_accounts_full() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM email_accounts").fetchall()
    return [dict(r) for r in rows]


def set_email_synced(email: str, when: str):
    with _lock, _conn() as c:
        c.execute("UPDATE email_accounts SET last_synced = ? WHERE email = ?", (when, email))


def delete_email_account(email: str) -> bool:
    with _lock, _conn() as c:
        cur = c.execute("DELETE FROM email_accounts WHERE email = ?", (email,))
        return cur.rowcount > 0
