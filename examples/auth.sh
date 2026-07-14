#!/usr/bin/env bash
# Auth API — one test case per endpoint.
. "$(dirname "$0")/_common.sh"

echo "### GET /api/health — liveness (public)"
req GET /api/health

echo "### GET /api/auth/me — current user + {configured, enforced} (public)"
req GET /api/auth/me

echo "### GET /api/auth/login — starts Microsoft sign-in (returns a redirect)"
echo "  (open this in a browser rather than curl — it redirects to Microsoft)"
echo "  $BASE/api/auth/login"
echo ""

echo "### POST /api/auth/logout — clear the session"
req POST /api/auth/logout
