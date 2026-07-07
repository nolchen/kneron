"""
Test suite for the PM Agent backend.

Runs against an isolated temp database (DATA_DIR) so it never touches your real
pm_data.db. Uses FastAPI's TestClient — no running server needed.

Run with:   pytest -q
"""

import os
import tempfile
import importlib
import pytest

# Point all data at a throwaway dir BEFORE importing the app
_TMP = tempfile.mkdtemp(prefix="pm_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["VAULT_PATH"] = os.path.join(_TMP, "vault")
os.environ["LLM_PROVIDER"] = "ollama"  # not actually called in these tests
# Existing functional tests exercise features in open/demo mode; the dedicated
# RBAC test below flips enforcement on itself. (load_dotenv won't override these.)
os.environ["AUTH_ENFORCED"] = "false"

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def fresh_data():
    """Reset to demo data before each test for isolation."""
    main.db.init_db()
    main._seed_mock(reset_assignments=True)
    yield


# ---------------------------------------------------------------------------
# Health / basics
# ---------------------------------------------------------------------------

def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_team_seeded():
    r = client.get("/api/team")
    assert r.status_code == 200
    members = r.json()["team_members"]
    assert len(members) == 15
    # sorted by workload descending
    scores = [m["workload_score"] for m in members]
    assert scores == sorted(scores, reverse=True)


def test_projects_and_priorities():
    assert len(client.get("/api/projects").json()["projects"]) == 3
    pr = client.get("/api/priorities").json()["priorities"]
    # highest-priority issue (a blocker) should rank first
    assert "blocker" in pr[0]["labels"]


# ---------------------------------------------------------------------------
# Data integrity — the bug we just fixed
# ---------------------------------------------------------------------------

def test_all_assignees_are_real_team_members():
    team = {m["login"] for m in client.get("/api/team").json()["team_members"]}
    data = main._data_snapshot()
    for issue in data["issues"]:
        for a in issue["assignees"]:
            assert a in team, f"issue assignee {a} not on team"
    for pr in data["pull_requests"]:
        assert pr["author"] in team, f"PR author {pr['author']} not on team"
        for a in pr["assignees"]:
            assert a in team, f"PR assignee {a} not on team"


# ---------------------------------------------------------------------------
# Team CRUD
# ---------------------------------------------------------------------------

def test_add_and_remove_member():
    r = client.post("/api/team/member", json={"name": "Test Person", "role": "QA", "repos": "repo-a, repo-b"})
    assert r.status_code == 200
    assert r.json()["login"] == "test_person"
    assert r.json()["repos_active"] == ["repo-a", "repo-b"]

    # shows up in the team
    assert any(m["login"] == "test_person" for m in client.get("/api/team").json()["team_members"])

    # duplicate rejected
    assert client.post("/api/team/member", json={"name": "Test Person"}).status_code == 400

    # remove it
    assert client.delete("/api/team/member/test_person").status_code == 200
    assert client.delete("/api/team/member/test_person").status_code == 404


# ---------------------------------------------------------------------------
# Assignments + workload effect
# ---------------------------------------------------------------------------

def test_assignment_lifecycle_and_workload():
    # baseline workload for nolan_chen
    def score(login):
        return next(m["workload_score"] for m in client.get("/api/team").json()["team_members"] if m["login"] == login)

    base = score("nolan_chen")

    # create an unassigned high-priority task
    a = client.post("/api/assignments", json={
        "title": "Ship the thing", "assignees": [], "due_date": "2026-07-01",
        "priority": "high", "status": "todo", "notes": "",
    }).json()
    aid = a["id"]

    # unassigned → no workload change
    assert score("nolan_chen") == base

    # assign nolan → +5 for high priority, and status auto-flips to in-progress
    upd = client.patch(f"/api/assignments/{aid}/assign", json={"assignees": ["nolan_chen"]}).json()
    assert upd["status"] == "in-progress"
    assert score("nolan_chen") == round(base + 5, 1)

    # unassign → back to baseline + back to todo
    upd = client.patch(f"/api/assignments/{aid}/assign", json={"assignees": []}).json()
    assert upd["status"] == "todo"
    assert score("nolan_chen") == base

    # delete
    assert client.delete(f"/api/assignments/{aid}").status_code == 200
    assert client.delete(f"/api/assignments/{aid}").status_code == 404


def test_assignment_persists_via_db_layer():
    a = client.post("/api/assignments", json={
        "title": "Persist me", "assignees": ["bobby_lee"], "due_date": "2026-07-02",
        "priority": "medium", "status": "in-progress", "notes": "note",
    }).json()
    # read straight from the db module (proves it's actually stored, not just in a list)
    stored = main.db.get_assignment(a["id"])
    assert stored is not None
    assert stored["title"] == "Persist me"
    assert stored["assignees"] == ["bobby_lee"]


# ---------------------------------------------------------------------------
# Email integration (unconfigured state)
# ---------------------------------------------------------------------------

def test_email_status_configured_flag(monkeypatch):
    # With no Microsoft creds, the app must report not-configured (and not crash).
    monkeypatch.delenv("MS_CLIENT_ID", raising=False)
    monkeypatch.delenv("MS_CLIENT_SECRET", raising=False)
    r = client.get("/api/email/status")
    assert r.status_code == 200
    assert r.json()["configured"] is False

    # With creds present, it flips to configured.
    monkeypatch.setenv("MS_CLIENT_ID", "fake-id")
    monkeypatch.setenv("MS_CLIENT_SECRET", "fake-secret")
    assert client.get("/api/email/status").json()["configured"] is True


# ---------------------------------------------------------------------------
# Role-based access control (enforced mode)
# ---------------------------------------------------------------------------

def test_role_hierarchy_enforced(monkeypatch):
    """With AUTH_ENFORCED on, a user may only assign a level strictly below
    their own — and never escalate themselves. Guards against the privilege-
    escalation bug where any L1 could make themselves L3."""
    import auth
    monkeypatch.setenv("AUTH_ENFORCED", "true")
    for email, role in [("l3@k.us", "L3"), ("l2@k.us", "L2"),
                        ("l1@k.us", "L1"), ("t@k.us", "L1"), ("t2@k.us", "L2")]:
        main.db.upsert_user(email=email, name=email, role=role)

    def sess(email):
        return {auth.SESSION_COOKIE: auth.make_session_token(email)}

    def set_role(actor, target, role):
        return client.put(f"/api/users/{target}/role", json={"role": role},
                          cookies=sess(actor)).status_code

    assert set_role("l1@k.us", "t@k.us", "L1") == 403   # L1 can't manage anyone
    assert set_role("l2@k.us", "t@k.us", "L1") == 200   # L2 manages an L1
    assert set_role("l2@k.us", "t@k.us", "L2") == 403   # can't grant own level
    assert set_role("l2@k.us", "t2@k.us", "L1") == 403  # can't touch an L2
    assert set_role("l3@k.us", "t@k.us", "L2") == 200   # L3 grants up to L2
    assert set_role("l3@k.us", "t@k.us", "L3") == 403   # nobody mints an L3
    assert set_role("l3@k.us", "l3@k.us", "L2") == 403  # no self-edit


# ---------------------------------------------------------------------------
# Fail-closed hardening: enforcement must never run in a fail-open state.
# ---------------------------------------------------------------------------

def test_dev_login_disabled_when_enforced_even_if_sso_unconfigured(monkeypatch):
    """Dev-login is a no-password session mint. It must be off whenever auth is
    enforced — including when SSO isn't configured yet, which previously left it
    open and let anyone POST themselves an L3 session."""
    monkeypatch.setenv("AUTH_ENFORCED", "true")
    monkeypatch.delenv("MS_CLIENT_ID", raising=False)      # SSO NOT configured
    monkeypatch.delenv("MS_CLIENT_SECRET", raising=False)
    r = client.post("/api/auth/dev-login", json={"email": "x@k.us", "role": "L3"})
    assert r.status_code == 403


def test_dev_login_allowed_in_demo_mode():
    """With enforcement off (the demo default), dev-login still works."""
    r = client.post("/api/auth/dev-login", json={"email": "dev@k.us", "role": "L3"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "L3"


def test_can_grant_fails_closed_on_unknown_role():
    """A legacy/corrupt role string must not rank below everyone and become
    freely modifiable — an unknown role on either side is ungrantable."""
    import auth
    assert auth.can_grant("L3", "L2") is True
    assert auth.can_grant("L2", "L2") is False
    assert auth.can_grant("L3", "admin") is False   # unknown target -> protected
    assert auth.can_grant("admin", "L1") is False   # unknown actor -> powerless


def test_enforcement_config_errors_blocks_unsafe_enforcement(monkeypatch):
    """The startup guard flags every fail-open hole when enforcing, and clears
    once SESSION_SECRET, SSO, and FIRST_ADMIN_EMAIL are all set."""
    import auth
    # Not enforced -> no requirements at all.
    monkeypatch.setenv("AUTH_ENFORCED", "false")
    assert auth.enforcement_config_errors() == []

    # Enforced but nothing configured -> all three problems reported.
    monkeypatch.setenv("AUTH_ENFORCED", "true")
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("MS_CLIENT_ID", raising=False)
    monkeypatch.delenv("MS_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("FIRST_ADMIN_EMAIL", raising=False)
    assert len(auth.enforcement_config_errors()) == 3

    # Fully configured -> safe to enforce.
    monkeypatch.setenv("SESSION_SECRET", "a-real-long-random-secret")
    monkeypatch.setenv("MS_CLIENT_ID", "id")
    monkeypatch.setenv("MS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("FIRST_ADMIN_EMAIL", "boss@k.us")
    assert auth.enforcement_config_errors() == []


def test_decide_role_no_auto_l3_when_enforced(monkeypatch):
    """Under enforcement, only the pinned FIRST_ADMIN_EMAIL becomes L3; a random
    first sign-in does NOT inherit honcho via the count==0 bootstrap."""
    import auth
    monkeypatch.setenv("AUTH_ENFORCED", "true")
    monkeypatch.setenv("FIRST_ADMIN_EMAIL", "boss@k.us")
    assert auth.decide_role("boss@k.us") == "L3"
    assert auth.decide_role("stranger@k.us") == "L1"


# ---------------------------------------------------------------------------
# Knowledge graph — emails
# ---------------------------------------------------------------------------

def test_email_shows_in_knowledge_graph():
    """An email note must surface as an 'email' node in /api/graph and link to a
    team member it mentions. Regression guard: the graph once read the wrong
    metadata key ('note_type' vs 'type'), so email nodes never appeared."""
    member = client.get("/api/team").json()["team_members"][0]
    addr, login = member["email"], member["login"]

    note = client.post("/api/notes", json={
        "title": "Email: Graph regression check",
        "content": f"From: Boss <boss@kneron.us>\n\nLooping in {addr} on this.",
        "note_type": "email",
    }).json()

    try:
        g = client.get("/api/graph").json()
        email_nodes = [n for n in g["nodes"] if n["type"] == "email"]
        assert any("Graph regression check" in n["label"] for n in email_nodes), \
            "email note did not become an email node"
        pnode = "p:" + login
        linked = [e for e in g["edges"]
                  if pnode in (e["source"], e["target"])
                  and (e["source"].startswith("e:") or e["target"].startswith("e:"))]
        assert linked, "email node was not linked to the mentioned team member"
    finally:
        client.delete(f"/api/notes/{note['id']}")
