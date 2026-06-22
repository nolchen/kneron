#!/usr/bin/env bash
# Start both backend and frontend dev servers

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# Activate the tracked git hooks (secret-leak guard) for this clone. Idempotent.
if [ -d "$ROOT/.git" ] && [ "$(git -C "$ROOT" config --get core.hooksPath)" != ".githooks" ]; then
  git -C "$ROOT" config core.hooksPath .githooks && echo "==> Enabled .githooks (pre-commit secret guard)."
fi
chmod +x "$ROOT/.githooks/"* 2>/dev/null

# Backend
if [ ! -d "$BACKEND/.venv" ]; then
  echo "==> Running backend setup first..."
  bash "$BACKEND/setup.sh"
fi

if [ ! -f "$BACKEND/.env" ]; then
  echo "ERROR: $BACKEND/.env not found."
  echo "       Copy backend/.env.example → backend/.env and set your ANTHROPIC_API_KEY."
  exit 1
fi

echo "==> Starting backend on http://localhost:8000 ..."
(source "$BACKEND/.venv/bin/activate" && cd "$BACKEND" && uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

echo "==> Starting frontend on http://localhost:3000 ..."
(cd "$FRONTEND" && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:3000"
echo "  API docs → http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
