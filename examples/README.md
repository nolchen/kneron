# PM Agent API examples

Runnable test cases for every API, one script per group. Kept **separate from
`SDK.md`** (which is the reference doc) so you can run each API test on its own.

## Setup
```bash
# 1. Sign in at the app, then DevTools → Application → Cookies → copy `pm_session`
export BASE="https://<your-deploy>:8443"      # e.g. https://10.200.211.156:8443
export PM_SESSION="<pm_session cookie value>"
```

## Run
```bash
./examples/auth.sh             # health, auth/me, login, logout
./examples/team.sh             # team, add/remove member
./examples/assignments.sh      # list, create, edit, assign, delete a task
./examples/program.sh          # projects, roadmap, priorities, summary, graph
./examples/ai.sh               # chat, generate report, notes  (Kneron gpt-5.4)
./examples/email_calendar.sh   # email status, inbox, scan, calendar confirm
./examples/admin.sh            # users, roles, sync, repos  (L2+)
```

Each script prints the exact `curl` for each endpoint, runs it, and shows the
response — so it doubles as copy-paste reference and as a live test.

- `-k` accepts the self-signed cert; drop it once a real cert is in place.
- Writes need an **L2/L3** session; reads work for any signed-in user (and return
  empty when signed out).
- `../scripts/test_api.sh` is the quick pass/fail smoke test across the main endpoints.
