"""
Microsoft 365 email integration (Option A — each user connects their own inbox).

OAuth2 authorization-code flow via MSAL. Each person logs into Microsoft and grants
read access to THEIR OWN mailbox (delegated Mail.Read). We store their refresh token
and use Microsoft Graph to pull recent emails, which then feed the RAG notes store.

Config (env — see .env.example):
  MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID (default "common"),
  MS_REDIRECT_URI (default http://localhost:8000/api/email/callback)
"""

import os
import httpx
import msal

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read", "User.Read"]  # offline_access is added automatically by MSAL


def _cfg() -> dict:
    return {
        "client_id":     os.environ.get("MS_CLIENT_ID", ""),
        "client_secret": os.environ.get("MS_CLIENT_SECRET", ""),
        "tenant":        os.environ.get("MS_TENANT_ID", "common"),
        "redirect_uri":  os.environ.get("MS_REDIRECT_URI", "http://localhost:8000/api/email/callback"),
    }


def is_configured() -> bool:
    c = _cfg()
    return bool(c["client_id"] and c["client_secret"])


def _app() -> msal.ConfidentialClientApplication:
    c = _cfg()
    return msal.ConfidentialClientApplication(
        client_id=c["client_id"],
        client_credential=c["client_secret"],
        authority=f"https://login.microsoftonline.com/{c['tenant']}",
    )


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------

def auth_url(state: str) -> str:
    """URL to send the user to so they can sign in and grant access."""
    return _app().get_authorization_request_url(
        SCOPES,
        state=state,
        redirect_uri=_cfg()["redirect_uri"],
        prompt="select_account",
    )


def exchange_code(code: str) -> dict:
    """Exchange the auth code for tokens. Returns dict with access_token,
    refresh_token, expires_in, and the account's email/name."""
    result = _app().acquire_token_by_authorization_code(
        code, scopes=SCOPES, redirect_uri=_cfg()["redirect_uri"],
    )
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "Token exchange failed"))

    claims = result.get("id_token_claims", {}) or {}
    email  = claims.get("preferred_username") or claims.get("email") or "unknown"
    name   = claims.get("name", email)
    return {
        "access_token":  result["access_token"],
        "refresh_token": result.get("refresh_token", ""),
        "email":         email,
        "name":          name,
    }


def refresh_access_token(refresh_token: str) -> str:
    """Get a fresh access token from a stored refresh token."""
    result = _app().acquire_token_by_refresh_token(refresh_token, scopes=SCOPES)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "Token refresh failed"))
    return result["access_token"]


# ---------------------------------------------------------------------------
# Graph — read mail
# ---------------------------------------------------------------------------

def fetch_recent_messages(access_token: str, top: int = 20) -> list[dict]:
    """Pull the most recent messages from the user's inbox."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "$top": str(top),
        "$select": "subject,from,receivedDateTime,bodyPreview",
        "$orderby": "receivedDateTime desc",
    }
    r = httpx.get(f"{GRAPH}/me/messages", headers=headers, params=params, timeout=30)
    r.raise_for_status()
    out = []
    for m in r.json().get("value", []):
        sender = (m.get("from", {}) or {}).get("emailAddress", {}) or {}
        out.append({
            "subject":  m.get("subject", "(no subject)"),
            "from":     sender.get("address", ""),
            "from_name": sender.get("name", ""),
            "received": m.get("receivedDateTime", ""),
            "preview":  m.get("bodyPreview", ""),
        })
    return out
