#!/usr/bin/env bash
# Admin API (users, roles, sync). Needs an L2/L3 session.
. "$(dirname "$0")/_common.sh"

echo "### GET /api/users — list users + roles (L2+)"
req GET /api/users

echo "### PUT /api/users/{email}/role — change a role, strictly-below only (L2+)"
echo "  (example — will 403 unless the target is below your level)"
req PUT /api/users/maxwell.chen@kneron.us/role '{"role":"L1"}'

echo "### POST /api/sync — refresh the GitHub snapshot (L2+)"
req POST /api/sync

echo "### GET /api/repos — configured repos"
req GET /api/repos
