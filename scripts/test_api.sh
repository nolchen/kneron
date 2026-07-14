#!/usr/bin/env bash
#
# Smoke-test the PM Agent API end to end.
#
# Usage:
#   BASE="https://10.200.211.156:8443" PM_SESSION="<pm_session cookie>" ./scripts/test_api.sh
#
# Get PM_SESSION: sign in at the app, then DevTools → Application → Cookies →
# copy the value of `pm_session`. Without it, only the public checks run.
#
# -k is used throughout because the deploy uses a self-signed cert. Drop it once
# a real (IT-issued) cert is in place.

BASE="${BASE:-https://10.200.211.156:8443}"
SESS="${PM_SESSION:-}"
CURL=(curl -sk -m 60)
[ -n "$SESS" ] && CURL+=(-b "pm_session=$SESS")

pass=0; fail=0
check() { # name  expected_http  curl-args...
  local name="$1" want="$2"; shift 2
  local code; code=$("${CURL[@]}" -o /tmp/pm_body.$$ -w "%{http_code}" "$@")
  if [ "$code" = "$want" ]; then
    printf "  ✅ %-34s %s\n" "$name" "$code"; pass=$((pass+1))
  else
    printf "  ❌ %-34s got %s (want %s) %s\n" "$name" "$code" "$want" "$(head -c 120 /tmp/pm_body.$$)"; fail=$((fail+1))
  fi
  rm -f /tmp/pm_body.$$
}

echo "PM Agent API smoke test → $BASE"
echo "session: $([ -n "$SESS" ] && echo "provided" || echo "NONE (public checks only)")"
echo ""

echo "── public ──"
check "GET  /api/health"        200 "$BASE/api/health"
check "GET  /api/auth/me"       200 "$BASE/api/auth/me"

if [ -z "$SESS" ]; then
  echo ""
  echo "No PM_SESSION set — skipping authenticated checks."
  echo "Sign in, copy the pm_session cookie, and re-run with PM_SESSION=<value>."
  exit 0
fi

echo ""
echo "── whoami ──"
"${CURL[@]}" "$BASE/api/auth/me" | python3 -c "import sys,json;u=(json.load(sys.stdin).get('user') or {});print('   signed in as',u.get('email'),'role',u.get('role'))" 2>/dev/null

echo ""
echo "── read endpoints ──"
check "GET  /api/team"          200 "$BASE/api/team"
check "GET  /api/assignments"   200 "$BASE/api/assignments"
check "GET  /api/projects"      200 "$BASE/api/projects"
check "GET  /api/roadmap"       200 "$BASE/api/roadmap"
check "GET  /api/priorities"    200 "$BASE/api/priorities"
check "GET  /api/graph"         200 "$BASE/api/graph"
check "GET  /api/notes"         200 "$BASE/api/notes"
check "GET  /api/email/status"  200 "$BASE/api/email/status"

echo ""
echo "── AI (slower) ──"
check "GET  /api/summary"       200 "$BASE/api/summary"
check "POST /api/chat"          200 -X POST "$BASE/api/chat" -H "Content-Type: application/json" -d '{"message":"one word: hi","history":[]}'
check "POST /api/notes/generate" 200 -X POST "$BASE/api/notes/generate" -H "Content-Type: application/json" -d '{"prompt":"","scope":"all"}'

echo ""
echo "──────────────────────────────"
echo "  $pass passed, $fail failed"
[ "$fail" = 0 ] && echo "  ✅ all good" || echo "  ⚠️ see failures above"
exit $fail
