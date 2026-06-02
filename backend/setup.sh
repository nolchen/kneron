#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."

echo "==> Setting up PM Dashboard backend"

# Create & activate venv
python3 -m venv "$SCRIPT_DIR/.venv"
source "$SCRIPT_DIR/.venv/bin/activate"

# Install our backend deps
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# Install Hermes Agent as a package (gives us run_agent, agent/, etc.)
echo "==> Installing Hermes Agent..."
pip install -q -e "$ROOT/hermes-agent"

# Install the anthropic SDK (Hermes lazy-loads it)
pip install -q "anthropic>=0.40.0"

echo ""
echo "==> Done! Copy .env.example to .env and fill in your API keys:"
echo "    cp backend/.env.example backend/.env"
echo ""
echo "==> Then start the backend:"
echo "    source backend/.venv/bin/activate && cd backend && uvicorn main:app --reload"
