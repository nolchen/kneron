#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."

echo "==> Setting up PM Dashboard backend"

# Create & activate venv
python3 -m venv "$SCRIPT_DIR/.venv"
source "$SCRIPT_DIR/.venv/bin/activate"

# Install backend deps (everything the app needs is pinned in requirements.txt:
# FastAPI, uvicorn, the openai SDK for any OpenAI-compatible LLM, ChromaDB, etc.)
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "==> Done! Copy .env.example to .env (defaults run a free local Ollama setup):"
echo "    cp backend/.env.example backend/.env"
echo ""
echo "==> Then start the backend:"
echo "    source backend/.venv/bin/activate && cd backend && uvicorn main:app --reload"
