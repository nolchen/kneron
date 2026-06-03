# Email Setup — Connect Microsoft 365 Inboxes

This turns on the **Email** tab so each teammate can connect their own Outlook/Microsoft 365
inbox and let the AI read it. You do this **once** (it registers the app with Microsoft);
after that, each person just clicks "Connect an inbox."

You need a **Microsoft account** that can register an app in Azure / Entra. Most work
accounts can; if yours is locked down, your IT admin does Part 1 and hands you the values.

---

## Part 1 — Register the app in Azure (one time, ~5 min)

1. Go to **portal.azure.com** → sign in.
2. Search for **"Microsoft Entra ID"** (formerly Azure Active Directory) → open it.
3. Left menu → **App registrations** → **+ New registration**.
4. Fill in:
   - **Name:** `PM Agent`
   - **Supported account types:**
     - Just your company → *"Accounts in this organizational directory only"*
     - Any Microsoft account → *"Accounts in any organizational directory and personal Microsoft accounts"*
   - **Redirect URI:** choose **Web**, value:
     ```
     http://localhost:8000/api/email/callback
     ```
     (When you deploy, you'll add your live backend URL + `/api/email/callback` here too.)
5. Click **Register**.

You'll land on the app's **Overview** page. Copy these two values:
- **Application (client) ID**  →  this is `MS_CLIENT_ID`
- **Directory (tenant) ID**    →  this is `MS_TENANT_ID`

---

## Part 2 — Create a client secret

1. In your app → left menu → **Certificates & secrets**.
2. **Client secrets** tab → **+ New client secret**.
3. Description: `pm-agent`, Expires: 24 months → **Add**.
4. **Copy the secret's `Value` immediately** (not the "Secret ID" — the **Value**).
   It's only shown once. This is `MS_CLIENT_SECRET`.

---

## Part 3 — Add the email permissions

1. In your app → left menu → **API permissions**.
2. **+ Add a permission** → **Microsoft Graph** → **Delegated permissions**.
3. Search and tick each of these:
   - `Mail.Read`
   - `User.Read`
   - `offline_access`
4. **Add permissions**.
5. (Optional but nice) **Grant admin consent for [your org]** — if you can, click it so
   teammates don't each see a consent prompt. If the button is greyed out, no problem —
   each person just approves once when they connect.

> **Delegated** is the key word — it means the app only ever reads a mailbox *that the
> signed-in person personally approved*. Nobody's inbox is touched without their click.

---

## Part 4 — Put the values in the backend

Edit `Kneron/backend/.env` (create it from `.env.example` if it doesn't exist) and fill in:

```
MS_CLIENT_ID=<Application (client) ID from Part 1>
MS_CLIENT_SECRET=<the secret Value from Part 2>
MS_TENANT_ID=<Directory (tenant) ID from Part 1, or "common" for personal accounts>
MS_REDIRECT_URI=http://localhost:8000/api/email/callback
FRONTEND_URL=http://localhost:3000
```

Restart the backend:

```bash
bash start.sh
```

---

## Part 5 — Connect an inbox

1. Open the app → **Email** tab. It should now say it's configured.
2. Click **Connect an inbox** → you're sent to the Microsoft sign-in.
3. Sign in, approve the access request → you're bounced back to the app.
4. Your inbox now shows under **Connected inboxes**.
5. Click **Sync emails now** → recent emails are pulled in.
6. Go to **AI PM Chat** and ask something like *"summarize the recent emails"* or
   *"did anyone email about a deadline?"* — the AI now answers from your inbox.

Each teammate repeats Part 5 on their own to connect their own inbox.

---

## When you deploy (later)

In the Azure app's **Authentication** page, add a second redirect URI pointing at your
live backend, e.g. `https://pm-agent-api.onrender.com/api/email/callback`, and set
`MS_REDIRECT_URI` + `FRONTEND_URL` to the deployed URLs in your host's env vars.

## Notes & limits

- **Privacy:** the app only reads inboxes people explicitly connect. Disconnecting (the
  trash icon on the Email tab) removes the stored token.
- **Security:** refresh tokens are stored in the local SQLite DB. Fine for a small trusted
  team; for wider use you'd encrypt them or use a secrets store.
- **What it reads:** the 20 most recent messages per inbox (subject, sender, preview) on
  each sync. It does not send, delete, or modify anything — read-only.
