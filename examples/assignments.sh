#!/usr/bin/env bash
# Assignments (task board) API — one test case per endpoint.
# Creates a task, edits it, assigns it, then deletes it.
. "$(dirname "$0")/_common.sh"

echo "### GET /api/assignments — list all tasks (scoped to your role)"
req GET /api/assignments

echo "### POST /api/assignments — create a task (L2+)"
AID=$(curl -sk -m60 -b "pm_session=$SESS" -X POST "$BASE/api/assignments" \
  -H "Content-Type: application/json" \
  -d '{"title":"__EXAMPLE__ ship the thing","due_date":"2026-08-01","priority":"high","status":"todo"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
echo "  created id: ${AID:-<none — need L2+ session>}"
echo ""

if [ -n "$AID" ]; then
  echo "### PUT /api/assignments/{id} — edit a task (L2+)"
  req PUT "/api/assignments/$AID" '{"priority":"medium"}'

  echo "### PATCH /api/assignments/{id}/assign — assign people, auto-notifies (L2+)"
  req PATCH "/api/assignments/$AID/assign" '{"assignees":["bobby_lee"]}'

  echo "### DELETE /api/assignments/{id} — delete a task (L2+)"
  req DELETE "/api/assignments/$AID"
fi
