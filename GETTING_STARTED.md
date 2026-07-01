# PM Agent — Getting Started (Run It On Your Laptop)

A complete guide to running PM Agent locally, the API reference, and how the
role-based task-assignment workflow works.

---

## 1. What you're running

Three pieces run together on your machine:

| Piece | Tech | Port | What it does |
|---|---|---|---|
| **Backend** | Python (FastAPI) | `8000` | API, auth, AI, database access |
| **Frontend** | Next.js (React) | `3000` | The dashboard you open in the browser |
| **Database** | SQLite (local, zero-setup) | — | Stores team, tasks, users, roles |
| **AI** | Ollama (local) or Groq (cloud) | — | Powers the chatbot + report/email extraction |

Locally it defaults to a **SQLite file** and **local Ollama AI**, so you can run
it with no cloud accounts at all.

---

## 2. Prerequisites

Install these first (all free):

- **Python 3.11+** — <https://www.python.org/downloads/>
- **Node.js 18+** — <https://nodejs.org/> (for the frontend)
- **Git** — <https://git-scm.com/>
- **Ollama** (for local AI) — <https://ollama.com/download>, then run once:
  ```
  ollama pull llama3.2
  ```
  *(Or skip Ollama and use a free Groq key instead — see step 5.)*

Check they're installed:
```
python3 --version
node --version
git --version
```

---

## 3. Get the code

```
git clone https://github.com/nolchen/kneron.git
cd kneron/PM_Agent
```

---

## 4. One-time setup

**Backend** (creates a virtual environment and installs dependencies):
```
bash backend/setup.sh
cp backend/.env.example backend/.env
```

**Frontend**:
```
cd frontend
npm install
cd ..
```

---

## 5. Configure `backend/.env`

Open `backend/.env` in any text editor. For a **quick local run**, the defaults
are fine — you only need to pick your AI provider:

- **Local AI (free, no key):** leave `LLM_PROVIDER=ollama` (needs Ollama from step 2).
- **Cloud AI (free key):** set `LLM_PROVIDER=groq` and add `GROQ_API_KEY=gsk_...`
  from <https://console.groq.com>.

Everything else (database, email, auth) is **optional** for a local trial and can
stay commented out. To also try the **email → tasks** feature, fill in the
Microsoft section (`MS_CLIENT_ID` / `MS_CLIENT_SECRET` / `MS_TENANT_ID`) — see
`DEPLOY.md` for the Azure app-registration steps.

---

## 6. Run it

From the `PM_Agent` folder:
```
bash start.sh
```
This starts the backend on `:8000` and the frontend on `:3000`. Then open:

> **http://localhost:3000**

*(To run them separately: in one terminal `source backend/.venv/bin/activate && cd backend && uvicorn main:app --reload`, and in another `cd frontend && npm run dev`.)*

---

## 7. Load demo data

On first open you'll see a setup card. Click **"Load Demo Data"** — this fills a
realistic 15-person team, three projects, and a board of tasks so you can explore
everything without connecting GitHub or email.

*(This button works in local/open mode. It's intentionally disabled in the
deployed production app to keep real data clean.)*

---

## 8. Roles & assigning tasks — the workflow

### The three roles
| Level | Who | Can do |
|---|---|---|
| **L3 — Admin** | you / leads | Add & remove people, change roles (up to L2), create & assign tasks |
| **L2 — Manager** | team leads | Create & assign tasks, add L1 members |
| **L1 — Member** | ICs / interns | See only their own assigned tasks — read-only board |

Rules that are enforced on the server (not just hidden in the UI):
- You can only grant a level **strictly below your own** (an L3 can make someone
  L2, never another L3; an L2 can make someone L1).
- **No one can change their own role** — no self-promotion.

### How assigning a task works (end to end)
1. On the **Assignments** page, an **L2 or L3** creates a task (title, due date,
   priority) or opens an existing one.
2. They pick one or more people to **assign** it to.
3. The task's status auto-moves to **"Being Worked On,"** and each newly assigned
   person is **notified** (by email, if email is configured).
4. That person opens **"My Tasks"** and sees the task waiting for them, with its
   due date and priority. An **L1** sees *only* their own tasks — nothing else.

So the flow is: **manager assigns → assignee is notified → assignee sees it under
"My Tasks."**

### Trying the role rules locally
- To *see the whole app and the assign→receive flow*, open mode (the default
  local setup) is enough — assign tasks and watch them land on the board.
- To *enforce the role restrictions* (e.g. prove an L1 can't assign), set
  `AUTH_ENFORCED=true` in `.env` and sign in with **Microsoft accounts** (real
  logins). In open mode everyone is treated as an admin, so restrictions don't
  apply — that's by design for easy local trials.

---

## 9. API documentation

The backend auto-generates **live, interactive API docs**. With the app running,
open:

> **http://localhost:8000/docs**

This is a full Swagger UI — every endpoint, its parameters, and a "Try it out"
button to call it live. (A machine-readable spec is at
`http://localhost:8000/openapi.json`.)

### Key endpoints at a glance

**Auth**
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/auth/login` | Start Microsoft sign-in |
| GET | `/api/auth/me` | Who am I (current user + role) |
| POST | `/api/auth/logout` | Sign out |

**People & roles** *(L3 for role changes)*
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/users` | List users + roles |
| PUT | `/api/users/{email}/role` | Change someone's role |
| PUT | `/api/users/{email}/manager` | Set who they report to |
| GET | `/api/team` | Team members + workload |
| POST | `/api/team/member` | Add a team member |
| DELETE | `/api/team/member/{login}` | Remove one |

**Assignments / tasks** *(L2+ to create/assign)*
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/assignments` | List tasks (scoped to what you can see) |
| POST | `/api/assignments` | Create a task |
| PUT | `/api/assignments/{id}` | Edit a task |
| PATCH | `/api/assignments/{id}/assign` | **Assign people** → notifies them |
| DELETE | `/api/assignments/{id}` | Delete a task |

**Program data**
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/projects` | Projects + milestones |
| GET | `/api/roadmap` | Timeline |
| GET | `/api/priorities` | Ranked priorities |
| GET | `/api/summary` | AI summary of current status |
| GET | `/api/graph` | Knowledge-graph nodes/edges |

**Email → tasks & calendar** *(each user, their own inbox)*
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/me/inbox` | Is my inbox connected? |
| POST | `/api/me/scan` | Read my inbox → propose calendar items/tasks |
| POST | `/api/me/calendar/confirm` | Confirm → write to calendar + board |
| GET | `/api/email/status` | Email configured? which inboxes? |

**AI & reports**
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat` | Ask the AI PM about the team/tasks |
| POST | `/api/notes/generate` | Generate a status report |
| GET | `/api/notes` | List saved reports/notes |

**Health**: `GET /api/health` → `{"status":"ok"}`

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `next: command not found` | Run `npm install` in `frontend/` |
| Backend won't start / import errors | Re-run `bash backend/setup.sh`, ensure `.venv` is active |
| Chat/reports error | Make sure Ollama is running (`ollama serve`) or a valid `GROQ_API_KEY` is set |
| Dashboard shows "no data" | Click **Load Demo Data**, or connect email/GitHub |
| Port already in use | Something's on `:8000`/`:3000` — stop it, or change the port |

---

## In short

`bash backend/setup.sh` → `cp backend/.env.example backend/.env` →
`cd frontend && npm install` → back to `PM_Agent` → `bash start.sh` →
open **localhost:3000** → **Load Demo Data** → explore. Full API at
**localhost:8000/docs**.
