# PM Agent Dashboard

An AI-powered program-manager dashboard for any team — engineering, sales, ops, whatever.
Track workload, assignments, deadlines, and project health, and ask a built-in AI agent
questions about it all in plain English. Runs fully local and free, or deploys to the cloud.

## What it does

- **Dashboard** — at-a-glance stats plus auto-generated alerts (overdue work, overloaded
  people, at-risk milestones) and an AI-written executive summary
- **Team** — add/remove members, see each person's live workload and active task count
- **Assignments** — a 3-column board: *Needs to Start → Available people → Being Worked On*.
  Create a task, assign one or more people, and their workload updates automatically
- **Timeline** — every assignment grouped by due date (overdue / this week / next week / later)
- **Calendar** — month view with milestone and assignment due dates
- **Priorities** — open tasks ranked by priority labels
- **Reports** — generate AI status reports (streamed live), saved and searchable; also
  written to an Obsidian vault as Markdown
- **AI PM Chat** — talk to the agent directly. It has your team data loaded and searches
  past reports/notes (RAG) to answer questions
- **Knowledge Graph** — a live 3D map of how people, projects, tasks, reports, and emails
  connect; auto-fits so it stays readable as the team and its data grow
- **Dark mode**, dismissible alerts, and a custom brand palette throughout

## Stack

- **Backend** — FastAPI + Python, SQLite (persistent data), ChromaDB (RAG note search)
- **Frontend** — Next.js 16 (App Router), TypeScript, Tailwind CSS, Recharts
- **AI** — any OpenAI-compatible provider: Ollama (local, free, default), Groq (cloud,
  free tier), or OpenAI. Switchable via env vars — no code changes.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) for the local/free AI

```bash
ollama pull llama3.2          # chat / report model
ollama pull nomic-embed-text  # embeddings for notes search
```

### Install

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # defaults work out of the box (local Ollama)

# Frontend
cd ../frontend
npm install
```

### Run

From the `PM_Agent/` folder:

```bash
./start.sh
```

Or manually, in two terminals:

```bash
cd backend && source .venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app auto-loads realistic demo
data on first run, so it works immediately — no GitHub token or setup required.

**Sharing with a team:** run it on one machine and send teammates the
`http://<your-ip>:3000` URL that `start.sh` prints. Everyone hits the same backend
and database on that machine, so all users see the same shared, consistent data —
no per-user copies. See [GETTING_STARTED.md](./GETTING_STARTED.md) §6b. Leave
`NEXT_PUBLIC_API_URL` unset in `frontend/.env.local` for this to work.

## Environment variables

All optional — the defaults run a free local setup.

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` \| `groq` \| `openai` |
| `OLLAMA_MODEL` | `llama3.2` | Model when using Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama endpoint |
| `GROQ_API_KEY` | — | Required if `LLM_PROVIDER=groq` |
| `OPENAI_API_KEY` | — | Required if `LLM_PROVIDER=openai` |
| `EMBED_PROVIDER` | `ollama` | `ollama` \| `openai` (for notes search) |
| `DATA_DIR` | backend folder | Where SQLite + ChromaDB live (set to a volume in prod) |
| `VAULT_PATH` | `../PM-Vault` | Obsidian vault folder for report sync |
| `ALLOWED_ORIGINS` | — | Extra CORS origins (your deployed frontend URL) |
| `GITHUB_TOKEN` | — | Optional — sync real repos instead of demo data |

See `backend/.env.example` for the full annotated list.

## Data & persistence

Team members, assignments, and the data snapshot persist to `backend/pm_data.db` (SQLite).
Reports/notes persist to a local ChromaDB store. Everything survives restarts. The
"Load Demo Data" button is an explicit reset.

## Obsidian integration

Generated reports are written as Markdown into the `PM-Vault/PM-Agent/` folder, so they
show up in Obsidian automatically. The **Sync Obsidian Vault** button scans the vault and
indexes any notes you've written so the AI chat can reference them.

## Deploying for a team

See [DEPLOY.md](./DEPLOY.md) for a free step-by-step (Vercel + Render + Groq).

## Notes

- Runs in open mode by default — anyone with the URL can view/edit, which is what makes
  the shared-on-your-network setup frictionless for a trusted team. Microsoft SSO with
  L1/L2/L3 roles is built in; set `AUTH_ENFORCED=true` (plus the Microsoft env vars) to
  require login and enforce role permissions before opening it wider. See `DEPLOY.md`.
- The app ships with mock data so it runs without any external services. Connect a real
  GitHub org by setting `GITHUB_TOKEN` and syncing repos from the dashboard.

---

