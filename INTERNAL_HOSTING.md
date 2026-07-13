# Hosting PM Agent on an internal Kneron machine

Run the whole app on **one always-on machine** inside Kneron's network. Everyone
on the office network/VPN opens it at `http://<machine-ip>:3000` (or a friendly
internal hostname). One backend, one database — everyone sees the same data, and
nothing is exposed to the public internet.

This is a good fit because PM Agent reads employees' inboxes: keeping it on the
internal network means that data never leaves the company.

---

## What runs
Two processes on the same machine:

| Process  | Command                                   | Port | Bound to  |
|----------|-------------------------------------------|------|-----------|
| Backend  | `uvicorn main:app`                        | 8000 | `0.0.0.0` |
| Frontend | `next start -H 0.0.0.0`                   | 3000 | `0.0.0.0` |

`0.0.0.0` is the important part — it means "reachable by the machine's IP,"
not just `localhost`. The browser only ever talks to the frontend (`:3000`),
which proxies `/api/*` to the backend on the same box.

---

## Option A — quick trial (one command)
On the machine, after cloning the repo and creating `backend/.env`:

```bash
./start-server.sh
```

It builds the frontend, starts both servers bound to `0.0.0.0`, and prints the
shareable URL. Good for a first test. **It stops when you close the terminal**,
so use Option B for a real deployment.

---

## Option B — proper always-on install (Linux + systemd)
So it survives logout and reboots. Assumes the repo lives at `/opt/pm-agent`
owned by a `pmagent` user — adjust the paths/user in the two unit files if not.

```bash
# 1. Get the code + deps onto the machine
sudo git clone <your repo> /opt/pm-agent
cd /opt/pm-agent
bash backend/setup.sh                      # backend venv + deps
cp backend/.env.example backend/.env       # then fill in the real values
cd frontend && npm install && npm run build && cd ..

# 2. Install the services (edit paths/user inside them first if needed)
sudo cp deploy/pm-agent-backend.service  /etc/systemd/system/
sudo cp deploy/pm-agent-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pm-agent-backend pm-agent-frontend

# 3. Check they're up
systemctl status pm-agent-backend pm-agent-frontend
```

After any code update: `git pull`, rebuild the frontend (`cd frontend && npm run
build`), then `sudo systemctl restart pm-agent-frontend pm-agent-backend`.

*(No systemd? `pm2` works too: `pm2 start` each command with the same env, then
`pm2 save && pm2 startup`.)*

---

## Required environment
- **`backend/.env`** — `GROQ_API_KEY`, the Microsoft app creds, `COOKIE_SECURE=false`
  (until you put HTTPS in front — see below), `SEED_DEMO_DATA=false`.
- **Frontend** — `BACKEND_ORIGIN=http://localhost:8000` (set in the service file /
  `start-server.sh`). **Leave `NEXT_PUBLIC_API_URL` unset** so the browser uses
  same-origin; if it's set to a URL at build time, every visitor's browser calls
  that URL directly instead of this server.

---

## Firewall
Open the two ports on the machine so the network can reach them:

```bash
# Linux (ufw)
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp     # only needed if you want /docs reachable off-box
```

---

## ⚠️ Microsoft email login needs HTTPS — the one real blocker
Microsoft Entra (Azure) **only allows `http://` redirect URIs for `localhost`.**
For any other address — including `http://10.0.4.17:3000` — it **requires
`https://`.** So on a plain-`http` IP, sign-in and the email→calendar feature
will fail (Azure rejects the redirect).

**The fix (needs Kneron IT):** give the machine an internal hostname and an
HTTPS certificate, and put a small reverse proxy in front. [Caddy](https://caddyserver.com)
is the easiest — this whole `Caddyfile` is enough:

```
pm-agent.kneron.us {
    reverse_proxy localhost:3000
}
```

Then:
1. Register `https://pm-agent.kneron.us/api/auth/callback` as a redirect URI in
   the Azure app (Authentication → Add a platform → Web).
2. Set `backend/.env` → the redirect/base URLs to `https://pm-agent.kneron.us`
   and `COOKIE_SECURE=true`.

Everything *except* Microsoft login/email works fine on plain `http://IP:3000`
if you want to demo before IT sets up the cert.

---

## Note for Kneron IT (hand them this)
> We want to host an internal tool (Next.js + FastAPI) on a Linux machine on the
> office network. We need:
> 1. An always-on machine/VM with a **static internal IP**.
> 2. An **internal DNS hostname** for it (e.g. `pm-agent.kneron.us`).
> 3. An **HTTPS certificate** for that hostname (internal CA is fine) — required
>    because Microsoft sign-in rejects non-HTTPS redirect URIs.
> 4. Firewall: allow **443** (and **3000** if not using the reverse proxy) to the
>    machine from the office network/VPN.
>
> We'll handle the app, the reverse proxy (Caddy), and the Azure app registration.
