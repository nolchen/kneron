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
    assert len(members) == 12
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
