#!/usr/bin/env bash
# Shared setup for the API examples. Each example script sources this.
#
#   BASE       deploy URL (default: the current internal deploy)
#   PM_SESSION your pm_session cookie value (sign in, then DevTools →
#              Application → Cookies → copy `pm_session`)
#
# -k accepts the self-signed cert; drop it once a real cert is in place.

BASE="${BASE:-https://10.200.211.156:8443}"
SESS="${PM_SESSION:-}"

if [ -z "$SESS" ]; then
  echo "⚠️  PM_SESSION not set — auth'd calls will come back empty/401."
  echo "    Sign in, copy the pm_session cookie, then:"
  echo "    BASE=$BASE PM_SESSION=<cookie> $0"
  echo ""
fi

# req METHOD PATH [JSON_BODY] — print the call, run it, show the (truncated) result
req() {
  local m="$1" p="$2" body="$3"
  printf '  $ curl -sk -b "pm_session=…" -X %s %s%s' "$m" "$BASE" "$p"
  [ -n "$body" ] && printf " -d '%s'" "$body"
  printf '\n'
  local args=(-sk -m 60 -b "pm_session=$SESS" -X "$m" "$BASE$p")
  [ -n "$body" ] && args+=(-H "Content-Type: application/json" -d "$body")
  curl "${args[@]}" | head -c 500
  printf '\n\n'
}
