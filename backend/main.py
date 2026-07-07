import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel

load_dotenv()

from github_client import GitHubClient
from pm_agent import ProgramManagerAgent
from notes_store import NotesStore
from vault_client import write_note, scan_vault
import db
import email_client
import auth
import notifications
import visibility

_notes = NotesStore()

MOCK_REPOS = ["kneron/backend-api", "kneron/mobile-app", "kneron/ml-pipeline"]

MOCK_TEAM = [
    {"login": "nolan_chen",       "role": "Backend Engineer",    "open_issues": 8,  "open_prs": 3, "recent_commits": 12, "repos_active": ["kneron/backend-api", "kneron/ml-pipeline"], "workload_score": 20.0},
    {"login": "bobby_lee",        "role": "Mobile Engineer",     "open_issues": 5,  "open_prs": 2, "recent_commits": 9,  "repos_active": ["kneron/mobile-app"], "workload_score": 13.5},
    {"login": "julia_aquino",     "role": "Full-Stack Engineer", "open_issues": 4,  "open_prs": 2, "recent_commits": 7,  "repos_active": ["kneron/backend-api", "kneron/mobile-app"], "workload_score": 11.5},
    {"login": "thomas_train",     "role": "Backend Engineer",    "open_issues": 4,  "open_prs": 2, "recent_commits": 6,  "repos_active": ["kneron/backend-api"], "workload_score": 11.0},
    {"login": "deez_nuts",        "role": "ML Engineer",         "open_issues": 3,  "open_prs": 1, "recent_commits": 6,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 8.0},
    {"login": "albert_liu",       "role": "DevOps Engineer",     "open_issues": 2,  "open_prs": 2, "recent_commits": 4,  "repos_active": ["kneron/backend-api"], "workload_score": 8.0},
    {"login": "alice_zhu",        "role": "Frontend Engineer",   "open_issues": 3,  "open_prs": 1, "recent_commits": 5,  "repos_active": ["kneron/mobile-app", "kneron/backend-api"], "workload_score": 7.5},
    {"login": "jenna_wu",         "role": "ML Engineer",         "open_issues": 2,  "open_prs": 1, "recent_commits": 4,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 6.0},
    {"login": "chuddington_chad", "role": "Mobile Engineer",     "open_issues": 2,  "open_prs": 1, "recent_commits": 3,  "repos_active": ["kneron/mobile-app"], "workload_score": 5.5},
    {"login": "drake_drizzy",     "role": "Frontend Engineer",   "open_issues": 1,  "open_prs": 1, "recent_commits": 2,  "repos_active": ["kneron/mobile-app"], "workload_score": 4.0},
    {"login": "kendrick_llamar",  "role": "Data Engineer",       "open_issues": 1,  "open_prs": 0, "recent_commits": 3,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 2.5},
    {"login": "sandy_eggos",      "role": "QA Engineer",         "open_issues": 0,  "open_prs": 1, "recent_commits": 1,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 2.5},
    # Free / available — recently rolled off other work, no open assignments.
    {"login": "joe_mama",         "role": "Frontend Engineer",   "open_issues": 0,  "open_prs": 0, "recent_commits": 0,  "repos_active": ["kneron/mobile-app"], "workload_score": 0.0},
    {"login": "elon_must",        "role": "Platform Engineer",   "open_issues": 0,  "open_prs": 0, "recent_commits": 0,  "repos_active": ["kneron/backend-api"], "workload_score": 0.0},
    {"login": "obama_joe",        "role": "ML Engineer",         "open_issues": 0,  "open_prs": 0, "recent_commits": 0,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 0.0},
]

