"""
Authentication + roles.

Sign-in is Microsoft (Entra ID) OAuth — the same Azure app already used for the
email/calendar integration. On callback we look the person up in the `users`
table, mint a signed JWT, and drop it in an httpOnly cookie. Every request then
carries that cookie; `current_user` decodes it back to a user record.

Roles: admin > manager > intern.
  - admin   : everything, incl. changing other people's roles
  - manager : assign / edit tasks for anyone (e.g. give an intern work)
  - intern  : see the board, work their own tasks

Rollout safety: gating only takes effect when AUTH_ENFORCED is on. While it's
off (the default), the role dependencies pass through as a synthetic admin, so
the existing demo keeps working until SSO is wired up and you flip the switch.
"""

import os
import time

import jwt  # PyJWT
import msal
from fastapi import HTTPException, Request

import db

ROLES = ("admin", "manager", "intern")

SESSION_COOKIE = "pm_session"
_TOKEN_TTL = 60 * 60 * 24 * 7  # 7 days
# Sign-in is unified with mailbox + calendar access: one Microsoft consent grants
# identity AND the Graph scopes the AI needs to scan the person's inbox and write
# to their calendar. MSAL adds openid/profile/email/offline_access automatically
# (offline_access is what yields the refresh token we store).
LOGIN_SCOPES = ["User.Read", "Mail.Read", "Calendars.ReadWrite"]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _secret() -> str:
    # Falls back to a dev secret so local runs work; set SESSION_SECRET in prod.
    return os.environ.get("SESSION_SECRET", "dev-insecure-change-me")


def auth_enforced() -> bool:
    return os.environ.get("AUTH_ENFORCED", "").lower() in ("1", "true", "yes", "on")


def is_configured() -> bool:
    return bool(os.environ.get("MS_CLIENT_ID") and os.environ.get("MS_CLIENT_SECRET"))


def _redirect_uri() -> str:
    return os.environ.get("MS_LOGIN_REDIRECT_URI", "http://localhost:8000/api/auth/callback")


def _ms_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=os.environ["MS_CLIENT_ID"],
        client_credential=os.environ["MS_CLIENT_SECRET"],
        authority=f"https://login.microsoftonline.com/{os.environ.get('MS_TENANT_ID', 'common')}",
    )


def cookie_kwargs() -> dict:
    """Cookie attributes. Cross-site (Vercel↔Render) needs SameSite=None + Secure,
    which requires HTTPS — so for local http set COOKIE_SECURE=false."""
    secure = os.environ.get("COOKIE_SECURE", "true").lower() != "false"
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "none" if secure else "lax",
        "max_age": _TOKEN_TTL,
        "path": "/",
    }


# ---------------------------------------------------------------------------
# Microsoft OAuth (login)
# ---------------------------------------------------------------------------

def login_url(state: str) -> str:
    return _ms_app().get_authorization_request_url(
        LOGIN_SCOPES, state=state, redirect_uri=_redirect_uri(), prompt="select_account"
    )


def exchange_code(code: str) -> dict:
    """Trade the auth code for the person's email + name + a refresh token
    (the refresh token lets the AI read their inbox / write their calendar later)."""
    res = _ms_app().acquire_token_by_authorization_code(
        code, scopes=LOGIN_SCOPES, redirect_uri=_redirect_uri()
    )
    if "access_token" not in res:
        raise RuntimeError(res.get("error_description", "Microsoft login failed"))
    claims = res.get("id_token_claims", {}) or {}
    email = (claims.get("preferred_username") or claims.get("email") or "").lower()
    if not email:
        raise RuntimeError("Could not read an email from the Microsoft account")
    return {
        "email": email,
        "name": claims.get("name", email),
        "refresh_token": res.get("refresh_token", ""),
    }


# ---------------------------------------------------------------------------
# Users + sessions
# ---------------------------------------------------------------------------

def decide_role(email: str) -> str:
    """Role for a brand-new user. FIRST_ADMIN_EMAIL (or the very first person to
    sign in) becomes admin so there's always someone who can manage roles."""
    first_admin = os.environ.get("FIRST_ADMIN_EMAIL", "").lower()
    if first_admin and email == first_admin:
        return "admin"
    if db.count_users() == 0:
        return "admin"
    return "intern"


def login_user(email: str, name: str) -> dict:
    existing = db.get_user(email)
    role = existing["role"] if existing else decide_role(email)
    return db.upsert_user(email=email, name=name, role=role)


def make_session_token(email: str) -> str:
    now = int(time.time())
    return jwt.encode({"sub": email, "iat": now, "exp": now + _TOKEN_TTL}, _secret(), algorithm="HS256")


def current_user(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = jwt.decode(token, _secret(), algorithms=["HS256"])
    except Exception:
        return None
    email = data.get("sub")
    return db.get_user(email) if email else None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

_DEV_ADMIN = {"email": "dev@local", "name": "Dev (auth off)", "role": "admin"}


def require_user(request: Request) -> dict:
    u = current_user(request)
    if u:
        return u
    if not auth_enforced():
        return _DEV_ADMIN
    raise HTTPException(401, "Not signed in")


def require_role(*roles: str):
    """Dependency factory: Depends(require_role('admin','manager'))."""
    def dep(request: Request) -> dict:
        u = require_user(request)
        if not auth_enforced():
            return u
        if u["role"] not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(roles)}")
        return u
    return dep


require_manager = require_role("admin", "manager")
require_admin = require_role("admin")
