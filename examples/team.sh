#!/usr/bin/env bash
# Team API — one test case per endpoint.
. "$(dirname "$0")/_common.sh"

echo "### GET /api/team — members with workload, status, active tasks"
req GET /api/team

echo "### POST /api/team/member — add a member (L2+)"
req POST /api/team/member '{"login":"jane_doe","name":"Jane Doe","role":"Engineer"}'

echo "### DELETE /api/team/member/{login} — remove a member (L2+)"
req DELETE /api/team/member/jane_doe
