import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel

load_dotenv()

from github_client import GitHubClient
from pm_agent import ProgramManagerAgent
from notes_store import NotesStore
from vault_client import write_note, scan_vault
import db
import email_client

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
        {"number": 312, "title": "API gateway crashes under sustained 5k rps load", "url": "#", "state": "open", "labels": ["blocker", "performance"], "assignees": ["nolan_chen"], "created_at": "2026-05-20T10:00:00Z", "updated_at": "2026-05-30T09:00:00Z", "repo": "kneron/backend-api"},
        {"number": 289, "title": "OAuth token refresh fails after 1hr expiry", "url": "#", "state": "open", "labels": ["bug", "priority-high", "auth"], "assignees": ["julia_aquino"], "created_at": "2026-05-18T08:00:00Z", "updated_at": "2026-05-29T14:00:00Z", "repo": "kneron/backend-api"},
        {"number": 76,  "title": "App crashes on iOS 17.4 when camera permission denied", "url": "#", "state": "open", "labels": ["bug", "priority-high", "ios"], "assignees": ["bobby_lee"], "created_at": "2026-05-22T11:00:00Z", "updated_at": "2026-05-31T10:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 301, "title": "Rate limiter doesn't reset correctly on rolling window", "url": "#", "state": "open", "labels": ["bug", "priority-high"], "assignees": ["nolan_chen"], "created_at": "2026-05-25T09:00:00Z", "updated_at": "2026-05-31T08:00:00Z", "repo": "kneron/backend-api"},
        {"number": 45,  "title": "KL720 inference latency spikes to 30ms on large batches", "url": "#", "state": "open", "labels": ["priority-high", "performance"], "assignees": ["deez_nuts"], "created_at": "2026-05-21T13:00:00Z", "updated_at": "2026-05-28T16:00:00Z", "repo": "kneron/ml-pipeline"},
        {"number": 88,  "title": "Push notifications silently dropped on Android 14", "url": "#", "state": "open", "labels": ["bug", "priority-medium", "android"], "assignees": ["bobby_lee", "albert_liu"], "created_at": "2026-05-19T15:00:00Z", "updated_at": "2026-05-27T11:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 315, "title": "Add Prometheus metrics endpoint /metrics", "url": "#", "state": "open", "labels": ["enhancement", "priority-medium", "observability"], "assignees": ["albert_liu"], "created_at": "2026-05-26T10:00:00Z", "updated_at": "2026-05-30T12:00:00Z", "repo": "kneron/backend-api"},
        {"number": 92,  "title": "Onboarding flow skips step 3 for new Android users", "url": "#", "state": "open", "labels": ["bug", "priority-medium"], "assignees": ["chuddington_chad"], "created_at": "2026-05-24T09:00:00Z", "updated_at": "2026-05-29T10:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 48,  "title": "Add quantisation support for INT4 models", "url": "#", "state": "open", "labels": ["enhancement", "priority-medium"], "assignees": ["deez_nuts", "jenna_wu"], "created_at": "2026-05-23T14:00:00Z", "updated_at": "2026-05-28T15:00:00Z", "repo": "kneron/ml-pipeline"},
        {"number": 320, "title": "Write API v2 migration guide for external devs", "url": "#", "state": "open", "labels": ["documentation"], "assignees": ["julia_aquino"], "created_at": "2026-05-27T11:00:00Z", "updated_at": "2026-05-31T09:00:00Z", "repo": "kneron/backend-api"},
    ],
    "pull_requests": [
        {"number": 334, "title": "fix: patch rolling-window rate limiter reset logic", "url": "#", "state": "open", "author": "nolan_chen", "assignees": ["julia_aquino"], "created_at": "2026-05-30T10:00:00Z", "updated_at": "2026-05-31T08:00:00Z", "repo": "kneron/backend-api", "draft": False},
        {"number": 335, "title": "feat: add /metrics Prometheus endpoint", "url": "#", "state": "open", "author": "albert_liu", "assignees": ["nolan_chen"], "created_at": "2026-05-29T14:00:00Z", "updated_at": "2026-05-30T11:00:00Z", "repo": "kneron/backend-api", "draft": False},
        {"number": 97,  "title": "fix: camera permission crash on iOS 17.4", "url": "#", "state": "open", "author": "bobby_lee", "assignees": ["julia_aquino"], "created_at": "2026-05-31T09:00:00Z", "updated_at": "2026-05-31T10:00:00Z", "repo": "kneron/mobile-app", "draft": False},
        {"number": 98,  "title": "fix: android push notification delivery", "url": "#", "state": "open", "author": "chuddington_chad", "assignees": ["bobby_lee"], "created_at": "2026-05-28T16:00:00Z", "updated_at": "2026-05-29T09:00:00Z", "repo": "kneron/mobile-app", "draft": True},
        {"number": 52,  "title": "perf: optimise batch inference loop for KL720", "url": "#", "state": "open", "author": "deez_nuts", "assignees": ["jenna_wu"], "created_at": "2026-05-30T13:00:00Z", "updated_at": "2026-05-31T07:00:00Z", "repo": "kneron/ml-pipeline", "draft": False},
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
    """Assemble the complete data dict (team from DB + snapshot) for AI context / dashboards."""
    snap = _data_snapshot()
    if snap is None:
        return None
    return {"team_members": _team_with_workload(), **snap}


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
    today = datetime.utcnow()
    due_offset = {"high": 2, "medium": 7, "low": 14}
    for idx, issue in enumerate(MOCK_DATA["issues"]):
        p = _issue_priority(issue["labels"])
        due = (today + timedelta(days=due_offset[p] + (idx % 5))).strftime("%Y-%m-%d")
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


@app.on_event("startup")
def startup():
    """Init the database. Seed demo data only on a fresh, empty DB —
    existing data is preserved across restarts."""
    db.init_db()
    if not db.get_team_members() and _data_snapshot() is None:
        _seed_mock(reset_assignments=True)
        print("[startup] Fresh DB — demo data seeded.")
    else:
        print("[startup] Existing data found — loaded from database.")


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
def load_mock():
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
def set_repos(config: ReposConfig):
    db.set_meta("repos", config.repos)
    return {"repos": config.repos}


@app.post("/api/sync")
def sync(config: Optional[ReposConfig] = None):
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
def get_team():
    if not db.get_team_members() and _data_snapshot() is None:
        raise HTTPException(400, "No data synced yet. POST /api/sync to fetch GitHub data first.")
    return {"team_members": _team_with_workload()}


@app.post("/api/team/member")
def add_member(body: TeamMemberCreate):
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
def remove_member(login: str):
    if not db.delete_team_member(login):
        raise HTTPException(404, "Member not found")
    return {"deleted": login}


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

@app.get("/api/assignments")
def get_assignments():
    return {"assignments": db.get_assignments()}


@app.post("/api/assignments")
def create_assignment(body: AssignmentBody):
    a = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        **body.model_dump(),
    }
    db.add_assignment(a)
    return a


@app.put("/api/assignments/{aid}")
def update_assignment(aid: str, body: AssignmentBody):
    updated = db.update_assignment(aid, body.model_dump())
    if updated is None:
        raise HTTPException(404, "Assignment not found")
    return updated


class AssignWorkers(BaseModel):
    assignees: List[str]  # list of logins; empty list = unassign all

@app.patch("/api/assignments/{aid}/assign")
def assign_workers(aid: str, body: AssignWorkers):
    a = db.get_assignment(aid)
    if a is None:
        raise HTTPException(404, "Assignment not found")
    fields = {"assignees": body.assignees}
    # Auto-set status based on whether anyone is assigned
    if body.assignees and a.get("status") == "todo":
        fields["status"] = "in-progress"
    elif not body.assignees and a.get("status") == "in-progress":
        fields["status"] = "todo"
    return db.update_assignment(aid, fields)


@app.delete("/api/assignments/{aid}")
def delete_assignment(aid: str):
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
def get_summary():
    _require_data()
    agent = _pm()
    summary = agent.summarize_status(_full_data())
    return {"summary": summary}


def _chat_context(req: ChatRequest):
    github_context = _full_data() if req.include_github else None
    history = [{"role": m.role, "content": m.content} for m in req.history] if req.history else None
    # RAG: search past notes for anything relevant to the question
    try:
        notes_context = _notes.search(req.message, n=3)
    except Exception:
        notes_context = []
    return github_context, history, notes_context


@app.post("/api/chat")
def chat(req: ChatRequest):
    agent = _pm()
    github_context, history, notes_context = _chat_context(req)
    response = agent.chat(
        user_message=req.message,
        github_context=github_context,
        conversation_history=history,
        notes_context=notes_context,
    )
    return {"response": response}


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    agent = _pm()
    github_context, history, notes_context = _chat_context(req)

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
def get_notes():
    return {"notes": _notes.list_all()}


@app.post("/api/notes")
def save_note(body: NoteCreate):
    note = _notes.save(title=body.title, content=body.content, note_type=body.note_type)
    return note


@app.post("/api/notes/generate")
def generate_and_save():
    """Non-streaming fallback — prefer /api/notes/generate/stream."""
    _require_data()
    agent   = _pm()
    content = agent.summarize_status(_full_data())
    title   = f"Team Status Report — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
    note    = _notes.save(title=title, content=content, note_type="report")
    try:
        write_note(title=title, content=content, note_type="report")
    except Exception as e:
        print(f"[vault] Could not write to vault: {e}")
    return note


@app.post("/api/notes/generate/stream")
def generate_and_save_stream():
    """Stream the report generation live, then save to ChromaDB + Obsidian vault."""
    _require_data()
    agent = _pm()
    title = f"Team Status Report — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

    # _build_messages slims this down to key stats; pass the full snapshot
    # so it has the keys it expects (matches /api/chat/stream and /api/summary).
    data = _full_data()

    prompt = (
        "Write a concise executive status report (8-10 bullet points) covering: "
        "team workload and who is overloaded, top risks, milestone progress, "
        "and the 3 most important actions to take this week. Be specific — use names and numbers."
    )

    chunks_collected: list[str] = []

    def generate():
        for chunk in agent.stream_chat(
            user_message=prompt,
            github_context=data,
        ):
            chunks_collected.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        # Save after streaming completes
        content = "".join(chunks_collected)
        try:
            _notes.save(title=title, content=content, note_type="report")
            write_note(title=title, content=content, note_type="report")
        except Exception as e:
            print(f"[notes] Save error: {e}")

        yield f"data: {json.dumps({'done': True, 'title': title})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/notes/save-to-vault/{note_id}")
def save_existing_to_vault(note_id: str):
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
def sync_vault():
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
def delete_note(note_id: str):
    _notes.delete(note_id)
    return {"deleted": note_id}


# ---------------------------------------------------------------------------
# Email integration (Microsoft 365 — each user connects their own inbox)
# ---------------------------------------------------------------------------

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


@app.get("/api/email/status")
def email_status():
    """Whether email is configured + which accounts are connected."""
    return {
        "configured": email_client.is_configured(),
        "accounts": db.list_email_accounts(),
    }


@app.get("/api/email/connect")
def email_connect():
    """Return the Microsoft sign-in URL for the user to grant inbox access."""
    if not email_client.is_configured():
        raise HTTPException(400, "Email is not configured. Set MS_CLIENT_ID / MS_CLIENT_SECRET.")
    url = email_client.auth_url(state="pm-agent")
    return {"auth_url": url}


@app.get("/api/email/callback")
def email_callback(code: str = "", error: str = "", error_description: str = ""):
    """Microsoft redirects here after the user signs in. Exchange + store the token."""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/email?error={error}")
    if not code:
        return RedirectResponse(f"{FRONTEND_URL}/email?error=missing_code")
    try:
        tok = email_client.exchange_code(code)
        db.save_email_account(
            email=tok["email"], name=tok["name"],
            refresh_token=tok["refresh_token"],
            connected_at=datetime.utcnow().isoformat(),
        )
        return RedirectResponse(f"{FRONTEND_URL}/email?connected={tok['email']}")
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/email?error={str(e)[:100]}")


@app.post("/api/email/sync")
def email_sync():
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
            db.set_email_synced(acct["email"], datetime.utcnow().isoformat())
        except Exception as e:
            errors.append(f"{acct['email']}: {str(e)[:80]}")

    return {"synced_emails": total, "accounts": len(accounts), "errors": errors}


@app.delete("/api/email/accounts/{email}")
def email_disconnect(email: str):
    if not db.delete_email_account(email):
        raise HTTPException(404, "Account not connected")
    return {"disconnected": email}
