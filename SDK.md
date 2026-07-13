# PM Agent — API / SDK Reference

The PM Agent backend is a REST API (FastAPI). Everything the app does — team,
tasks, calendar, AI chat, reports — is available over HTTP. This document is the
contract; `scripts/test_api.sh` exercises it end to end.

- **Base URL (current deploy):** `https://10.200.211.108:8443`
- **Interactive docs (OpenAPI/Swagger):** `https://10.200.211.108:8443/docs`
- **Content type:** `application/json` for all request/response bodies
- **AI engine:** Kneron-hosted `gpt-5.4` (OpenAI-compatible endpoint)

> The self-signed cert shows a one-time browser warning; `curl` needs `-k` to
> accept it. A proper hostname + cert from IT removes both.

---

## Authentication

Auth is **Microsoft sign-in** (OAuth). A successful login sets an **HttpOnly
session cookie** named `pm_session`; every request reads that cookie. There are
no API keys for callers — identity comes from the cookie.

**Getting a session to test with:**
1. Sign in at `https://10.200.211.108:8443` with your Microsoft account.
2. Open browser **DevTools → Application → Cookies** → copy the value of
   **`pm_session`**.
3. Pass it on every request: `-b "pm_session=<value>"` (or header
   `Cookie: pm_session=<value>`).

### Roles (RBAC)
| Role | Who | Can |
|------|-----|-----|
| **L1** | Intern | Read-only — sees their scoped view |
| **L2** | Manager | + create / assign / edit tasks, manage L1 people |
| **L3** | Admin | + manage everyone, change roles, email/calendar admin |

- **Not signed in:** read endpoints return **empty** results; any write/action returns **401**.
- Each caller only sees data their role permits (scoping is server-side).

### Error format
Errors return the matching HTTP status with a JSON body:
```json
{ "detail": "human-readable reason" }
```
Common: `401` not signed in · `403` role too low · `400` bad input · `502` AI upstream error.

---

## Endpoints

### Auth
| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/api/health` | public | Liveness check → `{"status":"ok"}` |
| GET | `/api/auth/login` | public | Starts Microsoft sign-in (redirects) |
| GET | `/api/auth/me` | public | Current user + `{configured, enforced}` |
| POST | `/api/auth/logout` | public | Clears the session cookie |

### Team & workload
| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/api/team` | read | Members with workload, status, active tasks |
| POST | `/api/team/member` | L2+ | Add a member |
| DELETE | `/api/team/member/{login}` | L2+ | Remove a member |

### Assignments (the task board)
| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/api/assignments` | read | All tasks (scoped) |
| POST | `/api/assignments` | L2+ | Create a task |
| PUT | `/api/assignments/{id}` | L2+ | Edit a task |
| PATCH | `/api/assignments/{id}/assign` | L2+ | Assign people (auto-notifies) |
| DELETE | `/api/assignments/{id}` | L2+ | Delete a task |

### Program views
| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/api/projects` | read | Projects/repos |
| GET | `/api/roadmap` | read | Milestones/timeline |
| GET | `/api/priorities` | read | Ranked priorities |
| GET | `/api/summary` | read | AI executive summary |
| GET | `/api/graph` | read | Knowledge-graph nodes/edges |

### AI assistant & reports
| Method | Path | Role | Notes |
|--------|------|------|-------|
| POST | `/api/chat` | L1+ | Ask a question; body `{message, history, include_github}` |
| POST | `/api/notes/generate` | L1+ | Generate a status report; body `{prompt, scope}` |
| GET | `/api/notes` | L1+ | List saved reports/notes |
| POST | `/api/notes` | L1+ | Save a manual note |

### Email → calendar (per-user)
| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/api/me/inbox` | L1+ | Is my inbox connected |
| POST | `/api/me/scan` | L1+ | Scan my inbox → meeting/task proposals |
| POST | `/api/me/calendar/confirm` | L1+ | Confirm proposals → board + Outlook |

### Admin
| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/api/users` | L2+ | List users + roles |
| PUT | `/api/users/{email}/role` | L2+ | Change a role (strictly-below only) |
| POST | `/api/sync` | L2+ | Refresh GitHub snapshot |

*(Full list, including request/response schemas, is live at `/docs`.)*

---

## Example requests

```bash
BASE="https://10.200.211.108:8443"
SESSION="paste-your-pm_session-cookie-here"

# Who am I
curl -sk -b "pm_session=$SESSION" "$BASE/api/auth/me"

# The team
curl -sk -b "pm_session=$SESSION" "$BASE/api/team"

# Ask the AI
curl -sk -b "pm_session=$SESSION" -X POST "$BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Who is most overloaded this week?","history":[]}'

# Generate a status report
curl -sk -b "pm_session=$SESSION" -X POST "$BASE/api/notes/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"","scope":"all"}'

# Create + assign a task (L2+)
AID=$(curl -sk -b "pm_session=$SESSION" -X POST "$BASE/api/assignments" \
  -H "Content-Type: application/json" \
  -d '{"title":"Ship the release","due_date":"2026-08-01","priority":"high"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sk -b "pm_session=$SESSION" -X PATCH "$BASE/api/assignments/$AID/assign" \
  -H "Content-Type: application/json" -d '{"assignees":["bobby_lee"]}'
```

---

## Quick test
Run the bundled smoke test against any deploy:
```bash
BASE="https://10.200.211.108:8443" PM_SESSION="<your-cookie>" ./scripts/test_api.sh
```
It checks health, auth, the read endpoints, an AI chat, and a report, and prints
a pass/fail summary. See the script for details.
