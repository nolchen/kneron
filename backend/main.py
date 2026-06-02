import json
import os
import uuid
from datetime import datetime
from typing import Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from github_client import GitHubClient
from pm_agent import ProgramManagerAgent
from notes_store import NotesStore
from vault_client import write_note, scan_vault

_notes = NotesStore()

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------
_cache: dict       = {"data": None, "repos": []}
_team_store: list  = []   # all team members (mock-seeded or manually added)
_assignments: list = []   # user-created assignments

MOCK_TEAM = [
    {"login": "marcus_dev",    "role": "Backend Engineer",    "open_issues": 8,  "open_prs": 3, "recent_commits": 12, "repos_active": ["kneron/backend-api", "kneron/ml-pipeline"], "workload_score": 20.0},
    {"login": "sarah_kim",     "role": "Mobile Engineer",     "open_issues": 5,  "open_prs": 2, "recent_commits": 9,  "repos_active": ["kneron/mobile-app"], "workload_score": 13.5},
    {"login": "alex_chen",     "role": "Full-Stack Engineer", "open_issues": 4,  "open_prs": 2, "recent_commits": 7,  "repos_active": ["kneron/backend-api", "kneron/mobile-app"], "workload_score": 11.5},
    {"login": "jessica_lee",   "role": "Backend Engineer",    "open_issues": 4,  "open_prs": 2, "recent_commits": 6,  "repos_active": ["kneron/backend-api"], "workload_score": 11.0},
    {"login": "priya_patel",   "role": "ML Engineer",         "open_issues": 3,  "open_prs": 1, "recent_commits": 6,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 8.0},
    {"login": "jake_wilson",   "role": "DevOps Engineer",     "open_issues": 2,  "open_prs": 2, "recent_commits": 4,  "repos_active": ["kneron/backend-api"], "workload_score": 8.0},
    {"login": "emma_zhang",    "role": "Frontend Engineer",   "open_issues": 3,  "open_prs": 1, "recent_commits": 5,  "repos_active": ["kneron/mobile-app", "kneron/backend-api"], "workload_score": 7.5},
    {"login": "carlos_mendez", "role": "ML Engineer",         "open_issues": 2,  "open_prs": 1, "recent_commits": 4,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 6.0},
    {"login": "maya_robinson",  "role": "Mobile Engineer",    "open_issues": 2,  "open_prs": 1, "recent_commits": 3,  "repos_active": ["kneron/mobile-app"], "workload_score": 5.5},
    {"login": "lisa_nguyen",   "role": "Frontend Engineer",   "open_issues": 1,  "open_prs": 1, "recent_commits": 2,  "repos_active": ["kneron/mobile-app"], "workload_score": 4.0},
    {"login": "david_park",    "role": "Data Engineer",       "open_issues": 1,  "open_prs": 0, "recent_commits": 3,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 2.5},
    {"login": "ryan_torres",   "role": "QA Engineer",         "open_issues": 0,  "open_prs": 1, "recent_commits": 1,  "repos_active": ["kneron/ml-pipeline"], "workload_score": 2.5},
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
        {"number": 312, "title": "API gateway crashes under sustained 5k rps load", "url": "#", "state": "open", "labels": ["blocker", "performance"], "assignees": ["marcus_dev"], "created_at": "2026-05-20T10:00:00Z", "updated_at": "2026-05-30T09:00:00Z", "repo": "kneron/backend-api"},
        {"number": 289, "title": "OAuth token refresh fails after 1hr expiry", "url": "#", "state": "open", "labels": ["bug", "priority-high", "auth"], "assignees": ["alex_chen"], "created_at": "2026-05-18T08:00:00Z", "updated_at": "2026-05-29T14:00:00Z", "repo": "kneron/backend-api"},
        {"number": 76,  "title": "App crashes on iOS 17.4 when camera permission denied", "url": "#", "state": "open", "labels": ["bug", "priority-high", "ios"], "assignees": ["sarah_kim"], "created_at": "2026-05-22T11:00:00Z", "updated_at": "2026-05-31T10:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 301, "title": "Rate limiter doesn't reset correctly on rolling window", "url": "#", "state": "open", "labels": ["bug", "priority-high"], "assignees": ["marcus_dev"], "created_at": "2026-05-25T09:00:00Z", "updated_at": "2026-05-31T08:00:00Z", "repo": "kneron/backend-api"},
        {"number": 45,  "title": "KL720 inference latency spikes to 30ms on large batches", "url": "#", "state": "open", "labels": ["priority-high", "performance"], "assignees": ["priya_patel"], "created_at": "2026-05-21T13:00:00Z", "updated_at": "2026-05-28T16:00:00Z", "repo": "kneron/ml-pipeline"},
        {"number": 88,  "title": "Push notifications silently dropped on Android 14", "url": "#", "state": "open", "labels": ["bug", "priority-medium", "android"], "assignees": ["sarah_kim", "jake_wilson"], "created_at": "2026-05-19T15:00:00Z", "updated_at": "2026-05-27T11:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 315, "title": "Add Prometheus metrics endpoint /metrics", "url": "#", "state": "open", "labels": ["enhancement", "priority-medium", "observability"], "assignees": ["jake_wilson"], "created_at": "2026-05-26T10:00:00Z", "updated_at": "2026-05-30T12:00:00Z", "repo": "kneron/backend-api"},
        {"number": 92,  "title": "Onboarding flow skips step 3 for new Android users", "url": "#", "state": "open", "labels": ["bug", "priority-medium"], "assignees": ["lisa_nguyen"], "created_at": "2026-05-24T09:00:00Z", "updated_at": "2026-05-29T10:00:00Z", "repo": "kneron/mobile-app"},
        {"number": 48,  "title": "Add quantisation support for INT4 models", "url": "#", "state": "open", "labels": ["enhancement", "priority-medium"], "assignees": ["priya_patel", "ryan_torres"], "created_at": "2026-05-23T14:00:00Z", "updated_at": "2026-05-28T15:00:00Z", "repo": "kneron/ml-pipeline"},
        {"number": 320, "title": "Write API v2 migration guide for external devs", "url": "#", "state": "open", "labels": ["documentation"], "assignees": ["alex_chen"], "created_at": "2026-05-27T11:00:00Z", "updated_at": "2026-05-31T09:00:00Z", "repo": "kneron/backend-api"},
    ],
    "pull_requests": [
        {"number": 334, "title": "fix: patch rolling-window rate limiter reset logic", "url": "#", "state": "open", "author": "marcus_dev", "assignees": ["alex_chen"], "created_at": "2026-05-30T10:00:00Z", "updated_at": "2026-05-31T08:00:00Z", "repo": "kneron/backend-api", "draft": False},
        {"number": 335, "title": "feat: add /metrics Prometheus endpoint", "url": "#", "state": "open", "author": "jake_wilson", "assignees": ["marcus_dev"], "created_at": "2026-05-29T14:00:00Z", "updated_at": "2026-05-30T11:00:00Z", "repo": "kneron/backend-api", "draft": False},
        {"number": 97,  "title": "fix: camera permission crash on iOS 17.4", "url": "#", "state": "open", "author": "sarah_kim", "assignees": ["alex_chen"], "created_at": "2026-05-31T09:00:00Z", "updated_at": "2026-05-31T10:00:00Z", "repo": "kneron/mobile-app", "draft": False},
        {"number": 98,  "title": "fix: android push notification delivery", "url": "#", "state": "open", "author": "lisa_nguyen", "assignees": ["sarah_kim"], "created_at": "2026-05-28T16:00:00Z", "updated_at": "2026-05-29T09:00:00Z", "repo": "kneron/mobile-app", "draft": True},
        {"number": 52,  "title": "perf: optimise batch inference loop for KL720", "url": "#", "state": "open", "author": "priya_patel", "assignees": ["ryan_torres"], "created_at": "2026-05-30T13:00:00Z", "updated_at": "2026-05-31T07:00:00Z", "repo": "kneron/ml-pipeline", "draft": False},
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gh() -> GitHubClient:
    return GitHubClient(token=os.environ.get("GITHUB_TOKEN"))


def _pm() -> ProgramManagerAgent:
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    return ProgramManagerAgent(model=model)


def _require_data():
    if not _cache["data"]:
        raise HTTPException(
            status_code=400,
            detail="No data synced yet. POST /api/sync to fetch GitHub data first.",
        )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="PM Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def auto_seed():
    """Auto-load demo data on startup so the app is ready immediately."""
    global _team_store, _assignments
    _cache["data"] = MOCK_DATA
    _cache["repos"] = ["kneron/backend-api", "kneron/mobile-app", "kneron/ml-pipeline"]
    _team_store = [m.copy() for m in MOCK_TEAM]
    print("[startup] Demo data loaded automatically.")


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
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/mock")
def load_mock():
    global _team_store, _assignments
    _cache["data"] = MOCK_DATA
    _cache["repos"] = ["kneron/backend-api", "kneron/mobile-app", "kneron/ml-pipeline"]
    _team_store = [m.copy() for m in MOCK_TEAM]
    _assignments = []
    return {"loaded": True, "team_members": len(_team_store)}


@app.get("/api/health")
def health():
    return {"status": "ok", "cached_repos": _cache["repos"]}


@app.get("/api/repos")
def get_repos():
    return {"repos": _cache["repos"]}


@app.post("/api/repos")
def set_repos(config: ReposConfig):
    _cache["repos"] = config.repos
    _cache["data"] = None  # invalidate cache
    return {"repos": _cache["repos"]}


@app.post("/api/sync")
def sync(config: Optional[ReposConfig] = None):
    repos = (config.repos if config else None) or _cache["repos"]
    if not repos:
        raise HTTPException(400, "No repos configured. POST /api/repos first.")
    client = _gh()
    try:
        data = client.aggregate_team_data(repos)
        _cache["data"] = data
        _cache["repos"] = repos
        return {
            "synced_repos": repos,
            "team_members": len(data["team_members"]),
            "open_issues": len(data["issues"]),
            "open_prs": len(data["pull_requests"]),
        }
    finally:
        client.close()


ASSIGNMENT_WEIGHT = {"high": 5, "medium": 3, "low": 1}

@app.get("/api/team")
def get_team():
    source = _team_store if _team_store else (_cache["data"] or {}).get("team_members", [])
    if not source and not _cache["data"]:
        raise HTTPException(400, "No data synced yet. POST /api/sync to fetch GitHub data first.")

    # Compute extra workload from active assignments (shared across all assignees)
    extra: dict = {}
    for a in _assignments:
        if a.get("assignees") and a.get("status") != "done":
            w = ASSIGNMENT_WEIGHT.get(a.get("priority", "medium"), 3)
            for login in a["assignees"]:
                extra[login] = extra.get(login, 0) + w

    members = []
    for m in source:
        mc = m.copy()
        mc["workload_score"] = round(m.get("workload_score", 0) + extra.get(m["login"], 0), 1)
        members.append(mc)

    members.sort(key=lambda m: m["workload_score"], reverse=True)
    return {"team_members": members}


@app.post("/api/team/member")
def add_member(body: TeamMemberCreate):
    login = body.name.strip().lower().replace(" ", "_")
    if any(m["login"] == login for m in _team_store):
        raise HTTPException(400, f"Member '{login}' already exists")
    repos = [r.strip() for r in body.repos.split(",") if r.strip()]
    member = {
        "login": login,
        "role": body.role,
        "open_issues": 0, "open_prs": 0, "recent_commits": 0,
        "repos_active": repos,
        "workload_score": 0.0,
    }
    _team_store.append(member)
    return member


@app.delete("/api/team/member/{login}")
def remove_member(login: str):
    global _team_store
    before = len(_team_store)
    _team_store = [m for m in _team_store if m["login"] != login]
    if len(_team_store) == before:
        raise HTTPException(404, "Member not found")
    return {"deleted": login}


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

@app.get("/api/assignments")
def get_assignments():
    return {"assignments": _assignments}


@app.post("/api/assignments")
def create_assignment(body: AssignmentBody):
    a = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        **body.model_dump(),
    }
    _assignments.append(a)
    return a


@app.put("/api/assignments/{aid}")
def update_assignment(aid: str, body: AssignmentBody):
    for i, a in enumerate(_assignments):
        if a["id"] == aid:
            _assignments[i] = {**a, **body.model_dump()}
            return _assignments[i]
    raise HTTPException(404, "Assignment not found")


class AssignWorkers(BaseModel):
    assignees: List[str]  # list of logins; empty list = unassign all

@app.patch("/api/assignments/{aid}/assign")
def assign_workers(aid: str, body: AssignWorkers):
    for i, a in enumerate(_assignments):
        if a["id"] == aid:
            updated = {**a, "assignees": body.assignees}
            # Auto-set status based on whether anyone is assigned
            if body.assignees and a.get("status") == "todo":
                updated["status"] = "in-progress"
            elif not body.assignees and a.get("status") == "in-progress":
                updated["status"] = "todo"
            _assignments[i] = updated
            return _assignments[i]
    raise HTTPException(404, "Assignment not found")


@app.delete("/api/assignments/{aid}")
def delete_assignment(aid: str):
    global _assignments
    before = len(_assignments)
    _assignments = [a for a in _assignments if a["id"] != aid]
    if len(_assignments) == before:
        raise HTTPException(404, "Assignment not found")
    return {"deleted": aid}


@app.get("/api/projects")
def get_projects():
    _require_data()
    return {"projects": _cache["data"]["projects"]}


@app.get("/api/roadmap")
def get_roadmap():
    _require_data()
    milestones = []
    for project in _cache["data"]["projects"]:
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

    issues = sorted(_cache["data"]["issues"], key=score, reverse=True)
    return {"priorities": issues}


@app.get("/api/summary")
def get_summary():
    _require_data()
    agent = _pm()
    summary = agent.summarize_status(_cache["data"])
    return {"summary": summary}


def _chat_context(req: ChatRequest):
    github_context = _cache["data"] if req.include_github else None
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
    content = agent.summarize_status(_cache["data"])
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

    # Trim context to key stats only — much faster than dumping full JSON
    data = _cache["data"]
    slim_context = {
        "team_members": [
            {"login": m["login"], "role": m.get("role",""), "workload_score": m["workload_score"]}
            for m in data.get("team_members", [])
        ],
        "projects": [
            {"repo": p["repo"], "open_issues": p["open_issues_count"], "open_prs": p["open_prs_count"],
             "milestones": [{"title": ms["title"], "progress": ms["progress"], "due_on": ms.get("due_on","")}
                            for ms in p.get("milestones", [])]}
            for p in data.get("projects", [])
        ],
        "top_issues": [
            {"title": i["title"], "labels": i["labels"], "assignees": i["assignees"]}
            for i in data.get("issues", [])[:8]
        ],
    }

    prompt = (
        "Write a concise executive status report (8-10 bullet points) covering: "
        "team workload and who is overloaded, top risks, milestone progress, "
        "and the 3 most important actions to take this week. Be specific — use names and numbers."
    )

    chunks_collected: list[str] = []

    def generate():
        for chunk in agent.stream_chat(
            user_message=prompt,
            github_context=slim_context,
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
