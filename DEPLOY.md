# Deploying PM Agent for a Team (Free)

This takes you from "runs on my laptop" to "my teammates open a URL and sign in
with their Microsoft account."

**Architecture when deployed:**
```
  Browsers ──► Vercel (frontend, free)
                  │  Next.js rewrites /api/* server-side (same-origin proxy)
                  ▼
              Render (backend, free)  ──►  Neon Postgres (data, free)
                  │                   ──►  Groq (hosted AI, free)
                  ▼
              Microsoft 365 / Entra (sign-in + email/calendar)
```

> **Why the proxy matters:** the browser only ever talks to the Vercel domain;
> Next forwards `/api/*` to Render behind the scenes. This keeps the session
> cookie **first-party**, which is required — modern browsers (Safari + Chrome)
> block third-party cookies, so a direct cross-origin Vercel→Render call would
> break login. Do **not** set `NEXT_PUBLIC_API_URL`; use `BACKEND_ORIGIN`.

Accounts you'll need (all free, no card for the core path): **Vercel**,
**Render**, **Neon**, **Groq**, and an **Azure / Microsoft 365** tenant you can
register an app in.

---

## Part 1 — Groq API key (the AI)

1. **console.groq.com** → sign up → **API Keys** → **Create API Key** (`gsk_…`).

---

## Part 2 — Neon Postgres (persistent data)

Render's free disk is wiped on every sleep/redeploy, so use a free Postgres so
data actually sticks. The app supports it out of the box (no code change).

1. **neon.tech** → sign up → **New Project**.
2. Copy the connection string — looks like:
   ```
   postgresql://USER:PASSWORD@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require
   ```
   Keep the `?sslmode=require` — Neon needs it. You'll paste this as
   `DATABASE_URL` in Part 4.

---

## Part 3 — Azure app registration (sign-in + email)

Sign-in and the email→calendar feature use Microsoft Graph.

1. **portal.azure.com** → **App registrations** → **New registration** (or open
   your existing "PM Agent" app). Note the **Application (client) ID** and
   **Directory (tenant) ID**.
