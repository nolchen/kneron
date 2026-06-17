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
from datetime import datetime
from pathlib import Path

# Backend selection:
#   DATABASE_URL set (postgres://…) -> Postgres: persistent, shared, survives
#                                      redeploys. Use this in production.
#   otherwise                       -> local SQLite file: zero-config for dev.
# The SQL below is written ONCE and runs on both — `?` placeholders are
# translated to `%s` for Postgres, and every upsert uses the portable
# `ON CONFLICT (...) DO UPDATE` syntax (SQLite 3.24+ and Postgres both support it).
DATABASE_URL = os.environ.get("DATABASE_URL", "")
_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))

if _PG:
    import psycopg
    from psycopg.rows import dict_row

# DATA_DIR lets a host mount a persistent volume (SQLite mode only).
_DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent))
_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _DATA_DIR / "pm_data.db"
_lock   = threading.Lock()


class _Conn:
    """Backend-agnostic wrapper: call sites write SQL with `?` placeholders and
    use `with _conn() as c: c.execute(...)`. We translate placeholders for
    Postgres and proxy the context-manager protocol (commit on clean exit)."""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        if _PG:
            sql = sql.replace("?", "%s")
        return self._raw.execute(sql, params)

    def __enter__(self):
        self._raw.__enter__()
        return self

    def __exit__(self, *exc):
        return self._raw.__exit__(*exc)


def _conn() -> "_Conn":
    if _PG:
        return _Conn(psycopg.connect(DATABASE_URL, row_factory=dict_row))
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return _Conn(c)


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
        # Migration: add email column to pre-existing SQLite tables (no-op if present).
        # A fresh Postgres DB already has it from CREATE TABLE above, and a failed
        # ALTER would poison the Postgres transaction — so only attempt on SQLite.
        if not _PG:
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
        # App users + their permission level (admin | manager | intern).
        # Populated on Microsoft SSO login; role gates what each person can do.
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email      TEXT PRIMARY KEY,
                name       TEXT DEFAULT '',
                role       TEXT DEFAULT 'intern',
                created_at TEXT,
                last_login TEXT DEFAULT ''
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
                "INSERT INTO team_members (login, role, email, workload_score, repos_active, open_issues, open_prs, recent_commits) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (login) DO UPDATE SET role=EXCLUDED.role, email=EXCLUDED.email, "
                "workload_score=EXCLUDED.workload_score, repos_active=EXCLUDED.repos_active, "
                "open_issues=EXCLUDED.open_issues, open_prs=EXCLUDED.open_prs, recent_commits=EXCLUDED.recent_commits",
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
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
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
        # On first insert last_synced starts empty; on conflict we update the
        # token/name but leave last_synced untouched (preserving sync history).
        c.execute(
            "INSERT INTO email_accounts (email, name, refresh_token, connected_at, last_synced) "
            "VALUES (?, ?, ?, ?, '') "
            "ON CONFLICT (email) DO UPDATE SET name=EXCLUDED.name, "
            "refresh_token=EXCLUDED.refresh_token, connected_at=EXCLUDED.connected_at",
            (email, name, refresh_token, connected_at),
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


# ---------------------------------------------------------------------------
# App users + roles (admin | manager | intern)
# ---------------------------------------------------------------------------

def get_user(email: str) -> dict | None:
    with _lock, _conn() as c:
        r = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(r) if r else None


def count_users() -> int:
    with _lock, _conn() as c:
        return c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]


def upsert_user(email: str, name: str = "", role: str = "intern") -> dict:
    """Insert a user, or refresh name + last_login for an existing one.
    An existing user's role is preserved (change it via set_user_role)."""
    now = datetime.utcnow().isoformat()
    with _lock, _conn() as c:
        # Insert new, or refresh name + last_login for an existing user.
        # On conflict we deliberately leave `role` untouched (change via set_user_role).
        c.execute(
            "INSERT INTO users (email, name, role, created_at, last_login) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, last_login = EXCLUDED.last_login",
            (email, name, role, now, now),
        )
    return get_user(email)


def set_user_role(email: str, role: str) -> dict | None:
    with _lock, _conn() as c:
        cur = c.execute("UPDATE users SET role = ? WHERE email = ?", (role, email))
        if cur.rowcount == 0:
            return None
    return get_user(email)


def list_users() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT email, name, role, created_at, last_login FROM users ORDER BY role, email"
        ).fetchall()
    return [dict(r) for r in rows]
