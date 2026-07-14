#!/usr/bin/env bash
# Email → calendar API (per-user; reads the signed-in person's inbox).
. "$(dirname "$0")/_common.sh"

echo "### GET /api/email/status — is email configured + connected inboxes"
req GET /api/email/status

echo "### GET /api/me/inbox — is MY inbox connected"
req GET /api/me/inbox

echo "### POST /api/me/scan — scan my inbox → meeting/task proposals"
req POST /api/me/scan

echo "### POST /api/me/calendar/confirm — confirm proposals → board + Outlook"
echo "  (body is one of the proposals returned by /api/me/scan)"
req POST /api/me/calendar/confirm '{"title":"Sync meeting","start":"2026-08-01T14:00:00","attendees":[]}'