2. **Certificates & secrets** → **New client secret** → copy the value (this is
   `MS_CLIENT_SECRET`; you can't see it again).
3. **API permissions** → add **Microsoft Graph → Delegated**: `Mail.Read`,
   `Calendars.ReadWrite`, `User.Read`, `offline_access` → then **Grant admin
   consent** (an admin must click this; it's required for mail/calendar).
4. **Authentication** → **Add a platform → Web** → add these redirect URIs.
   They point at your **Vercel** host (so the OAuth callback comes back through
   the proxy and the cookie is first-party):
   ```
   https://<your-app>.vercel.app/api/auth/callback
   https://<your-app>.vercel.app/api/email/callback
   ```
   (You can keep `http://localhost:8000/...` URIs too, for local dev.)

> Redirect URIs must match **exactly** (scheme, host, path, no trailing slash)
> and be **HTTPS** for non-localhost — Vercel gives you HTTPS automatically.

---

## Part 4 — Deploy the backend to Render

1. Push your code to GitHub (done).
2. **render.com** → **New** → **Blueprint** → connect the repo. Render reads
   `render.yaml` and pre-fills the service.
3. Set these environment variables (the `sync: false` ones it prompts for):

   | Variable | Value |
   |---|---|
   | `GROQ_API_KEY` | your key from Part 1 |
   | `DATABASE_URL` | your Neon string from Part 2 |
   | `SESSION_SECRET` | a long random string (e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`) — keep it stable |
   | `MS_CLIENT_ID` / `MS_CLIENT_SECRET` / `MS_TENANT_ID` | from Part 3 |
   | `MS_REDIRECT_URI` | `https://<your-app>.vercel.app/api/email/callback` |
   | `MS_LOGIN_REDIRECT_URI` | `https://<your-app>.vercel.app/api/auth/callback` |
   | `FRONTEND_URL` | `https://<your-app>.vercel.app` |
   | `ALLOWED_ORIGINS` | `https://<your-app>.vercel.app` |
   | `FIRST_ADMIN_EMAIL` | the email that should be the first L3 admin |
   | `AUTH_ENFORCED` | `true` |
   | `SEED_DEMO_DATA` | `false` |
   | `COOKIE_SECURE` | `true` |

4. **Apply / Deploy.** Copy the public URL (e.g. `https://pm-agent-api-xxxx.onrender.com`).
5. Test: open `<that URL>/api/health` → `{"status":"ok"}`.

> **Startup fails on purpose** if `AUTH_ENFORCED=true` but `SESSION_SECRET` or
> the `MS_*` creds are missing — it refuses to boot wide-open. If the deploy
> exits with that error, fill in those vars and redeploy.

> **Notes search (optional):** Groq has no embeddings API. For the AI to search
> past reports, set `EMBED_PROVIDER=openai` + `OPENAI_API_KEY` (pennies). For
> fully free, leave `EMBED_PROVIDER=none` — everything works except semantic
> note search.

---

## Part 5 — Deploy the frontend to Vercel

1. **vercel.com** → **Add New Project** → import the repo.
2. Set **Root Directory** to `frontend`.
3. Add **one** environment variable (Production):
   ```
   BACKEND_ORIGIN = https://pm-agent-api-xxxx.onrender.com   (your Render URL)
   ```
   ⚠️ Do **not** set `NEXT_PUBLIC_API_URL` — it bypasses the proxy and brings the
   login loop back. `BACKEND_ORIGIN` is what the Next rewrite proxies to.
4. **Deploy.** You get `https://<your-app>.vercel.app`.
5. Go there → **Sign in with Microsoft**. You should land in the dashboard. The
   first person to sign in (or `FIRST_ADMIN_EMAIL`) becomes the L3 admin.

---

## Part 6 — Each person connects their own inbox

On the **Email** page (or **My Tasks**), each user clicks **Connect / Sign in
with Microsoft** to grant access to *their own* mailbox. The AI then scans their
inbox, extracts meetings/deadlines, and writes them to their calendar and the
board — only their own data, never anyone else's.

---

## Roles

- **L3 (admin):** add/remove members, change roles (up to L2), create/assign tasks.
- **L2 (manager):** create/assign tasks, add L1 members.
- **L1 (intern):** read-only on their own tasks.

Manage these in **Users & Roles** (L3 only). You can't change your own role or
grant a level at/above your own — no self-promotion.

---

## Free-tier quirk (just one now)

Render's free instance **sleeps after ~15 min of inactivity** — the first visit
after that takes ~30–50s to wake up, then it's fast again. Annoying, not broken.

Data **persists** (it's in Neon, not Render's disk), so sleep/redeploys no longer
wipe anything. To kill the wake-up delay entirely, upgrade Render to ~$7/mo.

---

## Costs

| Service | Cost |
|---------|------|
| Vercel  | Free |
| Render  | Free (sleeps), or ~$7/mo always-on |
| Neon    | Free persistent Postgres |
| Groq    | Free tier |
| OpenAI embeddings | optional, ~pennies/mo (skip for fully free) |

**Fully free path = $0.** Just live with the cold-start delay.

---

## Quick troubleshooting

| Symptom | Cause / fix |
|---|---|
| `DNS_HOSTNAME_RESOLVED_PRIVATE` / 404 on Vercel | `BACKEND_ORIGIN` not set on Vercel → the proxy has no target. Set it, redeploy. |
| Sign in loops back to the login page | `NEXT_PUBLIC_API_URL` is set (remove it), or `MS_*REDIRECT_URI` points at the Render host instead of the **Vercel** host. |
| `AADSTS50011` (redirect mismatch) | The Vercel callback URLs aren't registered in Azure (Part 3, step 4). |
| "Email not configured" | `MS_CLIENT_ID` / `MS_CLIENT_SECRET` not set on Render. |
| `AADSTS65001` (not consented) | Admin consent not granted for the Graph scopes (Part 3, step 3). |
| Backend exits on deploy | `AUTH_ENFORCED=true` but `SESSION_SECRET` / `MS_*` missing — set them. |
