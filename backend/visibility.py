"""
Role-scoped visibility — decides which team members (and their tasks) a given
signed-in user is allowed to see.

Model: each user has a `manager_email` (their boss). A signed-in user is linked
to a team member by matching email (users.email == team_members.email).

  L3 (honcho)  -> everyone
  L2 (manager) -> themselves + their direct reports (users whose manager is them)
  L1 (intern)  -> themselves + peers (other users under the same manager)

A return of None means "no restriction" (see everyone) — used for L3 and for
demo mode (auth not enforced), so the open demo keeps working unchanged.
"""

import auth
import db


def _email_to_login() -> dict[str, str]:
    """Map a person's email -> their team-member login (the id used on tasks)."""
    return {
        m["email"].lower(): m["login"]
        for m in db.get_team_members()
        if m.get("email")
    }


def visible_emails(user: dict) -> set[str] | None:
    """Set of user emails this person may see, or None for everyone (L3)."""
    role = user.get("role")
    me = (user.get("email") or "").lower()
    if role == "L3":
        return None

    users = db.list_users()
    seen = {me}
    if role == "L2":
        # self + direct reports
        seen |= {u["email"].lower() for u in users if (u.get("manager_email") or "").lower() == me}
    else:
        # intern: self + peers under the same manager
        my_mgr = (user.get("manager_email") or "").lower()
        if my_mgr:
            seen |= {u["email"].lower() for u in users if (u.get("manager_email") or "").lower() == my_mgr}
    return seen


def visible_logins(user: dict) -> set[str] | None:
    """Set of team-member logins this person may see, or None for everyone."""
    emails = visible_emails(user)
    if emails is None:
        return None
    e2l = _email_to_login()
    return {e2l[e] for e in emails if e in e2l}


def scope_for(request) -> set[str] | None:
    """Logins visible to the requester. None = no filter (see all).
    - auth not enforced (demo): None (everyone), so nothing changes.
    - enforced + signed in: that user's visible logins.
    - enforced + not signed in: empty set (see nothing).
    """
    if not auth.auth_enforced():
        return None
    user = auth.current_user(request)
    if not user:
        return set()
    return visible_logins(user)


def can_manage(request) -> bool:
    """Whether the requester may create/assign/edit tasks (L2 or L3).
    True in demo mode so the open demo keeps full controls."""
    if not auth.auth_enforced():
        return True
    user = auth.current_user(request)
    return bool(user and user.get("role") in ("L2", "L3"))
