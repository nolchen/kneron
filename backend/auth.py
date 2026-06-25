"""
Authentication + roles.

Sign-in is Microsoft (Entra ID) OAuth — the same Azure app already used for the
email/calendar integration. On callback we look the person up in the `users`
table, mint a signed JWT, and drop it in an httpOnly cookie. Every request then
carries that cookie; `current_user` decodes it back to a user record.

Roles are tiered levels L1 < L2 < L3 (L1 lowest, L3 highest):
  - L3 (honcho)  : everything, incl. changing other people's roles
  - L2 (manager) : assign / edit tasks for anyone (e.g. give an L1 work)
  - L1 (intern)  : see the board, work their own tasks

Rollout safety: gating only takes effect when AUTH_ENFORCED is on. While it's
off (the default), the role dependencies pass through as a synthetic L3, so
the existing demo keeps working until SSO is wired up and you flip the switch.
"""

import os
import secrets
import time

import jwt  # PyJWT
import msal
from fastapi import HTTPException, Request

import db

ROLES = ("L1", "L2", "L3")  # ordered low -> high


def rank(role: str) -> int:
    """Numeric rank of a role; -1 if unknown. L1=0 < L2=1 < L3=2."""
    return ROLES.index(role) if role in ROLES else -1


def can_grant(actor_role: str, target_role: str) -> bool:
    """True if an actor may assign `target_role` to someone — only levels
    STRICTLY below the actor's own. So L3 manages up to L2, L2 up to L1, and
    nobody can mint another L3 through the API (the top admin is env-pinned).

    Fail closed on an unrecognized role on either side: an unknown/legacy role
    string (e.g. one that escaped the L1/L2/L3 migration) is treated as
    ungrantable and untouchable rather than ranking below everyone."""
    a, t = rank(actor_role), rank(target_role)
    if a < 0 or t < 0:
        return False
    return a > t

SESSION_COOKIE = "pm_session"
OAUTH_STATE_COOKIE = "pm_oauth_state"
_TOKEN_TTL = 60 * 60 * 24 * 7  # 7 days
# Sign-in only needs identity. Mailbox + calendar access is a SEPARATE, opt-in
# consent handled by the Connect-Email flow (email_client.SCOPES) — so just
# logging into the dashboard never requires mail/calendar permissions (and thus
# no admin-consent wall for plain sign-in). MSAL adds openid/profile/email
# automatically.
LOGIN_SCOPES = ["User.Read"]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Known, public fallback used only for local/demo runs. Signing real sessions
# with this would let anyone forge a token, so enforcement refuses to use it.
_DEFAULT_SECRET = "dev-insecure-change-me"


def _secret() -> str:
    # Falls back to a dev secret so local runs work; set SESSION_SECRET in prod.
    return os.environ.get("SESSION_SECRET", _DEFAULT_SECRET)


def auth_enforced() -> bool:
    return os.environ.get("AUTH_ENFORCED", "").lower() in ("1", "true", "yes", "on")


def is_configured() -> bool:
    return bool(os.environ.get("MS_CLIENT_ID") and os.environ.get("MS_CLIENT_SECRET"))


def enforcement_config_errors() -> list[str]:
    """Companion config that MUST be present before AUTH_ENFORCED can safely be
    on. Returns human-readable problems; empty means safe to enforce. Each item
    is a way enforcement would otherwise fail *open* (anyone gets in / becomes
    admin), so startup raises on any of them rather than booting wide open."""
    if not auth_enforced():
        return []
    problems = []
    if _secret() == _DEFAULT_SECRET:
        problems.append(
            "SESSION_SECRET is unset — session tokens would be signed with a "
            "public default key, so anyone could forge an admin session."
        )
    if not is_configured():
        problems.append(
            "MS_CLIENT_ID / MS_CLIENT_SECRET are unset — Microsoft SSO is the "
            "only real login under enforcement, and dev-login would stay open."
        )
    if not os.environ.get("FIRST_ADMIN_EMAIL", "").strip():
        problems.append(
            "FIRST_ADMIN_EMAIL is unset — the first person to sign in would "
            "auto-become L3 (honcho)."
        )
    return problems


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


# --- CSRF protection: the `state` param is bound to a short-lived cookie set at
# login start and verified on callback, so an attacker can't forge a callback. ---

def new_state() -> str:
    return secrets.token_urlsafe(24)


def state_cookie_kwargs() -> dict:
    # The Connect-Email flow sets this via a cross-origin fetch, so cross-site
    # (Vercel↔Render) needs SameSite=None + Secure or the browser drops it as a
    # third-party cookie. Locally (same-site localhost over http) fall back to lax.
    secure = os.environ.get("COOKIE_SECURE", "true").lower() != "false"
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "none" if secure else "lax",
        "max_age": 600,
        "path": "/",
    }


def verify_state(received: str, expected: str) -> bool:
    return bool(received and expected and secrets.compare_digest(received, expected))


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
    sign in) becomes L3 (honcho) so there's always someone who can manage roles."""
    first_admin = os.environ.get("FIRST_ADMIN_EMAIL", "").lower()
    if first_admin and email == first_admin:
        return "L3"
    # Bootstrap convenience for local/demo only: the first user becomes L3 so
    # there's always an admin. Under enforcement this is unsafe (a stranger
    # could win the race to the public callback), and the startup guard already
    # requires FIRST_ADMIN_EMAIL there — so never auto-grant L3 when enforced.
    if not auth_enforced() and db.count_users() == 0:
        return "L3"
    return "L1"


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

_DEV_ADMIN = {"email": "dev@local", "name": "Dev (auth off)", "role": "L3"}


def require_user(request: Request) -> dict:
    u = current_user(request)
    if u:
        return u
    if not auth_enforced():
        return _DEV_ADMIN
    raise HTTPException(401, "Not signed in")


def require_role(*roles: str):
    """Dependency factory: Depends(require_role('L2','L3'))."""
    def dep(request: Request) -> dict:
        u = require_user(request)
        if not auth_enforced():
            return u
        if u["role"] not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(roles)}")
        return u
    return dep


require_manager = require_role("L2", "L3")   # L2 (manager) and up
require_admin = require_role("L3")           # L3 (honcho) only