MOCK_DATA = {
    "team_members": MOCK_TEAM,
    "projects": [
        {
            "repo": "kneron/backend-api",
            "full_name": "Kneron / Backend API",
            "description": "Core REST API powering all Kneron products",
            "open_issues_count": 14,
            "open_prs_count": 5,
            "milestones": [
                {"id": 1, "title": "v2.0 Public Release", "description": "Full API v2 with rate limiting and OAuth", "due_on": "2026-06-20T00:00:00Z", "open_issues": 6, "closed_issues": 9, "progress": 60.0, "repo": "kneron/backend-api"},
                {"id": 2, "title": "Performance Hardening", "description": "P99 latency < 200ms under 10k rps", "due_on": "2026-07-15T00:00:00Z", "open_issues": 4, "closed_issues": 2, "progress": 33.3, "repo": "kneron/backend-api"},
            ],
        },
        {
            "repo": "kneron/mobile-app",
            "full_name": "Kneron / Mobile App",
            "description": "iOS & Android app built with React Native",
            "open_issues_count": 9,
            "open_prs_count": 3,
            "milestones": [
                {"id": 3, "title": "App Store Launch", "description": "Pass Apple review and hit the store", "due_on": "2026-06-10T00:00:00Z", "open_issues": 3, "closed_issues": 11, "progress": 78.6, "repo": "kneron/mobile-app"},
            ],
        },
        {
            "repo": "kneron/ml-pipeline",
            "full_name": "Kneron / ML Pipeline",
            "description": "Training and inference infrastructure for edge AI models",
            "open_issues_count": 6,
            "open_prs_count": 2,
            "milestones": [
                {"id": 4, "title": "Edge Inference v1", "description": "Sub-5ms inference on KL720 chip", "due_on": "2026-07-01T00:00:00Z", "open_issues": 5, "closed_issues": 3, "progress": 37.5, "repo": "kneron/ml-pipeline"},
            ],
        },
    ],
    "issues": [
        {"number": 341, "title": "Redis session cache evicts active tokens under memory pressure", "url": "#", "state": "open", "labels": ["blocker", "performance"], "assignees": ["nolan_chen"], "created_at": "2026-06-05T10:00:00Z", "updated_at": "2026-06-16T09:00:00Z", "repo": "kneron/backend-api"},
        {"number": 298, "title": "Refresh-token rotation breaks SSO for returning users", "url": "#", "state": "open", "labels": ["bug", "priority-high", "auth"], "assignees": ["thomas_train"], "created_at": "2026-06-03T08:00:00Z", "updated_at": "2026-06-15T14:00:00Z", "repo": "kneron/backend-api"},
        {"number": 103, "title": "Dark mode flickers on cold app launch (Android)", "url": "#", "state": "open", "labels": ["bug", "priority-medium", "android"], "assignees": ["bobby_lee"], "created_at": "2026-06-07T11:00:00Z", "updated_at": "2026-06-17T10:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 355, "title": "GraphQL N+1 queries slow /dashboard by 4x", "url": "#", "state": "open", "labels": ["bug", "priority-high", "performance"], "assignees": ["julia_aquino"], "created_at": "2026-06-04T09:00:00Z", "updated_at": "2026-06-17T08:00:00Z", "repo": "kneron/backend-api"},
        {"number": 61,  "title": "INT8 quantised model drops 6% accuracy on KL630", "url": "#", "state": "open", "labels": ["priority-high", "performance"], "assignees": ["deez_nuts"], "created_at": "2026-06-02T13:00:00Z", "updated_at": "2026-06-14T16:00:00Z", "repo": "kneron/ml-pipeline"},
        {"number": 117, "title": "Deep links open the wrong screen after app update", "url": "#", "state": "open", "labels": ["bug", "priority-medium", "ios"], "assignees": ["chuddington_chad"], "created_at": "2026-06-06T15:00:00Z", "updated_at": "2026-06-13T11:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 362, "title": "Add structured JSON logging across API services", "url": "#", "state": "open", "labels": ["enhancement", "priority-medium", "observability"], "assignees": ["albert_liu"], "created_at": "2026-06-08T10:00:00Z", "updated_at": "2026-06-16T12:00:00Z", "repo": "kneron/backend-api"},
        {"number": 71,  "title": "Model export pipeline times out on >500MB checkpoints", "url": "#", "state": "open", "labels": ["bug", "priority-medium"], "assignees": ["jenna_wu", "kendrick_llamar"], "created_at": "2026-06-05T14:00:00Z", "updated_at": "2026-06-15T15:00:00Z", "repo": "kneron/ml-pipeline"},
        {"number": 129, "title": "Offline mode loses unsynced edits on force-quit", "url": "#", "state": "open", "labels": ["bug", "priority-high"], "assignees": ["alice_zhu", "drake_drizzy"], "created_at": "2026-06-09T09:00:00Z", "updated_at": "2026-06-17T09:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 368, "title": "Document webhook retry/back-off behaviour for partners", "url": "#", "state": "open", "labels": ["documentation"], "assignees": ["julia_aquino"], "created_at": "2026-06-10T11:00:00Z", "updated_at": "2026-06-16T09:00:00Z", "repo": "kneron/backend-api"},
        {"number": 74,  "title": "Flaky inference regression tests block the CI nightly", "url": "#", "state": "open", "labels": ["bug", "priority-medium"], "assignees": ["sandy_eggos"], "created_at": "2026-06-07T16:00:00Z", "updated_at": "2026-06-14T07:00:00Z", "repo": "kneron/ml-pipeline"},
        # Unassigned / open work — up for grabs.
        {"number": 372, "title": "Stand up staging environment with prod parity", "url": "#", "state": "open", "labels": ["enhancement", "priority-medium"], "assignees": [], "created_at": "2026-06-12T10:00:00Z", "updated_at": "2026-06-16T10:00:00Z", "repo": "kneron/backend-api"},
        {"number": 134, "title": "Add pull-to-refresh to the activity feed", "url": "#", "state": "open", "labels": ["enhancement", "priority-medium"], "assignees": [], "created_at": "2026-06-11T11:00:00Z", "updated_at": "2026-06-15T11:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 79,  "title": "Benchmark KL630 vs KL720 throughput for the docs", "url": "#", "state": "open", "labels": ["documentation"], "assignees": [], "created_at": "2026-06-13T14:00:00Z", "updated_at": "2026-06-16T14:00:00Z", "repo": "kneron/ml-pipeline"},
    ],
    "pull_requests": [
        {"number": 340, "title": "fix: cap redis session cache with LRU eviction guard", "url": "#", "state": "open", "author": "nolan_chen", "assignees": ["thomas_train"], "created_at": "2026-06-15T10:00:00Z", "updated_at": "2026-06-17T08:00:00Z", "repo": "kneron/backend-api", "draft": False},
        {"number": 343, "title": "feat: structured JSON logging middleware", "url": "#", "state": "open", "author": "albert_liu", "assignees": ["nolan_chen"], "created_at": "2026-06-14T14:00:00Z", "updated_at": "2026-06-16T11:00:00Z", "repo": "kneron/backend-api", "draft": False},
        {"number": 104, "title": "fix: dark-mode cold-launch flicker", "url": "#", "state": "open", "author": "bobby_lee", "assignees": ["alice_zhu"], "created_at": "2026-06-16T09:00:00Z", "updated_at": "2026-06-17T10:00:00Z", "repo": "kneron/mobile-app", "draft": False},
        {"number": 105, "title": "fix: deep-link routing after app update", "url": "#", "state": "open", "author": "chuddington_chad", "assignees": ["bobby_lee"], "created_at": "2026-06-13T16:00:00Z", "updated_at": "2026-06-14T09:00:00Z", "repo": "kneron/mobile-app", "draft": True},
        {"number": 62,  "title": "perf: recover INT8 accuracy via per-channel calibration", "url": "#", "state": "open", "author": "deez_nuts", "assignees": ["jenna_wu"], "created_at": "2026-06-14T13:00:00Z", "updated_at": "2026-06-15T07:00:00Z", "repo": "kneron/ml-pipeline", "draft": False},
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gh() -> GitHubClient:
    return GitHubClient(token=os.environ.get("GITHUB_TOKEN"))


def _pm() -> ProgramManagerAgent:
    return ProgramManagerAgent()  # provider + model resolved from env (see llm_config.py)


def _data_snapshot() -> Optional[dict]:
    """The non-team GitHub/mock data (projects, issues, pull_requests), or None."""
    return db.get_meta("github_snapshot")


def _full_data() -> Optional[dict]:
    """Assemble the complete data dict (team + live assignment board + snapshot)
    for AI context / dashboards. Assignments are included so the AI sees the
    current board and calendar — not just the static issue snapshot."""
    snap = _data_snapshot()
    if snap is None:
        return None
    return {
        "team_members": _team_with_workload(),
        "assignments":  db.get_assignments(),
        **snap,
    }


def _scoped_data(request) -> Optional[dict]:
    """Like _full_data, but team + assignments are limited to what the requester
    may see (their visible people). No-op in demo mode / for admins."""
    data = _full_data()
    if data is None:
        return None
    vis = visibility.scope_for(request)
    if vis is None:
        return data
    scoped = dict(data)
    scoped["team_members"] = [m for m in data.get("team_members", []) if m["login"] in vis]
    scoped["assignments"] = [a for a in data.get("assignments", []) if set(a.get("assignees", [])) & vis]
    return scoped


def _require_data():
    if _data_snapshot() is None:
        raise HTTPException(
            status_code=400,
            detail="No data synced yet. POST /api/sync to fetch GitHub data first.",
        )


def _issue_priority(labels: list) -> str:
    """Map GitHub-style labels to an assignment priority."""
    low = [l.lower() for l in labels]
    if "blocker" in low or "priority-high" in low:
        return "high"
    if "bug" in low or "priority-medium" in low:
        return "medium"
    return "low"


def _seed_assignments_from_issues():
    """Turn the mock issues into real assignments so workload is driven by
    visible work — no more phantom workload from a hidden base score."""
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    due_offset = {"high": 1, "medium": 6, "low": 12}
    # Per-issue jitter so due dates are spread out — a few overdue, some this
    # week, some further out — rather than bunched by priority.
    jitter = [-3, 2, 5, -1, 1, 4, 0, 3, -2, 7, 1]
    for idx, issue in enumerate(MOCK_DATA["issues"]):
        p = _issue_priority(issue["labels"])
        days = due_offset[p] + jitter[idx % len(jitter)]
        due = (today + timedelta(days=days)).strftime("%Y-%m-%d")
        db.add_assignment({
            "id":         str(uuid.uuid4()),
            "created_at": today.isoformat(),
            "title":      issue["title"],
            "assignees":  issue["assignees"],
            "due_date":   due,
            "priority":   p,
            "status":     "in-progress" if issue["assignees"] else "todo",
            "notes":      f"From {issue['repo']} · {', '.join(issue['labels'])}",
        })


def _seed_mock(reset_assignments: bool = True):
    """Load demo data into the DB. Optionally wipe assignments (explicit reset only)."""
    # Base workload is 0 — workload comes entirely from assignments, so what you
    # see on the board fully explains each person's load.
    db.replace_team_members([
        {**m, "workload_score": 0.0, "email": f"{m['login'].replace('_', '.')}@kneron.us"}
        for m in MOCK_TEAM
    ])
    db.set_meta("github_snapshot", {
        "projects":       MOCK_DATA["projects"],
        "issues":         MOCK_DATA["issues"],
        "pull_requests":  MOCK_DATA["pull_requests"],
    })
    db.set_meta("repos", MOCK_REPOS)
    if reset_assignments:
        db.clear_assignments()
        _seed_assignments_from_issues()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="PM Dashboard API", version="1.0.0")

# Allowed origins: localhost for dev + any URLs from ALLOWED_ORIGINS env (comma-separated).
# Set ALLOWED_ORIGINS to your deployed frontend URL(s) in production.
_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_env_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _env_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _login_from_email(email: str) -> str:
    """Stable team-member login derived from an email local-part."""
    return email.split("@")[0].replace(".", "_").lower()


def _ensure_member_from_inbox(email: str, name: str = "") -> None:
    """A connected inbox == a person on the team. Idempotent — adds them to the
    board if not already there. This is how the team is built when demo data is
    off: only people who've actually connected an inbox show up."""
    login = _login_from_email(email)
    if not db.member_exists(login):
        db.add_team_member({
            "login": login, "role": "", "email": email, "workload_score": 0,
            "repos_active": [], "open_issues": 0, "open_prs": 0, "recent_commits": 0,
        })


def _seed_demo_enabled() -> bool:
    return os.environ.get("SEED_DEMO_DATA", "true").lower() in ("1", "true", "yes", "on")


@app.on_event("startup")
def startup():
    """Init the database. With SEED_DEMO_DATA on, seed mock data on a fresh DB.
    With it off, the team is built purely from connected inboxes."""
    # Fail closed: never boot with AUTH_ENFORCED on but the companion secrets
    # missing, which would let auth run wide open (forgeable tokens, dev-login
    # still on, or a stranger auto-promoted to admin).
    problems = auth.enforcement_config_errors()
    if problems:
        raise RuntimeError(
            "AUTH_ENFORCED is on but unsafe to enforce — fix these and restart:\n  - "
            + "\n  - ".join(problems)
        )
    db.init_db()
    if _seed_demo_enabled():
        if not db.get_team_members() and _data_snapshot() is None:
            _seed_mock(reset_assignments=True)
            print("[startup] Fresh DB — demo data seeded.")
        else:
            print("[startup] Existing data found — loaded from database.")
    else:
        for acct in db.list_email_accounts():
            _ensure_member_from_inbox(acct["email"], acct.get("name", ""))
        print("[startup] Demo seeding OFF — team = connected inboxes only.")

    # Data-gated endpoints (roadmap / summary / reports) require a snapshot to
    # exist. With no GitHub sync and demo data off, none is ever created, so
    # seed an empty one — the app then works off team + assignments alone.
    if _data_snapshot() is None:
        db.set_meta("github_snapshot", {"projects": [], "issues": [], "pull_requests": []})

    # Best-effort: index Obsidian vault notes so the AI chat can reference them.
    # ChromaDB is ephemeral on some hosts, so re-index on each boot.
    try:
        existing = {n["title"] for n in _notes.list_all()}
        indexed = 0
        for vn in scan_vault():
            if vn["title"] not in existing:
                _notes.save(title=vn["title"], content=vn["content"], note_type=vn.get("type", "note"))
                indexed += 1
        print(f"[startup] Vault indexed: {indexed} new note(s).")
    except Exception as e:
        print(f"[startup] Vault index skipped: {e}")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ReposConfig(BaseModel):
    repos: List[str]

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    include_github: bool = True

class TeamMemberCreate(BaseModel):
    name: str          # display name e.g. "John Smith"
    role: str = ""
    repos: str = ""    # comma-separated

class AssignmentBody(BaseModel):
    title: str
    assignees: List[str] = []  # one or more logins
    due_date: str              # YYYY-MM-DD
    priority: str = "medium"   # low | medium | high
    status: str = "todo"       # todo | in-progress | done
    notes: str = ""


# ---------------------------------------------------------------------------
# Routes1
# ---------------------------------------------------------------------------

@app.post("/api/mock")
def load_mock(_: dict = Depends(auth.require_admin)):
    # Refuse in prod: SEED_DEMO_DATA=false means demo data is intentionally off,
    # so mock data can't sneak back in (e.g. after an ephemeral-DB wipe).
    if not _seed_demo_enabled():
        raise HTTPException(403, "Demo data is disabled (SEED_DEMO_DATA=false).")
    _seed_mock(reset_assignments=True)
    return {"loaded": True, "team_members": len(db.get_team_members())}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "cached_repos": db.get_meta("repos", []),
        "github_configured": bool(os.environ.get("GITHUB_TOKEN")),
    }


@app.get("/api/repos")
def get_repos():
    return {"repos": db.get_meta("repos", [])}


@app.post("/api/repos")
def set_repos(config: ReposConfig, _: dict = Depends(auth.require_manager)):
    db.set_meta("repos", config.repos)
    return {"repos": config.repos}


# ---------------------------------------------------------------------------
# Auth (Microsoft SSO) + users / roles
# ---------------------------------------------------------------------------

@app.get("/api/auth/login")
def auth_login():
    """Kick off Microsoft sign-in; redirects the browser to Microsoft."""
    if not auth.is_configured():
        raise HTTPException(400, "Microsoft sign-in is not configured (set MS_CLIENT_ID / MS_CLIENT_SECRET).")
    state = auth.new_state()
    resp = RedirectResponse(auth.login_url(state))
    # Bind this login attempt to a cookie so the callback can verify it (CSRF).
    resp.set_cookie(auth.OAUTH_STATE_COOKIE, state, **auth.state_cookie_kwargs())
    return resp


@app.get("/api/auth/callback")
def auth_callback(request: Request, code: str = "", state: str = ""):
    """Microsoft redirects here after sign-in. Establish a session, then send
    the user back to the frontend."""
    # CSRF: the state must match the cookie we set when login began.
    if not auth.verify_state(state, request.cookies.get(auth.OAUTH_STATE_COOKIE, "")):
        raise HTTPException(400, "Invalid or expired sign-in state. Please try signing in again.")
    if not code:
        raise HTTPException(400, "Missing authorization code")
    try:
        info = auth.exchange_code(code)
    except Exception as e:
        raise HTTPException(400, f"Login failed: {e}")
    user = auth.login_user(info["email"], info["name"])
    # Unified access: sign-in also connects their mailbox + calendar. Stash the
    # refresh token so the AI can scan their inbox / write events on their behalf.
    if info.get("refresh_token"):
        db.save_email_account(info["email"], info["name"], info["refresh_token"], datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
    if not _seed_demo_enabled():
        _ensure_member_from_inbox(info["email"], info.get("name", ""))
    token = auth.make_session_token(user["email"])
    resp = RedirectResponse(os.environ.get("FRONTEND_URL", "http://localhost:3000"))
    resp.set_cookie(auth.SESSION_COOKIE, token, **auth.cookie_kwargs())
    resp.delete_cookie(auth.OAUTH_STATE_COOKIE, path="/")  # one-time use
    return resp


@app.get("/api/auth/me")
def auth_me(request: Request):
    """Who am I? Drives the frontend's login state."""
    return {
        "user": auth.current_user(request),
        "configured": auth.is_configured(),
        "enforced": auth.auth_enforced(),
    }


@app.post("/api/auth/logout")
def auth_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.SESSION_COOKIE, path="/")
    return resp


class DevLogin(BaseModel):
    email: str
    name: str = ""
    role: str = "L3"  # L1 | L2 | L3


@app.post("/api/auth/dev-login")
def auth_dev_login(body: DevLogin):
    """Local-only shortcut to get a session without Microsoft. Disabled whenever
    auth is enforced, so it can't be used to bypass real auth in prod — even if
    SSO isn't configured yet (which would otherwise leave this wide open)."""
    if auth.auth_enforced():
        raise HTTPException(403, "Dev login is disabled when auth is enforced.")
    if body.role not in auth.ROLES:
        raise HTTPException(400, f"role must be one of {auth.ROLES}")
    user = db.upsert_user(email=body.email.strip().lower(), name=body.name or body.email, role=body.role)
    token = auth.make_session_token(user["email"])
    resp = JSONResponse({"user": user})
    resp.set_cookie(auth.SESSION_COOKIE, token, **auth.cookie_kwargs())
    return resp


@app.get("/api/users")
def list_users(_: dict = Depends(auth.require_manager)):
    return {"users": db.list_users()}


class RoleUpdate(BaseModel):
    role: str  # L1 | L2 | L3


@app.put("/api/users/{email}/role")
def set_user_role(email: str, body: RoleUpdate, actor: dict = Depends(auth.require_manager)):
    if body.role not in auth.ROLES:
        raise HTTPException(400, f"role must be one of {auth.ROLES}")
    target = email.strip().lower()
    if target == (actor.get("email") or "").lower():
        raise HTTPException(403, "You can't change your own role.")
    # You may only assign a level strictly below your own (L3→≤L2, L2→L1).
    if not auth.can_grant(actor["role"], body.role):
        raise HTTPException(403, f"As {actor['role']} you can only assign roles below your own level.")
    # And you can't touch someone already at or above your own level.
    existing = db.get_user(target)
    if existing and not auth.can_grant(actor["role"], existing["role"]):
        raise HTTPException(403, "You can't change the role of someone at or above your level.")
    user = db.set_user_role(target, body.role)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


class ManagerUpdate(BaseModel):
    manager_email: str  # who this person reports to ("" = no manager)


@app.put("/api/users/{email}/manager")
def set_user_manager(email: str, body: ManagerUpdate, _: dict = Depends(auth.require_admin)):
    user = db.set_user_manager(email.strip().lower(), body.manager_email.strip().lower())
    if user is None:
        raise HTTPException(404, "User not found")
    return user


@app.post("/api/sync")
def sync(config: Optional[ReposConfig] = None, _: dict = Depends(auth.require_manager)):
    repos = (config.repos if config else None) or db.get_meta("repos", [])
    if not repos:
        raise HTTPException(400, "No repos configured. POST /api/repos first.")
    client = _gh()
    try:
        data = client.aggregate_team_data(repos)
    finally:
        client.close()

    # Safety: a real sync always returns at least one project. If we got nothing,
    # the fetch failed (no GITHUB_TOKEN, or private/nonexistent repos) — do NOT
    # overwrite existing data with empties (that wipes the dashboard). Bail loudly.
    if not data["projects"] and not data["team_members"]:
        raise HTTPException(
            502,
            "GitHub sync returned no data — check that GITHUB_TOKEN is set and the "
            "repos are accessible. Your existing data was left unchanged.",
        )

    # GitHub is the source of truth on a successful sync — replace team + snapshot
    db.replace_team_members(data["team_members"])
    db.set_meta("github_snapshot", {
        "projects":      data["projects"],
        "issues":        data["issues"],
        "pull_requests": data["pull_requests"],
    })
    db.set_meta("repos", repos)
    return {
        "synced_repos": repos,
        "team_members": len(data["team_members"]),
        "open_issues": len(data["issues"]),
        "open_prs": len(data["pull_requests"]),
    }


ASSIGNMENT_WEIGHT = {"high": 5, "medium": 3, "low": 1}


def _team_with_workload() -> list[dict]:
    """Team members with workload_score derived from active assignments.
    The stored base score is 0 — load comes entirely from assigned, non-done
    work — so this must be applied wherever team data is consumed (dashboard
    AND the AI context), or workload reads as 0."""
    extra: dict = {}
    for a in db.get_assignments():
        if a.get("assignees") and a.get("status") != "done":
            w = ASSIGNMENT_WEIGHT.get(a.get("priority", "medium"), 3)
            for login in a["assignees"]:
                extra[login] = extra.get(login, 0) + w

    members = []
    for m in db.get_team_members():
        mc = m.copy()
        mc["workload_score"] = round(m.get("workload_score", 0) + extra.get(m["login"], 0), 1)
        members.append(mc)

    members.sort(key=lambda m: m["workload_score"], reverse=True)
    return members

@app.get("/api/team")
def get_team(request: Request):
    if not db.get_team_members() and _data_snapshot() is None:
        raise HTTPException(400, "No data synced yet. POST /api/sync to fetch GitHub data first.")
    members = _team_with_workload()
    vis = visibility.scope_for(request)
    if vis is not None:
        members = [m for m in members if m["login"] in vis]
    return {"team_members": members}


@app.post("/api/team/member")
def add_member(body: TeamMemberCreate, _: dict = Depends(auth.require_manager)):
    login = body.name.strip().lower().replace(" ", "_")
    if db.member_exists(login):
        raise HTTPException(400, f"Member '{login}' already exists")
    repos = [r.strip() for r in body.repos.split(",") if r.strip()]
    member = {
        "login": login,
        "role": body.role,
        "email": f"{login.replace('_', '.')}@kneron.us",
        "open_issues": 0, "open_prs": 0, "recent_commits": 0,
        "repos_active": repos,
        "workload_score": 0.0,
    }
    db.add_team_member(member)
    return member


@app.delete("/api/team/member/{login}")
def remove_member(login: str, _: dict = Depends(auth.require_manager)):
    if not db.delete_team_member(login):
        raise HTTPException(404, "Member not found")
    return {"deleted": login}


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

@app.get("/api/assignments")
def get_assignments(request: Request):
    items = db.get_assignments()
    vis = visibility.scope_for(request)
    if vis is not None:
        manage = visibility.can_manage(request)
        # See a task if you're on it; managers also see unassigned tasks they can hand out.
        items = [
            a for a in items
            if (set(a.get("assignees", [])) & vis) or (manage and not a.get("assignees"))
        ]
    return {"assignments": items}


def _notify_assignees(assignees: List[str], subject: str, message: str):
    """Best-effort ping to each assigned person, looked up via their team email."""
    by_login = {m["login"]: m for m in db.get_team_members()}
    for login in assignees:
        m = by_login.get(login)
        if m and m.get("email"):
            notifications.notify({"email": m["email"], "name": login}, subject, message)


@app.post("/api/assignments")
def create_assignment(body: AssignmentBody, actor: dict = Depends(auth.require_manager)):
    a = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        **body.model_dump(),
    }
    db.add_assignment(a)
    if a["assignees"]:
        _notify_assignees(a["assignees"], "New task assigned",
                          f"{a['title']} — due {a.get('due_date') or 'TBD'} ({a.get('priority')} priority)")
    return a


@app.put("/api/assignments/{aid}")
def update_assignment(aid: str, body: AssignmentBody, actor: dict = Depends(auth.require_manager)):
    updated = db.update_assignment(aid, body.model_dump())
    if updated is None:
        raise HTTPException(404, "Assignment not found")
    return updated


class AssignWorkers(BaseModel):
    assignees: List[str]  # list of logins; empty list = unassign all

@app.patch("/api/assignments/{aid}/assign")
def assign_workers(aid: str, body: AssignWorkers, actor: dict = Depends(auth.require_manager)):
    a = db.get_assignment(aid)
    if a is None:
        raise HTTPException(404, "Assignment not found")
    fields = {"assignees": body.assignees}
    # Auto-set status based on whether anyone is assigned
    if body.assignees and a.get("status") == "todo":
        fields["status"] = "in-progress"
    elif not body.assignees and a.get("status") == "in-progress":
        fields["status"] = "todo"
    updated = db.update_assignment(aid, fields)
    newly_added = [x for x in body.assignees if x not in a.get("assignees", [])]
    if newly_added:
        _notify_assignees(newly_added, "Task assigned to you",
                          f"{a['title']} — due {a.get('due_date') or 'TBD'}")
    return updated


@app.delete("/api/assignments/{aid}")
def delete_assignment(aid: str, actor: dict = Depends(auth.require_manager)):
    if not db.delete_assignment(aid):
        raise HTTPException(404, "Assignment not found")
    return {"deleted": aid}


@app.get("/api/projects")
def get_projects():
    _require_data()
    return {"projects": _data_snapshot()["projects"]}


@app.get("/api/roadmap")
def get_roadmap():
    _require_data()
    milestones = []
    for project in _data_snapshot()["projects"]:
        for ms in project.get("milestones", []):
            milestones.append({**ms, "repo": project["repo"]})
    milestones.sort(key=lambda m: (m.get("due_on") or "9999"))
    return {"milestones": milestones}


PRIORITY_RANK = {"blocker": 4, "priority-high": 3, "bug": 2, "priority-medium": 1}


@app.get("/api/priorities")
def get_priorities():
    _require_data()

    def score(issue):
        return max(
            (PRIORITY_RANK.get(lb.lower(), 0) for lb in issue.get("labels", [])),
            default=0,
        )

    issues = sorted(_data_snapshot()["issues"], key=score, reverse=True)
    return {"priorities": issues}


@app.get("/api/summary")
def get_summary(request: Request):
    _require_data()
    agent = _pm()
    try:
        summary = agent.summarize_status(_scoped_data(request))
    except Exception as e:
        raise HTTPException(502, f"AI call failed: {str(e)[:300]}")
    return {"summary": summary}


@app.get("/api/graph")
def get_graph(request: Request):
    """Knowledge graph for the dashboard: people, projects, tasks and reports as
    nodes; relationships (assigned-to, works-on, mentioned-in, [[links]]) as edges.
    Role-scoped — you only see your slice when auth is enforced."""
    vis = visibility.scope_for(request)              # None = see everyone
    members = _team_with_workload()
    if vis is not None:
        members = [m for m in members if m["login"] in vis]
    visible = {m["login"] for m in members}
    snap = _data_snapshot() or {}
    projects = snap.get("projects", [])
    try:
        all_notes = _notes.list_all()
    except Exception:
        all_notes = []
    emails  = [n for n in all_notes if n.get("note_type") == "email"][:12]
    reports = [n for n in all_notes if n.get("note_type") != "email"][:8]
    notes   = emails + reports

    nodes, edges = [], []
    ids, edge_keys = set(), set()

    def node(nid, label, ntype, val=1.0):
        if nid not in ids:
            ids.add(nid)
            nodes.append({"id": nid, "label": label, "type": ntype, "val": round(val, 1)})

    def edge(a, b):
        if a == b or a not in ids or b not in ids:
            return
        key = tuple(sorted((a, b)))
        if key not in edge_keys:
            edge_keys.add(key)
            edges.append({"source": a, "target": b})

    for m in members:
        node("p:" + m["login"], m["login"], "person", 1 + m.get("workload_score", 0) / 10)
    for p in projects:
        node("proj:" + p["repo"], p["repo"].split("/")[-1], "project", 2)
    for m in members:                                # works-on
        for repo in m.get("repos_active", []):
            edge("p:" + m["login"], "proj:" + repo)

    count = 0                                        # assigned-to
    for a in db.get_assignments():
        if a.get("status") == "done" or count >= 20:
            continue
        if vis is not None and not (set(a.get("assignees", [])) & visible):
            continue
        node("t:" + a["id"], a["title"], "task")
        count += 1
        for x in a.get("assignees", []):
            edge("p:" + x, "t:" + a["id"])

    by_addr = {(m.get("email") or "").lower(): m for m in members if m.get("email")}
    nid_of = lambda n2: ("e:" if n2.get("note_type") == "email" else "n:") + n2["id"]

    def link_people(nid, blob):
        for addr, m in by_addr.items():              # exact email-address match
            if addr and addr in blob:
                edge(nid, "p:" + m["login"])
        for m in members:                            # name / login mention
            parts = [w for w in m["login"].lower().replace("_", " ").split() if len(w) > 2]
            if parts and all(w in blob for w in parts):
                edge(nid, "p:" + m["login"])

    for n in emails:                                 # emails the agent has read
        nid = "e:" + n["id"]
        subj = n.get("title", "").replace("Email: ", "", 1)[:34] or "(email)"
        node(nid, subj, "email")
        link_people(nid, (n.get("title", "") + " " + n.get("content", "")).lower())

    for n in reports:                                # reports / notes (Obsidian layer)
        nid = "n:" + n["id"]
        node(nid, n["title"][:34], "report")
        blob = (n.get("title", "") + " " + n.get("content", "")).lower()
        link_people(nid, blob)
        for tgt in re.findall(r"\[\[([^\]]+)\]\]", n.get("content", "")):   # [[wikilinks]]
            for n2 in notes:
                if n2["id"] != n["id"] and tgt.lower() in n2["title"].lower():
                    edge(nid, nid_of(n2))

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Personal email → tasks → calendar (for the signed-in user)
# ---------------------------------------------------------------------------

def _login_for_email(email: str) -> Optional[str]:
    """Map a person's email to their team-member login (for their task board)."""
    el = (email or "").lower()
    for m in db.get_team_members():
        if (m.get("email") or "").lower() == el:
            return m["login"]
    return None


def _user_access_token(user: dict) -> str:
    """Fresh Microsoft Graph access token for the signed-in user, from the
    refresh token captured at login."""
    acct = db.get_email_account(user["email"])
    if not acct or not acct.get("refresh_token"):
        raise HTTPException(400, "Your inbox isn't connected. Sign in with Microsoft to grant mail + calendar access.")
    try:
        return email_client.refresh_access_token(acct["refresh_token"])
    except Exception as e:
        raise HTTPException(401, f"Microsoft access expired — please sign in again. ({e})")


@app.get("/api/me/inbox")
def my_inbox_status(user: dict = Depends(auth.require_user)):
    acct = db.get_email_account(user["email"])
    return {
        "connected":   bool(acct and acct.get("refresh_token")),
        "email":       user.get("email", ""),
        "last_synced": (acct or {}).get("last_synced", ""),
    }


@app.post("/api/me/scan")
def scan_my_inbox(user: dict = Depends(auth.require_user)):
    """Read the signed-in user's recent mail and PROPOSE calendar-worthy tasks/
    events. Writes nothing — the user confirms before anything lands."""
    token = _user_access_token(user)
    try:
        messages = email_client.fetch_recent_messages(token, top=25)
    except Exception as e:
        raise HTTPException(502, f"Couldn't read your inbox: {e}")
    # Drop automated/promotional noise so the extractor isn't diluted by it.
    NOISE = ("no-reply", "noreply", "donotreply", "promomail", "newsletter",
             "notifications@", "mailer", "updates@", "@promo")
    messages = [m for m in messages if not any(t in (m.get("from") or "").lower() for t in NOISE)]
    if not messages:
        return {"proposals": [], "scanned": 0}
    emails_text = "\n\n".join(
        f"Subject: {m['subject']}\nFrom: {m['from']}\nReceived: {m['received']}\n{m['preview']}"
        for m in messages
    )
    today = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")
    raw = _pm().extract_events(emails_text, today)
    # Keep only well-formed, confident events; normalise nulls the small model
    # sometimes emits so the confirm step always gets valid strings.
    proposals = [
        {
            "title": p["title"],
            "start": p["start"],
            "end": p.get("end") or "",
            "attendees": p.get("attendees") or [],
            "source_subject": p.get("source_subject") or "",
        }
        for p in raw
        if p.get("title") and p.get("start") and p.get("confidence", 1) >= 0.5
    ]
    db.set_email_synced(user["email"], datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
    return {"proposals": proposals, "scanned": len(messages)}


class ProposedEvent(BaseModel):
    title: str
    start: str                       # 'YYYY-MM-DDTHH:MM:SS'
    end: str = ""
    attendees: List[str] = []
    source_subject: str = ""
    add_to_board: bool = True        # also create a task on their board


class ConfirmEvents(BaseModel):
    events: List[ProposedEvent]


@app.post("/api/me/calendar/confirm")
def confirm_my_events(body: ConfirmEvents, user: dict = Depends(auth.require_user)):
    """Land approved events on the app's OWN calendar/board (always — needs no
    Microsoft permission). Also mirror to the user's Outlook calendar when the
    Calendars.ReadWrite consent is available; if it isn't, the in-app calendar
    still gets the event so the feature works without admin consent."""
    my_login = _login_for_email(user["email"])
    # Best-effort Outlook token; may lack the calendar scope (or no inbox) — fine.
    try:
        token = _user_access_token(user)
    except Exception:
        token = None

    results = []
    for ev in body.events:
        end = ev.end or ev.start
        # assignees = the signed-in user + any attendees who are on the team
        assignees = []
        if my_login:
            assignees.append(my_login)
        for addr in ev.attendees:
            login = _login_from_email(addr)
            if login != my_login and db.member_exists(login):
                assignees.append(login)

        # 1) Always write to the in-app calendar (a dated board item).
        db.add_assignment({
            "id":         str(uuid.uuid4()),
            "title":      ev.title,
            "assignees":  assignees,
            "due_date":   (ev.start or "")[:10],
            "priority":   "medium",
            "status":     "in-progress",
            "notes":      f"From email: {ev.source_subject}",
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        })

        # 2) Best-effort mirror to Outlook (silently skipped if no calendar consent).
        web_link, outlook_error = None, None
        if token:
            try:
                # Personal calendar block only — no attendees, so Outlook does
                # NOT email a meeting invite to anyone. Co-workers are recorded
                # as assignees on the in-app board above.
                created = email_client.create_calendar_event(
                    token, subject=ev.title, start_iso=ev.start, end_iso=end,
                    body=f"Added by PM Agent from email: {ev.source_subject}",
                )
                web_link = created.get("webLink")
            except Exception as e:
                outlook_error = str(e)[:120]

        results.append({
            "title": ev.title, "ok": True, "onAppCalendar": True,
            "outlookSynced": bool(web_link), "webLink": web_link,
            "outlookError": outlook_error,
        })
    return {"results": results}


def _chat_context(req: ChatRequest, request: Request):
    github_context = _scoped_data(request) if req.include_github else None
    history = [{"role": m.role, "content": m.content} for m in req.history] if req.history else None
    # RAG: search past notes for anything relevant to the question...
    try:
        notes_context = _notes.search(req.message, n=3)
    except Exception:
        notes_context = []
    # ...then always fold in the most recent reports/notes, so the AI references
    # past Obsidian reports even when semantic search finds nothing (or embeddings
    # are unavailable). Dedupe by title, cap the total.
    try:
        recent = _notes.list_all()[:3]
    except Exception:
        recent = []
    seen = {n["title"] for n in notes_context}
    for n in recent:
        if n["title"] not in seen:
            notes_context.append(n)
            seen.add(n["title"])
    notes_context = notes_context[:5]
    return github_context, history, notes_context


@app.post("/api/chat")
def chat(req: ChatRequest, request: Request, _: dict = Depends(auth.require_user)):
    agent = _pm()
    github_context, history, notes_context = _chat_context(req, request)
    try:
        response = agent.chat(
            user_message=req.message,
            github_context=github_context,
            conversation_history=history,
            notes_context=notes_context,
        )
    except Exception as e:
        # Surface the provider's real error (rate limit, context too long, bad
        # key, …) instead of a blank 500 — critical for diagnosing prod.
        raise HTTPException(502, f"AI call failed: {str(e)[:300]}")
    return {"response": response}


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest, request: Request, _: dict = Depends(auth.require_user)):
    agent = _pm()
    github_context, history, notes_context = _chat_context(req, request)

    def generate():
        for chunk in agent.stream_chat(
            user_message=req.message,
            github_context=github_context,
            conversation_history=history,
            notes_context=notes_context,
        ):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Notes / Reports (RAG store)
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    title: str
    content: str
    note_type: str = "report"  # report | summary | note


@app.get("/api/notes")
def get_notes(_: dict = Depends(auth.require_user)):
    return {"notes": _notes.list_all()}


@app.post("/api/notes")
def save_note(body: NoteCreate, _: dict = Depends(auth.require_user)):
    note = _notes.save(title=body.title, content=body.content, note_type=body.note_type)
    return note


SCOPE_LABEL = {
    "week": "this week", "month": "this month", "quarter": "this quarter",
    "year": "this year", "all": "overall",
}


class ReportRequest(BaseModel):
    prompt: str = ""        # optional free-text ask ("my tasks due this week", etc.)
    scope: str = "all"      # week | month | quarter | year | all


def _report_instruction(req: "ReportRequest", role: str) -> str:
    """Build the report ask — scoped by timeframe and tailored to the role."""
    today = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")
    scope_txt = SCOPE_LABEL.get(req.scope, "overall")
    if role == "L1":
        focus = (
            "Focus on MY tasks and deadlines: what I need to do, what is due soon or "
            "overdue, and how I should prioritize. Pull from the assignment board (my "
            "tasks, with due dates synced from my calendar and email)."
        )
    elif role in ("L2", "L3"):
        focus = (
            "Give a team overview: workload balance, who is overloaded vs. who has "
            "capacity, at-risk or overdue deadlines, and concrete recommendations for "
            "how to divvy out or rebalance tasks so the team runs more efficiently."
        )
    else:
        focus = "Summarize current status, the biggest risks, and the top next actions."
    custom = (
        f' The reader specifically asked: "{req.prompt.strip()}". Answer that directly.'
        if req.prompt.strip() else ""
    )
    return (
        f"Today is {today}. Write a focused status report scoped to {scope_txt}. {focus} "
        f"Use the team data, the live assignment board (tasks + due dates from calendar/email), "
        f"and milestones provided. Be specific — name people, task titles, and dates. "
        f"Use clear bullet points.{custom}"
    )


def _report_title(req: "ReportRequest") -> str:
    stamp = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")
    if req.prompt.strip():
        head = req.prompt.strip()
        head = (head[:48] + "…") if len(head) > 48 else head
        return f"{head} — {stamp} UTC"
    return f"Status report ({SCOPE_LABEL.get(req.scope, 'overall').capitalize()}) — {stamp} UTC"


@app.post("/api/notes/generate")
def generate_and_save(request: Request, req: Optional[ReportRequest] = None, _: dict = Depends(auth.require_user)):
    """Non-streaming fallback — prefer /api/notes/generate/stream."""
    _require_data()
    req = req or ReportRequest()
    agent = _pm()
    role = (auth.current_user(request) or {}).get("role") or "L3"
    try:
        content = agent.chat(_report_instruction(req, role), github_context=_scoped_data(request))
    except Exception as e:
        raise HTTPException(502, f"AI call failed: {str(e)[:300]}")
    title = _report_title(req)
    note = _notes.save(title=title, content=content, note_type="report")
    try:
        write_note(title=title, content=content, note_type="report")
    except Exception as e:
        print(f"[vault] Could not write to vault: {e}")
    return note


@app.post("/api/notes/generate/stream")
def generate_and_save_stream(request: Request, req: Optional[ReportRequest] = None, _: dict = Depends(auth.require_user)):
    """Stream a prompt-driven, role-aware, scoped report; then save it."""
    _require_data()
    req = req or ReportRequest()
    agent = _pm()
    role = (auth.current_user(request) or {}).get("role") or "L3"
    title = _report_title(req)
    data = _scoped_data(request)            # only what this person may see
    instruction = _report_instruction(req, role)

    chunks_collected: list[str] = []

    def generate():
        for chunk in agent.stream_chat(user_message=instruction, github_context=data):
            chunks_collected.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        content = "".join(chunks_collected)
        try:
            _notes.save(title=title, content=content, note_type="report")
            write_note(title=title, content=content, note_type="report")
        except Exception as e:
            print(f"[notes] Save error: {e}")

        yield f"data: {json.dumps({'done': True, 'title': title})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/notes/save-to-vault/{note_id}")
def save_existing_to_vault(note_id: str, _: dict = Depends(auth.require_manager)):
    """Push an existing note from ChromaDB into the Obsidian vault."""
    all_notes = _notes.list_all()
    note = next((n for n in all_notes if n["id"] == note_id), None)
    if not note:
        raise HTTPException(404, "Note not found")
    try:
        path = write_note(title=note["title"], content=note["content"], note_type=note.get("type", "note"))
        return {"path": str(path)}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/vault/sync")
def sync_vault(_: dict = Depends(auth.require_manager)):
    """Scan the Obsidian vault and index any new .md files into ChromaDB."""
    vault_notes = scan_vault()
    indexed = 0
    skipped = 0
    existing_titles = {n["title"] for n in _notes.list_all()}

    for vn in vault_notes:
        if vn["title"] in existing_titles:
            skipped += 1
            continue
        try:
            _notes.save(
                title     = vn["title"],
                content   = vn["content"],
                note_type = vn.get("type", "note"),
            )
            indexed += 1
        except Exception as e:
            print(f"[vault] Failed to index {vn['title']}: {e}")

    return {"indexed": indexed, "skipped": skipped, "total_in_vault": len(vault_notes)}


@app.get("/api/vault/status")
def vault_status():
    vault_notes = scan_vault()
    return {
        "vault_path": str(__import__("vault_client").VAULT_PATH),
        "total_notes": len(vault_notes),
        "notes": [{"title": n["title"], "type": n["type"], "created_at": n["created_at"]} for n in vault_notes],
    }


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: str, _: dict = Depends(auth.require_manager)):
    _notes.delete(note_id)
    return {"deleted": note_id}


# ---------------------------------------------------------------------------
# Email integration (Microsoft 365 — each user connects their own inbox)
# ---------------------------------------------------------------------------

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


@app.get("/api/email/status")
def email_status(user: dict = Depends(auth.require_user)):
    """Whether email is configured + which accounts are connected. Any signed-in
    user can read this (so they see their own inbox); non-managers only see their
    own account, managers/admins see the whole connected pool."""
    accounts = db.list_email_accounts()
    if auth.auth_enforced() and user.get("role") not in ("L2", "L3"):
        own = (user.get("email") or "").lower()
        accounts = [a for a in accounts if a["email"].lower() == own]
    return {
        "configured": email_client.is_configured(),
        "accounts": accounts,
    }


@app.get("/api/email/connect")
def email_connect(_: dict = Depends(auth.require_admin)):
    """Return the Microsoft sign-in URL for the user to grant inbox access."""
    if not email_client.is_configured():
        raise HTTPException(400, "Email is not configured. Set MS_CLIENT_ID / MS_CLIENT_SECRET.")
    state = auth.new_state()
    resp = JSONResponse({"auth_url": email_client.auth_url(state=state)})
    # Bind to a cookie so the callback can verify (CSRF) — same pattern as login.
    resp.set_cookie(auth.OAUTH_STATE_COOKIE, state, **auth.state_cookie_kwargs())
    return resp


@app.get("/api/email/callback")
def email_callback(request: Request, code: str = "", state: str = "", error: str = "", error_description: str = ""):
    """Microsoft redirects here after the user signs in. Exchange + store the token."""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/email?error={error}")
    if not auth.verify_state(state, request.cookies.get(auth.OAUTH_STATE_COOKIE, "")):
        return RedirectResponse(f"{FRONTEND_URL}/email?error=invalid_state")
    if not code:
        return RedirectResponse(f"{FRONTEND_URL}/email?error=missing_code")
    try:
        tok = email_client.exchange_code(code)
        db.save_email_account(
            email=tok["email"], name=tok["name"],
            refresh_token=tok["refresh_token"],
            connected_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        )
        if not _seed_demo_enabled():
            _ensure_member_from_inbox(tok["email"], tok.get("name", ""))
        resp = RedirectResponse(f"{FRONTEND_URL}/email?connected={tok['email']}")
        resp.delete_cookie(auth.OAUTH_STATE_COOKIE, path="/")  # one-time use
        return resp
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/email?error={str(e)[:100]}")


@app.post("/api/email/sync")
def email_sync(_: dict = Depends(auth.require_admin)):
    """Pull recent emails from every connected inbox into the RAG store
    so the AI chat can reference them."""
    if not email_client.is_configured():
        raise HTTPException(400, "Email is not configured.")
    accounts = db.get_all_email_accounts_full()
    if not accounts:
        raise HTTPException(400, "No inboxes connected yet.")

    total = 0
    errors = []
    for acct in accounts:
        try:
            access = email_client.refresh_access_token(acct["refresh_token"])
            messages = email_client.fetch_recent_messages(access, top=20)
            for m in messages:
                title   = f"Email: {m['subject']}"
                content = (
                    f"From: {m['from_name']} <{m['from']}>\n"
                    f"Received: {m['received']}\n"
                    f"To inbox: {acct['email']}\n\n{m['preview']}"
                )
                _notes.save(title=title, content=content, note_type="email")
                total += 1
            db.set_email_synced(acct["email"], datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
        except Exception as e:
            errors.append(f"{acct['email']}: {str(e)[:80]}")

    return {"synced_emails": total, "accounts": len(accounts), "errors": errors}


@app.delete("/api/email/accounts/{email}")
def email_disconnect(email: str, _: dict = Depends(auth.require_admin)):
    if not db.delete_email_account(email):
        raise HTTPException(404, "Account not connected")
    return {"disconnected": email}


# ---------------------------------------------------------------------------
# Email → Calendar (scan inboxes → AI proposes events → write to Outlook)
# ---------------------------------------------------------------------------

class ProposedEvent(BaseModel):
    title: str
    start: str                 # local ISO, e.g. 2026-06-20T14:00:00
    end: str
    attendees: List[str] = []
    source_subject: str = ""
    body: str = ""


class CalendarCreateBody(BaseModel):
    inbox: str                 # which connected account's calendar to write to
    events: List[ProposedEvent]
    timezone: str = "Asia/Taipei"


@app.post("/api/email/scan-to-events")
def scan_emails_to_events(_: dict = Depends(auth.require_admin)):
    """Scan every connected inbox and have the AI propose calendar events.
    Returns proposals for review — deliberately does NOT create anything yet."""
    if not email_client.is_configured():
        raise HTTPException(400, "Email is not configured.")
    accounts = db.get_all_email_accounts_full()
    if not accounts:
        raise HTTPException(400, "No inboxes connected yet.")

    agent = _pm()
    today = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")
    proposals, errors = [], []
    for acct in accounts:
        try:
            access   = email_client.refresh_access_token(acct["refresh_token"])
            messages = email_client.fetch_recent_messages(access, top=20)
            text = "\n\n".join(
                f"Subject: {m['subject']}\nFrom: {m['from']}\nReceived: {m['received']}\n{m['preview']}"
                for m in messages
            )
            for ev in agent.extract_events(text, today_iso=today):
                ev["inbox"] = acct["email"]
                proposals.append(ev)
        except Exception as e:
            errors.append(f"{acct['email']}: {str(e)[:80]}")

    return {"proposed_events": proposals, "accounts": len(accounts), "errors": errors}


@app.post("/api/calendar/create")
def create_calendar_events(body: CalendarCreateBody, _: dict = Depends(auth.require_admin)):
    """Create the (reviewed) events on the connected account's Microsoft calendar."""
    if not email_client.is_configured():
        raise HTTPException(400, "Email is not configured.")
    acct = db.get_email_account(body.inbox)
    if not acct or not acct.get("refresh_token"):
        raise HTTPException(404, f"Inbox '{body.inbox}' is not connected.")

    access = email_client.refresh_access_token(acct["refresh_token"])
    created, errors = [], []
    for ev in body.events:
        try:
            # Personal calendar block only — no attendees, so no invite emails.
            res = email_client.create_calendar_event(
                access_token=access,
                subject=ev.title,
                start_iso=ev.start,
                end_iso=ev.end,
                body=ev.body or f"Created by PM Agent from email: {ev.source_subject}",
                timezone=body.timezone,
            )
            created.append(res)
        except Exception as e:
            errors.append(f"{ev.title}: {str(e)[:80]}")

    return {"created": created, "errors": errors}
