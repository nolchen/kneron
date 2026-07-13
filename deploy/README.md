# deploy/

systemd unit files for running PM Agent as an always-on service on an internal
Linux machine.

- `pm-agent-backend.service` — FastAPI backend (uvicorn, port 8000)
- `pm-agent-frontend.service` — Next.js frontend (port 3000, bound to `0.0.0.0`)

Full walkthrough (paths, env, firewall, and the Microsoft-login HTTPS
requirement) is in [`../INTERNAL_HOSTING.md`](../INTERNAL_HOSTING.md).

Quick install (adjust the `User`/paths inside the unit files first):

```bash
cd frontend && npm run build && cd ..          # build once before enabling
sudo cp deploy/pm-agent-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pm-agent-backend pm-agent-frontend
```
