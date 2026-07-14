#!/usr/bin/env bash
# AI assistant + reports API (runs on Kneron-hosted gpt-5.4).
. "$(dirname "$0")/_common.sh"

echo "### POST /api/chat — ask the AI (grounded in live team data)"
req POST /api/chat '{"message":"Who is most overloaded this week?","history":[],"include_github":true}'

echo "### POST /api/notes/generate — generate a status report"
req POST /api/notes/generate '{"prompt":"","scope":"all"}'

echo "### GET /api/notes — list saved reports/notes"
req GET /api/notes

echo "### POST /api/notes — save a manual note"
req POST /api/notes '{"title":"Example note","content":"Written via the API.","note_type":"note"}'
