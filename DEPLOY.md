# Deploying PM Agent for a Team (Free)

This takes you from "runs on my laptop" to "my teammates open a URL."

**Architecture when deployed:**
```
  Teammates' browsers ──► Vercel (frontend, free)
                              │
                              ▼
                          Render (backend, free)
                              │
                              ▼
                          Groq (free hosted AI)
```

Three free accounts: **Vercel**, **Render**, **Groq**. No credit card needed for the free path.

---

## Part 1 — Get a Groq API key (the AI)

1. **console.groq.com** → sign up (free, no card).
2. **API Keys** → **Create API Key** → copy it (starts with `gsk_`).

---

## Part 2 — Deploy the backend to Render

1. Make sure your code is pushed to GitHub (done).
2. **render.com** → sign up → **New** → **Blueprint**.
3. Connect your GitHub repo. Render finds `Kneron/backend/render.yaml` and sets everything up.
4. It'll prompt you for the secret values:
   - `GROQ_API_KEY` = your key from Part 1
   - `ALLOWED_ORIGINS` = leave blank for now (you'll fill it after Part 3)
   - `OPENAI_API_KEY` = see the note below
5. Click **Apply / Deploy**. Wait a few minutes.
6. Copy the public URL (e.g. `https://pm-agent-api.onrender.com`).
7. Test it: open `<that URL>/api/health` → you should see `{"status":"ok",...}`.

> **Notes search (optional):** Groq has no embeddings API, so the AI's ability to
> search past reports needs OpenAI embeddings (costs pennies, but needs a card).
> - **Want it?** Set `EMBED_PROVIDER=openai` and add `OPENAI_API_KEY`.
> - **Want fully free?** In the Render dashboard set `EMBED_PROVIDER=none-skip` (any non-openai value). The app still works — chat, assignments, reports all run. The AI just won't pull from saved notes. Reports still generate; they just won't be searchable.

---

## Part 3 — Deploy the frontend to Vercel

1. **vercel.com** → sign up → **Add New Project** → import your repo.
2. Set **Root Directory** to `Kneron/frontend`.
3. Add an **Environment Variable**:
   ```
   NEXT_PUBLIC_API_URL = https://pm-agent-api.onrender.com   (your Render URL)
   ```
4. **Deploy.** Vercel gives you a URL like `https://your-app.vercel.app`.
5. **Back in Render**, set `ALLOWED_ORIGINS` to that Vercel URL → save (it redeploys).

---

## Part 4 — Share it

Send teammates the Vercel URL. They all hit the same backend, so everyone sees the same data.

---

## The two free-tier quirks (important)

Render's free tier has two limitations you should know about:

1. **It sleeps after 15 min of inactivity.** The first visit after that takes ~30 seconds
   to wake up (you'll see a loading spinner). Then it's fast again. Annoying, not broken.

2. **Storage is ephemeral — data resets when the service restarts** (after sleep or a
   redeploy). So your team's assignments/team edits are *not* permanently saved on the free
   tier. On restart it reloads the demo data fresh.

   This is fine for a **demo or short-lived trial**. For data that truly sticks around, you'd
   either:
   - pay Render ~$7/mo for a persistent disk, **or**
   - connect a free hosted Postgres (Neon / Supabase have genuinely-free persistent tiers) —
     this needs a small code change to `db.py`, ask and I'll do it.

---

## Costs

| Service | Cost |
|---------|------|
| Vercel  | Free |
| Render  | Free (sleeps + resets), or ~$7/mo for always-on + persistent disk |
| Groq    | Free tier |
| OpenAI embeddings | optional, ~pennies/mo (skip for fully free) |

**Fully free path = $0.** Just live with the sleep delay and data resets.

## No login yet

Anyone with the URL can view and edit. Fine for a trusted small team; add auth before going wider.
