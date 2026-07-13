#!/usr/bin/env bash
#
# Production launcher for hosting PM Agent on ONE internal machine, reachable by
# its IP address (e.g. http://10.0.4.17:3000) by everyone on the office network.
#
# Difference vs. start.sh (the dev launcher):
#   - builds the frontend and runs the PRODUCTION server (faster, stable)
#   - binds BOTH the frontend and backend to 0.0.0.0 so they're reachable by IP
#   - sets BACKEND_ORIGIN so the frontend proxies /api/* to the local backend
#   - leaves NEXT_PUBLIC_API_URL empty so browsers use same-origin (required so
#     OTHER people's browsers hit THIS server, not their own localhost)
#
# For a real always-on deployment, run this under a process manager instead of a
# terminal — see deploy/README.md (systemd / pm2). This script is the source of
# truth those wrappers call.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# The frontend (running on THIS box) proxies /api/* to the backend on THIS box,
# so localhost is correct here — it's a server-to-server hop, not the browser.
export BACKEND_ORIGIN="${BACKEND_ORIGIN:-http://localhost:${BACKEND_PORT}}"
# Force same-origin in the browser bundle. If this is set to a URL at BUILD time,
# every visitor's browser calls that URL directly (cross-origin / their own box).
unset NEXT_PUBLIC_API_URL || true
export NODE_ENV=production

if [ ! -d "$BACKEND/.venv" ]; then
  echo "==> Backend not set up — running backend/setup.sh ..."
  bash "$BACKEND/setup.sh"
fi
if [ ! -f "$BACKEND/.env" ]; then
  echo "ERROR: $BACKEND/.env not found. Copy backend/.env.example → backend/.env and fill it in." >&2
  exit 1
fi

echo "==> Building the frontend (production) ..."
( cd "$FRONTEND" && npm run build )

# Best-effort LAN IP for the "share this" line.
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')"

echo "==> Starting backend on 0.0.0.0:${BACKEND_PORT} ..."
( source "$BACKEND/.venv/bin/activate" && cd "$BACKEND" && exec uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" ) &
BACKEND_PID=$!

echo "==> Starting frontend on 0.0.0.0:${FRONTEND_PORT} ..."
( cd "$FRONTEND" && exec npm run start -- -H 0.0.0.0 -p "$FRONTEND_PORT" ) &
FRONTEND_PID=$!

echo ""
echo "  On this machine   → http://localhost:${FRONTEND_PORT}"
if [ -n "$LAN_IP" ]; then
  echo "  Team on network   → http://${LAN_IP}:${FRONTEND_PORT}"
fi
echo "  API docs          → http://localhost:${BACKEND_PORT}/docs"
echo ""
echo "  NOTE: Microsoft email login needs an HTTPS hostname (see INTERNAL_HOSTING.md)."
echo "  Ctrl+C stops both."
echo ""

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT TERM
wait
