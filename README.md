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

From the `Kneron/` root:

```bash
./start.sh
```

Or manually, in two terminals:

```bash
cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app auto-loads realistic demo
data on first run, so it works immediately — no GitHub token or setup required.

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

- No authentication yet — anyone with the URL can view/edit. Fine for a trusted team; add
  auth before opening it wider.
- The app ships with mock data so it runs without any external services. Connect a real
  GitHub org by setting `GITHUB_TOKEN` and syncing repos from the dashboard.
