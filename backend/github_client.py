import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

GITHUB_API = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.client = httpx.Client(
            base_url=GITHUB_API,
            headers=headers,
            timeout=30.0,
        )

    def _get_all_pages(self, path: str, params: Dict = None) -> List[Dict]:
        items = []
        page = 1
        p = {**(params or {}), "per_page": 100, "page": page}
        while True:
            r = self.client.get(path, params=p)
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            items.extend(data)
            if len(data) < 100:
                break
            page += 1
            p["page"] = page
        return items

    def get_repo(self, owner_repo: str) -> Dict:
        owner, repo = owner_repo.split("/", 1)
        r = self.client.get(f"/repos/{owner}/{repo}")
        r.raise_for_status()
        return r.json()

    def get_issues(self, owner_repo: str) -> List[Dict]:
        owner, repo = owner_repo.split("/", 1)
        all_items = self._get_all_pages(
            f"/repos/{owner}/{repo}/issues",
            {"state": "open"},
        )
        # Filter out pull requests (GitHub returns PRs in issues endpoint)
        return [i for i in all_items if "pull_request" not in i]

    def get_pull_requests(self, owner_repo: str) -> List[Dict]:
        owner, repo = owner_repo.split("/", 1)
        return self._get_all_pages(
            f"/repos/{owner}/{repo}/pulls",
            {"state": "open"},
        )

    def get_milestones(self, owner_repo: str) -> List[Dict]:
        owner, repo = owner_repo.split("/", 1)
        return self._get_all_pages(
            f"/repos/{owner}/{repo}/milestones",
            {"state": "open"},
        )

    def get_recent_commits(self, owner_repo: str, days: int = 7) -> List[Dict]:
        owner, repo = owner_repo.split("/", 1)
        since = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat() + "Z"
        return self._get_all_pages(
            f"/repos/{owner}/{repo}/commits",
            {"since": since},
        )

    def aggregate_team_data(self, repos: List[str]) -> Dict:
        team_members: Dict[str, Dict] = {}
        projects = []
        all_issues = []
        all_prs = []

        for repo_str in repos:
            try:
                repo_meta = self.get_repo(repo_str)
                issues = self.get_issues(repo_str)
                prs = self.get_pull_requests(repo_str)
                milestones = self.get_milestones(repo_str)
                commits = self.get_recent_commits(repo_str)

                for issue in issues:
                    for assignee in issue.get("assignees", []):
                        login = assignee["login"]
                        m = team_members.setdefault(login, {
                            "login": login,
                            "avatar_url": assignee.get("avatar_url"),
                            "open_issues": 0,
                            "open_prs": 0,
                            "recent_commits": 0,
                            "repos_active": [],
                        })
                        m["open_issues"] += 1
                        if repo_str not in m["repos_active"]:
                            m["repos_active"].append(repo_str)

                for pr in prs:
                    login = pr["user"]["login"]
                    m = team_members.setdefault(login, {
                        "login": login,
                        "avatar_url": pr["user"].get("avatar_url"),
                        "open_issues": 0,
                        "open_prs": 0,
                        "recent_commits": 0,
                        "repos_active": [],
                    })
                    m["open_prs"] += 1
                    if repo_str not in m["repos_active"]:
                        m["repos_active"].append(repo_str)

                for commit in commits:
                    author = commit.get("author")
                    if author:
                        login = author["login"]
                        m = team_members.setdefault(login, {
                            "login": login,
                            "avatar_url": author.get("avatar_url"),
                            "open_issues": 0,
                            "open_prs": 0,
                            "recent_commits": 0,
                            "repos_active": [],
                        })
                        m["recent_commits"] += 1

                ms_list = [
                    {
                        "id": ms["number"],
                        "title": ms["title"],
                        "description": ms.get("description"),
                        "due_on": ms.get("due_on"),
                        "open_issues": ms["open_issues"],
                        "closed_issues": ms["closed_issues"],
                        "progress": round(
                            ms["closed_issues"]
                            / max(1, ms["open_issues"] + ms["closed_issues"])
                            * 100,
                            1,
                        ),
                        "repo": repo_str,
                    }
                    for ms in milestones
                ]

                projects.append({
                    "repo": repo_str,
                    "full_name": repo_meta.get("full_name", repo_str),
                    "description": repo_meta.get("description"),
                    "open_issues_count": len(issues),
                    "open_prs_count": len(prs),
                    "milestones": ms_list,
                })

                all_issues.extend([
                    {
                        "number": i["number"],
                        "title": i["title"],
                        "url": i["html_url"],
                        "state": i["state"],
                        "labels": [lb["name"] for lb in i.get("labels", [])],
                        "assignees": [a["login"] for a in i.get("assignees", [])],
                        "created_at": i["created_at"],
                        "updated_at": i["updated_at"],
                        "repo": repo_str,
                    }
                    for i in issues
                ])

                all_prs.extend([
                    {
                        "number": pr["number"],
                        "title": pr["title"],
                        "url": pr["html_url"],
                        "state": pr["state"],
                        "author": pr["user"]["login"],
                        "assignees": [a["login"] for a in pr.get("assignees", [])],
                        "created_at": pr["created_at"],
                        "updated_at": pr["updated_at"],
                        "repo": repo_str,
                        "draft": pr.get("draft", False),
                    }
                    for pr in prs
                ])

            except Exception as e:
                print(f"[github] Error fetching {repo_str}: {e}")

        for m in team_members.values():
            m["workload_score"] = round(
                m["open_issues"] * 1.0 + m["open_prs"] * 2.0 + m["recent_commits"] * 0.5,
                1,
            )

        return {
            "team_members": list(team_members.values()),
            "projects": projects,
            "issues": all_issues,
            "pull_requests": all_prs,
        }

    def close(self):
        self.client.close()
