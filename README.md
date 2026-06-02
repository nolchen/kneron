# Kneron PM Agent Dashboard

An AI-powered program manager dashboard for engineering teams. Tracks GitHub workload, milestones, and priorities — with a conversational AI agent you can ask questions directly.

## What it does

- **Dashboard** — executive summary of sprint health, team load, and at-risk milestones
- **Team** — per-engineer workload scores based on open issues, PRs, and recent commits
- **Assignments** — create and track assignments across the team
- **Roadmap** — milestone progress across all repos
- **Calendar** — deadline view for upcoming milestones
- **Reports** — generated status reports saved to an Obsidian vault
- **Chat** — talk to the PM agent directly; it has full GitHub context loaded

## Stack

- **Backend** — FastAPI + Python, GitHub REST API, ChromaDB (note storage)
- **Frontend** — Next.js 14 (App Router), TypeScript, Tailwind CSS
- **AI** — Ollama running locally (default: `llama3.2`), OpenAI-compatible API

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) installed and running

```bash
ollama pull llama3.2
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — add GITHUB_TOKEN if using private repos
```

### Frontend

```bash
cd frontend
npm install
```

### Run

From the `Kneron/` root:

```bash
./start.sh
```

Or manually:

```bash
# terminal 1
cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000

# terminal 2
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | *(empty)* | GitHub PAT — needed for private repos or >60 req/hr |
| `OLLAMA_MODEL` | `llama3.2` | Any model available in your local Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama API endpoint |

## Notes

The app ships with realistic mock data so it works out of the box without a GitHub token. Connect a real org by setting `GITHUB_TOKEN` and pointing it at your repos via the dashboard.
